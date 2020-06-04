"""This is the main file for plotting.
This scripts takes arguments parsed by the user, usually a config file"""

import logging
import sys, os

try:
    from .forge.utilities import parse_args, LogFile, load_yaml
    from .forge.utilities import load_plugins, reload_plugins
    from .forge.tools import read_in_files, save_plot, save_data
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

filterwarnings("ignore", message="save()", category=UserWarning)
sys.path.append(os.path.dirname(os.path.realpath(__file__)))


class PlottingMain:
    def __init__(self, configs=None):
        """Configs must be a list representation of valid args!"""

        self.data = {}
        self.rootdir = Path(__file__).parent.resolve()
        self.plotObjects = []
        self.backend = None

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
        self.log.critical("Loading config file: {}".format(self.args.file))
        self.config = load_yaml(self.args.file)

        # Define backend for plotting
        self.backend = self.config.get("backend", "bokeh")
        hv.extension(self.backend)
        self.log.info("Plotting backend is {}".format(self.backend))

        self.log.critical("Loading data files...")
        self.data, load_order = read_in_files(self.config["Files"], self.config)
        self.config[
            "file_order"
        ] = load_order  # To keep easy track of the names and not the pathes

        self.log.critical("Loading data files completed.")

        # Loading measurement plugins
        self.log.critical("Loading plot modules...")
        self.plugins = load_plugins(self.config, self.rootdir)

    def run(self):
        """Runs the script"""
        reload_plugins(self.plugins)
        self.plot()
        if self.args.dont_show:
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
                config_data = [
                    (
                        analysis,
                        analysis_obj,
                        deepcopy(self.data),
                        self.config.copy(),
                        self.log,
                    )
                    for analysis, analysis_obj in self.plugins.items()
                ]
                self.plotObjects = []
                for conf in config_data:
                    self.plotObjects.append(self.start_analysis(*conf))

            else:
                self.log.error("Data type of analysis parameter must be list of str.")

    def temp_png_output(self, plot_object, backend=None):
        """This function plots a object, by saving the plot as png file in a temporary file and returning the path
        to the file"""
        save_plot(
            "temp_plot", plot_object, self.rootdir, save_as=["png"], backend=backend
        )
        return os.path.join(self.rootdir, "png", "temp_plot.png")

    def temp_html_output(self, plot_object, backend=None):
        """This function plots a object, by saving the plot as html file in a temporary file and returning the path
        to the file"""
        save_plot(
            "temp_plot", plot_object, self.rootdir, save_as=["html"], backend=backend
        )
        return os.path.join(self.rootdir, "html", "temp_plot.html")

    def show_results(self):
        """This function shows all results form all analyses"""
        for plot in self.plotObjects:
            if "All" in plot:
                if self.backend == "matplotlib":
                    renderer = hv.renderer(self.backend)
                    renderer.show(plot["All"])
                if self.backend == "bokeh":
                    finalfig = hv.render(plot["All"], backend="bokeh")
                    show(finalfig)
                sleep(1.0)
            else:
                self.log.info("No 'all' plot defined, skipping...")

    def save_to(self, progress_queue=None, backend=None, to_call=None):
        """This function saves all plots from every analysis for each datasets"""

        # Generate base folder
        save_dir = os.path.normpath(self.config.get("Output", "Plots"))
        try:
            os.mkdir(save_dir)
        except:
            self.log.warning(
                "The directory: {} already exists, files inside can/will be overwritten!".format(
                    save_dir
                )
            )

        self.log.info("Saving data...")
        from forge.tools import save_data

        save_data(self, self.config.get("Save_as", []), save_dir, to_call=to_call)

        # check if any plot should be saved
        anyplot = False
        for ploti in ["png", "html", "svg"]:
            if ploti in self.config.get("Save_as", []):
                anyplot = True

        if not anyplot:
            self.log.info("No plot type specified for saving...")
            return

        self.log.critical("Saving plots...")
        progress_steps = 0
        saved = 0

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
                                progress_queue.put(
                                    {"PROGRESS": saved / (progress_steps + 1)}
                                )
                            plots = Allplots
                            for attr in path:
                                plots = getattr(plots, attr)
                            try:
                                label = "_".join(path)
                            except:
                                label = plots._label

                            save_plot(
                                label,
                                plots,
                                save_dir,
                                save_as=self.config.get("Save_as", ["png"]),
                                backend=backend,
                            )
                            saved += 1
                    except:
                        save_plot(
                            Allplots.group,
                            Allplots,
                            save_dir,
                            save_as=self.config.get("Save_as", ["png"]),
                            backend=backend,
                        )
                        saved += 1

                else:
                    self.log.info(
                        "Saving all subplots from the 'All' not possible due to missing key..."
                    )
                    self.log.info("Saving all plots across the dictionary instead...")
                    progress_steps = len(plot.items())
                    for key, subplot in plot.items():
                        if progress_queue:
                            progress_queue.put(
                                {"progress": saved / (progress_steps + 1)}
                            )
                        save_plot(key, subplot, save_dir, backend=backend)
                        saved += 1
                try:
                    if "html" in self.config.get(
                        "Save_as", []
                    ) or "png" in self.config.get("Save_as", []):
                        self.log.info("Export the 'All' plot...")
                        save_plot(
                            plot.get("Name", "All Plots"),
                            plot["All"],
                            save_dir,
                            backend=self.backend,
                        )
                        if progress_queue:
                            progress_queue.put({"PROGRESS": 1})
                    else:
                        progress_queue.put({"PROGRESS": 1})
                except:
                    self.log.warning(
                        "'All plots' could not be saved....", exc_info=True
                    )

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
                log.error(
                    "A really bad error happened in analysis process {}! "
                    "System exception info could not be obtained correctly. "
                    "The thing I have is the exception itself: {}"
                    ", and the error while obtaining the stack trace: {}".format(
                        analysis, err, err2
                    )
                )
            finally:
                log.error(
                    "An error happened during execution of analysis process: {} with error {}\n"
                    "Traceback: {}".format(
                        analysis, err, traceback.print_exception(*exc_info)
                    )
                )
                del exc_info
                raise


if __name__ == "__main__":
    plot = PlottingMain()
    plot.run()
