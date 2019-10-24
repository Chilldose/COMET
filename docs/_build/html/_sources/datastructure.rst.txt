
Data Structure
==============

In this chapter the base data structure of COMET is explained. The data storage and state variables are stored in global accessible variables. This means they can (provided you follow
the rules provided in this doc) accessed from anywhere in the framework. Every user can add, delete or alter variables.
So be warned, do not meddle with variables you do not know! For the sake of dynamicallity of the software
it is necessary for the data structures not to be thread safe. This means every variable can be out of date
after accessing it. Furthermore, fast writing to a variable can lead to race conditions inside of the program, if
badly written.

An easy rule of thumb to avoid race conditions and unnecessary variables declarations are:

    * Do you really need this variable global accessible?
    * Only one subprogram can alter the value, all others just reads from it
    * Only binary states allowed for multi access variables
    * Non state critical variables for multi access variables

With these simple rules you should not have problems with this state machine.

Framework variables
~~~~~~~~~~~~~~~~~~~

Every main part of COMET has access to an unique dictionary, containing all important variables and objects for COMET to
run. This dictionary is generated in the ``main.py`` file and is then passed to the event loops and eventually passed to
all measurement plugins.

With it you can access all important variables of the state machine, xyz-Stages etc. This dictionary is not restricted to
the amount of entries listed below. So if you see fit or need more variables, which need to be accessible across all threads and parts
of the program you can add some.

.. warning:: Some of the variables are crucial for a stable working program, so be careful when edition this dictionary!

When you start a clean instance of COMET this dictionary contains the following entries:

    :**Configs**: The Configs dictionary containing all variables of the state machine and the other dict objects in the setup config.
    :**Devices**: A dictionary containing all connected and loaded devices.
    :**VCW**: A Visa Connect Wizard instance which has all functions for communication with devices.
    :**rootdir**: The root directory of the software.
    :**App**: The Qt App object this software is running in.
    :**Table**: The xyz-Stage object the software is connected to (None if no table is configured/connected).
    :**Switching**: A switching object instance the software is connected to (None if none is configured/connected).
    :**Message_to_main**: A Queue object to the GUI event loop.
    :**Message_from_main**: A Queue object to the measurement event loop.
    :**Queue_to_GUI**: Deprecated Queue object, which will be integrated into message_to_main.
    :**Django**: The Django web-server object the software is connected to (None if none is configured/connected).
    :**Server**: The TCP/IP server the software is connected to (None if none is configured/connected).
    :**Client**: The TCP/IP client the software is connected to (None if none is configured/connected).

For the normal user the only important keys form this dictionary are: Configs, Devices, VCW, Table and Switching. With these
few you have everything, that is necessary to build your own setup, with GUI and measurement plugins.

Measurements Main Object
~~~~~~~~~~~~~~~~~~~~~~~~

The measurements Main Object is located in the file ``measurements.py`` file. It contains the class: ``measurements_classs``,
which inherits from the **Thread** module.

Started only by the measurement event loop as an own thread, it gets passed the measurement event loop instance, the framework
variables and the measurement job details.

While the first parameter is only used internally and should not bother you the framework and the job details, my be of interest.
The **framework** is a dictionary containing all important variables like the state machine variables, for more information see the previous chapter
:ref:`Framework variables`.

.. note:: Each measurement plugin gets passed the ``measurement_class`` object, and therefore your plugin can access these variables, via ``measurement_class.framework``.

The **job_details** is a dict, that was send by the user, and is containing all information concerning the current measurement job.
Like with the framework variable this object is accessible via ``measurement_class.job_details``.

To make the access to the important framework variables (and more) easier for the user, the measurement class has some of the
variables as members.

    :**.settings**: The state machine dict
    :**.devices**: The devices object dict
    :**.VCW**: The VCW object
    :**.table**: The table object
    :**.switching**: The switching object
    :**.queue_to_event_loop**: Queue object to the measurement event loop
    :**.queue_to_main**: Queue object to the GUI event loop

------------------------------------------------------------------------------------------------------------------------

    :**.build_command**: A function which can build you device commands. See API for more information
    :**.measurement_data**: A dict containing keys for all measurements and inside are numpy arrays holding the measured data
    :**.measurement_files**: The files object for automatic generated output files for each running measurement type.


GUI Main Object
~~~~~~~~~~~~~~~

The GUI Main Object is located in the file ``GUI_classes.py`` file. It contains the class: ``GUI_classes``,
which inherits from the **QWidget** module.

Directly started by the ``main.py`` file it only gets passed the framework variables. Which is then accessible via ``GUI_classes.framework``
from all your GUI plugins, since the GUI object gets passed to every GUI plugin.

To make the access to the important framework variables (and more) easier for the user, the measurement class has some of the
variables as members.

    :**.default_values_dict**: The state machine dict
    :**.devices_dict**: The devices object dict
    :**.VCW**: The VCW object
    :**.table**: The table object
    :**.switching**: The switching object
    :**.message_from_main**: Queue object to the measurement event loop
    :**.message_to_main**: Queue object to the GUI event loop
    :**.client**: TCP/IP client
    :**.server**: TCP/IP server
    :**.additional_files**: The dict object for additional files specified in the configs

One important member of the ``GUI_classes`` is the ``GUI_classes.add_update_function``. If you want to have a function called
on every update of the GUI, you can pass any function object to this function and it will add it to the GUI update framework.

.. warning:: But be aware! If your function draws to much computing power you may experience lags and or crashed or freezes!


Config Files
~~~~~~~~~~~~

To configure a project setup you need to have a directory in your ``COMET\config\Setup_configs`` with the name of your  liking.
The only restriction is that this directory you created has a YAML styled file called ``settings.yml`` and inside at least
the entry ``Settings_name: settings`` is configured. The rest is -in theory- optional.

A good starting point would be a file with at least these ::

    --- # Block of dict entries

    # Critical parameters
    Settings_name: settings # The name of the settings which will be shown in the framework and will be the addressing name (settings here is important)

    measurement_types: # Different measurement types which can be conducted
        - temperature
        - humidity

    measurement_order: # aka. all measurement plugins
        - IVCV


    # Optional parameters
    temp_history: 3600 # How much should be shown in the humidity history in seconds
    temphum_update_intervall: 5000 # Update intervall of the humidity controll in ms
    temphum_plugin: Brandbox_temperature_humidity
    time_format: "%H:%M:%S" # Time format of the humidity control
    GUI_update_interval: 200.0 # How often should the GUI be updated in ms
    store_data_as: json # Additional parameter, usually data will be stored as ascii during measurement,
    # but if you need the data in another format you can specify it here

    GUI_render_order: # Give a render order if need be, otherwise all found gui elements will be rendered
        - DeviceCommunication
        - DataBrowser
        - Resources



    # Devices aliases for internal use, the key will then be the frameworks internal representation and the value is the display name
    Aliases:
        BiasSMU: 2470 Keithley SMU

    Devices:
          2470SMU:
            Device_name: 2470 Keithley SMU # The actual device name from which it should get all commands
            Device_IDN: KEITHLEY INSTRUMENTS,MODEL 2470,04424944,1.6.8d
            Connection_resource: IP:TCPIP0::192.168.130.131::inst0::INSTR

parameters, though. If you want to know more how and why these parameters are nice to have, see chapter :ref:`How to`.
Here all parameters are explained in detail.

This YAML file will be added as aa dictionary in the :ref:`Framework variables`, accessible under the path ``Configs\settings``
By placing more than one YAML file in the projects folder, more dictionaries will be created in the ``Configs`` of the framework variables.
Each of these YAML files must have a ``Settings_name`` which is unique!

.. note::  The name to access it is the the value you are giving under the entry ``Settings_name``.

A special place here is if you create a YAML file with the ``Settings_name: framework_variables``, these are additional
parameters which you want to have in your ``settings.yml`` file, but to keep the ``settings.yml`` file clean you can write
them in here. Usually this file is used to define default values for state machine parameters your plugins need.


Addtional Files
~~~~~~~~~~~~~~~

What if you have some further data files, which you need for your measurement plugin to work, which does not fit in any
of the previously explained solutions.

Do not worry! COMET has the capability to load any (UNICODE) file in variable path depth. Any directory you place in your
project directory will get an entry in the ``Configs`` dictionary of the framework variables, so: ``framework\Configs\<YourDirName>``.
Every file inside this directory will be interpreted as text file and read in as such. The individual files are again
accessible by key. So: ``framework\Configs\<YourDirName>\<File1>``.

.. important:: If in your directory other directories are present, COMET will do the same with this directory and so on!

To make this mechanism more clear see the example below, image you have a project directory path structure like: ::

    │   badstrip.yml
    │   framework_variables.yml
    │   settings.yml
    │   switching.yml
    │
    └───Pad_files
        ├───HPK 6 inch
        │       Irradiation2.txt
        │
        ├───HPK 6 inch 2018
        │       2S.txt
        │       PSlight_notcorr.txt


This will result in a dictionary in the ``Configs`` parameters as: ::

    YourProject = {
                    settings: <dict>
                    badstrip: <dict>
                    switching: <dict>

                    Pad_files: {
                                HPK 6 inch: {Irradiation2: <txt>}
                                HPK 6 inch 2018: {2S: <txt>, PSlight_notcorr: <txt>}
                                }
                    }

