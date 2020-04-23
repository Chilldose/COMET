if __name__ == '__main__':
    import os
    import platform
    OS = platform.system()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    os.system("cd {}".format(dir_path))
    os.system("set QT_SCALE_FACTOR=1.5")

    if OS == "Linux":
        os.system("export DISPLAY:=0.0")
    from COMET.main import main # This starts the actual measurement software
    main()
