# Here some special tools for the analysis are put

import numpy as np
import logging
from .utilities import load_yaml
import os, sys
import traceback
import re
import ast
import holoviews as hv
from holoviews import opts
import numpy as np
import pandas as pd
from bokeh.models import LinearAxis, Range1d
import subprocess

# from bokeh.io import export_svgs, export_png
# from bokeh.io import save
import json, yaml
from copy import deepcopy
from bokeh.models import HoverTool
import importlib.util

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
        ("T", "tera"): 1e12,
        ("G", "giga"): 1e9,
        ("M", "mega"): 1e6,
        ("k", "kilo"): 1e3,
        ("", ""): 1e0,
        ("m", "milli"): 1e-3,
        ("u", "micro"): 1e-6,
        ("n", "nano"): 1e-9,
        ("p", "pico"): 1e-12,
        ("f", "femto"): 1e-15,
        ("a", "atto"): 1e-18,
    }
    old_unit_key = None
    for file in data["keys"]:
        # Find current order of magnitude
        if not data[file]["units"]:
            log.warning(
                "No units defined for file {}. No conversion possible".format(file)
            )
            continue
        if dataType in data[file]["measurements"]:
            idx = data[file]["measurements"].index(dataType)
            if len(data[file]["units"][idx]) > 1:
                oldunit = data[file]["units"][idx][
                    0
                ]  # The first should be the correct magnitude
            else:
                oldunit = ""

            # find unit to convert to old and new
            old_unit_key = ("", "")
            for keys in engUnits.keys():
                if unit in keys:
                    to_convert = keys
                if oldunit in keys:
                    old_unit_key = keys

            # Calc difference between the units
            factor = engUnits[old_unit_key] / engUnits[to_convert]
            data[file]["data"][dataType] = data[file]["data"][dataType] * factor

            if len(data[file]["units"][idx]) > 1:
                # Todo: error in units if several conversions are made!!!!
                # Convert the units to the correct representation
                data[file]["units"][idx] = to_convert[0] + data[file]["units"][idx][:]
            else:
                data[file]["units"][idx] = to_convert[0] + data[file]["units"][idx]
        else:
            log.warning(
                "Conversion of units could not be done due to missing data! Data set: {}".format(
                    file
                )
            )
            return data

    # Convert the all df as well
    if old_unit_key:
        factor = engUnits[old_unit_key] / engUnits[to_convert]
        data["All"][dataType] = data["All"][dataType] * factor

    return data


def Simple2DPlot(
    data,
    configs,
    measurement_to_plot,
    xaxis_measurement,
    analysis_name,
    vdims="Name",
    keys=None,
    **kwargs
):
    """
    Generates a 2D Plot out of a pandas data frame for the DataVis
    :param data: the data structure for one measurement
    :param configs: the configs dict
    :param measurement_to_plot: y data name in the df
    :param xaxis_measurement: name of the meausurement which define the xaxsis, x data
    :param analysis_name: The name of the analysis, from the config
    :param keys: the keys from which data sets the plotting should be done
    :return: Holoviews plot object (only 2D plot)
    """

    # Generate a plot with all data plotted
    log.debug("Started plotting {} curve...".format(measurement_to_plot))
    conf = deepcopy(configs.get(analysis_name, {}))

    if (
        "Bars" in conf.get(measurement_to_plot, {}).get("PlotStyles", ["Curve"])
        or False
    ):
        conf[measurement_to_plot]["PlotStyles"].pop(
            conf[measurement_to_plot]["PlotStyles"].index("Bars")
        )
        plots = holoplot(
            measurement_to_plot,
            data,
            conf,
            kdims=[xaxis_measurement, measurement_to_plot],
            vdims=vdims,
            keys=keys,
            **kwargs
        )
        conf[measurement_to_plot]["PlotStyles"] = ["Bars"]
        bars = holoplot(
            measurement_to_plot,
            data,
            conf,
            kdims=[xaxis_measurement],
            vdims=measurement_to_plot,
            keys=keys,
            **kwargs
        )
        if plots:
            return bars + plots
        else:
            return bars
    else:
        return holoplot(
            measurement_to_plot,
            data,
            conf,
            kdims=[xaxis_measurement, measurement_to_plot],
            vdims=vdims,
            keys=keys,
            **kwargs
        )


def plot_all_measurements(
    data, config, xaxis_measurement, analysis_name, do_not_plot=(), keys=None, **kwargs
):
    return plot(
        data,
        config,
        xaxis_measurement,
        analysis_name,
        do_not_plot=do_not_plot,
        keys=keys,
        **kwargs
    )


def plot(
    data,
    config,
    xaxis_measurement,
    analysis_name,
    do_not_plot=(),
    plot_only=(),
    keys=None,
    **kwargs
):
    """
    Simply plots all available measurements from data frames against one xaxsis measurement.
    The data structure needs a entry for 'measurements' containing a list of all measurements
    :param data: The data structure
    :param config: The Configs dictionary
    :param xaxis_measurement: The measurement against all others are plotted
    :param analysis_name: The analysis name out of which the configs for the individual plots are extracted
    :param do_not_plot: List/tuple of plots which should not be plotted aka. columns in each dataset
    :param plot_only: List/tuple of plots which should only be plottet aka. columns in each dataset
    :param keys: the keys from which data sets the plotting should be done, aka the data file name
    :return: Holoviews Plot object
    """

    finalPlot = None
    for measurement in plot_only if plot_only else data["columns"]:
        if measurement not in do_not_plot:
            try:
                if finalPlot:
                    finalPlot += Simple2DPlot(
                        data,
                        config,
                        measurement,
                        xaxis_measurement,
                        analysis_name,
                        keys=keys,
                        **kwargs
                    )
                else:
                    finalPlot = Simple2DPlot(
                        data,
                        config,
                        measurement,
                        xaxis_measurement,
                        analysis_name,
                        keys=keys,
                        **kwargs
                    )
            except:
                pass

    return config_layout(finalPlot, **config.get(analysis_name, {}).get("Layout", {}))


def save_plot(name, subplot, save_dir, save_as=("default"), backend="bokeh"):
    """Saves a plot object"""
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    path = os.path.normpath(save_dir)

    # Generate the figure
    if "default" in save_as:
        stdformat = "html" if backend == "bokeh" else "png"
        save_dir = os.path.join(path, name)
        save_dir += "." + stdformat
        log.info("Saving default plot {} as {} to {}".format(name, stdformat, save_dir))
        hv.save(subplot, save_dir, backend=backend)
        return

    # Save the figure
    for save_format in save_as:
        if save_format in ["png", "html", "svg"]:
            try:
                log.info("Saving plot {} as {} to {}".format(name, save_format, path))
                if save_format.lower() == "html":
                    save_dir = os.path.join(path, "html")
                    if not os.path.exists(save_dir):
                        os.mkdir(save_dir)
                    hv.save(
                        subplot.opts(toolbar="above"),
                        os.path.join(save_dir, name) + ".html",
                        backend=backend,
                    )
                    subplot.opts(toolbar=None)

                elif save_format.lower() == "png":
                    save_dir = os.path.join(path, "png")
                    if not os.path.exists(save_dir):
                        os.mkdir(save_dir)
                    hv.save(
                        subplot, os.path.join(save_dir, name) + ".png", backend=backend
                    )
                elif save_format.lower() == "svg":
                    save_dir = os.path.join(path, "svg")
                    if not os.path.exists(save_dir):
                        os.mkdir(save_dir)
                    hv.save(
                        subplot, os.path.join(save_dir, name) + ".svg", backend=backend
                    )
                else:
                    log.debug(
                        "Saving format {} for plot save not recognised.".format(
                            save_format
                        )
                    )

            except Exception as err:
                log.warning(
                    "Exporting plot {} was not possible. Error: {}".format(name, err)
                )


def twiny(plot, element):
    # Setting the second y axis range name and range
    # Usage:
    # >>> curve_acc = hv.Scatter(options)(plot=dict(finalize_hooks=[twinx]))
    start, end = element.range(1)
    label = element.dimensions()[1].pprint_label
    plot.state.extra_y_ranges = {"foo": Range1d(start=start, end=end)}
    # Adding the second axis to the plot.
    linaxis = LinearAxis(axis_label=label, y_range_name="foo")
    plot.state.add_layout(linaxis, "right")


def reject_outliers(sr, iq_range=0.5):
    pcnt = (1. - iq_range) / 2.
    qlow, median, qhigh = sr.dropna().quantile([pcnt, 0.50, 1. - pcnt])
    iqr = qhigh - qlow
    return sr[(sr - median).abs() <= iqr]


def config_layout(PlotItem, **kwargs):
    """Configs the layout of the output"""
    for key, value in kwargs.items():
        try:
            getattr(PlotItem, key)(value)
        except AttributeError as err:
            log.warning(
                "Option '{}' for plot not possible with error: {}".format(key, err)
            )

    try:
        TOOLTIPS = [("File", "@Name"), ("index", "$index"), ("(x,y)", "($x, $y)")]
        hover = HoverTool(tooltips=TOOLTIPS)
        PlotItem.opts(
            opts.Curve(tools=[hover], toolbar="disable"),
            opts.Scatter(tools=[hover], toolbar="disable"),
            opts.Histogram(tools=[hover], toolbar="disable"),
            opts.Points(tools=[hover], toolbar="disable"),
            opts.BoxWhisker(tools=[hover], toolbar="disable"),
            opts.Bars(
                tools=[HoverTool(tooltips=[("Value of ID:", " $x"), ("Value:", "$y")])],
                toolbar="disable",
            ),
            opts.Violin(tools=[hover], toolbar="disable"),
        )
    except AttributeError as err:
        log.error(
            "Nonetype object encountered while configuring final plots layout. This should not happen! Error: {}".format(
                err
            )
        )
    except ValueError as err:
        if (
            "unexpected option 'tools'" in str(err).lower()
            or "unexpected option 'toolbar'" in str(err).lower()
        ):
            pass
        else:
            raise
    return PlotItem


def convert_to_df(convert, abs=False, keys="all"):
    """
    Converts a dict to panda dataframes for easy manipulation etc.
    Warning: All data arrays ust have the same length otherwise conversion not possible!

    :param data: Dictionary with data
    :param abs: if the data returned will be the absolute value of the data
    :param keys: use only this list of keys to generate df, use this key settings to convert only the needed fraction of data to dfs. Handy if you have data with different sizes which cannot be converted to a common df
                 fill in "all" to convert all keys to a dataframe
    :return: pandas data frame object
    """
    to_convert = deepcopy(convert)
    if not to_convert:
        raise Exception("Cannot convert empty data array to DataFrame!")
    # Convert all data to panda data frames
    index = list(to_convert.keys())
    precol = list(to_convert[index[0]]["data"].keys())
    columns = []

    if isinstance(keys, list) or isinstance(keys, tuple):
        for key in keys:
            if key in precol:
                columns.append(key)
        if not columns:
            raise Exception(
                "No passed keys: {} matched the possible columns of the passed data: {}. "
                "DataFrame generation failed!".format(keys, precol)
            )
    elif keys == "all":
        columns = precol
    if not columns:
        raise Exception("DataFrame generation failed! No valid columns found!")

    return_dict = {
        "All": pd.DataFrame(columns=columns),
        "keys": index,
        "columns": columns,
    }
    for key, data in to_convert.items():
        return_dict[key] = data
        try:
            if abs:  # Build abs of data or not
                for meas, arr in data["data"].items():
                    if meas in columns:
                        try:
                            data["data"][meas] = np.abs(arr)
                        except:  # If the value is some non float or int etc
                            pass

            sub_set = {}
            for ind in columns:
                try:
                    sub_set[ind] = data["data"][ind]
                except:
                    log.warning(
                        "Key {} was not present, no data conversion".format(ind)
                    )
            sub_set["Name"] = [
                key for i in range(len(sub_set[list(sub_set.keys())[0]]))
            ]
            df = pd.DataFrame(data=sub_set)

            # Convert all datatypes that are not float or int to np.nan
            for meas in df.keys():
                if meas != "Name":
                    df[meas] = pd.to_numeric(df[meas], errors="coerce")


        except KeyError as err:
            log.error(
                "In order to convert the data to panda dataframe, the data structure needs to have a key:'data'"
            )
            raise err

        return_dict[key]["data"] = df  # DF for every single file
        return_dict["All"] = pd.concat(
            [return_dict["All"], df], sort=True
        )  # all files together

    return return_dict


def rename_columns(df, new_names):
    """Renames columns in a data frame. Needs the dataframe and a dict of the desired names"""
    df["All"] = df["All"].rename(columns=new_names)
    df["columns"] = list(df["All"].columns)

    for key in df["keys"]:
        df[key]["data"] = df[key]["data"].rename(columns=new_names)
        df[key]["measurements"] = list(df[key]["data"].columns)

    return df


def plainPlot(
    plotType, xdata, ydata, label="NOName", plotName=None, configs={}, **addConfigs
):
    """

    :param plotType: The type of plot you want (bars, Curve etc.)
    :param xdata: The xdata
    :param ydata: The ydata
    :param label: The Plot Label
    :param plotName: The Name of the pot config name
    :param Config: The Configs dict (PlotName must be a valid key!)
    :param Configs: The configs the plot should have, additionally
    :return: the plotObject
    """

    if hasattr(hv, plotType):
        log.debug("Generating plain plot {} of type {}".format(label, plotType))
        plot = getattr(hv, plotType)(list(zip(xdata, ydata)), label=label)

        # Update the plot specific options if need be
        plot = customize_plot(plot, plotName, configs, **addConfigs)
        plot = plot.relabel(label)
        return plot

    else:
        log.error("Holovies has no attribute with name: {}".format(plotType))


def holoplot(plotType, df_list, configs, kdims, vdims=None, keys=None, **addConfigs):
    """
    Simply plots an configs a plot
    :param plotType: The type of plot, e.g. 'IV'
    :param df_list: List of panda dataframes
    :param configs: the plot configuration dicts, only dicts with entries holoviews can decode, all other in kwargs
    :param kdims: key dimensions to plot aka xyz axis, the first two kdims must be the x and y data specifier!!!
    :param vdims: value dimension, aka, the depth or the name across to plot
    :param keys: the keys from which data sets the plotting should be done
    :param **kwargs: some additional kwargs which can be needed by the self written tools
    :return: Holoviews plot object
    """

    # Add the additional configs to the configs
    configs = configs.copy()
    finalPlot = None

    if len(kdims) < 2:
        log.debug(
            "Holoplots usually needs at least two kdims to work with! Plotting may fail"
        )
        ind = 0
    else:
        ind = 1

    # Loop over all types of plots which should be created
    for type in configs.get(plotType, {}).get("PlotStyles", ["Curve"]):
        plot = None
        # Loop over all data
        log.info("Generating plot {} in Style {}".format(plotType, type))
        if hasattr(hv, type):
            for key in keys if keys else df_list["keys"]:  # Loop over all files
                if kdims[ind] in df_list[key]["data"]:
                    log.debug("Generating plot {} for {}".format(key, plotType))
                    # get labels from the configs
                    legend_name = configs.get("Files_legend_aliases", {}).get(key, None)
                    legend_name = legend_name if legend_name else key
                    try:
                        xlabel, ylabel = get_axis_labels(df_list, key, kdims, vdims)
                    except Exception as err:
                        log.error(
                            "Could not generate x and y label for plot {}. Error: {}".format(
                                plotType, err
                            )
                        )
                        xlabel, ylabel = "X-Axis", "Y-Axis"
                    if plot:
                        plot *= getattr(hv, type)(
                            df_list[key]["data"],
                            kdims=kdims,
                            vdims=vdims,
                            label=legend_name,
                            group=type,
                        )
                    else:
                        plot = getattr(hv, type)(
                            df_list[key]["data"],
                            kdims=kdims,
                            vdims=vdims,
                            label=legend_name,
                            group=type,
                        )
                    plot.opts(xlabel=xlabel, ylabel=ylabel)
                else:
                    log.warning(
                        "The data key: {} is not present in dataset {}. Skipping this particular plot.".format(
                            kdims[1], key
                        )
                    )
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


def get_axis_labels(df_list, key, kdims, vdims):
    """Generates the axis labels"""
    try:
        if df_list[key]["units"][df_list[key]["measurements"].index(kdims[1])]:
            ylabel = "{} ({})".format(
                kdims[1],
                df_list[key]["units"][df_list[key]["measurements"].index(kdims[1])],
            )
        else:
            ylabel = "{}".format(kdims[1])
    except:
        try:
            if df_list[key]["units"][df_list[key]["measurements"].index(vdims)]:
                ylabel = "{} ({})".format(
                    vdims,
                    df_list[key]["units"][df_list[key]["measurements"].index(vdims)],
                )
            else:
                ylabel = "{}".format(vdims)
        except:
            ylabel = "{}".format(kdims[1])

    try:
        if df_list[key]["units"][df_list[key]["measurements"].index(kdims[0])]:
            xlabel = "{} ({})".format(
                kdims[0],
                df_list[key]["units"][df_list[key]["measurements"].index(kdims[0])],
            )
        else:
            xlabel = "{}".format(kdims[0])
    except:
        xlabel = "{}".format(kdims[0])

    return xlabel, ylabel


def relabelPlot(plot, label, group=None):
    return plot.relabel(label, **{"group": group} if group else {})


def applyPlotOptions(plot, optionsdict):
    """Applies user defined options directly to the plot without changing previous options"""
    # Now convert the non converted values in the dict
    options = ast_evaluate_dict_values(optionsdict)
    return plot.opts(options)


def customize_plot(plot, plotName, configs, **addConfigs):
    """
    This function customizes the Plot like axis etc.
    :param plot: The holoviews plot object
    :param plotName: The name of the Plot
    :param configs: The Configs specific for this analysis.
    :return: configured plot object
    """

    # Look if a PlotLabel is in the addConfigs
    if "PlotLabel" in addConfigs:
        newlabel = addConfigs.pop("PlotLabel")
        plotName = newlabel
    else:
        newlabel = None

    # Get options
    log.debug(
        "Configuring plot with holoviews parameters for plot {}...".format(plotName)
    )
    gen_opts = configs.get("General", {})
    specific_opts = configs.get(plotName, {}).get("PlotOptions", {})
    options = {}
    options.update(gen_opts)
    options.update(specific_opts)
    options.update(addConfigs)

    # Now convert the non converted values in the dict
    options = ast_evaluate_dict_values(options)

    try:
        if not newlabel:
            label = configs.get(plotName, {}).get("PlotLabel", "")
        else:
            label = newlabel
        plot = plot.relabel(label).opts(**options)
    except AttributeError as err:
        log.error(
            "Relabeling plot {} was not possible! Error: {}".format(
                configs.get(plotName, {}).get("PlotLabel", ""), err
            )
        )
    except ValueError as err:
        log.warning("Value error occured during plot customization. Trying to apply option on per-subplot-level...")
        try:
            for path in plot.keys():
                subplot = plot
                for subpath in path:
                    subplot = getattr(subplot, subpath)
                # Check if non valid options for single plots are inside, remove them and try applying them later
                opts = {}
                valid_opts = deepcopy(options)
                for forbidden_opt in ["legend_position", "show_legend"]:
                    if forbidden_opt in options:
                        opts[forbidden_opt] = valid_opts.pop(forbidden_opt)
                subplot.opts(**valid_opts)
            plot = plot.relabel(label)
            try:
                plot.opts(**opts)
            except Exception as err:
                log.error("Invalid option occured during plot custimization on sub-plot level. I could not resolve it. I will ignore this option. Err: {}".format(err))

        except Exception as err:
            log.error(
                "Configuring plot {} was not possible! Error: {}".format(
                    configs.get(plotName, {}).get("PlotLabel", ""), err
                )
            )
    return plot


def ast_evaluate_dict_values(edict):
    """Ast evaluates dict entries and returns the evaluated dict."""
    returndict = {}
    for key, value in edict.items():
        if isinstance(value, dict):
            value = ast_evaluate_dict_values(value)
        if isinstance(value, str):  # Only evaluate str values all other must be correct
            try:
                value = eval(value)
            except Exception as err:
                log.debug(
                    "Could not interpret '{}' in key '{}' as a valid object. Stays as is! Error: {}".format(
                        value, key, err
                    )
                )

        returndict[key] = value
    return returndict


def read_in_files(filepathes, configs):
    """
    This function is to streamline the import of data
    :param filepathes: A list of files
    :param configs: the configs file content
    :return: data dicts
    """
    filetype = configs.get("Filetype", None)
    ascii_specs = configs.get("ASCII_file_specs", None)
    csv_specs = configs.get("CSV_file_specs", None)
    custom_specs = configs.get("Custom_specs", None)

    if filetype:
        if filetype.upper() == "ASCII":
            if ascii_specs:
                return read_in_ASCII_measurement_files(filepathes, ascii_specs)
            else:
                log.error(
                    "ASCII file type files must be given with specifications how to interpret data."
                )
        elif filetype.upper() == "JSON":
            return read_in_JSON_measurement_files(filepathes)
        elif filetype.upper() == "CSV":
            return read_in_CSV_measurement_files(filepathes, csv_specs)
        elif filetype.upper() == "CUSTOM":
            if custom_specs:
                data_raw = read_in_CUSTOM_measurement_files(filepathes, custom_specs)
                if data_raw and isinstance(data_raw, dict):
                    # Add the necessary data structure
                    final_data = {}
                    for key, value in data_raw.items():
                        try:
                            if isinstance(value, dict):
                                processed_data = {"analysed": False, "plots": False}
                                processed_data["data"] = value["data"]
                                if "measurements" not in value:
                                    processed_data["measurements"] = list(
                                        value["data"].keys()
                                    )
                                else:
                                    processed_data["measurements"] = value[
                                        "measurements"
                                    ]
                                if "units" not in value:
                                    processed_data["units"] = [
                                        "arb. units"
                                        for i in processed_data["measurements"]
                                    ]
                                else:
                                    processed_data["units"] = value["units"]
                                if "header" not in value:
                                    processed_data["header"] = ""
                                else:
                                    processed_data["header"] = value["header"]
                                if "additional" in value:
                                    processed_data["additional"] = value["additional"]
                                final_data[key] = processed_data
                            else:
                                log.error(
                                    "Data format for custom data array {} is not dict. Discarding data.".format(
                                        key
                                    )
                                )
                        except Exception as err:
                            log.error(
                                "An error happened during parsind data from CUSTOM importer output. Most likely the outpot did not had the correct form. Error: {}".format(
                                    err
                                )
                            )
                    return final_data, []
                else:
                    log.error(
                        "Return data from CUSTOM file parsing did not yield valid data. Data must be a dictionary!"
                    )
                    return {}, []

            else:
                log.error(
                    "If you want to use custom file import you must specifiy a 'Custom_specs' section in "
                    "your configuration."
                )
                return {}

    data = {}
    load_order = []
    for file in filepathes:
        if os.path.exists(file):
            filename, file_extension = os.path.splitext(file)
            if file_extension.lower() == ".txt" or file_extension.lower == ".dat":
                if ascii_specs:
                    data_new, load = read_in_ASCII_measurement_files(
                        [file], ascii_specs
                    )
                    data.update(data_new)
                    load_order.append(load)
                else:
                    log.error(
                        "ASCII file type files must be given with specifications how to interpret data."
                    )
            elif (
                file_extension.lower() == ".json"
                or file_extension.lower == ".yml"
                or file_extension.lower == ".yaml"
            ):
                data_new, order = read_in_JSON_measurement_files([file])
                load_order.append(order)
                data.update(data_new)
                continue  # In order to prevent the next load order to be executed
            elif file_extension.lower() == ".csv":
                data_new, load = read_in_CSV_measurement_files([file], csv_specs)
                data.update(data_new)
            else:
                log.critical("File type could not be extracted from file {}, trying as ASCII input...".format(filename))
                if ascii_specs:
                    data_new, load = read_in_ASCII_measurement_files(
                        [file], ascii_specs
                    )
                    data.update(data_new)
                    load_order.append(load)
                else:
                    log.error(
                        "ASCII file type files must be given with specifications how to interpret data. No data import!"
                    )
            load_order.append(file)
        else:
            log.error("Path {} does not exists, skipping file!".format(file))
    return data, load_order


def read_in_CUSTOM_measurement_files(filepathes, configs):
    """
    Loads a custom module for file import, executes it and returns data
    :param filepathes: List of filepathes
    :param module: the module name
    :param name: the class/function name
    :param kwargs: additional kwargs the module needs
    :return: parsed data as dict
    """
    try:
        path = configs["path"]
        module = configs["module"]
        name = configs["name"]
        spec = importlib.util.spec_from_file_location(module, os.path.normpath(path))
        func = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(func)
        return getattr(func, name)(filepathes, **configs.get("parameters", {}))
    except ImportError as err:
        log.error("Could not load module for custom import with error: {}".format(err))
        return None
    except Exception as err:
        log.error(
            "An error happened while performing custom import: {}".format(
                traceback.format_exc()
            )
        )
        return None


def read_in_CSV_measurement_files(filepathes, configs=None):
    """This reads in csv files and converts the directly to a pandas data frame!!!"""
    all_data = {}
    load_order = []
    if not configs:
        configs = {}

    for file in filepathes:
        load_order.append(file)
        data_dict = {"analysed": False, "plots": False, "header": ""}
        data = pd.read_csv(file)
        data_dict["measurements"] = configs.get("measurements", list(data.columns))
        data_dict["units"] = configs.get("units", ["" for i in data_dict["measurements"]])
        data_dict["data"] = data
        all_data[os.path.basename(file).split(".")[0]] = data_dict

    return all_data, load_order


def read_in_JSON_measurement_files(filepathes):
    """This function reads in a QTC measurement file and return a dictionary with the data in the file"""
    all_data = {}
    load_order = []

    try:
        for files in filepathes:
            filename = os.path.basename(str(files)).split(".")[0]
            log.info("Try reading JSON file: {}".format(filename))

            data = load_yaml(os.path.normpath(files))
            # Add filename and rest of the dict important values

            if "data" in data:
                data.update({"analysed": False, "plots": False})
                # Convert all lists to np.ndarrays
                for key, dat in data["data"].items():
                    data["data"][key] = np.array(dat)
                all_data[filename] = data
                load_order.append(filename)

            else:  # This is true for DataVIS outputs wiht several files in one json file
                for filename, item in data.items():
                    item.update({"analysed": False, "plots": False})
                    # Convert all lists to np.ndarrays
                    for key, dat in item["data"].items():
                        item["data"][key] = np.array(dat)
                    all_data[filename] = item
                    load_order.append(filename)

        return all_data, load_order

    except Exception as e:
        log.warning(
            "Something went wrong while importing the file "
            + str(files)
            + " with error: "
            + str(e)
        )


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
        log.error(
            "Something went wrong while importing the file "
            + str(current_file)
            + " with error: "
            + str(e)
        )


def parse_file_data(filecontent, settings):
    """This function parses the ADCII file content to the needed data types"""
    filecontent = filecontent.split("\n")

    header = filecontent[: settings.get("header_lines", 0)]
    if "measurement_description" in settings:
        measurements = filecontent[
            settings["measurement_description"]
            - 1 : settings["measurement_description"]
        ]
    else:
        measurements = [""]
    if "units_line" in settings:
        units = filecontent[settings["units_line"] - 1 : settings["units_line"]]
    else:
        units = [""]
    data = filecontent[settings["data_start"] - 1 :]
    separator = settings.get("data_separator", None)
    preunits = settings.get("units", None)
    premeasurement_cols = settings.get("measurements", None)

    units_exp = r"{}".format(settings.get("units_regex", r"(#?)\w*\s?\W?(#|\w*)\W*\s*"))
    data_exp = r"{}".format(settings.get("measurement_regex", r"(#|\w+)\s?\W?\w*\W?"))

    regex = [re.compile(data_exp, re.MULTILINE), re.compile(units_exp)]

    # First parse the units and measurement types
    parsed_obj = [[], []]
    if (
        not preunits or not premeasurement_cols
    ):  # If you have defined both dont do that, otherwise make best effort
        log.info("Trying to extract measurements and units from file...")
        for k, data_to_split in enumerate((measurements, units)):
            for i, meas in enumerate(
                data_to_split
            ):  # This is just for safety there is usually one line here
                to_del_ind = []
                meas = re.findall(
                    regex[k], meas.strip()
                )  # usually all spaces should be excluded but not sure if tab is removed as well
                for j, singleitem in enumerate(meas):
                    if isinstance(singleitem, tuple):
                        found = False
                        for singlemeas in singleitem:
                            if singlemeas.strip():
                                meas[j] = singlemeas.strip()
                                found = True
                                break
                        if not found:
                            to_del_ind.append(j)

                    elif isinstance(singleitem, str):
                        if singleitem.strip():
                            meas[j] = singleitem.strip()
                        else:
                            to_del_ind.append(j)
                for j in reversed(to_del_ind):  # Delete empty or non valid ones
                    meas.pop(j)
                parsed_obj[k] = meas

    if premeasurement_cols:
        log.info("Using predefined columns...")
        parsed_obj[0] = deepcopy(premeasurement_cols)
    if preunits:
        log.info("Using predefined units...")
        parsed_obj[1] = deepcopy(preunits)

    if not parsed_obj[0] and not parsed_obj[1]:
        log.error("No measurements and units extracted. Plotting will fail!")

    # Now parse the actual data and build the tree dict structure needed
    data_lists = (
        []
    )  # is a list containing all entries from one measurement, while having the same order like the measurements object
    parsed_data = []
    data_dict = {}
    for dat in data:
        dat = dat.split(separator)
        dat = [ind.strip() for ind in dat]
        if len(dat):
            for j, singleentry in enumerate(dat):
                try:  # try to convert to number
                    dat[j] = float(singleentry)
                except:
                    dat[j] = np.nan  # singleentry.strip()

        if parsed_data:  # This prevents zero len error
            if dat:
                if len(dat) == len(
                    parsed_data[-1]
                ):  # This prevents empty line or malformed data entry line error
                    parsed_data.append(dat)
                else:
                    dat.extend([np.nan for i in range(len(parsed_data[-1]) - len(dat))])
                    parsed_data.append(dat)
            else:
                log.info("Data shape is not consistent. Droping data: {}".format(dat))
        else:
            parsed_data.append(dat)

    for i, meas in enumerate(
        parsed_obj[0][: len(parsed_data[0])]
    ):  # Prevents wolfgangs header error
        data_lists.append([parsed_data[x][i] for x in range(len(parsed_data))])
        # Construct dict
        if meas not in data_dict:
            data_dict.update({str(meas): np.array(data_lists[i], dtype=np.float64)})
        else:
            filenum = 1
            while meas + "_{}".format(filenum) in data_dict:
                filenum += 1
            new_name = meas + "_{}".format(filenum)
            log.critical(
                "Name {} already exists. Data array will be renamed to {}".format(
                    meas, new_name
                )
            )
            data_dict.update({new_name: np.array(data_lists[i], dtype=np.float64)})
            # Adapt the measurements name as well
            parsed_obj[0][i] = new_name

    log.critical(
        "Extracted measurements are: {} with len {}".format(
            parsed_obj[0], len(parsed_obj[0])
        )
    )
    log.critical(
        "Extracted units are: {} with len {}".format(parsed_obj[1], len(parsed_obj[1]))
    )
    if len(parsed_obj[0]) != len(parsed_obj[1]):
        log.warning(
            "Parsed measurement decription len is not equal to len of extracted units. Errors may rise! If this error persists please change units_regex and measurement_regex in the"
            " ASCII parameters to fit your data! Or define your own correctly."
        )
    return_dict = {
        "data": data_dict,
        "header": header,
        "measurements": parsed_obj[0],
        "units": parsed_obj[1],
    }
    return return_dict


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Series):
            return obj.tolist()
        if isinstance(obj, pd.DataFrame):
            return {i: obj[i].tolist() for i in obj.keys()}
        return json.JSONEncoder.default(self, obj)


def save_dict_as_json(data, dirr, base_name):
    json_dump = json.dumps(data, cls=CustomJSONEncoder)
    with open(os.path.join(dirr, base_name + ".json"), "w") as outfile:
        json.dump(json_dump, outfile)

    for key in data:
        with open(os.path.join(dirr, "{}.json".format(key)), "w") as outfile:
            json_dump = json.dumps(data[key], cls=CustomJSONEncoder)
            json.dump(json_dump, outfile)


def save_dict_as_hdf5(data, dirr, base_name):
    df = convert_to_df(data)
    df["All"].to_hdf(os.path.join(dirr, base_name + ".hdf5"), key="df", mode="w")
    for key in df.get("keys", []):
        data[key]["data"].to_hdf(
            os.path.join(dirr, "{}.hdf5".format(key)), key="df", mode="w"
        )


def save_dict_as_xml(data, filepath, name, xml_template_dict):
    """
    Writes out the data as xml file, from a xml template

    :param filepath: Filepath where to store the xml
    :param name: name of the file
    :param data_dict: The data to store in this file. It has to be the dict representation of the xml file
    :param xml_template_dict: The xml template dict
    :return:
    """
    for key, dat in data.items():
        if xml_template_dict:
            template = xml_template_dict
            header_dict = insert_values_from_header(template, dat["header"])
            header_dict = insert_values_from_external_scripts(template, header_dict)
            final_xml = convert_dict_to_xml(header_dict)
            final_xml_dict = insert_templates(dat, final_xml, template)
            final_xml_dict = change_file_specific_xml_header(final_xml_dict, template)

            for subkey, value in final_xml_dict.items():
                save_as_xml(
                    value,
                    os.path.join(os.path.normpath(filepath)),
                    "{}_{}".format(key, subkey),
                )
        else:
            log.error(
                "No xml template stated in settings. Please add 'xml_template' to your configs."
            )

def change_file_specific_xml_header(final_xml_dict, template):
    """Changes the file specific header for each file"""
    import xml.etree.ElementTree as ET

    def validate_node(parent, temdict):
        try:
            for key, value in temdict.items():
                if isinstance(value, dict):
                    newvalue = validate_node(parent.find(key), value)
                else:
                    newvalue = value

                if newvalue:
                    child = parent.find(key)
                    child.text = value
        except:
            log.error("Child {} could not be found in xmltree. Skipping.".format(key))
            return None



    for file_header, new_header in template["File_specific_header"].items():
        if file_header in final_xml_dict:
            validate_node(final_xml_dict[file_header], new_header)
    return final_xml_dict


def save_data(plotting_Object, types, dirr, base_name="data", to_call=None):
    """Saves the data in the specified type"""

    check_if_data_changed(
        plotting_Object, to_call=to_call
    )  # Check if data has changed during analysis
    for typ in types:
        if typ in ["json", "hdf5", "xml"]:
            try:
                os.mkdir(os.path.join(os.path.normpath(dirr), "data"))
            except:
                pass
        if typ == "json":
            # JSON serialize
            log.info("Saving JSON file...")
            save_dict_as_json(
                deepcopy(plotting_Object.data),
                os.path.join(os.path.normpath(dirr), "data"),
                base_name,
            )
        if typ == "hdf5":
            # HDF5 serialize
            log.info("Saving HDF5 file...")
            save_dict_as_hdf5(
                deepcopy(plotting_Object.data),
                os.path.join(os.path.normpath(dirr), "data"),
                base_name,
            )
        if typ == "xml":
            # XML serialize
            log.info("Saving xml file...")
            if "xml_template" in plotting_Object.config:
                xml_template_dict = plotting_Object.config["xml_template"]
            else:
                xml_template_dict = plotting_Object.config.get(
                    "xml_template_path", None
                )
                xml_template_dict = load_yaml(xml_template_dict)
            if xml_template_dict:
                try:

                    save_dict_as_xml(
                        deepcopy(plotting_Object.data),
                        os.path.join(os.path.normpath(dirr), "data"),
                        base_name,
                        xml_template_dict,
                    )
                except:
                    log.error("An error happened during xml save.", exc_info=True)
            else:
                log.error(
                    "Could not save data as xml since no 'xml_template_path' was stated in the configs"
                )


def text_box(
    text, xpos, ypos, boxsize, fontsize=30, fontcolor="black", bgcolor="white"
):
    """Generates a box with text in it"""
    hvtext = hv.Text(xpos, ypos, text).opts(fontsize=fontsize, color=fontcolor)
    box = hv.Polygons(hv.Box(xpos, ypos, boxsize).opts(color="black")).opts(
        color=bgcolor
    )
    return box * hvtext


def insert_templates(dat, xml_string, xml_config_file):
    """Inserts any template for data into the XML string and returns a XML string"""  #
    import xml.etree.ElementTree as ET

    template_re = re.compile(r"//(.*)//")  # Regex for the template
    root = ET.fromstring(xml_string)  # convert the xml string to a xmltree

    def validate_node(elem, path):
        """This just validates the node from a given path for easy access"""
        for child in elem.getchildren():
            if path[0] == child.tag:
                if len(path[1:]):  # If len is left, the full path is not yet resolved
                    validate_node(child, path[1:])
                else:
                    return child

    def generate_template_xml_elements(kdim, element_name, xml_node, template, data):
        """Genrerates a xml template entry"""
        xml_node.remove(
            xml_node.find(element_name)
        )  # So that the template entry is gone
        keyword_re = re.compile(r"<(.*)>")
        for i, value in enumerate(data["data"][kdim]):
            root = ET.SubElement(xml_node, element_name)
            for key, entry in template.items():
                data_key = keyword_re.findall(entry)
                if data_key:
                    try:
                        element = ET.SubElement(root, key)
                        element.text = str(
                            data["data"][entry.replace("<", "").replace(">", "")][i]
                        )
                    except IndexError:
                        log.warning(
                            "The Index {} seems to be missing in the data".format(
                                entry.replace("<", "").replace(">", "")
                            )
                        )
                        break
        pass

    def dict_template_insert_iter(diction, path):
        """Goes over all entries in the dict and inserts single values from the header"""
        final_tree = {}
        for key, item in diction.items():
            if isinstance(item, dict):
                path.append(key)
                final_tree.update(dict_template_insert_iter(item, path))
                path.pop()
            else:
                keyword = template_re.match(str(item))
                subtrees = {}  # Todo: only one template allowed here, fix
                if keyword:
                    path.append(key)
                    for kdim in xml_config_file[keyword.string.replace("/", "")]:
                        if (
                            kdim in dat["data"].keys()
                        ):  # Todo: this may fail, and I am using raw data here,
                            subtrees[kdim] = deepcopy(root)
                            node = validate_node(
                                subtrees[kdim], path[:-1]
                            )  # Since we dont want the actual entry, just where to put it
                            generate_template_xml_elements(
                                kdim,
                                path[-1],
                                node,
                                xml_config_file[keyword.string.replace("/", "")][kdim],
                                dat,
                            )
                    final_tree.update(subtrees)
                    path.pop()
                # return final_tree
        return final_tree

    xml_dicts = dict_template_insert_iter(xml_config_file["Template"], path=[])
    return xml_dicts


def insert_values_from_header(xml_config_file, header=""):
    """
    Converts data to a specific form, as a dict stated in the config parameter.
    The config file must have a key named 'template' in it must be the dict representation of the xml file.
    Subkeys with a value enclosed by <..> are keywords. The header of the file will be searched for such key words.
    If it finds the regular expression r'<EXPR>\W\s?(.*)'

    :param data: data structure
    :param xml_config_file: the configs on how to convert data to xml
    :param header: a header (str) with key values like "Operator: Batman", the function tries to extract the data for the xml from there
    :return: None
    """
    template = deepcopy(xml_config_file["Template"])
    keyword_re = re.compile(r"<(.*)>")

    def dict_value_insert_iter(diction):
        """Goes over all entries in the dict and inserts single values from the header"""
        for key, item in diction.items():
            if isinstance(item, dict):
                dict_value_insert_iter(item)
            else:
                keyword = keyword_re.match(str(item))
                if keyword:
                    for line in header:
                        newvalue = re.search(r"{}\W\s?(.*)".format(keyword[1]), line)
                        if newvalue:
                            diction[key] = str(newvalue[1]).strip()
                            break
                        else:
                            # pass
                            diction[key] = str(None)
                else:
                    diction[key] = str(None)

    # Insert the simple values from the header
    dict_value_insert_iter(template)
    # Insert the templates

    return template

def insert_values_from_external_scripts(xml_config_file, header_dict):
    """
    Inserts data for entries, witch need data from external scripts like a online run number query from the web

    :param config_file: the configs
    :param xml_config_file: the configs on how to convert data to xml
    :param header_dict: the header (dict) with key values like "Operator: Batman", the function tries to extract the data for the xml from there
    :return: None
    """
    template = deepcopy(xml_config_file["Template"])
    keyword_re = re.compile(r"\[(.*)\]")

    def dict_value_insert_iter(diction, values_dict):
        """Goes over all entries in the dict and inserts single values from the header"""
        for key, item in diction.items():
            if isinstance(item, dict):
                dict_value_insert_iter(item, values_dict[key])
            else:
                keyword = keyword_re.match(str(item))
                if keyword:
                    # Start the script in a try except clause
                    keyword = keyword[0].strip("]").strip("[")
                    if keyword in xml_config_file:
                        try:
                            proc = subprocess.run("python " + xml_config_file[keyword], capture_output=True)
                            answer = proc.stdout.decode()
                            if keyword+"_regex" in xml_config_file:
                                regex = r"{}".format(xml_config_file.get(keyword+"_regex", r".*"))
                                parse_re = re.compile(regex)
                                answer = parse_re.findall(str(answer))[0]
                                values_dict[key] = str(answer).strip()
                                break
                            else:
                                values_dict[key] = str(answer).strip()
                                break
                        except:
                            log.error("Could not insert value from external script handler! Entry Name: {}".format(keyword), exc_info=True)

    # Insert the simple values from the header
    dict_value_insert_iter(template, header_dict)
    # Insert the templates

    return header_dict

def convert_dict_to_xml(data_dict):
    """Converts a dictionary to a xml conform string"""
    from dicttoxml import dicttoxml

    return dicttoxml(data_dict, attr_type=False)


def check_if_data_changed(plotting_Object, to_call=None):
    """Checks if data has changed during a analysis and asks if and what you want data you want to save"""
    originals = {i: {"original": j} for i, j in plotting_Object.data.items()}
    for analysisout in plotting_Object.plotObjects:
        if "data" in analysisout:  # Check if new data is present, if not ignore
            data = {k: analysisout["data"][k] for k in analysisout["data"]["keys"]}
            try:
                for key, value in data.items():
                    if key not in originals:
                        originals[key] = {}
                    else:
                        originals[key].update({analysisout["Name"]: value})
            except KeyError:
                log.error(
                    "New data was found for potential save but no name for analysis could be found. Please add a 'Name' entry to you analysis return!",
                    exc_info=True,
                )

    for file in originals:
        if (
            "original" not in originals[file] and len(originals[file].keys()) == 1
        ):  # If new data is present not included in the original data, add it
            plotting_Object.data[file] = originals[file][
                list(originals[file].keys())[0]
            ]

        if (
            len(originals[file].keys()) > 1
        ):  # Check if more than the original data is present
            # Check if len is 2 and originals is present and override is enabled then override
            data_override = plotting_Object.config.get("override_data", None)
            # If a specific dataset was selected
            if isinstance(data_override, bool):
                if (
                    len(originals[file].keys()) == 2
                    and "original" in originals[file]
                    and data_override == True
                ):
                    originals[file].pop("original")
                    analys = list(originals[file].keys())[0]
                    log.warning(
                        "Overriding data was set to true, overrding loaded data with data changed by analysis {}"
                        " for file {}".format(analys, file)
                    )
                    change_data(plotting_Object, originals, file, analys)

                elif (
                    len(originals[file].keys()) == 2
                    and "original" in originals[file]
                    and data_override == False
                ):
                    # do nothing
                    pass

                else:
                    if not to_call:
                        log.error(
                            "Either more than one analysis changed the output data for file {}, or override of data was not permitted... Saving data aborted!".format(
                                file
                            )
                        )
                    else:
                        to_call(
                            file, originals
                        )  # Legacy since it was ported from a different part


def change_data(plotting_Object, newdata, file, tosave):
    """Changes the data which will be saved in the end"""
    log.info("Setting new data from anlysis {} for file {}.".format(tosave, file))
    plotting_Object.data[file] = newdata[file][tosave]


def save_as_xml(data_dict, filepath, name):
    from json import loads
    from dicttoxml import dicttoxml
    from xml.dom.minidom import parseString
    import xml.etree.ElementTree as ET

    """
    Writes out the data as xml file

    :param filepath: Filepath where to store the xml
    :param name: name of the file 
    :param data_dict: The data to store in this file. It has to be the dict representation of the xml file
    :return:
    """
    file = os.path.join(os.path.normpath(filepath), name.split(".")[0] + ".xml")
    file = os.path.join(os.getcwd(), file)
    log.info("Saving file {}.".format(file))
    if isinstance(data_dict, ET.Element):
        dom = parseString(ET.tostring(data_dict))
        with open(file, "w+") as fp:
            fp.write(dom.toprettyxml())

    elif isinstance(data_dict, dict):
        xml = dicttoxml(data_dict, attr_type=False)
        dom = parseString(xml)  # Pretty print style
        with open(file, "w+") as fp:
            fp.write(dom.toprettyxml())

    elif isinstance(data_dict, str):
        xml = dicttoxml(loads(data_dict), attr_type=False)
        dom = parseString(xml)  # Pretty print style
        with open(file, "wb") as fp:
            fp.write(dom.toprettyxml())
    else:
        log.error(
            "Could not save data as xml, the data type is not correct. Must be dict or json"
        )


def moving_average(array, N):
    """Returns a moving average of the given array with mean over N values.
    Warning resulting array will be (N-1) shorter!"""
    return np.convolve(array, np.ones(N), 'valid') / N
