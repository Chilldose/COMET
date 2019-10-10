import logging
import time
import random
import sys, os

from COMET.core.process import Process, StopProcessIteration, SkipProcessIteration
from COMET.core.measurement import Measurement, StopMeasurement
from COMET.VisaConnectWizard import VisaConnectWizard import VisaDeviceManager

class MySubProcess(Process):

    default_delay = .75

    def is_alive(self):
        return self.parent.iteration < 4 and self.iteration < 3

    def iteration_end(self):
        logging.info("%s::%s -> %d", self.__class__.__name__, self.iteration_end.__name__, self.iteration)

    def wait(self):
        """A fancy random wait method."""
        t = time.time()
        delay = random.uniform(0.75, 1.25)
        throttle = 0.025
        sys.stdout.write("dispatching")
        while time.time() < t + delay:
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(throttle)
        sys.stdout.write("done.")
        sys.stdout.write(os.linesep)

class MyProcess(Process):

    def is_alive(self):
        return self.iteration < 10

    def iteration_begin(self):
        if self.iteration % 3:
            raise SkipProcessIteration("Let's skip this iteration ({})...".format(self.iteration))
        if self.iteration < 3 and self.delay >= 1.0:
            raise StopProcessIteration("This is too low!")
        logging.info("%s iteration=%d, manager=%s", self.__class__.__name__, self.iteration, self.parent.manager.__class__.__name__)

    def iteration_end(self):
        # Create a local process instance inside another process
        helper = MySubProcess(self)
        helper.run()

class MyFancyMeasurement(Measurement):

    def init(self):
        # Create static instance
        self.my_process1 = MyProcess(self, .2)

    def process(self):
        """My measurement process."""
        self.my_process1.run()
        # Create and run a local process instance
        my_process2 = MyProcess(self, .5)
        my_process2.run()
        # Bail out
        if random.randint(0, 1):
            raise StopMeasurement("Well, enough, we're done!")
        # This is executed conditional
        MyProcess(self, .1).run()

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)

    manager = VisaDeviceManager('@sim')
    context = {} # placeholder

    measurement = MyFancyMeasurement(manager)
    measurement.run()
