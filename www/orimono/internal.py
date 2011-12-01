'''
This houses our fabric commands for handling local (i.e., perforce-connected) servers
'''

from fabric.api import *
from fabric.context_managers import *
import config
import database
from helpers import *
from log import log
import os
import re
import datetime

# local alias to db connection
db = database.db

# compiled regexs
changelist_re = re.compile(r'Change (\d*) on (\d{4}\/\d{2}\/\d{2}) by (.*?@.*?) \'(.*?)\'')
branch_re = re.compile(r'Branch Spark_(.*?) (\d{4})\/(\d{2})\/(\d{2}) \'(.*?)\'')

def get_mapping(mapping_name):
    '''
    get a mapping record
    '''
    mapping = db.select('mappings',where='site=$site', vars = {'site': mapping_name })
    if mapping:
        return mapping[0]
    else:
        raise Exception('unknown mapping %s' % mapping_name)
    
def get_branch(mapping_name):
    ''' 
    get a branch version for a particular mapping
    '''
    with settings(mapping = os.path.realpath(get_mapping_site(mapping_name))):
        branch = env['mapping'].split('/')[-1]
        return branch
        
def get_version(mapping_name):
    ''' 
    get the latest changelist in a particular branch
    '''
    changes = get_changes(mapping_name, 1)
    if len(changes) > 0:
        return changes[0][0]
    else:
        return None
    
def get_changes(mapping_name, m = 1):
    ''' 
    get a list of M changelists for a particular branch
    '''
    with settings(branch = os.path.realpath(get_mapping_site(mapping_name)), m = m):
        with shell_env(**config.SHELL_ENV):
            raw_changes = local("/usr/local/bin/p4 changes -m%(m)s %(branch)s/..." % env, capture = True).split('\n') 
            changes = [] # list of tuples: (change_number, date, committed_by, truncated_msg)
            for rc in raw_changes:
                m = changelist_re.match(rc)
                if m:
                    changes.append(m.groups(0))
            return changes
            
def get_branches(project = 'Spark', n=5):
    ''' 
    get a list of N branches under a particular project
    note that until we have at least perforce 2010.2 
    the p4 branches command cannot filter itself by name
    instead, we're just using our convention of naming
    all branches Spark_*. obviously this will change as we
    create a proper SiTi branch, so this function will need
    to be revisited and updated.
    '''
    with settings(project = project, n = n):
        with shell_env(**config.SHELL_ENV):
            raw_branches = local("/usr/local/bin/p4 branches | grep %(project)s" % env, capture = True).split('\n')
            branches = [] # list of tuples: (branch version, datetime, message)
            for rb in raw_branches:
                m = branch_re.match(rb)
                if m:
                    t = m.groups(0)
                    branches.append((t[0],datetime.datetime(int(t[1]),int(t[2]), int(t[3])), t[4]))
                    
            branches = sorted(branches, key=lambda b: (b[1],b[0]), reverse=True)
            return branches[:n] 
    
def update(mapping_name):
    '''
    do a perforce sync followed by djangomigrate
    '''
    with settings(mapping = os.path.realpath(get_mapping_site(mapping_name))):
        with shell_env(**config.SHELL_ENV):
            log('local_update_start',None,mapping_name, 'Starting local update...')
            sync = local_sudo("/usr/local/bin/p4 sync %(mapping)s/..." % env, capture = True, user = config.P4_USER)
            log('local_update_finish',sync,mapping_name, 'Finished local update...')
            migrate(mapping_name)
            build(mapping_name)
            updated_version =  get_version(mapping_name)
            db.update('mappings',where="site=$site", vars={'site':mapping_name}, datetime=datetime.datetime.now(), changelist = updated_version, branch = get_branch(mapping_name))
            return updated_version

def migrate(mapping_name):
    ''' 
    replaces djangomigrate for a particular mapping
    '''
    with settings(mapping_root = get_mapping_root(mapping_name), mapping_application = get_mapping_application(mapping_name), branch=os.path.realpath(get_mapping_site(mapping_name))):
        with shell_env(PYTHONPATH="%(mapping_root)s:%(mapping_application)s" % env):
            log('local_migrate_start', None, mapping_name, 'Starting local migrate (this could take a while)...')
            migrate = local_sudo("python2.6 %(mapping_application)s/manage.py migrate lib" % env, capture = True, user = config.P4_USER)
            log('local_migrate_finish', migrate, mapping_name, 'Finished local migrate...')
            log ('local_refresh_start', None, mapping_name, 'Starting local refresh (this could take a while)...')
            refresh = local_sudo("python2.6 -uc 'import tools.refresh'" % env, capture = True, user = config.P4_USER)
            log('local_refresh_finish', refresh, mapping_name, 'Finished local refresh...')
  
def build(mapping_name):
    '''
    run build/build to create optimized js, etc
    '''
    with settings(mapping_site = get_mapping_site(mapping_name)):
        # build = local_sudo("cd %(mapping_site)s/build && ./build" % env, capture = True)
        # TODO - fix this, as sudo can't cd, so right now you have to have sudo w/o passwords
        log('local_build_start', None, mapping_name, 'Starting local build...')
        build = local("cd %(mapping_site)s/build && sudo ./build" % env, capture = True)
        log('local_build_finish', build, mapping_name, 'Finished local build...')
    
def restart_presence(mapping_name):
    '''
    restart the presence server for a particular mapping
    TODO - rewrite this script in python with system calls 
    instead of calling a bash script that is difficult to maintain
    '''
    with settings(mapping=mapping_name):
        restart = local_sudo("python2.6 /home/httpd/scripts/presencedaemon.py %(mapping)s restart" % env, capture = True)
        log('local_presence_restart', restart, mapping_name, 'Restarte local presence...')
        return True
        
def change_local_mapping(mapping_name, new_branch):
    '''
    changes a local mapping to a new branch
    '''
    with settings(mapping_root = get_mapping_root(mapping_name), mapping = get_mapping_site(mapping_name), branch = get_branch_path(new_branch), warn_only= True):
        if not os.path.isdir(env['branch']):
            raise Exception('Error - branch %(branch)s does not exist' % env)
        local_sudo("rm -f %(mapping)s" % env, capture = False) 
        change = local_sudo("ln -s %(branch)s %(mapping)s" % env, capture = False)
        log('local_mapping_change', change, mapping_name, 'Local mapping changed...')
        update_version = update(mapping_name)
        db.update('mappings', where="site=$site", vars = {'site':mapping_name}, datetime=datetime.datetime.now(), changelist = update_version, branch= new_branch)
        return update_version
