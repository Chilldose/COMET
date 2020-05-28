TCP/IP Server
=============

COMET supports a simple TCP/IP Server and Client app. Whit it JSON styled objects can
be transmitted to another TCP/IP Server or be received.

How to set up a Server and/or Client
------------------------------------

In order to set up a Server and/or Client you have to add the entry ``Socket_connection``
to you main config insider can be two entries the ``Host`` and/or the ``Client`` entry.

The ``Host`` must have the entries: ``IP`` and ``Port`` which designate the IP and the Host the server
should listen to.

The ``Client`` must have keys for the different clients you want to establish, insider
each of this clients the ``IP`` and ``Port`` entries like the server, (so the IP and Port it should send messages to)
must be present.


A possible configuration can look like: ::

  Socket_connection:

      Host:
        IP: 127.0.0.2
        Port: 65432

      Client:
        Telegram:
          IP: 127.0.0.4
          Port: 65432

How to receive a message
------------------------

Adding a handler for incoming messages is rather simple. The main GUI object, that what is passed
to every GUI plugin has a member function called ``.add_TCP_message_action_function``. Passing this
function a function object will add this object to the queue if messages arrive.

If a new message then arrives this function you passed will be given two parameters:
Firstly the action value: A some kind of flag, what this message is for. For example the telegram bot
inside COMET has the action "Telegram". You can use it to skim all messages for the correct ones.
The second value is an python object of type str or dict.

You can define a return value of your function if you like which must be a str serializable object,
which will be send to the client as acknowledgment/answer.


How to send a message
---------------------

Sending a message is a bit more complicated. To access a Client to send a message you have to navigate
to the framework variables, which are passed to every measurement and GUI plugin.
This is usually done via ``.client["Your_client_name"]``.

The you have to import the function ``send_TCP_message`` from the utilities module.
This function needs the client, the action name, and the actual message it should send.

Und this conditions the tcp connection handler will be run in a new thread to not
corrupt the program flow. This inhibits the possibility to access the answer from the server.
To get the answer you have to add the parameter ``no_thread=True`` to the parameters.
The communication will then run in the main thread and the answer can be recovered.
