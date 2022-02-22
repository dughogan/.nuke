#!/usr/bin/env python

"""
@author:
    - tpitts

@description:
    Build shot GUI for Nuke.

@applications
    - nuke

"""

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- IMPORTS --#
# built-in
from PyQt4 import QtGui, QtCore
import xml.etree.ElementTree as ET
import os, sys

# internal
from nuke_tools.build_shot import build_shot

# external
from app_manager.wip_manager import WipManager

from pipe_api.env import get_pipe_context

from pipe_core.pipe_enums import Discipline
from pipe_core.pipe_context import WipContext

from pipe_utils.system_utils import SYS_INFO, OS
from pipe_utils.response import Failure
from pipe_utils.io import IO

from ui_lib.dialogs import popup
from ui_lib.qt_manager import QtManager
from ui_lib.utils import get_dark_color_scheme
from ui_lib.utils import get_icon
from ui_lib.window import RWindow

'''
# third party
import nuke

# internal
from nuke_tools import utils as nuke_utils
from nuke_tools import node_utils

# external

from pipe_core.pipe_enums import Discipline
from pipe_core.model.wip_output_types import WipOutputType
from pipe_utils.response import Success, Failure
'''
#----------------------------------------------------------------------------#
#--------------------------------------------------------------- FUNCTIONS --#
def _pipe_obj_sort(a,b):
    """
    Sorts Sequence Pipe Objects with numeric sequences first followed by
    alphanumeric ones.
    """
    aName = a.name
    bName = b.name
    if aName.isdigit():
        if bName.isdigit():
            results = cmp(int(aName),int(bName))
        else:
            results = -1
    elif bName.isdigit():
        results = 1
    else:
        results = cmp(aName,bName)
    return results

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- CLASSES --#
class NukeBuildShot(RWindow):

    SINGLETON = None

    PREF_NAME = 'nuke_build_shot'

    WIP_NAME = 'master'

    #-------------------------------------------------------------------------
    #------------------------------------------------------------------ Init()
    def __init__(self, **kws):

        #-- Get pipe context and pipe objects
        self.pipe_ctx = get_pipe_context()

        self.project_object = self.pipe_ctx.get_project_obj()
        project_name = self.project_object.name

        self.path_ctx = self.pipe_ctx.get_path_context()

        self.seq_obj = self.pipe_ctx.get_sequence_obj()

        self.shot_obj = self.pipe_ctx.get_shot_obj()

        self.wip_obj = None
        self.vers_obj = None
        self.vers = None

        if self.shot_obj is not None:

            #-- Get the WIP object.
            self.wip_obj = self.pipe_ctx.get_wip_obj()

            #-- If no WIP object, then the user opened Nuke with the
            #-- discipline selected.

            self.open_wip = True

            if self.wip_obj is None:

                print "Defaulting to 'master' WIP."
                wip_manager = WipManager.instance()

                #-- Check for 'comp' WIP. Create it if needed, or grab latest
                #-- version.
                wips = self.shot_obj.find_wips(disc='comp', name='master')

                if len(wips) == 0:
                    response = wip_manager.create_wip(wip_name=self.WIP_NAME,
                                                          pipe_ctx=self.pipe_ctx)
                    if response:
                        self.wip_obj = response.payload.get_wip_obj()
                        self.open_wip = False
                    else:
                        return
                else:
                    self.wip_obj = wips[0]

                #-- Get the last version of the master WIP. If there are no
                #   versions, create the first WIP version.
                if len(self.wip_obj.versions) == 0:
                    path_ctx = self.wip_obj.get_path_context()
                    wip_ctx = WipContext.from_path_context(path_ctx)
                    response = wip_manager.version_up(wip_ctx=wip_ctx)
                    if response.is_success():
                        self.wip_obj = self.shot_obj.find_wips(disc='comp', name='master')[0]
                        self.vers_obj = self.wip_obj.versions.get_last()
                    else:
                        message = 'Could not create WIP version 1 for master'\
                            ' WIP.'
                        IO.error(message)
                        return Failure(message=message)
                else:
                    self.vers_obj = self.wip_obj.versions.get_last()
                self.vers = self.vers_obj.number

                #-- Get a new pipe context that reflects the new WIP

            #-- User selected a specific WIP and version, so we're going to use that.
            else:
                #-- Grab the latest version from the path context. If its not
                #-- there, get the last version.
                self.vers = self.path_ctx['version']
                if self.vers is None:
                    self.vers = self.wip_obj.versions.get_last().number
                self.vers_obj = self.wip_obj.versions.get(self.vers)
                self.open_wip = False

            self.path_ctx = self.vers_obj.get_path_context()
            self.pipe_ctx = WipContext.from_path_context(self.path_ctx)


        #---------------------------------------------------------------------
        #-------------------------------------------------------- Window Setup

        #-- Creates window.
        super(NukeBuildShot,self).__init__()
        self.SINGLETON = self
        self.setWindowTitle("Nuke Build Shot- %s" %project_name)
        self.setMinimumSize(300,300)

        self.set_icon(get_icon('rfx_logo.png', 32), 32)

        #---------------------------------------------------------------------
        #---------------------------------------------------- Horizontal Lines
        horiz_line0 = QtGui.QFrame()
        horiz_line0.setFrameStyle(QtGui.QFrame.HLine)

        main_layout = QtGui.QHBoxLayout(self)
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        #---------------------------------------------------------------------
        #-------------------------------------------------- Seq/Shot Selection

        seq_shot_group = QtGui.QGroupBox('Sequence/Shot/WIP (READ ONLY)')

        seq_shot_main = QtGui.QVBoxLayout()

        seq_shot_layout = QtGui.QHBoxLayout()

        #-- Seq/Shot Combo Boxes
        seq_lbl = QtGui.QLabel('Seq: ')
        self.sequence_txt = QtGui.QLineEdit('')
        shot_lbl = QtGui.QLabel('Shot: ')
        self.shot_txt = QtGui.QLineEdit('')

        #-- Make the shot/seq boxes read only
        self.sequence_txt.setReadOnly(True)
        self.shot_txt.setReadOnly(True)

        seq_shot_layout.addWidget(seq_lbl)
        seq_shot_layout.addWidget(self.sequence_txt)
        seq_shot_layout.addWidget(shot_lbl)
        seq_shot_layout.addWidget(self.shot_txt)

        #-- WIP/Vers Display Box
        wip_vers_layout = QtGui.QHBoxLayout()
        comp_wip_lbl = QtGui.QLabel('WIP/Version: ')
        self.comp_wip_txt = QtGui.QLineEdit()
        self.comp_wip_txt.setReadOnly(True)

        wip_vers_layout.addWidget(comp_wip_lbl)
        wip_vers_layout.addWidget(self.comp_wip_txt)

        seq_shot_main.addLayout(seq_shot_layout)
        seq_shot_main.addLayout(wip_vers_layout)

        seq_shot_group.setLayout(seq_shot_main)

        #---------------------------------------------------------------------
        #-------------------------------------------------- Read/Write Widgets
        read_write_group = QtGui.QGroupBox('Read/Write Settings')

        #-- WIP Selection
        wip_select_lbl = QtGui.QLabel('Select Lighting WIP to read passes from:')
        self.wip_combo_box = QtGui.QComboBox()

        #-- Save Setting Selection
        save_settings_lbl = QtGui.QLabel('How do you want to save?')
        self.save_combo_box = QtGui.QComboBox()
        save_options = ['Overwrite', 'Version Up', 'Don\'t Save']
        self.add_combo_items(self.save_combo_box, save_options)

        read_write_layout = QtGui.QVBoxLayout()
        read_write_layout.addWidget(wip_select_lbl)
        read_write_layout.addWidget(self.wip_combo_box)
        read_write_layout.addWidget(save_settings_lbl)
        read_write_layout.addWidget(self.save_combo_box)

        read_write_layout.addWidget(horiz_line0)

        read_write_group.setLayout(read_write_layout)

        #-- Cancel/Build Buttons
        go_group_layout = QtGui.QHBoxLayout()
        self.cancel_button = QtGui.QPushButton('Cancel')
        self.cancel_button.clicked.connect(self.cancel)
        self.build_button = QtGui.QPushButton('Build Shot')
        self.build_button.clicked.connect(self.build)

        go_group_layout.addWidget(self.build_button)
        go_group_layout.addWidget(self.cancel_button)

        #---------------------------------------------------------------------
        #----------------------------------------------------- Left Layout Org

        left_layout = QtGui.QVBoxLayout()
        left_layout.setAlignment(QtCore.Qt.AlignTop)

        left_layout.addWidget(seq_shot_group)
        left_layout.addWidget(read_write_group)
        left_layout.addLayout(go_group_layout)

        main_layout.addLayout(left_layout)

        #---------------------------------------------------------------------
        #------------------------------------------------ Fill Boxes and Lists

        self.fill_seq_shot()
        self.fill_wips()

    #-------------------------------------------------------------------------
    #----------------------------------------------------- Fill Seq/Shot Boxes
    def fill_seq_shot(self):

        cur_seq = ''
        cur_shot = ''
        seq_index = 0
        shot_index = 0

        if self.shot_obj is None:
            return Failure("Not in a sequence/shot context!")

        #-- Grab seq/shot names from path context.
        cur_seq = self.path_ctx['seq_name']
        cur_shot = self.path_ctx['shot_name']

        self.sequence_txt.setText(cur_seq)
        self.shot_txt.setText(cur_shot)

        #-- Since we locked down the seq/shot, we can assume the wip/version
        #-- won't be changing, so let's just let them use whatever wip they
        #-- want for now.

        #-- Grab WIP and latest version.

        #-- Set the display box to nothing.
        self.comp_wip_txt.setText('')

        wip_name = ''

        if self.wip_obj is not None and self.vers_obj is not None:
            wip_name = self.wip_obj.name + "_v%04d" % self.vers

        self.comp_wip_txt.setText(wip_name)


    #-------------------------------------------------------------------------
    #------------------------------------------------------ Fill WIP Combo Box
    def fill_wips(self):

        #-- Get the lighting WIPs for this shot and add them to the WIP
        #-- combo box.
        wip_list = []

        wips = self.shot_obj.find_wips(disc=Discipline.LIT).all()

        for w in wips:
            wip_list.append(w.name)

        wip_list.sort()

        self.add_combo_items(self.wip_combo_box, wip_list)

        if len(wip_list) == 0:
            self.build_button.setEnabled(False)
        else:
            self.build_button.setEnabled(True)


    def build(self):

        #-- Path to lit wip file to read passes from.

        #print self.shot_obj

        lit_wip_name = str(self.wip_combo_box.currentText())
        lit_wip_obj = self.shot_obj.find_wips(disc=Discipline.LIT, name=lit_wip_name).all()

        wip_path_ctx = lit_wip_obj[0].get_path_context()

        lit_wip_path = wip_path_ctx.get_path('sh_wip_dir')


        #-- Path to comp file to build.
        comp_path_ctx = self.vers_obj.get_path_context()
        comp_wip_path = comp_path_ctx.get_path('sh_wip_file')
        #print comp_wip_path

        #-- Save Mode.
        save_mode = str(self.save_combo_box.currentText())
        if save_mode == 'Overwrite':
            save_mode = 'overwrite'
        if save_mode == 'Version Up':
            save_mode = 'version'
        if save_mode == 'Don\'t Save':
            save_mode = 'pass'

        #-- Create .DAT File
        comp_dir = os.path.split(comp_path_ctx.get_path('sh_wip_file'))
        filename = comp_dir[1]
        file_pieces = filename.split('_')
        version = file_pieces[len(file_pieces)-1][:-3]
        dat_file_name = 'build_shot_%s.dat' % version
        dat_file_path = os.path.join(comp_dir[0], dat_file_name)
        #print "dat_file_path: ", dat_file_path

        dat_file = open(dat_file_path, 'w')
        dat_file.write('lit_wip_path: %s\n' % lit_wip_path)
        dat_file.write('comp_wip_file: %s\n' % comp_wip_path)
        dat_file.write('save_mode: %s\n' % save_mode)

        dat_file.close()

        kwargs = {}
        #kwargs['data_file'] = dat_file_path
        kwargs['lit_wip_path'] = lit_wip_path
        kwargs['comp_wip_file'] = comp_wip_path
        kwargs['save_mode'] = save_mode


        #-- Call build_shot() to run the actual build (in the scene).
        if self.open_wip:
            wip_manager = WipManager.instance()
            # response = wip_manager.open_wip_context(self.pipe_ctx)
            response = wip_manager.set_wip_context(self.pipe_ctx)

        rst_path = comp_path_ctx.get_path('sh_rst_file')
        if not os.path.isfile(rst_path):
            rst_dir_path = comp_path_ctx.get_path('sh_rst_dir')
            rst_files = []
            for dir_item in os.listdir(rst_dir_path):
                if os.path.splitext(dir_item)[1] == '.rsf':
                    rst_files.append(dir_item)
            choice_file = popup.show_options('Standard RST not found! Please '
                'choose one of the following below.', 'RST Error', rst_files)
            kwargs['rst_name'] = os.path.splitext(choice_file)[0]
        response = build_shot(**kwargs)

        if not response:
            popup.show_error(response.message, 'Build Shot- Error')

        self.close()

        #-- TODO: Set up build_shot to run in a background process for speed.

        #-- Set up a Nuke Executer

        #-- Fire off background process

        #-- Once background process is done, reload correct Nuke script.


    def cancel(self):
        self.close()



    #-------------------------------------------------------------------------
    #--------------------------------------------------------- Extra Functions

    #-- Convenience Function to add items to a combo box.
    def add_combo_items(self, *args):
        #print "\nin add combo items"
        combo_box = args[0]
        combo_box.clear()
        attrs = args[1]
        for item in attrs:
            #print "adding item: ", item
            combo_box.addItem(item)

def main():
    #-- Creates window.
    window = NukeBuildShot()
    window.launch()

#----------------------------------------------------------------------------------------#
#----------------------------------------------------------------------- DEFAULT START --#

if __name__ == "__main__":
    main()
