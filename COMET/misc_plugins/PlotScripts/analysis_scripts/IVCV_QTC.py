"""This script plots IVCV files together for files generated by QTC
Data must be """

import logging, os
import holoviews as hv
from holoviews import opts
from scipy.stats import linregress
from copy import deepcopy
import pandas as pd
import numpy as np
hv.extension('bokeh', 'matplotlib')

from bokeh.models import CustomJS
from bokeh.models.widgets import Button

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout, text_box
from forge.tools import twiny, relabelPlot, applyPlotOptions, rename_columns
from forge.tools import plot_all_measurements, convert_to_EngUnits
from forge.specialPlots import dospecialPlots
from forge.utilities import line_intersection


class IVCV_QTC:

    def __init__(self, data, configs):

        self.log = logging.getLogger(__name__)
        self.config = configs
        self.analysisName = "IVCV_QTC"
        self.data = convert_to_df(data, abs=True)
        self.data = rename_columns(self.data, self.config[self.analysisName].get("Measurement_aliases", {}))
        self.basePlots = None
        self.PlotDict = {"Name": "IVCV"} # Name of analysis and cnavas for all plots generated during this analysis
        self.capincluded = False
        if "capacitance" in self.data[self.data["keys"][0]]["data"] or "CV" in self.data[self.data["keys"][0]]["data"]:
            self.data["columns"].insert(3, "1C2") # because we are adding it later on
            self.capincluded = True
        self.measurements = self.data["columns"]
        self.xaxis = self.measurements[0]

        # The do not plot list, you can extend this list as you like
        self.donts = ("Name", "voltage_1", "Idark", "Idiel", "Rpoly", "Cac", "Cint", "Rint", "Pad", "Istrip")

        if "voltage" in self.measurements:
            self.xaxis = "voltage"
            padidx = self.measurements.index("voltage")
            del self.measurements[padidx]
        else:
            self.log.error("No 'voltage' entry found in data, cannot do IVC analysis. Maybe you have to set an alias for your measurement.")

        # Convert the units to the desired ones
        for meas in self.measurements:
            unit = self.config[self.analysisName].get(meas, {}).get("UnitConversion", None)
            if unit:
                self.data = convert_to_EngUnits(self.data, meas, unit)
        hv.renderer('bokeh')

    def run(self):
        """Runs the script"""

        # Add the 1/c^2 data to the dataframes
        for df in self.data["keys"]:
            if "CV" in self.data[df]["data"]:
                self.data[df]["data"].insert(3, "1C2", 1 / self.data[df]["data"]["CV"].pow(2))
                self.data[df]["units"].append("arb. units")
                self.data[df]["measurements"].append("1C2")
            elif "capacitance" in self.data[df]["data"]:
                self.data[df]["data"].insert(3, "1C2", 1 / self.data[df]["data"]["capacitance"].pow(2))
                self.data[df]["units"].append("arb. units")
                self.data[df]["measurements"].append("1C2")

        # Add the measurement to the list

        # Plot all Measurements
        self.basePlots = plot_all_measurements(self.data, self.config, self.xaxis, self.analysisName, do_not_plot = self.donts)
        #self.basePlots = applyPlotOptions(self.basePlots, {'Curve': {'color': "hv.Cycle('PiYG')"}})
        self.PlotDict["BasePlots"] = self.basePlots
        self.PlotDict["All"] = self.basePlots

        # Add full depletion point to 1/c^2 curve
        if self.config[self.analysisName].get("1C2", {}).get("DoFullDepletionCalculation", False):
            try:
                if self.basePlots.Overlay.CV_CURVES_hyphen_minus_Full_depletion.children:
                    c2plot = self.basePlots.Overlay.CV_CURVES_hyphen_minus_Full_depletion.opts(clone = True)
                else: c2plot = self.basePlots.Curve.CV_CURVES_hyphen_minus_Full_depletion.opts(clone = True)
                fdestimation = self.find_full_depletion(c2plot, self.data, self.config, PlotLabel="Full depletion estimation")
                self.PlotDict["All"] += fdestimation
                self.PlotDict["BasePlots"] += fdestimation
            except Exception as err:
                self.log.warning("No full depletion calculation possible... Error: {}".format(err))

        # Whiskers Plot
        self.WhiskerPlots = dospecialPlots(self.data, self.config, self.analysisName, "BoxWhisker", self.measurements)
        if self.WhiskerPlots:
            self.PlotDict["Whiskers"] = self.WhiskerPlots
            self.PlotDict["All"] = self.PlotDict["All"] + self.WhiskerPlots

        # Histogram Plot
        self.HistogramPlots = dospecialPlots(self.data, self.config, self.analysisName, "Histogram",
                                            self.measurements)
        if self.HistogramPlots:
            self.PlotDict["Histogram"] = self.HistogramPlots
            self.PlotDict["All"] = self.PlotDict["All"] + self.HistogramPlots

        # Reconfig the plots to be sure
        self.PlotDict["All"] = config_layout(self.PlotDict["All"], **self.config[self.analysisName].get("Layout", {}))

        return self.PlotDict

    def calculate_slopes(self, df, minSize, startidx=0):
        """
        Calculates two slopes one starting vom left and on starting from right. It checks if the r^2 value has increased
        and returns the r2 value as well as the slope parameters as tuples
        :param df: Data frame
        :param minSize: minumum size to start linregress
        :param startidx: startindex top start the calculation (cut the beginning eg)
        :return: LR2, Lparameters, RR2, Rparameters
        """

        # Calculate the slopes from the right and the left
        LR2 = 0  # r^2 values for both sides
        RR2 = 0
        lpp = 9999
        rpp = 9999
        Right_stats = 0
        Left_stats = 0
        for endidx in range(minSize+startidx, len(df)-startidx-minSize+1):  # Start a 5 since the linear fit needs at least a few values to work
            # Left slope
            slope_left, intercept_left, r_left, lp_value, std_err_left = linregress(df["xaxis"][startidx:endidx], df["yaxis"][startidx:endidx])
            r2_left = r_left * r_left
            self.log.debug("Left side fit: Slope {}, intercept: {}, r^2: {}, std: {}".format(
                slope_left, intercept_left, r2_left, std_err_left)
            )

            # Right slope
            slope_right, intercept_right, r_right, rp_value, std_err_right = linregress(df["xaxis"][-endidx:-startidx-1], df["yaxis"][-endidx:-startidx-1])
            r2_right = r_right * r_right
            self.log.debug("Right side fit: Slope {}, intercept: {}, r^2: {}, std: {}".format(
                slope_right, intercept_right, r2_right, std_err_right)
            )

            # See if the r2 value has increased and store end points
            if r2_left>LR2 and lp_value<lpp:
                LR2 = r2_left
                lpp =lp_value
                LeftEndPoints = (
                    (df["xaxis"][0], intercept_left),
                    (df["xaxis"][endidx], slope_left * df["xaxis"][endidx] + intercept_left)
                )
                Left_stats = (LeftEndPoints, slope_left, intercept_left, r_left, lp_value, std_err_left)

            # See if the r2 value has increased and store it
            if r2_right>RR2 and rp_value<rpp:
                RR2 = r2_right
                rpp = rp_value
                RightEndPoints = (
                    (df["xaxis"][endidx], slope_right * df["xaxis"][endidx] + intercept_right),
                    (df["xaxis"][len(df["xaxis"]) - 1], slope_right * df["xaxis"][len(df["xaxis"]) - 1] + intercept_right),
                )
                Right_stats = (RightEndPoints, slope_right, intercept_right, r_right, rp_value, std_err_right)

        return LR2, Left_stats, RR2, Right_stats

    def find_full_depletion(self, plot, data, configs, **addConfigs):
        """
        Finds the full depletion voltage of all data samples and adds a vertical line for the full depletion in the
        plot. Vertical line is the mean of all measurements. Furthermore, adds a text with the statistics.
        :param plot: The plot object
        :param data: The data files
        :param configs: the configs
        :param **addConfigs: the configs special for the 1/C2 plot, it is recomended to pass the same options here again, like in the original plot!
        :return: The updated plot
        """

        full_depletion_voltages = np.zeros((len(data["keys"]), 2))
        Left_stats = np.zeros((len(data["keys"]), 6), dtype=np.object)
        Right_stats = np.zeros((len(data["keys"]), 6), dtype=np.object)
        self.log.info("Searching for full depletion voltage in all files...")

        for i, samplekey in enumerate(data["keys"]):
            if "1C2" not in data[samplekey]["data"]:
                self.log.warning("Full depletion calculation could not be done for data set: {}".format(samplekey))

            else:
                self.log.debug("Data: {}".format(samplekey))
                sample = deepcopy(data[samplekey])
                try:
                    df = sample["data"][["voltage", "1C2"]].rename(columns={"voltage": "xaxis", "1C2": "yaxis"})
                except:
                    df = sample["data"][["Voltage", "1C2"]].rename(columns={"Voltage": "xaxis", "1C2": "yaxis"})
                df = df.dropna()

                # Loop one time from the right side and from the left, to get both slopes
                LR2, Left_stats[i], RR2, Right_stats[i] = self.calculate_slopes(df, minSize=5, startidx=5)

                # Make the line intersection
                full_depletion_voltages[i] = line_intersection(Left_stats[i][0], Right_stats[i][0])
                self.log.info("Full depletion voltage to data file {} is {}, with LR^2={} and RR^2={}".format(samplekey, full_depletion_voltages[i], LR2, RR2))

        # Add vertical line for full depletion
        # Calculate the mean of all full depeltion voltages and draw a line there
        valid_indz = np.nonzero(full_depletion_voltages[:, 0])
        vline = hv.VLine(np.mean(full_depletion_voltages[valid_indz], axis=0)[0]).opts(color='black', line_width=5.0)

        # Add slopes
        xmax = df["xaxis"][len(df["yaxis"])-1]
        left_line = np.array([[0, np.median(Left_stats[:,2])],[xmax, np.median(Left_stats[:,1])*xmax + np.median(Left_stats[:,2])]])
        left_line = hv.Curve(left_line).opts(color='grey')

        right_line = np.array([[0, np.median(Right_stats[:,2])],[xmax, np.median(Right_stats[:,1])*xmax + np.median(Right_stats[:,2])]])
        right_line = hv.Curve(right_line).opts(color='grey')

        # Add text
        self.log.info('Full depletion voltage: {} V, '
                        'Error: {} V'.format(np.round(np.median(full_depletion_voltages[valid_indz, 0]), 2),
                                           np.round(np.std(full_depletion_voltages[valid_indz, 0]), 2)))
        #text = hv.Text(np.mean(full_depletion_voltages[valid_indz], axis=0)[0]*2, np.mean(full_depletion_voltages[valid_indz], axis=0)[1]*1.2, 'Depletion voltage: {} V \n'
        #                'Error: {} V'.format(np.round(np.mean(full_depletion_voltages[:, 0]), 2),
        #                                   np.round(np.std(full_depletion_voltages[valid_indz, 0]), 2))
        #               ).opts(fontsize=30)

        bounds = np.mean(full_depletion_voltages[valid_indz], axis=0)
        text = text_box('Depletion voltage: {} V \n'
                        'Error: {} V'.format(np.round(np.mean(full_depletion_voltages[:, 0]), 2),
                                           np.round(np.std(full_depletion_voltages[valid_indz, 0]), 2)),
                       np.mean(full_depletion_voltages[valid_indz], axis=0)[0] * 2,
                       np.mean(full_depletion_voltages[valid_indz], axis=0)[1] * 1.3,
                       boxsize= (200, bounds[1]*0.3)
                       )
        # Update the plot specific options if need be
        returnPlot = vline * right_line * left_line * text * plot
        #returnPlot = relabelPlot(returnPlot, "CV CURVES - Full depletion calculation")
        returnPlot = customize_plot(returnPlot, "1C2", configs[self.analysisName], **addConfigs)



        return returnPlot