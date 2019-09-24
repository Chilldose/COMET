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