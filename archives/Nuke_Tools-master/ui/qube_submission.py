#!/usr/bin/python

"""
@author:
    mrowley

@description:
    Tools for submitting scripts to the farm


@ revision 08/26/2013
    rewrote original code to be more programmer-friendly. :)
"""

# built-in
import os
import re
import sys
import shutil
import pickle

# third-party
from PyQt4 import QtGui, QtCore
import nuke

# internal
from nuke_tools import render
from nuke_tools.batch.matte_plate_render import is_matte
from nuke_tools import node_utils
from nuke_tools.node_utils import get_comp_version

# external
from ui_lib.rnuke import old_widgets as nuke_gui
from ui_lib.window import RWindow
from pipe_api.env import get_pipe_context
from pipe_utils.sequence import FrameSet, FrameRange, FrameSequence
from pipe_core.pipe_enums import RenderVenue
from nuke_tools import node_utils as nu
from nuke_tools import script_utils as su
from pipe_utils.enumeration import Enum, EnumGroup
from pipe_utils.system_utils import get_user
from ui_lib.dialogs.popup import show_options

#----------------------------------------------------------------------------#
#--------------------------------------------------------------- FUNCTIONS --#

FILE = '/home/%s/.nuke_farm_prefs' % get_user()

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- CLASSES --#


class SubmitAction(EnumGroup):
    SUBMIT_MISSING_FRAMES = Enum(0, 'submit missing')
    SUBMIT = Enum(1, 'submit')
    CANCEL = Enum(2, 'cancel')


def save_gui_prefs(**prefs):
    """
    Save GUI preferences to file

    @param file: Path to the preference file
    @type file: str
    @param prefs: A dictionary keeps GUI preferences
    @type prefs: dict
    """
    if prefs is not None:
        file_id = open(FILE, 'w')
        pickle.dump(prefs, file_id)
        file_id.close()


def load_gui_prefs():
    """
    Load GUI preferences from file

    @param file: Path to the preference file
    @type file: str
    """
    root = nuke.toNode('root')
    start_frame = int(root['first_frame'].value())
    end_frame = int(root['last_frame'].value())
    frng = '%s-%s' % (start_frame, end_frame)
    default_prefs = {
        'cpus': 15,
        'f_range': frng,
        'chunksize': 2,
        'cache': 2650,
        'threads': 2,
        'wait_for': '',
        'retrywork': 2,
        'submit_blocked': False,
        'allow_local': False,
        'version_up': False,
        'heavy_render': False,
        #'motion_vector': False,
        'multiple_writes': False,
        'interactive': False,
        'label': '',
        'output': []
    }
    ## parse settings from previous run
    prefs_in_file = {}
    if os.path.exists(FILE):
        file_id = open(FILE, 'r')
        try:
            prefs_in_file = pickle.load(file_id)
        except:
            pass
        file_id.close()

    ## validate settings from previous run - or setup some defaults
    for key in default_prefs:
        if key in prefs_in_file:
            default_prefs[key] = prefs_in_file[key]

    # override the priority
    default_prefs['priority'] = 3000

    return default_prefs


class QubeGUI(RWindow):
    """
    Qube submission tool for Nuke
    """
    PREF_NAME = 'nuke_qube_submission'
    TITLE = 'Qube Submission'

    FRAME_VERSION_UP = 'Version Up Before Render'
    FRAME_OVERWRITE = 'Overwrite Frames'
    FRAME_DELETE = 'Delete Existing Frames'
    FRAME_CANCEL = 'Cancel Farm Submission'
    FRAME_MISSING = 'Render only missing frames'
    FRAME_OPTIONS = [FRAME_VERSION_UP, FRAME_OVERWRITE, FRAME_DELETE,
                     FRAME_CANCEL]

    def __init__(self, parent=None, pipe_ctx=None):
        RWindow.__init__(self, parent=parent)

        # get the pipe context
        self.pipe_ctx = pipe_ctx
        if self.pipe_ctx is None:
            self.pipe_ctx = get_pipe_context()

        # if not self.pipe_ctx.is_shot():
        #     raise Exception(
        #             '"%s" does not describe a shot context.' % self.pipe_ctx)

        # public members
        self.kwargs = {}
        self.sorted_to_del_frames = []
        self.sorted_missing_frames = []
        self.to_del_images = []
        self.submit_action = None
        self.submitter = False
        self.executer = None
        self.env = None
        self.root = nuke.toNode('root')

        # GUI
        self.setup_gui()

    def setup_gui(self):
        """
        Main UI for Qube Submission
        """
        self.main_layout = QtGui.QVBoxLayout(self)
        start_frame = int(self.root['first_frame'].value())
        last_frame = int(self.root['last_frame'].value())
        options = [{'Cpus': 15}, {'Priority': 3000}, {'Range': "%s-%s" % (
            start_frame, last_frame)}]
        self.option_widget = nuke_gui.RFXOptionListWidget(options, self)
        self.option_widget.widgets['Priority'].setRange(1, 4000)
        self.option_widget.widgets['Priority'].setSingleStep(100)
        self.option_widget.widgets['Cpus'].setMinimum(0)

        self.missing_frames_btn = \
            QtGui.QPushButton('Set Range to Missing Frames')
        self.missing_frames_btn.clicked\
            .connect(self.missing_frames_btn_clicked)

        # ADVANCED MENUS
        advanced_options = [{'ChunkSize':1}, {'Cache(mbs)':2650},
                            {'Threads':2}, {'Wait_For':''}, {'RetryWork':2}]
        self.advanced_option_widget = nuke_gui.RFXOptionListWidget(
            advanced_options, self)
        self.advanced_option_widget.widgets['ChunkSize'].setMinimum(1)
        self.advanced_option_widget.widgets['ChunkSize'].setMaximum(
            (last_frame - start_frame) + 1)
        self.advanced_option_widget.widgets['Cache(mbs)'].setRange(0, 2650)
        self.advanced_option_widget.widgets['Cache(mbs)'].setSingleStep(50)
        self.advanced_option_widget.widgets['Threads'].setMinimum(1)
        self.advanced_option_widget.widgets['Threads'].setMaximum(6)
        self.advanced_option_widget.widgets['RetryWork'].setMinimum(0)
        self.advanced_option_widget.widgets['RetryWork'].setMaximum(4)
        self.submit_blocked_checkbox = QtGui.QCheckBox('Submit Blocked', self)
        self.submit_local_checkbox = QtGui.QCheckBox('Submit Local', self)

        self.advanced_menu = nuke_gui.RFXCollapsibleWidget('Advanced Options',
                                                           self)
        self.advanced_menu.add_widget(self.advanced_option_widget)
        self.advanced_menu.add_widget(self.submit_blocked_checkbox)
        self.advanced_menu.add_widget(self.submit_local_checkbox)
        self.advanced_menu.show_button_clicked()

        self.submit_button = QtGui.QPushButton('Submit', self)
        self.close_button = QtGui.QPushButton('Close', self)
        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.addWidget(self.submit_button)
        self.button_layout.addWidget(self.close_button)

        self.auto_version_checkbox = QtGui.QCheckBox('Version Up', self)
        self.heavy_render_checkbox = QtGui.QCheckBox('Heavy Render', self)
        #self.motion_vector_checkbox = QtGui.QCheckBox('Motion Vector', self)
        self.submit_multi_checkbox = QtGui.QCheckBox('Multiple Writes', self)
        matte_nodes_exist = self.check_matte_nodes()
        if matte_nodes_exist:
            self.create_matte_plates = QtGui.QCheckBox('Create Matte Plates',
                                                       self)
        self.submit_interactive_checkbox = QtGui.QCheckBox(
            'Interactive License', self)
        self.submit_interactive_checkbox.setChecked(False)
        self.checkbox_1_layout = QtGui.QHBoxLayout()
        self.checkbox_1_layout.addWidget(self.auto_version_checkbox)
        self.checkbox_1_layout.addWidget(self.heavy_render_checkbox)
        if matte_nodes_exist:
            self.checkbox_1_layout.addWidget(self.create_matte_plates)
        #self.checkbox_1_layout.addWidget(self.motion_vector_checkbox)
        self.checkbox_2_layout = QtGui.QHBoxLayout()
        self.checkbox_2_layout.addWidget(self.submit_multi_checkbox)
        self.checkbox_2_layout.addWidget(self.submit_interactive_checkbox)

        self.input_layout = QtGui.QHBoxLayout()
        self.input_text = QtGui.QLabel('Job Label', self)
        self.input_name = QtGui.QLineEdit(self)
        self.input_layout.addWidget(self.input_text)
        self.input_layout.addWidget(self.input_name)

        self.main_layout.addWidget(self.option_widget)
        self.main_layout.addWidget(self.missing_frames_btn)
        self.main_layout.addLayout(self.checkbox_1_layout)
        self.main_layout.addLayout(self.checkbox_2_layout)
        self.main_layout.addLayout(self.input_layout)
        self.main_layout.addWidget(self.advanced_menu)
        self.main_layout.addLayout(self.button_layout)

        self.setLayout(self.main_layout)
        self.start()

        self.close_button.clicked.connect(self.save_prefs_and_exit)
        self.submit_button.clicked.connect(self.pre_submit)
        self.resize(self.sizeHint())

        #self.read_prefs()

    def check_matte_nodes(self):
        """
        Checks to see if any matte painting nodes exist in the current scene.
        """
        all_nodes = nuke.allNodes()
        matte_nodes = filter(is_matte, all_nodes)
        if len(matte_nodes) > 0:
            return True
        else:
            return False

    def missing_frames_btn_clicked(self):
        missing = su.find_missing_comp_frames()
        frames = self._get_missing_frames_text(missing)
        if frames:
            self.option_widget.widgets['Range'].setText(frames)

    def _get_missing_frames_text(self, missing_dict):
        if isinstance(missing_dict, dict) and len(missing_dict) > 0:
            frame_ranges = []
            for eye_frames in missing_dict.itervalues():
                for fr in eye_frames:
                    frame_ranges.append(FrameRange(fr[0], fr[1]))
            fr_set = FrameSet()
            fr_set.set_ranges(frame_ranges)
            frame_ranges = fr_set.ranges
            frames = []
            for frame_range in frame_ranges:
                frames.append('{0}-{1}'.format(frame_range.start,
                                               frame_range.end))
            frames = ','.join(frames)
            return frames
        else:
            return None

    def pre_submit(self):
        """
        Retrieve arguments to pass to submission function and then submit
        """
        # get the args from the main UI
        self.kwargs = self.get_parameters()

        # set up write nodes
        result = self.check_write_nodes()
        if result is False:
            return

        # set up frame ranges
        self.setup_frame_ranges()
        self.remove_existing_frames()

        # submit
        submitter = None

        # Check if frames already exist and prompt user if they do
        option = self.check_frames_exist(self.kwargs['frame_sets'].numbers)
        if option == self.FRAME_CANCEL:
            self.close()
            return
        elif option == self.FRAME_DELETE:
            pipe_obj = self.pipe_ctx.get_pipe_obj()
            ext = pipe_obj.cinema.comp_format.extension
            version = get_comp_version()
            path_ctx = self.pipe_ctx.get_path_context()

            # for normal write nodes
            writes = node_utils.get_all_nodes('Write', True, False)
            ordered_writes = sorted(writes, key=lambda x: x['render_order'].value())

            for number in self.kwargs['frame_sets'].numbers:
                for node in ordered_writes:
                    write_name = node['name'].value()
                    regex = re.search("rfxw", write_name, re.I)

                    if not regex:
                        write = nuke.toNode(node['name'].value())
                        version = exr_path.split('/')[-2]
                        path = write['file'].getValue()
                        nuke_path = re.sub('%v', version, path)
                        frame_sequence = FrameSequence(nuke_path)
                        frame_path = frame_sequence.get_frame(number).path
                        os.remove(frame_path)
                    else:
                        for eye in ['l', 'r']:
                            nuke_path = path_ctx.get_path('sh_comp_wip_output_file',
                                                          version=version, eye=eye,
                                                          ext=ext, namespace='shot')

                            frame_sequence = FrameSequence(nuke_path)
                            frame_path = frame_sequence.get_frame(number).path
                            try:
                                os.remove(frame_path)
                            except OSError:
                                continue

        elif option == self.FRAME_VERSION_UP:
            su.version_up()
            self.pipe_ctx = get_pipe_context()
        elif re.match('^{0}.*$'.format(self.FRAME_MISSING),
                      option):
            missing = su.find_missing_comp_frames()
            frame_set = self._get_missing_frames_text(missing)
            self.kwargs['frame_sets'] = FrameSet.parse(frame_set)
            # frame_range only used for storage purposes
            self.kwargs['frame_range'] = frame_set
            self.kwargs['f_range'] = self.kwargs['frame_range']
        # print results
        if self.submit_action != SubmitAction.CANCEL:
            submitter = render.submit(self.pipe_ctx, RenderVenue.FARM,
                                      **self.kwargs)
            self.show_results(submitter)
            self.close()

        # version up if the user has it selected
        if self.kwargs['version_up'] is True:
            su.version_up()

    def check_frames_exist(self, frame_numbers):
        # check for type of render node
        writes = node_utils.get_all_nodes('Write', True, False)
        ordered_writes = sorted(writes, key=lambda x: x['render_order'].value())
        pipe_obj = self.pipe_ctx.get_pipe_obj()
        ext = pipe_obj.cinema.comp_format.extension
        version = get_comp_version()
        path_ctx = self.pipe_ctx.get_path_context()
        exr_path = path_ctx.get_path('sh_comp_wip_output_file', version=version, eye='l',
                                      ext=ext, namespace='shot')
        frames_exist = False
        for number in frame_numbers:
            for node in ordered_writes:
                write_name = node['name'].value()
                regex = re.search("rfxw", write_name, re.I)

                if not regex:
                    write = nuke.toNode(node['name'].value())
                    version = exr_path.split('/')[-2]
                    path = write['file'].getValue()
                    nuke_path = re.sub('%v', version, path)

                    frame_sequence = FrameSequence(nuke_path)
                    frame_path = frame_sequence.get_frame(number).path
                    if os.path.exists(frame_path):
                        frames_exist = True
                        break
                else:
                    for eye in ['l', 'r']:
                        nuke_path = path_ctx.get_path('sh_comp_wip_output_file',
                                                      version=version, eye=eye,
                                                      ext=ext, namespace='shot')
                        frame_sequence = FrameSequence(nuke_path)
                        frame_path = frame_sequence.get_frame(number).path
                        if os.path.exists(frame_path):
                            frames_exist = True
                            break
                if frames_exist:
                    message = 'Frames already exist for this WIP version. What would '\
                              'you like to do?'
                    # Check if there are any missing frames. If there are, add the
                    # option to only render those frames
                    missing = su.find_missing_comp_frames()
                    missing_frames = self._get_missing_frames_text(missing)
                    options = self.FRAME_OPTIONS
                    if missing_frames:
                        missing_option = '{0} ({1})'.format(self.FRAME_MISSING,
                                                            missing_frames)
                        options.append(missing_option)
                    option = show_options(message, 'Farm Submission Choice', options,
                                          layout=QtCore.Qt.Vertical)
                    if option is None:
                        option = self.FRAME_CANCEL
                    return option
        return self.FRAME_OVERWRITE

    def get_parameters(self):
        """
        This function will set up our render parameters to pass into
        the executer and qube tasks.
        """
        kwargs = {}
        kwargs['label'] = str(self.input_name.text().toAscii())
        kwargs['version_up'] = bool(self.auto_version_checkbox.isChecked())
        kwargs['priority'] = str(
                self.option_widget.widgets['Priority'].value())
        kwargs['cpus'] = self.option_widget.widgets['Cpus'].value()

        # heavy render
        kwargs['heavy_render'] = bool(self.heavy_render_checkbox.isChecked())
        if self.check_matte_nodes():
            kwargs['create_matte_plates'] = \
                bool(self.create_matte_plates.isChecked())
        kwargs['chunksize'] = str(
                self.advanced_option_widget.widgets['ChunkSize'].value())
        kwargs['threads'] = str(
                self.advanced_option_widget.widgets['Threads'].value())
        kwargs['cache'] = str(
                self.advanced_option_widget.widgets['Cache(mbs)'].value())
        kwargs['wait_for'] = str(
                self.advanced_option_widget.widgets['Wait_For'].text())
        kwargs['retrywork'] = str(
                self.advanced_option_widget.widgets['RetryWork'].text())

        # set up frame-sets
        frame_set = str(self.option_widget.widgets['Range'].text())
        kwargs['frame_sets'] = FrameSet.parse(frame_set)

        # frame_range only used for storage purposes
        kwargs['frame_range'] = str(self.option_widget.widgets['Range'].text())
        kwargs['f_range'] = kwargs['frame_range']

        if self.submit_blocked_checkbox.isChecked():
            kwargs['status'] = 'blocked'

        # Extra stuff that the qube proc will take care of
        kwargs['allow_local'] = bool(self.submit_local_checkbox.isChecked())
        if kwargs['allow_local'] is True:
            kwargs['clusters'] = 'floor'
        else:
            kwargs['clusters'] = 'nuke'

        kwargs['multiple_writes'] = \
            bool(self.submit_multi_checkbox.isChecked())
        kwargs['interactive'] = \
            bool(self.submit_interactive_checkbox.isChecked())
        kwargs['submit_blocked'] = \
            bool(self.submit_blocked_checkbox.isChecked())
        kwargs['nuke_version'] = nuke.NUKE_VERSION_STRING  # @UndefinedVariable
        kwargs['deparment'] = 'Default'
        kwargs['output'] = []

        kwargs['project'] = self.pipe_ctx.get_label()

        return kwargs

    def check_write_nodes(self):
        """
        This function will define the write nodes in the scene
        and prepare them for writing.
        """
        msg = ''
        write_nodes = []
        for node in nu.get_all_nodes('Write'):
            if not node['disable'].value():
                write_nodes.append(node)

        if len(write_nodes) == 0:
            msg = ('Error! You do not have any Write nodes enabled in this '
                   'script. \nPlease enable one Write node and check it\'s '
                   'path\n')
            nuke_gui.RFXMessage('Multiple Write Node Check', msg)
            return False

        if len(write_nodes) > 1 and \
           self.submit_multi_checkbox.isChecked() is False:
            msg = ('Error! You have too many Write nodes enabled in this '
                   'script.\nPlease disable all but one Write node\n')
            nuke_gui.RFXMessage('Multiple Write Node Check', msg)
            return False

        for node in write_nodes:
            output = node['file'].value()

            # if output in self.kwargs['output']:
            #     msg = ('OY! Two or more write nodes have the same path.\n'
            #            'Shore that junk up!\n')
            #     nuke_gui.RFXMessage('Multiple Write Node Check', msg)
            #     return False
            self.kwargs['output'].append(output)

        if not self.kwargs['output']:
            msg = ('OY! Your Write node has no output path.\n'
                   'Fix that junk!\n')
            nuke_gui.RFXMessage('Multiple Write Node Check', msg)
            return False

        return True

    def sort_frames(self, frames):
        """
        Sorts the given frame list
        """
        tmp = None
        frame_size = len(frames)
        sorted_frame_list = []
        for index in xrange(frame_size):
            if frames[index] != frames[-1]:
                if (frames[index + 1] != frames[index] + 1 or
                   frames[index - 1] != frames[index] - 1):
                    if (frames[index + 1] != frames[index] + 1 and
                        frames[index - 1] != frames[index] - 1):
                        sorted_frame_list.append(str(frames[index]))
                    if frames[index - 1] != frames[index] - 1:
                        tmp = str(frames[index]) + '-'
                    elif tmp:
                        sorted_frame_list.append(tmp + str(frames[index]))
                        tmp = None
            else:
                if tmp:
                    sorted_frame_list.append(tmp + str(frames[-1]))
                else:
                    sorted_frame_list.append(str(frames[-1]))

        return sorted_frame_list

    def setup_frame_ranges(self):
        """
        This function will setup frame ranges for each write node
        Basically it accepts the following cases when submitting renders.

        tmp_range = '1,3,5-9,12,20-30,44-44'
        tmp_range = '2-30'
        tmp_range = '1'
        tmp_range = '15-15'
        tmp_range = '8,10,87'
        """

        tmp_range = '%s' % (self.option_widget.widgets['Range'].text()
                            .toAscii())
        req_frames = tmp_range.split(',')
        frame_ranges = []
        range_regex = re.compile('-')

        if len(req_frames) > 1:
            for frame in req_frames:
                if not range_regex.search(frame):
                    frame_ranges.append('%s-%s' % (frame, frame))
                else:
                    frame_ranges.append(frame)
        elif not range_regex.search(str(req_frames)):
            frame_ranges.append('%s-%s' % (req_frames[0], req_frames[0]))
        else:
            frame_ranges.append(tmp_range)

        missing_frames = []
        to_del_frames = []

        for frames in frame_ranges:
            step = 1
            self.kwargs['range'] = frames
            in_frame, out_frame = self.kwargs['range'].split('-')
            if re.search('x', out_frame):
                out_frame, step = out_frame.split('x')

            for out in self.kwargs['output']:
                for frame_number in xrange(int(in_frame), int(out_frame) + 1,
                                           int(step)):
                    tmp_frame = '%04d' % int(frame_number)
                    image_path = re.sub('%04d', tmp_frame, out)
                    result = re.search('%v', image_path)
                    if result:
                        l_image = re.sub('%v', 'l', image_path)
                        r_image = re.sub('%v', 'r', image_path)
                        if os.path.exists(l_image):
                            self.to_del_images.append(l_image)
                            if not frame_number in to_del_frames:
                                to_del_frames.append(frame_number)
                        else:
                            missing_frames.append(frame_number)
                        if os.path.exists(r_image):
                            self.to_del_images.append(r_image)
                            if not frame_number in to_del_frames:
                                to_del_frames.append(frame_number)
                        else:
                            missing_frames.append(frame_number)
                        continue
                    if os.path.exists(image_path):
                        self.to_del_images.append(image_path)
                        if not frame_number in to_del_frames:
                            to_del_frames.append(frame_number)
                    else:
                        missing_frames.append(frame_number)

        self.sorted_missing_frames = \
            self.sort_frames(list(set(missing_frames)))
        self.sorted_to_del_frames = self.sort_frames(to_del_frames)

    def remove_existing_frames(self):
        """
        Prompt the user if there are already frames in the
        output path folder.
        """
        self.submit_action = SubmitAction.SUBMIT
        if len(self.to_del_images):
            prompt = nuke_gui.RFXChoose('Existing Frames',
                'There are already existing frames\n'
                'where you wish to render at.\n\n'
                'You can either:\t\n'
                '-Version up the scene\n'
                '-Delete frames %s\n'
                '-Submit%s\n'
                '-Cancel the submission\n'
                % (self.sorted_to_del_frames, self.sorted_missing_frames),
                ['Version Up', 'Delete Frames', 'Submit', 'Cancel'])

            prompt.exec_()
            user_action = prompt.result
            if user_action == "Delete Frames":
                for img_path in self.to_del_images:
                    print 'removing file: ' + img_path
                    try:
                        os.remove(img_path)
                    except:
                        pass
            elif user_action == "Version Up":
                # TODO:
                # This function should communicate with Nuke
                # to set the file paths, etc.. in the nodes.
                su.version_up()
            #elif user_action == "Submit missing":
            #    self.submit_action = SubmitAction.SUBMIT_MISSING_FRAMES
            elif user_action == "Submit":
                sys.stderr.write('User is submitting anyway\n')
            else:
                sys.stderr.write('User Canceled the Qube submission\n')
                self.submit_action = SubmitAction.CANCEL

    def show_results(self, submitter):
        """
        Popup a window and display the Job ID
        """
        msg = ''
        if submitter is not None:
            for job in submitter:
                info = 'Job[%s]:\t%s' % (job.job['label'], job.job_id)
                msg += '%s\n' % info

        #maybe no jobs were created
        if msg == '':
            msg = 'No qube jobs created!'

        # show window
        nuke_gui.RFXMessage('Job ID', msg)

    def save_prefs_and_exit(self):
        """
        Function to close the window and save the prefs
        """
        save_gui_prefs(**self.kwargs)
        self.close()

    def read_prefs(self):
        """
        Function to read the preferences of the window contents from the
        last session.
        """
        self.kwargs = load_gui_prefs()

        # set the UI elements
        self.option_widget.widgets['Cpus'].setValue(int(self.kwargs['cpus']))
        self.option_widget.widgets['Priority']\
            .setValue(int(self.kwargs['priority']))
        self.option_widget.widgets['Range'].setText(self.kwargs['f_range'])
        self.advanced_option_widget.widgets['Cache(mbs)']\
            .setValue(int(self.kwargs['cache']))
        self.advanced_option_widget.widgets['Threads']\
            .setValue(int(self.kwargs['threads']))
        self.advanced_option_widget.widgets['RetryWork']\
            .setValue(int(self.kwargs['retrywork']))
        self.advanced_option_widget.widgets['Wait_For']\
            .setText(self.kwargs['wait_for'])
        self.input_name.setText(self.kwargs['label'])
        self.submit_interactive_checkbox.setChecked(self.kwargs['interactive'])
        self.submit_blocked_checkbox.setChecked(self.kwargs['submit_blocked'])
        self.submit_local_checkbox.setChecked(self.kwargs['allow_local'])
        self.heavy_render_checkbox.setChecked(self.kwargs['heavy_render'])
        #self.motion_vector_checkbox.setChecked(self.kwargs['motion_vector'])
        self.auto_version_checkbox.setChecked(self.kwargs['version_up'])
        self.submit_multi_checkbox.setChecked(self.kwargs['multiple_writes'])
