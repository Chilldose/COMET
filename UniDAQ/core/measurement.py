import time
import logging

class StopProcessIteration(Exception):
    """Raise to gracefully stop a process."""
    pass

class SkipProcessIteration(Exception):
    """Raise to skip execution of current iteration."""
    pass

class StopMeasurement(Exception):
    """Raise to gracefully stop a measurement."""
    pass

class MeasurementProcess(object):
    """Inherit this class to implement a measurement process loop.

    Keyword Arguments:
        - parent -- reference to parent instance (default None)
        - delay -- iteration delay in seconds (default 0.0 sec)
    """

    default_delay = 0.0
    """Default iteration delay in seconds."""

    def __init__(self, parent=None, delay=None):
        self.__parent = parent
        self.__delay = delay or self.default_delay
        self.__iteration = 0

    @property
    def parent(self):
        """Returns parent instance or None."""
        return self.__parent

    @property
    def delay(self):
        """Returns iteration delay."""
        return self.__delay

    @property
    def iteration(self):
        """Returns current iteration count."""
        return self.__iteration

    def is_alive(self):
        """Overload to implement custom loop stop condition."""
        raise NotImplementedError()

    def iteration_begin(self):
        """Called before loop delay.
        Overload this method with custom implementation.
        """
        pass

    def iteration_end(self):
        """Called after loop delay.
        Overload this method with custom implementation.
        """
        pass

    def wait(self):
        """Default iteration delay.
        Overwrite this method to implement a custom loop delay.
        """
        time.sleep(self.delay)

    def run(self):
        """Runs the process loop."""
        # Reset iteration counter
        self.__iteration = 0
        try:
            while self.is_alive():
                try:
                    self.iteration_begin()
                    self.wait()
                    self.iteration_end()
                except SkipProcessIteration as e:
                    logging.warning(e)
                # Increment iteration counter
                self.__iteration += 1
        except StopProcessIteration as e:
            logging.info(e)

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
