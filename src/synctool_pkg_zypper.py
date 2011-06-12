#
#	synctool_pkg_zypper.py		WJ111
#
#   synctool by Walter de Jong <walter@heiho.net> (c) 2003-2011
#
#   synctool COMES WITH NO WARRANTY. synctool IS FREE SOFTWARE.
#   synctool is distributed under terms described in the GNU General Public
#   License.
#

import synctool_object
import synctool_lib

from synctool_lib import stderr
from synctool_pkgclass import SyncPkg

import os
import string


class SyncPkgZypper(SyncPkg):
	'''package installer class for zypper'''
	
	def __init__(self):
		SyncPkg.__init__(self)
	
	
	def list(self, pkgs = None):
		SyncPkg.list(self, pkgs)
		
		cmd = 'rpm -qa'			# zypper has no 'list-installed' ?
		
		if pkgs:
			cmd = cmd + ' ' + string.join(pkgs)
		
		synctool_lib.DRY_RUN = False
		synctool_lib.shell_command(cmd)
		synctool_lib.DRY_RUN = self.dryrun
	
	
	def install(self, pkgs):
		SyncPkg.install(self, pkgs)

		cmd = 'zypper -y install ' + string.join(pkgs)
		
		synctool_lib.shell_command(cmd)
	
	
	def remove(self, pkgs):
		SyncPkg.remove(self, pkgs)
		
		cmd = 'zypper -y remove ' + string.join(pkgs)
		
		synctool_lib.shell_command(cmd)
	
	
	def upgrade(self):
		SyncPkg.upgrade(self)
		
		if self.dryrun:
			cmd = 'zypper list-updates'
		else:
			cmd = 'zypper -y update'
		
		synctool_lib.DRY_RUN = False
		synctool_lib.shell_command(cmd)
		synctool_lib.DRY_RUN = self.dryrun
	
	
	def clean(self):
		SyncPkg.clean(self)
		
		# zypper has no 'clean' action; just delete the cache files
		
		cache_dir = '/var/lib/zypper/RPMS'
		try:
			files = os.listdir(cache_dir)
		except OSError, msg:
			stderr('error: %s' % msg)
		else:
			for file in files:
				fullname = os.path.join(cache_dir, file)
				
				obj = synctool_object.SyncObject(None, fullname, 0)
				obj.hard_delete_file()


# EOB