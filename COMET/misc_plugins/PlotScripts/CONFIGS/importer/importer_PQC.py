'create a custom importer which is able to manage different kind of file analysis'
'read the files and in the end return a dictionary containing the file content'


def importer(filepaths, **kwargs):
    """The importer gets one positional argument, which is a list with the passed filepaths.
    Then kwargs are passed, the ones stated in the config file! If you do not pass any, then there are no kwargs!"""

    number_of_files = 0   #count the number of files that you are dealing with
    file_content = []
    dic = {}    #dictionary to store all the files content
    volt_dict = {}
    curr_dict = {}
    capacity_dict = {}
    area = {}
    return_dict = {}


    # Read in file content
    for file in filepaths:
        with open(file, "r") as fp:
            file_content.append(fp.read())
        file_name = filepaths[number_of_files].split('/')[-1]  #take the last element of the file path as the name of the file
        dic[file_name] = file_content[number_of_files].split('\n') #assign the file name to its content in a dcitionary
        dic[file_name]= [i.split('â')[0] for i in dic[file_name]] #sometimes for certain data there is an additional â that here is removed
        dic[file_name] = list(filter(None, dic[file_name])) #remove blank lines from the data

        index_of_datastart = 0
        index_of_dataend = 0

        #define two lists that will be used later to identify the line in the file where the date (12/10/2019) value is, and the start index of the data numerical values.
        numbers = ['0','1','2','3','4','5','6','7','8','9','-']
        data = ['2017','2018','2019','2020','2021','2022','2023','2024']

        #find the index of the line in the file where the data values start
        for element in dic[file_name]:

            if element.split(' ')[0][-4:] not in data and len(element) > 1:  #element.split(' ')[0][-4:] checks that this is not a date entry(10/11/2019); len(element) > 1 checks that this is at least a two columns data value.
                if element[0] not in numbers: #check if it is not a numerical value (non data)
                    index_of_datastart += 1
                    continue
                else:
                    index_of_datastart += 1
                    start_data = index_of_datastart
                    break

        # find the index of the line in the file where the data values end
        #reverse the list and repeat the above algorythm to find the start index of the data, in the end subtract this new find index to the index length of the file.
        revlist = reversed(dic[file_name])

        for element in revlist:

            if element.split(' ')[0][-4:] not in data and len(element) > 1:
                if element[0] not in numbers:
                    index_of_dataend += 1
                    continue
                else:
                    index_of_dataend += 1
                    end_data = len(dic[file_name]) - index_of_dataend
                    break


        #importing from a gate diode file
        if file_name[0:6] == 'IV_GCD':
            volt = []
            curr = []
            for i in dic[file_name][start_data:(end_data + 1)]:
                first, second = i.split('\t')   #extract elements of data from two columns and store the first element in a voltage list volt[] and the second in the current list curr[].
                volt.append(first)
                curr.append(second)
            volt_dict[file_name] = [float(i) for i in volt] #assuring that the data are stored as float numbers
            curr_dict[file_name] = [float(i) for i in curr]

            area[file_name] = [s for s in dic[file_name] if "Area" in s] #find the area entry in the file
            analysis_type = [s for s in dic[file_name] if "Run" in s][0].split(' ')[0] #find the analysis type in the file

            #return a dictionary
            return_dict[file_name] = {"data": {"Voltage": volt_dict[file_name], "Current": curr_dict[file_name]}}
            return_dict[file_name]["header"] = [area[file_name][0], analysis_type]
            return_dict[file_name].update({"measurements": ["Voltage", "Current"]})
            return_dict[file_name].update({"units": ["V", "A"]})

            number_of_files += 1

        #importing a diode file, same as gate file just changing the file_name specification.
        elif file_name[0:8] == 'CV_Diode':
            capacity = []
            volt = []
            curr = []
            for i in dic[file_name][start_data:(end_data + 1)]:
                first, second, third = i.split('\t')
                volt.append(first)
                curr.append(second)
                capacity.append(third)
            volt_dict[file_name] = [float(i) for i in volt]
            curr_dict[file_name] = [float(i) for i in curr]
            capacity_dict[file_name] = [float(i) for i in capacity]

            area[file_name] = [s for s in dic[file_name] if "Area" in s]
            analysis_type = [s for s in dic[file_name] if "Run" in s][0].split(' ')[0]
            return_dict[file_name] = {"data": {"Voltage": volt_dict[file_name], "Current": curr_dict[file_name], 'Capacity': capacity_dict[file_name]}}
            return_dict[file_name]["header"] = [area[file_name][0], analysis_type]
            return_dict[file_name].update({"measurements": ["Voltage", "Current", 'Capacity']})
            return_dict[file_name].update({"units": ["V", "A", 'F']})

            number_of_files += 1

        #importing a mos file, same as importing the other kind of analysis, here else is used because so far just three analysis can be done.
        else:
            capacity = []
            volt = []
            curr = []
            for i in dic[file_name][start_data:(end_data + 1)]:
                first, second, third = i.split('\t')
                volt.append(first)
                curr.append(second)
                capacity.append(third)
            volt_dict[file_name] = [float(i) for i in volt]
            curr_dict[file_name] = [float(i) for i in curr]
            capacity_dict[file_name] = [float(i) for i in capacity]
            area[file_name] = [s for s in dic[file_name] if "Area" in s]
            analysis_type = [s for s in dic[file_name] if "Run" in s][0].split(' ')[0]
            return_dict[file_name] = {"data": {"Voltage": volt_dict[file_name], "Current": curr_dict[file_name],
                                               'Capacity': capacity_dict[file_name]}}
            return_dict[file_name]["header"] = [area[file_name][0], analysis_type]
            return_dict[file_name].update({"measurements": ["Voltage", "Current", 'Capacity']})
            return_dict[file_name].update({"units": ["V", "A", 'F']})
            number_of_files += 1

    return return_dict


