
import logging
import holoviews as hv
import pandas as pd
from numpy import log
from scipy.signal import savgol_filter

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout
from forge.PQC_analysis_funktions import first_derivative, interpolate


class FET:
    def __init__(self, data, configs):
        for file in list(data.keys()):
            if "FET" not in data[file]["header"][3]:
                data.pop(file)
        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=False)
        self.config = configs
        self.basePlots = None
        self.analysisname = "FET"
        self.PlotDict = {"Name": self.analysisname}
        self.measurements = self.data["columns"]

        self.PlotDict["All"] = None
        self.do_analysis_1 = True
        self.do_analysis_2 = True
        self.do_analysis_3 = True
        self.df = pd.DataFrame(columns=["Name",  "_", "Batch", "Wafer No.", "_", "_", "HM location", "Test structure",
                                         "ELR Method", "Second Derivative", "Second Derivative log"])
        self.sort_parameter = self.config["FET"]["Bar_chart"]["CreateBarChart"]

        '''turns all headers into dictionaries and creates entries in self.data '''
        for file in self.data["keys"]:
            self.data[file]["Ana 1"] = "_"
            self.data[file]["Ana 2"] = "_"
            self.data[file]["Ana 3"] = "_"
            self.data[file]["header"] = self.list_to_dict(self.data[file]["header"])

    def list_to_dict(self, rlist):
        return dict(map(lambda s: map(str.strip, s.split(':', 1)), rlist))

    def run(self):
        if self.do_analysis_1:
            self.analysis("Ana 1")
        if self.do_analysis_2:
            self.analysis("Ana 2")
        if self.do_analysis_3:
            self.analysis("Ana 3")
        self.create_table()
        self.create_bars()
        return self.PlotDict

    def analysis(self, ana_type):
        for file in self.data["keys"]:
            '''deletes rows with duplicates in xaxis, and interpolates x and y'''
            self.data[file]["data"] = self.data[file]["data"].drop_duplicates(subset=[self.measurements[1]], keep='first')
            x, y = self.data[file]["data"][self.measurements[1]], self.data[file]["data"][self.measurements[3]]
            x, y = interpolate(list(x), list(y), stepsize=0.05)

            '''Ana 1: dy=first derivative, Ana 2: dy=second derivative, Ana 3: dy=second derivative of log(y)'''
            dy = self.derivative_wrapper(x, y, ana_type) #uses savgol filter
            self.plot_ana(x, y, dy, file, ana_type)

    def derivative_wrapper(self, x, y, ana_type):
        '''Ana 1: dy=first derivative, Ana 2: dy=second derivative, Ana 3: dy=second derivative of log(y)'''
        window_size = 11
        poly_deg = 3
        if ana_type == "Ana 1":
            y = savgol_filter(y, window_size, poly_deg)
            dy = first_derivative(x, y)
        elif ana_type == "Ana 2":
            y = savgol_filter(y, window_size, poly_deg)
            dy = first_derivative(x, y)
            dy = first_derivative(x, dy)

        elif ana_type =="Ana 3":
            y = savgol_filter(y, window_size, poly_deg)
            dy = first_derivative(x, log(y))
            dy = first_derivative(x, dy)
            dy[:] = [value / (2 * 10**6) for value in dy]
        return dy

    '''adds holoviews object to plot dict, and voltage to self.data '''
    def plot_ana(self, x, y, dy, file, ana_type):
        curve = hv.Curve(zip(x, y), kdims=self.measurements[1], vdims=self.measurements[2])
        derivative = hv.Curve(zip(x, dy)).opts(color="gray")
        df = pd.DataFrame({"x": x, "y": y, "dy": dy})

        '''returns voltage and: for Ana 1 fit line, for Ana 2/3 line to show where the voltage is'''
        voltage, line = self.find_voltage(df, x, ana_type)
        voltage = round(voltage, 4)

        text_str = "voltage: " + str(voltage)
        if ana_type == "Ana 3":
            text_str += "\nDerivative scaled down by: \n/ (2 * 10^6)"
        text = hv.Text(min(dy) * (6 / 4), max(dy) * (7 / 8), text_str, fontsize=20)

        curve = curve * derivative * line * text
        if ana_type == "Ana 3":
            curve.opts(**self.config["FET"].get("General", {}), ylim=(min(dy) - 3 * min(y) / 20, max(dy) + max(dy) / 10))
        else:
            curve.opts(**self.config["FET"].get("General", {}), ylim=(min(y) - 3 * min(y) / 20, max(y) + max(y) / 10))

        self.data[file][ana_type] = voltage
        if self.PlotDict["All"] is None:
            self.PlotDict["All"] = curve
        else:
            self.PlotDict["All"] = self.PlotDict["All"] + curve


    def find_voltage(self, df, x, ana_type):
        '''returns voltage and: for Ana 1 fit line, for Ana 2/3 line to mark voltage'''
        if ana_type == "Ana 1":
            df = df[df.dy == df.dy.max()]
            inflection_x, inflection_y, slope = df['x'].iloc[0], df['y'].iloc[0], df['dy'].iloc[0]
            d = inflection_y - slope * inflection_x
            voltage = -d / slope # y = kx + d --> x = (y-d)/k with x = 0

            fit_line = [[0, d], [x[-1], x[-1] * slope + d]]
            fit_line = hv.Curve(fit_line).opts(color="red", line_width=1.5)
            return voltage, fit_line

        elif ana_type == "Ana 2":
            df = df[df.dy == df.dy.max()]
            voltage = df['x'].iloc[0]
            line = hv.VLine(voltage).opts(color="black", line_width=1.0)
            return voltage, line

        elif ana_type == "Ana 3":
            df = df[df.dy == df.dy.min()]
            voltage = df['x'].iloc[0]
            line = hv.VLine(voltage).opts(color="black", line_width=1.0)
            return voltage, line

    def create_table(self):
        '''fills the data frame so data can later be grouped by keyword ("Vendor", "Batch" etc.)'''
        for file in self.data["keys"]:
            ana_1 = self.data[file]["Ana 1"]
            ana_2 = self.data[file]["Ana 2"]
            ana_3 = self.data[file]["Ana 3"]
            value_list = [key for key in self.data[file]["header"]["sample_name"].split("_")]
            value_list2 = [key for key in self.data[file]["header"]["sample_type"].split("_")]
            value_list = [file] + value_list + value_list2 + [ana_1, ana_2, ana_3]

            dic = dict(zip(self.df.keys(), value_list))
            self.df = self.df.append(dic, ignore_index=True)

        del self.df["_"]
        table = hv.Table(self.df)
        table.opts(width=1300, height=800)
        self.PlotDict["All"] = self.PlotDict["All"] + table

    def create_bars(self):
        '''creates labels so each bar consists of the right group '''
        labels = ["Batch", "Wafer No.", "HM location", "Test structure"]
        labels.remove(self.sort_parameter)

        '''Groupes firstly by sort_parameter after that by labens , Calculates mean if all labels are equivalent'''

        for group in self.df.groupby(self.sort_parameter): #groups by whatever you choose so batch etc.
            innermost_groups = group[1].groupby(labels) #each group in innermost_groups corresponds to a group of 3 bars
            ana1_l = innermost_groups["ELR Method"].mean()
            ana2_l = innermost_groups["Second Derivative"].mean()
            ana3_l = innermost_groups["Second Derivative log"].mean()

            keys = ["/".join(key) for key in innermost_groups.groups.keys()]

            '''creates new df so its easier to create grouped barchart hv.object  basicly like df.melt'''
            bar_df = pd.DataFrame(columns=["labels", "ELR Method", "Second Derivative", "Second Derivative log"])
            for i, key in enumerate(keys):
                dic_1 = {"labels": key, "Method": "ELR Method", "Voltage": ana1_l[i]}
                dic_2 = {"labels": key, "Method": "Second Derivative", "Voltage": ana2_l[i]}
                dic_3 = {"labels": key, "Method": "Second Derivative log", "Voltage": ana3_l[i]}

                bar_df = bar_df.append(dic_1, ignore_index=True)
                bar_df = bar_df.append(dic_2, ignore_index=True)
                bar_df = bar_df.append(dic_3, ignore_index=True)

            bar_grouped = hv.Bars(data=bar_df, kdims=["labels", "Method"], vdims=["Voltage"])
            bar_grouped.opts(width=1000, height=400, xlabel='', ylabel='Voltage [V]',
                             title=self.sort_parameter + ": " + group[0], xrotation=45)
            self.PlotDict["All"] = self.PlotDict["All"] + bar_grouped