import os
import re

class PadFile(object):
    """Represents a silicon pad file."""

    regex_pair = re.compile(r'^([^\:]+)\s*:\s*(.*)$')
    regex_strip = re.compile(r'^strip\s+')

    def __init__(self):
        self.reset()

    def reset(self):
        self.header = []
        self.reference_pads = []
        self.additional_params = {}
        self.data = []

    def __getitem__(self, key):
        return self.__dict__[key]

    def items(self):
        return self.__dict__.items()

    def load(self, filename):
        """Loads a pad file from filesystem."""
        self.reset()
        # Parser mode
        parse_header = True
        # Parse file
        with open(os.path.join(filename), "r") as f:
            for line in f:
                # Collect raw header lines TODO is this required?
                if parse_header:
                    self.header.append(line)
                    # Switch parser mode if 'strip x y z' reached'
                    if self.regex_strip.match(line):
                        parse_header = False
                        continue
                    line = line.strip()
                    result = self.regex_pair.match(line)
                    if result:
                        key = result.group(1)
                        value = result.group(2)
                        # Found reference pad
                        if key == 'reference pad':
                            self.reference_pads.append(int(value))
                        # Found additional parameter
                        else:
                            self.additional_params[key] = value
                else:
                    line = line.strip()
                    strip, x, y, z = line.split()
                    self.data.append([int(strip), float(x), float(y), float(z)])
