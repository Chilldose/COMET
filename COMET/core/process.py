import time
import logging

class StopProcessIteration(Exception):
    """Raise to gracefully stop a process."""
    pass

class SkipProcessIteration(Exception):
    """Raise to skip execution of current iteration."""
    pass

class Process(object):
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

    def init(self):
        """Called at the begin of a process.
        Overload this method with custom implementation.
        """
        pass

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

    def final(self):
        """Called at the very end of a process.
        Overload this method with custom implementation.
        """
        pass

    def run(self):
        """Runs the process loop."""
        # Reset iteration counter
        self.__iteration = 0
        self.init()
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
        self.final()

if __name__ == '__main__':
    import doctest
    doctest.testmod()
