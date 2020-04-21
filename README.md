# COMET

## What you need

**First** you need a python python 3.7 64 bit distribution. (32 bit works as well but will be unstable)
I recommended to use COMET with an Anaconda python distribution which you can download here:

[Download Anaconda here](https://www.anaconda.com/download/)

.. warning:: Make sure to download the 64-bit version!

it will work with a normal python version too, but I have not tested it. Furthermore, i have set up an Anaconda environment,
so you do not need to painfully install all modules by hand.


**Secondly** if you want the SQC setup version you need to install National Instrument VISA drivers. These drivers can be found here:

[NI-Visa drivers](http://www.ni.com/download/ni-visa-17.0/6646/en/>)

if you want to use the Analysis and and plotting functionallity only, you do not need this.

You will need drivers higher than 17.0 for COMET to work properly. If you have installed a LabView version it is usually already
installed on your pc. If so, make sure in the NiMAX app what version of NI-Visa is installed on your system.

.. :warning: The module PyVISA works with 32- and 64- bit Python and can deal with 32- and 64-bit NI-VISA libraries without any extra configuration. What PyVISA cannot do is open a 32-bit VISA library while running in 64-bit Python (or the other way around).

.. :warning: There is a pyvisa-py version as well, which does not rely on the NIVisa drivers. For simple measurement setups this will work as well, but it is not as sophisticated as the normal pyvisa and errors may happen. So be warned.

The program is known to be running on Windows, Linux (Centos7) and Mac.

## Setting Up The Environment

With python up and running, you can run the **environement_setup.py <your_system_req_file.yml** file by e.g.::

    python environment_setup.py requirements_Winx86.yml

this will (when Anaconda is installed) automatically install all required modules for the program to run. If you don't have Anaconda installed and don't want to use it, you can look in the "requirements.yml" file to see what dependencies the program needs.

## Once installed, test

If you have installed all correctly we can now test if everything is set-up correctly. First go and follow the
instructions on **Setting Up The Environment**. When this is done open the Anaconda Prompt app on your PC and activate
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

## Download the COMET source code


If you just want the latest version of COMET, download it from my GitHub repository.

[Git repo](https://github.com/Chilldose/COMET)

## How to Use

There is a documentation and a section called "Tutorial", this will guide you through the process of how to use this software and it will give you even more additional information about the software. You can access the [Documentation](https://chilldose.github.io/COMET/) or if you look into the folder ~/docs/index.html.

## Built With

* [PyVisa](https://github.com/pyvisa/pyvisa) - For the communication with devices
* [PyQt](https://github.com/pyqt) - For the GUI
* [Pyqtgraph](https://github.com/pyqtgraph/) - For the plots



## Versioning

I use the [SemVer](http://semver.org/) for versioning.


## Authors

* **Dominic Blöch** - *Initial work and Developer* - [Chilldose](https://github.com/Chilldose)
* **Bernhard Arnold** - *Developer* - [arnobaer](https://github.com/arnobaer)

Beta Tester:

* **Gabriel Szabo** - *Project Student*

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Thanks to my friends for their help
* The foodora pizza delivery guy with the long beard
