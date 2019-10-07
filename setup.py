from setuptools import setup, find_packages
import imp

with open("README.md") as f:
    readme = f.read()

with open("LICENSE.md") as f:
    license = f.read()

version = imp.load_source('COMET.main', 'COMET/__init__.py').__version__

setup(
    name="COMET",
    version=version,
    description="A framework for automated DAQ for semiconductor device testing",
    long_description=readme,
    author="Dominic Blöch",
    author_email="dominic.bloech@oeaw.ac.at",
    url="https://github.com/Chilldose/COMET",
    license=license,
    packages=find_packages(),
    install_requires=[
        'llvmlite',
        'numba',
        'numpy',
        'PyQt5',
        'PyQt5-sip',
        'pyqtgraph',
        'PyVISA',
        'PyVISA-py',
        'PyVISA-sim',
        'PyYAML',
        'scipy',
    ],
    entry_points={
        'gui_scripts': [
            'COMET = COMET.main:main'
        ]
    },
    package_data={
        "COMET": [
            "config/*.json",
            "config/default/*.yml",
            "config/device_lib/*.yml",
            "config/Pad_files/*/*.txt",
            "QT_Designer_UI/*.ui",
            "images/*"
        ]
    }
)
