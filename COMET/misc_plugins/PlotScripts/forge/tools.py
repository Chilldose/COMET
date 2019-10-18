# Here some special tools for the analysis are put

import numpy as np
import logging
from .utilities import load_yaml
import os, sys
import re
import holoviews as hv
from holoviews import opts
import numpy as np
hv.extension('bokeh')
import pandas as pd
from bokeh.models import LinearAxis, Range1d
from bokeh.io import export_svgs, export_png
from bokeh.io import save
import json, yaml
from copy import deepcopy
try:
    import pdfkit
except:
    pass



log = logging.getLogger("tools")
sys.path.append("../")

# Here all basic custom scripts which alter the plot must be called.
# Each script must return the altered PlotObject
def convert_to_EngUnits(data, dataType, unit="nano"):
    """Takes a data dict with arbiterary number of measurements and converts a axis to a specific eng unit
     for a specific measurement
    """
    log.info("Converting {} for all measurements to '{}'".format(dataType, unit))
    engUnits = {
        ("T","tera") : 1e12,
        ("G","giga") : 1e9,
        ("M","mega") : 1e6,
        ("k","kilo") : 1e3,
        ("","") :     1e0,
        ("m","milli") : 1e-3,
        ("u","micro") : 1e-6,
        ("n","nano") : 1e-9,
        ("p","pico") :  1e-12
    }

    for file in data["keys"]:
        # Find current order of magnitude
        if dataType in data[file]["measurements"]:
            idx = data[file]["measurements"].index(dataType)
            if len(data[file]["units"][idx]) > 1:
                oldunit = data[file]["units"][idx][0] # The first should be the correct magnitude
            else: oldunit = ""

            # find unit to convert to old and new
            old_unit_key = ("","")
            for keys in engUnits.keys():
                if unit in keys:
                    to_convert = keys
                if oldunit in keys:
                    old_unit_key = keys

            # Calc difference between the units
            factor = engUnits[old_unit_key]/engUnits[to_convert]
            data[file]["data"][dataType] = data[file]["data"][dataType]*factor

            if len(data[file]["units"][idx]) > 1:
                # Todo: error in units if several conversions are made!!!!
                # Convert the units to the correct representation
                data[file]["units"][idx] = to_convert[0] + data[file]["units"][idx][:]
            else:
                data[file]["units"][idx] = to_convert[0] + data[file]["units"][idx]
        else:
            log.warning("Conversion of units could not be done due to missing data! Data set: {}".format(file))
            return data

    # Convert the all df as well
    factor = engUnits[old_unit_key] / engUnits[to_convert]
    data["All"][dataType] = data["All"][dataType] * factor

    return data


    # if "ToolsOptions" in configs.get(plotType, {}):
    #     log.info("Starting customizing plot with tool box scripts...")
    #     kwargs = configs[plotType]["ToolsOptions"]
    #
    #     # Engineering Notation
    #     log.info("Engineering notation...")
    #     plot = EngUnit_representation(plot, kwargs.get("xaxisENG", False), kwargs.get("yaxisENG", False))
    #
    # else:
    #     log.debug(
    #         "No ToolsOptions defined, no alterations made to plot, continuing with holoviews configurations...")

def SimplePlot(data, configs, measurement_to_plot, xaxis_measurement, analysis_name):
    """
    Plots a panda data frames together
    :param data: the data structure for one measurement
    :param configs: the configs dict
    :param measurement_to_plot: y data
    :param xaxis_measurement: name of the meausurement which define the xaxsis, x data
    :param analysis_name: The name of the analysis, from the config
    :return: Holoviews plot object
    """

    # Generate a plot with all data plotted
    log.debug("Started plotting {} curve...".format(measurement_to_plot))
    return holoplot(measurement_to_plot, data, configs.get(analysis_name, {}), xaxis_measurement, measurement_to_plot)

def plot_all_measurements(data, config, xaxis_measurement, analysis_name, do_not_plot=()):
    """
    Simply plots all available measurements from data frames against one xaxsis measurement.
    The data structure needs a entry for 'measurements' containing a list of all measurements
    :param data: The data structure
    :param config: The Configs dictionary
    :param xaxis_measurement: The measurement against all others are plotted
    :param analysis_name: The analysis name out of which the configs for the individual plots are extracted
    :param do_not_plot: List/tuple of plots which should not be plotted
    :return: Holoviews Plot object
    """

    finalPlot = None
    for measurement in data["columns"]:
        if measurement not in do_not_plot:
            if finalPlot:
                finalPlot += SimplePlot(data, config, measurement, xaxis_measurement, analysis_name)
            else:
                finalPlot = SimplePlot(data, config, measurement, xaxis_measurement, analysis_name)


    return config_layout(finalPlot, **config.get(analysis_name, {}).get("Layout", {}))

def save_plot(name, subplot, save_dir, save_as="default"):
    """Saves a plot object"""
    log.info("Saving {}".format(name))

    try:
        if "default" in save_as:
            fig = hv.render(subplot, backend='bokeh')
            save(fig, os.path.join(save_dir, "{}.html".format(name)), fmt="html", title=name)  # , width=1920, height=1080)
        if "html" in save_as:
            fig = hv.render(subplot, backend='bokeh')
            path = os.path.join(save_dir, "html")
            if not os.path.exists(path):
                os.mkdir(path)
            save(fig, os.path.join(path, "{}.html".format(name)), fmt="html", title=name)  # , width=1920, height=1080)

            if "pdf" in save_as:
                #todo: does not work :/
                htmlpath = path
                path = os.path.join(save_dir, "pdf")
                if not os.path.exists(path):
                    os.mkdir(path)
                options = {
                    'page-size': 'A4',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                }

                pdfkit.from_file(os.path.join(htmlpath, "{}.html".format(name)),
                                 os.path.join(path, "{}.pdf".format(name)),
                                 options=options)


        if "png" in save_as:
            fig = hv.render(subplot.opts(toolbar=None), backend='bokeh')
            path = os.path.join(save_dir, "png")
            if not os.path.exists(path):
                os.mkdir(path)
            export_png(fig, os.path.join(path, "{}.png".format(name)))  # , width=1920, height=1080)
        if "svg" in save_as:
            #subplot.output_backend = "svg"
            fig = hv.render(subplot.opts(toolbar=None), backend='bokeh')
            path = os.path.join(save_dir, "svg")
            if not os.path.exists(path):
                os.mkdir(path)
            fig.output_backend = "svg"
            export_svgs(fig, os.path.join(path, "{}.svg".format(name)))
            #export_svgs(fig, os.path.join(path, "{}.svg".format(name)),)
    except Exception as err:
        log.warning("Exporting plot {} was not possible. Error: {}".format(name, err))
        log.info("Try exporting as png...")
        fig = hv.render(subplot.opts(toolbar=None), backend='bokeh')
        try:
            export_png(fig, os.path.join(save_dir, "{}.png".format(name)))  # , width=1920, height=1080)
            log.info("Exporting as png was successful!")
        except:
            log.error("Exporting '{}' as png was also not possible...".format(name))

def twiny(plot, element):
    # Setting the second y axis range name and range
    # Usage:
    # >>> curve_acc = hv.Scatter(options)(plot=dict(finalize_hooks=[twinx]))
    start, end = (element.range(1))
    label = element.dimensions()[1].pprint_label
    plot.state.extra_y_ranges = {"foo": Range1d(start=start, end=end)}
    # Adding the second axis to the plot.
    linaxis = LinearAxis(axis_label=label, y_range_name='foo')
    plot.state.add_layout(linaxis, 'right')


def reject_outliers(sr, iq_range=0.5):
    pcnt = (1 - iq_range) / 2
    qlow, median, qhigh = sr.dropna().quantile([pcnt, 0.50, 1-pcnt])
    iqr = qhigh - qlow
    return sr[ (sr - median).abs() <= iqr]

def config_layout(PlotItem, **kwargs):
    """Configs the layout of the output"""
    for key, value in kwargs.items():
        getattr(PlotItem, key)(value)

    PlotItem.opts(
        opts.Curve(tools=['hover']),
        opts.Scatter(tools=['hover']),
        opts.Histogram(tools=['hover']),
        opts.Points(tools=['hover']),
        opts.BoxWhisker(tools=['hover']),
        opts.Violin(tools=['hover'])
    )
    return PlotItem

def convert_to_df(to_convert, abs = False):
    """
    Converts a dict to panda dataframes for easy manipulation etc.
    :param data: Dictionary with data
    :param abs: if the data returned will be the absolute value of the data
    :return: pandas data frame object
    """
    # Convert all data to panda data frames
    index = list(to_convert.keys())
    columns = list(to_convert[index[0]]["data"].keys())
    return_dict = {"All": pd.DataFrame(columns=columns), "keys": index, "columns":columns}
    for key, data in to_convert.items():
        return_dict[key] = data
        try:
            if abs:
                for meas, arr in data["data"].items():
                    data["data"][meas] = np.abs(arr)
            data["data"]["Name"] = [key for i in range(len(data["data"][list(data["data"].keys())[0]]))]
            df = pd.DataFrame(data=data["data"])
        except KeyError as err:
            log.error("In order to convert the data to panda dataframe, the data structure needs to have a key:'data'")
            raise err
        return_dict[key]["data"] = df
        return_dict["All"] = pd.concat([return_dict["All"],df], sort=True)

    return return_dict

def holoplot(plotType, df_list, configs, xdata, ydata, **addConfigs):
    """
    Simply plots an configs a plot
    :param plotType: The type of plot, e.g. 'IV'
    :param df_list: List of panda dataframes
    :param configs: the plot configuration dicts, only dicts with entries holoviews can decode, all other in kwargs
    :param xdata: xlabel which will be plotted
    :param ydata: ylabel which will be plotted
    :param **kwargs: some additional kwargs which can be needed by the self written tools
    :return: Holoviews plot object
    """

    # Add the additional configs to the configs
    configs = configs.copy()
    finalPlot = None
    # Loop over all types of plots which should be created
    for type in configs.get(plotType, {}).get("PlotStyles", ["Curve"]):
        plot = None
        # Loop over all data
        log.info("Generating plot {} in Style {}".format(plotType, type))
        for key in df_list["keys"]:
            if hasattr(hv,type):
                if ydata in df_list[key]["data"]:
                    log.debug("Generating plot {} for {}".format(key, plotType))
                    # get labels from the configs
                    ylabel = "{} [{}]".format(ydata, df_list[key]["units"][df_list[key]["measurements"].index(ydata)])
                    xlabel = "{} [{}]".format(xdata, df_list[key]["units"][df_list[key]["measurements"].index(xdata)])
                    if plot:
                        plot *= getattr(hv, type)(df_list[key]["data"], xdata, ydata, label=key)
                    else: plot = getattr(hv, type)(df_list[key]["data"], xdata, ydata, label=key)
                    plot.opts(xlabel=xlabel, ylabel=ylabel)
                else:
                    log.warning("The data key: {} is not present in dataset {}. Skipping this particular plot.".format(ydata, key))
            else:
                log.error("The plot type {} is not part of Holoviews.".format(type))
        log.debug("Generated plot: {} of type {}".format(plot, type))

        # Configure the plot
        log.debug("Configuring plot...")

        # Update the plot specific options if need be
        addConfigs.update(configs.get(plotType, {}).get("{}Options".format(type), {}))
        plot = customize_plot(plot, plotType, configs, **addConfigs)

        if finalPlot:
            finalPlot += plot
        else:
            finalPlot = plot

    return finalPlot

def relabelPlot(plot, label):
    return plot.relabel(label)

def customize_plot(plot, plotName, configs, **addConfigs):
    """
    This function customizes the Plot like axis etc.
    :param plot: The holoviews plot object
    :param plotName: The name of the Plot
    :param configs: The Configs specific for this analysis.
    :return: configured plot object
    """

    # Get options
    log.debug("Configuring plot with holoviews parameters for plot {}...".format(plotName))
    gen_opts = configs.get("General", {})
    specific_opts = configs.get(plotName,{}).get("PlotOptions", {})
    options = {}
    options.update(gen_opts)
    options.update(specific_opts)
    options.update(addConfigs)
    plot = plot.relabel(configs.get(plotName, {}).get("PlotLabel", "")).opts(**options)
    return plot

def read_in_JSON_measurement_files(filepathes):
    """This function reads in a QTC measurement file and return a dictionary with the data in the file"""
    all_data = {}
    load_order = []

    try:
        for files in filepathes:
            filename = os.path.basename(str(files)).split(".")[0][4:]
            log.info("Try reading JSON file: {}".format(filename))
            current_file = files
            data = load_yaml(os.path.normpath(files))
            # Add filename and rest of the dict important values
            data.update({"analysed": False, "plots": False})
            all_data[filename] = data
            load_order.append(filename)

        return all_data, load_order

    except Exception as e:
        log.error("Something went wrong while importing the file " + str(current_file) + " with error: " + str(e))

def read_in_ASCII_measurement_files(filepathes, settings):
    """This function reads in a QTC measurement file and return a dictionary with the data in the file"""

    all_data = {}
    load_order = []

    try:
        for files in filepathes:
            filename = os.path.basename(str(files)).split(".")[0]
            log.info("Try reading ASCII file: {}".format(filename))
            current_file = files
            with open(os.path.normpath(files)) as f:
                data = f.read()
            data = parse_file_data(data, settings)
            # Add filename and rest of the dict important values
            data.update({"analysed": False, "plots": False})
            all_data[filename] = data
            load_order.append(filename)

        return all_data, load_order

    except Exception as e:
        log.error("Something went wrong while importing the file " + str(current_file) + " with error: " + str(e))


def parse_file_data(filecontent, settings):
    """This function parses the ADCII file content to the needed data types"""
    filecontent = filecontent.split("\n")

    header = filecontent[:settings["header_lines"]]
    measurements = filecontent[settings["measurement_description"] - 1:settings["measurement_description"]]
    units = filecontent[settings["units_line"] - 1:settings["units_line"]]
    data = filecontent[settings["data_start"] - 1:]

    units_exp = re.compile(r"#?\w*\s?\W?(\w*)\W?\s*")
    data_exp = re.compile(r"(#|\w+)\s?\W?\w*\W?", re.MULTILINE)

    regex = [data_exp, units_exp]

    # First parse the units and measurement types
    parsed_obj = []
    for k, data_to_split in enumerate((measurements, units)):
        for i, meas in enumerate(data_to_split):  # This is just for safety ther is usually one line here
            meas = re.findall(regex[k], meas)  # usually all spaces should be excluded but not sure if tab is removed as well
            for j, singlemeas in enumerate(meas):
                meas[j] = singlemeas.strip()
            parsed_obj.append(meas)

    # Now parse the actual data and build the tree dict structure needed
    data_lists = []  # is a list containing all entries from one measurement, while having the same order like the measurements object
    parsed_data = []
    data_dict = {}
    for dat in data:
        dat = dat.split()
        for j, singleentry in enumerate(dat):
            try:  # try to convert to number
                dat[j] = float(singleentry.strip())
            except:
                dat[j] = np.nan  # singleentry.strip()
        if dat:
            parsed_data.append(dat)

    for i, meas in enumerate(parsed_obj[0][:len(parsed_data[0])]): # Prevents wolfgangs header error
        data_lists.append([parsed_data[x][i] for x in range(len(parsed_data))])
        # Construct dict
        if meas not in data_dict:
            data_dict.update({str(meas): np.array(data_lists[i], dtype=np.float32)})
        else:
            filenum = 1
            while meas+"_{}".format(filenum) in data_dict:
                filenum += 1
            new_name = meas+"_{}".format(filenum)
            log.critical("Name {} already exists. Data array will be renamed to {}".format(meas, new_name))
            data_dict.update({new_name: np.array(data_lists[i], dtype=np.float32)})
            # Adapt the measurements name as well
            parsed_obj[0][i] = new_name

    return_dict = {"data": data_dict, "header": header, "measurements": parsed_obj[0][:len(parsed_data[0])], "units": parsed_obj[1][:len(parsed_data[0])]}
    return return_dict


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
           return obj.tolist()
        return json.JSONEncoder.default(self, obj)

def save_dict_as_json(data, dirr, base_name):
    json_dump = json.dumps(data, cls=NumpyEncoder)
    with open(os.path.join(dirr, base_name+".json"), 'w') as outfile:
        json.dump(json_dump, outfile)

    for key in data:
        with open(os.path.join(dirr, "{}.json".format(key)), 'w') as outfile:
            json_dump = json.dumps(data[key], cls=NumpyEncoder)
            json.dump(json_dump, outfile)

def save_dict_as_hdf5(data, dirr, base_name):
    df = convert_to_df(data)
    df["All"].to_hdf(os.path.join(dirr, base_name+".hdf5"), key='df', mode='w')
    for key in df.get("keys", []):
        data[key]["data"].to_hdf(os.path.join(dirr, "{}.hdf5".format(key)), key='df', mode='w')

def save_data(self, type, dirr, base_name="data"):
        """Saves the data in the specified type"""
        try:
            os.mkdir(os.path.join(os.path.normpath(dirr), "data"))
        except:
            pass

        if type == "json":
            # JSON serialize
            self.log.info("Saving JSON file...")
            save_dict_as_json(deepcopy(self.plotting_Object.data), os.path.join(os.path.normpath(dirr), "data"), base_name)
        if type == "hdf5":
            self.log.info("Saving HDF5 file...")
            save_dict_as_hdf5(deepcopy(self.plotting_Object.data), os.path.join(os.path.normpath(dirr), "data"), base_name)