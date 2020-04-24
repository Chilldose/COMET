import re, os

def do_get_light_config(value, TelegramResponder):
    """Light? - Gives you the possible light configurations"""
    for val in value.values():
        if val.strip() == "Light?":
            if "433MHz_Transiever" in TelegramResponder.main.default_values_dict["settings"]:
                TelegramResponder.answer += "All possible light configurations: \n\n"
                for light in TelegramResponder.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"].keys():
                    TelegramResponder.answer += '{}\n'.format(light)
            else:
                TelegramResponder.answer += "No transiever defined. Cannot do what you asked."


def do_send_RF_code(value, TelegramResponder):
    """Switch ConfigName <ON/OFF> - Turns light ON or OFF"""

    for val in value.values():
        light = re.findall(r"Switch\b\s*(\w*)", val)
        parts = val.split()
        if light and len(parts) > 2:  # Turn on or off if the command is correct
            if "433MHz_Transiever" in TelegramResponder.main.default_values_dict["settings"]:
                if light[0] in TelegramResponder.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"].keys():
                    onoff = 1 if parts[-1].upper() == "ON" else 0
                    path = os.path.normpath(TelegramResponder.main.default_values_dict["settings"]["433MHz_Transiever"]["path"])
                    for switch in TelegramResponder.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"][light[0]]:
                        code = switch
                        cmd = '{} {} {}'.format(path, code, onoff)
                        os.system(cmd)
                    if onoff:
                        old_light = TelegramResponder.current_light
                        TelegramResponder.current_light = light[0]
                    else:
                        old_light = None  # Because everything is off
                        TelegramResponder.current_light = None

                    # Switch the old one off, which are not included in the new one
                    if old_light:
                        path = os.path.normpath(TelegramResponder.main.default_values_dict["settings"]["433MHz_Transiever"]["path"])
                        onoff = 0
                        for switch in TelegramResponder.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"][
                            old_light]:
                            if switch not in TelegramResponder.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"][
                                TelegramResponder.current_light]:
                                code = switch
                                cmd = '{} {} {}'.format(path, code, onoff)
                                os.system(cmd)

                    TelegramResponder.answer += "Done and enjoy."
                else:
                    TelegramResponder.answer += "This light configuration is not defined."
            else:
                TelegramResponder.answer += "No transiever defined. Cannot do what you asked."

        elif light and len(parts) == 2:  # if no on or off is defined
            TelegramResponder.answer = {"CALLBACK": {"info": "Would you like to turn {} ON or OFF".format(light[0]),
                                        "keyboard": {"ON": "Switch {} ON".format(light[0]),
                                                     "OFF": "Switch {} OFF".format(light[0])},
                                        "arrangement": ["ON", "OFF"]}}
        elif light and len(parts) == 1:  # If just the switch command was send
            if "433MHz_Transiever" in TelegramResponder.main.default_values_dict["settings"]:
                keyboard = {}
                arrangement = []
                for light in TelegramResponder.main.default_values_dict["settings"]["433MHz_Transiever"]["Codes"]:
                    keyboard[light] = 'Switch {}'.format(light)
                    arrangement.append([light])
                TelegramResponder.answer = {"CALLBACK": {"info": "Possible light configurations:",
                                            "keyboard": keyboard,
                                            "arrangement": arrangement}}


def send_info(value, TelegramResponder):
    """Info - Sends some infos to the user"""
    # create an exporter instance, as an argument give it
    # the item you wish to export
    for val in value.values():  # Todo: add the temperature and humidity response
        if re.findall(r"Info\b\s*", val):
            text = "Temperature and Humidity: \n\n"

