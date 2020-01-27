"""This class responds to Telegram messages. Send by a Client"""
import re
import pyqtgraph as pg
import pyqtgraph.exporters
import os
from .PyqtgraphExporter import PQG_ImageExporter

class TelegramBotResponder:

    def __init__(self, parent_class):
        """
        :param parent_class: the GUI class
        """

        self.main = parent_class
        self.answer = ""

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
                        exporter = PQG_ImageExporter(plt)
                        # set export parameters if needed
                        exporter.parameters()['width'] = 1920  # (note this also affects height parameter)
                        #exporter.parameters()['height'] = 1080  # (note this also affects height parameter)
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
                               "ping - Just returns success \n"

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
                text += "Current Bias voltage: {} % \n".format(self.main.default_values_dict["settings"]["bias_voltage"])
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