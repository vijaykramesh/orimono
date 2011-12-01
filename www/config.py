'''
settings for uzume orimono
'''
import web

DEBUG = True

SAPPER_IP = '10.8.1.12'
# app mappings
MAPPING_ROOT = '/home/httpd/mapping/'
BRANCH_ROOT = '/home/httpd/sites/uzume/'

# list of local mappings we care about
MAPPINGS = (
    'dev.internal.com',
    'qa.internal.com'
)

# list of external servers & mappings
EXTERNAL_MAPPINGS = ( 
    {'site': 'qa.external.com', 'http': 'qa.external.com', 'db': 'db.qa.external.com', 'presence': 'presence.qa.external.com'},
    {'site': 'live.external.com', 'http': 'live.external.com', 'db': 'db.live.external.com', 'presence': 'presence.live.external.com' }
)

# share map across external servers
SAN_SHARE = '/mnt/san/siti2-live/sites/uzume/'
PASSWORDS = { 'qa.external.com': 'SUDOPASS', 'db.qa.exernal.com': 'SUDOPASS', 'presence.qa.external.com': 'SUDOPASS' }
    

PACKAGE_PATH = '/home/uzume/packages'

# shell env for fabric
P4_USER = 'web'

SHELL_ENV = {
    'P4PORT': 'P4_SERVER:1666',
    'P4CLIENT': 'FOOBAR',
    'P4HOST': 'foobar',
    'P4USER': 'foobar''
}


    
# db connection
DB_USER = 'foobar'
DB_PASSWORD = 'foobar'
DB_DATABASE = 'orimono'


# orbited
ORBITED_HOST = 'orimono.internal.com'
ORBITED_PORT = 8080 

COMET_HOST = 'orimono.internal.com'
COMET_PORT = 5992
