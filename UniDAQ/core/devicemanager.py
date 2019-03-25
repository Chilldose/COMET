from .device import VisaDevice
import visa

class VisaDeviceManager(object):
    """Generic VISA device manager.

    Keyword attributes:
    - backend -- VISA backend (default is 'default_backend')

    Example:
    >>> manager = VisaDeviceManager('@sim')
    >>> config = {'get_idn': '?IDN'}
    >>> manager.register_device('MyDevice', 'ASRL1::INSTR', config)
    >>> device = manager.get_device('MyDevice')
    >>> device.get_idn()
    'LSG Serial #1234'
    """

    default_backend = '@py'
    """Default VISA backend."""

    read_termination = '\n'
    """Read termination sequence."""

    def __init__(self, backend=None):
        self.devices = {}
        self.resource_manager = visa.ResourceManager(backend or self.default_backend)

    def get_device(self, name):
        """Returns VISA device or None if no such device exists."""
        return self.devices.get(name)

    def register_device(self, name, resource_name, config=None):
        """Register a new VISA device."""
        resource = self.resource_manager.open_resource(resource_name,read_termination=self.read_termination)
        device = VisaDevice(name, resource, config)
        self.devices[name] = device

if __name__ == '__main__':
    import doctest
    doctest.testmod()
