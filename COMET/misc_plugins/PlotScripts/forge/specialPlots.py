"""Here special plot scripts are defined, which can be accessed from the config"""
from forge.tools import (
    customize_plot,
    config_layout,
    relabelPlot,
    reject_outliers,
    text_box,
)
import holoviews as hv
from holoviews import opts
from holoviews.operation import histogram
import logging
import pandas as pd
import numpy as np
from scipy import stats


log = logging.getLogger(__name__)


def dospecialPlots(data, config, analysisType, plotType, measurements, **plotConfigs):
    """
    Can plot all plots from the specialPlots library and returns
    It looks in all data files and plots it, if specified in the config!
    Returns a Holoviews plot object configured with the standard configs
    It does not allow additional configs for the holoview

    :param data: Dictionary with the data frames
    :param config: The configs dict
    :param analysisType: The analysis type in which should be looked
    :param plotType: The type of plot as str
    :param plotConfigs: The parameters for the special plot, not the holoviews framework!!!
    :param measurements: A list of all possible measurements
    :return: Holoviews plot object with all plots
    """

    # Plot all Histograms
    Plots = None
    log.info("Plotting special plot: {}".format(plotType))
    for meas in measurements:  #
        if plotType in config[analysisType].get(meas, {}).get(
            "AdditionalPlots", ""
        ) and plotType in config[analysisType].get("DoSpecialPlots", []):
            if Plots:
                Plots += eval(
                    "{plotType}({dfs},{measurement},{configs}, {analysisType}, **{plotConfigs})".format(
                        plotType="{}".format(plotType),
                        dfs="data",
                        measurement="meas",
                        configs="config",
                        analysisType="analysisType",
                        plotConfigs="plotConfigs",
                    )
                )
            else:
                Plots = eval(
                    "{plotType}({dfs},{measurement},{configs}, {analysisType}, **{plotConfigs})".format(
                        plotType="{}".format(plotType),
                        dfs="data",
                        measurement="meas",
                        configs="config",
                        analysisType="analysisType",
                        plotConfigs="plotConfigs",
                    )
                )
    if Plots:
        try:
            Plots = config_layout(Plots, **config[analysisType].get("Layout", {}))
        except:
            pass
    else:
        log.warning(
            "No plots could be generated for {} Plot. No data had a flag for plotting this type of plot".format(
                plotType
            )
        )
    return Plots


def BoxWhisker(dfs, measurement, configs, analysisType, **addConfigs):
    """Plots a measurement from all df as boxwisker"""
    newConfigs = addConfigs
    log.info("Generating BoxWhisker Plot for {}".format(measurement))
    try:
        plot = hv.BoxWhisker(
            dfs["All"],
            kdims=["Name"],
            vdims=[measurement],
            label="BoxWhisker: {}".format(measurement),
            group="BoxWhisker: {}".format(measurement),
        )

        try:
            ylabel = "{} [{}]".format(
                measurement,
                dfs[dfs["keys"][0]]["units"][
                    dfs[dfs["keys"][0]]["measurements"].index(measurement)
                ],
            )
        except Exception as err:
            log.error(
                "Label could not be genereated for concatonated Histogram {}. Error: {}".format(
                    measurement, err
                )
            )
            ylabel = "X-Axis"
        plot.opts(
            box_alpha=0.3,
            xrotation=80,
            box_color="blue",
            height=500,
            show_legend=False,
            width=600,
            whisker_color="blue",
            ylabel=ylabel,
        )

        # Update the plot specific options if need be
        generalOptions = configs[analysisType].get("General", {})
        newConfigs.update(generalOptions.copy())
        data_options = (
            configs[analysisType]
            .get(measurement, {})
            .get("BoxWhisker", {})
            .get("PlotOptions", {})
        )
        newConfigs.update(
            configs[analysisType].get("{}Options".format("BoxWhisker"), {})
        )
        newConfigs.update(data_options)
        plot = customize_plot(plot, "", configs[analysisType], **newConfigs)

    except Exception as err:
        log.error(
            "Unexpected error happened during BoxWhisker plot generation {}. Error: {}".format(
                measurement, err
            )
        )
        return None

    return plot


def Violin(dfs, measurement, configs, analysisType, **addConfigs):
    """Plots a measurement from all df as boxwisker"""
    newConfigs = addConfigs
    log.info("Generating Violin Plot for {}".format(measurement))
    try:
        plot = hv.Violin(
            dfs["All"],
            kdims="Name",
            vdims=measurement,
            label="Violin: {}".format(measurement),
            group="Violin: {}".format(measurement),
        )
        # get labels from the configs
        # ylabel = "{} [{}]".format(measurement, dfs[dfs["keys"][0]]["units"][dfs[dfs["keys"][0]]["measurements"].index(measurement)])
        try:
            ylabel = "{} [{}]".format(
                measurement,
                dfs[dfs["keys"][0]]["units"][
                    dfs[dfs["keys"][0]]["measurements"].index(measurement)
                ],
            )
        except Exception as err:
            log.error(
                "Label could not be generated for violin plot {}. Error: {}".format(
                    measurement, err
                )
            )
            ylabel = "Y-Axis"
        plot.opts(
            box_alpha=0.3,
            xrotation=80,
            box_color="blue",
            height=500,
            show_legend=False,
            width=600,
            ylabel=ylabel,  # inner='quartiles'
        )

        # Update the plot specific options if need be
        generalOptions = configs[analysisType].get("General", {})
        newConfigs.update(generalOptions.copy())
        data_options = (
            configs[analysisType]
            .get(measurement, {})
            .get("Violin", {})
            .get("PlotOptions", {})
        )
        newConfigs.update(configs[analysisType].get("{}Options".format("Violin"), {}))
        newConfigs.update(data_options)
        plot = customize_plot(plot, "", configs[analysisType], **newConfigs)
    except Exception as err:
        log.error(
            "Unexpected error happened during violin plot generation {}. Error: {}".format(
                measurement, err
            )
        )
        return None

    return plot


def concatHistogram(
    dfs, measurement, configs, analysisType, bins=50, iqr=None, **addConfigs
):
    """Concatenates dataframes and generates a Histogram for all passed columns"""
    newConfigs = addConfigs

    # If auxConfigs in measuremnt config for bins and IQR replace them
    auxOptions = configs.get(analysisType, {}).get(measurement, {}).get("AuxOptions", {}).get("concatHistogram",{})
    if "bins" in auxOptions:
        bins = int(auxOptions["bins"])
    if "iqr" in auxOptions:
        iqr = float(auxOptions["iqr"])


    log.info("Generating concat histograms for measurements {}...".format(measurement))
    try:
        df = dfs["All"]
        # Sanatize data
        data = df[measurement].dropna()  # Drop all nan
        if iqr:
            log.info("Outliers correction with iqr: {}".format(iqr))
            data = reject_outliers(data, iqr)
        mean = np.round(np.mean(data), 2)
        rms = np.round(np.sqrt(np.mean(data ** 2)), 2)
        std = np.round(np.std(data), 2)
        median = np.round(np.median(data), 2)
        data = np.histogram(data, bins=bins)

        plt = hv.Histogram(
            data,
            label="Concatenated Histogram: {}".format(measurement),
            group="Concatenated Histogram: {}".format(measurement),
        )
        # plt = hv.Histogram(data, vdims=to_plot, group="Concatenated Histogram: {}".format(to_plot))

        try:
            xlabel = "{} ({})".format(
                measurement,
                dfs[dfs["keys"][0]]["units"][
                    dfs[dfs["keys"][0]]["measurements"].index(measurement)
                ],
            )
        except Exception as err:
            log.error(
                "Label could not be genereated for concatonated Histogram {}. Error: {}".format(
                    measurement, err
                )
            )
            xlabel = "X-Axis"

        plt.opts(xlabel=xlabel)
        # Update the plot specific options if need be
        generalOptions = configs[analysisType].get("General", {})
        newConfigs.update(generalOptions.copy())
        data_options = (
            configs[analysisType]
            .get(measurement, {})
            .get("Concatenated Histogram", {})
            .get("PlotOptions", {})
        )
        newConfigs.update(
            configs[analysisType].get("{}Options".format("Histogram"), {})
        )
        newConfigs.update(data_options)
        # addConfigs.update({"xlabel": measurement})
        plots = customize_plot(plt, "", configs[analysisType], **newConfigs)

        # Add text
        text = (
            "\nMean: {mean} \n"
            "Median: {median} \n"
            "RMS: {rms}\n"
            "std: {std}".format(mean=mean, median=median, rms=rms, std=std)
        )
        log.info(text)
        y = data[0].max()
        x = data[1][int(len(data[1]) * 0.9)]
        text = hv.Text(x, y, text).opts(fontsize=30)
        plots = plots * text

    except Exception as err:
        log.error(
            "Unexpected error happened during concatHist plot generation {}. Error: {}".format(
                measurement, err
            )
        )
        return None

    return plots


def Histogram(dfs, measurement, configs, analysisType, bins=50, iqr=None, commas=2, **addConfigs):
    """Generates a Points Plot with a corresponding Histogram"""
    newConfigs = addConfigs
    log.info("Generating histograms for measurement {}...".format(measurement))
    finalplots = None
    try:
        for key in dfs["keys"]:
            log.info(
                "Generating histograms for measurement {} for file {}...".format(
                    measurement, key
                )
            )
            # Sanatize data
            data = dfs[key]["data"][measurement].dropna()  # Drop all nan
            if iqr:
                log.info("Outliers correction with iqr: {}".format(iqr))
                data = reject_outliers(data, iqr)
            mean = np.round(np.mean(data), commas)
            rms = np.round(np.sqrt(np.mean(data ** 2)), commas)
            std = np.round(np.std(data), commas)
            median = np.round(np.median(data), commas)
            data = np.histogram(data, bins=bins)
            plt = hv.Histogram(
                data,
                label="Histogram: {}".format(measurement),
                group="Histogram: {}: {}".format(measurement, key),
            )

            try:
                xlabel = "{} ({})".format(
                    measurement,
                    dfs[dfs["keys"][0]]["units"][
                        dfs[dfs["keys"][0]]["measurements"].index(measurement)
                    ],
                )
            except Exception as err:
                log.error(
                    "Label could not be generated for Histogram {}. Error: {}".format(
                        measurement, err
                    )
                )
                xlabel = "X-Axis"

            plt.opts(xlabel=xlabel)
            # Update the plot specific options if need be
            generalOptions = configs[analysisType].get("General", {})
            newConfigs.update(generalOptions.copy())
            data_options = (
                configs[analysisType]
                .get(measurement, {})
                .get("Single Histogram", {})
                .get("PlotOptions", {})
            )
            newConfigs.update(
                configs[analysisType].get("{}Options".format("Histogram"), {})
            )
            newConfigs.update(data_options)
            plots = customize_plot(plt, "", configs[analysisType], **newConfigs)

            # Add text
            text = (
                "\nMean: {mean} \n"
                "Median: {median} \n"
                "RMS: {rms}\n"
                "std: {std}".format(mean=mean, median=median, rms=rms, std=std)
            )
            log.info(text)
            y = data[0].max()
            x = data[1][int(len(data[1]) * 0.9)]
            text = hv.Text(x, y, text).opts(fontsize=30)
            # text = text_box(text, x, y, boxsize= (100, 150))
            plots = plots * text

            if finalplots:
                finalplots += plots
            else:
                finalplots = plots
    except Exception as err:
        log.error(
            "Unexpected error happened during Hist plot generation {}. Error: {}".format(
                measurement, err
            )
        )
        return None

    return finalplots


def SimplifiedBarChart(
    dfs, measurement, configs, analysisType, xaxis, bins=50, **addConfigs
):
    """Generates a simplified bar chart with a simplified x axis, can be handy if you have lots of points """
    newConfigs = addConfigs
    log.info("Generating BarChart for measurement {}...".format(measurement))
    finalplots = None
    try:
        for key in dfs["keys"]:
            log.info(
                "Generating histograms for measurement {} for file {}...".format(
                    measurement, key
                )
            )
            # Sanatize data
            data = dfs[key]["data"][[measurement, xaxis]].dropna()  # Drop all nan
            invertedaxis = data.reset_index().set_index(measurement)
            data = np.histogram(data[measurement], bins=data[xaxis])

            plt = hv.Histogram(
                data, label="BarChart: {}".format(measurement), group="{}".format(key)
            )

            try:
                xlabel = "{} [{}]".format(
                    measurement,
                    dfs[dfs["keys"][0]]["units"][
                        dfs[dfs["keys"][0]]["measurements"].index(measurement)
                    ],
                )
            except Exception as err:
                log.error(
                    "Label could not be generated for Histogram {}. Error: {}".format(
                        measurement, err
                    )
                )
                xlabel = "X-Axis"

            plt.opts(xlabel=xlabel)
            # Update the plot specific options if need be
            generalOptions = configs[analysisType].get("General", {})
            newConfigs.update(generalOptions.copy())
            data_options = (
                configs[analysisType]
                .get(measurement, {})
                .get("Single Histogram", {})
                .get("PlotOptions", {})
            )
            newConfigs.update(
                configs[analysisType].get("{}Options".format("Histogram"), {})
            )
            newConfigs.update(data_options)
            plots = customize_plot(plt, "", configs[analysisType], **newConfigs)

            if finalplots:
                finalplots += plots
            else:
                finalplots = plots
    except Exception as err:
        log.error(
            "Unexpected error happened during Hist plot generation {}. Error: {}".format(
                measurement, err
            )
        )
        return None

    return finalplots
