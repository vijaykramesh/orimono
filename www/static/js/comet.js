// this is the comet client that connects to our eventlet server

// where orbited is running
 SERVER_HOST = 'orimono.internal.com';
 SERVER_PORT = '8080';
// 
// where the eventlet server is running
 TARGET_HOST = 'orimono.internal.com';
 TARGET_PORT = '5992';


var CometQueue = function(){
    var self = this;
    self.queue = [];
    self.processing = false;
    
    self.push = function(to_push){
	self.queue.push(to_push);
	self.process();
    };

    self.process = function(){
	if (self.processing == false){
	    self.processing = true;
	    to_process = self.queue[0];
	    try{
		return_status = Comet.process(to_process);
	    }catch(e){
		    console.log("CometQueue Error: " + e.name + ' -- ' + e.message); 
	    }
	    if (return_status['status'] == false) console.log('CometQueue failed to process message: ' + to_process);
	    if (return_status['status'] == true || (return_status['status'] == false && return_status['shift_on_errors'] == true)) self.queue.shift();
	    self.processing = false;
	    if (self.queue.length > 0) self.process();
	}
    };
};

CometClient = function() {
    var self = this
    var conn = null
    var buffer = ""
    
    // Public callbacks
    self.onopen = function() {}
    self.onmessage = function() {}
    self.onclose = function(code) {}
    
    
    // Public methods: connect, nick, ident, names, join, quit
    self.connect = function(host, port) {
        conn = new self.transport();
        // Set socket callbacks
        conn.onread = read
        conn.onclose = close
        conn.onopen = open
        conn.open(host, port);
    }
    self.close = function() {
        conn.close()
    }
    self.send = function(s) {
        send(s)
    }
    
    
    // Socket functions: send, read, open, and close
    var send = function(s) {
        // If we were going to use UTF8ToBytes, this would be the place
        conn.send(s)
    }
    var read = function(s) {
        buffer += s
        parse_buffer()
    }
    var open = function() {
        self.onopen()
    }
    var close = function(code) {
        self.onclose(code)
    }
    var onopen = function(){
	Comet.connected(true);
    }
    self.onmessage = function(m){
	Comet.receive(m);
    }
    self.comet_send = function(m){
	self.send('MESSAGE:' + JSON.stringify(m));
    };
    // Message parsing and dispatching
    var parse_buffer = function() {
        var msgs = buffer.split("\n")
        buffer = ""

        // Dispatch any lines in the buffer
        for (var i=0; i< msgs.length; i++)
            dispatch(msgs[i])
    }
    var dispatch = function(msg) {
        self.onmessage(msg)
    }
}

CometClient.prototype.transport = Orbited.TCPSocket


var Comet = function(){
    
    var queue = new CometQueue();
    var client = null;

    // internal state
    var connected = false;
   
    // Constructor
    var init = function(){
		
	// create comet connection applet (via Orbited)
	if (!client) client = new CometClient();
	
	// connect to the comet server
	if (client && connected == false) client.connect(TARGET_HOST,TARGET_PORT);
	

    };
    
    
    // message routing -- 
    // after Comet.client.receive_packet receives a message
    // Comet.receive determines what to do with it
    var receive = function(m){
	m = JSON.parse(m);
	if (m.error != null){
	    console.log('Comet service error');
	}else if (m.type){
	    queue.push(m);
	}else{
	    console.error('Comet packet type not present');
	}
    };
    
    var process = function(m){
	
	var return_status = {'shift_on_errors': true, 'status': true };
	switch (m.type){
	    case 'log':
		append_log(m['message'], m['status']);
		break;
		
	    default:
		console.log('Comet packet type unknown');
		return_status['status'] = false;
		break;
	}
	
	return return_status;				
    };
	
    var append_log = function(msg, status){
	var log_template = '<div class="alert-message %status%"><a class="close" href="#">×</a>%msg%</p></div>'
	var $log = $(log_template.replace('%status%', status).replace('%msg%',msg));
	$('#action_messages').append($log);
	$log.show().alert();
    };
    
    var send = function(m){
	return client.comet_send(m);
    };
    
    var onclose = function(){    
	connected = false;
    };
    
    $(document).ready(init);
    
    
    // public API
    var api = {};
    
    // attributes
    api.connected = function(v){ if (v){ connected = v; } return connected; };
    
    // functions
    api.init = init;
    api.receive = receive;
    api.send = send;
    api.process = process;
    api.onclose = onclose;
    return api;
	
    
}();

