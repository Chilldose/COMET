"""Simply plots all data as curve plots"""

"""This script is just a template out of which you can build your own analysis"""

import logging
import holoviews as hv
import pandas as pd
from holoviews import opts


from forge.tools import customize_plot, holoplot, convert_to_df, config_layout
from forge.tools import twiny, relabelPlot
from forge.tools import plot_all_measurements, convert_to_EngUnits
from forge.tools import plot
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
        self.measurements = self.data["columns"][4:]  # Cut the non measurement lines
        # hv.renderer('bokeh')
        self.keys_basenames = [name.split("_")[-2] for name in self.data["keys"]]
        self.countries = []

        # Plot canvas:
        self.Plots = None
        self.cases = None
        self.recovered = None
        self.deaths = None
        self.casesrelgrowth = None
        self.recoveredrelgrowth = None
        self.deathsrelgrowth = None
        self.casesNorm = None
        self.recoveredNorm = None
        self.deathsNorm = None
        self.GrowthvsCases = None
        self.DeathvsCases = None

    def run(self):
        """Runs the script"""
        from forge.tools import (
            plainPlot,
        )  # some elusive error in debugger it works while running it does not, but only here

        # Do some grouping and sanatizing
        groupedcountries = self.data["All"].groupby(
            self.data["All"]["Country/Region"]
        )  # Data grouped by country
        self.countries = list(groupedcountries.groups)

        self.PlotDict["All"] = None
        prekeys = self.data["keys"]
        for items in self.config["COVID19"]["Countries"]:
            countryName = list(items.keys())[0]
            inhabitants = list(items.values())[0]
            countrycasegrouped = groupedcountries.get_group(countryName).groupby(
                "Name"
            )  # Grouped for death, confirmed, recovered

            seldata = (
                {}
            )  # a dict containing all data from one country grouped by death, confirmed, recovered
            for i, key in enumerate(
                prekeys
            ):  # The three groups: death, confirmed, recovered
                rawdata = countrycasegrouped.get_group(
                    key
                ).sum()  # Some countries have region information (I combine them to a single one)
                seldata[self.keys_basenames[i]] = rawdata[self.measurements].reindex(
                    self.measurements
                )

            # Now do the anlysis
            growth = {}
            relgrowth = {}
            for key, dat in seldata.items():
                growth[key] = dat.diff()
                # Calculate the relative growth
                gr = growth[key].reindex(self.measurements)
                absc = dat.reindex(self.measurements)
                relgrowth[key] = (
                    gr.shift(periods=-1, fill_value=np.nan)
                    .divide(absc.replace(0, np.nan))
                    .shift(periods=1, fill_value=np.nan)
                    * self.config["COVID19"]["GrowingRateMulti"]
                )

            # Replace the data in the data structure
            newkeys = [
                "Accumulated",
                "Growth",
                "RelativeGrowth*{}".format(self.config["COVID19"]["GrowingRateMulti"]),
            ]
            self.data["keys"] = newkeys
            self.data["columns"] = self.keys_basenames
            units = ["#" for i in self.keys_basenames]
            for key, dat in zip(newkeys, [seldata, growth, relgrowth]):
                self.data[key] = {"analysed": False, "plots": False, "header": ""}
                self.data[key]["measurements"] = self.keys_basenames
                self.data[key]["units"] = units
                # self.data[key]["units"][-2] = "%" # The last one is percent
                dat["Date"] = pd.to_datetime(
                    pd.Series(
                        self.measurements,
                        name="Date",
                        index=pd.Index(self.measurements),
                    ),
                    infer_datetime_format=True,
                )
                dat["Date"] = dat["Date"].dt.to_period("d")
                dat["Name"] = pd.Series(
                    [key for i in self.measurements],
                    name="Name",
                    index=pd.Index(self.measurements),
                )
                self.data[key]["measurements"].append("Date")
                self.data[key]["units"].append("")
                self.data[key]["data"] = pd.DataFrame(dat)

            # Start plotting
            # All individual
            donts = ["Date"]
            individual = plot_all_measurements(
                self.data,
                self.config,
                "Date",
                "COVID19",
                keys=[
                    "Accumulated",
                    "Growth",
                    "RelativeGrowth*{}".format(
                        self.config["COVID19"]["GrowingRateMulti"]
                    ),
                ],
                do_not_plot=donts,
                PlotLabel="{}".format(countryName),
            )

            if self.Plots:
                self.Plots += individual
            else:
                self.Plots = individual

            self.relgrowth_all_countries(countryName)
            if self.config["COVID19"]["Normalize"] == True:
                self.accumulated_all_countries_normalizes(countryName, inhabitants)
            elif self.config["COVID19"]["Normalize"] == False:
                self.accumulated_all_countries(countryName)

            # Cases vs growth
            if not self.GrowthvsCases:
                self.GrowthvsCases = plainPlot(
                    "Curve",
                    self.data["Accumulated"]["data"]["confirmed"],
                    self.data["Growth"]["data"]["confirmed"],
                    label=countryName,
                    ylabel="New Cases",
                    **self.config["COVID19"]["General"],
                    **self.config["COVID19"]["GvC"]["PlotOptions"]
                )
            else:
                self.GrowthvsCases *= plainPlot(
                    "Curve",
                    self.data["Accumulated"]["data"]["confirmed"],
                    self.data["Growth"]["data"]["confirmed"],
                    label=countryName,
                    ylabel="New Cases",
                    **self.config["COVID19"]["General"],
                    **self.config["COVID19"]["GvC"]["PlotOptions"]
                )

            # Death vs growth
            if not self.DeathvsCases:
                self.DeathvsCases = plainPlot(
                    "Curve",
                    self.data["Accumulated"]["data"]["confirmed"],
                    self.data["Accumulated"]["data"]["deaths"],
                    label=countryName,
                    ylabel="Total Deaths",
                    **self.config["COVID19"]["General"],
                    **self.config["COVID19"]["GvC"]["PlotOptions"]
                )
            else:
                self.DeathvsCases *= plainPlot(
                    "Curve",
                    self.data["Accumulated"]["data"]["confirmed"],
                    self.data["Accumulated"]["data"]["deaths"],
                    label=countryName,
                    ylabel="Total Deaths",
                    **self.config["COVID19"]["General"],
                    **self.config["COVID19"]["GvC"]["PlotOptions"]
                )

        # Relabel the plots
        self.GrowthvsCases = relabelPlot(
            self.GrowthvsCases.opts(xlim=(1, None), ylim=(1, None)),
            "New Cases vs. Total Cases",
        )
        self.DeathvsCases = relabelPlot(
            self.DeathvsCases.opts(xlim=(1, None), ylim=(1, None)),
            "Total Death vs. Total Cases",
        )
        if not self.config["COVID19"]["Normalize"]:
            self.cases = relabelPlot(self.cases, "Confirmed Cases not normalized")
            self.recovered = relabelPlot(
                self.recovered, "Recovered Cases not normalized"
            )
            self.deaths = relabelPlot(self.deaths, "Deaths not normalized")
        self.casesrelgrowth = relabelPlot(
            self.casesrelgrowth, "Confirmed Cases relative growth"
        )
        self.recoveredrelgrowth = relabelPlot(
            self.recoveredrelgrowth, "Recovered Cases relative growth"
        )
        self.deathsrelgrowth = relabelPlot(
            self.deathsrelgrowth, "Deaths relative growth"
        )
        if self.config["COVID19"]["Normalize"]:
            self.casesNorm = relabelPlot(self.casesNorm, "Confirmed Cases normalized")
            self.recoveredNorm = relabelPlot(
                self.recoveredNorm, "Recovered Cases normalized"
            )
            self.deathsNorm = relabelPlot(self.deathsNorm, "Deaths normalized")

        # Define Plotting order
        self.plottingOrder = [
            self.GrowthvsCases,
            self.DeathvsCases,
            self.casesNorm,
            self.recoveredNorm,
            self.deathsNorm,
            self.casesrelgrowth,
            self.recoveredrelgrowth,
            self.deathsrelgrowth,
            self.cases,
            self.recovered,
            self.deaths,
            self.Plots,
        ]
        for plot in self.plottingOrder:
            if plot:
                if self.PlotDict["All"]:
                    self.PlotDict["All"] += plot
                else:
                    self.PlotDict["All"] = plot

        # Reconfig the plots to be sure
        self.PlotDict["All"].opts(opts.Bars(stacked=True))
        self.PlotDict["All"] = config_layout(
            self.PlotDict["All"],
            **self.config.get(self.analysisname, {}).get("Layout", {})
        )
        return self.PlotDict

    def accumulated_all_countries_normalizes(self, countryName, inhabitants):

        # Normalize to mio inhabitants
        factor = float(inhabitants) / 1e6

        # Change data
        for data in ["confirmed", "deaths", "recovered"]:
            self.data["Accumulated"]["data"][data] = (
                self.data["Accumulated"]["data"][data] / factor
            )
            # self.data["Accumulated"]["data"].insert(0, "{}Norm".format(data), self.data["Accumulated"]["data"][data]/factor) # Not very efficient
            # self.data["Accumulated"]["measurements"].append(data)
            # self.data["Accumulated"]["units"].append("#/1e6")
            # self.data["columns"].append("{}Norm".format(data))
            # self.config["COVID19"]["{}Norm".format(data)] = self.config["COVID19"][data]

        # Plot total Cases for all countries in one plot
        acc = plot(
            self.data,
            self.config,
            "Date",
            "COVID19",
            keys=["Accumulated"],
            do_not_plot=["Date", "deaths", "recovered", "DeathsNorm", "RecoveredNorm"],
            PlotLabel="{}".format(countryName),
        )
        if self.casesNorm:
            self.casesNorm *= acc
        else:
            self.casesNorm = acc

        # Plot total Recovered for all countries in one plot
        rec = plot(
            self.data,
            self.config,
            "Date",
            "COVID19",
            keys=["Accumulated"],
            do_not_plot=["Date", "deaths", "confirmed", "DeathsNorm", "ConfirmedNorm"],
            PlotLabel="{}".format(countryName),
        )
        if self.recoveredNorm:
            self.recoveredNorm *= rec
        else:
            self.recoveredNorm = rec

        # Plot total Death for all countries in one plot
        deaths = plot(
            self.data,
            self.config,
            "Date",
            "COVID19",
            keys=["Accumulated"],
            do_not_plot=[
                "Date",
                "recovered",
                "confirmed",
                "RecoveredNorm",
                "ConfirmedNorm",
            ],
            PlotLabel="{}".format(countryName),
        )
        if self.deathsNorm:
            self.deathsNorm *= deaths
        else:
            self.deathsNorm = deaths

    def accumulated_all_countries(self, countryName):
        """ACCUMULATED PLOTS ALL COUNTRIES TOGETHER"""
        # Plot total Cases for all countries in one plot
        acc = plot(
            self.data,
            self.config,
            "Date",
            "COVID19",
            keys=["Accumulated"],
            do_not_plot=["Date", "deaths", "recovered"],
            PlotLabel="{}".format(countryName),
        )
        if self.cases:
            self.cases *= acc
        else:
            self.cases = acc

        # Plot total Recovered for all countries in one plot
        rec = plot(
            self.data,
            self.config,
            "Date",
            "COVID19",
            keys=["Accumulated"],
            do_not_plot=["Date", "deaths", "confirmed"],
            PlotLabel="{}".format(countryName),
        )
        if self.recovered:
            self.recovered *= rec
        else:
            self.recovered = rec

        # Plot total Death for all countries in one plot
        deaths = plot(
            self.data,
            self.config,
            "Date",
            "COVID19",
            keys=["Accumulated"],
            do_not_plot=["Date", "recovered", "confirmed"],
            PlotLabel="{}".format(countryName),
        )
        if self.deaths:
            self.deaths *= deaths
        else:
            self.deaths = deaths

    def relgrowth_all_countries(self, countryName):
        """ACCUMULATED PLOTS ALL COUNTRIES TOGETHER"""
        # Plot total Cases for all countries in one plot
        acc = plot(
            self.data,
            self.config,
            "Date",
            "COVID19",
            keys=[
                "RelativeGrowth*{}".format(self.config["COVID19"]["GrowingRateMulti"])
            ],
            do_not_plot=["Date", "deaths", "recovered"],
            PlotLabel="{}".format(countryName),
            ylabel="Confirmed (%)",
        )
        if self.casesrelgrowth:
            self.casesrelgrowth *= acc
        else:
            self.casesrelgrowth = acc

        # Plot total Recovered for all countries in one plot
        rec = plot(
            self.data,
            self.config,
            "Date",
            "COVID19",
            keys=[
                "RelativeGrowth*{}".format(self.config["COVID19"]["GrowingRateMulti"])
            ],
            do_not_plot=["Date", "deaths", "confirmed"],
            PlotLabel="{}".format(countryName),
            ylabel="Recovered (%)",
        )
        if self.recoveredrelgrowth:
            self.recoveredrelgrowth *= rec
        else:
            self.recoveredrelgrowth = rec

        # Plot total Death for all countries in one plot
        deaths = plot(
            self.data,
            self.config,
            "Date",
            "COVID19",
            keys=[
                "RelativeGrowth*{}".format(self.config["COVID19"]["GrowingRateMulti"])
            ],
            do_not_plot=["Date", "recovered", "confirmed"],
            PlotLabel="{}".format(countryName),
            ylabel="Deaths (%)",
        )
        if self.deathsrelgrowth:
            self.deathsrelgrowth *= deaths
        else:
            self.deathsrelgrowth = deaths
