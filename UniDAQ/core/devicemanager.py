from .device import VisaDevice
import visa

class DummyResource(object):
    """Fake resource for tests without hardware."""

    def __init__(self, address):
        self.address = address

    def read(self, command):
        print("::{}::read('{}')".format(self.__class__.__name__, command))
        return None

    def write(self, command):
        print("::{}::write('{}')".format(self.__class__.__name__, command))

    def query(self, command):
        print("::{}::query('{}')".format(self.__class__.__name__, command))
        return None

class VisaDeviceManager(object):
    """Generic VISA device manager.

    Keyword attributes:
    - backend -- VISA backend (default is 'default_backend')

    Example:
    >>> manager = VisaDeviceManager('@py')
    >>> manager.register_device('GPIB0::12::INSTR', 'SMU2410')
    >>> device = manager.get_device('SMU2410')
    >>> device.get_idn()
    """

    default_backend = '@py'
    """Default VISA backend."""

    def __init__(self, backend=None):
        self.devices = {}
        self.resource_manager = visa.ResourceManager(backend or self.default_backend)

    def get_device(self, name):
        return self.devices[name]

    def register_device(self, address, name, config=None):
        try: # HACK use dummy if resource unavailable
            resource = self.resource_manager.open_resource(address)
        except:
            resource = DummyResource(address)
        device = VisaDevice(resource, name, config)
        self.devices[name] = device
