"""An example how a custom importer works"""


def myImporter(filepathes, **kwargs):
    """The importer gets one positional argument, which is a list with the passed filepathes.
    Then kwargs are passed, the ones stated in the config file! If you do not pass any, then there are no kwargs!"""


    # In our case there are two optional parametes lets print them:
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

    # The top level keys are usually the file names and the values is a dict with keys being the measurement names,
    # with their values being lists of list like:
    return_dict["FirstFile"] = {"CoolMeasurement": [[1,2,3,4,5], [1,2,3,4,5]]}
    return_dict["SecondFile"] = {"OtherMeasurement": [[5,4,3,2,1], [5,4,3,2,1]]}
    return return_dict


