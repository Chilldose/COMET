"""Simply plots all data as curve plots"""

"""This script is just a template out of which you can build your own analysis"""

import logging
import holoviews as hv

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout
from forge.tools import twiny, relabelPlot
from forge.tools import plot_all_measurements, convert_to_EngUnits
from forge.tools import plot
from forge.specialPlots import dospecialPlots
from forge.utilities import line_intersection


class GCD:
    def __init__(self, data, configs):

        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=False)
        self.config = configs
        self.df = []
        self.basePlots = None
        self.analysisname = "GCD"
        self.PlotDict = {"Name": self.analysisname}
        self.measurements = self.data["columns"]
        # hv.renderer('bokeh')

    def run(self):
        """Runs the script"""


        for it ,entry in enumerate(self.data["keys"]):
            print( entry)
            currents = self.data[entry]["data"]["Current"].values
            plateau = self.config[self.analysisname].get("plateau", 0.02)
            sum = 0
            n = 0
            voltages = self.data[entry]["data"]["Voltage"].values       
            for i in range(len(currents)): 
                 #print(currents[len(currents)-1-i])
                 if 1-(currents[len(currents)-1-i]/currents[len(currents)-1-i-1]) > plateau: 
                     sum = 0
                     for j in range(i):
                         sum += currents[len(currents)-1-j]
                     n = i
                     print(voltages[len(voltages)-1-i])
                     break

            ave = sum*1./n          
            maximum = max(currents)
            diff = maximum - ave
            #s0 = diff/(1.6e-19*5.415e9*0.00505) #flute2
            s0 = diff/(1.6e-19*5.415e9*0.00723) #flute4
            print("max =",maximum)
            print("average =",ave)
            print("diff =",diff)   
            print("s0 =",s0)
            myvalue = "%.3f" % s0
            name = "_".join(entry.split("_")[2:5]) 
            label = name + "_s0 = " + myvalue + " cm/s"
            label = label.replace("-","_")
            self.data["keys"][it] = label
            self.data[label] = self.data.pop(entry)
            #print(self.data["HPK_VPX33234-001_PSS_HM-WW_1stflute2_GCD_27_5_2020_9h7m27s"]["data"]["Current"].values[-1])

            #print(self.config[self.analysisname].get("plateau", 0.02))

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
            self.measurements[0],
            self.analysisname,
            do_not_plot=[self.measurements[0]],
        )

        self.PlotDict["All"] = self.basePlots

        #print(type(self.PlotDict["All"]))
        return self.PlotDict
