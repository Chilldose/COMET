COMET crashed or I found a BUG, what should I do
================================================

This section is dedicated how to report BUGs and crashes correctly

Before submitting a BUG report please check the following things:

  * Have you tried turn it off and on again?
  * Have you read the manual?
  * Are you sure it is a BUG?
  * Have you correctly configured the software?
  * Is the data you provided correct?
  * Have you downloaded the newest version? If not do ``python COMET.py --update`` and try again.
  * Have you NOT tempered with some code beforehand?
  * Have you checked the logging stream handler for the error message?
  * Have you read and understood the logging stream handler for the error message?
  * Have you googled the error code of the error message?
  * Have you used the software as intended? No random button pressing?

If the answer is "yes" to all of these above questions. Then please file a report/issue
on my GitHub page under the COMET repository with as many details as possible like:

  * What was it you wanted to do.
  * What did you actually do.
  * When did it happen.

Please always provide the most recent logging output and the actual error message.

If the logging output does not yield useful information, to backtrace the problem, please change the
logging level in the option "Logging/Set Logging Level". Here you can change the logging level of all logging handlers.
I would recommend to change the logging level of the "FileRotationHandler", since it is persistent. Then trigger the error and
provide the last few logging messages from this.

.. note:: In my experience the most errors happen due to wrong use or wrong configurations. So please make sure you have read the manual and use the software as intended.
