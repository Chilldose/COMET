import os
import glob

from .padfile import PadFile

# TODO get some light on naming

class Setup(object):
    """Represents a measurements setup."""

    def __init__(self):
        self.configs = {}
        self.Pad_files = {}

    def load(self, path):
        """Load setup from filesystem."""
        self.load_configs(path)
        self.load_pad_files(path)

    def load_configs(self, path):
        """Load setup configs from filesystem."""
        self.configs = {}
        for filename in glob.glob(os.path.join(path, 'config', '*.yml')):
            with open(filename, "r") as f:
                config = yaml.safe_load(f)
                name = config['Settings_name']
                self.configs[name] = config

    def load_pad_files(self, path):
        self.Pad_files = {}
        for filename in glob.glob(os.path.join(path, 'Pad_files', '*', '*.txt')):
            pad_file = PadFile()
            pad_file.load(filename)
            key = os.path.splitext(os.path.basename(filename))[0]
            self.Pad_files[key] = pad_file
