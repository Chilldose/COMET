"""This class responds to Telegram messages. Send by a Client"""
import re
import pyqtgraph as pg
#import pyqtgraph.exporters #This does not work currently
import os
try:
    from .PyqtgraphExporter import PQG_ImageExporter
except:
    pass

class TelegramBotResponder:

    def __init__(self, parent_class):
        """
        :param parent_class: the GUI class
        """

        self.main = parent_class
        self.answer = ""
        self.RPI_modules = False
        self.current_light = None # The current light config

        # Load Raspberry modules
        try:
            self.RPI_modules = True
        except:
            self.RPI_modules = False

    def run(self, action, value):
        """
        :param action: Must be TelegramBot, otherwise the message will not be processed
        :param value: The value to be processed. It has to be a dict, with keys beeing the ID and value the message from the ID
        :return: str response
        """
        if action == "TelegramBot":
            self.answer = "" # The final answer
            try:
                self.respond_to_PING(value)
                self.QTC_Status(value)
                self.give_help(value)
                self.which_plots(value)
                self.error_log(value)
                self.get_light_config(value)
                self.send_RF_code(value)

                # These function alter the data type of answer!!
                self.send_plot(value)

                if not self.answer:
                    self.answer = "Command not supported by COMET, please give a valid command. Type 'Help' for all commands."
            except Exception as err:
                self.main.log.critical("Could not understand query {} from TCP Client. Errorcode: {}".format(value, err))
                return "Could not understand query {} from TCP Client. Errorcode: {}".format(value, err)
            return self.answer
        else:
            return None

    def which_plots(self, value):
        """Returns a list of possible plots"""
        for val in value.values():
            if re.findall(r"Plots\b\?", val):
                self.answer += "The possible plots to show are: \n\n"
                self.answer += "\n".join(self.main.plot_objs.keys())
                self.answer += "\n\nYou can access them by typing 'Plot <xyz>'"

    def get_light_config(self, value):
        """Gives you all light configurations"""
        for val in value.values():
            if val.strip() == "Light?":
                if "433MHz_Transiever" in self.main.default_values_dict["settings"]:
                    self.answer += "All possible light configurations: \n\n"
                    for light in self.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"].keys():
                        self.answer += '{}\n'.format(light)
                else:
                    self.answer += "No transiever defined. Cannot do what you asked."


    def send_RF_code(self, value):
        """This function is only possible if the system is a raspberry pi. It sends a 433MHz code.
        It uses the 433MHz libs from github for transmitting"""

        for val in value.values():
            light = re.findall(r"Switch\b\s*(\w*)", val)
            parts = val.split()
            if light and len(parts)>2: # Turn on or off if the command is correct
                if "433MHz_Transiever" in self.main.default_values_dict["settings"]:
                    if light[0] in self.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"].keys():
                        onoff = 1 if parts[-1].upper() == "ON" else 0
                        path = os.path.normpath(self.main.default_values_dict["settings"]["433MHz_Transiever"]["path"])
                        for switch in self.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"][light[0]]:
                            code = switch
                            cmd = '{} {} {}'.format(path, code, onoff)
                            os.system(cmd)
                        if onoff:
                            old_light = self.current_light
                            self.current_light = light[0]
                        else:
                            old_light = None # Because everything is off
                            self.current_light = None

                        # Switch the old one off, which are not included in the new one
                        if old_light:
                            path = os.path.normpath(self.main.default_values_dict["settings"]["433MHz_Transiever"]["path"])
                            onoff = 0
                            for switch in self.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"][old_light]:
                                if switch not in self.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"][self.current_light]:
                                    code = switch
                                    cmd = '{} {} {}'.format(path, code, onoff)
                                    os.system(cmd)

                        self.answer += "Done and enjoy."
                    else:
                        self.answer += "This light configuration is not defined."
                else:
                    self.answer += "No transiever defined. Cannot do what you asked."

            elif light and len(parts) == 2: # if no on or off is defined
                self.answer = {"CALLBACK": {"info": "Would you like to turn {} ON or OFF".format(light[0]),
                                            "keyboard": {"ON": "Switch {} ON".format(light[0]), "OFF": "Switch {} OFF".format(light[0])},
                                            "arrangement": ["ON", "OFF"]}}
            elif light and len(parts) == 1: # If just the switch command was send
                if "433MHz_Transiever" in self.main.default_values_dict["settings"]:
                    keyboard = {}
                    arrangement = []
                    for light in self.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"]:
                        keyboard[light] = 'Switch {}'.format(light)
                        arrangement.append([light])
                    self.answer = {"CALLBACK": {"info": "Possible light configurations:",
                                                "keyboard": keyboard,
                                                "arrangement": arrangement}}



    def send_plot(self, value):
        """Saves a plot as png and returns the path to this plot to the bot"""
        # create an exporter instance, as an argument give it
        # the item you wish to export
        for val in value.values():
            plot = re.findall(r"Plot\b\s*(\w*)", val)
            if plot:
                if plot[0] in self.main.plot_objs.keys():
                    plt = self.main.plot_objs[plot[0]]
                    try:
                        plt = plt.plotItem
                    except:
                        pass
                    try:
                        #exporter = pg.exporters.ImageExporter(plt) # Original exporter but he has a bug. --> Selfwritten one from stackoverflow
                        exporter = PQG_ImageExporter(plt) # This may fail
                        # set export parameters if needed
                        exporter.parameters()['width'] = 1920  # (note this also affects height parameter)
                        # save to file
                        filepath = os.path.join(os.path.dirname(__file__), "__temp__")
                        if os.mkdir(filepath) if not os.path.isdir(filepath) else True:
                            for file in  os.listdir(filepath):
                                os.remove(os.path.join(filepath, file))
                            exporter.export(os.path.join(filepath, '{}_plot.jpg'.format(plot[0])))

                            self.answer = {"PLOT": str(os.path.join(filepath, '{}_plot.jpg'.format(plot[0])))}

                    except Exception as err:
                        self.main.log.error("Export of png for plot {} did not work. Error: {}".format(plot[0], err))
                else:
                    self.answer += "The plot {} is not a possible plot. Type: 'Plots?' to see valid plots."

    def give_help(self,value):
        """Returns all commands"""
        for val in value.values():
            if re.findall(r"Help\b", val) or re.findall(r"help\b", val):
                self.answer += "Status - Gives information about the QTC status\n" \
                               "Help - Gives you a list of all commands \n" \
                               "Plots? - Gives you a list of all possible plots \n" \
                               "Plot <xyz> - Plots you a certain plot \n" \
                               "Error # - Gives you the last # entries in the event log \n" \
                               "ping - Just returns success \n" \
                               "All possible commands for RPI:" \
                               "Light? - Gives you the possible light configurations \n" \
                               "Switch ConfigName <ON/OFF> - Turns light ON or OFF "

    def error_log(self, value):
        """This function returns the error log. """
        for val in value.values():
            if re.findall(r"Error\b", val) or re.findall(r"errors\b", val):
                errors = self.main.event_loop_thread.error_log
                num = val.split()
                if len(num)>1:
                    for error in errors[-int(num[-1]):]:
                        self.answer += ":\n ".join(error) + "\n\n"
                else:
                    self.answer += "The event log printer must be called with a number! Like 'Error 5'. This will give " \
                                   "you the last 5 entries in the event log."



    def QTC_Status(self, value):
        """Gives back the QTC Status"""
        for val in value.values():
            if re.findall(r"Status\b", val):
                text = "Current QTC status: \n\n"
                text += "Measurement running: {} \n".format(self.main.default_values_dict["settings"]["Measurement_running"])
                text += "Measurement progress: {} % \n".format(self.main.default_values_dict["settings"]["progress"])
                text += "Current Bias voltage: {} \n".format(self.main.default_values_dict["settings"].get("bias_voltage", 0))
                text += "Start time: {} \n".format(self.main.default_values_dict["settings"]["Start_time"])
                text += "Est. end time: {} \n".format(self.main.default_values_dict["settings"]["End_time"])
                text += "Single Strip scan time: {} s\n".format(self.main.default_values_dict["settings"]["strip_scan_time"])
                text += "Bad Strips: {} \n".format(self.main.default_values_dict["settings"]["Bad_strips"])
                text += "Current filename: {} \n".format(self.main.default_values_dict["settings"]["Current_filename"])
                text += "Current operator: {} \n".format(self.main.default_values_dict["settings"]["Current_operator"])
                text += "Sensor type: {} \n".format(self.main.default_values_dict["settings"]["Current_sensor"])
                text += "Project: {} \n".format(self.main.default_values_dict["settings"]["Current_project"])
                text += "Table moving: {} \n".format(self.main.default_values_dict["settings"]["table_is_moving"])
                text += "Current Switching: {} \n".format(self.main.default_values_dict["settings"]["current_switching"])
                self.answer += text


    def respond_to_PING(self, value):
        for val in value.values():
            if str(val).strip().lower() == "ping":
                self.answer = "Success \n\n"