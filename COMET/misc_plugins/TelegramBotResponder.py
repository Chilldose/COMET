"""This class responds to Telegram messages. Send by a Client"""
import re
#import pyqtgraph.exporters #This does not work currently
import os
import importlib
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
        self.function_helps = {} # The help text of all available functions
        self.load_plugins()


    def run(self, action, value):
        """
        :param action: Must be TelegramBot, otherwise the message will not be processed
        :param value: The value to be processed. It has to be a dict, with keys beeing the ID and value the message from the ID
        :return: str response
        """
        if action == "TelegramBot":
            self.answer = "" # The final answer
            try:
                for func in self.function_helps:
                    getattr(self, func)(value, self)
                if not self.answer:
                    self.answer = "Command not supported by COMET, please give a valid command. Type 'Help' for all commands."
            except Exception as err:
                self.main.log.critical("Could not understand query {} from TCP Client. Errorcode: {}".format(value, err))
                return "Could not understand query {} from TCP Client. Errorcode: {}".format(value, err)
            return self.answer
        else:
            return None

    def load_plugins(self):
        """Loads the list of plugins via import loaded and makes them members of the telegramResponder"""

        # Add the generall functions from this script
        members = dir(self)
        for mem in members:
            if "do_" in mem:
                try:
                    self.function_helps[mem] = getattr(self, mem).__doc__
                except:
                    pass

        # Load the other plugins make them a member and add the doc string
        if "TelegramResponderPlugins" in self.main.framework_variables["Configs"]["config"]["settings"]:
            for plugin in self.main.framework_variables["Configs"]["config"]["settings"]["TelegramResponderPlugins"]:
                try:
                    module = importlib.import_module("COMET.misc_plugins.TelegramResponderPlugins.{}".format(plugin))
                    for members in dir(module):
                        if "do_" in members:
                            setattr(self, members, getattr(module, members))
                            self.function_helps[members] = getattr(self, members).__doc__
                except:
                    pass

    def do_which_plots(self, value, *args):
        """Plots? - Gives you a list of all possible plots """
        for val in value.values():
            if re.findall(r"Plots\b\?", val):
                self.answer += "The possible plots to show are: \n\n"
                self.answer += "\n".join(self.main.meas_data.keys())
                self.answer += "\n\nYou can access them by typing 'Plot <xyz>'"

    def do_send_plot_buttons(self, value, *args):
        """Sends a callback keyboard for all possible plots"""
        for val in value.values():
            if val.strip().lower() == "plot":
                keyboard = {}
                arrangement = []
                for plots in self.main.meas_data.keys():
                    keyboard[plots] = 'Plot {}'.format(plots)
                    arrangement.append([plots])
                self.answer = {"CALLBACK": {"info": "Choose a plot you want to see:",
                                                         "keyboard": keyboard,
                                                         "arrangement": arrangement}}

    def do_send_plot(self, value, *args):
        """Plot <xyz> - Plots you a certain plot"""
        # create an exporter instance, as an argument give it
        # the item you wish to export
        for val in value.values():
            plot = re.findall(r"Plot\b\s*(\w*)", val)
            if plot:
                if plot[0] in self.main.meas_data.keys():
                    plt_data = self.main.meas_data[plot[0]]
                    exporter = self.main.default_values_dict['settings'].get('Telegram_exporter', 'matplotlib')

                    # Matplotlib exporter
                    if exporter == "matplotlib":
                        try:
                            import matplotlib
                            import matplotlib.pyplot as plt
                            from matplotlib import dates

                            # Try to get the x and y axis
                            axis = self.main.plot_objs_axis.get(plot[0], ("X-Axis", "Y-Axis"))

                            fig, ax = plt.subplots()
                            ax.plot(plt_data[0], plt_data[1])
                            ax.set(xlabel=axis[0], ylabel=axis[1],
                                   title=plot[0])
                            ax.grid()

                            time = True if "time" in axis[0] else False
                            if time and plt_data[0]:
                                # matplotlib date format object
                                hfmt = dates.DateFormatter('%d/%m %H:%M')
                                ax.xaxis.set_major_formatter(hfmt)

                            # save to file
                            filepath = os.path.join(os.path.dirname(__file__), "__temp__")
                            if os.mkdir(filepath) if not os.path.isdir(filepath) else True:
                                for file in os.listdir(filepath):
                                    os.remove(os.path.join(filepath, file))
                            fig.savefig(os.path.join(filepath, '{}_plot.png'.format(plot[0])))
                            self.answer = {"PLOT": str(os.path.join(filepath, '{}_plot.png'.format(plot[0])))}

                        except ImportError:
                            self.main.log.error("It seem matplotlib is not installed, no plotting can be done.")
                            self.answer = "It seem matplotlib is not installed, no plotting can be done."
                        except Exception as err:
                            self.main.log.error("An error occured while plotting: Error {}".format(err))
                            self.answer = "An error occured while plotting: Error {}".format(err)

                    elif exporter == "pyqtgraph":
                        #PYqtexporter
                        try:
                            plt = self.main.plot_objs[plot[0]]
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
                    self.answer += "The plot '{}' is not a possible plot. Type: 'Plots?' to see valid plots.".format(val)

    def do_give_help(self,value, *args):
        """Help - Gives you a list of all commands"""
        for val in value.values():
            if re.findall(r"Help\b", val) or re.findall(r"help\b", val):
                for help in self.function_helps.values():
                    self.answer += "{}\n".format(help)

    def do_error_log(self, value, *args):
        """Error # - Gives you the last # entries in the event log"""
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

    def do_respond_to_PING(self, value, *args):
        """ping - Just returns success"""
        for val in value.values():
            if str(val).strip().lower() == "ping":
                self.answer = "Success \n\n"

    def do_update_code_from_repo(self, value, *args):
        """Update - Tries to update the code from a remote repo"""
        for val in value.values():
            if re.findall(r"Update\b", val):
                try:
                    import git
                except:
                    self.answer = "Could not import git module, please install 'gitpython' first on the machine."
                    return
                fetch_out = ""
                pull_out = ""
                try:
                    repo = git.Repo()
                    o = repo.remotes.origin
                    fetch_out = o.fetch()
                    pull_out = o.pull()
                    self.answer = "Code successfully updated!"
                except: self.answer = "Could not pull from remote repo. No update done. \n" \
                                      "FETCH MESSAGE: {} \n" \
                                      "PULL MESSAGE: {} \n".format(fetch_out, pull_out)

    def do_update_settings_from_repo(self, value, *args):
        """Update settings - Tries to update the settings. This only works if you have a assigned repo in the configs dir."""

        for val in value.values():
            if re.findall(r"Update settings\b", val):
                try:
                    import git
                except:
                    self.answer = "Could not import git module, please install 'gitpython' first on the machine."
                    return
                fetch_out = ""
                pull_out = ""
                path = os.path.normpath("COMET/config")
                os.system("cd {}".format(path))
                try:
                    repo = git.Repo()
                    o = repo.remotes.origin
                    fetch_out = o.fetch()
                    pull_out = o.pull()
                    self.answer = "Code successfully updated!"
                except: self.answer = "Could not pull from remote repo. No update done. \n" \
                                      "FETCH MESSAGE: {} \n" \
                                      "PULL MESSAGE: {} \n".format(fetch_out, pull_out)



