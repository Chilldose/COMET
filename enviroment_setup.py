# This functions just adds a conda enviroment for the software

import os

cmd ="conda env create -f requirements.yml"
os.system(cmd)

# To remove enviroment
cmd = "conda remove --name UniDAQenv --all"