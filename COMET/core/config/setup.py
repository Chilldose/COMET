import os
import glob
import yaml

from .padfile import PadFile

# TODO shed some light on naming

class Setup(object):
    """Represents a measurements setup."""

    def __init__(self):
        self.name = None
        self.config = {}
        self.Pad_files = {}

    def __getitem__(self, key):
        """Provided for convenience."""
        return self.__dict__[key]

    def __iter__(self):
        """Provided for convenience."""
        return iter(self.__dict__)

    iter = __iter__

    def items(self):
        """Provided for convenience."""
        return self.__dict__.items()

    def get(self, key, default=None):
        """Provided for convenience."""
        return self.__dict__.get(key, default)

    def load(self, path):
        """Load setup from filesystem."""
        self.name = os.path.basename(path)
        self.load_config(path)
        self.load_pad_files(path)

    def load_config(self, path):
        """Load setup config from filesystem."""
        self.config = {}
        for filename in glob.glob(os.path.join(path, 'config', '*.yml')):
            with open(filename, "r") as f:
                config = yaml.safe_load(f)
                name = config['Settings_name']
                self.config[name] = config

    def load_pad_files(self, path):
        self.Pad_files = {}
        for filename in glob.glob(os.path.join(path, 'Pad_files', '*', '*.txt')):
            project = os.path.basename(os.path.dirname(filename))
            if project not in self.Pad_files:
                self.Pad_files[project] = {}
            sensor = os.path.splitext(os.path.basename(filename))[0]
            pad_file = PadFile()
            pad_file.load(filename)
            self.Pad_files[project][sensor] = pad_file
