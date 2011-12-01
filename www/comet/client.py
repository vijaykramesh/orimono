import config
import eventlet
import simplejson as json

'''
A simple eventlet client to push messages to our comet server
'''

def send(status, message):
    sock = eventlet.connect((config.COMET_HOST,int(config.COMET_PORT)))
    msg = {'type':'log','message':message,'status':status}
    sock.send('MESSAGE:%s' % json.dumps(msg))
    return
