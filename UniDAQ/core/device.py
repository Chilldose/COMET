from types import MethodType
import re

class GenericDevice(object):
    """Generic device, inherit to implement device drivers.

    Keyword arguments:
    - name -- device manager instance
    """

    def __init__(self, name):
        self.name = name

    def read(self, command):
        """Read from to device."""
        raise NotImplementedError()

    def write(self, command):
        """Write from to device."""
        raise NotImplementedError()

    def query(self, command):
        """Query (write and read) from device."""
        raise NotImplementedError()

class ConfDevice(GenericDevice):
    """Generic configurable device, inherit to implement device drivers.

    Keyword arguments:
    - name -- device manager instance
    - config -- device configuration dictionary

    Example:
    >>> config = {'set_voltage': 'SOUR:VOLT:LEV {:f}'}
    >>> device = ConfDevice('MyDevice', config)
    >>> device.set_voltage(42.0)
    """

    default_config = {}
    """Default configuration, can be overwritten by user configuration."""

    def __init__(self, name, config=None):
        super(ConfDevice, self).__init__(name)
        # Setup configuration
        self.__config = dict(self.default_config)
        self.__config.update(config or {})
        # Register methods from configuration
        for key, value in self.__config.items():
            if re.match(r'^get_\w+$', key):
                self.__register(self.query, key, value)
            if re.match(r'^set_\w+$', key):
                self.__register(self.write, key, value)

    def __register(self, method, name, command):
        """Registers get/set methods loaded from config."""
        def f(self, *args, **kwargs):
            return method(command.format(*args, **kwargs))
        setattr(self, name, MethodType(f, self))

    @property
    def config(self):
        """Returns device configuration."""
        return self.__config


class VisaDevice(ConfDevice):
    """Generic VISA device driver.

    Keyword arguments:
    - name -- device manager instance
    - resource -- VISA resource assigned to device
    - config -- device configuration dictionary

    Example:
    >>> rm = visa.ResourceManager()
    >>> resource = rm.open_resource('...')
    >>> config = {'set_voltage': 'SOUR:VOLT:LEV {:f}'}
    >>> device = VisaDevice(resource, 'MyDevice', config)
    >>> device.get_idn()
    'MY INSTRUMENT IC. MODEL 1234'
    >>> device.set_voltage(42.0)
    """

    default_config = {
        'get_idn': '*IDN?'
    }
    """Default VISA resource configuration, can be overwritten by user configuration."""

    def __init__(self, resource, name, config=None):
        super(VisaDevice, self).__init__(name, config)
        self.__resource = resource

    @property
    def resource(self):
        """Returns VISA resource."""
        return self.__resource

    def read(self, command):
        """Read from VISA resource."""
        return self.resource.read(command)

    def write(self, command):
        """Write to from VISA resource."""
        self.resource.write(command)

    def query(self, command):
        """Query from VISA resource."""
        return self.resource.query(command)
