# This module makes the program interact with the command line

import cmd, types
from threading import Thread


class DAQShell(cmd.Cmd):
    """This class is for the commandline interface of the DAQ software.
    Every function stated with 'do_' will be executable in the unidaq shell.
    If you want to add additional functions, you can pass an callable object to
    self.add_cmd_command(obj) and you also can access it in the shell.
    Use list to show all available commands"""
    intro = '\n\nWelcome to the UniDAQ Shell.   \n' \
            'Type help or ? to list commands concerning generall help.\n' \
            'Type list to list all commands within the UniDAQ framework. \n' \
            'This was programmed by Dominic Bloech during his Phd thesis at HEPHY Vienna \n' \
            'at a cloudy day while his student measured some sensors.'
    prompt = '(UniDAQ) '
    file = None
    global get_shell

    def __init__(self):
        """Initiates the cmd line interface etc"""
        self.list_of_objects = []
        self.list_of_objects_str = []

    def get_shell(self):
        """Returns the shell item"""
        return self

    def add_cmd_command(self, object):
        """This function adds an object to the cmd prompt by calling the object with the args and kwargs"""
        self.list_of_objects.append(object)
        self.list_of_objects_str.append(object.__name__)
        setattr(self, "do_"+str(object.__name__), object)
        #new_class_member = getattr(self, "do_"+str(object.__name__))
        #new_class_member = types.MethodType(object, None, self)

    def do_list(self, arg=None):
        """Just calls do_UniDAQ_functions"""
        self.do_UniDAQ_functions()


    def do_UniDAQ_functions(self, arg=None):
        """This function writes back all functions added for use in the UniDAQ framework"""
        print "All functions provided by the UniDAQ framework:"
        for i in self.list_of_objects:
            print str(i.__name__)
        print "=================================================="
        print "For more information to the methods type help <topic>"

    def start(self):
        "Starts the actual thread in which the shell is running"
        cmd.Cmd.__init__(self)
        self.t = Thread(target=self.start_shell)
        self.t.setDaemon(True)
        self.t.start()

    def start_shell(self):
        """This starts the shell"""
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            print "^C"

    def do_bye(self, arg):
        'Stops the UniDAQ shell'
        print('Thank you for using UniDAQ')
        return True

    def precmd(self, line):
        """Just the pre command"""
        print "====================================="
        return line

    def postcmd(self, retval, line):
        """Just the post command"""
        if "list" not in line and line.split()[0] in self.list_of_objects_str:
            try:
                print "Executed command:".ljust(30) + str(line)
                print "Type of return value: ".ljust(30) + str(type(retval))
                print str(retval)
            except:
                pass
        print "====================================="
        return False

