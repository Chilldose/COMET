# This file is for checking the IDN of devices

import visa
from VisaConnectWizard import *

vcw = VisaConnectWizard()

vcw.show_instruments()

print "Select resource"
device_number = raw_input("Number: ")

vcw.connect_to_instruments(False, [int(device_number)])
#IDN = vcw.verify_ID(int(0))
#print IDN
#print vcw.myInstruments[0]

while True:
    query = raw_input("Command: ")
    if query == "stop":
        break
    reply = vcw.query(vcw.myInstruments[0], str(query))
    print str(reply)


vcw.close_connections()

#print "The IDN of this device is: " + IDN


