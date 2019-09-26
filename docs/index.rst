.. UniDAQ documentation master file, created by
   sphinx-quickstart on Thu Aug 02 08:34:07 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

:orphan:

Welcome to the UniDAQ documentation!
====================================

This software was developed by Dominic Blöch during his Phd Thesis at HEPHY Vienna.
It features a GUI based software for testing semiconductor Sensor.
The core program features easy device implementation through plugin support. The same holds for adding GUI elements and measurements.

.. toctree::
   :maxdepth: 2
   :caption: COMET Guides

   programstructure
   installation
   gettingstarted
   tutorial
   measurementjobgen

.. toctree::
   :maxdepth: 2
   :caption: COMET Structure

   datastructure
   dataexchange


.. toctree::
   :maxdepth: 1
   :caption: Measurement Plugins

   measurement_plugins/IVCV
   measurement_plugins/Stripscan
   measurement_plugins/RelaxTimeAnalysis

.. toctree::
   :maxdepth: 1
   :caption: General Purpose GUI Plugins

   GUI_plugins/resources
   GUI_plugins/Device_Com
   GUI_plugins/Data_Explorer


.. toctree::
   :maxdepth: 1
   :caption: Code references

   Tools


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
