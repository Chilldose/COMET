"""This script plots IVCV files together for files generated by QTC
Data must be """

import logging, os
import holoviews as hv
from holoviews import opts
from scipy.stats import linregress
from copy import deepcopy
import pandas as pd
import numpy as np

from bokeh.models import CustomJS
from bokeh.models.widgets import Button

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout, text_box
from forge.tools import twiny, relabelPlot, applyPlotOptions, rename_columns
from forge.tools import plot_all_measurements, convert_to_EngUnits
from forge.specialPlots import dospecialPlots
from forge.utilities import line_intersection


class MemoryEffect_IMS:
    def __init__(self, data, configs):

        self.log = logging.getLogger(__name__)
        self.config = configs
        self.analysisName = "MemoryEffect_IMS"
        self.data = convert_to_df(data, abs=self.config.get("abs_value_only", False))
        self.data = rename_columns(
            self.data, self.config[self.analysisName].get("Measurement_aliases", {})
        )
        self.basePlots = None
        self.PlotDict = {
            "Name": "MemoryEffect_IMS"
        }  # Name of analysis and cnavas for all plots generated during this analysis
        self.measurements = self.data["columns"]
        self.xaxis = self.measurements[7]

        # The do not plot list, you can extend this list as you like
        self.donts = ["stdC11R11", "stdC127R127", "stdC255R257", "step", "Name"]

        self.errors = {"C11R11": self.data["All"]["stdC11R11"], "C127R127": self.data["All"]["stdC127R127"], "C255R257": self.data["All"]["stdC255R257"]}


    def run(self):
        """Runs the script"""

        # Convert the units to the desired ones
        self.original_data = deepcopy(self.data) # Is needed for gradin

        # Plot deltas of each measurement
        abs_diff = self.data["All"][["C11R11","C127R127", "C255R257"]].diff(axis=0)
        rel_diff = (abs_diff/self.data["All"][["C11R11","C127R127", "C255R257"]]).rename(columns={"C11R11":"C11R11_reldiff",
                                                                                                    "C127R127":"C127R127_reldiff",
                                                                                                    "C255R257":"C255R257_reldiff"})
        abs_diff = abs_diff.rename(columns={"C11R11":"C11R11_absdiff","C127R127":"C127R127_absdiff", "C255R257":"C255R257_absdiff"})

        temp = rel_diff.join(abs_diff)
        self.data["All"] = self.data["All"].join(temp)
        self.data["columns"].extend(["C11R11_absdiff", "C127R127_absdiff","C255R257_absdiff",
                                            "C11R11_reldiff",
                                            "C127R127_reldiff",
                                            "C255R257_reldiff"])

        for file in self.data["keys"]:
            self.data[file]["measurements"].extend(["C11R11_absdiff", "C127R127_absdiff","C255R257_absdiff",
                                            "C11R11_reldiff",
                                            "C127R127_reldiff",
                                            "C255R257_reldiff"])
            self.data[file]["data"] = self.data["All"]
            self.data[file]["units"].extend(["None", "urad","urad","urad", "%", "%","%"])



        # Plot all Measurements
        self.basePlots = plot_all_measurements(
            self.data,
            self.config,
            self.xaxis,
            self.analysisName,
            do_not_plot=self.donts,
            ErrorBars=self.errors
        )

        # self.basePlots = applyPlotOptions(self.basePlots, {'Curve': {'color': "hv.Cycle('PiYG')"}})
        self.PlotDict["BasePlots"] = self.basePlots
        self.PlotDict["All"] = self.basePlots



        return self.PlotDict