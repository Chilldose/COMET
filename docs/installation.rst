Installation
============

What you need
~~~~~~~~~~~~~
**First** you need a python 3.7 64 bit distribution. (32 bit works as well but will be unstable)
I recommended to use COMET with an Anaconda python distribution which you can download here:

`Download Anaconda here <https://www.anaconda.com/download/>`_

.. warning:: Make sure to download the 64-bit version!

.. note:: You can alternatively install a miniconda version, if the full anaconda is to heavy.

it will work with a normal python version too, but I have not tested it. Furthermore, i have set up an Anaconda environment,
so you do not need to painfully install all modules by hand.

.. note:: The next step is only needed if you intend to use the probe station device communication functionality. If you do not need it skip the next part.

**Secondly** you need to install National Instrument VISA drivers. These drivers can be found here:

`NI-Visa drivers <http://www.ni.com/download/ni-visa-17.0/6646/en/>`_

You will need drivers higher than 17.0 for COMET to work properly. If you have installed a LabView version it is usually already
installed on your pc. If so, make sure in the NiMAX app what version of NI-Visa is installed on your system.

.. warning:: The module PyVISA works with 32- and 64- bit Python and can deal with 32- and 64-bit NI-VISA libraries without any extra configuration. What PyVISA cannot do is open a 32-bit VISA library while running in 64-bit Python (or the other way around).

.. note:: There is a pyvisa-py version as well, which does not rely on the NIVisa drivers. For simple measurement setups this will work as well, but it is not as sophisticated as the normal pyvisa and errors may happen. So be warned.

If you do not want or can install the NI-Visa drivers COMET ships with a device communication that is completely independent of those drivers.
BUT these drivers are far from perfect and not as sophisticated as the NI drivers. So be warned.

The program is known to be running on Windows, Linux (Centos7) and Mac.

Setting Up The Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

With python up and running, you can run the **setup.py** file.
This will then install all packages the software needs to be fully functional. ::

    python setup.py

If something does not go as intended you can try to install a specific OS setup file by e.g. ::

    python setup.py COMET/resources/<your_system_req_file.yml>

this will (if Anaconda is installed) automatically install all required modules for the program to run.
If you don't have Anaconda installed and don't want to use it, you can look in the "COMET/resources/requirements.yml" file to see what dependencies the program needs.
If the software cannot find anaconda installed it will ask you to directly install the "normal" python pip file.

If you have anaconda installed to your system and installed the anaconda environment you must activate this environment by ::

    (base) activate COMET
    (COMET) python COMET

Once installed, test (Only SQC)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you have installed all correctly we can now test if everything is set-up correctly. First go and follow the
instructions on :ref:`Setting Up The Environment`. When this is done open the Anaconda Prompt app on your PC and activate
the new environment which should have been set-up for you while installation. After that import the PyVisa module and
try to start a resource manager ::

    (base) activate COMET
    (COMET) python
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

`Git repo <https://github.com/Chilldose/COMET>`_.

Once you have the version you like, continue with the :ref:`Getting Started` section.


I want to start COMET with point an click
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since python scripts are usually started via the command line. In the case of COMET ::

  python COMET.py

it is not intended to have a "double-click" function. Furthermore, COMET comes with some command line arguments you can use.
But if you really want to have a icon to click. You can do the following.

In the operating system of your choice you have to find the installation directory of you anaconda installation.
Under win10 its something like ``C:\Users\MyUserName\anaconda3``. For linux and Mac it is similar.

The create a .bat (for win) or .sh (for linux) file inside the commands ::

  call C:\Users\MyUserName\anaconda3\Scripts\activate.bat C:\Users\MyUserName\anaconda3\envs\COMET
  call cd C:\<path_to_the_COMET_dir>\
  call python COMET.py
  pause

need to be executed. In this case for a .bat file. If you do not have Anaconda installed you can delete the first entry, which simply activates
the conda env for COMET.
