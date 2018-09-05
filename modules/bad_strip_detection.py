# This python program gives function for bad strip dtection of silicon based sensors
# It is based on the bad strip detection of M. Valentan but was improved by D. Blöch

import numpy as np
import math
import copy


class bad_strip_detection:
    """Class which provides all necessary functions for bad strip detection, for more information on its capabilites
    look at the reference manual. Written by Dominic Bloech, based on Manfred Valentan"""

    def __init__(self):
        """Just some initialization stuff"""
        pass

    def read_in_file(self):
        """This function reads in a QTC measurement file and return a dictionary with the data in the file"""
        pass

    def preanalyzation(self):
        """Preanalyze the data and calculates things like the mean temperature and other corrections.
        Needs to be called every time new data should be analyzed or parameters like temperature has changed"""
        pass

    def analyze_data(self):
        """Analyze the data given, generates and returns a plot item which can be plottet or saved"""
        pass

    def single_strip_detection(self):
        """Detects if the given strip has a defect, common only to itself and returns what kind of defect it prob. is"""
        pass

    def multiple_strip_detection(self):
        """Detects errors common to multiple strips"""
        pass

    def temperatur_correction(self):
        """Takes strips and makes a temperature correction of the strip"""
        pass

    def generate_plot(self):
        """This function generates a plot items based on matplotlib, which can eventually be plotted or saved
        It highlights the bad strips and annotates them. Several plot items are generated, one for each measurement
        If no errors can be found no plot item will be generated. Return value is dictionary with key=Measurement,
        value=plot item"""

    def generate_summarize_text(self):
        """generates a text which shows all found errors plus classification"""
        pass

    def do_analyzation(self):
        """This analyzes the data given and returns the error plots and text"""
        pass

    def do_online_cutoff_analysis(self):
        """ Does the online cutoff analysis.
        This function returns False if one or more strip values did not pass the specs. Can also work if only one value
        after the other is passed.
        """
        pass

    def do_online_badstrip_detection(self, events):
        """
        This functions calls the actual online bad strip detection analysis stripts and will return a False if one or
        more strips show bad behavior.

        :param events: Is a dictionary containing key: measurement and value: the measured value.
                       if it is a list of dictionaries, the program will interpret cross relations as well
        :return:
        """
        pass