"""__author__: Dallavalle Riccardo
__email__: dallavallericcardo@outlook.com
Create a custom importer which is able to manage different kind of file analysis.
Read the files and in the end return a dictionary containing the file content"""
import os
import logging
file_content = []
dic = {}  # Dictionary to store all the files content
volt_dict = {}
curr_dict = {}
capacity_dict = {}
area = {}
return_dict = {}
all_files_types_of_analysis = [] # List that store the kind of analysis that need to be done for your files

def importer(filepaths, **kwargs):
    """The importer gets one positional argument, which is a list with the passed filepaths.
    Then kwargs are passed, the ones stated in the config file! If you do not pass any, then there are no kwargs!"""
    # Read in file content
    for fileidx, file in enumerate(filepaths):
        with open(file, "r") as fp:
            file_content.append(fp.read())
        file_name = os.path.basename(filepaths[fileidx])  # Take the last element of the file path as the name of the file
        dic[file_name] = file_content[fileidx].split('\n') # Assign the file name to its content in a dcitionary
        dic[file_name]= [i.split('â')[0] for i in dic[file_name]] # Sometimes for certain data there is an additional â that here is removed
        dic[file_name] = list(filter(None, dic[file_name])) # Remove blank lines from the data
        analysis_type = [s for s in dic[file_name] if "Run" in s][0].split()[0] # Define the analysis type (gate, diode or mos)
        all_files_types_of_analysis.append(analysis_type)
        index_of_datastart = dic[file_name].index([s for s in dic[file_name] if "Run" in s][0]) + 4 # (3+1) from Run entry to data values +3, +1 because the first data value is often unstable (ignore it)

        # Find where the data ends
        end_data = find_dataend(dic[file_name])

        # Importing from a file
        data_extracted = extract_data(file_name, dic[file_name], index_of_datastart, end_data)
        return_dict = return_dictionary(data_extracted, file_name, analysis_type)

    return return_dict

def return_dictionary(data_extracted, file_name, analysis_type):
    if len(data_extracted[2]) > 1: # For files containing capacity measurements
        return_dict[file_name] = {"data": {"Voltage": data_extracted[0], "Current": data_extracted[1], 'Capacity': data_extracted[2]}}
        return_dict[file_name]["header"] = [data_extracted[3], analysis_type, all_files_types_of_analysis]
        return_dict[file_name].update({"measurements": ["Voltage", "Current", 'Capacity']})
        return_dict[file_name].update({"units": ["V", "A", 'F']})
    else:
        return_dict[file_name] = {"data": {"Voltage": data_extracted[0], "Current": data_extracted[1]}}
        return_dict[file_name]["header"] = [data_extracted[3], analysis_type, all_files_types_of_analysis]
        return_dict[file_name].update({"measurements": ["Voltage", "Current"]})
        return_dict[file_name].update({"units": ["V", "A"]})

    return return_dict

def find_dataend(file):
    # Define a function to find where the data ends
    numbers = ['0','1','2','3','4','5','6','7','8','9','-']
    index_of_dataend = 0
    revlist = reversed(file)
    for element in revlist:
        if len(element) > 1:
            if element[0] not in numbers:
                index_of_dataend += 1
                continue
            else:
                index_of_dataend += 1
                end_data = len(file) - index_of_dataend
                break

    return end_data

def extract_data(file_name, dictionary, index_of_datastart, end_data):
    log = logging.getLogger(__name__)
    capacity = []
    volt = []
    curr = []
    for i in dictionary[index_of_datastart:(end_data + 1)]:
        data_columns = i.split()  # Extract the data values
        volt.append(data_columns[0])
        curr.append(data_columns[1])
        try:
            capacity.append(data_columns[2])
        except Exception:
            pass
    try:
        volt_dict[file_name] = [float(i) for i in volt]
    except Exception as err:
        log.warning("Not all the voltage data is a float number, check that you have written it correctly... Error: {}".format(err))
    try:
        curr_dict[file_name] = [float(i) for i in curr]
    except Exception as err:
        log.warning("Not all the current data is a float number, check that you have written it correctly... Error: {}".format(err))
    try:
        capacity_dict[file_name] = [float(i) for i in capacity]
    except Exception:
        capacity_dict[file_name] = []
        log.warning("Impossible to extract capacity values, check if you wrote it correctly or if it is contained in the file...")
    area[file_name] = [s for s in dic[file_name] if "Area" in s][0]

    return volt_dict[file_name], curr_dict[file_name], capacity_dict[file_name], area[file_name]