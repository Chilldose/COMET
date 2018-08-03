import ast
import json
import os
import os.path as osp
import sys, importlib, logging

import numpy as np
import pyqtgraph as pq
from PyQt5.QtCore import Qt
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .. import utilities

l = logging.getLogger(__name__)

hf = utilities.help_functions()


class DataBrowser_window:

    def __init__(self, GUI_classes, layout):

        # Variables
        self.variables = GUI_classes
        self.layout = layout

        #self.variables.default_values_dict["Defaults"].update({"current_selected_browser_value": None, "current_selected_main_object": None})
        self._translate = QtCore.QCoreApplication.translate

        @hf.raise_exception
        def pad_browser_update():
            items = []
            for i, pad_files in enumerate(self.variables.pad_files_dict.keys()):
                items.append(QtWidgets.QTreeWidgetItem(self.data_ui.Padfile_selector_3))
                self.data_ui.Padfile_selector_3.topLevelItem(i).setText(0, self._translate("data_browser", str(pad_files)))
                for j, childs in enumerate(self.variables.pad_files_dict[str(pad_files)]):
                    QtWidgets.QTreeWidgetItem(items[i])
                    self.data_ui.Padfile_selector_3.topLevelItem(i).child(j).setText(0, self._translate("data_browser", str(childs)))

        @hf.raise_exception
        def load_padfile_to_screen(item, kwargs=None):
            '''This function loads the pad file to screen'''

            # First find selected pad file in the dict
            sensor_found = False
            proj = ""
            sens = "" # needed for jit
            for projects in self.variables.pad_files_dict.keys():
                for sensors in self.variables.pad_files_dict[projects]:
                    if item.text(0) == sensors:
                        sensor_found = True
                        proj = projects
                        sens = sensors
                        break
                if sensor_found:
                    break
            else:
                self.data_ui.pad_text.setText(self._translate("data_browser", ""))

            if sensor_found:
                text = ""
                for lines in self.variables.pad_files_dict[proj][sens]["header"]:
                    text += str(lines)

                for items in self.variables.pad_files_dict[proj][sens]["data"]:
                    for values in items:
                        text += str(values) + "\t"
                    text += "\n"
                self.data_ui.pad_text.setText(self._translate("data_browser", text))

        # functions for the device tab
        @hf.raise_exception
        def devices_browser_update():
                for i, devices in enumerate(self.variables.devices_dict.keys()):
                    QtWidgets.QTreeWidgetItem(self.data_ui.device_selector)
                    self.data_ui.device_selector.topLevelItem(i).setText(0, self._translate("data_browser", str(devices)))


        @hf.raise_exception
        def load_device_values(item, kwargs = None):
                '''Loads the big list of values'''

                try:
                    try:
                        self.data_ui.key_edit.setText("")
                        self.data_ui.value_edit.setText("")
                        try:
                            self.variables.default_values_dict["Defaults"]["current_selected_browser_value"] = item.text(0)
                            item = item.text(0)
                            #print self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]
                        except:
                            pass
                            #print "Key Error is raised, the key 'current_selected_browser_value' could not be found"

                        for i in range(self.data_ui.key_value_tree.topLevelItemCount()):
                            self.data_ui.key_value_tree.takeTopLevelItem(0)

                        for i, keys in enumerate(self.variables.devices_dict[str(self.variables.default_values_dict["Defaults"]["current_selected_browser_value"])].keys()):
                            QtWidgets.QTreeWidgetItem(self.data_ui.key_value_tree)
                            self.data_ui.key_value_tree.topLevelItem(i).setText(0, self._translate("data_browser", keys))
                            self.data_ui.key_value_tree.topLevelItem(i).setText(1, self._translate("data_browser", str(self.variables.devices_dict[item][keys])))
                    #except KeyError:
                        #print "Key Error is raised, the key 'current_selected_browser_value' could not be found"
                        #l.error("Key Error is raised, the key 'current_selected_browser_value' could not be found")
                    except:
                        pass
                        #l.error("Unknown error was raised during loading of device values" + str(sys.exc_info()[0]))
                        #print "Unknown error was raised during loading of device values", sys.exc_info()[0]

                except Exception as error:
                    print "Error type:", error
                    #print "Trace: ", traceback #sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                    raise sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]

        @hf.raise_exception
        def reload_devices_button_action(kwargs = None):
            device = str(self.variables.default_values_dict["Defaults"]["current_selected_browser_value"])

            if device != "None":
                load_device_values(device)

        @hf.raise_exception
        def save_devices_button_action(kwargs = None):
            fileDialog = QFileDialog()
            path = fileDialog.getOpenFileName()[0]
            if path:
                device = self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]
                hf.write_init_file(str(path.split("/")[-1].split(".")[0]), self.variables.devices_dict[device], str(path[:-len(path.split("/")[-1])]))

        @hf.raise_exception
        def add_item_device_button(kwargs = None):
            if self.data_ui.key_edit.text() not in self.variables.devices_dict[self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]]:
                self.variables.devices_dict[self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]][self.data_ui.key_edit.text()] = self.data_ui.value_edit.text()
                reload_devices_button_action()

        @hf.raise_exception
        def change_value_devices_button(kwargs = None):

            if self.data_ui.key_edit.text() and self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]:
                settings = self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]

                if settings in self.variables.devices_dict and self.data_ui.key_edit.text() in self.variables.devices_dict[settings]: # Has to be so, otherwise mismatch can happen
                    try:
                        conv_object = ast.literal_eval(str(self.data_ui.value_edit.text()))
                        self.variables.devices_dict[settings][self.data_ui.key_edit.text()] = conv_object
                    except:
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Critical)
                        msg.about(None, "Error", "Could not interpret input \"" + str(self.data_ui.value_edit.text()) +"\" \n it seems that this is not a valid literal.")
                        l.error("Could not interpret input " + str(self.data_ui.value_edit.text()) +" it seems that this is not a valid literal." )

                    #try:
                        #Try making a list out of the input
                     #   if self.data_ui.value_edit.text().find(",") > 0:
                    #        list = str(self.data_ui.value_edit.text().strip("[").strip("]")).strip("\"").split(",")
                    #        list = map(lambda x: x.strip().strip("'"), list)
                    #        try:
                    #            list = map(float, list) # tries to convert to float
                     #       except:
                    #            pass

                    #        self.variables.devices_dict[settings][self.data_ui.key_edit.text()] = list
                    #        reload_devices_button_action()
                    #        return

                    #except:
                    #    pass


                    #try:
                    #    value = float(self.data_ui.value_edit.text())
                    #except:
                    #    value = self.data_ui.value_edit.text()

                    finally:
                        reload_devices_button_action()

                else:
                    reply = QMessageBox.question(None, 'Warning',"This Key is not included in the dictionary. Would you like to add it to the dictionary?", QMessageBox.Yes, QMessageBox.No)

                    if reply == QMessageBox.Yes:
                        add_item_device_button()
                    else:
                        pass

        @hf.raise_exception
        def remove_item_device_button(kwargs = None):
            if self.data_ui.key_edit.text() in self.variables.devices_dict[self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]]:
                reply = QMessageBox.question(None, 'Warning', "Are you sure to remove the selected item?",QMessageBox.Yes, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.variables.devices_dict[self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]].pop(self.data_ui.key_edit.text(),None)
                    reload_devices_button_action()
            else:
                QMessageBox.question(None, 'Warning', "Hold on there Pirate!!! You try to delete an element which does not exist.", QMessageBox.Ok)

        @hf.raise_exception
        def import_clicked_value_devices(item,kwargs = None):
            self.data_ui.key_edit.setText(item.text(0))
            self.data_ui.value_edit.setText(item.text(1))

        # settings tab
        @hf.raise_exception
        def settings_browser_update(kwargs = None):
            for i, devices in enumerate(self.variables.default_values_dict.keys()):
                QtWidgets.QTreeWidgetItem(self.data_ui.settings_selector_2)
                self.data_ui.settings_selector_2.topLevelItem(i).setText(0, self._translate("data_browser", str(devices)))

        @hf.raise_exception
        def load_settings_values(item,kwargs = None):
            '''Here they key value edit is loaded'''
            try:
                self.data_ui.key_edit.setText("")
                self.data_ui.value_edit.setText("")

                try:
                    self.variables.default_values_dict["Defaults"]["current_selected_browser_value"] = item.text(0)
                    item = item.text(0)
                except:
                    pass
                    #print "Key Error is raised, the key 'current_selected_browser_value' could not be found"

                for i in range(self.data_ui.key_value_tree_2.topLevelItemCount()):
                    self.data_ui.key_value_tree_2.takeTopLevelItem(0)

                for i, keys in enumerate(self.variables.default_values_dict[item].keys()):
                    QtWidgets.QTreeWidgetItem(self.data_ui.key_value_tree_2)
                    self.data_ui.key_value_tree_2.topLevelItem(i).setText(0, self._translate("data_browser", keys))
                    self.data_ui.key_value_tree_2.topLevelItem(i).setText(1, self._translate("data_browser", str(self.variables.default_values_dict[item][keys])))
            #except KeyError:
                #print "Key Error is raised, the key 'current_selected_browser_value' could not be found"
                #l.error("Key Error is raised, the key 'current_selected_browser_value' could not be found")
            except:
                pass
                #l.error("Unknown error was raised during loading of device values" + str(sys.exc_info()[0]))
                #print "Unknown error was raised during loading of device values", sys.exc_info()[0]

        @hf.raise_exception
        def reload_settings_button_action(kwargs = None):
            device = str(self.variables.default_values_dict["Defaults"]["current_selected_browser_value"])

            if device != "None":
                self.variables.ui_plugins["Settings_window"].load_new_settings()  # reloads the settings made
                load_settings_values(device)


        @hf.raise_exception
        def import_clicked_value_settings(item,kwargs = None):
            '''This imports the values from the item to the edit lines'''
            self.data_ui.key_edit_2.setText(item.text(0))
            self.data_ui.value_edit_2.setText(item.text(1))


        @hf.raise_exception
        def save_settings_button_action(kwargs = None):

            fileDialog = QFileDialog()
            path = fileDialog.getOpenFileName()[0]
            if path:
                settings = self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]
                hf.write_init_file(str(path.split("/")[-1].split(".")[0]), self.variables.default_values_dict[settings], str(path[:-len(path.split("/")[-1])]))

        @hf.raise_exception
        def add_item_settings_button(kwargs = None):

            if self.data_ui.key_edit_2.text() not in self.variables.default_values_dict[self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]]:
                self.variables.default_values_dict[self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]][self.data_ui.key_edit_2.text()] = self.data_ui.value_edit_2.text()
                reload_settings_button_action()

        @hf.raise_exception
        def change_value_settings_button(kwargs = None):

            if self.data_ui.key_edit_2.text() and self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]:
                settings = self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]

                if settings in self.variables.default_values_dict and self.data_ui.key_edit_2.text() in self.variables.default_values_dict[settings]: # Has to be so, otherwise mismatch can happen
                    try:
                        conv_object = ast.literal_eval(self.data_ui.value_edit_2.text())
                        self.variables.default_values_dict[settings][self.data_ui.key_edit_2.text()] = conv_object

                    except:
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Critical)
                        msg.about(None, "Error", "Could not interpret input \"" + str(self.data_ui.value_edit_2.text()) +"\" \n it seems that this is not a valid literal.")
                        l.error("Could not interpret input " + str(self.data_ui.value_edit_2.text()) +" it seems that this is not a valid literal." )

                    reload_settings_button_action()
                    #try:
                    #    #Try making a list out of the input
                    #    if self.data_ui.value_edit_2.text().find(",") >0:
                    #        list = str(self.data_ui.value_edit_2.text().strip("[").strip("]")).strip("\"").split(",")
                    #        list = map(lambda x: x.strip().strip("'"), list)
                    #        try:
                    #            list = map(float, list) # tries to convert to float
                    #        except:
                    #            pass

                    #        self.variables.default_values_dict[settings][self.data_ui.key_edit_2.text()] = list
                    #        reload_settings_button_action()
                    #        return
                    #except:
                    #    pass
                    #try:
                    #    value = float(self.data_ui.value_edit_2.text())
                    #except:
                    #    value = self.data_ui.value_edit_2.text()

                else:
                    reply = QMessageBox.question(None, 'Warning',"This Key is not included in the dictionary. Would you like to add it to the dictionary?", QMessageBox.Yes, QMessageBox.No)

                    if reply == QMessageBox.Yes:
                        add_item_settings_button()
                    else:
                        pass

        @hf.raise_exception
        def remove_item_settings_button(kwargs = None):
            if self.data_ui.key_edit_2.text() in self.variables.default_values_dict[self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]]:
                reply = QMessageBox.question(None, 'Warning', "Are you sure to remove the selected item?",QMessageBox.Yes, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.variables.default_values_dict[self.variables.default_values_dict["Defaults"]["current_selected_browser_value"]].pop(self.data_ui.key_edit_2.text(),None)
                    reload_settings_button_action()
            else:
                QMessageBox.question(None, 'Warning', "Hold on there Pirate!!! You try to delete an element which does not exist.", QMessageBox.Ok)

        # pad files

        #def pad_browser_update():
        #    for i, pad in enumerate(self.variables.default_values_dict.keys()):
        #        QtWidgets.QTreeWidgetItem(self.data_ui.settings_selector_2)
        #        self.data_ui.settings_selector_2.topLevelItem(i).setText(0, self._translate("data_browser", str(devices)))

        #def load_pad_values(item):
        #            try:

        #                self.data_ui.key_edit.setText("")
        #                self.data_ui.value_edit.setText("")

        #                try:
        #                    self.variables.default_values_dict["Defaults"]["current_selected_browser_value"] = item.text(0)
        #                    item = item.text(0)
        #                except:
        #                   pass

        #                for i in range(self.data_ui.key_value_tree_2.topLevelItemCount()):
        #                    self.data_ui.key_value_tree_2.takeTopLevelItem(0)

        #               for i, keys in enumerate(self.variables.default_values_dict[item].keys()):
        #                    QtWidgets.QTreeWidgetItem(self.data_ui.key_value_tree_2)
        #                    self.data_ui.key_value_tree_2.topLevelItem(i).setText(0, self._translate("data_browser", keys))
        #                    self.data_ui.key_value_tree_2.topLevelItem(i).setText(1, self._translate("data_browser", str(
        #                        self.variables.default_values_dict[item][keys])))
        #            except:
        #                pass



        # Data browser
        data_browser_widget = QWidget()
        self.data_ui = self.variables.load_QtUi_file("./modules/QT_Designer_UI/data_explorer.ui", data_browser_widget)
        #self.data_ui = Ui_data_browser()
        #self.data_ui.setupUi(data_browser_widget)

        settings_browser_update()
        devices_browser_update()
        pad_browser_update()


        self.data_ui.device_selector.itemClicked.connect(load_device_values)
        self.data_ui.reload_button.clicked.connect(reload_devices_button_action)
        self.data_ui.key_value_tree.itemClicked.connect(import_clicked_value_devices)
        self.data_ui.Change_value_button.clicked.connect(change_value_devices_button)
        self.data_ui.Add_button.clicked.connect(add_item_device_button)
        self.data_ui.remove_item_device.clicked.connect(remove_item_device_button)
        self.data_ui.save_button.clicked.connect(save_devices_button_action)

        self.data_ui.settings_selector_2.itemClicked.connect(load_settings_values)
        self.data_ui.reload_button_2.clicked.connect(reload_settings_button_action)
        self.data_ui.key_value_tree_2.itemClicked.connect(import_clicked_value_settings)
        self.data_ui.change_value_2.clicked.connect(change_value_settings_button)
        self.data_ui.add_item.clicked.connect(add_item_settings_button)
        self.data_ui.remove_item_settings.clicked.connect(remove_item_settings_button)
        self.data_ui.save_button_2.clicked.connect(save_settings_button_action)

        self.data_ui.Padfile_selector_3.itemClicked.connect(load_padfile_to_screen)


        self.layout.addWidget(data_browser_widget)


        # Add cmd option
        self.variables.shell.add_cmd_command(self.get)

    def get(self, command):
        """This functions takes in the type (Devices, Settings, Pad files), (name of main cat), (key)
        And returns the value of this key"""

        # Pick command
        commands = str(command).strip().split()
        parent = commands[0]
        sub = commands[1]
        key = commands[2]

        if parent.upper() == "DEVICES" or parent.upper() == "DEVICE":
            try:
                return str(self.variables.devices_dict[sub][key])
            except KeyError as e:
                return "An key error occured: " + str(e)

        elif parent.upper() == "DEFAULTS" or parent.upper() == "DEFAULT":
            try:
                return str(self.variables.default_values_dict["Defaults"][sub][key])
            except KeyError as e:
                return "An key error occured: " + str(e)

        elif parent.upper() == "SWITCHING":
            try:
                return str(self.variables.default_values_dict["Switching"][sub][key])
            except KeyError as e:
                return "An key error occured: " + str(e)

        # TODO: pad files currently not accessible due to spaces
        elif parent.upper() == "PAD" or parent.upper() == "PAD FILES" or parent.upper() == "PAD FILE":
            try:
                return str(self.variables.pad_files_dict[sub][key])
            except KeyError as e:
                return "An key error occured: " + str(e)

        else:
            return "Could not interpret input."


