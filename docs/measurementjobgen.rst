Measurement Job Generation
==========================

The measurement job generation is one of the most important tasks in the framework and is due to its design highly adaptable
to input data. The general workflow of the mechanism is relatively fast explained, though.

Base Structure
~~~~~~~~~~~~~~

As mentioned in the :ref:`Data Exchange` section the program exchanges data via python dictionary objects. The same holds
for the measurement job generation. The sended message consists of a prior which must contain the following data

.. code-block:: python

    general_settings = {
                        "Measurement" :
                            {
                            "Save_data": <bool>,
                            "skip_init": <bool>,
                            "Filepath": <A valid filepath>,
                            "Filename": <A valid filename>
                            }
                       }

The Key from the main dict says, that the event loop has to interpret all following data as a measurement job.

Though, more parameters would be possible here, like conifgs etc, I would not recommend it, since it is intended to only
have the basic global parameters in it.

The ``Save_data`` parameter states weather or not to save data to a file or not

.. important:::: I would recommend to always save to a file!

The ``skip_init`` parameters states if all instruments should be re-initialized prior to the measurement. And the other two
parameters are self-explanatory.

.. tip:: A very handy optional parameter can be the ``header`` parameter. Here only a string is valid. This string will be written to the file prior to the measurement.

The next crucial key entry is the measurement itself. This means whichever measurement you want to conduct.

.. important:: The key of the measurement must be a valid measurement plugin name!

So e.g. if you want to call the ``IV_class()`` measurement the key of the dict entry in the job dictionary has to be ``"IV": ...``

The value to this key can be again a dictionary containing all data YOUR measurement pluging needs. Here you are not restricted by the framework.

A full demo dict can look like this

.. code-block:: python

    job_dict = {"Measurement" :
                        {"Save_data": bool,
                        "Filepath": "A valid filepath",
                        "Filename": "A valid filename,
                        "skip_init": bool,
                        "header":"# Measurement file: \n " \
                                 "# Campaign: MyCampaign \n " \
                                 "# Sensor Type: CoolSensor \n " \
                                 "# ID: 12334 \n " +\
                                 "# Operator: Batman \n " \
                                 "# Date: 2.2.2222 \n\n"
                        "dynamicwaiting": {"StartVolt": 0,
                                           "EndVolt": -1000,
                                           "Steps": 1,
                                           "compliance": 0.0001,
                                           "num_of_points": 30
                                          }
                                   }


               }


After the whole job data is gathered you can place it on the queue to the event loop and the measurement starts.

.. code-block:: python

    message_from_main.put(job_dict)


You can place more then one measurement in the dictionary. If more then one is prevalent the program conducts all measurements!

.. important::  The order how the measurements are conducted is defined by the config parameter ``measurement_order`` in you project config file.

.. tip:: It is good practice to always write the job to the log file if something went wrong. This can easily be done via the log system!

Accessing measurement data
~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to use the data in the measurement plugin you have written, you just need to access it via the designated object.
If you have followed the :ref:`How to` you should have directly access to the dictionary.

A small example:

.. code-block:: python

    class IV_class: # Every measurement muss have a class named after the file AND the suffix '_class'

        def __init__(self, main_class):
            # Here all parameters can be definde, which are crucial for the module to work, you can add as much as you want
            self.main = main_class # Import the main parameters and functions (as well as the job dictionary

        def show_the_job():
            """Simply prints the job details"""
            print(self.main.job_details)
