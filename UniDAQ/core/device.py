
class Device(object):
    """Generic device.

    Keyword arguments:
    - manager -- device manager instance
    """

    def __init__(self, manager):
        self.manager = manager

    def read(self):
        """Read from to device."""
        raise NotImplementedError()

    def write(self, data):
        """Write from to device."""
        raise NotImplementedError()

class VisaDevice(object):
    """Generic VISA device.

    Keyword arguments:
    - manager -- VISA device manager instance
    """

    def __init__(self, manager, address):
        super(VisaDevice, self).__init__(manager)
        self.address = address
