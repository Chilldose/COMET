"""__author__: Dallavalle Riccardo
__email__: dallavallericcardo@outlook.com
This script plots files generated for PQC"""

import logging
import holoviews as hv
from scipy.stats import linregress
import scipy.signal
from copy import deepcopy
from scipy.interpolate import interp1d
import pandas as pd
import numpy as np
from forge.tools import customize_plot, holoplot, convert_to_df, config_layout, applyPlotOptions
from forge.tools import plot_all_measurements, convert_to_EngUnits
from forge.utilities import line_intersection
# Generate lists that are used later on to store different parameter values for all the files used in the analysis
# For analysis mos
cv_files = []
fbvoltage = []
fbvoltage_firstderivative = []
Accum_capacitance_list = []
Accum_capacitance_normalized_list = []
Tox_list = []
Nox_list = []
# For analysis diode
fdepvoltage = []
diode_files = []
resistivity = []
# For analysis gate
gate_files = []
Surface_current = []
Surface_recombination_velocity = []
Surface_current_average = []
Surface_recombination_velocity_average = []

class IV_PQC:
    def __init__(self, data, configs):
        # Do the analysis of the gate diode files as the last one.
        if not all(analysis_type[0:6] == 'IV_GCD' for analysis_type in data[list(data.keys())[0]]['header'][2]):
            data = self.file_order(data)

        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=False, keys='all')
        self.config = configs
        self.df = []
        self.basePlots = None
        self.basePlots_2 = None
        self.name = "IV_PQC"
        self.PlotDict = {"Name": "IV"}
        self.capincluded = False
        # Add different columns to the data frame;
        self.data["columns"].insert(3, "CapacityCopy")
        self.data["columns"].insert(4, "derivative")
        self.data["columns"].insert(5, "derivative2")
        self.data["columns"].insert(6, "1C2")
        self.data["columns"].insert(7, "derivative1C2")
        self.data["columns"].insert(8, "x")
        self.data["columns"].insert(9, "N")
        self.data["columns"].insert(10, "firstderivative_gate")
        self.capincluded = True
        self.measurements = self.data["columns"]
        self.xaxis = self.measurements[0] #Select your x axis, normally voltage.
        # Convert the units to the desired ones
        for meas in self.measurements:
            unit = self.config[self.name].get(meas, {}).get("UnitConversion", None)
            if unit:
                self.data = convert_to_EngUnits(self.data, meas, unit)

    def run(self):
        """Runs the script"""
        # Generate lists to store your plots
        self.PlotDict["BasePlots_MOS"] = []
        self.PlotDict["BasePlots_diode"] = []
        self.PlotDict["BasePlots_gate"] = []

        for df in self.data["keys"]:

            # Start the cv_mos analysis
            if self.data[df]['header'][1][0:6] == "CV_MOS": #check analysis type
                self.PlotDict["BasePlots_MOS"] = self.analysis_mos(df)

            # Start the Diode Analysis
            elif self.data[df]['header'][1][0:8] == 'CV_Diode':
                self.PlotDict["BasePlots_MOS"] = self.analysis_diode(df)

            # Start the Gate diode analysis
            else:
                self.PlotDict["BasePlots_MOS"] = self.analysis_gate(df)

        self.PlotDict["All"] = self.plot(self.PlotDict["BasePlots_diode"], self.PlotDict["BasePlots_MOS"], self.PlotDict["BasePlots_gate"], cv_files, diode_files, gate_files)

        return self.PlotDict

    def file_order(self, data):
        # Do the analysis of the gate diode files as the last one.
        i = 0
        while data[list(data.keys())[0]]['header'][1][0:6] == 'IV_GCD':
            data[list(data.keys())[0] + str(i)] = data[list(data.keys())[0]] # Push the gate diode files to the last elements of the list
            del data[list(data.keys())[0]] # Delete previous position of the gate diode files in the list
            i += 1

        return data

    def analysis_mos(self, df):
        #global fBestimation
        cv_files.append(df)  # Append data-frame to a list containing all the cv mos files that you want to analyze.

        # Double check that the voltage values have increasing order.
        if 'Voltage' in self.data[df]['data'] and self.data[df]["data"]["Voltage"][0] > 0: # If the first element is positive signifies that the voltage values have been stored in decreasing order
            self.data[df]["data"]["Voltage"] = list(reversed(self.data[df]["data"]["Voltage"]))  # If voltage values have decreasing order, reverse them.
            self.data[df]["data"]["Capacity"] = list(reversed(self.data[df]["data"]["Capacity"]))

        # Normalize capacity by the Area and set to cm^2
        self.data[df]["data"]["Capacity"] = self.data[df]["data"]["Capacity"] / (float(self.data[df]["header"][0].split(':')[1]) * (1e-8))

        # Generate a capacity copy without the small kink at the begging of the curve
        CapacityCopy = self.data[df]["data"]["Capacity"].copy()
        capMin = np.max(self.data[df]["data"]["Capacity"][:20])  # Find the Maximum among the first 20 values of the Capacity and set it as the minimum Capacity value
        for x in range(len(self.data[df]["data"]["Capacity"])):
            if CapacityCopy[x] < capMin:
                CapacityCopy[x] = capMin
        # Insert into the data frame
        self.insert_in_df(df, 3, "CapacityCopy", CapacityCopy)

        # Build second derivative
        seconddev = self.build_second_derivative(self.data[df]["data"][self.xaxis], self.data[df]["data"]["CapacityCopy"])
        self.insert_in_df(df, 4, "derivative2", seconddev)

        # Build interpolated plot and interpolated derivatives
        capa_interp_plot, derivative_interpolation_plot, secondderivative_interp_plot, max_firstder_plot, voltage_value_of_max_firstder = self.interpol(df, self.data[df]["data"][self.xaxis], self.data[df]["data"]["CapacityCopy"])

        # Find the index of the row which contains the maximum value of the second derivative
        indexMax = self.data[df]['data'].index.get_loc(self.data[df]['data']['derivative2'].values.argmax())

        # Find the index of the row which contains the minimum value of the second derivative
        indexMin = self.data[df]['data'].index.get_loc(self.data[df]['data']['derivative2'].values.argmin())

        # Plot all Measurements
        self.donts_mos = ["timestamp", "voltage", "Voltage", "Stepsize", "Wait", "Stepsize", "Frequency", "x", "N", "Current"]  # don't plot these.
        self.basePlots5 = plot_all_measurements(self.data, self.config, self.xaxis, self.name, do_not_plot=self.donts_mos, keys=cv_files)
        self.PlotDict["BasePlots_MOS"] = self.basePlots5

        # Add flat bandage voltage point to the Capacity curve
        if self.config["IV_PQC"].get("CapacityCopy", {}).get("findFlatBandVoltage", False):
            try:
                if self.basePlots5.Overlay.MOS_CV_CURVES.children:
                    clone_plot = self.basePlots5.Overlay.MOS_CV_CURVES.opts(clone=True)
                else:
                    clone_plot = self.basePlots5.Curve.MOS_CV_CURVES.opts(clone=True)
                fBestimation = self.find_flatBand_voltage(clone_plot, self.data, self.config, indexMax, indexMin, df, cv_files, voltage_value_of_max_firstder, PlotLabel="Flat band voltage estimation")
            except Exception as err:
                self.log.warning("No flat band voltage calculation possible... Error: {}".format(err))

        # Do these plots for the analysis of one single cv mos file
        if len(cv_files) == 1:
            self.PlotDict["BasePlots_MOS"] += fBestimation[0]
            self.PlotDict["BasePlots_MOS"] += derivative_interpolation_plot
            self.PlotDict["BasePlots_MOS"] += secondderivative_interp_plot
            self.PlotDict["BasePlots_MOS"] += capa_interp_plot
            self.PlotDict["BasePlots_MOS"] += capa_interp_plot * max_firstder_plot * derivative_interpolation_plot * secondderivative_interp_plot
            self.PlotDict["BasePlots_MOS"] += fBestimation[6] * max_firstder_plot * derivative_interpolation_plot

        # Add a Table that shows the differents analysis parameters values
        df2 = pd.DataFrame({"Name": cv_files, "Flatband Voltage second_derivative (V)": fbvoltage,
             'Flatband Voltage first_derivative (V)': fbvoltage_firstderivative,
             'Accumulation capacitance (F)': Accum_capacitance_list,
             'Accumulation capacitance normalized (F/cm^2)': Accum_capacitance_normalized_list, 'Tox (nm)': Tox_list,
             'Nox (cm^-2)': Nox_list})
        table1 = hv.Table(df2, label='Mos analysis')
        table1.opts(width=1300, height=800)
        # Do plots
        self.PlotDict["BasePlots_MOS"] += table1

        return self.PlotDict["BasePlots_MOS"]

    def analysis_diode(self, df):
        #global fdestimation
        diode_files.append(df)  # Append to a list containing all the diode files
        self.data[df]["data"]["Voltage"] = list(map(abs, self.data[df]["data"]["Voltage"]))  # take absolute value of Voltage

        # Try interpolation + filtered savitzy-golay derivative plot
        capacity_curve, derivative_onec2_curve, deronec2_savgol_plot = self.interp_derivative_diode(df, self.data[df]["data"][self.xaxis], self.data[df]["data"]["Capacity"])
        self.insert_in_df(df, 3, "1C2", 1 / self.data[df]["data"]["Capacity"].pow(2))

        # Compute first derivative of 1/C2
        firstdev_invers_C2 = self.build_first_derivative(self.data[df]["data"][self.xaxis], self.data[df]["data"]["1C2"])
        self.insert_in_df(df, 4, "derivative1C2", firstdev_invers_C2)

        # Calculate deep x
        x = (self.config['IV_PQC_parameter']['epsilonNull'] * (1e-6) * float(self.data[df]['header'][0].split(':')[1]) * self.config['IV_PQC_parameter']['epsilonSiliconOxide']) / self.data[df]["data"]["Capacity"][:42]
        self.insert_in_df(df, 5, "x", x)

        # Calculate doping profile
        N = (2) / (self.config['IV_PQC_parameter']['epsilonNull'] * (1e-2) \
                   * self.config['IV_PQC_parameter']['q'] * self.config['IV_PQC_parameter']['epsilonSiliconOxide'] *
                   self.data[df]["data"]["derivative1C2"][:42] \
                   * (float(self.data[df]['header'][0].split(':')[1]) * (1e-8)) * (float(self.data[df]['header'][0].split(':')[1]) * (1e-8)))
        self.insert_in_df(df, 6, 'N', N)

        # Plot all Measurements
        self.donts_diode = ["timestamp", "voltage", "Voltage", "Stepsize", "Wait", "Stepsize", "Frequency", "x", "N", "Capacity", "Current"]  # do not plot capacity voltage plot
        self.basePlots4 = plot_all_measurements(self.data, self.config, self.xaxis, self.name, do_not_plot=self.donts_diode, keys=diode_files)
        self.PlotDict["BasePlots_diode"] = self.basePlots4

        # Add a plot with a different x axis
        self.basePlots_2 = plot_all_measurements(self.data, self.config, 'x', self.name, do_not_plot=['Voltage', 'Current', 'Capacity', '1C2', 'derivative1C2', 'x'], keys=diode_files)  # diode is the list containing all the diode files
        self.PlotDict["BasePlots_diode"] += self.basePlots_2

        # Add full depletion point to 1/c^2 curve
        if self.config["IV_PQC"].get("1C2", {}).get("DoFullDepletionCalculation", False):
            try:
                if self.basePlots4.Overlay.A_1C2.children:
                    c2plot = self.basePlots4.Overlay.A_1C2.opts(clone=True)
                else:
                    c2plot = self.basePlots4.Curve.A_1C2.opts(clone=True)
                fdestimation = self.find_full_depletion_c2(c2plot, self.data, self.config, diode_files, PlotLabel="Full depletion estimation")
            except Exception as err:
                self.log.warning("No full depletion calculation possible... Error: {}".format(err))

        # Find resistivity
        C_min = np.mean(self.data[df]['data']['Capacity'][-20:])
        d_active = self.config['IV_PQC_parameter']['epsilonNull'] * self.config['IV_PQC_parameter']['epsilonSiliconOxide'] * (float(self.data[df]['header'][0].split(':')[1]) * (1e-8)) * (1e-2) / C_min  # in cm
        T_n = 295 / 300
        u_holes_mobility = 54.3 * pow(T_n, -0.57) + 1.36 * (1e+8) * pow(295, -2.23) / (1 + ((5e+12) / (2.35 * (1e+17) * pow(T_n, 2.4))) * 0.88 * pow(T_n, -0.146))  # in cm^2/(V*s)
        rho = d_active * d_active / (2 * self.config['IV_PQC_parameter']['epsilonNull'] * (1e-2) * self.config['IV_PQC_parameter']['epsilonSiliconOxide'] * fdestimation[1] * u_holes_mobility)  # in Ohm * cm
        rho_table = '{:.2e}'.format(rho)  # value to show later on in the table showing the results of the analysis
        resistivity.append(rho_table)

        # Add a table that show the results of the analysis
        if len(diode_files) == 1:
            self.PlotDict["BasePlots_diode"] += fdestimation[0]
            # Add trial plots
            self.PlotDict["BasePlots_diode"] += capacity_curve
            ##self.PlotDict["BasePlots_diode"] += derivative_onec2_curve * deronec2_savgol_plot
            ##self.PlotDict["BasePlots_diode"] += deronec2_savgol_plot
            # Add table
            df3 = pd.DataFrame({"Name": diode_files, "full depletion voltage (V)": fdepvoltage, " Bulk resistivity (Ohm * cm)": resistivity})
            table2 = hv.Table(df3, label='Diode analysis')
            table2.opts(width=1300, height=800)
            self.PlotDict["BasePlots_diode"] += table2

        else:
            df3 = pd.DataFrame({"Name": diode_files, "full depletion voltage (V)": fdepvoltage, "Bulk resistivity (Ohm * cm)": resistivity})
            table2 = hv.Table(df3, label='Diode analysis')
            table2.opts(width=1300, height=800)
            self.PlotDict["BasePlots_diode"] += table2

        return self.PlotDict["BasePlots_diode"]

    def analysis_gate(self, df):
        #global curr_savgol_plot, maxsavgol
        gate_files.append(df)  # append to a list containing all the gate diode files

        # Remove initial kink from the data
        start_value = np.mean(self.data[df]['data']['Current'][10:20])
        CurrentCopy = self.data[df]["data"]["Current"].copy()
        for x in range(int(len(self.data[df]["data"]["Current"]) / 2)):
            if CurrentCopy[x] < start_value:
                CurrentCopy[x] = start_value

        # Generate curve
        plot_not_kink= self.add_single_plots(self.data[df]["data"][self.xaxis], CurrentCopy, "Current")

        # Try savgol filter
        ##try:
        ##    i = 0
        ##    while i < 2:
        ##        curr_savgol = scipy.signal.savgol_filter(self.data[df]['data']['Current'], 31, 3)  # window size 51, polynomial order 3
        ##        i += 1
        ##    maxsavgol = max(curr_savgol)
        ##    curr_savgol_plot = self.add_single_plots(self.data[df]['data']['Voltage'], curr_savgol, "SavgolCurrent")
        ##except Exception:
        ##    self.log.warning("No savgol plot possible... Error: {}")

        # Interpolation current curve
        xnew, ynew = self.interpolated_axis(df, self.data[df]["data"][self.xaxis], CurrentCopy)
        curr_interp_plot = self.add_single_plots(xnew, ynew, "InterpolatedCurrent")

        # Build the first derivatives
        firstderi_interp = self.build_first_derivative(xnew, ynew)
        dif_intep_plot = self.add_single_plots(xnew, firstderi_interp, "FirstDerivativeCurrent")

        # Second derivative
        second_deriv_interp = self.build_second_derivative(xnew, ynew)
        dif2_intep_plot = self.add_single_plots(xnew, second_deriv_interp, "SecondDerivativeCurrent")

        # Not interpolated first derivative
        firstdev_not_interp = self.build_first_derivative(self.data[df]["data"]["Current"], self.data[df]["data"]["Voltage"])
        self.insert_in_df(df, 3, "firstderivative_gate", firstdev_not_interp)

        # Try to find the start and ending indices of the points where you want to average, used to handle the problematic files
        max1_index = list(firstderi_interp).index(max(firstderi_interp))
        min1_index = list(firstderi_interp).index(min(firstderi_interp))
        if min1_index < max1_index:
            min1_index = max1_index + 1
            max1_index = min1_index - 2
        median_index = int(len(xnew) / 2)
        if median_index < max1_index:
            median_index = max1_index + 1
        if min1_index < median_index:
            min1_index = median_index + 1
            max1_index = median_index - 1

        # Find the segment where you want to average using the second derivative
        interesting_section = sorted(list(second_deriv_interp[max1_index:median_index]), reverse=True)
        firstminimum = interesting_section[0]
        interesting_section2 = sorted(list(second_deriv_interp[median_index:min1_index]), reverse=True)
        second_minimum = interesting_section2[0]

        # Find average
        start_average = list(second_deriv_interp).index(firstminimum)
        end_average = list(second_deriv_interp).index(second_minimum)
        I_surf_maxima_average = np.mean(list(ynew[start_average:end_average]))

        # Compute the surface current with the average method
        mxx = max(ynew)  # find maximum value of the current-voltage curve
        miny = np.mean(list(ynew[-1000:]))  # find the minimum of the current-voltage curve by averaging 20 points values in the curve tail
        I_surf_average = I_surf_maxima_average - miny  # compute the surface current by computing the difference between the maximum and minimum value
        I_surf_average_table = '{:.2e}'.format(I_surf_average)
        Surface_current_average.append(I_surf_average_table)

        # Compute surface current with the maximum method
        Isurf_max = mxx - miny  # compute the surface current by computing the difference between the maximum and minimum value
        Isurf_table = '{:.2e}'.format(Isurf_max)
        Surface_current.append(Isurf_table)

        # Compute Surface_recombination_velocity with the maximum method
        S_null_max = Isurf_max / (self.config['IV_PQC_parameter']['q'] * self.config['IV_PQC_parameter']['n_i_intrinsic_carrier_concentration'] * (float(self.data[df]['header'][0].split(':')[1]) * (1e-8)))
        Surface_recombination_velocity.append(S_null_max)

        # Compute Surface_recombination_velocity with the average method
        S_null_average = I_surf_average / (self.config['IV_PQC_parameter']['q'] * self.config['IV_PQC_parameter']['n_i_intrinsic_carrier_concentration'] * (float(self.data[df]['header'][0].split(':')[1]) * (1e-8)))
        Surface_recombination_velocity_average.append(S_null_average)

        # Add text to the plot
        text = hv.Text(3, 9 * (1e-11), 'Isurf_max: {} A\n'
                                       'Isurf_average: {} A\n'
                                       'Surface recombination velocity_max: {} cm/s\n'
                                       'Surface recombination velocity_average: {} cm/s'.format(np.round(Isurf_max, 15), np.round(I_surf_average, 15), np.round(S_null_max, 4), np.round(S_null_average, 4))).opts(style=dict(text_font_size='20pt'))

        # Do this if the analysis is of just one file.
        if len(gate_files) == 1:
            # Add overlaid lines on the plot
            Path_min = hv.Path([(-2, miny), (6, miny)]).opts(line_width=2.0)
            Path_mxx = hv.Path([(-2, mxx), (6, mxx)]).opts(line_width=2.0)
            ##Path_savgolmax = hv.Path([(-2, maxsavgol), (6, maxsavgol)]).opts(line_width=2.0)
            Path_average = hv.Path([(-2, I_surf_maxima_average), (6, I_surf_maxima_average)]).opts(line_width=2.0)
            Path_Isurf = hv.Arrow(-1, mxx, 'max', '^')
            Path_Isurf_average = hv.Arrow(0, I_surf_maxima_average, 'average', '^')
            # Plot all Measurements
            self.donts_gatediode = ["timestamp", "voltage", "Voltage", 'Current', "Stepsize", "Wait", "Stepsize", "Frequency", "x", "N"]  # don't plot these.
            self.PlotDict["BasePlots_gate"] = plot_not_kink
            self.PlotDict["BasePlots_gate"] += dif_intep_plot
            self.PlotDict["BasePlots_gate"] += dif2_intep_plot
            self.PlotDict["BasePlots_gate"] += curr_interp_plot
            try:
                self.PlotDict["BasePlots_gate"] += curr_savgol_plot
                self.PlotDict["BasePlots_gate"] += curr_savgol_plot * plot_not_kink
            except Exception:
                self.log.warning("No savgol plot possible... Error: {}")
            self.PlotDict["BasePlots_gate"] += text * plot_not_kink * Path_min * Path_mxx * Path_average * Path_Isurf * Path_Isurf_average #* Path_savgolmax
            self.PlotDict["BasePlots_gate"] += curr_interp_plot * dif_intep_plot * dif2_intep_plot * plot_not_kink

            # Add table that shows resulting parameters of the analysis
            df4 = pd.DataFrame({"Name": gate_files, "Surface current_max (A)": Surface_current,
                                "Surface current_average (A)": Surface_current_average,
                                'Surface recombination velocity_max (cm/s)': Surface_recombination_velocity,
                                'Surface recombination velocity_average (cm/s)': Surface_recombination_velocity_average})
            table3 = hv.Table((df4), label='Gate analysis')
            table3.opts(width=1300, height=800)
            self.PlotDict["BasePlots_gate"] += table3

        # Do this if the analysis is of more than one file
        elif len(gate_files) > 1:
            self.donts = ["timestamp", "voltage", "Voltage", "Stepsize", "Wait", "Stepsize", "Frequency", "firstderivative_gate", "x", "N"]  # do not plot this data
            self.basePlots3 = plot_all_measurements(self.data, self.config, self.xaxis, self.name, do_not_plot=self.donts, keys=gate_files)
            self.PlotDict["BasePlots_gate"] = self.basePlots3

            # Add table that shows resulting parameters of the analysis
            df4 = pd.DataFrame({"Name": gate_files, "Surface current_max (A)": Surface_current,
                                "Surface current_average (A)": Surface_current_average,
                                'Surface recombination velocity_max (cm/s)': Surface_recombination_velocity,
                                'Surface recombination velocity_average (cm/s)': Surface_recombination_velocity_average})
            table3 = hv.Table((df4), label='Gate analysis')
            table3.opts(width=1300, height=800)
            self.PlotDict["BasePlots_gate"] += table3

        return self.PlotDict["BasePlots_gate"]

    def build_second_derivative(self, xaxis, yaxis):
        # Build first and second derivative
        dx1 = np.diff(xaxis)
        dy2 = np.diff(yaxis, n=2)  # n=2 applies diff() two times to compute the second derivative, dy2 is of length yaxis-2
        dy2 = np.insert(dy2, 0, dy2[0])  # Add one element to dy2 to have the same length of dx1
        seconddev = dy2 / dx1
        seconddev = np.insert(seconddev, 0, seconddev[0])  # Add one element to the array to have the same amount of rows as in df

        return seconddev

    def interpolated_axis(self, df, xaxis, yaxis):
        # Do interpolation
        f = interp1d(xaxis, yaxis, kind='cubic')  # f is the interpolation function
        xnew = np.arange(self.data[df]['data']['Voltage'][0], list(self.data[df]['data']['Voltage'][-1:])[0], 0.001)
        try:
            ynew = f(xnew)
        except Exception:
            ynew = np.arange(len(list(xnew)))

        return xnew, ynew

    def add_single_plots(self, xaxis, yaxis, name):
        points_plot = (xaxis, yaxis)
        interp_plot = hv.Curve(points_plot)
        interp_plot = customize_plot(interp_plot, name, self.config["IV_PQC"])

        return interp_plot

    def interpol(self, df, xaxis, yaxis):
        xnew, ynew = self.interpolated_axis(df, xaxis, yaxis)
        capa_interp_plot = self.add_single_plots(xnew, ynew, "Capacity")

        # Build derivatives of the interpolated data
        firstdev_interp = self.build_first_derivative(xnew, ynew)
        derivative_interpolation_plot = self.add_single_plots(xnew, firstdev_interp, "derivative")
        seconddev_interp = self.build_second_derivative(xnew, ynew)
        secondderivative_interp_plot = self.add_single_plots(xnew, seconddev_interp, "derivative2")

        # Find the flatband-voltage through the maximum value of the first derivative
        item_max = firstdev_interp.argmax()
        voltage_value_of_max_firstder = xnew[item_max]
        max_firstder_plot = hv.VLine(voltage_value_of_max_firstder).opts(line_width=1.0)
        fbvoltage_firstderivative.append(voltage_value_of_max_firstder)

        return capa_interp_plot, derivative_interpolation_plot, secondderivative_interp_plot, max_firstder_plot, voltage_value_of_max_firstder

    def interp_derivative_diode(self, df, xaxis, yaxis):
        # Interpolate the capacity
        xnew, ynew = self.interpolated_axis(df, xaxis, yaxis)
        Onec2 = 1 / (ynew * ynew)  # 1C2 array
        capacity_curve = self.add_single_plots(xnew, Onec2, "1C2")

        # Derivative
        first_dev = self.build_first_derivative(xnew, Onec2)
        derivative_onec2_curve = self.add_single_plots(xnew, first_dev, "1C2")

        # Savgolay plot
        derivative_savgol_filtered = scipy.signal.savgol_filter(first_dev, 5, 3)  # Window size 5, polynomial order 3
        deronec2_savgol_plot = self.add_single_plots(xnew, derivative_savgol_filtered, "1C2")

        return capacity_curve, derivative_onec2_curve, deronec2_savgol_plot

    def find_flatBand_voltage(self, plot, data, configs, indexMax, indexMin, df, cv_files, voltage_value_of_max_firstder, **addConfigs): #cv is the list containing all the cvmos files
        """
        Finds the full depletion voltage of all data samples and adds a vertical line for the full depletion in the
        plot. Vertical line is the mean of all measurements. Furthermore, adds a text with the statistics.
        :param plot: The plot object
        :param data: The data files
        :param configs: the configs
        :param **addConfigs: the configs special for the 1/C2 plot, it is recommended to pass the same options here again, like in the original plot!
        :return: The updated plot
        """
        #global Right_stats, fit_stats
        self.log.info("Searching for flat band voltage in all files...")
        sample = deepcopy(data[df])

        # Create a new data frame with just two columns
        try:
            df1 = pd.DataFrame({"xaxis": sample["data"]["voltage"], "yaxis": sample["data"]["CapacityCopy"]})
        except Exception:
            df1 = pd.DataFrame({"xaxis": sample["data"]["Voltage"], "yaxis": sample["data"]["CapacityCopy"]})
        df1 = df1.dropna()

        # Loop one time from the right side, to get the slope of the accumulation region, and then loop on the fit region to get the fit slope
        RR2 = 0
        fitR2 = 0
        for idx in range(5, len(df1)-5):
            # Right
            slope_right, intercept_right, r_right, p_value, std_err_right = linregress(df1["xaxis"][idx:],df1["yaxis"][idx:])
            r2_right = r_right * r_right
            self.log.debug("Right side fit: Slope {}, intercept: {}, r^2: {}, std: {}".format(slope_right, intercept_right, r2_right, std_err_right))

            # See if the r2 value has increased and store it
            if r2_right >= RR2:
                RR2 = r2_right
                RightEndPoints = (
                    (df1["xaxis"][idx], slope_right * df1["xaxis"][idx] + intercept_right),
                    (df1["xaxis"][len(df1["xaxis"]) - 1], slope_right * df1["xaxis"][len(df1["xaxis"]) - 1] + intercept_right)
                )
                Right_stats = [RightEndPoints, slope_right, intercept_right, r_right, p_value, std_err_right]

        # Fit central region
        for idx in range(indexMax, indexMin-1):
            # Do central fit
            slope_fit, intercept_fit, r_fit, p_valuefit, std_err_fit = linregress(df1["xaxis"][idx:indexMin-1],df1["yaxis"][idx:indexMin-1])
            r2_fit = r_fit * r_fit
            self.log.debug("central fit: Slope {}, intercept: {}, r^2: {}, std: {}".format(slope_fit, intercept_fit, r2_fit, std_err_fit))

            # See if the r2 value has increased and store it
            if r2_fit >= fitR2:
                fitR2 = r2_fit
                fitEndPoints = (
                    (df1["xaxis"][indexMax], slope_fit * df1["xaxis"][indexMax] + intercept_fit),
                    (df1["xaxis"][idx+1], slope_fit * df1["xaxis"][idx+1] + intercept_fit) # use idx +1 to avoid having the same end points
                )
                fit_stats = [fitEndPoints, slope_fit, intercept_fit, r_fit, p_valuefit, std_err_fit]

        # Add central slope
        xmax = df1["xaxis"][indexMin]
        fit_line = np.array([[df1["xaxis"][indexMax-3], fit_stats[1] * df1["xaxis"][indexMax-3] + fit_stats[2]], [xmax+0.2, fit_stats[1] * (xmax+0.2) + fit_stats[2]]])

        # Add right slope
        xmax = df1["xaxis"][len(df1["yaxis"]) - 1]
        right_line = np.array([[df1["xaxis"][indexMax-3], Right_stats[1] * df1["xaxis"][indexMax-3] + Right_stats[2]], [xmax, Right_stats[1] * xmax + Right_stats[2]]])

        # Compute the flatband voltage
        flatband_voltage = line_intersection(fit_stats[0], Right_stats[0])
        self.log.info("Flatband voltage to data file {} is {}".format(df,flatband_voltage[0]))

        # Find oxide thickness Tox in nm
        Accum_capacitance = np.max(df1["yaxis"]) * (float(self.data[df]['header'][0].split(':')[1]) * (1e-8))  # float(..) is the area.
        Accum_capacitance_table = '{:.2e}'.format(Accum_capacitance)
        Accum_capacitance_normalized = np.max(df1["yaxis"])  # F/cm^2
        Accum_capacitance_normalized_table = '{:.2e}'.format(Accum_capacitance_normalized)
        Tox = self.config['IV_PQC_parameter']['epsilonNull'] * self.config['IV_PQC_parameter']['epsilonSiliconOxide'] * 1e+5 / Accum_capacitance_normalized
        Tox_table = '{:.2e}'.format(Tox)

        # Find Fixed oxide charge Nox in cm^-2
        phi_s = self.config['IV_PQC_parameter']['electronAffinity'] + self.config['IV_PQC_parameter']['bandGapEnergy'] / 2 \
                + (self.config['IV_PQC_parameter']['boltzmannConstant'] * self.config['IV_PQC_parameter']['Temperature']
                   * np.log(self.config['IV_PQC_parameter']['SiliconDoping'] / self.config['IV_PQC_parameter']['intrinsicDopingConcentration'])) / self.config['IV_PQC_parameter']['q']
        phi_ms = self.config['IV_PQC_parameter']['phi_m'] - phi_s
        Nox = (Accum_capacitance_normalized * (phi_ms + flatband_voltage[0])) / (self.config['IV_PQC_parameter']['q'])
        Nox_table = '{:.2e}'.format(Nox) # Value to insert later on in the results table

        # Append the values resulting from the analysis to the corresponding lists.
        fbvoltage.append(flatband_voltage[0])
        Accum_capacitance_list.append(Accum_capacitance_table)
        Accum_capacitance_normalized_list.append(Accum_capacitance_normalized_table)
        Tox_list.append(Tox_table)
        Nox_list.append(Nox_table)

        # Add text
        text = hv.Text(10, 0.00000000065, 'Flat band voltage_fit_2nd derivative: {} V \n'
                                            'Flat band voltage first derivative: {} V \n'
                                            'C accumulation: {} F \n'
                                            'C accumulation/A: {} F/cm\N{SUPERSCRIPT TWO} \n'
                                            'Tox: {} nm \n'
                                            'Nox: {} cm\N{SUPERSCRIPT MINUS}\N{SUPERSCRIPT TWO}'.format(
            np.round(np.median(flatband_voltage[0]), 2),
            np.round(voltage_value_of_max_firstder, 2),
            np.round(Accum_capacitance, 10),
            np.round(Accum_capacitance_normalized, 10),
            np.round(Tox, 2),
            np.format_float_scientific(Nox, 2))).opts(style=dict(text_font_size='25pt'))

        # If more than one file do not do the derivates plots
        if not len(cv_files) == 1:
            returnPlot = plot
            returnPlot = customize_plot(returnPlot, "1C2", configs["IV_PQC"], **addConfigs)
            return returnPlot, flatband_voltage[0], Accum_capacitance_table, Accum_capacitance_normalized_table, Tox_table, Nox_table

        elif len(cv_files) == 1:
            # Plot a vertical line in the value of the fb voltage
            vline = hv.VLine(flatband_voltage[0]).opts(color='black', line_width=1.0)

            # Plots of the derivatives
            secondDerivativePlot = self.basePlots5.Curve.secondderivative

            # Plots of the fits
            right_line = hv.Curve(right_line).opts(color='blue',line_width=1.0)
            fit_line = hv.Curve(fit_line).opts(color='red', line_width=1.5)
            returnPlot = plot * right_line * fit_line * secondDerivativePlot * vline
            returnPlot = customize_plot(returnPlot, "1C2", configs["IV_PQC"], **addConfigs)
            returnplot2 = plot * fit_line * right_line * vline * text
            return returnPlot, flatband_voltage[0], Accum_capacitance_table, Accum_capacitance_normalized_table, Tox_table, Nox_table, returnplot2

    def find_full_depletion_c2(self, plot, data, configs, diode_files, **addConfigs):
        """
        Finds the full depletion voltage of all data samples and adds a vertical line for the full depletion in the
        plot. Vertical line is the mean of all measurements. Furthermore, adds a text with the statistics.
        :param plot: The plot object
        :param data: The data files
        :param configs: the configs
        :param **addConfigs: the configs special for the 1/C2 plot, it is recomended to pass the same options here again, like in the original plot!
        :return: The updated plot
        """
        #global LeftEndPoints, df
        Left_stats = np.zeros((len(diode_files), 6), dtype=np.object)
        self.log.info("Searching for full depletion voltage in all files...")

        for samplekey in diode_files:
            if "1C2" not in data[samplekey]["data"]:
                self.log.warning("Full depletion calculation could not be done for data set: {}".format(samplekey))
            else:
                self.log.debug("Data: {}".format(samplekey))
                sample = deepcopy(data[samplekey])
                df = pd.DataFrame({"xaxis": sample["data"]["Voltage"], "yaxis": sample["data"]["1C2"]})
                df = df.dropna()

                # Loop one time from the from the left side, to get the slope
                LR2 = 0
                for idx in range(5, len(df)-20):
                    # Left
                    slope_left, intercept_left, r_left, p_value, std_err_left = linregress(df["xaxis"][:-idx], df["yaxis"][:-idx])
                    r2_left = r_left * r_left
                    self.log.debug("Left side fit: Slope {}, intercept: {}, r^2: {}, std: {}".format(slope_left, intercept_left, r2_left, std_err_left))

                    # See if the r2 value has increased and store end points
                    if r2_left >= LR2:
                        LR2 = r2_left
                        LeftEndPoints = ((df["xaxis"][0], intercept_left), (df["xaxis"][idx], slope_left * df["xaxis"][idx] + intercept_left))

        # Find the right fit by averaging on the final 20 points
        average_right = np.mean(list(df['yaxis'][-20:]))
        RightEndPoints =[(df['xaxis'][len(df['xaxis'])-20], average_right), (df['xaxis'][len(df['xaxis'])-1], average_right)]

        # Find the line intersection
        full_depletion_voltages = line_intersection(LeftEndPoints, RightEndPoints)
        fdepvoltage.append(full_depletion_voltages[0])
        self.log.info('Full depletion voltage: {} V'.format(np.round(full_depletion_voltages[0], 2)))

        # Add vertical line for full depletion
        vline = hv.VLine(full_depletion_voltages[0]).opts(color='black', line_width=5.0)

        # Add slopes
        left_line = np.array([[0, np.median(Left_stats[:,2])], [full_depletion_voltages[0], full_depletion_voltages[1]]])
        left_line = hv.Curve(left_line).opts(color='grey')
        right_line = hv.HLine(average_right).opts(color='grey')

        # Add text
        text = hv.Text(230, 5e+21, 'Depletion voltage: {} V'.format(np.round(full_depletion_voltages[0], 2))).opts(style=dict(text_font_size='20pt'))

        # Update the plot specific options if need be
        returnPlot = plot * vline * right_line * left_line * text
        returnPlot = customize_plot(returnPlot, "1C2", configs["IV_PQC"], **addConfigs)

        return returnPlot, full_depletion_voltages[0]

    def plot(self, diodePlots, mos_Plots, gate_Plots, cv_files, diode_files, gate_files):
        # Select the plots to show depending on the kind of files you have
        if len(cv_files) != 0 and len(diode_files) != 0 and len(gate_files) != 0:
            self.PlotDict['All'] = gate_Plots + diodePlots + mos_Plots
        elif len(cv_files) != 0 and len(diode_files) != 0 and len(gate_files) == 0:
            self.PlotDict['All'] = diodePlots + mos_Plots
        elif len(cv_files) == 0 and len(diode_files) != 0 and len(gate_files) == 0:
            self.PlotDict['All'] = diodePlots
        elif len(cv_files) != 0 and len(diode_files) == 0 and len(gate_files) == 0:
            self.PlotDict['All'] = mos_Plots
        elif len(cv_files) == 0 and len(diode_files) == 0 and len(gate_files) != 0:
            self.PlotDict['All'] = gate_Plots
        elif len(cv_files) != 0 and len(diode_files) == 0 and len(gate_files) != 0:
            self.PlotDict['All'] = gate_Plots + mos_Plots
        else:
            self.PlotDict['All'] = diodePlots + gate_Plots
        self.PlotDict["All"] = applyPlotOptions(self.PlotDict["All"], {'Curve': {'color': "hv.Palette('Category20')"}})  # To change colors

        return self.PlotDict["All"]

    def build_first_derivative(self, xaxis, yaxis):
        dx = np.diff(xaxis)
        dy = np.diff(yaxis)
        firstdev = dy / dx
        firstdev = np.insert(firstdev, 0, firstdev[0])  # Add an element to the array to have the same number of rows as in df

        return firstdev

    def insert_in_df(self, df, column, name, measurement):
        self.data[df]["data"].insert(column, name, measurement)
        self.data[df]["units"].append("arb. units")
        self.data[df]["measurements"].append(name)