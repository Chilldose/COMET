if __name__ == '__main__':
    import os
    os.system("set QT_SCALE_FACTOR=1.5")
    from COMET.main import main# This starts the actual measurement software
    try:
        main()
    except:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        os.system("cd {}".format(dir_path))
        # For Linux on remote Displays
        os.system("export DISPLAY:=0.0")
        main()
