Data Visualization and Analysis
===============================

The Data Visualization and Analysis tab is an easy way to plot/analyse all kind of data. It can cope with ASCII, JSON and HDF5
files. The core GUI element looks like

.. image:: ../pictures/VIS.png
   :alt: Flowchart_main
   :class: floatingflask

The option **Data Files** lets you select the data files to be plotted together. Therefore you need a **Analysis Template**
which has all information stored for analysing and plotting the selected data. The **save to** option lets you define a
directory to store your data/plots.

To actually see something one has to hit the **Render** button, which initiates the plotting/analysis. And with the save
as button and the corresponding combo box you can choose to save the data, as well as who the data is stored.

.. important:: The analysis script is actually a stand alone software which can also be found on my github page. So if you are interested in developing your own plotting plugin, please see the corresponding docs of the plotting scripts.

After rendering you can choose which generated plot you want to display in the options **Plots**.
If you are not content with the plotting results, lets say the y-limits are not correct the plotting option for each
particular plot will be displayed. You can either select one and manipulate it there or, you can add new ones as well in the
line edit below. By pressing the **Apply** button the software reconfigs the plot and displays it to you.

.. caution:: If you pass a critical parameter which is somehow malformed in its value. You can damage the current plot object to a degree it is no longer plottable. In this case you have to re-render all plots. By doing so you loose all previous changes to the plots!

For the basic structure and usage of the plotting lib please see the ReadMe for the plotting lib at `Plotting Scripts doc <https://github.com/Chilldose/PlotScripts>`_