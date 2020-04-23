# PlotScripts
 These scripts are for simple plotting of data. It uses the holoviews plotting libraries for plotting

 # How to use
 First you need to install a Anaconda python 3.x version on your computer. After doing that you can install the conda envrionement by.

 ```python
conda env create -f requirements_<yourSystem>.yml
```

Next step is to activate the new build environement:


```
conda activate PlotScripts
```

Now it should be possible to run the scripts. This you can do by:

```python
python myplot.py --config <pathtoConfigfile>
```

This should initiate the plotting script and when finished, should reward you with a nice html plot.

There are several possible args you can pass,

| Arg                                | Type          | mandatory  | description                                                       |
| ---------------------------------- |:-------------:| ----------:| ----------------------------------------------------------------- |
| --config, --file, --c, --conf      | path/str      | yes        | The path to the config file                                       |
| --dont_show                             | bool          |   no       | If False the script will not show any html plots, default is True |
| --save, --s                        | bool          |    no      | Bool if you want to save the plots or not, default is False        |

# The Config file
In order to plot anything you need to have a Config file. These files are YAML styled files. Some examples can be found in the CONFIGS folder.
In principle such a file looks like this:

<pre>
---
  Files: # The files which are plotted together
    - MyMeasurementfilePath.txt

  Filetype: ASCII # What kind of type is my file, other options are CSV,JSON, customizations

  # If CUSTOM was choosen in 'Filetype', then you must define this custom specs section to tell where to find the file etc
  Custom_specs:
    path: <path_to_your_python_file> # The path to your python file where the importer is
    module: foo # The module name
    name: bar # The function name inside you want to load
    parameters: # Additional parameters your importer needs. Do not use if you dont need ones
      param1: 1
      param2: "Hello"

  Measurement_aliases:
    Your_column_name: the_alias
    Your_column_name2: the_alias2

  Output: myplot #Output folder path for my plots
  backend: bokeh # Choose the backend for the plotting Warning: Output may change with different backends.

  Save_as: # save the plots in different data formats, if more than one is specified all of them will be plotted
    - html
    - png
    - svg

  Analysis:
    - myAnalysisPlugin # The analysis Plugin over which the data will be run. These plugins must be located in the foler "analysis_scripts"

  Poolsize: 4 # Maximum pool size of simultaneous analysis scripts

  # Optional Parameters
  ASCII_file_specs: # The specifications for the ascii file type measurements files
    header_lines: 8
    measurement_description: 9
    units_line: 9
    data_start: 10

  # Options for the different Analyses scripts
  # These options are entirely up to you and what you need in your analysis
  myAnalysisPlugin:  This must match at least one of your measurement analysis plugins
      General: # Options common to all plots
          fontsize: {'title': 28, 'labels': 24, 'xticks': 24, 'yticks': 24, 'legend': 11}
          responsive: False
          width: 1200
          height: 700
          shared_axes: False
      Layout: # these must the the names of the methods understood by holoviews!!! and a valid parameters
          cols: 2 # How many columns there are in the final output plot

      DoSpecialPlots: # Whether or not to do the SpecialPlot, it may not succeed if not at least one measurement has this special plot stated
          - BoxWhisker
          - Violin
          - concatHistogram
          - Histogram

      # Options for SpecialPlots, the suffix must always be "Options"
      BoxWhiskerOptions:
          shared_axes: False
          box_alpha: 0.3
          width: 1200
          height: 900

      # Measurements
      MyFirstMeasurement: # The name of a measurement, as stated in the measurement file
          PlotLabel: Cool Label for my Plot
          PlotStyles: # How to Plot the raw data, all holoviews plots are supported, if you pass the correct PlotOptions.
            - Scatter
          UnitConversion: nano # The values for this measurement will be converted to this order of magnitude
          AdditionalPlots: # Which AdditionalPlots should be made.
              - BoxWhisker
          PlotOptions: # These options will directly be passed to the renderer, make sure they are valid. Look into holoviews, what options are supported
              logy: True
              logx: False
              invert_xaxis: False
              invert_yaxis: false
              #ylim: !!python/tuple [0, 10e-6]
              #xlim: !!python/tuple [0, 1000]
              legend_position: "bottom_right"
              #aspect: equal
              padding: !!python/tuple [0, 0.1]
              show_grid: True
              gridstyle:
                  grid_line_color: black
                  grid_line_width: 1.5
                  minor_xgrid_line_color: lightgray
                  minor_ygrid_line_color: lightgray
                  xgrid_line_dash: [4, 4]
                  ygrid_line_dash: [10, 4]
              #xlabel: voltage [V]
              #ylabel: current [A]
              shared_axes: False # If the axes should be shared with other plots, usually it is False
              xformatter: "%.0f"
              yformatter: "%.0f"
          ToolsOptions: # These options are for the PlotScripts tool box, or for the self written customizations
              yaxisENG: True # If you want to plot the y axis in engineering representation
</pre>

# Custom importer

If the given ASCII, JSON or CSV importer does not fit your needs you can write your own importer to import your data.
For that you have to specify the Filetype entry in the configs as 'CUSTOM' and define a 'Custom_specs' section as
seen in the example config.
Inside your python script a function named after the entry name in the Custom_specs section must be there.
This function gets 1 positional argument which is a list of filepathes to the choosen files. And all parameters as kwargs
specified in the 'parameters' entry in the Custom_specs section. If you do not need any extra parameters you can delete the parameters
entry in your config.

After parsing your data, the framework wants as a return a dict. The top level keys must be a kind of representation of your files (I use the filename).
The values to this keys are again dicts with keys beeing the columns/data sets inside like voltage, capacitance etc. As values it can be any iterable object. But I would recommend a list or a numpy array.  

# Plotting backend
PlotScripts is build on holoviews, and can plot with different plotting backends. The standard backend is bokeh. But you can choose another backend if you want with the parameter "backend". The options are bokeh, matplotlib and plotly.

Depending on the capabilities of the plotting backend, some plotting options may not be present in all backends. Therefore, the output may change!

The automatic preview will always be done via the bokeh backend. If you want to suppress this you have to pass the argument --dont_show.

# The measurements files
If you have json or YAML files you do not need special treatment here, just state it correctly in the config file.

If you have ASCII styled files you need to include the parameters

<pre>
ASCII_file_specs: # The specifications for the ascii file type measurements files
    header_lines: 18
    measurement_description: 20
    units_line: 21
    data_start: 22
</pre>

in you config file. The sub-parameters:

+ header_lines defines the length of the header in lines.
+ measurement_description the line with the name of the measurements
+ units_line the line where the units a described (can be the same line as measurement_description) the only thing this line need to have is something like curr [A], curr[A] or something like this, so the cript can find the units
+ data_start is the starting line of the data, which can be separated by tabs, whitespace or commas

If you follow this rules the script should be able to interpret your data.

## Optional parameters:
Further customization can be done via the optional parameters:

<pre>
separator: ";"
measurement_regex: ""
units_regex: ""
measurements:
    - voltage
    - current
units:
    - V
    - A
</pre>

+ separator: Define your own data separator if the data is not separated by a whitespace character
+ measurement_regex: If the build in measurement regex, does not yield the correct measurements, here you can define your own regex for that
+ units_regex: If the build in units regex, does not yield the correct measurements, here you can define your own regex for that
+ measurements: Define a list of measurement names, which describe your data (you can use this if the regex totally fails or if you do not have such a header.)
+ units: Define a list of units, which describe your data (you can use this if the regex totally fails or if you do not have such a header.)

Warning: Since '\\' is an escape character in python you have to escape this character by typing '\\\\' instead of one. Otherwise the regex will fail.  

A readable ASCII file (with the above config) would be:

<pre>

# Measurement file:
 # Project: HPK 6 inch 2018
 # Sensor Type: 2S
 # ID: VPX28442_11_2S
 # Operator: Dominic
 # Date: Wed Feb 27 08:48:27 2019


# implant_width: 22
# implant_length: 0
# metal_width: 32
# Campaign: Hamamatsu 6inch 2S
# Creator: Dominic Bloech 03.12.2018
# type: p-type
# pitch: 90
# metal_length: 49504
# thickness: 240


Pad                     Istrip                  Rpoly                   Idark                   Cac            
#                       current[A]              res[Ohm]                current[A]              cap[F]
1.0                     --                      --                      --                      --               
2.0                     -1.66724566667e-10      1895982.8106            -2.31596666667e-07      1.48568333333e-10     
3.0                     -1.599834e-10           1889915.74685           -2.30320333333e-07      1.48593666667e-10                
4.0                     -1.48145666667e-10      1892659.50326           -2.29964666667e-07      1.48617666667e-10         



</pre>


# The measurement plugins
The measurement plugins located in the analysis_scripts folder need to be python classes.
Form the main they are getting passed the data, and the config dictionaries

1) The data dict:
This dictionary is containing all the data from the files with the key beeing the base name of the files from the config.
Inside each entry is again a dictionary with the keys:

+ data - a Dict with all measurements and each entry containing a ndarray with the data
+ header - a list of str containing the header from the file
+ measurements - a list of all measurements, in the order of the input file
+ units - a list containinf all units fot each measurement
+ analysed - a bool value (for your use)
+ plots - a bool value (for your use)

2) The configs dict:
This dictionary is a 1 to 1 representation of your config file


## The basic structure of analysis plugins
In principle you can do whatever you want from this point on, but I have written some cool tools for plotting which will help you create some cool plots in no time with little effort.
The structure I am plotting is as follows:

<pre>
class IVCV:

    def __init__(self, data, configs):

        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=True) # Converts the data to pandas dataframes, and the optional parameter "abs" will return only the abs value for each measurement.
        self.config = configs
        self.df = []
        self.basePlots = None
        self.PlotDict = {}

        # Convert the units to the desired ones
        for meas in self.measurements:
            unit = self.config["IVCV_QTC"].get(meas, {}).get("UnitConversion", None)
            if unit:
                self.data = convert_to_EngUnits(self.data, meas, unit)

        hv.renderer('bokeh')

    def run(self):
        """Runs the script"""

        # Plot all Measurements
        self.basePlots = plot_all_measurements(self.data, self.config, "voltage", "IVCV_QTC", do_not_plot=("voltage"))
        self.PlotDict["BasePlots"] = self.basePlots
        self.PlotDict["All"] = self.basePlots

        # Whiskers Plot
        self.WhiskerPlots = dospecialPlots(self.data, self.config, "IVCV_QTC", "BoxWhisker", self.measurements)
        if self.WhiskerPlots:
            self.PlotDict["Whiskers"] = self.WhiskerPlots
            self.PlotDict["All"] = self.PlotDict["All"] + self.WhiskerPlots # This is how you add plots together in holoviews

        # Reconfig the plots to be sure
        self.PlotDict["All"] = config_layout(self.PlotDict["All"], **self.config["IVCV_QTC"].get("Layout", {}))
        return self.PlotDict

</pre>**

As a return the framework wants a least a dictionary with the entry "All", in which all plots are combined, if this is not there, no plots will be shown and saving cannot be done.


# Tools and other things

The framework has lots of subroutines which can simplify your workflow. These are located
in the folders "forge". It tried to give every function a Docstring but sometimes I am lacy but you will figure out what it does.

+ The utilities script gives you some basic non plot specific functions, normally you will not need them
+ The tools script gives you tools how to plot or manipulate data
+ The specialPlots script includes all special plot scripts, like violin, Histogram etc. you can add some as well


The most important functions are:
+ forge.tools.plot_all_measurements - These function plots you all measurements
+ forge.tools.convert_to_EngUnits - Converts the df entries to the specified order of magnitude
+ forge.specialPlots.dospecialPlots - These function plots you all measurements, in the desired special plot style
