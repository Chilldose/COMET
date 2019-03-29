import os
import glob
import yaml

class DeviceLib(object):
    """Represents a device lib configuration."""

    def __init__(self):
        self.devices = {}

    def __getitem__(self, key):
        return self.devices[key]

    def items(self):
        return self.devices.items()

    def load(self, path):
        """Load device lib from filesystem."""
        self.devices = {}
        for filename in glob.glob(os.path.join(path, '*.yml')):
            with open(filename, 'r') as f:
                config = yaml.safe_load(f)
                name = config['Device_name']
                self.devices[name] = config
