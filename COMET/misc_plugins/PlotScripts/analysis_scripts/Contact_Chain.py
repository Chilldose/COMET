
import logging
import holoviews as hv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from forge.tools import convert_to_df

class Contact_Chain:
    def __init__(self, data, configs):
        '''removes wrong data'''
        for file in list(data.keys()):
            if "contact chain" not in data[file]["header"][3].lower():
                data.pop(file)

        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=False)
        self.config = configs
        self.df = []
        self.basePlots = None
        self.analysisname = "Contact_Chain"
        self.PlotDict = {"Name": self.analysisname}
        self.measurements = self.data["columns"]

        self.sort_parameter = self.config["Contact_Chain"]["Bar_chart"]["CreateBarChart"]
        self.Substrate_Type = ["Polysilicon", "N+", "P+"]
        self.filename_df = pd.DataFrame(
            columns=["Filename", "Substrate Type", "_", "Batch", "Wafer No.", "_", "HM location",
                     "Test structure", "Resistance", "Standard deviation"])
        self.PlotDict["All"] = None
        self.limits = {"Polysilicon": 4*10**7, "N+": 10**5, "P+": 8 * 10**4}
        self.files_to_fit = self.config["files_to_fit"]

        hvtext = hv.Text(0, 0, self.analysisname, fontsize=20).opts(color="black", xlabel='', ylabel='')
        box = hv.Polygons(hv.Box(0, 0, 1).opts(color="black")).opts(color="white")
        self.PlotDict["All"] = box * hvtext

    def list_to_dict(self, rlist):
        return dict(map(lambda s: map(str.strip, s.split(':', 1)), rlist))

    def run(self):
        '''turns all headers into dictionaries and fills file_name_df'''
        for file in self.data["keys"]:
            self.data[file]["header"] = self.list_to_dict(self.data[file]["header"])
            resistance, std = self.calculate_resistance(file)
            self.fill_filename_df(file, resistance, std)
        del self.filename_df["_"]

        '''groups barcharts by Substrate Type and then by given parameter'''
        for substrate in self.filename_df.groupby("Substrate Type"):
            for group in substrate[1].groupby(self.sort_parameter):
                self.create_barchart(group[1], group[0], substrate[0])

        self.create_table()
        if self.files_to_fit:
            for file in self.files_to_fit:
                self.create_fit(file)
        return self.PlotDict

    def calculate_resistance(self, file, fit=False):
        '''calculates sheet resistance of given file, returns resistance and correspondinge standard deviation'''
        resistance = 0
        '''Linear regression'''
        x = self.data[file]["data"]["current"]
        y = self.data[file]["data"]["voltage_vsrc"]
        coef, cov_matrix = np.polyfit(x, y, 1, cov=True)
        line = coef[0] * x + coef[1]

        '''calculate sheet Resistance and standard deviation'''
        resistance += coef[0]
        variance = cov_matrix[0][0]
        std = np.sqrt(variance)

        if fit:
            return resistance, std, line
        return resistance, std

    def create_barchart(self, group_df, group_name, substrate):
        '''Calculates mean if all labels are equivalent'''
        labels = ["Batch", "Wafer No.", "HM location", "Test structure"]
        labels.remove(self.sort_parameter)
        innermost_groups = group_df.groupby(labels)
        r_mean = innermost_groups["Resistance"].mean() ##calculate the error that happens here

        '''creates chart data and BarChart Object'''
        keys = ["/".join(key) for key in innermost_groups.groups.keys()]
        chart_data = [(label, resistance) for label, resistance in zip(keys, r_mean)]
        labels = "/".join(labels)
        chart = hv.Bars(chart_data, hv.Dimension(labels), "Resistance")

        '''calculates std_mean with error propagation'''
        std_mean_l = []
        for group in innermost_groups: #each group corresponds to a bar
            std_mean2 = 0
            for i in group[1]["Standard deviation"]:
                std_mean2 += (i/len(group[1]["Standard deviation"]))**2
            std_mean2 = np.sqrt(std_mean2)
            std_mean_l.append(std_mean2)

        '''calculate error of r_mean '''
        r_mean_error = []
        for index, group in enumerate(innermost_groups):
            diff_from_mean = 0
            group_mean = r_mean[index]
            for i in group[1]["Resistance"]:
                if len(group[1]["Resistance"]) > 1:
                    diff_from_mean += ((i - group_mean)**2/(len(group[1]["Resistance"])-1))
            diff_from_mean = np.sqrt(diff_from_mean)
            r_mean_error.append(diff_from_mean)

        error = [max(i, j) for i, j in zip(r_mean_error, std_mean_l)]

        '''creates errorbars and configures the plot'''
        error_bars = hv.ErrorBars((keys, r_mean, error))
        error_bars.opts(line_width=5)
        chart = chart * error_bars
        #chart = error_bars

        chart.opts(title=substrate + " " + group_name, **self.config["Van_der_Pauw"].get("General", {}),
                   ylim=(0, self.limits[substrate]), xrotation=45)

        if self.PlotDict["All"] is None:
            self.PlotDict["All"] = chart
        else:
            self.PlotDict["All"] = self.PlotDict["All"] + chart

    def fill_filename_df(self, file, resistance, std):
        '''fills the data frame so data can later be grouped by keyword ("Vendor", "Batch" etc.)'''
        value_list = [key for key in self.data[file]["header"]["sample_name"].split("_")]
        value_list2 = [key for key in self.data[file]["header"]["sample_type"].split("_")]
        for subs in self.Substrate_Type:
            if subs in self.data[file]["header"]["measurement_name"]:
                value_list = [file, subs] + value_list + value_list2

        dic = dict(zip(self.filename_df.keys(), value_list))
        dic["Resistance"] = resistance
        dic["Standard deviation"] = std
        self.filename_df = self.filename_df.append(dic, ignore_index=True)

    def create_table(self):
        self.filename_df["Standard deviation"] = self.filename_df["Standard deviation"].apply(np.format_float_scientific, args=[3])
        self.filename_df["Resistance"] = self.filename_df["Resistance"].apply(np.format_float_scientific, args=[3])


        table = hv.Table(self.filename_df)
        table.opts(width=1300, height=800)
        self.PlotDict["All"] = self.PlotDict["All"] + table

    def create_fit(self, filename):
        if filename in self.data["keys"]:
            resistance, std, fit = self.calculate_resistance(filename, fit=True)
            x = self.data[filename]["data"]["current"]
            y = self.data[filename]["data"]["voltage_vsrc"]
            scatter = hv.Scatter((x, y), kdims=self.measurements[1], vdims=self.measurements[2])
            scatter.opts(color='green')
            curve = scatter * hv.Curve((x, fit))
            curve.opts(**self.config["Van_der_Pauw"].get("General", {}), xrotation=45,
                       title="Index: " + str(self.filename_df.loc[self.filename_df['Filename'] == filename].index[0]),
                       ylim=(np.sign(y.min()) * abs(y.min()) - abs((y.max() - y.min()) * (1/8)), y.max() * (9/8)))
                        #just a complicated way to set ylim() because ymin() can be < or > 0
            self.PlotDict["All"] = self.PlotDict["All"] + curve
