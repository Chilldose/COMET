# UniDAQ

This software was developed by Dominic Blöch during his Phd Thesis at the HEPHY Vienna. It features a GUI implementation of a semiconductor Sensor test software.
With it it is possible to "plugin" measurements devices via config files. Furthermore, measurements schemes and GUI objects can also easily be plugged in.

## Getting Started

In order to run this program you need either Anaconda2 or Python3 and the NI-Visa drivers. For more information on versions see Chapter "What you need".

### Installation

With python up and running you can install the application using pip.

```bash
pip install git+https://github.com/chilldose/UniDAQ@0.10.0
```

this will automatically install all required dependencies for the program to run.
To install the required dependencies manually (for development) use `requirements.txt` file.

```bash
pip install -r requirements.txt
```

## Running The Program

If you installed the program using pip just run:

```bash
UniDAQ
```

If you run a development version locally, execute the `main` module (not the file):

```
python -m UniDAQ.main
```

## How to Use

There is a documentation and a section called "Tutorial", this will guide you through the process of how to use this software and it will give you even more additional information about the software. You can access the documentation via this [Link](https://chilldose.github.io/UniDAQ/) or if you look into the folder ~/docs/index.html.



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

* **Dominic Blöch** - *Initial work and Developer* - [Chilldose](https://github.com/Chilldose)
* **Bernhard Arnold** - *Developer* - [arnobaer](https://github.com/arnobaer)

Beta Tester:

* **Gabriel Szabo** - *Project Student*

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Thanks to my friends for their help
* The foodora pizza delivery guy with the long beard
