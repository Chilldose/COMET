import sys
import selectors
import json
import io
import struct


class Message:
    """Generate a Message Class for the client"""
    def __init__(self, selector, sock, addr, request):
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

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError("Invalid events mask mode {repr(mode)}.")
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
            print("sending {} to {}".format(self._send_buffer, self.addr))
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]

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

    def _create_message(self, _, content_bytes, content_type, content_encoding):
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
####################
    def _process_response_json_content(self):
        """Write back the content of the response if json format"""
        content = self.response
        result = content.get("result")
        print("got result: {}".format(result))
########################
    def _process_response_binary_content(self):
        content = self.response
        print("got response: {}".format(content))

    def process_events(self, mask):
        """Looks if mask state is either read or write and, then executes read or write """
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()
    #####################
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
    ###############################
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

    def close(self):
        """Closes the connection to the socket by unregistering it from the selector
        so it does not listen anymore and then closes the connection on the socket"""
        print("closing connection to", self.addr)
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print("error: selector.unregister() exception for {}: {}".format(self.addr, e))

        try:
            self.sock.close()
        except OSError as e:
            print("error: socket.close() exception for {}: {}".format(self.addr, e))
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

    #################################
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

    #############################
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
            print("received response {} from {}".format(repr(self.response), self.addr))
            self._process_response_json_content()
        else:
            # Binary or unknown content-type
            self.response = data
            print('received {} response from {}'.format(self.jsonheader["content-type"],self.addr))
            self._process_response_binary_content()
        # Close when response has been processed
        self.close()