"""This is the main file for plotting.
This scripts takes arguments parsed by the user, usually a config file"""

import logging
import sys, os

try:
    from .forge.utilities import parse_args, LogFile, load_yaml
    from .forge.utilities import load_plugins, reload_plugins
    from .forge.tools import read_in_files, save_plot
except:
    from forge.utilities import parse_args, LogFile, load_yaml
    from forge.utilities import load_plugins, reload_plugins
    from forge.tools import read_in_files, save_plot

import traceback
import holoviews as hv
from bokeh.io import show
from pathlib import Path
from copy import deepcopy
from time import sleep
from warnings import filterwarnings
filterwarnings('ignore', message='save()', category=UserWarning)
hv.extension('bokeh')
sys.path.append(os.path.dirname(os.path.realpath(__file__)))


class PlottingMain:

    def __init__(self, configs = None):
        """Configs must be a list representation of valid args!"""

        self.data = {}
        self.rootdir = Path(__file__).parent.resolve()
        self.plotObjects = []

        # Initialize a logfile class
        self.logFile = LogFile(path="LogFiles\LoggerConfig.yml")

        self.log = logging.getLogger("mainPlotting")

        # Get the args parsed to this script if necessary
        if not configs:
            self.args = parse_args()
            self.log.critical("Arguments parsed: {}".format(self.args))
        else:
            self.args = parse_args(configs)
            self.log.critical("Arguments parsed: {}".format(self.args))

        # Load the config to a dictionary
        self.config = load_yaml(self.args.file)

        self.log.critical("Loaded config file: {}".format(self.args.file))


        self.log.critical("Loading data files...")
        self.data, load_order = read_in_files(self.config["Files"], self.config)
        self.config["file_order"] = load_order  # To keep easy track of the names and not the pathes

        self.log.critical("Loading data files completed.")

        # Loading measurement plugins
        self.log.critical("Loading plot modules...")
        self.plugins = load_plugins(self.config, self.rootdir)

    def run(self):
        """Runs the script"""
        reload_plugins(self.plugins)
        self.plot()
        if self.args.show:
            self.show_results()
        if self.args.save:
            self.save_to()


    def plot(self):
        """This function starts the plotting process. It simply calls the plotting script"""
        if "Analysis" in self.config:
            if isinstance(self.config["Analysis"], list):
                # All plot scripts must return the plot objects, in which all plots are included. Saving of plots will
                # be done via the main script.
                # config_data = [(analysis, analysis_obj, deepcopy(self.data), self.config.copy(), self.log) for analysis, analysis_obj in self.plugins.items()]
                config_data = [(analysis, analysis_obj, deepcopy(self.data), self.config.copy(), self.log) for analysis, analysis_obj in self.plugins.items()]
                self.plotObjects = []
                for conf in config_data:
                    self.plotObjects.append(self.start_analysis(*conf))

            else:
                self.log.error("Data type of analysis parameter must be list of str.")

    def temp_html_output(self, plot_object):
        """This function plots a object, by saving the plot as html file in a temporary file and returning the path
        to the file"""
        #finalfig = hv.render(plot_object, backend='bokeh')
        save_plot("temp_plot", plot_object, self.rootdir, save_as="html")
        return os.path.join(self.rootdir, "html", "temp_plot.html")

    def show_results(self):
        """This function shows all results form all analyses"""
        hv.renderer('bokeh')
        self.log.info("Showing the 'all' plot from every analysis...")
        for plot in self.plotObjects:
            if "All" in plot:
                finalfig = hv.render(plot["All"], backend='bokeh')
                show(finalfig)
                sleep(1.)
            else:
                self.log.info("No 'all' plot defined, skipping...")

    def save_to(self, progress_queue=None):
        """This function saves all plots from every analysis for each datasets as svg"""
        self.log.critical("Saving plots...")
        progress_steps = 0
        saved = 0
        # Generate base folder
        save_dir = os.path.normpath(self.config.get("Output", "Plots"))
        try:
            #Todo:directory tree generation
            os.mkdir(save_dir)
        except:
            self.log.warning("The directory: {} already exists, files inside can/will be overwritten!".format(save_dir))
        if os.path.exists(os.path.normpath(save_dir)):
            if progress_queue:
                progress_queue.put({"STATE": "Saving plots..."})
            for plot in self.plotObjects:
                if "All" in plot:
                    self.log.info("Saving all subplots from the 'All' plot...")
                    Allplots = plot["All"]
                    try:
                        plotslist_tuple = Allplots.keys()
                        progress_steps += len(plotslist_tuple)
                        for path in plotslist_tuple:
                            if progress_queue:
                                progress_queue.put({"PROGRESS": saved/(progress_steps + 1)})
                            plots = Allplots
                            for attr in path:
                                plots = getattr(plots, attr)
                            try:
                                label = "_".join(path)
                            except:
                                label = plots._label

                            save_plot(label, plots, save_dir, save_as=self.config.get("Save_as", ["html"]))
                            saved += 1
                    except:
                        save_plot(Allplots.group, Allplots, save_dir, save_as=self.config.get("Save_as", ["html"]))
                        saved += 1

                else:
                    self.log.info("Saving all subplots from the 'All' not possible due to missing key...")
                    self.log.info("Saving all plots across the dictionary...")
                    progress_steps = len(plot.items())
                    for key, subplot in plot.items():
                        if progress_queue:
                            progress_queue.put({"progress": saved/(progress_steps + 1)})
                        save_plot(key, subplot, save_dir)
                        saved += 1
                try:
                    self.log.info("Export the 'All' html plot...")
                    save_plot(plot.get("Name", "All Plots"), plot["All"], save_dir)
                    if progress_queue:
                        progress_queue.put({"PROGRESS": 1})
                except:
                    self.log.warning("'All plots' could not be saved....")

        else:
            self.log.error("The path: {} does not exist...".format(save_dir))
        if progress_queue:
            progress_queue.put({"STATE": "IDLE"})

    @staticmethod
    def start_analysis(analysis, analysis_obj, data, config, log):
        """Simply starts the passed analysis"""
        try:
            log.critical("Starting analysis/plot script: {}".format(analysis))
            analysisObj = getattr(analysis_obj, analysis)(data, config)
            return analysisObj.run()

        except Exception as err:
            try:
                exc_info = sys.exc_info()
            except Exception as err2:
                log.error("A really bad error happened in analysis process {}! "
                               "System exception info could not be obtained correctly. "
                               "The thing I have is the exception itself: {}"
                               ", and the error while obtaining the stack trace: {}".format(analysis, err, err2))
            finally:
                log.error("An error happened during execution of analysis process: {} with error {}\n"
                                "Traceback: {}".format(analysis, err, traceback.print_exception(*exc_info)))
                del exc_info
                raise

if __name__ == "__main__":
    plot = PlottingMain()
    plot.run()
