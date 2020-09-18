"""Appends the file pathes of all files in the --data_directory path argument to the given --config_path
configuration file."""

import argparse, yaml, os

parser = argparse.ArgumentParser(description='Adds every path in given folder to given config file')
parser.add_argument("-c","--config_path", type=str, help="Example: \"C:\\Users\\flohu\\OneDrive\\Documents\\GitHub\\PlotScripts\\CONFIGS\\PQC_analyses.yml\"")
parser.add_argument("-d","--data_directory", type=str, help="Example: \"C:\\Users\\flohu\\OneDrive\\Documents\\Uni\Bachelor\\BachelorArbeit\\Daten\Van-der-Pauw_Probecard\"")
args = parser.parse_args()
def absoluteFilePaths(directory):
    for dirpath,_,filenames in os.walk(directory):
        return [os.path.join(dirpath, f) for f in filenames]

def write_to_yaml(config_path, data_directory):
    data_paths = absoluteFilePaths(data_directory)
    with open(config_path, 'r') as file:
        dic = yaml.load(file, Loader=yaml.FullLoader)
        dic['Files'] = dic['Files'] + data_paths
    with open(config_path, 'w') as file:
        yaml.dump(dic, file, sort_keys=False)

if __name__=="__main__":
    write_to_yaml(args.config_path, args.data_directory)