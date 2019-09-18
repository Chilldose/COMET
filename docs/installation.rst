.. _installation:

Installation
===============

What you need
~~~~~~~~~~~~~
**First** you need a python python 3.7 64 bit distribution. (32 bit works as well but will be unstable)
I recommended to use COMET with an Anaconda python distribution which you can download here:

`Download Anaconda here <https://www.anaconda.com/download/>`_

.. warning:: Make sure to download the 64-bit version!

it will work with a normal python version too, but I have not tested it. Furthermore, i have set up an Anaconda environment,
so you do not need to painfully install all modules by hand.


**Secondly** you need to install National Instrument VISA drivers. These drivers can be found here:

`NI-Visa drivers <http://www.ni.com/download/ni-visa-17.0/6646/en/>`_

You will need drivers higher than 17.0 for COMET to work properly. If you have installed a LabView version it is usually already
installed on your pc. If so, make sure in the NiMAX app what version of NI-Visa is installed on your system.

.. warning:: The module PyVISA works with 32- and 64- bit Python and can deal with 32- and 64-bit NI-VISA libraries without any extra configuration. What PyVISA cannot do is open a 32-bit VISA library while running in 64-bit Python (or the other way around).

.. note:: There is a pyvisa-py version as well, which does not rely on the NIVisa drivers. For simple measurement setups this will work as well, but it is not as sophisticated as the normal pyvisa and errors may happen. So be warned.

The program is known to be running on Windows, Linux (Centos7) and Mac.

Setting Up The Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

With python up and running, you can run the the **environement_setup.py** file by::

    python environment_setup.py

this will (when Anaconda is installed) automatically install all required modules for the program to run. If you don't have Anaconda installed and don't want to use it, you can look in the "requirements.yml" file to see what dependencies the program needs.

Once installed, test
~~~~~~~~~~~~~~~~~~~~
If you have installed all correctly we can now test if everything is set-up correctly. First go and follow the
instructions on :ref:`Setting Up The Environment`. When this is done open the Anaconda Prompt app on your PC and activate
the new environment which should have been set-up for you while installation. After that import the PyVisa module and
try to start a resource manager ::

    (base) activate UniDAQenv
    (UniDAQenv) python
    Python 3.7 |Anaconda, Inc.| (default, May  1 2018, 18:37:09) [MSC v.1500 64 bit (AMD64)] on win32
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import visa
    >>> rm = visa.ResourceManager()
    >>> print(rm.list_resources())

If this code does not yield any errors, PyVisa and the environment was correctly installed on your system. And if some devices are already
connected to your system these should be listed now.

Download the COMET source code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you just want the latest version of COMET, download it from my GitHub repository.

`Git repo <https://github.com/Chilldose/UniDAQ>`_.

Once you have the version you like, continue with the :ref:`gettingstarted` section.

