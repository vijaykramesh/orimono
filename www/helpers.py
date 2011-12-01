import os
import config

# some helper functions
def get_mapping_root(name):
    return os.path.join(config.MAPPING_ROOT, name)
    
def get_mapping_site(name):
    return os.path.join(config.MAPPING_ROOT, name, 'application')
    
def get_mapping_application(name):
    return os.path.join(config.MAPPING_ROOT, name, 'application','uzume')

def get_branch_path(name):
    if os.path.isdir(os.path.join(config.BRANCH_ROOT, name)):
        return os.path.join(config.BRANCH_ROOT, name)
    elif os.path.isdir(os.path.join(config.BRANCH_ROOT, 'snapshots', name)):
        return os.path.join(config.BRANCH_ROOT, 'snapshots', name)
    else:
        raise Exception('Unknown branch %s' % name)
        
def _get_external(name,key):
    for m in config.EXTERNAL_MAPPINGS:
        if m['site'] == name:
            v = m.get(key, None)
            if not v: raise Exception('Unknown key %s' % key)
            return v
    raise Exception('Unknown mapping %s' % name)
        
def get_http_host(name):
    return _get_external(name, 'http')
    
def get_presence_host(name):
    return _get_external(name, 'presence')
    
def get_db_host(name):
    return _get_external(name, 'db')
