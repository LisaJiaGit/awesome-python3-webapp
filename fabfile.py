#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Lisa Jia'

'''
Deployment toolkit. 
'''

import os, re 
from datetime import datetime

from fabric.api import *

env.user = 'ubuntu'
env.sudo_user = 'root'
env.hosts = ['118.89.44.70']

db_user = 'www-data'
db_password = 'www-data'

_TAR_FILE = 'dist-awesome.tar.gz'

#tmp:temporary
_REMOTE_TMP_TAR = '/tmp/%s' % _TAR_FILE 

_REMOTE_BASE_DIR = '/srv/awesome'


def _current_path():
    return os.path.abspath('.')


def _now():
    return datetime.now().strftime('%y-%m-%d_%H.%M.%S')


def build():
    '''
    Build dist package.
    '''
    excludes = ['test', '.*', '*.pyc', '*.pyo']
    includes = ['static', 'templates', 'transwarp', 'favicon.ico', '*.py']
    #local() Run command on the local system.
    local('rm -f dist/%s' % _TAR_FILE)
    #cd local dir path
    with lcd(os.path.join(os.path.abspath('.'), 'www')):
        #tar '/www' to '/dist/dist-awesome.tar.gz' 
        #'-czvf': Compress file
        cmd = ['tar', '--dereference', '-czvf', '../dist/%s' % _TAR_FILE]
        cmd.extend(['--exclude=\'%s\'' % ex for ex in excludes])
        cmd.extend(includes)
        local(' '.join(cmd))    


def deploy():
    newdir = 'www-%s' % _now()
    run('rm -f %s' % _REMOTE_TMP_TAR)
    #Upload one or more files to a remote host.
    put('dist/%s' % _TAR_FILE, _REMOTE_TMP_TAR)
    
    with cd(_REMOTE_BASE_DIR):
        sudo('mkdir %s' % newdir)
    with cd('%s/%s' % (_REMOTE_BASE_DIR, newdir)):
        #'-xavf': decompress file
        sudo('tar -xzvf %s' % _REMOTE_TMP_TAR)
        sudo('chmod 755 app.py')
    with cd(_REMOTE_BASE_DIR):
        sudo('rm -rf www')
        sudo('ln -s %s www' % newdir)
        '''
        ???
        '''
        sudo('chown www-data:www-data www')
        sudo('chown -R www-data:www-data %s' % newdir)
    with settings(warn_only=True):
        sudo('supervisorctl stop awesome')
        sudo('supervisorctl start awesome')
        sudo('supervisorctl status')
        
        sudo('/etc/init.d/nginx reload')

