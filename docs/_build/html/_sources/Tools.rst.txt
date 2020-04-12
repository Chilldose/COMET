Measurement Tool Box functions
==============================

In the following a simple doc string representation of all tool box functions are displayed. These functions can be used
to simplify your own measurement plugin. You can simply import it and save an instance of this class and reference it.
Or more conveniently, your measurement plugin can inherit the tools class and make every member of **tools** a member of
your plugin. To see how this works see in the tutorial section the chapter :ref:`Add a new measurement`.

.. autoclass:: measurement_plugins.forge_tools.tools
	:members:


VCW - Visa Connect Wizard
=========================

In the following a simple doc string representation of all VCW functions are displayed. These functions can be used
to simplify your own measurement plugin. You can simply import it and save an instance of this class and reference it.
Or more conveniently, your measurement plugin always gets a working instance of it in the form of the framework variables
object. With it you can easy and savely send your devices any kind of command directly.

.. note:: Usually you are using a wrapper function of the :ref:`Measurement Tool Box functions` for this functions!

.. autoclass:: VisaConnectWizard.VisaConnectWizard
	:members:


XYZ-Stage Control Class
=======================

The XYZ-Stage Control Class is a core feature of COMET it allows you to safely operate any configured automated table.
An instance is generated on start up -if a stage is configured- in the :ref:`Framework variables`. It features several
move functions which has build in the functionality to first move down the stage and then move to another location and
if in position move the table up again. This prevents scratches on e.g. silicon sensors when contacted with needles.

Furthermore, it checks the position of the stage to make sure the table is always on the correct location. If not an error
will be raised in the COMETs internal error handling system.

.. autoclass:: utilities.table_control_class
	:members:

Switching System Control Class
==============================

The Switching System Control Class gives you functions to safely operate a switching system.
An instance is generated on start up in the :ref:`Framework variables`. It has the ability to cope
with lots of different variants of switching systems. In the following section the needed config files and a how to, will
be explained.

First of all you need at least one switching device configured. This device needs an entry ``Device_type: Switching relay``
so that COMET knows that this device is a switching capable device. The other parameters of this device are of the same
type as any other measurement device.

The other thing you need are configs to tell COMET what to switch. Therefore, you need a config YAML file in your project
with the ``Settings_name: Switching`` entry and ``Device_type: Switching relay``. This is followed by the entry ``Switching_Schemes``.
In it are the different measurement types to switch followed by the name of the device and then the switching relays which need
to be closed.

To clarify what I mean with that see an example: ::

    ---
    Settings_name: Switching
    Device_type: "Switching relay"
    Switching_Schemes:
      IV: # Name of the switching configuration
        HVSwitching: # Name or Alias of a Switching device
          - A1  # relay to switch
          - B1
          - C2
      Rpoly:
        HVSwitching: # Name or Alias of a Switching device
          - A1
          - B1
          - C1

        LVSwitching: # Name or Alias of a Switching device
          - 1C05
          - 1C06

Here two switching schemes are defined. IV and Rpoly. For IV only the device/alias HVSwitching will be switched with
the relays: A1,B1,C2. For Rpoly not only HVSwitching also the switching device LVSwitching will be switched.

If you have configured your setup like this it is fairly easy to switch to the measurement configuration IV.
Just call the function: ``switch_to_measurement("IV")`` and the class will handle the switching on its own.

.. important:: The class checks if the switching has been done correctly. If your switching of the device does not match the intended switching an error will be raised and the user will be informed.

Some devices have the ability to do a device exclusive switching, so all switching logic is done by the device.
If you want to use this device exclusive switching, the device config file must have the entry: ``device_exclusive_switching: True``
Otherwise you can set it False or not state it at all.
For non exclusive switching devices the switching logic will be done via the switching class.

.. note:: In future releases there will be a config option to decide BBM or MBB. Currently it is hard coded to BBM since this is the recommended way to do it.

.. autoclass:: COMET.utilities.switching_control
	:members:

