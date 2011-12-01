import web
import config
import database
from log import log
from helpers import *
import orimono.internal
import orimono.external
import sys
import os
import datetime
import json

web.config.debug = config.DEBUG

# url mapping
urls = (
    '/', 'Index',
    '/login/', 'Login',
    '/logout/', 'Logout',
    '/internal/', 'Internal',
    '/internal/update/', 'InternalUpdate',
    '/internal/restartpresence/', 'InternalRestartPresence',
    '/internal/changemapping/', 'InternalChangeMapping',
    '/external/', 'External',
    '/external/deploy/internal/', 'ExternalDeployInternal',
    '/external/deploy/external/', 'ExternalDeployExternal', 
    '/external/restartpresence/', 'ExternalRestartPresence',
    '/admin/populate/mappings/', 'AdminPopulateMappings',
    '/admin/update/internal/', 'AdminUpdateInternal',
)

# define our application
app = web.application(urls, globals())
application = app.wsgifunc()

# local db alias
db = database.db

# session
if web.config.debug:
    # we do a weird hack to enable session with debug on
    if web.config.get('_session') is None:
        session = web.session.Session(app, web.session.DBStore(db,'sessions'), initializer = {'login': 0, 'permission': 0, 'username': None})
        web.config._session = session
    else:
        session = web.config._session
else:
    # otherwise just init it normally
    session = web.session.Session(app, web.session.DBStore(db,'sessions'), initializer = {'login': 0, 'permission': 0, 'username': None})
    



def logged():
    if session.get('login', False) == 1:
        return True
    else:
        return False
        
def permission(v = None):
    ''' 
    can be used to check against a particular passed permission
    or just returns the permission level for a logged in user
    '''
    
    if not logged() or not session.permission: return False
    if v:
        if session.permission >= v:
            return True
        else:
            return False
            
    return session.permission
    
def checkaccess(auth = False, level = 0):
    ''' 
    our check login & potentially permission level decorator
    '''
    def decorator(func):
        def proxyfunc(self, *args, **kwargs):
            if not logged():
                raise web.seeother('/login/')
            if auth == True:
                if not permission(level):
                    raise web.seeother('/?error=permission')
            return func(self, *args, **kwargs)
        return proxyfunc
    return decorator
        
def checkadmin():
    '''
    verifies a request came from localhost
    todo - implement better security here
    '''
    def decorator(func):
        def proxyfunc(self, *args, **kwargs):
            if web.ctx.ip != config.SAPPER_IP:
                raise web.seeother('/login/')
            return func(self, *args, **kwargs)
        return proxyfunc
    return decorator


# defining template bases, etc
render = web.template.render('templates/', base='base', globals = {'local_mappings': config.MAPPINGS, 'external_mappings': config.EXTERNAL_MAPPINGS, 'orbited_host': config.ORBITED_HOST, 'orbited_port': config.ORBITED_PORT})
ajax_render = web.template.render('templates/')

# our views
class Index:
    @checkaccess(auth=False)
    def GET(self):
        data = web.input()
        error = data.get('error', None)
        message = data.get('message', None)
        return render.index(error = error, message = message)

class Login:
    def GET(self):
        if logged():
            raise web.seeother('/')
            
        return render.login(error = False)
        
    def POST(self):
        username, password = web.input().username, web.input().password
        ident = db.select('users', where='username=$username and password=PASSWORD($password)', vars=locals())
        if ident:
            r = ident[0]
            session.login = 1
            session.username = username
            session.permission = r['permission']
            db.update('users', where='id=$id', vars=r, last_login=datetime.datetime.now())
            log('login',username)
            raise web.seeother('/')
        else:
            session.login = 0
            session.permission = 0
            return render.login(error = True)
class Logout:
    @checkaccess(auth=False)
    def GET(self):
        log('logout',session.username)
        session.username = None
        session.login = 0
        session.permission = 0
        
        raise web.seeother('/login/')
        
class Internal:
    def POST(self):
        return web.badrequest()
    
    @checkaccess(auth=True, level = 1)
    def GET(self):
        data = web.input()
        mapping_name = data.get('mapping_name', None)
        mapping_n = data.get('n', 5)
        if not mapping_name or mapping_name not in config.MAPPINGS:
            return web.notfound()
        
        local_mapping = orimono.internal.get_mapping(mapping_name)
        
        mapping_changes = orimono.internal.get_changes(mapping_name, mapping_n)
        branch = orimono.internal.get_branch(mapping_name)
        available_branches = orimono.internal.get_branches()
        return render.internal(mapping_name = mapping_name, mapping_changes = mapping_changes, branch=branch, local_mapping = local_mapping, available_branches = available_branches)
            
        
class InternalUpdate:
    def GET(self):
        return web.badrequest()
        
    @checkaccess(auth=True, level=2)
    def POST(self):
        data = web.input()
        mapping_name = data.get('mapping_name', None)
        if not mapping_name or mapping_name not in config.MAPPINGS:
            return web.notfound()
            
        version = orimono.internal.update(mapping_name)
        content = ajax_render.completed(message = '%s has been updated to %s' % (mapping_name, version))
        web.header('Content-Type', 'application/json')
        return json.dumps({'version': version, 'mapping_name': mapping_name, 'datetime':unicode(datetime.datetime.now()), 'content': unicode(content)})

class InternalRestartPresence:
    def GET(self):
        return web.badrequest()
        
    @checkaccess(auth=True, level=2)
    def POST(self):
        data = web.input()
        mapping_name = data.get('mapping_name', None)
        if not mapping_name or mapping_name not in config.MAPPINGS:
            return web.notfound()
            
        restarted = orimono.internal.restart_presence(mapping_name)
        web.header('Content-Type', 'application/json')
        content = ajax_render.completed(message = '%s presence has been restarted' % (mapping_name))
        return json.dumps({'content': unicode(content)})
        
        
class InternalChangeMapping:
    def GET(self):
        return web.badrequest()
        
    @checkaccess(auth = True, level = 2)
    def POST(self):
        data = web.input()
        mapping_name = data.get('mapping_name', None)
        new_branch = data.get('new_branch', None)
        if not mapping_name or not new_branch or mapping_name not in config.MAPPINGS:
            return web.notfound()
        
        version = orimono.internal.change_local_mapping(mapping_name, new_branch)
        content = ajax_render.completed(message = '%s has been changed to %s (changelist %s)' % (mapping_name, new_branch, version))
        branch_details = ajax_render.branch_details(branch = orimono.internal.get_branch(mapping_name), mapping_changes = orimono.internal.get_changes(mapping_name, 5))
        web.header('Content-Type', 'application/json')
        return json.dumps({'version': version, 'mapping_name': mapping_name, 'datetime': unicode(datetime.datetime.now()), 'content': unicode(content), 'branch_details': unicode(branch_details)})
        
      
class External:
    def POST(self):
        return web.badrequest()
    
    @checkaccess(auth=True, level = 1)
    def GET(self):
        data = web.input()
        mapping_name = data.get('mapping_name', None)
        mapping_n = data.get('n', 5)
        if not mapping_name or mapping_name not in  [ m['site'] for m in config.EXTERNAL_MAPPINGS]:
            return web.notfound()
        
        external_mapping = orimono.external.get_mapping(mapping_name)
        mapping_changes = orimono.external.get_changes(mapping_name, mapping_n)
        branch = external_mapping['branch']
        
        return render.external(mapping_name = mapping_name, mapping_changes = mapping_changes, branch=branch, external_mapping = external_mapping)
        
class ExternalRestartPresence:
    def GET(self):
        return web.badrequest()
        
    @checkaccess(auth=True, level=2)
    def POST(self):
        data = web.input()
        mapping_name = data.get('mapping_name', None)
        if not mapping_name or mapping_name not in  [ m['site'] for m in config.EXTERNAL_MAPPINGS]:
            return web.notfound()
            
        restarted = orimono.external.restart_presence(mapping_name)
        web.header('Content-Type', 'application/json')
        content = ajax_render.completed(message = '%s presence has been restarted' % (mapping_name))
        return json.dumps({'content': unicode(content)})
        
class ExternalDeployInternal:
    def GET(self):
        return web.badrequest()
        
    @checkaccess(auth=True, level=2)
    def POST(self):
        
        data = web.input()
        mapping_name = data.get('mapping_name', None)
        if not mapping_name or mapping_name not in  [ m['site'] for m in config.EXTERNAL_MAPPINGS]:
            return web.notfound()
        
        deploy_mapping = data.get('deploy_mapping', None)
        if not deploy_mapping or deploy_mapping not in config.MAPPINGS:
            return web.notfound()
          
        include_content = True if data.get('include_content', None) == 'true' else False    
        updated_mapping = orimono.external.deploy_from_local(deploy_mapping, mapping_name, include_content =include_content )
        content = ajax_render.completed(message = '%s has been deployed to %s -- now at %s (%s)' % (deploy_mapping, updated_mapping['site'],updated_mapping['branch'], updated_mapping['changelist']))
        branch_details = ajax_render.branch_details(branch = updated_mapping['branch'], mapping_changes = orimono.external.get_changes(mapping_name, 5))
        web.header('Content-Type', 'application/json')
        return json.dumps({'version': updated_mapping['changelist'], 'mapping_name': mapping_name, 'datetime':unicode(datetime.datetime.now()), 'branch_details': unicode(branch_details), 'content': unicode(content)})


class ExternalDeployExternal:
    def GET(self):
        return web.badrequest()
        
    @checkaccess(auth=True, level=2)
    def POST(self):
        data = web.input()
        from_mapping_name = data.get('from_mapping_name', None)
        if not from_mapping_name or from_mapping_name not in  [ m['site'] for m in config.EXTERNAL_MAPPINGS]:
            return web.notfound()
        
        to_mapping_name = data.get('to_mapping_name', None)
        if not to_mapping_name or to_mapping_name not in  [ m['site'] for m in config.EXTERNAL_MAPPINGS]:
            return web.notfound()
            
            
            
        updated_mapping = orimono.external.deploy_from_external(from_mapping_name, to_mapping_name)
        content = ajax_render.completed(message = '%s has been deployed to %s -- now at %s (%s)' % (to_mapping_name, updated_mapping['site'],updated_mapping['branch'], updated_mapping['changelist']))
        branch_details = ajax_render.branch_details(branch = updated_mapping['branch'], mapping_changes = orimono.external.get_changes(mapping_name, 5))
        web.header('Content-Type', 'application/json')
        return json.dumps({'version': updated_mapping['changelist'], 'mapping_name': updated_mapping['site'], 'datetime':unicode(datetime.datetime.now()), 'branch_details': unicode(branch_details), 'content': unicode(content)})


        
class AdminPopulateMappings:
    '''
    often a site mapping will not have the latest version of the code for that branch
    in order to track up-to-what changelist of a branch a mapping has, we update the 
    mappings table with changelist number and timestamp. this code should only be run once
    when setting up the app, as it updates all local mappings. external mappings will need 
    to be manually populated in the db.
    
    '''
    @checkaccess(auth=True, level = 2)
    def GET(self):
        existing_mappings = {}
        mappings = db.select('mappings')
        for m in mappings:
            existing_mappings[m['site']] = {'id': m['id'], 'datetime': m['datetime'], 'changelist': m['changelist']}
            
        for m in config.MAPPINGS:
            if m not in existing_mappings:
                existing_mappings[m] = {'id':None}
                
            # update local mapping so we can get the changelist number
            existing_mappings[m]['changelist'] = orimono.internal.update(m)
            existing_mappings[m]['branch'] = orimono.internal.get_branch(m)
            
                
        for n,d in existing_mappings.iteritems():
            if d['id']:
                db.update('mappings',where="id=$id", vars=d, datetime=datetime.datetime.now(), changelist = d['changelist'], branch = d['branch'])
            else:
                db.insert('mappings', datetime = datetime.datetime.now(), site = n, changelist = d['changelist'], branch = d['branch'])
                
        return web.seeother('/?message=Updated%20Mappings%20DB')
    
    def POST(self):
        pass
            
       
class AdminUpdateInternal:
    @checkadmin()
    def GET(self):
        existing_mappings = {}
        for m in config.MAPPINGS:
            existing_mappings[m] = orimono.internal.get_mapping(m)
            existing_mappings[m]['changelist'] = orimono.internal.update(m)
            existing_mappings[m]['branch'] = orimono.internal.get_branch(m)
          
        for n,d in existing_mappings.iteritems():
            if d['id']:
                db.update('mappings',where="id=$id", vars=d, datetime=datetime.datetime.now(), changelist = d['changelist'], branch = d['branch'])
            else:
                db.insert('mappings', datetime = datetime.datetime.now(), site = n, changelist = d['changelist'], branch = d['branch'])
        
        return True
