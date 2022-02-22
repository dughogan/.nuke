#!/usr/bin/python

#----------------------------------------------------------------------------#
#------------------------------------------------------------------ HEADER --#

"""
@author:
    dhogan

@description:
    Allows users to create toolset directories using a UI.
"""

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- IMPORTS --#

# built-in
import sys
import os
import shutil
import glob

# third-party
from PyQt4 import QtCore, QtGui

# external
from path_lib import get_path, join
from pipe_core import PipeContext, Project
from ui_lib.window import RWindow
from pipe_utils.system_utils import SYS_INFO, get_home
from pipe_utils.response import Success
from pipe_utils.file_system import (safe_make_dir, delete_any,
                                    stomp_copy, copy_dir)

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- CLASSES --#

class ToolsetManager(RWindow):
    """
    Toolset directory creator and remover.
    """
    def __init__(self, *kws):
        """
        Constructor
        """
        # create window
        super(ToolsetManager, self).__init__()
        self.setWindowTitle("ToolSet Manager")

        self.user_dir = get_home()
        nuke_ver = PipeContext.from_env().get_pipe_obj().software.nuke_version
        platform_ver = SYS_INFO.platform_dir
        root_path = get_path('co_plugin_type_dir',
                             app_name='nuke',
                             plugin_type='toolsets',
                             version=nuke_ver.name)
        self.toolset_path = root_path + "/ToolSets/"

        self.edit = QtGui.QLineEdit("Name of ToolSet")
        self.instructions = QtGui.QLabel("Please choose which file you'd like"
                                   " to share and which shared ToolSet you'd"
                                   " like to copy it to, then press 'Copy"
                                   " to Shared ToolSet Directory'.")
        self.shared_toolsets_label =  QtGui.QLabel("Shared Toolsets")
        self.toolsets = QtGui.QListWidget()

        self.nuke_files_label = QtGui.QLabel("Local ToolSet Nuke Files")
        self.nuke_files = QtGui.QListWidget()
        self.nuke_files.setSelectionMode(2)

        # list toolsets
        shared_toolset_dir = glob.glob('/code/global/nuke/toolsets/*/ToolSets/*')
        for directory in shared_toolset_dir:
            toolset = directory.rpartition('/')[2]
            toolset = QtGui.QListWidgetItem(toolset)
            self.toolsets.addItem(toolset)

        # local nuke files
        user_dir = get_home()
        local_toolset_nuke_files = glob.glob(user_dir + '/.nuke/ToolSets/*')
        for nuke_file in local_toolset_nuke_files:
            toolset_path = nuke_file.rpartition('/')[2]
            toolset = QtGui.QListWidgetItem(toolset_path)
            if not toolset_path.endswith(".nk"):
                toolset.setForeground(QtCore.Qt.red)
            self.nuke_files.addItem(toolset)

        # buttons
        self.make_button = QtGui.QPushButton("Make ToolSet")
        self.remove_button = QtGui.QPushButton("Remove ToolSet")
        self.remove_nuke_file_button = QtGui.QPushButton("Remove Nuke Files")
        self.copy_button = QtGui.QPushButton("Copy to Shared ToolSet Directory")
        self.clear_toolset_button = QtGui.QPushButton("Clear")
        self.clear_toolset_button.setFixedWidth(100)
        self.clear_nuke_file_button = QtGui.QPushButton("Clear")
        self.clear_nuke_file_button.setFixedWidth(100)

        # main layout
        main_layout = QtGui.QGridLayout()
        main_layout.setColumnMinimumWidth(1, 500)
        self.setLayout(main_layout)

        # new toolset name
        toolset_name = QtGui.QVBoxLayout()
        toolset_name.addWidget(self.edit)
        main_layout.addLayout(toolset_name, 1, 1)

        # top buttons
        top_buttons = QtGui.QHBoxLayout()
        top_buttons.addWidget(self.make_button)
        top_buttons.addWidget(self.remove_button)
        top_buttons.addWidget(self.clear_toolset_button)
        main_layout.addLayout(top_buttons, 2, 1)

        # shared toolsets
        shared_toolsets_layout = QtGui.QVBoxLayout()
        shared_toolsets_layout.addWidget(self.shared_toolsets_label)
        shared_toolsets_layout.addWidget(self.toolsets)
        main_layout.addLayout(shared_toolsets_layout, 3, 1)

        # nuke file buttons
        nuke_file_buttons = QtGui.QHBoxLayout()
        nuke_file_buttons.addWidget(self.remove_nuke_file_button)
        nuke_file_buttons.addWidget(self.clear_nuke_file_button)
        main_layout.addLayout(nuke_file_buttons, 4, 1)

        # nuke files list and final buttons
        nuke_files_layout = QtGui.QVBoxLayout()
        nuke_files_layout.addWidget(self.nuke_files_label)
        nuke_files_layout.addWidget(self.nuke_files)
        nuke_files_layout.addWidget(self.instructions)
        nuke_files_layout.addWidget(self.copy_button)
        main_layout.addLayout(nuke_files_layout, 5, 1)

        # button signals
        self.make_button.clicked.connect(self._make_new_toolset)
        self.remove_button.clicked.connect(self._remove_toolset)
        self.remove_nuke_file_button.clicked.connect(self._remove_nuke_file)
        self.copy_button.clicked.connect(self._copy_nuke_toolset_file)
        self.clear_toolset_button.clicked.connect(lambda: self._clear(self.toolsets))
        self.clear_nuke_file_button.clicked.connect(lambda: self._clear(self.nuke_files))

    def _make_new_toolset(self):
        """
        Makes toolset directory.
        """
        toolset = self.edit.text()
        if toolset == "Name of ToolSet":
            return None

        toolset_dir = self.toolset_path + self.edit.text()
        safe_make_dir(str(toolset_dir), True)
        self.toolsets.addItem(toolset)
        return Success("Toolset '" + str(toolset) + "' created.")

    def _remove_toolset(self):
        """
        Removes toolset directory.
        """
        warning = QtGui.QMessageBox.warning(self, "Warning",
                                            "You're about to delete a ToolSet, "
                                            "are you sure you want to do this?",
                                            QtGui.QMessageBox.Ok,
                                            QtGui.QMessageBox.Cancel)
        if warning == QtGui.QMessageBox.Ok:
            selected_toolset = self.toolsets.currentItem().text()
            toolset_dir_path = self.toolset_path + selected_toolset
            delete_any(str(toolset_dir_path))
            for selected_item in self.toolsets.selectedItems():
                self.toolsets.takeItem(self.toolsets.row(selected_item))

            return Success("Toolset '" + str(selected_toolset) + "' removed.")

    def _remove_nuke_file(self):
        """
        Removes nuke files from ToolSet directory.
        """
        warning = QtGui.QMessageBox.warning(self, "Warning",
                                            "You're about to delete nuke files, "
                                            "are you sure you want to do this?",
                                            QtGui.QMessageBox.Ok,
                                            QtGui.QMessageBox.Cancel)
        if warning == QtGui.QMessageBox.Ok:
            for selected_item in self.nuke_files.selectedItems():
                nuke_file_path = str(self.user_dir + '/.nuke/ToolSets/' +
                                     selected_item.text())
                delete_any(str(nuke_file_path))
                self.nuke_files.takeItem(self.nuke_files.row(selected_item))

            return Success("Nuke files removed")

    def _copy_nuke_toolset_file(self):
        """
        Copies a local .nk ToolSet file to a shared ToolSet directory.
        """
        try:
            selected_nuke_file = self.nuke_files.currentItem().text()
        except AttributeError:
            warning = QtGui.QMessageBox.information(self, "OOPS!",
                                                    "No Nuke File Selected.",
                                                    QtGui.QMessageBox.Ok,)
            return warning
        try:
            selected_toolset = self.toolsets.currentItem().text()
        except AttributeError:
            warning = QtGui.QMessageBox.information(self, "OOP!",
                                                    "No ToolSet Dir Selected.",
                                                    QtGui.QMessageBox.Ok,)
            return warning

        toolset_dir_path = str(self.toolset_path + selected_toolset + "/")
        for selected_item in self.nuke_files.selectedItems():
            nuke_file_path = str(self.user_dir + '/.nuke/ToolSets/'
                                 + selected_item.text())
            if not nuke_file_path.endswith('.nk'):
                warning = QtGui.QMessageBox.warning(self, "Warning",
                                            "You're about to copy a ToolSet "
                                            "directory, are you sure you "
                                            "want to do this?",
                                            QtGui.QMessageBox.Ok,
                                            QtGui.QMessageBox.Cancel)
                if warning == QtGui.QMessageBox.Ok:
                    copy_dir(nuke_file_path, toolset_dir_path)
                    QtGui.QMessageBox.information(self, "COPIED",
                                                  "Your ToolSet Directory has "
                                                  "been copied to: " +
                                                  str(toolset_dir_path),
                                                  QtGui.QMessageBox.Ok)
            else:
                stomp_copy(nuke_file_path, toolset_dir_path)
                QtGui.QMessageBox.information(self, "COPIED",
                                              "Your Nuke files have "
                                              "been copied to: " +
                                              str(toolset_dir_path),
                                              QtGui.QMessageBox.Ok)

    def _clear(self, widget):
        """
        Clear selection in widget.
        """
        for index in xrange(widget.count()):
            item = widget.item(index)
            widget.setItemSelected(item, False)

def main():
    """
    Show window.
    """
    window = ToolsetManager()
    window.launch()

if __name__ == '__main__':
    main()
