# This functions just adds a conda enviroment for the software

import os
import sys

class environement_setup:

    def install_env(self):
        """This function checks the python version and what kind of python (anaconda or not)"""
        python_type = sys.version
        python_version = sys.version_info

        print("Version INFOS")
        print(python_type)
        print(python_version)

        try:
            cmd = "conda env create -f requirements.yml"
            os.system(cmd)
        except:
            print("No Anaconda installation found please install all modules listed in the requirements.yml via pip")

        if python_version[0] != 3:
            print("Warning: Python version must be 3.x to work properly")

if __name__ == "__main__":
    env = environement_setup()
    env.install_env()
