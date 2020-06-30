"""Simply plots all data as curve plots"""

"""This script is just a template out of which you can build your own analysis"""

import logging
import numpy as np

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout, moving_average
from forge.tools import twiny, relabelPlot
from forge.tools import plot_all_measurements, plot, convert_to_EngUnits
from forge.specialPlots import dospecialPlots
from forge.utilities import line_intersection


class SQC_SELFTEST:
    def __init__(self, data, configs):

        self.log = logging.getLogger(__name__)

        self.data = data
        self.config = configs
        self.df = []
        self.basePlots = None
        self.analysisname = "SQC_SELFTEST"
        self.PlotDict = {"Name": self.analysisname}



    def run(self):
        """Runs the script"""

        self.analysis()

        # Convert the units to the desired ones
        for meas in self.measurements:
            unit = (
                self.config[self.analysisname].get(meas, {}).get("UnitConversion", None)
            )
            if unit:
                self.data = convert_to_EngUnits(self.data, meas, unit)

        # Plot all Measurements
        self.basePlots = plot(
            self.data,
            self.config,
            self.xaxis,
            self.analysisname,
            do_not_plot=[self.xaxis],
        )
        self.PlotDict["All"] = self.basePlots

        # Plot all special Plots:
        # Histogram Plot
        self.Histogram = dospecialPlots(
            self.data,
            self.config,
            self.analysisname,
            "Histogram",
            self.measurements,
            **self.config[self.analysisname]
            .get("AuxOptions", {})
            .get("singleHistogram", {})
        )
        if self.Histogram:
            self.PlotDict["Histogram"] = self.Histogram
            self.PlotDict["All"] = self.PlotDict["All"] + self.Histogram

        # Whiskers Plot
        self.WhiskerPlots = dospecialPlots(
            self.data, self.config, self.analysisname, "BoxWhisker", self.measurements
        )
        if self.WhiskerPlots:
            self.PlotDict["Whiskers"] = self.WhiskerPlots
            self.PlotDict["All"] = self.PlotDict["All"] + self.WhiskerPlots
        return self.PlotDict

    def analysis(self):
        """Does the analysis"""

        average_len = 1

        # Manipulate data
        for entry in self.data:
            self.data[entry]["data"]["measurement"] = np.array(range(0,1000-(average_len-1)))
            self.data[entry]["measurements"].insert(0, "measurement")
            self.data[entry]["units"].insert(0, "#")

            # Do moving average over all data arrays
            for col in self.data[entry]["data"]:
                if col != "measurement":
                    self.data[entry]["data"][col] = moving_average(self.data[entry]["data"][col], average_len)

        # Do rpoly conversion
        rpolyvoltage = -1
        for file in self.data:
            self.data[file]["data"]["R1"] = rpolyvoltage/self.data[file]["data"]["R1"]
            indx = self.data[file]["measurements"].index("R1")
            self.data[file]["units"][indx] = "Ohm"

        # Convert to df
        self.data = convert_to_df(self.data, abs=False)
        self.measurements = self.data["columns"]
        self.xaxis = "measurement"