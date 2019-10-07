import os
import glob
import yaml

class DeviceLib(object):
    """Represents a device lib configuration."""

    def __init__(self):
        self.devices = {}

    def __getitem__(self, key):
        """Provided for convenience."""
        return self.devices[key]

    def __iter__(self):
        """Provided for convenience."""
        return iter(self.devices)

    iter = __iter__

    def items(self):
        """Provided for convenience."""
        return self.devices.items()

    def get(self, key, default=None):
        """Provided for convenience."""
        return self.devices.get(key, default)

    def load(self, path):
        """Load device lib from filesystem."""
        self.devices = {}
        for filename in glob.glob(os.path.join(path, '*.yml')):
            with open(filename, 'r') as f:
                config = yaml.safe_load(f)
                name = config['Device_name']
                self.devices[name] = config
