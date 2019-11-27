from types import MethodType
import logging
import time
import re

class Device(object):
    """Generic VISA device driver.

    Keyword arguments:
    - manager -- resource manager
    - config -- device configuration dictionary

    Example:
    >>> manager = VisaConnectWizard()
    >>> config = {'set_voltage': '!VOLT {:.2f}'}
    >>> device = Device(manager, config)
    >>> device.set_voltage(42.0)
    """

    default_config = {
        'get_idn': '*IDN?',
        'set_reset': '*RST',
        'set_clear': '*CLS',
    }
    """Default VISA resource configuration, can be overwritten by user configuration."""

    reset_throttle = 0.05
    """Throttle for executing lsit of reset commands, in seconds."""

    def __init__(self, manager, config=None):
        self.__manager = manager
        # Copy default configuration
        self.__config = self.default_config.copy()
        # Update configuration
        if config is not None:
            self.__config.update(config)
        # Register methods from configuration
        for key, value in self.__config.items():
            # Register getters
            if re.match(r'^get_\w+$', key):
                self.__register(self.query, key, value)
            # Register setters
            if re.match(r'^set_\w+$', key):
                self.__register(self.write, key, value)

    def __register(self, method, name, command):
        """Registers get/set methods loaded from config."""
        def f(self, *args, **kwargs):
            logging.debug("%s(%s)::%s(command='%s')", self.__class__.__name__, self.resource, name, command)
            return method(command.format(*args, **kwargs))
        setattr(self, name, MethodType(f, self))

    @property
    def manager(self):
        """Returns resource manager."""
        return self.__manager

    @property
    def config(self):
        """Returns device configuration dictionary."""
        return self.__config

    def __getitem__(self, key):
        """Provided for convenience."""
        return self.config[key]

    def items(self):
        """Provided for convenience."""
        return self.config.items()

    @property
    def resource(self):
        """Returns VISA resource from configuration."""
        return self.config.get('Visa_Resource')

    def read(self):
        """Read from VISA resource. Use optional type callback to cast result."""
        logging.debug("%s(%s)::read()", self.__class__.__name__, self.resource)
        return self.manager.read(self.resource)

    def write(self, command):
        """Write to from VISA resource."""
        logging.debug("%s(%s)::write(command='%s')", self.__class__.__name__, self.resource, command)
        self.manager.write(self.resource, command)

    def query(self, command):
        """Query from VISA resource. Use optional type callback to cast result."""
        logging.debug("%s(%s)::query(command='%s')", self.__class__.__name__, self.resource, command)
        return self.manager.query(self.resource, command)

    def reset(self):
        commands = self.config.get('reset')
        if commands is None:
            return
        for command in commands:
            for k, v in command.items():
                k = 'set_{}'.format(k)
                getattr(self, k)(v)
                # HACK self.read() # free buffer -- Ugh! Some instruments might require this!
                time.sleep(self.reset_throttle)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
