# This python program gives functions for bad strip detection of silicon based sensors
# It is based on the bad strip detection of M. Valentan. Improvements done by D. Bloech

import yaml
import logging
import os
import numpy as np
from utilities import help_functions
import numba as nb
from scipy.stats import norm, stats
hf = help_functions()

l = logging.getLogger(__name__)


class stripanalysis:
    """Class which provides all necessary functions for bad strip detection, for more information on its capabilites
    look at the reference manual. Written by Dominic Bloech, based on Manfred Valentan"""

    def __init__(self, main_obj, filepath = "analysis.ini"):
        """Just some initialization stuff"""
        self.main = main_obj
        self.settings = None
        self.all_data = {}
        self.jit_lms = nb.jit('UniTuple(float64[:], 2)(float64[:], float64[:], float64)', nopython=False)(self.lmsalgorithm)
        #self.jit_lms = self.lmsalgorithm

        # First read in the ini file if necessary
        if not self.main:
            self.read_in_config_file(filepath)
        else:
            self.settings = self.main.default_values_dict["Badstrip"]

    def read_in_config_file(self, filepath = "analysis.ini"):
        """Reads the .ini file and returns the configparser typical dicts. If file could not be found IOError will be raised."""
        l.info("Try reading badstrip ini file...")
        try:
            file_string = os.path.abspath(str(filepath))
            settings_file = open(file_string, "r")
            self.settings = yaml.load(settings_file)
            settings_file.close()
            l.info("Badstrip ini file " + str(filepath) + " was successfully loaded.")
            #l.info("Included sections in badstrip ini file" + str(self.settings.sections()))
        except IOError, e:
            print "IO error while accessing init file in badstrip detection, with error: " + str(e)
            l.error("IO error while accessing init file in badstrip detection, with error: " + str(e))

    def read_in_measurement_file(self, filepathes):
        """This function reads in a QTC measurement file and return a dictionary with the data in the file"""
        try:
            for files in filepathes:
                current_file = files
                with open(str(files)) as f:
                    data = f.read()
                data = self.parse_file_data(data)
                # Add filename and rest of the dict important values
                filename = os.path.basename(str(files)).split(".")[0][4:]
                data.update({"analysed": False, "plots": False})
                self.all_data.update({filename: data})

        except Exception as e:
            print "Something went wrong while importing the file " + str(current_file) + " with error: " + str(e)
            l.error("Something went wrong while importing the file " + str(current_file) + " with error: " + str(e))

    def parse_file_data(self, filecontent):
        """This function parses the file content to the needed data type"""
        filecontent = filecontent.split("\n")

        header = filecontent[:self.settings["header_lines"]]
        measurements = filecontent[self.settings["measurement_description"]-1:self.settings["measurement_description"]]
        units = filecontent[self.settings["units_line"]-1:self.settings["units_line"]]
        data = filecontent[self.settings["data_start"]-1:]

        # First parse the units and measurement types
        parsed_obj = []
        for k, data_to_split in enumerate((measurements, units)):
            for i, meas in enumerate(data_to_split): # This is just for safety ther is usually one line here
                meas = meas.split() # usually all spaces should be excluded but not sure if tab is removed as well
                for j, singlemeas in enumerate(meas):
                    meas[j] = singlemeas.strip()
                parsed_obj.append(meas)

        # Now parse the actual data and build the tree dict structure needed
        data_lists = [] # is a list containing all entries from one measurement, while having the same order like the measurements object
        parsed_data = []
        data_dict = {}
        for dat in data:
            dat = dat.split()
            for j, singleentry in enumerate(dat):
                try: # try to convert to number
                    dat[j] = float(singleentry.strip())
                except:
                    dat[j] = singleentry.strip()
            if len(dat) == len(parsed_obj[0]):
                parsed_data.append(dat)


        for i, meas in enumerate(parsed_obj[0]):
            data_lists.append([parsed_data[x][i] for x in range(len(parsed_data))])
            # Construct dict
            data_dict.update({str(meas): data_lists[i]})

        return_dict = {"data": data_dict, "header": header, "measurements": parsed_obj[0], "units": parsed_obj[1]}
        return return_dict

    def single_defect_detection(self):
        """Detects if the given strip has a defect, common only to itself and returns what kind of defect it prob. is"""
        pass

    def cluster_defect_detection(self):
        """Detects errors common to multiple strips"""
        pass

    def temperatur_correction(self):
        """Takes strips and makes a temperature correction of the strip"""
        pass

    def do_lms_fit(self, x, y):
        """Does the lms fit from Rudi and times the execution.
        This is a legacy function and can be removed if necessary"""
        res, time = self.lms_line(x, y, self.settings["quantile"])

        return time, res

    @hf.raise_exception
    def do_analysis(self):
        """This will run the analysis for all measurements loaded, which have not been analysed yet"""

        for run in self.all_data.values(): # Loop over all measurements
            if not run["analysed"]: # Exclude the ones which are already analysed
                # Add a new entrie for the analysis results and get xdata
                results = run["analysis_results"] = {
                                                        "lms_fit": {},
                                                        "histogram": {},
                                                        "pdf": {},
                                                        "report": {},
                                                        "threshold": {}
                                                    }
                xdata = range(len(run["data"]["Pad"]))
                #Loop over all measurement types
                for meas, ydata in run["data"].items():
                    # Do the lms linefit for every measurement prevalent
                    if "Pad" not in meas: # Exclude the pad analysis
                        print "Calculating lms line for: " + str(meas)
                        time, res = self.do_lms_fit(xdata, ydata)
                        results["lms_fit"][meas] = res
                        results["report"][meas] = "LMS line fit: \n" \
                                                   "k= " + str(res[0]) + ",\t" +\
                                                   "d= " + str(res[1]) + "\n\n"

                        print "Time taken for analysis: " + str(time)

                        # Generate Histogram----------------------------

                        # Remove outliner if necessary
                        if self.settings["remove_outliner"]:
                            ydata = self.remove_outliner(ydata) # Warning this changes the length of the array!!!

                        # Make actual histogram
                        x,y = self.do_histogram(ydata, 50)
                        results["histogram"][meas] = [x,y]

                        # Generate PDF
                        pdf = self.do_normaldist(ydata, 50)
                        results["report"][meas] += "Normal distribution: \n" \
                                                   "mu= " + str(pdf[0]) + ",\t" +\
                                                   "std= " + str(pdf[1])+ "\n\n"
                        results["pdf"][meas] = pdf

                        # Make singlestrip threshold analysis
                        bad_strips = self.do_offline_singlestrip_analysis(meas, ydata)
                        results["report"][meas] += "Threshold analysis: \n" +\
                                                   "Total number of bad strips: " + str(len(bad_strips)) + "\n\n"
                        results["threshold"][meas] = bad_strips

                # When everything is finished switch flag to analysed
                run["analysed"] = True

        print "Analysis done"

    def do_offline_singlestrip_analysis(self, meas, data):
            """This function just calls the online analysis for every strip and generates a report text"""
            bad_strips = []
            for i, val in enumerate(data):
                result = self.do_online_singlestrip_analysis((meas, val))
                if result:
                    bad_strips.append((i, result[2]))
            return bad_strips




    def do_online_singlestrip_analysis(self, measurement_tuple):
        """ Does the online cutoff analysis.
        This function returns False if one or more strip values did not pass the specs. Can also work if only one value
        after the other is passed.

        :param measurement_tuple this must be a tuple containing (Measurement_name, value)
        :return None if all is alright, list [type, (measurement, [critical values], meas value)]
        """
        # First find the measurement and what are the
        if measurement_tuple[0] in self.settings:
            # Check if the value is inside the boundaries
            value = measurement_tuple[1] # Just for readability
            meas = measurement_tuple[0]
            min_value = float(self.settings[meas][1][0])
            max_value = float(self.settings[meas][1][1])
            if value <= max_value and value >= min_value:
                return None
            else:
                return (measurement_tuple[0], [min_value,max_value], value)

        else:
            l.error("Measurement: " + str(measurement_tuple[0] + "could not be found as analysable measurement, please add it."))
            return ["Measurement not found", (None, None, None)]

    def do_online_cluster_analysis(self, list_of_strip_dicts):
        """
        This functions calls the actual online bad strip detection analysis stripts and will return a False if one or
        more strips show bad behavior.

        :param events: Is a dictionary containing key: measurement and value: the measured value.
                       if it is a list of dictionaries, the program will interpret cross relations as well
        :return:
        """
        pass

    def lmsalgorithm(self, x, y, q):
        # initialisations
        qresmin = np.Inf
        length = len(x)
        klms = 1
        dlms = 1

        for i in range(length):
            for j in range(length):
                if x[i] != y[j]:
                    k = (y[j] - y[i]) / (x[j] - x[i])
                    d = y[j] - k * x[j]
                    res = y - (y + [k] * x)
                    sres = np.sort(np.power(res, 2))
                    nxqround = round((length) * q)
                    qres = sres[int(nxqround)]
                    if qres < qresmin:
                        klms = k
                        dlms = d
                        qresmin = qres

        return (klms, dlms)

    @hf.timeit
    def lms_line(self, x, y, q):
        """
        Robust regression line by least quantile of squares function [klms,dlms]=lms_line(x,y,q).
        Fit a line to x/y by requiring the q-quantile of the squared residuals to be minimal.
        For q=0.5 the quantile is the median, and the line is the LMS regression of y on x
        Author: R. Fruehwirth, 12-02-2001
        Ported to Python by M. Valentan, 27-04-2015
        Improved by Dominic Bloech, 10-10-2018
        """
        x = np.array(x, dtype='f')
        y = np.array(y, dtype='f')
        # length check
        if len(x) != len(y):
            l.error("LMS line regression error: Cannot analyse data arrays of different length.")
            return -1
        # shape check
        if x.shape != y.shape:
            l.error("LMS line regression error: Cannot analyse data arrays of different shape.")
            return -1
        # calculation
        try:
            result = self.jit_lms(x, y, q)
        except Exception as e: # This happens when the pads are not numbers but should not concernt anyone
            print "Error occured while calculating LMS line with error: " + str(e)
            result = [1,1]

        return [result[0], result[1]]

    def do_histogram(self, y, bins):
        """Generates a histogram of data given by y in n bins"""
        yres, xres = np.histogram(np.array(y), bins=int(bins))
        return xres,yres

    def do_normaldist(self, ydata, bins):
        """Calculates the normal distrubution of a dataset and returns the mu and std.
        If results (dict) is given, then the data will be appended there

        :param data numpyarray containing the data
        :param results optional parameter which stores the results somewhere
        :return a tuple of data (mu, std, [pdfdata])
        """
        # Calculate the mean and std
        mu, std = norm.fit(ydata)
        # calculate the histogram and std am mu new
        x,y = self.do_histogram(ydata, bins)
        # Calculate the distribution for plotting in a histogram
        p = norm.pdf(x, loc=mu, scale=std)

        return (mu, std, x, p)

    def remove_outliner(self, ydata):
        """Removes outliner from dataset
        Uses the zscore algorithm"""

        # Method by z-score
        z = np.abs(stats.zscore(ydata))
        final_list = np.array(ydata)[(z < self.settings["outlier_std"])]

        # Method by std deviation (not very robust)
        # final_list = [x for x in ydata if (x > mu - self.settings["outlier_std"] * std)]
        # final_list = [x for x in final_list if (x < mu + self.settings["outlier_std"] * std)]

        return final_list



if __name__ == "__main__":
    det = stripanalysis(None, "C:\\Users\\dbloech\\PycharmProjects\\Doktorat\\QTC-Software\\UniDAQ\\init\\default\\badstrip.yml")
    det.read_in_measurement_file(["C:\Users\dbloech\Desktop\str_VC740655_11_2SBaby_1.txt","C:\Users\dbloech\Desktop\str_VC740655_18_2SBaby_2.txt"])
    det.do_analysis()