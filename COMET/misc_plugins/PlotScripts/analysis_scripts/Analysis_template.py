"""Simply plots all data as curve plots"""

"""This script is just a template out of which you can build your own analysis"""

import logging
import holoviews as hv

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout
from forge.tools import twiny, relabelPlot
from forge.tools import plot_all_measurements, convert_to_EngUnits
from forge.specialPlots import dospecialPlots
from forge.utilities import line_intersection


class TCAD:
    def __init__(self, data, configs):

        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=False)
        self.config = configs
        self.df = []
        self.basePlots = None
        self.analysisname = "TCAD"
        self.PlotDict = {"Name": self.analysisname}
        self.measurements = self.data["columns"]
        # hv.renderer('bokeh')

    def run(self):
        """Runs the script"""

        # Convert the units to the desired ones
        for meas in self.measurements:
            unit = (
                self.config[self.analysisname].get(meas, {}).get("UnitConversion", None)
            )
            if unit:
                self.data = convert_to_EngUnits(self.data, meas, unit)

        # Plot all Measurements
        self.basePlots = plot_all_measurements(
            self.data,
            self.config,
            self.measurements[0],
            self.analysisname,
            do_not_plot=[self.measurements[0]],
        )
        self.PlotDict["All"] = self.basePlots

        # Plot all special Plots:
        # Histogram Plot
        self.Histogram = dospecialPlots(
            self.data,
            self.config,
            self.analysisname,
            "concatHistogram",
            self.measurements,
            **self.config[self.analysisname]
            .get("AuxOptions", {})
            .get("concatHistogram", {})
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

        # Violin Plot
        self.Violin = dospecialPlots(
            self.data, self.config, self.analysisname, "Violin", self.measurements
        )
        if self.Violin:
            self.PlotDict["Violin"] = self.Violin
            self.PlotDict["All"] = self.PlotDict["All"] + self.Violin

        # Reconfig the plots to be sure
        self.PlotDict["All"] = config_layout(
            self.PlotDict["All"],
            **self.config.get(self.analysisname, {}).get("Layout", {})
        )
        return self.PlotDict
