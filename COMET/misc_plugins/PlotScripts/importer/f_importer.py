
from forge.tools import read_in_ASCII_measurement_files

def myImporter(filepathes, **kwargs):
    '''keys of ana_types get used later to find the correct file !'''
    ana_types = {"MOS capacitor": [], "FET": [], "Van-der-Pauw": [], "bulk cross": [], "Polysilicon meander": [],
                 "Metal meander": [], "Contact Chain": [], "CBKR": [], "Linewidth": []}

    MOS = {'header_lines': 13, 'measurement_description': 14, 'units_line': 14, 'data_start': 15}
    FET = {'header_lines': 31, 'measurement_description': 32, 'units_line': 32, 'data_start': 33}
    Van = {'header_lines': 11, 'measurement_description': 12, 'units_line': 12, 'data_start': 13}
    Meander_m = {'header_lines': 11, 'measurement_description': 12, 'units_line': 12, 'data_start': 13}
    Meander_p = {'header_lines': 25, 'measurement_description': 26, 'units_line': 26, 'data_start': 27}
    chain = {'header_lines': 11, 'measurement_description': 12, 'units_line': 12, 'data_start': 13}
    CBKR = {'header_lines': 11, 'measurement_description': 12, 'units_line': 12, 'data_start': 13}
    Linewidth = {'header_lines': 11, 'measurement_description': 12, 'units_line': 12, 'data_start': 13}

    settings_list = [MOS, FET, Van, Van, Meander_p, Meander_m, chain, CBKR, Linewidth]
    for file in filepathes:
        with open(file, "r") as fp:
            for line in fp:
                for key in ana_types.keys():
                    if key.lower() in line.lower():
                        ana_types[key].append(file)
                        break

    final_data, final_order = {}, []
    for i, key in enumerate(ana_types.keys()):
        all_data, load_order = read_in_ASCII_measurement_files(ana_types[key], settings_list[i])
        final_data.update(all_data)
        final_order += load_order

    return final_data