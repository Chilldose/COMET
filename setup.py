# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

with open("LICENSE.md") as f:
    license = f.read()

setup(
    name="UniDAQ",
    version="0.9.2",
    description="A framework for automated DAQ for semiconductor device testing",
    long_description=readme,
    author="Dominic Blöch",
    author_email="rhtbapat@gmail.com",
    url="https://github.com/Chilldose/UniDAQ",
    license=license,
    packages=find_packages(),
    scripts=["main.py"],
    package_data={
        "UniDAQ": ["QT_Designer_UI/*.ui", "images/*"]
    }
)
