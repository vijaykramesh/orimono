'''
This houses our fabric commands for handling external (i.e., perforce-naive) servers
'''

from fabric.api import *
from fabric.context_managers import *
import fabric.network
import config
import database
from helpers import *
from log import log
import orimono.internal
import os
import re
import datetime

# local alias to db connection
db = database.db

# compiled regexs
changelist_re = re.compile(r'Change (\d*) on (\d{4}\/\d{2}\/\d{2}) by (.*?@.*?) \'(.*?)\'')
branch_re = re.compile(r'Branch Spark_(.*?) (\d{4})\/(\d{2})\/(\d{2}) \'(.*?)\'')

def get_mapping(mapping_name, force_fetch = False):
    '''
    get the mapping record for a deployed site
    '''
    
    # try to pull the info from the database first
    if not force_fetch:
        mapping = db.select('mappings',where='site=$site', vars = {'site': mapping_name })
        if mapping:
           return mapping[0]
            
    # otherwise get it from the server, and update the db for good measure
    with settings(host_string = get_http_host(mapping_name), mapping = get_mapping_site(mapping_name)):
        deploy = run('readlink -f %(mapping)s' % env)
        fabric.network.disconnect_all()
        root, app = os.path.split(deploy)
        uzume, dt, cl = app.split('-')
        mapping = db.select('mappings', where='site=$site', vars = {'site': mapping_name})
        if mapping:
            m = mapping[0]
            if m['changelist'] != cl:
                db.update('mappings',where="id=$id", vars={'id': m['id']}, datetime=dt, changelist = cl)
            return m
        else:
            # this is bad, we don't know what branch the code is!
            db.insert('mappings', datetime = dt, site = mapping_name, changelist = cl)
            return get_mapping(mapping_name, False)
      
def get_changes(mapping_name, m = 1):
    ''' 
    get a list of M changelists for a particular mapping
    requires our mappings db having branch info for the 
    external mapping
    '''
    mapping = get_mapping(mapping_name)
    if not mapping['branch']:
        raise Exception('Unknown branch for %s' % mapping_name)
    
    with settings(branch = os.path.realpath(get_branch_path(mapping['branch'])), m = m):
        with shell_env(**config.SHELL_ENV):
            raw_changes = local("/usr/local/bin/p4 changes -m%(m)s %(branch)s/..." % env, capture = True).split('\n') 
            changes = [] # list of tuples: (change_number, date, committed_by, truncated_msg)
            for rc in raw_changes:
                m = changelist_re.match(rc)
                if m:
                    changes.append(m.groups(0))
            return changes
                            
def deploy_from_local(local_mapping_name, external_mapping_name, include_content = False):
    '''
    deploy from local_mapping_name to external mapping name
    '''
    formatted_timestamp = datetime.datetime.now().strftime('%Y%m%d')
    local_mapping = orimono.internal.get_mapping(local_mapping_name)
    
    deploy_name = 'uzume-%s-%s' % (formatted_timestamp, local_mapping['changelist'])
    archive_name = '%s.tgz' % deploy_name
    transform = "s,^,%s/,S" % deploy_name
    log('external_start_deploy', "updating to %s (%s) from %s" % (local_mapping['branch'], local_mapping['changelist'], local_mapping_name), external_mapping_name, 'Starting deploy of %s (%s) from %s to %s' % (local_mapping['branch'], local_mapping['changelist'], local_mapping_name, external_mapping_name) )
    with settings(
                host_string = get_http_host(external_mapping_name), 
                passwords = config.PASSWORDS,
                local_mapping = get_mapping_site(local_mapping_name), 
                branch = local_mapping['branch'],
                changelist = local_mapping['changelist'],
                external_mapping_root = get_mapping_root(external_mapping_name),
                external_mapping_site = get_mapping_site(external_mapping_name),
                external_mapping_application = get_mapping_application(external_mapping_name),
                transform = transform, 
                archive_name = archive_name, 
                deploy_name = deploy_name, 
                package_path = config.PACKAGE_PATH, 
                branch_root = config.BRANCH_ROOT,
                san_share = config.SAN_SHARE,
                tar_exclude = '' if include_content else "--exclude='uzume/data/content/*'"):
        local('/usr/local/bin/tar --transform %(transform)s -czf %(package_path)s/%(archive_name)s -C %(local_mapping)s %(tar_exclude)s .' % env)
        log('external_scp', None, external_mapping_name, 'Copying deploy archive (this will take a few minutes)...')
        put('%(package_path)s/%(archive_name)s' % env, env['san_share'])
        unpack = run('/usr/local/bin/tar xzf %(san_share)s%(archive_name)s -C %(branch_root)s' % env)
        log('external_http_unpack', unpack, external_mapping_name, 'Unpacked deploy archive to http server...')
        run('rm -f %(branch_root)scurrent && ln -fs %(branch_root)s%(deploy_name)s %(branch_root)scurrent' % env)
        run("find %(branch_root)scurrent/ -name '*.pyc' -exec rm -f {} \;" % env)
        sudo("/usr/local/bin/sed -i --follow-symlinks \"s/BUILD_VERSION = '.*'/BUILD_VERSION = '%(branch)s %(changelist)s'/\" %(external_mapping_root)s/settingslocal.py" % env)
        restart = sudo('/usr/sbin/apachectl restart')
        log('external_httpd_restart', restart, external_mapping_name, 'Restarted Apache...') 
        with shell_env(PYTHONPATH="%(external_mapping_root)s:%(external_mapping_application)s" % env):
            log('external_migrate_start', None, external_mapping_name, 'Starting external migrate (this could take a while)...')
            migrate = run("python2.6 %(external_mapping_application)s/manage.py migrate lib" % env)
            log('external_migrate_finish', migrate, external_mapping_name, 'Finished external migrate...')
            log('external_refresh_start', None, external_mapping_name, 'Starting external refresh (this could take a while)...')
            refresh = run("python2.6 -uc 'import tools.refresh'" % env)
            log('external_refresh_finish', refresh, external_mapping_name, 'Finished external refresh...')
        with cd("%(external_mapping_site)s/build" % env):
            log('external_build_start', None, external_mapping_name, 'Starting external build...')
            build = sudo("./build")
            log('external_build_finish', build, external_mapping_name, 'Finished external build...')
    with settings(
                host_string = get_presence_host(external_mapping_name),
                passwords = config.PASSWORDS,
                external_mapping_name = external_mapping_name,
                archive_name = archive_name,    
                deploy_name = deploy_name,
                package_path = config.PACKAGE_PATH,
                branch_root = config.BRANCH_ROOT,
                san_share = config.SAN_SHARE):
        
        unpack = run('/usr/local/bin/tar xzf %(san_share)s%(archive_name)s -C %(branch_root)s' % env)
        log('external_presence_unpack', unpack, external_mapping_name, 'Unpacked deploy archive to presence server...' )
        run('rm -f %(branch_root)scurrent && ln -fs %(branch_root)s%(deploy_name)s %(branch_root)scurrent' % env)
        run("find %(branch_root)scurrent/ -name '*.pyc' -exec rm -f {} \;" % env)
        restart_presence(external_mapping_name)        
    db.update('mappings', where='site=$site', vars = { 'site': external_mapping_name }, datetime = datetime.datetime.now(), changelist = local_mapping['changelist'], branch = local_mapping['branch'])
    log('external_finish_deploy', 'updated %s to %s (%s) from %s' % (external_mapping_name, local_mapping['branch'], local_mapping['changelist'], local_mapping['site']), external_mapping_name, 'Completed external deploy...')
    fabric.network.disconnect_all()
    return get_mapping(external_mapping_name)
    
def restart_presence(external_mapping_name):
    with settings(
                host_string = get_presence_host(external_mapping_name),
                passwords = config.PASSWORDS,
                external_mapping_name = external_mapping_name,
                mapping_root = get_mapping_root(external_mapping_name),
                mapping_application = get_mapping_application(external_mapping_name)
               ):
        restart = sudo("python2.6 /home/httpd/scripts/presencedaemon.py %(external_mapping_name)s restart" % env, shell = False)
        log('external_presence_restart', restart, external_mapping_name, "Restarted external presence...")
        fabric.network.disconnect_all()
        return True
        
def deploy_from_external(from_mapping_name, to_mapping_name):
    '''
    deploys code from one external mapping to another
    currently assumes both external mappings have access 
    to config.SAN_SHARE -- will want to update this to allow
    for non-san-aware pushes also.
    '''

    
    formatted_timestamp = datetime.datetime.now().strftime('%Y%m%d')
    from_mapping = orimono.external.get_mapping(from_mapping_name)
    deploy_name = 'uzume-%s-%s' % (formatted_timestamp, from_mapping['changelist'])
    archive_name = '%s.tgz' % deploy_name
    log('external_start_deploy', "updating to %s (%s) from %s" % (from_mapping['branch'], from_mapping['changelist'], from_mapping_name), to_mapping_name, 'Starting deploy of %s (%s) from %s to %s' % (from_mapping['branch'], from_mapping['changelist'], from_mapping_name, to_mapping_name) )
    with settings(
                host_string = get_http_host(to_mapping_name), 
                passwords = config.PASSWORDS,
                from_mapping = get_mapping_site(from_mapping_name), 
                branch = from_mapping['branch'],
                changelist = from_mapping['changelist'],
                to_mapping_root = get_mapping_root(to_mapping_name),
                to_mapping_site = get_mapping_site(to_mapping_name),
                to_mapping_application = get_mapping_application(to_mapping_name),
                archive_name = archive_name,    
                deploy_name = deploy_name,                
                branch_root = config.BRANCH_ROOT,
                san_share = config.SAN_SHARE,
                ):
        
        unpack = run('/usr/local/bin/tar xzf %(san_share)s%(archive_name)s -C %(branch_root)s' % env)
        log('external_http_unpack', unpack, to_mapping_name, 'Unpacked deploy archive to http server...')
        #~ TODO - enter maintenance mode, send broadcast, delay this action for N minutes
        
        run('rm -f %(branch_root)scurrent && ln -fs %(branch_root)s%(deploy_name)s %(branch_root)scurrent' % env)
        run("find %(branch_root)scurrent/ -name '*.pyc' -exec rm -f {} \;" % env)
        sudo("/usr/local/bin/sed -i --follow-symlinks \"s/BUILD_VERSION = '.*'/BUILD_VERSION = '%(branch)s %(changelist)s'/\" %(to_mapping_root)s/settingslocal.py" % env)
        restart = sudo('/usr/sbin/apachectl restart')
        log('external_httpd_restart', restart, to_mapping_name, 'Restarted Apache...') 
        with shell_env(PYTHONPATH="%(to_mapping_root)s:%(to_mapping_application)s" % env):
            log('external_migrate_start', None, to_mapping_name, 'Starting external migrate (this could take a while)...')
            migrate = run("python2.6 %(to_mapping_application)s/manage.py migrate lib" % env)
            log('external_migrate_finish', migrate, to_mapping_name, 'Finished external migrate...')
            log('external_refresh_start', None, to_mapping_name, 'Starting external refresh (this could take a while)...')
            refresh = run("python2.6 -uc 'import tools.refresh'" % env)
            log('external_refresh_finish', refresh, to_mapping_name, 'Finished external refresh...')
        with cd("%(to_mapping_site)s/build" % env):
            log('external_build_start', None, to_mapping_name, 'Starting external build...')
            build = sudo("./build")
            log('external_build_finish', build, to_mapping_name, 'Finished external build...')
    with settings(
                host_string = get_presence_host(to_mapping_name),
                passwords = config.PASSWORDS,
                to_mapping_name = to_mapping_name,
                archive_name = archive_name,    
                deploy_name = deploy_name,
                package_path = config.PACKAGE_PATH,
                branch_root = config.BRANCH_ROOT,
                san_share = config.SAN_SHARE):
        
        unpack = run('/usr/local/bin/tar xzf %(san_share)s%(archive_name)s -C %(branch_root)s' % env)
        log('external_presence_unpack', unpack, to_mapping_name, 'Unpacked deploy archive to presence server...' )
        run('rm -f %(branch_root)scurrent && ln -fs %(branch_root)s%(deploy_name)s %(branch_root)scurrent' % env)
        run("find %(branch_root)scurrent/ -name '*.pyc' -exec rm -f {} \;" % env)
        restart_presence(to_mapping_name)        
    db.update('mappings', where='site=$site', vars = { 'site': to_mapping_name }, datetime = datetime.datetime.now(), changelist = from_mapping['changelist'], branch = from_mapping['branch'])
    log('external_finish_deploy', 'updated %s to %s (%s) from %s' % (to_mapping_name, from_mapping['branch'], from_mapping['changelist'], from_mapping['site']), to_mapping_name, 'Completed external deploy...')
    fabric.network.disconnect_all()
    return get_mapping(to_mapping_name)
