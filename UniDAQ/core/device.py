from types import MethodType
import re

class GenericDevice(object):
    """Generic device, inherit to implement device drivers.

    Keyword arguments:
    - name -- device name

    Example:
    >>> class MyDevice(GenericDevice):
    ...     def __init__(self, name):
    ...         super(MyDevice, self).__init__(name)
    ...         self.memory = {}
    ...     def read(self, key):
    ...         return self.memory.get(key)
    ...     def write(self, key, value):
    ...         self.memory[key] = value
    >>> device = MyDevice('MyDevice')
    >>> device.name
    'MyDevice'
    >>> device.write('foo', 42)
    >>> device.read('foo')
    42
    """

    def __init__(self, name):
        self.__name = name

    @property
    def name(self):
        """Returns device name."""
        return self.__name

    def read(self, *args, **kwargs):
        """Read from to device."""
        raise NotImplementedError()

    def write(self, *args, **kwargs):
        """Write from to device."""
        raise NotImplementedError()

    def query(self, *args, **kwargs):
        """Query (write and read) from device."""
        raise NotImplementedError()

class ConfDevice(GenericDevice):
    """Generic configurable device, inherit to implement device drivers.

    Keyword arguments:
    - name -- device manager instance
    - config -- device configuration dictionary

    Example:
    >>> config = {'get_idn': '?IDN', 'foo': 42}
    >>> device = ConfDevice('MyDevice', config)
    >>> device.name
    'MyDevice'
    >>> device.config.get('get_idn')
    '?IDN'
    >>> device.config.get('foo')
    42
    """

    default_config = {}
    """Default configuration, can be overwritten by user configuration."""

    def __init__(self, name, config=None):
        super(ConfDevice, self).__init__(name)
        # Setup configuration
        self.__config = self.default_config.copy()
        if isinstance(config, dict):
            self.__config.update(config)
        # Register methods from configuration
        for key, value in self.__config.items():
            # Register getters
            if re.match(r'^get_\w+$', key):
                self.__register(self.query, key, value)
            # Register setters
            if re.match(r'^set_\w+$', key):
                self.__register(self.query, key, value)

    def __register(self, method, name, command):
        """Registers get/set methods loaded from config."""
        def f(self, *args, **kwargs):
            return method(command.format(*args, **kwargs))
        setattr(self, name, MethodType(f, self))

    @property
    def config(self):
        """Returns device configuration dictionary."""
        return self.__config


class VisaDevice(ConfDevice):
    """Generic VISA device driver.

    Keyword arguments:
    - name -- device manager instance
    - resource -- VISA resource assigned to device
    - config -- device configuration dictionary

    Example:
    >>> import visa
    >>> rm = visa.ResourceManager('@sim')
    >>> resource = rm.open_resource('ASRL1::INSTR', read_termination='\\n')
    >>> config = {'get_idn': '?IDN', 'set_frequency': '!FREQ {:f}', 'get_frequency': '?FREQ'}
    >>> device = VisaDevice('MyDevice', resource, config)
    >>> device.get_idn()
    'LSG Serial #1234'
    >>> device.set_frequency(42.0)
    'OK'
    >>> device.get_frequency()
    '42.00'
    """

    default_config = {
        'get_idn': '*IDN?'
    }
    """Default VISA resource configuration, can be overwritten by user configuration."""

    def __init__(self, name, resource, config=None):
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


if __name__ == '__main__':
    import doctest
    doctest.testmod()
