import logging

class StopMeasurement(Exception):
    """Raise to gracefully stop a measurement."""
    pass

class Measurement(object):
    """Inherit this class to implement a measurement.

    Keyword Arguments:
        - context -- measurement loop context
    """

    def __init__(self, context):
        self.context = context

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
        # Initialize measurement
        self.init()
        try:
            # Run main measurement
            self.process()
        except StopMeasurement as e:
            logging.info("aborting %s", context)
        # Run final cleanup
        self.final()
        logging.info("stopped %s", context)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
