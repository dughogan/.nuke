#!/usr/bin/env python

#----------------------------------------------------------------------------#
#------------------------------------------------------------ HEADER_START --#

"""
@newField description: Description
@newField departments: Departments
@newField applications: Applications

@author:
    tnakamura

@organization:
    Reel FX Creative Studios

@description:
    UI for importing an animated camera (instance) with context selected by the user.

@departments:
    - lighting and composite

@applications:
    - nuke

"""
#----------------------------------------------------------------------------#
#-------------------------------------------------------------- HEADER_END --#

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- IMPORTS --#
from operator import itemgetter
from PyQt4 import QtGui
from PyQt4 import QtCore

import nuke
from nuke_tools import node_utils
from nuke_tools import camera_utils

from ui_lib.window import RWindow
from app_manager.session_manager import SessionManager
from pipe_core.model.pipe_obj import Project

from pipe_api.env import ENV
from pipe_api.controller import Creator

from pipe_utils.io import IO

from ui_lib.utils import set_expanding, get_dark_color_scheme
from ui_lib.dialogs import popup
from ui_lib.widgets.frame import HLine
from ui_lib.inputs.pipe_context_input import RPipeContextInput

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- GLOBALS --#

TOOL_TITLE = 'Import Camera Cache'
LABEL_NAME = 'Name: '
LABEL_CONTEXT = 'Context: '

LABEL_VERSION = 'Version: '
DEFAULT_CAMERA = 'Camera'
LABEL_SELECT_OPTION = 'Select camera(s) after imported.'
LABEL_LATEST = ' (latest)'

LABEL_CURRENT = '(current)'
NO_CONTEXT = ''
NO_CAMERA_FOUND = '(NO CAMERA FOUND WITH THE SELECTION.)'
LABEL_INSTRUNCTION = 'Check camera(s) to import below:'
LABEL_LOAD_CHECKBOX = 'Load'

CONTEXT_ASSET = 'Asset'
CONTEXT_SHOT = 'Shot'
CONTEXT_SEQUENCE = 'Sequence'
CONTEXT_CYCLE = 'Cycle'
CONTEXT_ASSEMBLY = 'Assembly'

KEY_CAMERA_INSTANCE = 'camera_instance'
KEY_CAMERA_NAME = 'camera_name'
KEY_CAMERA_VERSION = 'camera_version'

KEY_WIP_OWNER = 'wip_owner'
KEY_WIP = 'wip'


#----------------------------------------------------------------------------#
#--------------------------------------------------------------- FUNCTIONS --#

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- CLASSES --#

class ImportCamera(RWindow):
    """
    UI for importing cameras with the database..
    """
    SINGLETON = None

    def __init__(self):

        self.pipe_ctx = None
        self.project_id = None
        self.get_current_project()
#        ui.loadPlugin()
        self.user_context = None
        if self.pipe_ctx.is_asset():
            self.user_context = CONTEXT_ASSET
        elif self.pipe_ctx.is_shot():
            self.user_context = CONTEXT_SHOT
        elif self.pipe_ctx.is_sequence():
            self.user_context = CONTEXT_SEQUENCE
        elif self.pipe_ctx.is_cycle():
            self.user_context = CONTEXT_CYCLE
        elif self.pipe_ctx.is_assembly():
            self.user_context = CONTEXT_ASSEMBLY
        if self.user_context and self.pipe_ctx.pipe_obj_exists():
            super(ImportCamera, self).__init__()
            self.pipe_object = self.pipe_ctx.get_pipe_obj()
            if not self.initUI():
                self.__class__.SINGLETON = self
                return
        FAILURE_MSG = 'Failure: No context could be found.'
        popup.show_error(FAILURE_MSG, TOOL_TITLE)
        IO.print_system(FAILURE_MSG)

    def get_current_project(self):
        """
        Get the current project id.
        """
        self.pipe_ctx = ENV.get_pipe_context()
        if self.pipe_ctx:
            self.project_id = self.pipe_ctx.project
        return

    def on_import_button_clicked(self):
        """
        Callback function when import camera button is clicked on the UI.
        """
        if not self.camera_list:
            return
        selection = (self.select_option_cb.checkState() == QtCore.Qt.Checked)
        imported_node = []
        for checkbox in self.checkbox_widgets:
            if not checkbox.checkState() == QtCore.Qt.Checked:
                continue

            # Get camera instance and version number to import
            checkbox_dict = self.checkbox_widgets[checkbox]
            camera_instance = checkbox_dict[KEY_CAMERA_INSTANCE]
            selected_version = checkbox_dict[KEY_CAMERA_VERSION].currentText()
            top_node = None
            if str(selected_version).endswith(LABEL_LATEST):
                selected_version = str(selected_version).split()[0]
            """
            Import Camera Animation with the namespace
            """
            # Get the name and context of the camera animation
            namespace = str(camera_instance.name)
            context_name = 'No Ctx'
            if self.pipe_object:
                context_name = self.pipe_object.name

            camera_utils.import_camera_data(camera_instance, context_name, selected_version)

        self.close()
        return

    def set_type_of_context_object(self, reset=False):
        pipe_obj = self.pipe_object
        context = self.get_selected_context()
        if context == CONTEXT_ASSET:
            if reset:
                self.ctx_name_label.setText('')
            else:
                self.ctx_name_label.setText(' Type: '+pipe_obj.type.name)
        elif context == CONTEXT_ASSEMBLY:
            if reset:
                self.ctx_name_label.setText('')
            else:
                self.ctx_name_label.setText(' Type: '+pipe_obj.type.name)
        elif context == CONTEXT_SHOT:
            if reset:
                self.ctx_name_label.setText('')
            else:
                sequence_obj = pipe_obj.sequence
                self.ctx_name_label.setText(' Seq: '+sequence_obj.name)
        else:
            # Nothing for Cycle yet
            return

    def set_pipe_object(self, pipe_obj):
        if pipe_obj and pipe_obj != self.pipe_object:
            self.pipe_object = pipe_obj
            self.set_type_of_context_object()
            self.model_label.setText(pipe_obj.name)
            self._camera_table = self._build_versioned_camera_selector()
            self._scroll_area.setWidget(self._camera_table)
            print ("set_pipe_object: %s" % self.pipe_object.name)
        return

    def on_cancel_button_clicked(self):
        self.close()

    def remove_camera(self, name):
        """
        Removed the camera rig reference as well as its namespace.
        This removes all the objects under the namespace, too.
        """
        camera_rigs = cmds.ls(type=STEREO_RIG_TRANSFORM)
        for camera_node in camera_rigs:
            if (camera_node.startswith(name) and
                cmds.referenceQuery(camera_node, isNodeReferenced=True)):
                file_name = cmds.referenceQuery(camera_node, filename=True)
                cmds.file(file_name, removeReference=True)
                if cmds.namespace(exists=name):
                    objs = cmds.ls(name+':*')
                    if objs:
                        cmds.delete(objs)
                    cmds.namespace(removeNamespace=name)

    def select_option_changed(self):
        sender = self.sender()
        if not isinstance(sender, QtGui.QCheckBox):
            return
        if sender.checkState() == QtCore.Qt.Checked:
            self.select_option_label.setEnabled(True)
            return
        self.select_option_label.setEnabled(False)


    def checkbox_state_changed(self):
        """
        Callback function when checkbox is clicked on the UI.
        """
        sender = self.sender()
        if not isinstance(sender, QtGui.QCheckBox):
            return

        # Handle checkbox for each camera cache
        checkbox_dict = self.checkbox_widgets.get(sender, None)
        if sender.checkState() != QtCore.Qt.Checked:
            checkbox_dict[KEY_CAMERA_VERSION].setEnabled(False)
            return
        camera_name = checkbox_dict[KEY_CAMERA_NAME]
        checkbox_dict[KEY_CAMERA_VERSION].setEnabled(True)

        return

    def collect_camera(self):
        """
        Create the list of all versions for each camera anim objects.
        """
        self.camera_list = {}
        camera_instances = self.pipe_object.camera_instances.all()
        for instance in camera_instances:
            if not instance.active:
                continue
            camera_anim = instance.get_camera_anim(True)
            # Add all camera to the list
            version_list = []
            value = {}
            wip = None
            if camera_anim:
                wip = camera_anim.wip
                version_list = [x.number for x in camera_anim.versions.get_all()]
                version_list.sort(reverse=True)
            value[KEY_CAMERA_NAME] = str(instance.name)
            value[KEY_WIP] = wip
            value[KEY_CAMERA_VERSION] = version_list
            if wip:
                value[KEY_WIP_OWNER] = wip.name
            else:
                value[KEY_WIP_OWNER] = None
            self.camera_list[instance] = value
        return

    def set_camera_instance_name(self):
        """
        Based on the name of the camera, create name of a new instance.
        """
        camera_name = self.creating_camera_name
        self.camera_instance_name = camera_name
        if not isinstance(camera_name, str):
            self.camera_instance_name = DEFAULT_CAMERA
            return

        # Get all camera instances with the camera in this project
        camera_instances = []
        for camera in self.project_cameras:
            if camera.name == camera_name:
                camera_instances = camera.instances.all()
                break

        # Create a name for a new camera
        instance_names_list = \
            [x.name for x in camera_instances]
        if not instance_names_list:
            self.camera_instance_name += '1'
            return
        selected_list = \
            [x for x in instance_names_list if x.startswith(camera_name)]
        if not selected_list:
            self.camera_instance_name += '1'
            return
        postfix_list = []
        for item in selected_list:
            postfix = item[len(camera_name):]
            try:
                postfix_list.append(int(postfix))
            except ValueError:
                pass
        if not postfix_list:
            self.camera_instance_name += '1'
            return
        postfix_list.sort()
        self.camera_instance_name +=str(postfix_list[-1]+1)
        return

    def get_selected_context(self):
        if self.context_combo:
            return self.context_combo.currentText()
        else:
            return NO_CONTEXT

    """
    Create the table to select a camera to import.
    Similar to the one on reflex UI.
    """

    def _build_versioned_camera_selector(self):
        self.collect_camera()
        sorted_camera_list = sorted(self.camera_list.keys(),
                                    key=itemgetter('name'))
        """
        If no camera found, just show the message instead of the table
        """

        if self._camera_table is None:
            self._camera_table = QtGui.QTableWidget()
        table = self._camera_table

        if not sorted_camera_list:
            table.setRowCount(1)
            table.setColumnCount(1)
            name_item = QtGui.QTableWidgetItem(NO_CAMERA_FOUND)
            table.setItem(0, 0, name_item)
            return table

        """
        Create the table to list camera, its versions and wip name.
        """
        self.checkbox_widgets = {}
        table.setRowCount(len(sorted_camera_list))
        table.setColumnCount(4)

        # set header settings
        #
        table.setHorizontalHeaderLabels(['Camera Name', 'Version', 'WIP', 'Load'])
        horizontal_header = table.horizontalHeader()
        horizontal_header.setClickable(False)
        horizontal_header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        # set selection settings
        #
        table.setSelectionMode(table.NoSelection)

        # populate cells
        #
        for row, instance in enumerate(sorted_camera_list):
            labels = self.camera_list[instance]

            # Add a combo box for each camera to pic a version to export
            version_combo = QtGui.QComboBox(table)
            version_list = labels[KEY_CAMERA_VERSION]
            for version in version_list:
                if version == version_list[0]:
                    version = str(version)+LABEL_LATEST
                version_combo.addItem(str(version))

            version_item = QtGui.QTableWidgetItem()
            version_item.setFlags(QtCore.Qt.NoItemFlags)
            name_item = QtGui.QTableWidgetItem(instance.name)

            #
            # Add the name label and the version combo box
            table.setItem(row, 0, name_item)
            table.setItem(row, 1, version_item)
            table.setCellWidget(row, 1, version_combo)

            # Add a wip name
            wip_owner = str(labels[KEY_WIP_OWNER])
            wip_item = QtGui.QTableWidgetItem(wip_owner)
            table.setItem(row, 2, wip_item)

            # Add a checkbox for loading
            checkbox_item = QtGui.QTableWidgetItem()
            #checkbox_item.setCheckState(QtCore.Qt.Unchecked)
            table.setItem(row, 3, checkbox_item)
            checkbox = QtGui.QCheckBox()#LABEL_LOAD_CHECKBOX)
            checkbox.stateChanged.connect(self.checkbox_state_changed)
            table.setCellWidget(row, 3, checkbox)

            # Create a dictionary for each camera
            checkbox_dict = {}
            checkbox_dict[KEY_CAMERA_INSTANCE] = instance
            checkbox_dict[KEY_CAMERA_NAME] =  str(labels[KEY_CAMERA_NAME])
            checkbox_dict[KEY_CAMERA_VERSION] = version_combo
            checkbox_dict[KEY_CAMERA_VERSION].setEnabled(False)
            self.checkbox_widgets[checkbox] = checkbox_dict

        # resize cells
        #
        table.resizeRowsToContents()
        table.resizeColumnToContents(0)
        if table.columnWidth(0) < 100:
            table.setColumnWidth(0, 100)
        table.setColumnWidth(1, 70) # VERSION
        table.setColumnWidth(3, 50) # Check

        # resize table
        #
        table_height = table.horizontalHeader().sizeHint().height()
        table_height += table.frameWidth()*2
        for row in range(table.rowCount()):
            table_height += table.rowHeight(row)

        return table

    def on_context_changed(self, ctx):
        pipe_obj = ctx.get_pipe_obj()
        if not pipe_obj:
            FAILURE_MSG = 'Failure: No pipe object could be found.'
            popup.show_error(FAILURE_MSG, TOOL_TITLE)
            IO.print_system(FAILURE_MSG)
            return
        self.pipe_object = pipe_obj
        self._camera_table = self._build_versioned_camera_selector()
        return

    def initUI(self):

        self.model_name = None

        self.ctx_name_label = QtGui.QLabel()
        self.camera_grid = None
        self._camera_table = None
        self._scroll_area = None

        self.camera_name = ''
        self.camera_instance = None
        self.camera_anim = None
        self.camera_anim_versions = None
        self.version_index = {}

        self.camera_combo = None
        self.creating_camera_name = None
        self.namespace_line = None

        self._camera_table = self._build_versioned_camera_selector()
        self._camera_table.setAlternatingRowColors(True)
        p = self._camera_table.palette()
        p.setColor(QtGui.QPalette.Base, QtGui.QColor('#444444'))
        p.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor('#3d3d3d'))
        self._camera_table.setPalette(p)
        set_expanding(self._camera_table, True, True)

        vbox = QtGui.QVBoxLayout(self)
        frame, ctx_input = RPipeContextInput.new_framed(None, vbox, use_disc=False,
                                                        callback=self.on_context_changed)
        frame.setFixedHeight(frame.sizeHint().height())
        vbox.addWidget(frame)
        label_instrunction = QtGui.QLabel(LABEL_INSTRUNCTION)
        vbox.addWidget(label_instrunction)
        vbox.addWidget(self._camera_table)

        hbox2 = QtGui.QHBoxLayout()
        self.select_option_label = QtGui.QLabel(LABEL_SELECT_OPTION)
        self.select_option_cb = QtGui.QCheckBox()
        hbox2.addWidget(self.select_option_cb)
        hbox2.addWidget(self.select_option_label)
        self.select_option_cb.stateChanged.connect(self.select_option_changed)
        self.select_option_cb.setChecked(True)

        export_button = QtGui.QPushButton("Import")
        export_button.clicked.connect(self.on_import_button_clicked)
        cancel_button = QtGui.QPushButton("Cancel")
        cancel_button.clicked.connect(self.on_cancel_button_clicked)
        hbox0 = QtGui.QHBoxLayout()
        hbox0.addStretch(1)
        hbox0.addWidget(export_button)
        hbox0.addWidget(cancel_button)
        vbox.addLayout(hbox2)
        vbox.addLayout(hbox0)
        hline = HLine()

        self.setWindowTitle(str(TOOL_TITLE))
        self.setGeometry(300, 300, 512, 512)
        self.setMinimumSize(400, 500)
        self.show()

        return

def run():
    """
    run is the main starting function that invokes UI
    """

    if ImportCamera.SINGLETON is not None:
        if ImportCamera.SINGLETON.isVisible():
            ImportCamera.SINGLETON.activateWindow()
            ImportCamera.SINGLETON.raise_()
            return
        else:
            ImportCamera.SINGLETON = None
    ImportCamera().start()

if __name__ == '__main__':
    run()
