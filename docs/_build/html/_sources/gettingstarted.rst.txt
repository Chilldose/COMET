.. _gettingstarted:

Getting Started
===============

In order to run this program you need a Python Anaconda distribution and the NI-Visa drivers.
For more information on how to install see the :ref:`installation` guide.

Setting Up The Environement
~~~~~~~~~~~~~~~~~~~~~~~~~~~

With python up and running, you can run the the **environement_setup.py** file by::

    python environement_setup.py

this will (when Anaconda is installed) automatically install all required modules for the program to run. If you don't have Anaconda installed and don't want to use it, you can look in the "requirements.yml" file to see what dependencies the program needs.


Running The Program
~~~~~~~~~~~~~~~~~~~

Now it should be possible to run the program by: ::

    python UniDAQ.py

If you do not have Anaconda installed, start the program via ::

    python main.py

.. note:: If you running UniDAQ in a normal python distribution you have to install all modules by hand. No environement will be set up for you. For needed modules see the requirements.yml file.

.. warning:: If you run into a problem like, python does not find the environement, python was not recognised or a module cannot be found. Make sure the Anaconda python is accessible from the command prompt.

If something does not work out as planned try to test if everything was correctly installed on your system. Just follow
the instructions on :ref:`Once installed, test`

If everything has worked you should see a GUI pop up, which (depending on which GUI version you have) should look like
this

.. image:: pictures/UniDAQ_main.png
   :alt: PyVISA
   :class: floatingflask