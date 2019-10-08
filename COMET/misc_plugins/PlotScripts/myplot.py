"""This is the main file for plotting.
This scripts takes arguments parsed by the user, usually a config file"""

import logging
import sys, os

from .forge.utilities import parse_args, LogFile, load_yaml, exception_handler, sanatise_units, sanatise_measurement
from .forge.utilities import load_plugins
from multiprocessing import Pool
import traceback
import holoviews as hv
from bokeh.io import show
from pathlib import Path
from copy import deepcopy
from time import sleep
hv.extension('bokeh')
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import importlib

from bokeh.io import save

from .forge.tools import read_in_ASCII_measurement_files, read_in_JSON_measurement_files, save_plot

class PlottingMain:

    def __init__(self, configs = None):
        """Configs must be a list representation of valid args!"""

        self.data = {}
        self.rootdir = Path(__file__).parent.resolve()
        self.plotObjects = []


        # Initialize a logfile class
        self.logFile = LogFile(path="LogFiles\LoggerConfig.yml")

        self.log = logging.getLogger("mainPlotting")

        # Init Except hook
        #sys.excepthook = exception_handler

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

        # Initialize process pool
        #self.pool = Pool(processes=self.config.get("Poolsize", 1))

        self.log.critical("Loading data files...")
        if self.config["Filetype"].upper() == "ASCII":
            self.data, load_order = read_in_ASCII_measurement_files(self.config["Files"], self.config["ASCII_file_specs"])
            self.config["file_order"] = load_order # To keep easy track of the names and not the pathes

        elif self.config["Filetype"].upper() == "JSON":
            self.data, load_order = read_in_JSON_measurement_files(self.config["Files"])
            self.config["file_order"] = load_order  # To keep easy track of the names and not the pathes

        # Sanatise units and measurements
        #for data in self.data.values():
            #data["units"] = sanatise_units(data["units"])
            #data["measurements"] = sanatise_measurement(data["measurements"])
        self.log.critical("Loading data files completed.")

        # Loading measurement plugins
        self.log.critical("Loading plot modules...")
        self.plugins = load_plugins(self.config, self.rootdir)

    def run(self):
        """Runs the script"""
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
                config_data = [(analysis, analysis_obj, deepcopy(self.data), self.config.copy(), self.log) for analysis, analysis_obj in self.plugins.items()]
                # Todo: multiporcess the analysis
                #self.plotObjects = self.pool.starmap(self.start_analysis, config_data)
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

    def save_to(self):
        """This function saves all plots from every analysis for each datasets as svg"""
        self.log.info("Saving plots...")
        # Generate base folder
        save_dir = os.path.normpath(self.config.get("Output", "Plots"))
        try:
            #Todo:directory tree generation
            os.mkdir(save_dir)
        except:
            self.log.warning("The directory: {} already exists, files inside can/will be overwritten!".format(save_dir))
        if os.path.exists(os.path.normpath(save_dir)):
            for plot in self.plotObjects:
                if "All" in plot:
                    self.log.info("Saving all subplots from the 'All' plot...")
                    Allplots = plot["All"]
                    # todo: saving of table not working with keys!!!
                    try:
                        plotslist_tuple = Allplots.keys()
                        for path in plotslist_tuple:
                            plots = Allplots
                            for attr in path:
                                plots = getattr(plots, attr)
                            try:
                                label = plots._label
                            except:
                                label = "_".join(path)
                            save_plot(label, plots, save_dir, save_as=self.config["Save_as"])
                    except:
                        save_plot(Allplots.group, Allplots, save_dir, save_as=self.config["Save_as"])

                else:
                    self.log.info("Saving all subplots from the 'All' not possible due to missing key...")
                    self.log.info("Saving all plots across the dictionary...")
                    for key, subplot in plot.items():
                        save_plot(key, subplot, save_dir)
                try:
                    self.log.info("Export the 'All' html plot...")
                    save_plot(plot.get("Name", "All Plots"), plot["All"], save_dir)
                    #save(hv.render(plot["All"], backend='bokeh'), os.path.join(save_dir,"{}.html".format("All plots")))
                except:
                    self.log.warning("'All plots' could not be saved....")

        else:
            self.log.error("The path: {} does not exist...".format(save_dir))

    @staticmethod
    def start_analysis(analysis, analysis_obj, data, config, log):
        """Simply starts the passed analysis"""
        try:
            log.critical("Starting analysis/plot script: {}".format(analysis))
            analysisObj = getattr(analysis_obj, analysis)(data.copy(), config)
            return analysisObj.run()

        except Exception as err:
            try:
                exc_info = sys.exc_info()
            except Exception as err2:
                log.error("A really bad error happend in analysis process {}! "
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
