"""An example how a custom importer works"""


def myImporter(filepaths, **kwargs):
    """The importer gets one positional argument, which is a list with the passed filepathes.
    Then kwargs are passed, the ones stated in the config file! If you do not pass any, then there are no kwargs!"""


    # In our case there are two optional parametes lets print them:
    count = 0
    file_content = []
    dic = {}
    volt_dict = {}
    curr_dict = {}
    capacity_dict = {}
    area = {}
    return_dict = {}
    # Read in file content
    for file in filepaths:
        with open(file, "r") as fp:
            file_content.append(fp.read())
        file_name = filepaths[count].split('/')[-1]
        dic[file_name] = file_content[count].split('\n')
        dic[file_name]= [i.split('â')[0] for i in dic[file_name]]

        count2 = 0
        count3 = 0
        numbers = ['0','1','2','3','4','5','6','7','8','9','-']
        data = ['2017','2018','2019','2020','2021','2022','2023']
        for element in dic[file_name]:
            count2 += 1
            if element.split(' ')[0][-4:] not in data and len(element) > 1:
                if element[0] not in numbers:
                    continue
                else:
                    start_data = count2
                    break

        revlist = reversed(dic[file_name])

        for element in revlist:
            count3 += 1
            if element.split(' ')[0][-4:] not in data and len(element) > 1:
                if element[0] not in numbers:
                    continue
                else:
                    end_data = len(dic[file_name]) - count3
                    break

        if file_name[0:6] == 'IV_GCD':
            volt = []
            curr = []
            for i in dic[file_name][start_data:(end_data + 1)]:
                first, second = i.split('\t')
                volt.append(first)
                curr.append(second)
            volt_dict[file_name] = [float(i) for i in volt]
            curr_dict[file_name] = [float(i) for i in curr]

            area[file_name] = [s for s in dic[file_name] if "Area" in s]
            analysis_type = [s for s in dic[file_name] if "Run" in s][0].split(' ')[0]
            return_dict[file_name] = {"data": {"Voltage": volt_dict[file_name], "Current": curr_dict[file_name]}}
            return_dict[file_name]["header"] = [area[file_name][0], analysis_type]
            return_dict[file_name].update({"measurements": ["Voltage", "Current"]})
            return_dict[file_name].update({"units": ["V", "A"]})

            count += 1

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

            count += 1

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
            count += 1

    return return_dict


