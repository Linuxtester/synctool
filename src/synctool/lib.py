#
#   synctool.lib.py        WJ109
#
#   synctool Copyright 2013 Walter de Jong <walter@heiho.net>
#
#   synctool COMES WITH NO WARRANTY. synctool IS FREE SOFTWARE.
#   synctool is distributed under terms described in the GNU General Public
#   License.
#

'''common functions/variables for synctool suite programs'''

import os
import sys
import subprocess
import shlex
import time
import syslog
import signal
import multiprocessing
import Queue

import synctool.param

# options (mostly) set by command-line arguments
DRY_RUN = True
VERBOSE = False
QUIET = False
UNIX_CMD = False
NO_POST = False
MASTERLOG = False

# print nodename in output?
# This option is pretty useless except in synctool-ssh it may be useful
OPT_NODENAME = True

MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

# enums for terse output
TERSE_INFO = 0
TERSE_WARNING = 1
TERSE_ERROR = 2
TERSE_FAIL = 3
TERSE_SYNC = 4
TERSE_LINK = 5
TERSE_MKDIR = 6
TERSE_DELETE = 7
TERSE_OWNER = 8
TERSE_MODE = 9
TERSE_EXEC = 10
TERSE_UPLOAD = 11
TERSE_NEW = 12
TERSE_TYPE = 13
TERSE_DRYRUN = 14
TERSE_FIXING = 15
TERSE_OK = 16

TERSE_TXT = (
    'info', 'WARN', 'ERROR', 'FAIL',
    'sync', 'link', 'mkdir', 'rm', 'chown', 'chmod', 'exec',
    'upload', 'new', 'type', 'DRYRUN', 'FIXING', 'OK'
)

COLORMAP = {
    'black'   : 30,
    'darkgray': 30,
    'red'     : 31,
    'green'   : 32,
    'yellow'  : 33,
    'blue'    : 34,
    'magenta' : 35,
    'cyan'    : 36,
    'white'   : 37,
    'bold'    : 1,
    'default' : 0,
}


def verbose(msg):
    '''do conditional output based on the verbose command line parameter'''

    if VERBOSE:
        print msg


def stdout(msg):
    '''print message to stdout (unless special output mode was selected)'''

    if not (UNIX_CMD or synctool.param.TERSE):
        print msg


def stderr(msg):
    '''print message to stderr
    I don't like stderr much, so it really prints to stdout'''

    print msg


def terse(code, msg):
    '''print short message + shortened filename'''

    if synctool.param.TERSE:
        # convert any path to terse path
        if msg.find(' ') >= 0:
            arr = msg.split()
            if arr[-1][0] == os.sep:
                arr[-1] = terse_path(arr[-1])
                msg = ' '.join(arr)

        else:
            if msg[0] == os.sep:
                msg = terse_path(msg)

        if synctool.param.COLORIZE:        # and sys.stdout.isatty():
            txt = TERSE_TXT[code]
            color = COLORMAP[synctool.param.TERSE_COLORS[
                             TERSE_TXT[code].lower()]]

            if synctool.param.COLORIZE_BRIGHT:
                bright = ';1'
            else:
                bright = ''

            if synctool.param.COLORIZE_FULL_LINE:
                print '\x1b[%d%sm%s %s\x1b[0m' % (color, bright, txt, msg)
            else:
                print '\x1b[%d%sm%s\x1b[0m %s' % (color, bright, txt, msg)
        else:
            print TERSE_TXT[code], msg


def unix_out(msg):
    '''output as unix shell command'''

    if UNIX_CMD:
        print msg


def prettypath(path):
    '''print long paths as "$overlay/path"'''

    if synctool.param.FULL_PATH:
        return path

    if synctool.param.TERSE:
        return terse_path(path)

    if path[:synctool.param.OVERLAY_LEN] == (synctool.param.OVERLAY_DIR +
                                             os.sep):
        return os.path.join('$overlay', path[synctool.param.OVERLAY_LEN:])

    if path[:synctool.param.DELETE_LEN] == (synctool.param.DELETE_DIR +
                                            os.sep):
        return os.path.join('$delete', path[synctool.param.DELETE_LEN:])

    if path[:synctool.param.PURGE_LEN] == (synctool.param.PURGE_DIR +
                                           os.sep):
        return os.path.join('$purge', path[synctool.param.PURGE_LEN:])

    return path


def terse_path(path, maxlen = 55):
    '''print long path as "//overlay/.../dir/file"'''

    if synctool.param.FULL_PATH:
        return path

    # by the way, this function will misbehave a bit for a _destination_
    # path named "/opt/synctool/var/" again
    # because this function doesn't know whether it is working with
    # a source or a destination path and it treats them both in the same way

    if path[:synctool.param.VAR_LEN] == (synctool.param.VAR_DIR +
                                         os.sep):
        path = os.sep + os.sep + path[synctool.param.VAR_LEN:]

    if len(path) > maxlen:
        arr = path.split(os.sep)

        while len(arr) >= 3:
            idx = len(arr) / 2
            arr[idx] = '...'
            new_path = os.sep.join(arr)

            if len(new_path) > maxlen:
                arr.pop(idx)
            else:
                return new_path

    return path


def terse_match(a_terse_path, path):
    '''Return True if it matches, else False'''

    if a_terse_path[:2] != os.sep + os.sep:
        # it's not a terse path
        return False

    idx = a_terse_path.find(os.sep + '...' + os.sep)
    if idx == -1:
        # apparently it's a very short terse path
        return a_terse_path[1:] == path

    # match last part of the path
    if a_terse_path[idx+4:] != path[-len(a_terse_path[idx+4:]):]:
        return False

    # match first part of the path
    # Note: this is OK for destination paths, but bugged for source paths;
    # in source paths, '//' should expand to $SYNCTOOL/var/
    # (But terse_match() is used with dest paths only anyway)
    return a_terse_path[1:idx+1] == path[:len(a_terse_path[1:idx+1])]


def terse_match_many(path, terse_path_list):
    '''Return index of first path match in list of terse paths'''

    idx = 0
    for a_terse_path in terse_path_list:
        if terse_match(a_terse_path, path):
            return idx

        idx += 1

    return -1


def dryrun_msg(msg):
    '''print a "dry run" message filled to (almost) 80 chars'''

    if not DRY_RUN:
        return msg

    l1 = len(msg) + 4

    add = '# dry run'
    l2 = len(add)

    i = 0
    while i < 4:
        # format output; align columns by steps of 20
        col = 79 + i * 20
        if l1 + l2 <= col:
            return msg + (' ' * (col - (l1 + l2))) + add

        i += 1

    # else return a longer message
    return msg + '    ' + add


def openlog():
    '''start logging'''

    if DRY_RUN or not synctool.param.SYSLOGGING:
        return

    syslog.openlog('synctool', 0, syslog.LOG_USER)


def closelog():
    '''stop logging'''

    if DRY_RUN or not synctool.param.SYSLOGGING:
        return

    log('--')
    syslog.closelog()


def _masterlog(msg):
    '''log only locally (on the master node)'''

    if DRY_RUN or not synctool.param.SYSLOGGING:
        return

    syslog.syslog(syslog.LOG_INFO|syslog.LOG_USER, msg)


def log(msg):
    '''log message to syslog'''

    if DRY_RUN or not synctool.param.SYSLOGGING:
        return

    if MASTERLOG:
        # print it with magic prefix,
        # synctool-master will pick it up
        print '%synctool-log%', msg
    else:
        _masterlog(msg)


def run_with_nodename(cmd_arr, nodename):
    '''run command and show output with nodename
    It will run regardless of what DRY_RUN is'''

    sys.stdout.flush()
    sys.stderr.flush()

    try:
        f = subprocess.Popen(cmd_arr, shell=False, bufsize=4096,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    except OSError, err:
        stderr('failed to run command %s: %s' % (cmd_arr[0], err.strerror))
        return

    with f:
        for line in f:
            line = line.strip()

            # if output is a log line, pass it to the master's syslog
            if line[:15] == '%synctool-log% ':
                if line[15:] == '--':
                    pass
                else:
                    _masterlog('%s: %s' % (nodename, line[15:]))
            else:
                # pass output on; simply use 'print' rather than 'stdout()'
                if OPT_NODENAME:
                    print '%s: %s' % (nodename, line)
                else:
                    # do not prepend the nodename of this node to the output
                    # if option --no-nodename was given
                    print line


def shell_command(cmd):
    '''run a shell command
    Unless DRY_RUN is set'''

    if DRY_RUN:
        not_str = 'not '
    else:
        not_str = ''

    # a command can have arguments
    cmd_arr = shlex.split(cmd)
    cmdfile = cmd_arr[0]

    if not QUIET:
        stdout('%srunning command %s' % (not_str, prettypath(cmd)))

    verbose(dryrun_msg('  os.system(%s)' % prettypath(cmd)))
    unix_out('# run command %s' % cmdfile)
    unix_out(cmd)
    terse(TERSE_EXEC, cmdfile)

    if not DRY_RUN:
        sys.stdout.flush()
        sys.stderr.flush()

        try:
            subprocess.call(cmd, shell=True)
        except OSError, err:
            stderr("failed to run shell command '%s' : %s" % (prettypath(cmd),
                                                              err.strerror))
        sys.stdout.flush()
        sys.stderr.flush()


def exec_command(cmd_arr):
    '''run a command given in cmd_arr, regardless of DRY_RUN
    Returns: return code of execute command or -1 on error'''

    if not cmd_arr:
        raise RuntimeError, 'cmd_arr is not set'

    sys.stdout.flush()
    sys.stderr.flush()

    err = 0
    try:
        err = subprocess.call(cmd_arr, shell=False)
    except OSError, err:
        stderr('error: failed to exec %s: %s' % (cmd_arr[0], err.strerror))
        err = -1

    sys.stdout.flush()
    sys.stderr.flush()
    return err


def search_path(cmd):
    '''search the PATH for the location of cmd'''

    # maybe a full path was given
    path, _ = os.path.split(cmd)
    if path and os.path.isfile(cmd) and os.access(cmd, os.X_OK):
        return cmd

    # search the PATH environment variable
    if not os.environ.has_key('PATH'):
        return None

    env_path = os.environ['PATH']
    if not env_path:
        return None

    for path in env_path.split(os.pathsep):
        fullpath = os.path.join(path, cmd)
        # check that the command is an executable file
        if os.path.isfile(fullpath) and os.access(fullpath, os.X_OK):
            return fullpath

    return None


def mkdir_p(path):
    '''like mkdir -p; make directory and subdirectories
    Returns False on error, else True'''

    if os.path.exists(path):
        return True

    # temporarily restore admin's umask
    mask = os.umask(synctool.param.ORIG_UMASK)

    try:
        os.makedirs(path)
    except OSError, err:
        stderr('error: failed to create directory %s: %s' % (path,
                                                             err.strerror))
        os.umask(mask)
        return False

    os.umask(mask)
    return True


#
#   functions for straightening out paths that were given by the user
#

def strip_multiple_slashes(path):
    '''remove double slashes from path'''

    # like os.path.normpath(), but do not change symlinked paths

    if not path:
        return path

    double = os.sep + os.sep
    while path.find(double) != -1:
        path = path.replace(double, os.sep)

    if os.path.altsep:
        double = os.path.altsep + os.path.altsep
        while path.find(double) != -1:
            path = path.replace(double, os.sep)

    if path.find(os.sep + '...' + os.sep) >= 0:
        # a terse path is marked with '//' at the beginning
        path = os.sep + path

    return path


def strip_trailing_slash(path):
    '''remove trailing slash from path'''

    if not path:
        return path

    while len(path) > 1 and path[-1] == os.sep:
        path = path[:-1]

    return path


def strip_path(path):
    '''remove trailing and multiple slashes from path'''

    if not path:
        return path

    path = strip_multiple_slashes(path)
    path = strip_trailing_slash(path)

    return path


def strip_terse_path(path):
    '''strip a terse path'''

    if not path:
        return path

    if not synctool.param.TERSE:
        return strip_path(path)

    # terse paths may start with two slashes
    if len(path) >= 2 and path[:1] == '//':
        is_terse = True
    else:
        is_terse = False

    path = strip_multiple_slashes(path)
    path = strip_trailing_slash(path)

    # the first slash was accidentally stripped, so restore it
    if is_terse:
        path = os.sep + path

    return path


def prepare_path(path):
    '''strip path, and replace $SYNCTOOL by the installdir'''

    if not path:
        return path

    path = strip_multiple_slashes(path)
    path = strip_trailing_slash(path)
    path = path.replace('$SYNCTOOL/', synctool.param.ROOTDIR + os.sep)
    return path


def multiprocess(fn, work):
    '''run a function in parallel'''

    # Thanks go to Bryce Boe
    # http://www.bryceboe.com/2010/08/26/ \
    #   python-multiprocessing-and-keyboardinterrupt/

    if synctool.param.SLEEP_TIME != 0:
        synctool.param.NUM_PROC = 1

    # make a work queue
    jobq = multiprocessing.Queue()
    for item in work:
        jobq.put(item)

    # start NUMPROC worker processes
    pool = []
    i = 0
    while i < synctool.param.NUM_PROC:
        p = multiprocessing.Process(target=_worker, args=(fn, jobq))
        pool.append(p)
        p.start()
        i += 1

    try:
        for p in pool:
            p.join()

    except KeyboardInterrupt:
        # user hit Ctrl-C
        # terminate all workers
        for p in pool:
            p.terminate()
            p.join()

        # re-raise KeyboardInterrupt, for __main__ to catch
        raise


def _worker(fn, jobq):
    '''fn is the worker function to call
    jobq is a multiprocessing.Queue of function arguments
    If --zzz was given, sleep after finishing the work
    No return value is passed back'''

    # ignore interrupts, ignore Ctrl-C
    # the Ctrl-C will be caught by the parent process
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while not jobq.empty():
        try:
            arg = jobq.get(block=False)
        except Queue.Empty:
            break

        else:
            fn(arg)

            if synctool.param.SLEEP_TIME > 0:
                time.sleep(synctool.param.SLEEP_TIME)


if __name__ == '__main__':
    # __main__ is needed because of multiprocessing module
    pass


# EOB
