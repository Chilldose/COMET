import logging

class StopMeasurement(Exception):
    """Raise to gracefully stop a measurement."""
    pass

class Measurement(object):
    """Inherit this class to implement a measurement.

    Keyword Arguments:
        - manager -- a device manager instance
    """

    def __init__(self, manager):
        self.manager = manager

    def init(self):
        """Called at the begin of a measurement.
        Overload this method with custom implementation.
        """
        pass

    def process(self):
        """Called after measurement initalization.
        Overload this method with custom implementation. To gracefully stop the
        measurement raise a StopMeasurement exception inside the method.
        """
        pass

    def final(self):
        """Called after measurement process.
        Overload this method with custom implementation.
        """
        pass

    def run(self):
        """Runs the measurement."""
        context = self.__class__.__name__
        logging.info("starting %s", context)
        # Initialize the measurement
        self.init()
        try:
            # Run the main measurement
            self.process()
        except StopMeasurement as e:
            logging.info(e)
        # Run final cleanup
        self.final()
        logging.info("stopped %s", context)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
