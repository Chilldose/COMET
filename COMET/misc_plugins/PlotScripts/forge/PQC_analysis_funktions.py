import numpy as np
import holoviews as hv
import pandas as pd
import logging

from scipy.interpolate import interp1d
from scipy.stats import linregress
from scipy.signal import savgol_filter

log = logging.getLogger(__name__)

"""Analysis function for PQC setup files written by Florentin Huemer during his project thesis at HEPHY 2020"""

def linear_fit(x_Values,y_Values, full=False):
    '''returns array [y_values],slope, standard deviation of slope'''
    coef, cov_matrix = np.polyfit(x_Values, y_Values, 1, cov=True)
    line = coef[0] * x_Values + coef[1]
    variance = cov_matrix[0][0]
    std = np.sqrt(variance)
    if full:
        return line, coef[0], std
    else:
        return line

def Van_der_Pauw(x,y):
    _, slope, std = linear_fit(x, y, full=True)
    std = std * np.pi / np.log(2)
    sheet_r = slope * np.pi / np.log(2)
    return sheet_r, std

###############
'''MOS Flatbadvoltage'''
'''use plot_flatband_v for holoviews object, use fit_analysis or derivative analysis for voltage'''

def first_derivative(x, y):
    dy = np.zeros(len(y))
    dy[0] = (y[0] - y[1]) / (x[0] - x[1])
    dy[-1] = (y[-1] - y[-2]) / (x[-1] - x[-2])
    for i in range(1, len(y) - 1):
        dy[i] = (y[i + 1] - y[i - 1]) / (2 * (x[i] - x[i - 1]))
    return list(dy)

def interpolate(x, y, stepsize=0.01):
    '''smaller stepsize --> more points'''
    xnew = np.arange(x[0], x[-1], stepsize)
    f = interp1d(x, y, kind="cubic")
    ynew = f(xnew)
    return list(xnew), list(ynew)

def line_intersection(line1, line2):
    """Usage: line_intersection((A, B), (C, D))"""
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        log.error("Lines does not intersect...")
        return None

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y

def fit_analysis(x,y):
    '''uses fit method'''
    '''returns list of: Voltage and 2 tupels each containing 2 points (x,y) for the fit lines'''
    RR2 = 0
    fitR2 = 0
    for idx in range(5, len(x) - 5):
        # Right
        slope_right, intercept_right, r_right, _, std_err_right = linregress(x[idx:], y[idx:])
        r2_right = r_right * r_right

        # See if the r2 value has increased and store it
        if r2_right >= RR2:
             RR2 = r2_right
             RightEndPoints = ((x[idx], slope_right * x[idx] + intercept_right),
                               (x[len(x) - 1], slope_right * x[len(x) - 1] + intercept_right))
             Right_stats = [RightEndPoints, slope_right, intercept_right, r_right, _, std_err_right]

    startIndex = y.index(min(y))
    endIndex = len(x) - 1

    # Fit central region
    for idx in range(startIndex + 5, endIndex - 1):
        # Do central fit
        slope_fit, intercept_fit, r_fit, _, _ = linregress(x[startIndex: idx], y[startIndex: idx])
        r2_fit = r_fit * r_fit

        # See if the r2 value has increased and store it
        if r2_fit >= fitR2:
            fitR2 = r2_fit
            fitEndPoints = ((x[startIndex], slope_fit * x[startIndex] + intercept_fit),
                               (x[idx + 1], slope_fit * x[idx + 1] + intercept_fit))
            fit_stats = [fitEndPoints, slope_fit, intercept_fit, r_fit, _, _]

    # Add central slope, -3 on x value so the line doesnt end too soon, fit_line = [[start_x,start_x],[end_x,end_y]]
    xmax = x[endIndex]
    m_start = (x[startIndex - 3], fit_stats[1] * x[startIndex - 3] + fit_stats[2])
    m_end = (xmax + 0.2, fit_stats[1] * (xmax + 0.2) + fit_stats[2])

    # Add right slope
    xmax = x[len(y) - 1]
    r_start = (x[startIndex - 3], Right_stats[1] * x[startIndex - 3] + Right_stats[2])
    r_end = (xmax, Right_stats[1] * xmax + Right_stats[2])

    # intersect lines and store only the voltage
    flatband_voltage = line_intersection(fit_stats[0], Right_stats[0])[0]

    '''m_start is a tuple containing (x,y) values of the start point of the middle fit line'''
    return [flatband_voltage, (m_start, m_end), (r_start, r_end)]

def plot_flatband_v(x, y, ana_type, **kwargs):
    '''
    **kwargs for customizing the plot, ana_type must ether be "fit" or "derivative"
    '''
    x, y = list(x), list(y)
    if ana_type == "fit":
        voltage, middle_line, right_line = fit_analysis(x, y)
    elif ana_type == "derivative":
        voltage = derivative_analysis(x, y)
    else:
        log.error("ana_type must either be 'derivative' or 'fit'")
        exit(1)
    curve = hv.Curve(zip(x, y), kdims="voltage_hvsrc", vdims="capactiance")

    text_str = "Flatband Voltage: " + str(voltage) + "\nAnalysis Type: " + ana_type
    text = hv.Text(max(x) * (3 / 4), max(y) * (3 / 4), text_str, fontsize=20)
    line = hv.VLine(voltage).opts(color="black", line_width=1.0)

    curve = curve * text * line
    if ana_type == "fit":
        mid = hv.Curve([*middle_line]).opts(color="red", line_width=1.5)
        right = hv.Curve([*right_line]).opts(color="blue", line_width=1.0)
        curve = curve * text * line * mid * right
    curve.opts(ylim=(min(y) - 3 * min(y) / 20, max(y) + max(y) / 10), **kwargs)
    return curve

def derivative_analysis(x, y):
    '''returns voltage'''
    dy = first_derivative(x, y)
    df = pd.DataFrame({"x": x, "dy": dy})
    df = df.drop_duplicates(subset='x', keep='first')
    df = df[df.dy == df.dy.max()]
    return round(df['x'].iloc[0], 4)

###########################
'''FET'''
'''use voltage_FET for Voltage, use plot_FET for holoviews object'''

def plot_FET(x, y, ana_type, **kwargs):
    dy = derivative_wrapper(x, y, ana_type)
    return plot_ana(x, y, dy, ana_type, **kwargs)

def derivative_wrapper(x, y, ana_type, window_size=11, poly_deg=3):
    '''Ana 1: dy=first derivative, Ana 2: dy=second derivative, Ana 3: dy=second derivative of log(y)'''
    if ana_type == "Ana 1":
        y = savgol_filter(y, window_size, poly_deg)
        dy = first_derivative(x, y)
    elif ana_type == "Ana 2":
        y = savgol_filter(y, window_size, poly_deg)
        dy = first_derivative(x, y)
        dy = first_derivative(x, dy)

    elif ana_type =="Ana 3":
        y = savgol_filter(y, window_size, poly_deg)
        dy = first_derivative(x, np.log(y))
        dy = first_derivative(x, dy)
        dy[:] = [value / (2 * 10**6) for value in dy]
    return dy

def plot_ana(x, y, dy, ana_type, **kwargs):
    curve = hv.Curve(zip(x, y))
    derivative = hv.Curve(zip(x, dy)).opts(color="gray")
    df = pd.DataFrame({"x": x, "y": y, "dy": dy})

    '''returns voltage and: for Ana 1 fit line, for Ana 2/3 line to show where the voltage is'''
    voltage, line = find_voltage(df, x, ana_type)
    voltage = round(voltage, 4)

    text_str = "voltage: " + str(voltage)
    if ana_type == "Ana 3":
        text_str += "\nDerivative scaled down by: \n/ (2 * 10^6)"
    text = hv.Text(min(dy) * (6 / 4), max(dy) * (7 / 8), text_str, fontsize=20)

    curve = curve * derivative * line * text
    if ana_type == "Ana 3":
        curve.opts(ylim=(min(dy) - 3 * min(y) / 20, max(dy) + max(dy) / 10), **kwargs)
    else:
        curve.opts(ylim=(min(y) - 3 * min(y) / 20, max(y) + max(y) / 10), **kwargs)

    return curve

def find_voltage(df, x, ana_type):
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

def voltage_FET(x, y, ana_type):
    '''takes x,y values and ana_type (either "Ana 1", "Ana 2" or "Ana 3")'''
    '''returns voltage'''
    dy = derivative_wrapper(x, y, ana_type)
    df = pd.DataFrame({"x": x, "y": y, "dy": dy})
    voltage = find_voltage(df, x, ana_type)
