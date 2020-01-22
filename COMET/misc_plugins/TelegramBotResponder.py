"""This class responds to Telegram messages. Send by a Client"""
import re

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

                if not self.answer:
                    self.answer = "The QTC does not support your command, please give a valid command. Type 'QTC Help' for all commands."
            except Exception as err:
                self.main.log.critical("Could not understand query {} from TCP Client. Errorcode: {}".format(value, err))
                return "Could not understand query {} from TCP Client. Errorcode: {}".format(value, err)
            return self.answer
        else:
            return None

    def give_help(self,value):
        """Returns all commands"""
        for val in value.values():
            if re.findall(r"QTC\s*Help", val) or re.findall(r"\?", val):
                self.answer += "QTC Status - Gives information about the QTC status\n" \
                               "QTC Help - Gives you a list of all commands \n" \
                               "ping - Just returns success \n"

    def QTC_Status(self, value):
        """Gives back the QTC Status"""
        for val in value.values():
            if re.findall(r"QTC\s*Status", val):
                text = "Current QTC status: \n\n"
                text += "Measurement running: {} \n".format(self.main.default_values_dict["settings"]["Measurement_running"])
                text += "Measurement progress: {} % \n".format(self.main.default_values_dict["settings"]["progress"])
                text += "Start time: {} \n".format(self.main.default_values_dict["settings"]["Start_time"])
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