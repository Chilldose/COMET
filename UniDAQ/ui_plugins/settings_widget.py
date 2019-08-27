# This is some kind of widget for the settings

class settings_widget(object):
    """Functions which are needed for storing an acquiring settings values."""

    def __init__(self, *args, **kwargs):
        #self.measurements = None
        #self.variables = None
        pass

    def get_all_settings(self):
            '''This function gets all settings'''

            # Just a list of all settings which should be included
            settings_list = self.measurements
            settings_dict = {}

            for setting in settings_list:
                settings_to_write = self.get_specific_settings_value(str(setting) + "_measure")
                if settings_to_write:
                    settings_dict.update({str(setting + "_measure"): settings_to_write})

            # Special settings
            settings_to_write = self.get_specific_settings_value("IVCV_refinement")
            if settings_to_write:
                settings_dict.update({"IVCV_refinement": settings_to_write})

            return settings_dict

    def get_specific_settings_value(self, data_storage):
            '''This returns the values of a specific setting'''
            return self.variables.default_values_dict["settings"].get(str(data_storage), [False, 0, 0, 0])

    def load_new_values(self, data_storage, checkbox, first_value, second_value, third_value):
        '''This functions loads the  the values into the state machine'''
        list = [checkbox.isChecked(), first_value.value(), second_value.value(), third_value.value()]
        self.variables.default_values_dict["settings"][str(data_storage)] = list