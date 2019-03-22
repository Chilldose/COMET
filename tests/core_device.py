import json
import re
import sys, os

from UniDAQ.core.devicemanager import VisaDeviceManager

if __name__ == '__main__':

    manager = VisaDeviceManager()

    config = {
        'set_voltage': 'SOUR:VOLT:LEV {}',
        'set_fancy': 'FANCY:FUNC {} {} {} {}'
    }
    manager.register_device('USB0::0x1AB1::0x0588::DS1K00005888::INSTR', 'FancyDev', config)

    device = manager.get_device('FancyDev')
    device.get_idn()
    device.set_voltage(42)
    device.set_fancy("load", 42, 1.2, 3.5)

    with open(os.path.join(os.path.dirname(__file__), '2410_SMU.json')) as f:
        config = json.load(f)
    manager.register_device('USB0::0x1CD1::0x0588::DS1K00005888::INSTR', 'SMU2410', config)

    device = manager.get_device('SMU2410')
    device.get_idn()
    print("Available commands for device:", device.name)
    for method in device.__dict__:
        if re.match(r'^(set|get)_\w+$', method):
            print("->", method)
