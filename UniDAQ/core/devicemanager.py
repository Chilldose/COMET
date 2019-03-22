
class DeviceManager(object):
    """Generic device manager."""

    def __init__(self):
        self.devices = {}

    def getDevice(self, name):
        return self.devices[name]
