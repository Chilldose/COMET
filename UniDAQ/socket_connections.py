# This files handles socket connections for various tasks, like talking to a django server etc.

import socket
import threading
import logging
import queue
import selectors, types

class socket_connections(threading.Thread):

    def __init__(self, HOST='127.0.0.10', PORT=65432):
        super().__init__()
        self.HOST = HOST  # Standard loopback interface address (localhost)
        self.PORT = PORT  # Port to listen on (non-privileged ports are > 1023)
        self.log = logging.getLogger(__name__)
        self.message_queue = queue.Queue()
        self.sel = selectors.DefaultSelector()
        self.num_conns = 10 # Maximum number of simultaneous connections

        # Connection type
        self.protocol = socket.SOCK_STREAM
        self.type_ = socket.AF_INET

        # Deamon thread
        self.daemon = True



class Client_(socket_connections):
    """Handles a Client connection"""

    def __init__(self, HOST='127.0.0.10', PORT=65432):
        super().__init__(HOST, PORT)
        self.log.info("Initialized client at {}:{}".format(self.HOST, self.PORT))

    def send_message(self, message):
        # Sends a specific message, by starting a new client connection to the server
        self.enc_messsage = str.encode(message)
        self.run()

    def run(self):
        # This only opens a connection and sends data to the server then closes the connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            for i in range(0, self.num_conns):
                connid = i + 1
                self.log.debug('Starting connection', connid, 'to', (self.HOST, self.PORT))
                s.setblocking(False)
                s.connect_ex((self.HOST, self.PORT))
                events = selectors.EVENT_READ | selectors.EVENT_WRITE
                data = types.SimpleNamespace(connid=connid,
                                             msg_total=sum(len(m) for m in self.enc_messsage),
                                             recv_total=0,
                                             messages=list(self.enc_messsage),
                                             outb=b'')
                self.sel.register(s, events, data=data)
            #self.log.debug("Send data to server {}, message reads: {}".format(self.HOST, self.enc_messsage.decode()))
            #data = s.recv(1024)
        #print('Received', repr(data))

class Server_(socket_connections):
    """Handles a Server connection"""

    def __init__(self, HOST='127.0.0.10', PORT=65432):
        super().__init__(HOST, PORT)
        self.keep_running = False

    def get_message(self):
        """Returns one messege for the message queue if the queue is not empty. None
        will be returned if no messages are present.
        If gives you no information how many more messages are in the queue"""

        if not self.message_queue.empty():
            message = self.message_queue.get()
            return message
        else:
            return None

    def close_server(self):
        """Closes the server if opened"""
        #Todo: IF the server is waiting for a connection, it does not check if it should run, it always needs one extra message to do the loop again anddo it right.
        self.keep_running = False

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        self.log.debug('Accepted connection from ', addr)
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b'', outb=b'')
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                data.outb += recv_data
            else:
                print('closing connection to', data.addr)
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            if data.outb:
                self.log.debug('echoing', repr(data.outb), 'to', data.addr)
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]

    def run(self):
        self.keep_running = True
        self.log.info("Starting server at {}:{}".format(self.HOST, self.PORT))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.HOST, int(self.PORT)))
            s.listen()
            s.setblocking(False) # So the program does not block
            self.sel.register(s, selectors.EVENT_READ, data = None)
            while self.keep_running:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        self.service_connection(key, mask)
                    #self.log.debug("Received data from Client {}, which send {} bytes. Message reads: {}".format(addr, len(final_data), final_data.decode()))
                    #self.message_queue.put(final_data)# Puts the data on the queue

if __name__ == "__main__":
    server = Server_()
    server.run()