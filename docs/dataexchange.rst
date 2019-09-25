Data Exchange
=============

In this section the basic data exchange mechanisms will be explained COMET uses to exchange data between the GUI and the
measurement thread, as well the exchange of data between measurement devices.

Framework Data Exchange
~~~~~~~~~~~~~~~~~~~~~~~

Since you have learned that COMET uses several threads and event loops to work, a save way for data exchange has to be installed
to ensure thread save operations of the software.
Therefore, I have established several FIFO Queue objects you can use to exchange data from the GUI threads to the measuerment
threads.

These queue objects are:

    * Message_to_main
    * Message_from_main

and they can be accessed by the :ref:`Framework variables` object, your measurement plugin has access to.

**Message_to_main:**
is for sending data to the GUI event loop (or the Main program). Like with all messages in COMET the
message send over this queue must be a python dict object. Key being the message type and the value, the value this key should represent.
The GUI understands the following message types:

    :Errors: "Critical", "Info","MeasError", "DataError", "RequestError", "MEASUREMENT_FAILED", "Warning", "FatalError", "ThresholdError", "ERROR", "Error"

    :Measurements: All measurements keys you have defined in your project settings file under the key ``measurement_types``

    :Events: "MEASUREMENT_STATUS", "MEASUREMENT_FINISHED", "CLOSE_PROGRAM", "ABORT_MEASUREMENT", "START_MEASUREMENT", "MEASUREMENT_EVENT_LOOP_STOPED"

As a User you only have to concern about the first to message types, so Errors and Measurements.

**Error** messages always looks like ``{"Info": "Some info you want to tell the GUI"}``. So the key is the error type
and the value is a string.

.. important:: It has always to be a string the value! But it is not important what is inside this string, this is up to the user!

This message is then written to the member variable of the GUI event loop ``error_log``, which the user can use to display the errors inside the GUI.
Other actions will not be taken by the framework with this kind of messages.

.. hint:: The message types are furthermore color coded. All errors are red, infos are green and warnings etc. are orange.

**Measurements** types have the same structure as the error types. The difference being, that the key must be a valid name you specified in your settings
under the key ``measurement_types``. Otherwise COMET will discard this event. The value of this message must always be a list of np.arrays or single values.
So an example message would be: ``{"IV": [np.array[], np.array[]]}`` these arrays will be appended to the existing data array for measurement data storage.
Which is in turn a np.array object.

.. important:: You do not have to send single value arrays over this queue. If you send a longer array of data, it will be appended via the numpy function np.append(measurement_array, yourarray).

**Events** are message types which are only used by core features of COMET and the user should never meddle with it. It can compromise the
stability of COMET. But if you really want to know. These messages are only flag messages so a message would look like:
``{"CLOSE_PROGRAM": True}`` which will shut down the program.

.. tip:: This "CLOSE_PROGRAM" message is with "ABORT_MEASUREMENT" the only messages you as user should use.


**Message_from_main:**
This queue is for sending data to the measurement event loop. Like with all messages in COMET the
message send over this queue must be a python dict object. Key being the message type and the value, the value this key should represent.
The event loop understands the following message types:

    :Status: "CLOSE", "MEASUREMENT_FINISHED", "MEASUREMENT_STATUS", "ABORT_MEASUREMENT"

    :Measurements: "Measurement", "Status", "Remeasure", "Alignment", "Sweep"

**Status:**
These type of messages are message types which are only used by core features of COMET These messages are only flag messages so a message would look like:
``{"ABORT_MEASUREMENT": True}`` which will end the measurement.

**Measurements:**
These are messages concerning the starting of a measurement plugin status and so on. To generate a measurement job please
see the dedicated chapter :ref:`Measurement Job Generation`.

.. warning:: "Remeasure", "Alignment", "Sweep" are deprecated messages, which will be deleted in future releases.

Device Data Exchange
~~~~~~~~~~~~~~~~~~~~

COMET uses the pyVisa module to exchange data with all kinds of measurement devices. This module is based on the
National Instruments VISA driver, and therefore needs its dependencies to work.

.. note:: There is a pyvisa-py module which is not dependent on the NI-Visa drivers, but its not as stable as the NI variant.

To advantage of this driver is, that it abstracts the device connection type to an easy usable interface. Basically, if
you have established a connection to a device, be it RS232, GPIB, TCP/IP or USB you do not need to concern yourself with
the details of this connection. All devices uses the same functions for reading and writing and the drivers does the correct
adjustments.

For further abstraction I have written a module which is a wrapper around pyvisa and makes thinks even more easy for you.
It is called the :ref:`VCW - Visa Connect Wizard`. In it are some tools you can use to connect to devices. It features a more
sophisticated error handling and automatic reconnection if a devices somehow loses the connection to the computer.

An instance of a VCW with all connected devices is supplied by the :ref:`Framework variables` object all your measurement plugins
get passed. You can access the VCW instance by the key ``VCW``.

The member ``VCW.myInstruments`` gives you a dict of all connected devices, the key being the VISA resource name and the key the actual resource.

The most important functions for a user are the ``read``, ``write`` and ``query`` function, with them you can directly send a command
to a device. But you most likely want to use a toolbox function for that, because it will build a correct command the device will understand.
If you encounter a command which is not coped by the device command set, then you can use this commands, otherwise I would recommend
to use a toolbox function.

In the Code Reference section under :ref:`VCW - Visa Connect Wizard` you find all member functions you can use with the VCW.