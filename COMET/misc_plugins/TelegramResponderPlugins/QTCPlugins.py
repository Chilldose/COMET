import re


def do_QTC_Status(value, TelegramResponder):  #
    """Status - Gives back the QTC Status"""
    for val in value.values():
        if re.findall(r"Status\b", val):
            text = "Current QTC status: \n\n"
            text += "Measurement running: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"][
                    "Measurement_running"
                ]
            )
            text += "Measurement progress: {} % \n".format(
                TelegramResponder.main.default_values_dict["settings"]["progress"]
            )
            text += "Current Bias voltage: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"].get(
                    "bias_voltage", 0
                )
            )
            text += "Start time: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"]["Start_time"]
            )
            text += "Est. end time: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"]["End_time"]
            )
            text += "Single Strip scan time: {} s\n".format(
                TelegramResponder.main.default_values_dict["settings"][
                    "strip_scan_time"
                ]
            )
            text += "Bad Strips: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"]["Bad_strips"]
            )
            text += "Current filename: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"][
                    "Current_filename"
                ]
            )
            text += "Current operator: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"][
                    "Current_operator"
                ]
            )
            text += "Sensor type: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"]["Current_sensor"]
            )
            text += "Project: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"][
                    "Current_project"
                ]
            )
            text += "Table moving: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"][
                    "table_is_moving"
                ]
            )
            text += "Current Switching: {} \n".format(
                TelegramResponder.main.default_values_dict["settings"][
                    "current_switching"
                ]
            )
            TelegramResponder.answer += text
