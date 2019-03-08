from setuptools import setup, find_packages
import imp

with open("README.md") as f:
    readme = f.read()

with open("LICENSE.md") as f:
    license = f.read()

version = imp.load_source('UniDAQ.main', 'UniDAQ/__init__.py').__version__

setup(
    name="UniDAQ",
    version=version,
    description="A framework for automated DAQ for semiconductor device testing",
    long_description=readme,
    author="Dominic Blöch",
    author_email="rhtbapat@gmail.com",
    url="https://github.com/Chilldose/UniDAQ",
    license=license,
    packages=find_packages(),
    entry_points={
        'gui_scripts': [
            'UniDAQ = UnIDAQ.main:main'
        ]
    },
    package_data={
        "UniDAQ": [
            "config/*.json",
            "config/default/*.yml",
            "config/device_lib/*.yml",
            "config/Pad_files/*/*.txt",
            "QT_Designer_UI/*.ui",
            "images/*"
        ]
    }
)
