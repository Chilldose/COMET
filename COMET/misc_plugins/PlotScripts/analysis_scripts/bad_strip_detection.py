# This python program gives functions for bad strip detection of silicon based sensors
# It is based on the bad strip detection of M. Valentan. Improvements done by D. Bloech

__version__ = "0.1.1"
__date__ = "11.Sept.2019"

import yaml, json
import logging
import os, io
import numpy as np
from time import time
from numba import jit
from scipy.stats import norm, stats
from forge.engineering_notation import EngNumber


class bad_strip_detection:
    """This is a wrapper for the plotting scripts, which simply calls the stripanalysis"""

    def __init__(self, data, configs):

        self.data = data
        self.configs = configs
        self.rename_columns()
        # Todo: inheritance may be the more elegant solution here
        self.analysis = stripanalysis(
            None, settings=self.configs["bad_strip_detection"]["Config"]
        )
        self.analysis.all_data = self.data

    def rename_columns(self):
        """Renames the columns for the badstripdetection"""
        aliases = self.configs.get("bad_strip_detection", {}).get(
            "Measurement_aliases", None
        )
        if aliases:
            for data in self.data:
                for oldkey, newkey in aliases.items():
                    try:
                        self.data[data]["data"][newkey] = self.data[data]["data"].pop(
                            oldkey
                        )
                        idx = self.data[data]["measurements"].index(oldkey)
                        self.data[data]["measurements"][idx] = newkey
                    except KeyError:
                        pass

    def run(self):
        """Runs the script"""
        self.analysis.do_analysis()
        if self.configs["bad_strip_detection"].get("do_holoviews_table", False):
            import holoviews as hv
            import pandas as pd

            df = {}
            # Generate dict with the length of all sub entries
            for name, data in self.analysis.all_data.items():
                df[name] = {k: len(v) for k, v in data["Detailed_info"].items()}
            data = pd.DataFrame.from_dict(df, orient="index")
            sum_df = pd.Series(data.sum(), name="Sum")
            data = data.append(sum_df)

            col_order = (
                ("index", "Name"),
                ("BadDC", "Bad DC Contact"),
                ("BadAC", "Bad AC Contact"),
                ("Pinholes", "Pinholes"),
                ("HighCurr", "High IStrip"),
                ("Rinterrupt", "Resistor interrupt"),
                ("LowCap", "Low Capacitance"),
                ("ImplantOpen", "Implant Open"),
                ("ImplantShort", "Implant Short"),
                ("MetalOpen", "Metal Open"),
                ("MetalShort", "Metal Short"),
                ("BadDC2", "DC2 Contact issue"),
                ("NonOptimalDC1", "DC1 soft issue"),
            )
            # col_order.extend(list(data.keys()))
            table = hv.Table(data, [*col_order], group="Bad Strip detection table")
            table.opts(**self.configs["bad_strip_detection"]["General"])

            return {"All": table, "Name": "Bad Strip Analysis"}


class stripanalysis:
    """Class which provides all necessary functions for bad strip detection, for more information on its capabilites
    look at the reference manual. Written by Dominic Bloech, based on Manfred Valentans bad strip detection"""

    def __init__(self, main_obj=None, filepath="analysis.ini", settings=None):
        """Just some initialization stuff"""
        self.main = main_obj
        self.settings = None
        self.all_data = {}
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.INFO)
        self.config_file = filepath

        # First read in the ini file if necessary
        if not self.main and not settings:
            self.read_in_config_file(filepath)
        elif self.main:  # For the Comet Framework
            self.settings = self.main.default_values_dict.get("Badstrip", {})
        elif settings:
            self.settings = settings
        else:
            self.log.error(
                "Bad strip detection could not be started due to invalid settings..."
            )

    def reload_config_file(self):
        self.read_in_config_file(self.config_file)

    def read_in_config_file(self, filepath="analysis.ini"):
        """Reads the .ini file and returns the configparser typical dicts. If file could not be found IOError will be raised."""
        self.log.info("Try reading badstrip config file...")
        try:
            file_string = os.path.abspath(str(filepath))
            settings_file = open(file_string, "r")
            self.settings = yaml.load(settings_file)
            settings_file.close()
            self.log.info(
                "Badstrip config file " + str(filepath) + " was successfully loaded."
            )
            # l.info("Included sections in badstrip ini file" + str(self.settings.sections()))
        except IOError as e:
            self.log.error(
                "IO error while accessing config file in badstrip detection, with error: "
                + str(e)
            )

    def read_in_measurement_file(self, filepathes):
        """This function reads in a QTC measurement file and return a dictionary with the data in the file"""
        try:
            for files in filepathes:

                # Find file extension
                fileext = files.split(".")[-1]

                if fileext in ["txt", "dat"]:
                    # Ascii file type
                    self.log.debug("Ascii file found {}".format(files))
                    current_file = files
                    with open(str(files)) as f:
                        data = f.read()
                    data = self.parse_file_data(data)

                # json file type
                if fileext in ["json"]:
                    self.log.debug("JSON file found {}".format(files))
                    with open(files, "r") as stream:
                        try:
                            data = yaml.load(stream, Loader=yaml.FullLoader)
                            if isinstance(data, str):
                                data = json.loads(data)
                        except yaml.YAMLError as exc:
                            self.log.error(
                                "While loading the yml file {} the error: {} happend.".format(
                                    files, exc
                                )
                            )

                # Convert all lists to np.ndarrays
                for key, dat in data["data"].items():
                    data["data"][key] = np.array(dat)

                # Add filename and rest of the dict important values
                filename = os.path.basename(str(files)).split(".")[0]
                data.update({"analysed": False, "plots": False})
                self.all_data.update(
                    {filename: data}
                )  # So nothing get deleted if additional files are loaded

        except Exception as e:
            self.log.error(
                "Something went wrong while importing the file "
                + str(files)
                + " with error: "
                + str(e)
            )

    def parse_file_data(self, filecontent):
        """This function parses the file content to the needed data type"""
        filecontent = filecontent.split("\n")

        header = filecontent[: self.settings["header_lines"]]
        measurements = filecontent[
            self.settings["measurement_description"]
            - 1 : self.settings["measurement_description"]
        ]
        units = filecontent[
            self.settings["units_line"] - 1 : self.settings["units_line"]
        ]
        data = filecontent[self.settings["data_start"] - 1 :]
        separator = self.settings.get("data_separator", None)

        # First parse the units and measurement types
        parsed_obj = []
        for k, data_to_split in enumerate((measurements, units)):
            for i, meas in enumerate(
                data_to_split
            ):  # This is just for safety ther is usually one line here
                meas = (
                    meas.split()
                )  # usually all spaces should be excluded but not sure if tab is removed as well
                for j, singlemeas in enumerate(meas):
                    meas[j] = singlemeas.strip()
                parsed_obj.append(meas)

        # Now parse the actual data and build the tree dict structure needed
        data_lists = (
            []
        )  # is a list containing all entries from one measurement, while having the same order like the measurements object
        parsed_data = []
        data_dict = {}
        for dat in data:
            dat = dat.split(separator)
            for j, singleentry in enumerate(dat):
                try:  # try to convert to number
                    dat[j] = float(singleentry.strip())
                except:
                    dat[j] = np.nan  # singleentry.strip()
            if len(dat) == len(parsed_obj[0]):
                parsed_data.append(dat)

        for i, meas in enumerate(parsed_obj[0]):
            data_lists.append([parsed_data[x][i] for x in range(len(parsed_data))])
            # Construct dict
            data_dict.update({str(meas): np.array(data_lists[i], dtype=np.float32)})

        return_dict = {
            "data": data_dict,
            "header": header,
            "measurements": parsed_obj[0],
            "units": parsed_obj[1],
        }
        return return_dict

    def temperatur_correction(self):
        """Takes strips and makes a temperature correction of the strip"""
        pass

    def create_piecewise_arrays(self, padarray, piecesize):
        start = np.arange(0, len(padarray) - piecesize, piecesize)
        end = np.arange(piecesize, len(padarray), piecesize)
        if len(end):
            if end[-1] < len(padarray):
                end[-1] = len(padarray)
            return start, end
        else:
            return [0], [len(padarray)]

    def do_piecewise_lms_fit(self, data_label, data, tokeep, piecesize):
        """
        Does the lms fit from Rudi and times the execution.
        This is a legacy function and can be removed if necessary
        :param data_label: The label of the data which should be analysed
        :param data: The data dict
        :param tokeep: Data dict which indizes from which data are valid data points
        :param piecesize: Piecesize at which the lms fit should be done
        :return: list of tuples containing klms and dlms for each piece
        """

        results = []
        padarray = data["Pad"][tokeep[data_label]]
        start = np.arange(0, len(padarray) - piecesize, piecesize)
        end = np.arange(piecesize, len(padarray), piecesize)
        if len(end):
            if end[-1] < len(padarray):
                end[-1] = len(padarray)

            for st, en in zip(start, end):
                results.append(
                    self.lms_line(
                        padarray[st:en],
                        data[data_label][st:en],
                        self.settings["quantile"],
                    )
                )

        else:
            self.log.warning(
                "To few data for lms fit in data {} with current settings. Returning mean instead.".format(
                    data_label
                )
            )
            results.append((np.mean(data[data_label]), 0))

        return results

    def median(self, data):
        """Returns the median of values"""
        return np.median(data)

    def check_sum_of_Istrip(self, Istrip, Idark):
        # Calc the current per strip
        measStripNum = len(Istrip)
        totalStripCurrent = np.sum(Istrip)

        # Check if sum of current is considerably bigger than the Idark
        if (
            abs(totalStripCurrent * (self.stripNum / measStripNum))
            > abs(Idark) * self.settings["MeasStripvsTotal"]
        ):
            strip = str(EngNumber(totalStripCurrent * (self.stripNum / measStripNum)))
            Idarks = str(EngNumber(float(Idark)))
            ratio = str(
                EngNumber(
                    abs(totalStripCurrent * (self.stripNum / measStripNum)) / abs(Idark)
                )
            )
            self.log.warning(
                "Single strip current and total current deviating more than specified: \n"
                "This can be an indicator that the Bias needle has a bad contact \n"
                "Sum of Strip current: {strip:>30}A \n"
                "Total Idark (median): {Idark:>30}A \n"
                "Ratio:                {ratio:>30} \n".format(
                    strip=strip, Idark=Idarks, ratio=ratio
                )
            )

        else:
            self.log.warning(
                "The ratio between the sum of Istrip to Idark is: {}".format(
                    abs(totalStripCurrent * (self.stripNum / measStripNum)) / abs(Idark)
                )
            )

    def find_pinhole(self, Idiel, shift=None):
        """Looks if high Idiel is prevalent and determines if pinhole is prevalent"""
        highIdiel = np.nonzero(np.abs(Idiel) > self.settings["IdielThresholdCurrent"])[
            0
        ]

        if len(highIdiel):
            if shift:
                highIdiel = self.shift_strip_numbering("Idiel", highIdiel, shift)
            self.log.warning("Possible pinholes found on strips: {}".format(highIdiel))
        else:
            self.log.info("No pinholes found.")

        return highIdiel

    def threshold_comparison(
        self, measurement, data, lms_fit, cutted, piecesize, factor, bigger=True
    ):
        """
        This function returns if a measurement is above a thresholed above the lms fit.
        Used for highcurrent strios
        :param measurement: Str- measurement you want to perform on
        :param data: data dict
        :param lms_fit: lms fit dict
        :param cutted: cutted strip dict
        :param piecesize: piecesize of lms fit
        :param factor: factor above lms fit to be recognized
        :param bigger: Whether or not the measuremnt should be bigger or lower to be true
        :return: list of true strips
        """

        single_data = data[measurement]
        single_lms = lms_fit[measurement]
        single_cutted = cutted[measurement]

        xvalues = data["Pad"]
        xvalues = xvalues[single_cutted]

        start, stop = self.create_piecewise_arrays(xvalues, piecesize)

        found = []
        for lms, sta, sto in zip(single_lms, start, stop):
            # Calc the points for the lms_array
            lms_array = np.array(
                [lms[0] * x + lms[1] for x in xvalues[sta:sto]], dtype=np.float32
            )
            if bigger:
                found.append(
                    np.nonzero(np.abs(single_data[sta:sto]) > abs(lms_array * factor))[
                        0
                    ]
                    + sta
                )
            else:
                found.append(
                    np.nonzero(np.abs(single_data[sta:sto]) < abs(lms_array * factor))[
                        0
                    ]
                    + sta
                )

        found = np.concatenate(found)
        return found

    def do_contact_check(self, measurement):
        """Quickly checks if AC and DC needle have contact or not"""
        # Todo: only report back faulty strips which have not jetzt been reported
        if len(measurement["Istrip"][1] > 10):
            DCerror = self.find_bad_DC_contact(
                measurement["Istrip"][1], measurement["Rpoly"][1]
            )
            ACerror = self.find_bad_AC_contact(
                measurement["Cac"][1], measurement["Rpoly"][1], []
            )

            if len(DCerror) or len(ACerror):
                return True
            else:
                return False

    def find_bad_DC_contact(self, Istrip, Rpoly, Cint, Cap, shift=None):
        """Looks for low Istrip and High Rpoly and determines bac DC needle contacts
        Furthermore calculates some statistics which can be accounted for bad DC needle contact"""

        # Todo: If the majority of strips have been measured with this error mode this simple implementation might fail.
        medianIstrip = np.median(Istrip)
        medianRpoly = np.median(Rpoly)

        # Check for low Istrip
        lowIstrip = np.nonzero(
            np.abs(Istrip) < abs(medianIstrip / self.settings["Istripfactor"])
        )
        HighRpoly = np.nonzero(Rpoly > medianRpoly * self.settings["Rpolyfactor"])

        # Find intersect
        intersectDC1 = np.intersect1d(lowIstrip[0], HighRpoly[0])

        # Do the cross validation between Cap and Cint to find bad DC2 contact
        # Theory is Cint is very susceptiple to a non perfect contact, as well as the Cap measurement.

        noOut, ind_bad_Cint = self.remove_outliner(Cint)
        noOut, ind_bad_Cap = self.remove_outliner(Cap)

        # Todo: further actions needed? Outliner enough? Could add some clustering as well. Could look if clusters intersect for Cint and Cap and print that out?
        if len(ind_bad_Cap) > self.settings["maximumCapOutliner"]:
            self.log.warning(
                "The number of outliner in the capacitance measurement indicates a non optimal DC1 needle contact."
            )
        if len(ind_bad_Cint) > self.settings["maximumCapOutliner"]:
            self.log.warning(
                "The number of outliner in the interstrip capacitance measurement indicates a non optimal DC2 needle contact."
            )

        if len(intersectDC1):
            if shift:
                intersectDC1 = self.shift_strip_numbering("Istrip", intersectDC1, shift)
            self.log.warning(
                "Possible bad DC1 needle contact on strips: {}".format(intersectDC1)
            )  # +1 because index starts at 0
        else:
            self.log.info("DC needle contact seem to be alright.")

        return intersectDC1, ind_bad_Cint, ind_bad_Cap

    def shift_strip_numbering(self, label, to_shift, shift_array):
        truth_table = shift_array[label]
        start, shift = 0, 1  # Arrays start with zero, stripnumbering starts with 1
        shifted_array = []
        for ind in to_shift:
            shift += np.count_nonzero(~truth_table[start : ind - 1])
            start = ind
            shifted_array.append(ind + shift)
        return shifted_array

    def find_bad_AC_contact(self, Cap, Rpar, pinholes, shift=None):
        """Finds out if a bad AC contact is prevalent"""
        # nCap = np.delete(Cap, pinholes) # Exclude pinholes in this calculations
        # nRpoly = np.delete(Rpoly, pinholes) # Exclude pinholes in this calculations
        # Todo: Not rpoly, Rpar
        medianCap = np.median(Cap)
        medianRpar = np.median(Rpar)

        # Out of bounds Cap
        CapOOB = np.where(
            np.logical_or(
                Cap < medianCap / self.settings["Capfactor"],
                Cap > medianCap * self.settings["Capfactor"],
            )
        )[
            0
        ]  # Out of bounds Cap
        RparOOB = np.where(
            np.logical_or(
                Rpar < medianRpar / self.settings["Rpolyfactor"],
                Rpar > medianRpar * self.settings["Rpolyfactor"],
            )
        )[0]
        # Find intersect
        intersect = np.intersect1d(CapOOB, RparOOB)
        # Find values not common to pinholes
        intersect = np.setdiff1d(intersect, pinholes)

        if len(intersect):
            if shift:
                intersect = self.shift_strip_numbering("Cac", intersect, shift)
            self.log.warning(
                "Possible bad AC needle contact found on strips: {}".format(intersect)
            )
        else:
            self.log.info("AC needle contact seems to be fine")
        return intersect

    def compare_closeness(self, array, lms_tuple, x_values, factor=1.0):
        """Takes an array and an lms fit and compares elementwise its values with the respective lms fit
        Returns elemtwise boolschen list for each element in the input array"""

        # Calc the points for the lms_array
        lms_array = np.array(
            [lms_tuple[0] * x + lms_tuple[1] for x in x_values], dtype=np.float32
        )
        # Compare
        return np.isclose(
            array,
            lms_array * factor,
            rtol=float(self.settings["rtol"]),
            atol=float(self.settings["atol"]),
        )

    def find_relation(self, compare, factors, data, lms_data, cutted, piecesize):
        """
        Finds if a relation between two observables are present, for e.g. imnplant short.
        It conpares the data with a factor from the lms line fit.
        Example: Implant short: ( ('Istrip', 'Rpoly'), (2,0.5), data, lms_data, cutted, piecesize)
        Data from istrip and Rpoly will be checked against the scaled (factor) lms_line fit. And a true table will be
        returned. These truth tables are checked for common indizes wich then will be (in our case) a implant short

        :param compare: Tuple - ("Istrip", "Rpoly") etc. So what data you want to compare
        :param factors: Tuple - (2, 0.5), scaling factor at which we say its suspicious
        :param data: Data dict containing data
        :param lms_data: Lms data dict
        :param cutted: Cutted indizes dict
        :param piecesize: lms piecesize
        :return: list of common indizes
        """

        # Todo: clean up this ugly code
        # todo: currently if Istrip and rply are measured at different points it will come to a data mismatch in the ned
        # and this method will fail!!!

        First = data[compare[0]]
        Firstcut = cutted[compare[0]]
        Firstlms = lms_data[compare[0]]
        Second = data[compare[1]]
        Secondcut = cutted[compare[1]]
        Secondlms = lms_data[compare[1]]

        if np.sum(Firstcut) != np.sum(Secondcut):
            both_cuts = np.logical_and(Firstcut, Secondcut)
            Firstcut, Secondcut = both_cuts, both_cuts
            self.log.warning(
                "Cannot compare array of different sizes. Taking logical and and try with this data. Data sets: {}".format(
                    compare
                )
            )

        xvalues = data["Pad"]
        Fxval = xvalues[Firstcut]
        Sxval = xvalues[Secondcut]

        Fyval_list_start, Fyval_list_stop = self.create_piecewise_arrays(
            Fxval, piecesize
        )
        Syval_list, Syval_list_stop = self.create_piecewise_arrays(Sxval, piecesize)

        # Compare per lms line piece
        intersect = []
        for Flms, Slms, Fsta, Fsto, Ssta, Ssto in zip(
            Firstlms,
            Secondlms,
            Fyval_list_start,
            Fyval_list_stop,
            Syval_list,
            Syval_list_stop,
        ):
            compF = self.compare_closeness(
                First[Fsta:Fsto], Flms, Fxval[Fsta:Fsto], factor=factors[0]
            )
            compS = self.compare_closeness(
                Second[Ssta:Ssto], Slms, Sxval[Ssta:Ssto], factor=factors[1]
            )
            # Find intersect
            intersect.append(
                np.nonzero(np.logical_and(compF, compS))[0] + Fsta
            )  # If data cut is not the same for istrip and rpoly error happens
        intersect = np.concatenate(intersect)
        return intersect

    def find_metal_and_implant_open(
        self, strips, data, lms_fit, cutted, piecesize, factor=1.0, shift=None
    ):
        """Finds metal opens"""
        # Todo: maybe first metal/implant open search and the rest for lowC. And I need the D value!
        # Istrip threshold comparison
        lowerIstrip = self.threshold_comparison(
            "Istrip", data, lms_fit, cutted, piecesize, factor, bigger=False
        )  # Since we have negative Istrip
        # Find possible metal open, by finding values in lowerIstrip which are not common to strips
        implant_open = np.intersect1d(lowerIstrip, strips)
        metal_open = np.setdiff1d(strips, implant_open)

        if len(implant_open):
            if shift:
                implant_open = self.shift_strip_numbering("Istrip", implant_open, shift)
            self.log.warning(
                "Possible implant open located at strips: {}".format(implant_open)
            )

        if len(metal_open):
            if shift:
                metal_open = self.shift_strip_numbering("Istrip", metal_open, shift)
            self.log.warning(
                "Possible metal open located at strips: {}".format(metal_open)
            )

        return implant_open, metal_open

    def find_implant_short(self, data, lms_data, cutted, piecesize, shift=None):
        """Finds implant shorts"""

        implant_shorts = self.find_relation(
            ("Istrip", "Rpoly"), (2.0, 0.5), data, lms_data, cutted, piecesize
        )

        if len(implant_shorts):
            if shift:
                implant_shorts = self.shift_strip_numbering(
                    "Istrip", implant_shorts, shift
                )
            self.log.warning(
                "Potential implant short found at strips: {}".format(implant_shorts)
            )
            return implant_shorts
        else:
            self.log.info("No implant shorts found.")
            return []

    def find_metal_short(self, data, lms_data, cutted, piecesize, shift=None):
        """Finds implant shorts"""

        # Make a simple threshold comparison for Cac
        metal_shorts = self.threshold_comparison(
            "Cac", data, lms_data, cutted, piecesize, 2, bigger=True
        )

        # Idiel is just a extra, which makes it more significant
        metal_Idiel_shorts = self.find_relation(
            ("Cac", "Idiel"), (2.0, 2.0), data, lms_data, cutted, piecesize
        )

        # Intersect Idiel with high Cac
        intersect = np.intersect1d(metal_shorts, metal_Idiel_shorts)

        if len(metal_shorts):
            if shift:
                metal_shorts = self.shift_strip_numbering("Cac", metal_shorts, shift)
                self.log.warning(
                    "Weak metal short found at strips: {}".format(metal_shorts)
                )

        if len(intersect) and shift:
            intersect = self.shift_strip_numbering("Idiel", intersect, shift)
            self.log.warning("Metal short found at strips: {}".format(intersect))
            return intersect
        else:
            self.log.info("No metal shorts found.")
            return []

    def remove_nan(self, data):
        """Removes nan values from any labeld data arrays"""
        working_data = {}
        cutted_array = {}
        for subdata in data:
            # Todo: Shift in data due to this here if some nans are in between
            tokeep = ~np.isnan(data[subdata])
            working_data[subdata] = data[subdata][tokeep]
            cutted_array[subdata] = tokeep
        return working_data, cutted_array

    # @hf.raise_exception
    def do_analysis(self):
        """This will run the analysis for all measurements loaded, which have not been analysed yet"""

        self.log.info("Starting badstrip analysis...")

        for data in self.all_data:
            if not self.all_data[data]["analysed"]:

                ### Setup the console handler with a StringIO object
                log_capture_string = io.StringIO()
                ch = logging.StreamHandler(log_capture_string)
                ch.setLevel(logging.INFO)

                ### Optionally add a formatter
                formatter = logging.Formatter("%(message)s")
                ch.setFormatter(formatter)

                ### Add the console handler to the logger
                self.log.addHandler(ch)

                self.log.info("Badstrip analysis results for file: {}".format(data))
                # Generate entry for conclusion text
                working_data = self.all_data[data]["data"].copy()
                self.stripNum = len(working_data["Istrip"])
                # Remove nan values
                working_data, cutted_array = self.remove_nan(working_data)

                Idark_median = self.median(working_data["Idark"])

                # Check if summ of Istrip is nearly the Idark
                self.check_sum_of_Istrip(working_data["Istrip"], Idark_median)

                # Look for low Istrip and High Rpoly, DC needle contact issues
                badDC, badCint, badCap = self.find_bad_DC_contact(
                    working_data["Istrip"],
                    working_data["Rpoly"],
                    working_data["Cint"],
                    working_data["Cac"],
                    cutted_array,
                )  # last value optional, used to calc the shift in the strip number

                # Look for high Idiel, pin holes
                pinholes = self.find_pinhole(working_data["Idiel"], cutted_array)

                # No pinhole, Cac and Rpoly - out of bounds, no AC needle contact
                badAC = self.find_bad_AC_contact(
                    working_data["Cac"], working_data["Rpoly"], pinholes, cutted_array
                )

                # Piecewise LMS fit and relative Threshold calculation for all datasets
                piecewiselms = {}
                for sdata in working_data:
                    if sdata in [
                        "Istrip",
                        "Idark",
                        "Rpoly",
                        "Rint",
                        "Cint",
                        "Idiel",
                        "Cac",
                        "QValue",
                    ]:
                        piecewiselms[sdata] = self.do_piecewise_lms_fit(
                            sdata, working_data, cutted_array, self.settings["LMSsize"],
                        )

                # 2x Istrip, 0.5x Rpoly, implant short
                implant = self.find_implant_short(
                    working_data,
                    piecewiselms,
                    cutted_array,
                    self.settings["LMSsize"],
                    cutted_array,
                )

                # 2x Cac, 2x Idiel, metal short
                metal = self.find_metal_short(
                    working_data,
                    piecewiselms,
                    cutted_array,
                    self.settings["LMSsize"],
                    cutted_array,
                )

                # High Istrip, high current (faulty strip)
                HighI = self.threshold_comparison(
                    "Istrip",
                    working_data,
                    piecewiselms,
                    cutted_array,
                    self.settings["LMSsize"],
                    self.settings["HighIstrip"],
                )
                HighINew = HighI
                if len(HighI):
                    HighINew = self.shift_strip_numbering("Istrip", HighI, cutted_array)
                    self.log.warning(
                        "High current strips found at: {}".format(HighINew)
                    )

                # Low Cac - bad capacitance
                LowCap = self.threshold_comparison(
                    "Cac",
                    working_data,
                    piecewiselms,
                    cutted_array,
                    self.settings["LMSsize"],
                    self.settings["LowCap"],
                    bigger=False,
                )
                LowCapNew = LowCap
                if len(LowCap):
                    LowCapNew = self.shift_strip_numbering("Cac", LowCap, cutted_array)
                    self.log.warning(
                        "Low capacitance strips found at: {}".format(LowCapNew)
                    )

                # High Rpoly, Resistor interrupt
                HighR = self.threshold_comparison(
                    "Rpoly",
                    working_data,
                    piecewiselms,
                    cutted_array,
                    self.settings["LMSsize"],
                    self.settings["HighRpoly"],
                )
                HighRNew = HighR
                if len(HighR):
                    HighRNew = self.shift_strip_numbering("Cac", HighR, cutted_array)
                    self.log.warning("Rpoly issue strips found at: {}".format(HighRNew))

                # lower Cac as usual D~normal,
                implant_open, metal_open = [], []
                if len(LowCapNew):
                    #   Proportional to Istrip, implant open, given by deviation of Istrip
                    #   No: metal open, given by deviation of Cac
                    implant_open, metal_open = self.find_metal_and_implant_open(
                        LowCapNew,
                        working_data,
                        piecewiselms,
                        cutted_array,
                        self.settings["LMSsize"],
                        self.settings["LowCap"],
                        cutted_array,
                    )

                # Check if parameters are within the specs
                self.check_if_in_specs(working_data)

                # Get all generated messages as an variable
                ### Pull the contents back into a string and close the stream
                log_contents = log_capture_string.getvalue()

                # Push the output to the data as analysis results
                self.all_data[data]["Analysis_conclusion"] = log_contents
                self.all_data[data]["analysed"] = True

                # Gather all strip informations
                self.all_data[data]["Detailed_info"] = {
                    "ImplantOpen": np.array(implant_open),
                    "MetalOpen": np.array(metal_open),
                    "LowCap": np.array(LowCapNew),
                    "Rinterrupt": np.array(HighRNew),
                    "HighCurr": np.array(HighINew),
                    "MetalShort": np.array(metal),
                    "ImplantShort": np.array(implant),
                    "BadAC": np.array(badAC),
                    "Pinholes": np.array(pinholes),
                    "BadDC": np.array(badDC),
                    "BadDC2": np.array(badCint),
                    "NonOptimalDC1": np.array(badCap),
                }

                if __name__ == "__main__":
                    print(log_contents)

                # log_capture_string.close()
                log_capture_string.truncate(0)
                log_capture_string.seek(0)

    # @hf.timeit
    def lms_line(self, x, y, q):
        """
        Robust regression line by least quantile of squares function [klms,dlms]=lms_line(x,y,q).
        Fit a line to x/y by requiring the q-quantile of the squared residuals to be minimal.
        For q=0.5 the quantile is the median, and the line is the LMS regression of y on x
        Author: R. Fruehwirth, 12-02-2001
        Ported to Python by M. Valentan, 27-04-2015
        Improved by Dominic Bloech, 10-10-2018
        """
        x = np.array(x, dtype=np.float32)
        y = np.array(y, dtype=np.float32)
        # length check
        if len(x) != len(y):
            self.log.error(
                "LMS line regression error: Cannot analyse data arrays of different length."
            )
            return -1
        # shape check
        if x.shape != y.shape:
            self.log.error(
                "LMS line regression error: Cannot analyse data arrays of different shape."
            )
            return -1
        # calculation
        try:
            result = lmsalgorithm(x, y, q)
        except Exception as e:  # This happens when the pads are not numbers but should not concernt anyone
            self.log.error(
                "Error occured while calculating LMS line with error: " + str(e)
            )
            result = [1, 1]

        return (result[0], result[1])

    def do_histogram(self, y, bins):
        """Generates a histogram of data given by y in n bins"""
        yres, xres = np.histogram(np.array(y), bins=int(bins))
        return xres, yres

    def do_normaldist(self, ydata, bins):
        """Calculates the normal distrubution of a dataset and returns the mu and std.
        If results (dict) is given, then the data will be appended there

        :param ydata numpyarray containing the data
        :param results optional parameter which stores the results somewhere
        :return a tuple of data (mu, std, [pdfdata])
        """
        # Calculate the mean and std
        mu, std = norm.fit(ydata)
        # calculate the histogram and std am mu new
        x, y = self.do_histogram(ydata, bins)
        # Calculate the distribution for plotting in a histogram
        p = norm.pdf(x, loc=mu, scale=std)

        return (mu, std, x, p)

    def remove_outliner(self, ydata):
        """Removes outliner from dataset
        Uses the zscore algorithm"""

        # Method by z-score
        data = ydata[np.logical_not(np.isnan(ydata))]
        z = np.abs(stats.zscore(data))
        final_list = np.array(data)[(z < self.settings["outlier_std"])]
        indizes_outliner = np.argwhere(z >= self.settings["outlier_std"])

        # Method by std deviation (not very robust)
        # final_list = [x for x in ydata if (x > mu - self.settings["outlier_std"] * std)]
        # final_list = [x for x in final_list if (x < mu + self.settings["outlier_std"] * std)]

        return final_list, indizes_outliner

    def get_correct_strip_numbering(self, indi, Padnumbering):
        """Returns the correct strip numbering for array, since nan values are cutted out during calculations
        Which implies a shit to the data"""
        return Padnumbering[indi]

    def check_if_in_specs(self, data):
        """
        Checks if the measurement data is inside the specs for e.g. CMS tracker
        :param data: data dict with all measurements
        :return: dict with all measurements containing (inside_specs, median_ok, glob_len)
        """
        return_dict = {}
        for meas, dat in data.items():
            if meas in self.settings:
                # Calc median
                medi = np.median(dat)
                inside_specs = np.where(
                    np.logical_and(
                        dat
                        > float(
                            self.settings[meas][1][0]
                        ),  # Looks which strips are inside
                        dat < float(self.settings[meas][1][1]),
                    )
                )[0]
                median_ok = np.where(
                    np.logical_and(
                        abs(dat)
                        < abs(
                            medi * (1 + self.settings[meas][2] / 100)
                        ),  # Looks which strips are inside median
                        abs(dat) > abs(medi * (1 - self.settings[meas][2] / 100)),
                    )
                )[0]
                glob_len = len(dat)

                self.log.warning(
                    "{}% of the strips are NOT inside {} specifications.".format(
                        round((1 - (len(inside_specs) / glob_len)) * 100, 2), meas
                    )
                )
                self.log.warning(
                    "{}% of the strips are NOT inside median({meas})+-{perc}%".format(
                        round((1 - (len(median_ok) / glob_len)) * 100, 2),
                        meas=meas,
                        perc=self.settings[meas][2],
                    )
                )
                return_dict[meas] = (inside_specs, median_ok, glob_len)
        return return_dict


# This function works as a decorator to measure the time of function to execute
def timeit(method):
    """
        Intended to be used as decorator for functions. It returns the time needed for the function to run

        :param method: method to be timed
        :return: time needed by method
        """

    def timed(*args, **kw):
        start_time = time()
        result = method(*args, **kw)
        end_time = time()

        exce_time = end_time - start_time

        return result, exce_time

    return timed  # here the memberfunction timed will be called


# These functions are for reading and writing to files------------------------------------
# -----------------------------------------------------------------------------------------


@jit(nopython=True, cache=True)
def lmsalgorithm(x, y, q):
    # initialisations
    qresmin = np.Inf
    length = len(x)
    klms = 1.0
    dlms = 1.0

    for i in range(length):
        for j in range(i + 1, length):
            if x[i] != y[j]:
                k = (y[j] - y[i]) / (x[j] - x[i])
                d = y[j] - k * x[j]
                res = y - (d + (k * x))
                sres = np.sort(np.power(res, 2))
                nxqround = round((length) * q)
                qres = sres[nxqround]
                if qres < qresmin:
                    klms = k
                    dlms = d
                    qresmin = qres

    return (klms, dlms)  # returns a slope and an offset


if __name__ == "__main__":
    det = stripanalysis(
        None,
        "C:\\Users\\dbloech\\PycharmProjects\\Doktorat\\QTC-Software\\UniDAQ\\UniDAQ\\config\\config\\badstrip.yml",
    )
    det.read_in_measurement_file(
        ["C:\\Users\\dbloech\\Desktop\\str_VPX28442_38_2S (defects by MV).txt"]
    )
    det.do_analysis()
