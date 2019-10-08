"""Here special plot scripts are defined, which can be accessed from the config"""
from forge.tools import customize_plot, config_layout, relabelPlot, reject_outliers
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
        if plotType in config[analysisType].get(meas, {}).get("AdditionalPlots", "") \
                and plotType in config[analysisType].get("DoSpecialPlots", []):
            if Plots:
                Plots += eval("{plotType}({dfs},{measurement},{configs}, {analysisType}, **{plotConfigs})".format(
                    plotType="{}".format(plotType),
                    dfs="data",
                    measurement="meas",
                    configs="config",
                    analysisType="analysisType",
                    plotConfigs="plotConfigs")
                )
            else:
                Plots = eval("{plotType}({dfs},{measurement},{configs}, {analysisType}, **{plotConfigs})".format(
                    plotType="{}".format(plotType),
                    dfs="data",
                    measurement="meas",
                    configs="config",
                    analysisType="analysisType",
                    plotConfigs="plotConfigs")
                )
    if Plots:
        try:
            Plots = config_layout(Plots, **config[analysisType].get("Layout", {}))
        except:
            pass
    else:
        log.warning(
            "No plots could be generated for {} Plot. No data had a flag for plotting this type of plot".format(
                plotType))
    return Plots

def BoxWhisker(dfs, measurement, configs, analysisType, **addConfigs):
    """Plots a measurement from all df as boxwisker"""
    log.info("Generating BoxWhisker Plot for {}".format(measurement))
    plot = hv.BoxWhisker(dfs["All"], kdims="Name", vdims=measurement, group="BoxWhisker: {}".format(measurement))
    # get labels from the configs
    ylabel = "{} [{}]".format(measurement, dfs[dfs["keys"][0]]["units"][dfs[dfs["keys"][0]]["measurements"].index(measurement)])
    plot.opts(box_alpha=0.3, xrotation= 80,
              box_color='blue', height=500,
              show_legend=False,
              width=600, whisker_color='blue', ylabel=ylabel
              )


    # Update the plot specific options if need be
    addConfigs.update(configs[analysisType].get("{}Options".format("BoxWhisker"), {}))
    plot = customize_plot(plot, "", configs[analysisType], **addConfigs)

    return plot

def Violin(dfs, measurement, configs, analysisType, **addConfigs):
    """Plots a measurement from all df as boxwisker"""
    log.info("Generating Violin Plot for {}".format(measurement))
    plot = hv.Violin(dfs["All"], kdims="Name", vdims=measurement, group="Violin: {}".format(measurement))
    # get labels from the configs
    ylabel = "{} [{}]".format(measurement, dfs[dfs["keys"][0]]["units"][dfs[dfs["keys"][0]]["measurements"].index(measurement)])
    plot.opts(box_alpha=0.3, xrotation= 80,
              box_color='blue', height=500,
              show_legend=False,
              width=600, ylabel=ylabel # inner='quartiles'
              )

    # Update the plot specific options if need be
    addConfigs.update(configs[analysisType].get("{}Options".format("Violin"), {}))
    plot = customize_plot(plot, "", configs[analysisType], **addConfigs)

    return plot


def concatHistogram(dfs, measurement, configs, analysisType,  bins=50, iqr=0.5, **addConfigs):
    """Concatenates dataframes and generates a Histogram for all passed columns"""

    log.info("Generating concat histograms for measurements {}...".format(measurement))
    df = dfs["All"]

    # Sanatize data
    data = df[measurement].dropna() # Drop all nan
    data = reject_outliers(data, iqr)
    data = np.histogram(data, bins=bins)

    plt = hv.Histogram(data, group="Concatenated Histogram: {}".format(measurement))
    #plt = hv.Histogram(data, vdims=to_plot, group="Concatenated Histogram: {}".format(to_plot))

    xlabel = "{} [{}]".format(measurement,
                              dfs[dfs["keys"][0]]["units"][dfs[dfs["keys"][0]]["measurements"].index(measurement)])
    plt.opts(xlabel=xlabel)
    # Update the plot specific options if need be
    addConfigs.update(configs[analysisType].get("{}Options".format("Histogram"), {}))
    #addConfigs.update({"xlabel": measurement})
    plots = customize_plot(plt, "", configs[analysisType], **addConfigs)

    return plots

def addHistogram(plotItem, dimensions="x"):
    """Generates a Points Plot with a corresponding Histogram
    #TODO:review, it may not work anymore"""
    plotList = plotItem.keys()

    hist = None
    for type, name in plotList:
        if type in ("Scatter", "Points", "Curve"):
            if hist:
                hist *= histogram(getattr(getattr(plotItem, type), name), dimension=dimensions)
            else:
                hist = histogram(getattr(getattr(plotItem, type), name), dimension=dimensions)
        else:
            log.warning("Histograms can only be added to plots of type: (Scatter, Points)")
    return (plotItem << hist.opts(show_legend=False)).opts(opts.Histogram(alpha=0.3, xticks=5))