"""__author__: Dallavalle Riccardo
__email__: dallavallericcardo@outlook.com"""

"""Create a custom importer which is able to manage different kind of file analysis.
Read the files and in the end return a dictionary containing the file content"""
import os

file_content = []
dic = {}  # dictionary to store all the files content
volt_dict = {}
curr_dict = {}
capacity_dict = {}
area = {}
return_dict = {}

def importer(filepaths, **kwargs):
    """The importer gets one positional argument, which is a list with the passed filepaths.
    Then kwargs are passed, the ones stated in the config file! If you do not pass any, then there are no kwargs!"""

    # Read in file content
    for fileidx, file in enumerate(filepaths):
        with open(file, "r") as fp:
            file_content.append(fp.read())
        file_name = os.path.basename(filepaths[fileidx])  #take the last element of the file path as the name of the file
        dic[file_name] = file_content[fileidx].split('\n') #assign the file name to its content in a dcitionary
        dic[file_name]= [i.split('â')[0] for i in dic[file_name]] #sometimes for certain data there is an additional â that here is removed
        dic[file_name] = list(filter(None, dic[file_name])) #remove blank lines from the data
        analysis_type = [s for s in dic[file_name] if "Run" in s][0].split()[0] #define the analysisi type (gate, diode or mos)
        index_of_datastart = dic[file_name].index([s for s in dic[file_name] if "Run" in s][0]) + 3


        #find where the data ends
        end_data = finddataend(dic[file_name])

        #importing from a gate diode file
        if analysis_type[0:6] == 'IV_GCD':
            dataextracted = extractdata(file_name, dic[file_name], index_of_datastart, end_data)

            return_dict[file_name] = {"data": {"Voltage": dataextracted[0], "Current": dataextracted[1]}}
            return_dict[file_name]["header"] = [dataextracted[3], analysis_type]
            return_dict[file_name].update({"measurements": ["Voltage", "Current"]})
            return_dict[file_name].update({"units": ["V", "A"]})

        else:
            dataextracted = extractdata(file_name, dic[file_name], index_of_datastart, end_data)

            return_dict[file_name] = {"data": {"Voltage": dataextracted[0], "Current": dataextracted[1],
                                               'Capacity': dataextracted[2]}}
            return_dict[file_name]["header"] = [dataextracted[3], analysis_type]
            return_dict[file_name].update({"measurements": ["Voltage", "Current", 'Capacity']})
            return_dict[file_name].update({"units": ["V", "A", 'F']})

    return return_dict


#define a function to find where the data ends
def finddataend(file):
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

def extractdata(file_name, dictionary, index_of_datastart, end_data):
    capacity = []
    volt = []
    curr = []
    for i in dictionary[index_of_datastart:(end_data + 1)]:
        data_columns = i.split()  # extract the data values
        volt.append(data_columns[0])
        curr.append(data_columns[1])
        try:
            capacity.append(data_columns[2])
        except:
            pass
    try:
        volt_dict[file_name] = [float(i) for i in volt]
    except:
        print("Not all the voltage data is a float number, check that you have written it correctly")
    try:
        curr_dict[file_name] = [float(i) for i in curr]
    except:
        print("Not all the current data is a float number, check that you have written it correctly")
    try:
        capacity_dict[file_name] = [float(i) for i in capacity]
    except:
        capacity_dict[file_name] = []
        print("Impossible to extract capacity values, check if you wrote it correctly")

    area[file_name] = [s for s in dic[file_name] if "Area" in s][0]

    return volt_dict[file_name], curr_dict[file_name], capacity_dict[file_name], area[file_name]