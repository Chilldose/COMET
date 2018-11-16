Structure
=========

The Framework is based on a multi-thread python environment. Since python is generally not thread-safe and race conditions
are often a problem, several precautions have to be made to safely share data between the different threads. For more
information on how to share data see chapter :ref:`dataexchange`.


Main Structure
~~~~~~~~~~~~~~

The picture below shows the main flow-chart of the framework. I will now give a short summary what the program does during boot-up.

It starts by loading all modules required for running, by also checking the availability of the modules. If the module cannot
be found a message will be promped and a request will be made if it should be installed now.

.. warning:: A restart of the program may be needed, in order for them to work.

Furthermore it prompts every action it takes while loading, think of it like some kind of rudimentary log system. After
loading all modules the init files, like default values and device config files are loaded. Furthermore, the actual log-file will be initialized.
After all this is done the framework tries to connect to all devices it has config files for and stores the information the state machine.

Finally two threads are spawned, one beeing the GUI-Thread and one beeing the measurement event loop thread (see next section)

Concerning the GUI-Thread: Here a event loop is established which can take on messages from other parts of the program, e.g.
new data from a measurement or error messages or warnings.

Furthermore, it starts a additional framework functions to continuously update plots and/or GUI elements. This functionality
is provided by a NON-THREAD-SAVE state machine. This is necessary in order to not cripple the functionality or the speed of the program.
In order to not have race conditions, the rule in the GUI-Thread is:

.. caution:: Never change variables which do not directly belong to the GUI. Only access non member variables by read operations and check if the data is valid.

But **DO NOT PANIC** only a few variables are susceptible to race conditions (if you are using predefined work suits like the QTC-Software).
If you are using a blank project, like it is described in the :ref:`Tutorials` section. EVERYTHING is safe and you can use it as you please.

In order to stop the program you have to send the right signal to the GUI-event loop. This message reads as follows: ``{"Status": {"CLOSE": True}}``

.. warning:: If the close program message is send from ANYWHERE in the program the program shuts down! But if a measurement is running, the program waits until the measurement is either finished or aborted correctly, it will not kill it.

.. image:: pictures/Flowchart_QTC.png
   :alt: Flowchart_main
   :class: floatingflask


Measurement event loop
~~~~~~~~~~~~~~~~~~~~~~

The measurement event loop of the Framework is a core feature and is complex enough to justify a seperate chapter.

It first initializes all class instances like tools for measurements and supply functions like the queue objects for data
exchange. It furthermore initializes continous task, like the humidity and temperature control/surveillance. This continous tasks
can be extended as well.

After that a event loop is established which waits for incomming messages from other threads. If one such message arrives, e.g.
a new measurement job, then the framwork take actions accordingly to the flow chart below.
If a new measurement should be conducted, a new thread will be spawned which solely conducts the measurement and is seperated
from the rest of the framework, except for a stop action flag. This is due to code robustness. Imagine another part of the
code consumes a lot of resources and/or crashes. Since the measurement thread is handling devices this thread may never experience
lags or something like that.

.. note:: If a program bug is prevalent in the actual measurement routine this mechanism will not help. So be careful while programming the measurement routines!

Another type of message, which the framework can handle are, status update queries, these type of messages are not specific
and can be extended. After gatering the required data, the thread sends the data back to the main thread.

.. warning:: This mechanism was mainly used in the early development phases and is now marked as depricated. Status updates are now handled via thread-safe data structures, which does not need message based data exchange.

.. image:: pictures/Flowchart_QTC_measurement_event_loop.png
   :alt: Flowchart_meas_gen
   :class: floatingflask