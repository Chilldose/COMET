"""Script for plotting relaxation time measurements done via the QTC"""
import logging
import holoviews as hv

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout
from forge.tools import twiny, relabelPlot
from forge.tools import plot_all_measurements, convert_to_EngUnits
from forge.specialPlots import dospecialPlots
from forge.tools import SimplePlot



class relaxation_time:

    def __init__(self, data, configs):

        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=True)
        self.config = configs
        self.df = []
        self.Plots = []
        self.allPlots = None
        self.individual = None
        self.PlotDict = {"Name": "Relaxation time"}
        self.measurements = self.data["columns"]
        #hv.renderer('bokeh')

    def run(self):
        """Runs the script"""

        # Convert the units to the desired ones
        for meas in zip(*[iter(self.measurements)]*2):
            unit = self.config["relaxation_time"].get("Relax", {}).get("UnitConversion", None)
            if unit:
                self.data = convert_to_EngUnits(self.data, meas[1], unit)

        # Plot all Measurements together
        for x, y in zip(*[iter(self.measurements)]*2):
            self.Plots.append(holoplot("Relax", self.data, self.config["relaxation_time"], x, y))

        # Add the individual plots
        self.allPlots = self.Plots[0]
        self.individual = self.Plots[0]
        for plot in self.Plots[1:]:
            self.allPlots *= plot
            self.individual += plot

        self.PlotDict["All"] = self.allPlots + self.individual

        # Reconfig the plots to be sure
        self.PlotDict["All"] = config_layout(self.PlotDict["All"], **self.config.get("Relaxation time", {}).get("Layout", {}))
        return self.PlotDict
