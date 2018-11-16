Data Structure
==============

The data storage and state variables are stored in global accessible variables. This means they can (provided you follow
the rules provided in this doc) accessed from anywhere in the framework. Every user can add, delete or alter variables.
So be warned, do not meddle with variables you do not know! For the sake of dynamicallity of the software
it is necessary for the data structures to be not thread safe. This means every variable can be deprecated or out of date
after accessing it. Furthermore, fast writting and reading can lead to race conditions inside of the program, when
badly written.

An easy rule of thumb to avoid race conditions and unnecessary variables declarations are:

    * Do you really need this variable global accessible?
    * Only one subprogram can alter the value, all others just reads from it
    * Only binary states allowed for multi access variables
    * Non state critical variables for multi access variables

With these simple rules you should not have problems with this state machine.


Main Files
~~~~~~~~~~

The main data structure is the ``default_values_dict`` it contains at least one dictionary called *defaults*.
In this dictionary all data stored in the ``defaults.yml`` file are prevalent. Furthermore, additional parameters are created
which are not stored in the YAML file. These parameters are crucial parameters which are not part of a configuriation file,
since the have to be always be there or represent dumb variables. These variables can be extendend or reduced only in the
actual code (for now). In the ``boot_up.py`` under the function ``update_defaults_dict.to_update()`` these variables can be accessed.

.. note:: By placing more then one YAML file in the ``defaults`` folder, more dictionaries will be created in the ``default_values_dict``. But you have to create at least the item ``Settings_name: name of the setting`` entry. Otherwise the program does not know how to name these settings. These settings can then be accessed via the name.

Device Files
~~~~~~~~~~~~

Like with the main dicts, which are more of general settings and state files, the ``devices_dict`` is a more specialiced
dictionary. This main dict will be populated by the content of the ``devices`` folder. So every YAML file in there will
have a entry in the dictionary. The basic structure or minimal structure of such a file is as follows:

.. code-block:: python

        {
        "Device_name": "2410 Keithley SMU",
        "Device_type": "SMU",
        "Display_name": "SMU1",
        "Device_IDN": "KEITHLEY INSTRUMENTS INC.,MODEL 2410,0854671,C33   Mar 31 2015 09:32:39/A02  /J/H",

        "Output_ON": "OUTP ON",
        "imp:default_voltage_mode": "FIXED",
        "set_voltage_mode": "SOUR:VOLT:MODE ",
        "default_terminal": "REAR",
        "set_terminal": "ROUT:TERM",
        }

So to round this up: You need at least the first four parameters. From the fifth parameter onwards it is a order type.

Display name fehlt noch zum erklaren

Ordertypes
**********

The software is highly adaptable to input data and data structures for different codecs. To achieve this some parametes
have to be set to teach the program how to be so intelligent. First the program features a initialization routine when starting
the software or a measurement.

If you want to run a specific command on start up you have to prefix this command with ``default_`` after that the command is
of your liking. The value of this item is the actual ASCII code which defines the command for the device. Each ``default_``
value has to have a ``set_`` command (otherwise the default command will be send without parameter). So each ``default_``
and ``set_`` pair define a full command. If the program encounters such a pair during initialization it tries to build a command.
In our case such a command can be build out of ``"default_terminal": "REAR"`` and ``"set_terminal": "ROUT:TERM"``. In our case
this would result in the command: ``ROUT:TERM REAR``.

If it is necessary to send some order before some others, another prefix can be added, the ``imp:`` prefix. With this
the program is ordered to send these parameters before all others.

.. warning:: If more then one ``imp:`` parameter is defined, then these items will be send in a random order!

While using the program you will encounter the situation that you have to build your own commands with changing input.
This can be changing the bias voltage of a device etc. With the utility function ``build_command(device_dict, command_tuple):``
the program can help you generates the full ASCII coded command which the device should recognize.

This function is designed to only take a bare minimum of input and build a fully functional command out of it, without
you knowing the command structure of the device. Such a command can look like this:

.. code-block:: python

    helpfull_functions.build_command(devices_dict["SMU1"], ("set_voltage", 10))

This command then returns the string (for this demo case) ``SOUR:VOLT:LEV 10``.
The first parameter has to be the device which you want the command build for, the second parameter is a tuple, first
entry in this tuple beeing the key in the dictionary aka. the command and the second beeing the value you want it set to.

.. note:: This is only the simples usage of this function!!! A full list of the capabilities of this build function can be found in the dedicated doc section or the source-code file ``utilities.py``, in which a multitude of possibilities for input and output is shown.


Sensor Files
~~~~~~~~~~~~

Yet another config files type are the Sensor or Pad files. In these files general information about the Sensor or to measure
device are stored as well as optional location information. This location information are for automated test in a probe station.
These files are stored in the ``Pad_files`` folder, which again can contain subfolder with names of your liking. These
additional folder will be interpreted as different projects you are working on. (See accessing the data section below).

Such a Pad file can look like this:

.. code-block:: python

   Campaign: Hamamatsu 6inch Irradiation
   Creator: Dominic Bloech 17.07.2018

   reference pad: 1
   reference pad: 32
   reference pad: 64

   # Additional parameters
   implant_length: 20036
   metal_width: 35
   implant_width: 22
   metal_length: 19332.35
   pitch: 90
   thickness: 240
   type: p-type

   strip	x	y	z
   1	    0	0	0
   2	    0	90	0
   3	    0	180	0
   4	    0	270	0
   5	    0	360	0
   6	    0	450	0
   7	    0	540	0
   8	    0  	630	0
   9	    0	720	0
   10	    0	810	0
   11	    0	900	0
   12	    0	990	0
   13	    0	1080	0
   14	    0	1170	0



In the first few lines of text the header is defined. Each line with a '#' is considered to be a comment line. The other
lines having a semicolon represent a item type variable for additional information. Non of these parameters in the header
are mandatory and you also can extend these parameters. How you use it in your workflow is to your liking.

If you want to make automated measurements in a probestation on the other hand you will need at least the ``reference_pad: 1``
items. These specify (if correctly implemented) the three points/pad numbers for the coordinate transformation.

.. note:: This structure is implemented as a plugin, if you write your own plugins for the alignment you can exchange this mechanism with one you like!

The second part of this file are coordinates. Here the starting line is ``strip	x	y	z``. This line HAS to start with
the word strip, otherwise the program will not know where the coordinates start. (Except you teach the program to).

.. note:: You can add more parameters if you want, e.g. an angle or so.

After that the program reads in the data separated by tabs or spaces in a list of lists. See accessing data part for clarification.

Accessing Pad data
******************

The corresponding data structure is called ``pad_files_dict``. The type of this structure is again a dictionary containing
as items the different folders in the ``Pad_files`` folder. These are as mentioned before interpreted as some kind of
projects you have. Inside those folders are then the individual pad files.

The accessing scheme is a hierarchical one. Meaning the keys of ``pad_files_dict`` are the names of the project aka. folder
names. Inside the value to this key you find yet again a dictionary with the keys being the individual sensors. Inside those
you find also a dictionary with the keys ``reference_pads``, ``header``, ``data`` and ``additional_params``.

    * The ``reference_pads`` entry contains the pad and the locations of the defined reference pads
    * The ``header`` entry contains the whole header
    * The ``additional_params`` entry contains the parameters of the header with : as dictionary
    * The ``data`` entry is a list of the length of the coordinate lines in the pad file. Each list entry is another list, containing the tab or space separated values form the coordiante section of the pad file.

Wow, a lot of dictionaries and list, to clarify a small example how you access data.

.. code-block:: python

    xcor = pad_files_dict["My_project"]["Sensor_1"]["data"][2][1] # Will be 0
    ycor = pad_files_dict["My_project"]["Sensor_1"]["data"][2][2] # Will be 90
    zcor = pad_files_dict["My_project"]["Sensor_1"]["data"][2][3] # Will be 0

    metal_width = pad_files_dict["My_project"]["Sensor_1"]["additional_params"]["metal_width"] # Will be 35

.. warning:: Be careful while accessing data from the dictionaries, if the key does not exist python will say No and the program stops. So make sure you check the availability while accessing!!!

