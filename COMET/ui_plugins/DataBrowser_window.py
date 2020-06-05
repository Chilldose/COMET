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

from ..utilities import raise_exception, write_init_file


class DataBrowser_window:
    def __init__(self, GUI_classes, layout):

        # Variables
        self.variables = GUI_classes
        self.layout = layout
        self._translate = QtCore.QCoreApplication.translate

        self.log = logging.getLogger(__name__)

        # Data browser
        self.data_browser_widget = QWidget()
        self.data_ui = self.variables.load_QtUi_file(
            "Data_explorer.ui", self.data_browser_widget
        )

        self.settings_browser_update()
        self.devices_browser_update()
        self.additional_files_browser_update()

        self.data_ui.device_selector.itemClicked.connect(self.load_device_values)
        self.data_ui.reload_button.clicked.connect(self.reload_devices_button_action)
        self.data_ui.key_value_tree.itemClicked.connect(
            self.import_clicked_value_devices
        )
        self.data_ui.Change_value_button.clicked.connect(
            self.change_value_devices_button
        )
        self.data_ui.Add_button.clicked.connect(self.add_item_device_button)
        self.data_ui.remove_item_device.clicked.connect(self.remove_item_device_button)
        self.data_ui.save_button.clicked.connect(self.save_devices_button_action)

        self.data_ui.settings_selector_2.itemClicked.connect(self.load_settings_values)
        self.data_ui.reload_button_2.clicked.connect(self.reload_settings_button_action)
        self.data_ui.key_value_tree_2.itemClicked.connect(
            self.import_clicked_value_settings
        )
        self.data_ui.change_value_2.clicked.connect(self.change_value_settings_button)
        self.data_ui.add_item.clicked.connect(self.add_item_settings_button)
        self.data_ui.remove_item_settings.clicked.connect(
            self.remove_item_settings_button
        )
        self.data_ui.save_button_2.clicked.connect(self.save_settings_button_action)

        self.data_ui.Padfile_selector_3.itemClicked.connect(self.load_file_to_screen)
        self.layout.addWidget(self.data_browser_widget)

    @raise_exception
    def additional_files_browser_update(self):
        items = []
        # Add a top level tree item for every directory
        for name, subdict in self.variables.additional_files.items():
            tree = QtWidgets.QTreeWidgetItem([name])
            self.data_ui.Padfile_selector_3.addTopLevelItem(tree)
            # Loop over all subdirectories and files
            self.add_subtree(tree, subdict)

    def add_subtree(self, tree, dictionary):
        """
        Adds a subtree to the tree structure

        :param tree: The Qtree object
        :param dict: the dictionary that should be added
        :return: None
        """

        for key, path in dictionary.items():
            if isinstance(path, dict):
                subtree = QtWidgets.QTreeWidgetItem(tree, [key])
                self.add_subtree(subtree, dictionary[key])

    def treeItemToFullPath(self, treeitem):
        """Reconstructs the full tree item path"""
        path = [treeitem.text(0)]
        while treeitem.parent() != None:
            path.extend([treeitem.parent().text(0)])
            treeitem = treeitem.parent()
        return path

    @raise_exception
    def load_file_to_screen(self, item, kwargs=None):
        """This function loads the pad file to screen"""

        # First find selected pad file in the dict

        path = self.treeItemToFullPath(item)
        file = self.variables.additional_files
        for dire in reversed(path):
            file = file[dire]
        if "raw" in file:
            self.data_ui.pad_text.setText(file["raw"])

    # functions for the device tab
    def devices_browser_update(self):
        for i, devices in enumerate(self.variables.devices_dict.keys()):
            QtWidgets.QTreeWidgetItem(self.data_ui.device_selector)
            self.data_ui.device_selector.topLevelItem(i).setText(
                0, self._translate("data_browser", str(devices))
            )

    def load_device_values(self, item, kwargs=None):
        """Loads the big list of values"""

        try:
            try:
                self.data_ui.key_edit.setText("")
                self.data_ui.value_edit.setText("")
                try:
                    self.variables.default_values_dict["settings"][
                        "current_selected_browser_value"
                    ] = item.text(0)
                    item = item.text(0)
                    # print(self.variables.default_values_dict["settings"]["current_selected_browser_value"])
                except:
                    pass
                    # print("Key Error is raised, the key 'current_selected_browser_value' could not be found")

                for i in range(self.data_ui.key_value_tree.topLevelItemCount()):
                    self.data_ui.key_value_tree.takeTopLevelItem(0)

                for i, keys in enumerate(
                    self.variables.devices_dict[
                        str(
                            self.variables.default_values_dict["settings"][
                                "current_selected_browser_value"
                            ]
                        )
                    ].keys()
                ):
                    QtWidgets.QTreeWidgetItem(self.data_ui.key_value_tree)
                    self.data_ui.key_value_tree.topLevelItem(i).setText(
                        0, self._translate("data_browser", keys)
                    )
                    self.data_ui.key_value_tree.topLevelItem(i).setText(
                        1,
                        self._translate(
                            "data_browser", str(self.variables.devices_dict[item][keys])
                        ),
                    )
            except:
                pass

        except Exception as e:
            print("Error type: {}".format(e))
            raise  # sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]

    def reload_devices_button_action(self, kwargs=None):
        device = str(
            self.variables.default_values_dict["settings"][
                "current_selected_browser_value"
            ]
        )

        if device != "None":
            self.load_device_values(device)

    def save_devices_button_action(self, kwargs=None):
        fileDialog = QFileDialog()
        path = fileDialog.getOpenFileName()[0]
        if path:
            device = self.variables.default_values_dict["settings"][
                "current_selected_browser_value"
            ]
            write_init_file(
                str(path.split("/")[-1].split(".")[0]),
                self.variables.devices_dict[device],
                str(path[: -len(path.split("/")[-1])]),
            )

    def add_item_device_button(self, kwargs=None):
        if (
            self.data_ui.key_edit.text()
            not in self.variables.devices_dict[
                self.variables.default_values_dict["settings"][
                    "current_selected_browser_value"
                ]
            ]
        ):
            self.variables.devices_dict[
                self.variables.default_values_dict["settings"][
                    "current_selected_browser_value"
                ]
            ][self.data_ui.key_edit.text()] = self.data_ui.value_edit.text()
            self.reload_devices_button_action()

    def change_value_devices_button(self, kwargs=None):

        if (
            self.data_ui.key_edit.text()
            and self.variables.default_values_dict["settings"][
                "current_selected_browser_value"
            ]
        ):
            settings = self.variables.default_values_dict["settings"][
                "current_selected_browser_value"
            ]

            if (
                settings in self.variables.devices_dict
                and self.data_ui.key_edit.text()
                in self.variables.devices_dict[settings]
            ):  # Has to be so, otherwise mismatch can happen
                try:
                    conv_object = ast.literal_eval(str(self.data_ui.value_edit.text()))
                    self.variables.devices_dict[settings][
                        self.data_ui.key_edit.text()
                    ] = conv_object
                except:
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.about(
                        None,
                        "Error",
                        'Could not interpret input "'
                        + str(self.data_ui.value_edit.text())
                        + '" \n it seems that this is not a valid literal.',
                    )
                    self.log.error(
                        "Could not interpret input "
                        + str(self.data_ui.value_edit.text())
                        + " it seems that this is not a valid literal."
                    )

                finally:
                    self.reload_devices_button_action()

            else:
                reply = QMessageBox.question(
                    None,
                    "Warning",
                    "This Key is not included in the dictionary. Would you like to add it to the dictionary?",
                    QMessageBox.Yes,
                    QMessageBox.No,
                )

                if reply == QMessageBox.Yes:
                    self.add_item_device_button()
                else:
                    pass

    def remove_item_device_button(self, kwargs=None):
        if (
            self.data_ui.key_edit.text()
            in self.variables.devices_dict[
                self.variables.default_values_dict["settings"][
                    "current_selected_browser_value"
                ]
            ]
        ):
            reply = QMessageBox.question(
                None,
                "Warning",
                "Are you sure to remove the selected item?",
                QMessageBox.Yes,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.variables.devices_dict[
                    self.variables.default_values_dict["settings"][
                        "current_selected_browser_value"
                    ]
                ].pop(self.data_ui.key_edit.text(), None)
                self.reload_devices_button_action()
        else:
            QMessageBox.question(
                None,
                "Warning",
                "Hold on there Pirate!!! You try to delete an element which does not exist.",
                QMessageBox.Ok,
            )

    def import_clicked_value_devices(self, item, kwargs=None):
        self.data_ui.key_edit.setText(item.text(0))
        self.data_ui.value_edit.setText(item.text(1))

    # settings tab
    def settings_browser_update(self, kwargs=None):
        for i, devices in enumerate(self.variables.default_values_dict.keys()):
            QtWidgets.QTreeWidgetItem(self.data_ui.settings_selector_2)
            self.data_ui.settings_selector_2.topLevelItem(i).setText(
                0, self._translate("data_browser", str(devices))
            )

    def load_settings_values(self, item, kwargs=None):
        """Here they key value edit is loaded"""
        try:
            self.data_ui.key_edit.setText("")
            self.data_ui.value_edit.setText("")

            try:
                self.variables.default_values_dict["settings"][
                    "current_selected_browser_value"
                ] = item.text(0)
                item = item.text(0)
            except:
                pass
                # print("Key Error is raised, the key 'current_selected_browser_value' could not be found")

            for i in range(self.data_ui.key_value_tree_2.topLevelItemCount()):
                self.data_ui.key_value_tree_2.takeTopLevelItem(0)

            for i, keys in enumerate(self.variables.default_values_dict[item].keys()):
                QtWidgets.QTreeWidgetItem(self.data_ui.key_value_tree_2)
                self.data_ui.key_value_tree_2.topLevelItem(i).setText(
                    0, self._translate("data_browser", keys)
                )
                self.data_ui.key_value_tree_2.topLevelItem(i).setText(
                    1,
                    self._translate(
                        "data_browser",
                        str(self.variables.default_values_dict[item][keys]),
                    ),
                )
        except:
            pass

    def reload_settings_button_action(self, kwargs=None):
        device = str(
            self.variables.default_values_dict["settings"][
                "current_selected_browser_value"
            ]
        )

        if device != "None":
            self.load_settings_values(device)
            try:  # Todo: legacy which is dependent from another gui
                self.variables.ui_plugins[
                    "Settings_window"
                ].load_new_settings()  # reloads the settings made
            except:
                pass

    def import_clicked_value_settings(self, item, kwargs=None):
        """This imports the values from the,  item to the edit lines"""
        self.data_ui.key_edit_2.setText(item.text(0))
        self.data_ui.value_edit_2.setText(item.text(1))

    def save_settings_button_action(self, kwargs=None):

        fileDialog = QFileDialog()
        path = fileDialog.getOpenFileName()[0]
        if path:
            settings = self.variables.default_values_dict["settings"][
                "current_selected_browser_value"
            ]
            write_init_file(
                str(path.split("/")[-1].split(".")[0]),
                self.variables.default_values_dict[settings],
                str(path[: -len(path.split("/")[-1])]),
            )

    def add_item_settings_button(self, kwargs=None):
        try:
            if (
                self.data_ui.key_edit_2.text()
                not in self.variables.default_values_dict[
                    self.variables.default_values_dict["settings"][
                        "current_selected_browser_value"
                    ]
                ]
            ):
                self.variables.default_values_dict[
                    self.variables.default_values_dict["settings"][
                        "current_selected_browser_value"
                    ]
                ][self.data_ui.key_edit_2.text()] = self.data_ui.value_edit_2.text()
                self.reload_settings_button_action()
        except:
            self.log.error(
                "It seems like you are trying to add nothing. Don't be a procastionator and add something usefull."
            )

    def change_value_settings_button(self, kwargs=None):
        try:
            if (
                self.data_ui.key_edit_2.text()
                and self.variables.default_values_dict["settings"][
                    "current_selected_browser_value"
                ]
            ):
                settings = self.variables.default_values_dict["settings"][
                    "current_selected_browser_value"
                ]

                if (
                    settings in self.variables.default_values_dict
                    and self.data_ui.key_edit_2.text()
                    in self.variables.default_values_dict[settings]
                ):  # Has to be so, otherwise mismatch can happen
                    try:
                        conv_object = ast.literal_eval(self.data_ui.value_edit_2.text())
                        self.variables.default_values_dict[settings][
                            self.data_ui.key_edit_2.text()
                        ] = conv_object

                    except:
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Critical)
                        msg.about(
                            None,
                            "Error",
                            'Could not interpret input "'
                            + str(self.data_ui.value_edit_2.text())
                            + '" \n it seems that this is not a valid literal.',
                        )
                        self.log.error(
                            "Could not interpret input "
                            + str(self.data_ui.value_edit_2.text())
                            + " it seems that this is not a valid literal."
                        )

                    self.reload_settings_button_action()

                else:
                    reply = QMessageBox.question(
                        None,
                        "Warning",
                        "This Key is not included in the dictionary. Would you like to add it to the dictionary?",
                        QMessageBox.Yes,
                        QMessageBox.No,
                    )

                    if reply == QMessageBox.Yes:
                        self.add_item_settings_button()
                    else:
                        pass
        except:
            self.log.error(
                "It seems you are trying to change nothing. Welcome to the club Bro."
            )

    def remove_item_settings_button(self, kwargs=None):
        try:
            if (
                self.data_ui.key_edit_2.text()
                in self.variables.default_values_dict[
                    self.variables.default_values_dict["settings"][
                        "current_selected_browser_value"
                    ]
                ]
            ):
                reply = QMessageBox.question(
                    None,
                    "Warning",
                    "Are you sure to remove the selected item?",
                    QMessageBox.Yes,
                    QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    self.variables.default_values_dict[
                        self.variables.default_values_dict["settings"][
                            "current_selected_browser_value"
                        ]
                    ].pop(self.data_ui.key_edit_2.text(), None)
                    self.reload_settings_button_action()
            else:
                QMessageBox.question(
                    None,
                    "Warning",
                    "Hold on there Pirate!!! You try to delete an element which does not exist.",
                    QMessageBox.Ok,
                )
        except:
            self.log.error(
                "You cannot delete nothing... Please select first a value to delete."
            )

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
                return str(self.variables.default_values_dict["settings"][sub][key])
            except KeyError as e:
                return "An key error occured: " + str(e)

        elif parent.upper() == "SWITCHING":
            try:
                return str(self.variables.default_values_dict["Switching"][sub][key])
            except KeyError as e:
                return "An key error occured: " + str(e)

        # TODO: pad files currently not accessible due to spaces
        elif (
            parent.upper() == "PAD"
            or parent.upper() == "PAD FILES"
            or parent.upper() == "PAD FILE"
        ):
            try:
                return str(self.variables.additional_files["Pad_files"][sub][key])
            except KeyError as e:
                return "An key error occured: " + str(e)

        else:
            return "Could not interpret input."
