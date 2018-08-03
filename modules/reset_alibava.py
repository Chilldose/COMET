# This file is for resetting the alibava module

from VisaConnectWizard import * # this module must be found either in same ordner or in lib directory of python
from time import sleep


def reset_alibava():
    vcw = VisaConnectWizard()
    vcw.show_instruments()

    print "Which resource is the relay?"
    device_number = raw_input("Number: ")

    if int(device_number) >= 0:
        vcw.baud_rate = 9600
        vcw.connect_to_instruments(False, [int(device_number)])

        print "Connected to device " + str(vcw.myInstruments[0])

        # Set pre-state
        ans = vcw.query(vcw.myInstruments[0], "Q")

        print str(ans)

        sleep(1)

        ans = vcw.query(vcw.myInstruments[0], "1")

        sleep(4)

        ans = vcw.query(vcw.myInstruments[0], "Q")

        vcw.close_connections()

def reset_alibava_full():

    vcw = VisaConnectWizard()
    vcw.show_instruments()

    print "Which resource is the relay?"
    device_number = raw_input("Number: ")

    vcw.baud_rate = 9600
    vcw.connect_to_instruments(False, [int(device_number)])

    print "Connected to device " + str(vcw.myInstruments[0])

    run = True

    # Set pre-state
    ans = vcw.query(vcw.myInstruments[0], "Q")

    while run:
        print "Reset relay?"
        inp = raw_input("Yes?: ")
        if inp == "Yes":

            ans = vcw.query(vcw.myInstruments[0], "Q")
            print str(ans)

            inp = raw_input("Yes?: ")

            ans = vcw.query(vcw.myInstruments[0], "1")
            print str(ans)

            inp = raw_input("Yes?: ")

            ans = vcw.query(vcw.myInstruments[0], "Q")
            print str(ans)



        elif inp == "close":
            run = False

    vcw.close_connections()

