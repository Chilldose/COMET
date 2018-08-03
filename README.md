# UniDAQ

This software was developed by Dominic Blöch during his Phd Thesis at the HEPHY Vienna. It features a GUI implemenentation of a semiconductor Sensor testsoftware.
With it it is possible to "plugin" measurements devices via config files. Furthermore, measurements schemes and GUI objects can also easaly be pluged in.

## Getting Started

In order to run this program you need a Python Anaconda distribution and the NI-Visa drivers. For more information on versions see Chapter "What you need".

### Setting Up The Environement

With python up and running you can run the the "environement_setup.py" file by.

```
python environement_setup.py
```

this will (when Anaconda is installed) automatically install all required modules for the program to run. If you don't have Anaconda installed and don't want to use it, you can look in the "requirements.yml" file to see what dependencies the program needs.

## Running The Program

Now it should be possible to run the program by:

```
python UniDAQ.py
```

If you do not have Anaconda installed, start the program via 

```
python main.py
```


## How to Use

Since I have not got time to write the how to, this has to stay empty for now. But you can try to figure it out yourself. Its not that hard, since its has a GUI.



## What you need

### Python

You need python 2.7 64 bit distribution. (32 bit works as well but unstable)
I recommended to use this program with a [Anaconda](https://www.anaconda.com/download/) python distribution, it will work with a normal version too, but I have not tested it.

### NI-Visa
You need [NI-Visa 17.0](http://www.ni.com/download/ni-visa-17.0/6646/en/) drivers or higher, for them to work. If you have installed LabView it is usually already installed on your pc.

The program is known to be running on Windows, Linux (Centos7) and Mac.


## Built With

* [PyVisa](https://github.com/pyvisa/pyvisa) - For the communication with devices
* [PyQt](https://github.com/pyqt) - For the GUI
* [Pyqtgraph](https://github.com/pyqtgraph/) - For the plots



## Versioning

I use the [SemVer](http://semver.org/) for versioning.


## Authors

* **Dominic Blöch** - *Initial work* - [Chilldose](https://github.com/Chilldose)

Beta Tester:

* **Gabriel Szabo** - *Project Student*

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Thanks to my friends for their help 
* The foodora pizza delivery guy with the long beard
