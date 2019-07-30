# This files handles socket connections for various tasks, like talking to a django server etc.

import socket
import threading
import logging
import queue

class socket_connections(threading.Thread):

    def __init__(self, HOST='127.0.0.10', PORT=65432):
        super().__init__()
        self.HOST = HOST  # Standard loopback interface address (localhost)
        self.PORT = PORT  # Port to listen on (non-privileged ports are > 1023)
        self.log = logging.getLogger(__name__)
        self.message_queue = queue.Queue()

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
            # Connect to the socket
            s.connect((self.HOST, int(self.PORT)))
            s.sendall(self.enc_messsage)
            self.log.debug("Send data to server {}, message reads: {}".format(self.HOST, self.enc_messsage.decode()))
            #data = s.recv(1024)
        #print('Received', repr(data))

class Server_(socket_connections):
    """Handles a Server connection"""

    def __init__(self, HOST='127.0.0.10', PORT=65432):
        super().__init__(HOST, PORT)
        self.keep_running = False

    def close_server(self):
        """Closes the server if opened"""
        #Todo: IF the server is waiting for a connection, it does not check if it should run, it always needs one extra message to do the loop again anddo it right.
        self.keep_running = False

    def run(self):
        self.keep_running = True
        self.log.info("Starting server at {}:{}".format(self.HOST, self.PORT))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.HOST, int(self.PORT)))
            s.listen()
            while self.keep_running:
                try:
                    conn, addr = s.accept()
                    with conn:
                        self.log.debug('Connected by {}:{}'.format(str(addr[0]),addr[1]))
                        final_data = b""
                        while True:
                            data = conn.recv(1024)
                            final_data += data
                            if not data:
                                break
                    self.log.debug("Received data from Client {}, which send {} bytes. Message reads: {}".format(addr, len(final_data), final_data.decode()))
                    self.message_queue.put(final_data)# Puts the data on the queue
                    #self.log.debug(final_data.decode())
                except ConnectionResetError as ConErr:
                    self.log.critical(ConErr)

if __name__ == "__main__":
    server = Server_()
    server.run()