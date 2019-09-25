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

.. autoclass:: UniDAQ.utilities.table_control_class
	:members:

Switching System Control Class
==============================

The Switching System Control Class gives you functions to safely operate a switching system. It has the ability to cope
with lots of different variants of switching systems. In the following section the needed config files and a how to will
be explained.

**TODO**

.. autoclass:: UniDAQ.utilities.switching_control
	:members:

