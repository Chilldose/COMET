

class brown_preanalysis:

    def __init__(self, data, configs):

        import numpy as np

        self.data = data
        self.config = configs

        for file in data.keys():
            # Adding units
            Headers = data[file]["measurements"]
            Units = []
            print(len(Headers), Headers)
            for i in Headers:
                if ("I_" in i) or ("G" in i):
                    Units.append("A")
                elif "T" in i:
                    Units.append("C")
                elif "C" in i:
                    Units.append("F")
                elif "RH" in i:
                    Units.append("%")
                elif "Strip" in i:
                    Units.append("#")
                else:
                    Units.append("A")
            print ("Units", len(Units), Units)
            data[file]["units"] = Units

            # Adding calculated measurements to list
            data[file]["measurements"].append("Rpoly")
            data[file]["units"].append("Ohm")
            data[file]["measurements"].append("Rpoly_nbr")
            data[file]["units"].append("Ohm")
            data[file]["measurements"].append("Rint")
            data[file]["units"].append("Ohm")
            data[file]["measurements"].append("Rint_Chi")
            data[file]["units"].append("Chi2")

            polarity = -1

            # Get open capacitance measurements from header
            currentLine = data[file]["header"][0]
            for currentLine in data[file]["header"]:
                print (currentLine)
                if 'Hz' in currentLine:  # This is just looking at possible positions for cap offsets.
                    if 'Not Measured' not in currentLine:
                        if 'and' in currentLine:
                            cc_offset = float(currentLine.split()[5])
                            print("Coupling Capacitance Offset", cc_offset)
                            ic_offset = float(currentLine.split()[6])
                            print("Interstrip Capacitance Offset", ic_offset)
                        elif '1000Hz' in currentLine:
                            cc_offset = float(currentLine.split(':')[1])
                            print("Coupling Capacitance Offset", cc_offset)
                        elif '1000000Hz' in currentLine:
                            ic_offset = float(currentLine.split(':')[1])
                            print("Interstrip Capacitance Offset", ic_offset)
                    else:  # if an offset measurement is not made then value will be in slightly different place on the line.
                        if currentLine.split()[5] == 'Not':
                            cc_offset = 0
                            if currentLine.split()[7] == 'Not':
                                ic_offset = 0
                            else:
                                ic_offset = float(currentLine.split()[7])
                        else:
                            cc_offset = float(currentLine.split()[5])
                            if currentLine.split()[6] == 'Not':
                                ic_offset = 0
                            else:
                                ic_offset = float(currentLine.split()[6])

                if 'Type' in currentLine:
                    if 'N' in currentLine:
                        polarity = 1


            # Get RPoly and Inter R steps
            RPolySteps = [0.0]
            InterRSteps = []
            for idx in [i for i, val in enumerate(Headers) if 'I_RBias_V' in val]:
                RBiasVStr = Headers[idx].replace('I_RBias_V', '')
                RPolySteps.append(float(RBiasVStr))
            for idx in [i for i, val in enumerate(Headers) if 'I_InterstripR_V' in val]:
                InterRSteps.append(float(Headers[idx].replace('I_InterstripR_V', '')))
            #print (RPolySteps, InterRSteps)

            IstripNbr = [np.nan]
            RPoly = []
            RPolyNbr = [np.nan]
            InterR = []
            InterR_Chi = []
            print ("Measurements:", len(data[file]["data"]["Strip"]))
            for strip in range(len(data[file]["data"]["Strip"]) - 1):
            #for strip in range(len(data[file]["data"]["Strip"])):
                #print ("Strip: ", strip)
                RBiasCurr = []
                RBiasNbrCurr = []
                InterRCurr = []
                IstripNbr.append(data[file]["data"]["IstripNbr_Median"][strip] * polarity)
                RBiasCurr.append(data[file]["data"]["Istrip_Median"][strip])
                RBiasNbrCurr.append(data[file]["data"]["IstripNbr_Median"][strip])
                #RBiasCurr.append(strip["Median"])
                #RBiasNbrCurr.append(strip["MedianNbr"])
                for i in range(len(RPolySteps) - 1):
                    RBiasName = "I_RBias_V" + RBiasVStr
                    RBiasNbrName = "I_RBias Nbr_V" + RBiasVStr
                    RBiasCurr.append(data[file]["data"][RBiasName][strip])
                    RBiasNbrCurr.append(data[file]["data"][RBiasNbrName][strip])

                #print (strip, RPolySteps, RBiasCurr)
                RPoly.append(np.polyfit(RBiasCurr,RPolySteps,1)[0])
                RPolyNbr.append(np.polyfit(RBiasNbrCurr, RPolySteps, 1)[0])
                #data[file]["data"]["Rpoly"][strip] = np.polyfit(RPolySteps,RBiasCurr,1)[0]
                #data[file]["data"]["RpolyNbr"] = np.polyfit(RPolySteps, RBiasNbrCurr,1)[0]

                if len(InterRSteps) > 0:
                    if data[file]["data"]["I_InterstripR_V" + str(InterRSteps[0])][strip] != 0:
                        for i in range(len(InterRSteps)):
                            InterRCurr.append(data[file]["data"]["I_InterstripR_V" + str(InterRSteps[i])][strip])
                        #print(InterRSteps, InterRCurr)
                        interR_fit = np.polyfit(InterRCurr, InterRSteps, 1)
                        InterR.append(interR_fit[0])
                        InterR_Chi.append(interR_fit[1])
                    else:
                        InterR.append(np.nan)
                        InterR_Chi.append(np.nan)
                else:
                    InterR.append(np.nan)
                    InterR_Chi.append(np.nan)

            RPoly.append(np.nan)
            InterR.append(np.nan)
            InterR_Chi.append(np.nan)
            #print (RPoly)
            #print (len(InterR), InterR)
            data[file]["data"]["Rpoly"] = RPoly
            data[file]["data"]["RpolyNbr"] = RPolyNbr
            data[file]["data"]["Rint"] = InterR
            data[file]["data"]["Rint_Chi"] = InterR_Chi

            # Correct capacitance measurements for open measurements
            data[file]["data"]["Coupling Cap"] = data[file]["data"]["Coupling Cap"] - cc_offset
            data[file]["data"]["Interstrip C"] = data[file]["data"]["Interstrip C"] - ic_offset

            # Correct currents for polarity
            data[file]["data"]["Istrip_Median"] = data[file]["data"]["Istrip_Median"] * polarity
            #print (len(IstripNbr), IstripNbr)
            data[file]["data"]["IstripNbr_Median"] = IstripNbr
            data[file]["data"]["Global Current"] = data[file]["data"]["Global Current"] * polarity
            data[file]["data"]["Pinhole"] = data[file]["data"]["Pinhole"] * polarity

            #I_headers = [i for i in Headers if "I_" in i]
            #print ("I_headers", I_headers)
            #for i in I_headers:
            #    data[file]["measurements"].remove(i)
            #print ("After removal", data[file]["measurements"])

    def int_to_Roman(self, num):
        val = [
            1000, 900, 500, 400,
            100, 90, 50, 40,
            10, 9, 5, 4,
            1
        ]
        syb = [
            "M", "CM", "D", "CD",
            "C", "XC", "L", "XL",
            "X", "IX", "V", "IV",
            "I"
        ]
        roman_num = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syb[i]
                num -= val[i]
            i += 1
        return roman_num


    def run(self):
        from .Stripscan import Stripscan
        stripi = Stripscan(self.data, self.config)
        for file in self.data.keys():
            print ("Before Stripscan", self.data[file]["measurements"])
            Headers = self.data[file]["measurements"]
            I_headers = [i for i in Headers if "I_" in i]
            for i in I_headers:
                stripi.donts.append(i)
            print ("Dont's", stripi.donts)

        #plots = Stripscan.run(stripi)
        plots = stripi.run() # ERIC: This is the intended way to use it (but look if it yields the same result as your method)

        plot_paths = plots["All"].keys()  # This will give you a list of tuple with the plot objects inside
        #print (plot_paths)

        """
        for path in plot_paths:
            print("HEY2", path)
            if "I_" in path:
                print ("HEY", path)
                plots["All"] -= path
            if "Strip_Currents" in path:  # Look if the cuirrent path is the plot you want
                print("HEY", path)
                #plot1 = plot_paths[path]
                the_plot_I_need = plots["All"]
                for subpath in path: # This loop does: self.PlotDict["All"]["Overlay"]["Strip_Currents"]
                    print ("sub", subpath)
                    plot1 = the_plot_I_need[subpath]
            if "Strip_Currents_Nbr" in path:  # Look if the cuirrent path is the plot you want
                print("HEY3", path)
                the_plot_I_need = plots["All"]
                for subpath in path:  # This loop does: self.PlotDict["All"]["Overlay"]["Strip_Currents"]
                    plot2 = the_plot_I_need[subpath]
        """

        # ERIC: In order to have a usable plot legend you have to rename the plots, but first you need a copy of the plot
        # to not change the original this can be done via .opts(clone=True)
        plot1 = plots["All"].Overlay.Strip_Currents.opts(clone=True)
        plot2 = plots["All"].Overlay.Strip_Currents_Nbr.opts(clone=True)
        plot2_re = None

        # Next rename the subplots
        for path_part in plot2.keys():
            subplot = plot2
            for part in path_part:
                subplot = getattr(subplot, part)
            label = subplot.label + " Nbr"
            subplot = subplot.relabel(label)
            if plot2_re:
                plot2_re *= subplot
            else:
                plot2_re = subplot

        combined_plot = plot1*plot2_re
        plots["All"] += combined_plot #combined_plot

        plot3 = plots["All"].Overlay.Poly_hyphen_minus_Silicon_Resistor_Resitance
        plot4 = plots["All"].Overlay.Poly_hyphen_minus_Silicon_Resistor_Resitance_Nbr
        combined_plot2 = plot3 * plot4
        plots["All"] += combined_plot2

        return plots

        # Lets say plot_pathes[0] = ("Overly", "Strip_Currents")

        # To access this plot you can write either

        #awesomeplot = self.PlotDict["All"].Overlay.Strip_Currents  # or

        #awesomeplot = self.PlotDict["All"]["Overlay"]["Strip_Currents"]  # This you would use if you are sure that this plot always exists, which you usually cannot guarantee

        # ERIC: This code is unreachabel
        return stripi.run()