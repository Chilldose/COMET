# This files handles socket connections for various tasks, like talking to a django server etc.

import socket
import threading
import logging
import queue
import selectors, types, json, io, sys, struct, traceback

class socket_connections(threading.Thread):

    def __init__(self, HOST='127.0.0.1', PORT=65432):
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

    def __init__(self, HOST='127.0.0.1', PORT=65432):
        super().__init__(HOST, PORT)
        self.log.info("Initialized client at {}:{}".format(self.HOST, self.PORT))
        self.request = None

    def send_request(self, action, value):
        """This function creates a request and sends it to the server
        This function can be called as often as you want"""
        self.request = self.create_request(action, value)
        return self.run() # Do not start a thread here, otherwise you will not get the output!

    def create_request(self, action, value):
        """This function creates a request """
        if action:
            return dict(
                type="text/json",
                encoding="utf-8",
                content=dict(action=action, value=value),
            )
        else:
            return dict(
                type="binary/custom-client-binary-type",
                encoding="binary",
                content=bytes(action + value, encoding="utf-8"),
            )

    def start_connection(self, host, port, request):
        addr = (host, int(port))
        self.log.debug("starting connection to"+str(addr))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(addr)  # Starts the connection
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        message = MessageClient(self.sel, sock, addr, request)
        self.sel.register(sock, events,
                     data=message)  # Sock should be monitored for read or write actions, and message is the object to do something with it

    def run(self):
        #request = self.create_request(action, value)
        if self.request:
            self.start_connection(self.HOST, self.PORT, self.request)
            try:
                while True:
                    events = self.sel.select(timeout=1)  # Select the socket
                    for key, mask in events:  # Key, mask gives you the sockets which are ready to read/write, mask gives you which thing is ready, read or write e.g.
                        message = key.data  # gives me my message class instance, previously passed to sel.register
                        try:
                            message.process_events(mask)
                        except Exception:
                            self.log.error("main: error: exception for }:{}".format(message.addr, traceback.format_exc()))
                            message.close()
                    # Check for a socket being monitored to continue.
                    if not self.sel.get_map():
                        break
            except KeyboardInterrupt:
                self.log.critical("caught keyboard interrupt, exiting")
            finally:
                #self.sel.close()
                self.request = None
                try:
                    return message.response
                except:
                    pass
        else:
            self.log.error("No valid request placed. No data sent!")



class Server_(socket_connections):
    """Handles a Server connection"""

    def __init__(self, responder_funct=None, HOST='127.0.0.1', PORT=65432):
        """This class has a responder member, define a function which should be called if a connection is established
        with the server. This function must return a valid python object. Which is then send to the Client"""
        super().__init__(HOST, PORT)
        self.keep_running = False
        self.responder = responder_funct

    def start_connection(self):

        addr = (self.HOST, self.PORT)
        self.log.debug("starting server at {}".format(addr))
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind(addr)
        lsock.listen()
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)


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
        self.log.debug("accepted connection from"+str(addr))
        conn.setblocking(False)
        message = MessageServer(self.sel, conn, addr, responder_funct=self.responder)
        self.sel.register(conn, selectors.EVENT_READ, data=message)

    def run(self):
        self.start_connection()
        try:
            while True:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        message = key.data
                        try:
                            message.process_events(mask)
                        except Exception:
                            self.log.error("main: error: exception for {}:{}".format(message.addr,traceback.format_exc()))
                            message.close()
                    # Check for a socket being monitored to continue.
                    #if not self.sel.get_map():
                    #    break

        except KeyboardInterrupt:
            self.log.critical("caught keyboard interrupt, exiting")
        finally:
            self.sel.close()

class BaseMessage:
    """Generate a Message Class for the client/server"""

    def __init__(self, selector, sock, addr, request=None):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.request = request
        self._recv_buffer = b""
        self._send_buffer = b""
        self._request_queued = False
        self._jsonheader_len = None
        self.jsonheader = None
        self.response = None
        self.response_created = False
        self.responder_funct = None # The function which respond to a request, only needed for the server

        self.log = logging.getLogger(__name__)

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError("Invalid events mask mode {}.".format(mode))
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        """Reads from the socket and adds the response to the recived buffer"""
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")

    def _write(self):
        """Checks if the send buffer contains data and sends the data over the socket"""
        if self._send_buffer:
            self.log.debug("sending " + str(repr(self._send_buffer)) + "to" + str(self.addr))
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                # Close when the buffer is drained. The response has been sent.
                if sent and not self._send_buffer:
                    self.close()

    def _json_encode(self, obj, encoding):
        """Simply encodes a python dictionary to a json encoded message to be send over a socket connection"""
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        """Simply decodes a json encoded message to a python dictionary"""
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _create_message(
        self, *_, content_bytes, content_type, content_encoding
    ):
        """Creates the structure header of a message, to be send over a socket
        It contains the byte order of your system, the content type e.g. text/json
        and the content encoding e.g. utf-8 and the length of the message in byte"""
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes)) # Unsign short, for the len of the message header
        message = message_hdr + jsonheader_bytes + content_bytes # Constructing a message encoded in bytes
        return message

    def process_events(self, mask):
        """Looks if mask state is either read or write and, then executes read or write """
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        """Dummy read function which does nothing, needs to be overwritten by client or server function"""
        self.log.error("You used the the standard read function which does nothing. Please overwrite!")

    def write(self):
        """Dummy read function which does nothing, needs to be overwritten by client or server function"""
        self.log.error("You used the the standard write function which does nothing. Please overwrite!")

    def close(self):
        """Closes the connection to the socket by unregistering it from the selector
        so it does not listen anymore and then closes the connection on the socket"""
        self.log.debug("closing connection to"+str(self.addr))
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            self.log.error("error: selector.unregister() exception for".format(self.addr, e))

        try:
            self.sock.close()
        except OSError as e:
            self.log.error("error: socket.close() exception for".format(self.addr, e))
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

    def process_protoheader(self):
        """The protoheader consists of two bytes prepended to every message
        Its an unsign integer containing the length of the message header."""
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._jsonheader_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_jsonheader(self):
        """Processes the json header it needs the header length already known"""
        hdrlen = self._jsonheader_len
        if len(self._recv_buffer) >= hdrlen: # Only process if the header is already fully there
            self.jsonheader = self._json_decode(
                self._recv_buffer[:hdrlen], "utf-8"
            )
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-type",
                "content-encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError('Missing required header "{}".'.format(reqhdr))


class MessageServer(BaseMessage):
    """Basic Message class for server messages"""

    def __init__(self, selector, sock, addr, request=None, responder_funct=None):
        super(MessageServer, self).__init__(selector, sock, addr, request=None)
        self.responder_funct = responder_funct

    def _create_response_json_content(self):
        """Here the """
        action = self.request.get("action", None)
        value = self.request.get("value", None)
        if action and value:
            answer = self.responder_funct(action, value)
            content = {"result": answer}
        else:
            content = {"result": 'Error: invalid action and or value {}, {}'.format(action, value)}
        content_encoding = "utf-8"
        response = {
            "content_bytes": self._json_encode(content, content_encoding),
            "content_type": "text/json",
            "content_encoding": content_encoding,
        }
        return response

    def _create_response_binary_content(self):
        response = {
            "content_bytes": b"First 10 bytes of request: "
            + self.request[:10],
            "content_type": "binary/custom-server-binary-type",
            "content_encoding": "binary",
        }
        return response

    def read(self):
        self._read()

        if self._jsonheader_len is None:
            self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.request is None:
                self.process_request()


    def write(self):
        if self.request:
            if not self.response_created:
                self.create_response()

        self._write()

    def process_request(self):
        content_len = self.jsonheader["content-length"]
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        if self.jsonheader["content-type"] == "text/json":
            encoding = self.jsonheader["content-encoding"]
            self.request = self._json_decode(data, encoding)
            self.log.debug('received {} request from {}'.format(self.jsonheader["content-type"], self.addr))
        else:
            # Binary or unknown content-type
            self.request = data
            self.log.debug('received {} request from {}'.format(self.jsonheader["content-type"], self.addr))
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")


    def create_response(self):
        if self.jsonheader["content-type"] == "text/json":
            response = self._create_response_json_content()
        else:
            # Binary or unknown content-type
            response = self._create_response_binary_content()
        message = self._create_message(**response)
        self.response_created = True
        self._send_buffer += message

class MessageClient(BaseMessage):
    """Basic Message class for client messages"""

    def __init__(self, selector, sock, addr, request):
        super(MessageClient, self).__init__(selector, sock, addr, request=request)

    def _process_response_json_content(self):
        """Write back the content of the response if json format"""
        content = self.response
        result = content.get("result")
        self.log.debug("got result: {}".format(result))

    def _process_response_binary_content(self):
        content = self.response
        self.log.debug("got response: {}".format(content))

    def read(self):
        """Reads from the socket.
        If previous a part of the message arrived several things can happen.
        No jsonhead_len available, it tries to decode it
        If jsonheader_len and jasonheader is not available, decode jsonheader
        if the jsonheader is decoded and no response is yet made process the response and act accordingly

        If the message is recieved completely all these thins will happen after another"""
        self._read()

        if self._jsonheader_len is None:
            self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.response is None:
                self.process_response()

    def write(self):
        """Looks if a request is already queued if not it queues it.
        It then writes the message on the socket
        Finally if the request is queued and the message was send the selector goes into read mode, to recieve data"""
        if not self._request_queued:
            self.queue_request()

        self._write()

        if self._request_queued:
            if not self._send_buffer:
                # Set selector to listen for read events, we're done writing.
                self._set_selector_events_mask("r")

    def queue_request(self):
        """Queues a request by encoding the message and gather statistics to it like type and encoding
        It also creates a byte message ready to send and stores it in the send buffer"""
        content = self.request["content"]
        content_type = self.request["type"]
        content_encoding = self.request["encoding"]
        if content_type == "text/json":
            req = {
                "content_bytes": self._json_encode(content, content_encoding),
                "content_type": content_type,
                "content_encoding": content_encoding,
            }
        else:
            req = {
                "content_bytes": content,
                "content_type": content_type,
                "content_encoding": content_encoding,
            }
        message = self._create_message(**req)
        self._send_buffer += message
        self._request_queued = True

    def process_response(self):
        """Processes the actual message"""
        content_len = self.jsonheader["content-length"]
        if not len(self._recv_buffer) >= content_len: # Checks if message was recieved
            return
        data = self._recv_buffer[:content_len] # If garbage data is extended discard it
        self._recv_buffer = self._recv_buffer[content_len:]
        if self.jsonheader["content-type"] == "text/json":
            encoding = self.jsonheader["content-encoding"]
            self.response = self._json_decode(data, encoding)
            self.log.debug('received {} request from {}'.format(self.jsonheader["content-type"], self.addr))
            self._process_response_json_content()
        else:
            # Binary or unknown content-type
            self.response = data
            self.log.debug('received {} request from {}'.format(self.jsonheader["content-type"], self.addr))
            self._process_response_binary_content()
        # Close when response has been processed
        self.close()

if __name__ == "__main__":

    def func(a,b):
        return "Recieved: {}, {}".format(a,b)

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug('This is a log message.')
    server = Server_(responder_funct = func)
    server.run()