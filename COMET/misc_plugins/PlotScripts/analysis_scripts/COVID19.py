"""Simply plots all data as curve plots"""

"""This script is just a template out of which you can build your own analysis"""

import logging
import holoviews as hv
import pandas as pd

hv.extension('bokeh')

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout
from forge.tools import twiny, relabelPlot
from forge.tools import plot_all_measurements, convert_to_EngUnits
from forge.specialPlots import dospecialPlots
from forge.utilities import line_intersection
import numpy as np


class COVID19:

    def __init__(self, data, configs):

        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=False)
        self.config = configs
        self.df = []
        self.basePlots = None
        self.analysisname = "COVID19"
        self.PlotDict = {"Name": self.analysisname}
        self.measurements = self.data["columns"][4:] # Cut the non measurement lines
        hv.renderer('bokeh')
        self.keys_basenames = [name.split("-")[-1] for name in self.data["keys"]]
        self.countries = []

    def run(self):
        """Runs the script"""

        # Do some grouping and sanatizing
        groupedcountries = self.data["All"].groupby(self.data["All"]["Country/Region"]) # Data grouped by country
        self.countries = list(groupedcountries.groups)
        countrycasegrouped = groupedcountries.get_group("US").groupby("Name") # Grouped for death, confirmed, recovered

        seldata = {} # a dict containing all data from one country grouped by death, confirmed, recovered
        for i, key in enumerate(self.data["keys"]): # The three groups: death, confirmed, recovered
            rawdata = countrycasegrouped.get_group(key).sum() # Some countries have region information (I combine them to a single one)
            seldata[self.keys_basenames[i]] = rawdata[self.measurements].reindex(self.measurements)

        # Now do the anlysis
        growth = {}
        relgrowth = {}
        for key, dat in seldata.items():
            growth[key] = dat.diff()
            # Calculate the relative growth
            gr = growth[key].reindex(self.measurements)
            absc = dat.reindex(self.measurements)
            relgrowth[key] = gr.shift(periods=-1, fill_value=np.nan).divide(absc.replace(0, np.nan)).shift(periods=1, fill_value=np.nan)

        # Replace the data in the data structure
        newkeys = ["Accumulated", "Growth", "RelativeGrowth"]
        self.data["keys"] = newkeys
        self.data["columns"] = self.keys_basenames
        units = ["#" for i in self.keys_basenames]
        for key, dat in zip(newkeys, [seldata, growth, relgrowth]):
            self.data[key] = {"analysed": False, "plots": False, "header": ""}
            self.data[key]["measurements"] = self.keys_basenames
            self.data[key]["units"] = units
            #self.data[key]["units"][-2] = "%" # The last one is percent
            dat["Date"] = pd.to_datetime(pd.Series(self.measurements, name="Date", index=pd.Index(self.measurements)), infer_datetime_format=True)
            dat["Name"] = pd.Series([key for i in self.measurements], name="Name", index=pd.Index(self.measurements))
            self.data[key]["measurements"].append("Date")
            self.data[key]["units"].append("")
            self.data[key]["data"] = pd.DataFrame(dat)

        # Start plotting
        # Accumulated
        donts = ["Date"]
        self.PlotDict["All"] = None
        # Define PlotLabel
        #for subkey, entry in self.config["COVID19"].items():
        #    if "PlotLabel" in entry:
        #        entry["PlotLabel"] = entry["PlotLabel"].split(":")[0].strip() + ": " + key
        self.Plots = plot_all_measurements(self.data, self.config, "Date", "COVID19", keys=["Accumulated"], do_not_plot=donts)
        if self.PlotDict["All"]:
            self.PlotDict["All"] += self.Plots
        else: self.PlotDict["All"] = self.Plots

        # Reconfig the plots to be sure
        self.PlotDict["All"] = config_layout(self.PlotDict["All"], **self.config.get(self.analysisname, {}).get("Layout", {}))
        return self.PlotDict
