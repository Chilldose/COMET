Measurement Job Generation
==========================

The measurement job generation is one of the most important tasks in the framework and is due to its design highly adaptable
to input data. The general workflow of the mechanism is relatively fast explained, though.

Base Structure
~~~~~~~~~~~~~~

As mentioned in the :ref:`Data Exchange` section the program exchanges data via python dictionary objects. The same holds
for the measurement job generation. The sendet message consists of a prior which must contain at the following data

.. code-block:: python

    general_settings = {"Measurement" :
                        {"Save_data": bool,
                        "Filepath": "A valid filepath",
                        "Filename": "A valid filename,
                        "skip_init": bool}
                       }

The Key from the main dict says, that the event loop has to interpret all following data in the consens of a measurement job.

Though more parameters would be possible here, like conifgs etc, I would not recommend it, since it is intended to only
have the basic global parameters in it.

The ``Save_data`` parameter states weather or not to save data to a file or not

.. note:: I would recommend to always save to a file!

The ``skip_init`` parameters states if all instruments should be initialized prior to the measurement. And the other two
parameters are self-explanatory.

.. note:: A very handy optional parameter can be the ``header`` parameter. Here only a string is valid. All written there will a prefix  the outputfile.

The next crucial key entry is the measurement itself. This means whichever measurement you want to conduct the key has
to have the same name as the measurement class its defined at.
So e.g. if you want to call the ``IV_class()`` measurement the key of the dict entry in the job dictionary has to be ``"IV": ...``

The value to this key can be again a dictionary containing all data YOUR measurement pluging needs.

A full demo dict can look like this

.. code-block:: python

    job_dict = {"Measurement" :
                        {"Save_data": bool,
                        "Filepath": "A valid filepath",
                        "Filename": "A valid filename,
                        "skip_init": bool,
                        "header":"# Measurement file: \n " \
                                 "# Campaign: " + self.variables.default_values_dict["Defaults"]["Current_project"] + "\n " \
                                 "# Sensor Type: " + self.variables.default_values_dict["Defaults"]["Current_sensor"] + "\n " \
                                 "# ID: " + self.variables.default_values_dict["Defaults"]["Current_filename"] + "\n " +\
                                 "# Operator: " + self.variables.default_values_dict["Defaults"]["Current_operator"] + "\n " \
                                 "# Date: " + str(time.asctime()) + "\n\n"
                        "dynamicwaiting": {"StartVolt": 0,
                                           "EndVolt": float(self.dynamic.EndVolt_IV.value()),
                                           "Steps": float(self.dynamic.Steps_IV.value()),
                                           "Complience": float(self.dynamic.complience_IV.value()),
                                           "num_of_points": 30
                                          }
                                   }


               }


After the whole job data is gathered you can place it on the queue to the event loop and the measurement starts.


.. code-block:: python

    self.variables.message_from_main.put(job_dict)


.. note:: You can place more then one measurement in the dictionary. If more then one is prevalent the program conducts all measurements! In order to not conduct randomized measurements you can state the parameter ``measurement_order`` in the ``defaults.yml`` file and state which measurement has to be conducted before another.

.. note:: It is good practice to always write the job to the log file if something went wrong this can easily be done via the log system!

Accessing measurement data
~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to use the data in the measurement plugin you have written you just need to access it via the designated object.
If you have followed the :ref:`Tutorials` you should have directly access to the dictionary. Each plugin gets as first
(and mostly only argument) the parent class object passed. If there you access the object ``parentclass.job_details`` you
get the whole dictionary back you just created in the previous section.

A small example:

.. code-block:: python

    class IV_class: # Every measurement muss have a class named after the file AND the suffix '_class'

    def __init__(self, main_class):
        # Here all parameters can be definde, which are crucial for the module to work, you can add as much as you want
        self.main = main_class # Import the main parameters and functions (as well as the job dictionary

    def show_the_job():
        """Simply prints the job details"""
        print self.main.job_details

