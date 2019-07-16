# Merges two strip files for eg 2S sensors
import numpy as np
from functools import reduce
import operator


def main(*pathes):

    files_list = load_files(pathes)

    final_file = merge_files(files_list, 21, 1016)

    save_file(final_file, pathes[0], 21)

def load_files(pathes):

    file_list = []
    for path in pathes:
        with open(path, "r") as f:
            file_list.append(f.readlines())
    return file_list

def merge_files(files, header=0, split=1016):

    # Get rid of header and find last number in the first file
    offset = 0
    header_str = files[0][:header]
    for file in files:
        new_line_num = []
        for line in file[header:header+split]:
            line = line.split()
            try:
                line[0] = float(line[0]) + offset # If nan values occure
                new_line_num.append(line)
            except:
                pass
        offset += int(line[0]) # Last lineentry, but first value (stripnumber)
        header_str.extend(new_line_num)

    return header_str

def save_file(file, path, header):
    ljust_len=24 # Same as with the others
    with open(path[:-4]+"_merged.txt", "w+") as f:
        header_str = "".join((file[:header]))
        f.write(header_str)
        for line in file[header:]:
            f.write(''.join([format(el, '<24') for el in line]))
            f.write('\n')


if __name__ == "__main__":
    main("\\\\HEROS\\dbloech\\QTC_measurements\\Tosort\\str_VPX28442_43_2S_side1.txt",
         "\\\\HEROS\\dbloech\\QTC_measurements\\Tosort\\str_VPX28442_43_2S_side2.txt")

