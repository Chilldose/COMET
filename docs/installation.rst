.. _installation:

Installation
===============

What you need
~~~~~~~~~~~~~
**First** you need a python python 2.7 64 bit distribution. (32 bit works as well but will be unstable)
I recommended to use UniDAQ with an Anaconda python distribution which you can download here:

`Download Anaconda here <https://www.anaconda.com/download/>`_

.. warning:: Make sure to download the 64-bit version!

it will work with a normal python version too, but I have not tested it. Furthermore, i have set up an Anaconda environement,
so you do not need to painfully install all modules by hand.


**Secondly** you need to install National Instrument VISA drivers. These drivers can be found here:

`NI-Visa drivers <http://www.ni.com/download/ni-visa-17.0/6646/en/>`_

You will need drivers higher than 17.0 for UniDAQ to work properly. If you have installed a LabView version it is usually already
installed on your pc. If so make sure in the NiMAX app what version of NI-Visa is installed on your system.

.. warning:: The module PyVISA works with 32- and 64- bit Python and can deal with 32- and 64-bit NI-VISA libraries without any extra configuration. What PyVISA cannot do is open a 32-bit VISA library while running in 64-bit Python (or the other way around).

The program is known to be running on Windows, Linux (Centos7) and Mac.


Once installed, test
~~~~~~~~~~~~~~~~~~~~
If you have installed all correctly we can now test if everything is setup correctly. First go and follow the
instructions on :ref:`Setting Up The Environement`. When this is done open the Anaconda Prompt app on your PC and activate
the new environement which should have been setup for you while installation. After that import the PyVisa module and
try to start a resource manager ::

    (base) activate UniDAQenv
    (UniDAQenv) python
    Python 2.7.15 |Anaconda, Inc.| (default, May  1 2018, 18:37:09) [MSC v.1500 64 bit (AMD64)] on win32
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import visa
    >>> rm = visa.ResourceManager()
    >>> print(rm.list_resources())

If this code does not yield any errors, PyVisa and the environement was correctly installed on your system. And if some devices are already
connected to your system these should be listed now.

Download the UniDAQ source code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you just want the latest version of e.g. the SQC software download the corresponding branch from my GitHub repository.

`Git repo <https://github.com/Chilldose/UniDAQ>`_.

If you want to develop your own GUI and measurement routines make sure to download a blank project from the tutorial branch `here <https://github.com/Chilldose/UniDAQ/tree/tutorial>`_.

Once you have the version you like, continue with the :ref:`gettingstarted` section.

