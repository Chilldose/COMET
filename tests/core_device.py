import json
import logging
import re
import sys, os

from UniDAQ.VisaConnectWizard import VisaConnectWizard as VisaDeviceManager
from UniDAQ.core.device import Device

if __name__ == '__main__':

    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger('pyvisa').setLevel(logging.INFO)

    manager = VisaDeviceManager(backend='@sim')

    config = {
        'Visa_Resource': manager.rm.open_resource('ASRL1::INSTR'),
        'get_idn': '?IDN',
        'set_offset': '!OFF {:.2f}',
        'get_offset': '?OFF',
        'reset': [
            {'offset': 2.0},
            {'offset': 3.0},
        ]
    }

    device = Device(manager, config)
    device.reset()

    idn = device.get_idn().strip()
    print("idn:", idn)

    value = float(device.get_offset())
    print("offset:", value)

    device.set_offset(4.2)
    device.read() # free buffer!!

    value = float(device.get_offset())
    print("offset:", value)
    # device.set_fancy("load", 42, 1.2, 3.5)

    print("Available commands for device:", device.config.get('Visa_Resource'))
    for method in device.__dict__:
        if re.match(r'^(set|get)_\w+$', method):
            print("->", method)
