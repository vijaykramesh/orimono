import config
import eventlet
from eventlet.green import socket
import simplejson as json

participants = set()


def read_chat_forever(writer, reader):
    line = reader.readline()
    # writer.write("%s\r\n" % 1)
    writer.flush()
    while line:
        # to prevent, e.g., Orbited connection messages from trying to be sent through
        # we have a simple scheme - a message must start with MESSAGE: followed by a JSON
        # parseable string
        if not line.startswith('MESSAGE:'):
            line = reader.readline()
            continue
        message = json.loads(line[8:])
        for p in participants:
            try:
                if p is not writer: # Don't echo
                    p.write(json.dumps(message))
                    p.flush()
            except socket.error, e:
                # ignore broken pipes, they just mean the participant
                # closed its connection already
                if e[0] != 32:
                    raise
        line = reader.readline()
    participants.remove(writer)

try:
    print "Orimono Comet starting up on port %s" % config.COMET_PORT
    server = eventlet.listen((config.COMET_HOST, config.COMET_PORT))
    while True:
        new_connection, address = server.accept()
        new_writer = new_connection.makefile('w')
        participants.add(new_writer)
        
        eventlet.spawn_n(read_chat_forever, 
                         new_writer, 
                         new_connection.makefile('r'))
except (KeyboardInterrupt, SystemExit):
    print "Orimono Comet exiting."

