#! /usr/bin/env python
#
#	synctool_master.py	WJ109
#

import synctool_config
import synctool_ssh

import os
import sys
import string
import getopt


OPT_SKIP_RSYNC = 0

PASS_ARGS = None


def rsync_masterdir(cfg, nodes):
	if not cfg.has_key('rsync_cmd'):
		print '%s: error: rsync_cmd has not been defined in %s' % (os.path.basename(sys.argv[0]), synctool_config.CONF_FILE)
		sys.exit(-1)

	rsync_cmd = cfg['rsync_cmd']

	synctool_ssh.run_parallel(cfg, nodes, '%s %s/' % (rsync_cmd, cfg['masterdir']), '%s/' % cfg['masterdir'], ':')


def run_remote_synctool(cfg, nodes):
	if not cfg.has_key('synctool_cmd'):
		print '%s: error: synctool_cmd has not been defined in %s' % (os.path.basename(sys.argv[0]), synctool_config.CONF_FILE)
		sys.exit(-1)

	synctool_cmd = cfg['synctool_cmd']

	synctool_ssh.run_remote_cmd(cfg, nodes, '%s %s' % (synctool_cmd, PASS_ARGS))


def usage():
	print 'usage: %s [options] [<arguments>]' % os.path.basename(sys.argv[0])
	print 'options:'
	print '  -h, --help                     Display this information'
	print '  -c, --conf=dir/file            Use this config file (default: %s)' % synctool_config.DEFAULT_CONF
	print '  -v, --verbose                  Be verbose'
	print '  -q, --quiet                    Suppress informational startup messages'
	print
	print '  -n, --node=nodelist            Execute only on these nodes'
	print '  -g, --group=grouplist          Execute only on these groups of nodes'
	print '  -x, --exclude=nodelist         Exclude these nodes from the selected group'
	print '  -X, --exclude-group=grouplist  Exclude these groups from the selection'
	print
	print '  -d, --diff=file                Show diff for file'
	print '  -1, --single=file              Update a single file'
	print '  -t, --tasks                    Run the scripts in the tasks/ directory'
	print '  -f, --fix                      Perform updates (otherwise, do dry-run)'
	print '      --skip-rsync               Do not sync the repository'
	print '                                 (eg. when it is on a shared filesystem)'
	print
	print 'A nodelist or grouplist is a comma-separated list'
	print 'Note that by default, it does a dry-run, unless you specify --fix'
	print
	print 'Written by Walter de Jong <walter@sara.nl> (c) 2003-2009'


def get_options():
	global PASS_ARGS, OPT_SKIP_RSYNC

#	if len(sys.argv) <= 1:
#		usage()
#		sys.exit(1)

	try:
		opts, args = getopt.getopt(sys.argv[1:], "hc:n:g:x:X:d:1:tfvq", ['help', 'conf=', 'debug', 'node=', 'group=',
			'exclude=', 'exclude-group=', 'diff=', 'single=', 'tasks', 'fix', 'verbose', 'quiet', 'skip-rsync'])
	except getopt.error, (reason):
		print '%s: %s' % (os.path.basename(sys.argv[0]), reason)
#		usage()
		sys.exit(1)

	except getopt.GetoptError, (reason):
		print '%s: %s' % (os.path.basename(sys.argv[0]), reason)
#		usage()
		sys.exit(1)

	except:
		usage()
		sys.exit(1)

	synctool_ssh.NODELIST = ''
	synctool_ssh.GROUPLIST = ''

	PASS_ARGS = ''

	for opt, arg in opts:
		if opt in ('-h', '--help', '-?'):
			usage()
			sys.exit(1)

		if opt in ('-c', '--conf'):
			synctool_config.CONF_FILE = arg
			continue

		if opt in ('-n', '--node'):
			if not synctool_ssh.NODELIST:
				synctool_ssh.NODELIST = arg
			else:
				synctool_ssh.NODELIST = synctool_ssh.NODELIST + ',' + arg
			continue

		if opt in ('-g', '--group'):
			if not synctool_ssh.GROUPLIST:
				synctool_ssh.GROUPLIST = arg
			else:
				synctool_ssh.GROUPLIST = synctool_ssh.GROUPLIST + ',' + arg
			continue

		if opt in ('-x', '--exclude'):
			if not synctool_ssh.EXCLUDELIST:
				synctool_ssh.EXCLUDELIST = arg
			else:
				synctool_ssh.EXCLUDELIST = synctool_ssh.EXCLUDELIST + ',' + arg
			continue

		if opt in ('-X', '--exclude-group'):
			if not synctool_ssh.EXCLUDEGROUPS:
				synctool_ssh.EXCLUDEGROUPS = arg
			else:
				synctool_ssh.EXCLUDEGROUPS = synctool_ssh.EXCLUDEGROUPS + ',' + arg
			continue

		if opt == '--skip-rsync':
			OPT_SKIP_RSYNC = 1
			continue

#		if opt in ('-d', '--diff'):
#			OPT_SKIP_RSYNC = 1
##			continue					fall through

		PASS_ARGS = PASS_ARGS + ' ' + opt

		if arg:
			PASS_ARGS = PASS_ARGS + ' ' + arg

	if args:
		PASS_ARGS = PASS_ARGS + ' ' + string.join(args)

	if len(PASS_ARGS) > 0 and PASS_ARGS[0] == ' ':
		PASS_ARGS = PASS_ARGS[1:]


if __name__ == '__main__':
	get_options()

	cfg = synctool_config.read_config()
	nodes = synctool_ssh.make_nodeset(cfg)

#############
#
#	enable debugging
#
#############
#	synctool_config.OPT_DEBUG = 1
#	synctool_ssh.OPT_DEBUG = 1

	if not OPT_SKIP_RSYNC:
		rsync_masterdir(cfg, nodes)

	run_remote_synctool(cfg, nodes)


# EOB