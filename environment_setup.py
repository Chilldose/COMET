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

        if python_version[0] != 3:
            print(
                "Warning: Python version must be 3.7.x to work properly. Errors may rise!"
            )

        try:
            requirement_file = sys.argv[1]
        except:
            print(
                "You did not pass a conda environment file. Do you want to install the non conda environment? [Y/n]?"
            )
            x = input()
            if x.upper() == "Y" or x.upper() == "Yes":
                requirement_file = "requirements_pip.yml"
                # Install pip env
                os.system("pip install -r {}".format(requirement_file))
                sys.exit(0)
            else:
                print("Aborting...")
                sys.exit(0)

        # Install anaconda env
        cmd = "conda env create -f {}".format(requirement_file)
        os.system(cmd)
        sys.exit(0)


if __name__ == "__main__":
    env = environement_setup()
    env.install_env()
