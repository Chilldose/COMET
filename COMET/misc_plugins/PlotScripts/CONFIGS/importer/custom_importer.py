"""An example how a custom importer works"""


def myImporter(filepathes, **kwargs):
    """The importer gets one positional argument, which is a list with the passed filepathes.
    Then kwargs are passed, the ones stated in the config file! If you do not pass any, then there are no kwargs!"""

    # Here you can print the kwargs:
    print(kwargs)

    file_content = []
    # Read in file content
    for file in filepathes:
        with open(file, "r") as fp:
            file_content.append(fp.read())

        # Here your content manipulation is done in my case I simply display the file content as print
        print(file_content[-1])

    # After importing and parsing the data the return must be a dict of dicts like described in the docs
    return_dict = {}

    # The top level keys are usually the file names and the values are a dict with keys being the measurement names,
    # with their values being lists of list like:
    return_dict["FirstFile"] = {
        "data": {
            "CoolxMeasurement": [1, 2, 3, 4, 5],
            "OtheryMeasurement": [5, 4, 3, 2, 1],
        }
    }
    return_dict["SecondFile"] = {
        "data": {
            "CoolxMeasurement": [1, 2, 3, 4, 5, 6],
            "OtheryMeasurement": [6, 5, 4, 3, 2, 1],
        }
    }

    # If you have a header you can add him via:
    return_dict["FirstFile"]["header"] = "Some cool optional header"

    # If you want to define your measurement it may be wise to define the possible measurements,
    # otherwise the script trys to extract the possible measurements from you data
    return_dict["FirstFile"].update(
        {"measurements": ["CoolxMeasurement", "OtheryMeasurement"]}
    )
    return_dict["SecondFile"].update(
        {"measurements": ["CoolxMeasurement", "OtheryMeasurement"]}
    )

    # The other thing you might want to add are the units, otherwise "arb. units" will be used
    return_dict["FirstFile"].update({"units": ["V", "A"]})
    return_dict["SecondFile"].update({"units": ["V", "A"]})

    # If you have some additional data you want to store you can store it in the entry "additional"
    return_dict["FirstFile"].update(
        {"additional": "some additional data, whatever you want."}
    )

    # If you want you can define an entry
    return return_dict
