#!/usr/bin/env python
#----------------------------------------------------------------------------#
#--------------------------------------------------------- HEADER_START -----#
"""
@author:
    mrowley

@description:
    Publish shot UI


@ revision 09/20/2013
    modified original code to be more programmer-friendly. :)

    10/1/2013
    first release.
"""
#--------------------------------------------------------- HEADER_END -------#
#----------------------------------------------------------------------------#

#----------------------------------------------------------------------------#
#-------------------------------------------------------------- IMPORTS -----#
import os
import sys

# third party
from PyQt4 import QtGui, QtCore

# internal
from nuke_tools import publish_utils, node_utils, script_utils
# local import
import widgets

# external
from ui_lib.window import RWindow, RWidget
from ui_lib.widgets.frame import RFrameLayout
from app_manager.cmd_executer import CmdExecuter
from pipe_utils import string_utils, xml_utils
from pipe_api.env import get_pipe_context
from pipe_utils.sequence import FrameRange, StereoView, NukeSequence
from pipe_core.pipe_context import PipeContext
from pipe_utils.email_utils import get_email_address
from pipe_utils.system_utils import get_user
from pipe_utils.file_system import (safe_symlink,get_base_name)
from pipe_utils import file_system
from pipe_utils.response import Success, Failure
from path_lib.utils import split, dirname
from ui_lib.rnuke import old_widgets as nuke_gui
from pipe_utils.xml_utils import ElementTree as ET
from app_manager.session_manager import SessionManager
from path_lib.utils import dirname

# farm submission
from farm_lib.qube_job import QubeJob
from farm_lib.qube_submitter import QubeSubmitter
from farm_lib.farm_utils import QubeAgenda
from farm_lib.farm_enums import JobType, QubeLanguage
import farm_lib.farm_utils as fu
from nuke_tools.farm_utils import get_latest_discipline_wip
from pipe_core.pipe_enums import Discipline
from nuke_tools.farm_utils import get_single_media_job

from ui_lib.dialogs.popup import show_error


py_script = 'python $PKG_NUKE_TOOLS/batch/media_submission_startup.py'

def show_results(submitter):
    """
    Popup a window and display the Job ID
    """
    msg = ''
    if submitter is not None:
        for job in submitter:
            info = 'Job[%s]:\t%s' % ( job.job['label'], job.job_id )
            msg += '%s\n' % info

    #maybe no jobs were created
    if msg == '':
        msg = 'No qube jobs created!'

    # show window
    message = nuke_gui.RFXMessage('Job ID', msg)

def error_window(msg):
    """
    Publish error window message
    """
    # show window
    nuke_gui.RFXMessage('Publish Error', msg)

def create_instructions(xml_file, **kwargs):
    # create xml root
    #
    root = ET.Element('publishInstructions', **kwargs)
    xml_utils.indent(root)

    # create directory that contains the xml file
    #
    xml_dir = os.path.dirname(xml_file)
    if not os.path.exists(xml_dir):
        file_system.safe_make_dir(xml_dir, make_all=True)

    # save the xml file
    #
    ET.ElementTree(root).write(xml_file)
    if not os.path.exists(xml_file):
        return Failure('There was a problem writing the instructions xml.')
    else:
        response = Success('Instructions xml created successfully.')
        response.payload = xml_file
        return response

class RPublish(RWindow):
    """
    Publish UI for Nuke
    """
    PREF_NAME = 'nuke_publish_shot'
    TITLE = 'Publish Frames'
    NOTES = 'terse notes (limited to 50 chars)'
    def __init__(self, parent=None, pipe_ctx=None):
        """
        Set up the main window
        """
        RWindow.__init__(self, parent=parent)
        self.pipe_ctx = pipe_ctx
        if self.pipe_ctx is None:
            self.pipe_ctx = get_pipe_context()

        if not self.pipe_ctx.is_shot():
            raise Exception(
                            '"%s" does not describe a shot context.' % self.pipe_ctx)

        self.versions = sorted(publish_utils.get_rendered_versions(), key=lambda x: x.number)
        self.versions.reverse()

        self.main_layout = QtGui.QVBoxLayout(self)
        end_button_layout = QtGui.QHBoxLayout()

        sequence = self.pipe_ctx.get_sequence_obj()
        shot = self.pipe_ctx.get_shot_obj()
        frame_range = shot.frame_range

        options = [{'label' : 'version', 'value' : ['%04d' % (v.number) for v in self.versions]},
                   {'label' : 'sequence', 'value' : sequence.name},
                   {'label' : 'shot', 'value' : shot.name},
                   {'label' : 'first_frame', 'value' : frame_range.start},
                   {'label' : 'last_frame', 'value' : frame_range.end},
                   {'label' : 'stills', 'value' : False},
                   {'label' : 'scratch', 'value' : True},
                   {'label' : 'version_up', 'value' : True},
                   {'label' : 'use_local_cpu', 'value' : False}]
                   # {'label' : 'apply_hud', 'value' : True}]

        self.notes = widgets.RTextEdit(text=self.NOTES)
        self.option_widget = widgets.ROptionWidget(options=options, title=RPublish.TITLE)
        self.publish_button = QtGui.QPushButton('Publish')
        self.close_button = QtGui.QPushButton('Close')
        end_button_layout.addWidget(self.publish_button)
        end_button_layout.addWidget(self.close_button)
        self.main_layout.addWidget(self.option_widget)
        self.main_layout.addWidget(self.notes)
        self.main_layout.addLayout(end_button_layout)
        self.setLayout(self.main_layout)
        self.start()

        self.close_button.clicked.connect(self.close)
        self.publish_button.clicked.connect(self.publish)

    def check_if_rendered(self, shot, version):
        last_version, _is_seq = \
        get_latest_discipline_wip(shot,
              discipline=Discipline.COMP,
              wip_name='master',
              use_sequence=False)
        sp_context = shot.get_path_context()

        namespace = 'comp'
        wip_context = PipeContext.from_pipe_obj(last_version)
        wip_context.shot = shot.name
        wip_context.wip_name = namespace

        output_dir = sp_context.get_render_path('sh_comp_output_dir',
                                                version=version,
                                                namespace='shot',
                                                disc='comp')
        return os.path.exists(output_dir)

    def publish(self):
        """
        Send the options in the UI to the publisher.
        """

        # matte_nodes = node_utils.node_query(attrs='is_matte_painting')
        # if not matte_nodes:
        #     error_window('No matte painting nodes present. Please address this!')
        #     raise Exception('No matte painting nodes present. Please address this!')

        mgr = SessionManager.inst()
        env = mgr.env_manager
        pipe_ctx = env.get_pipe_context()
        shot_obj = pipe_ctx.get_shot_obj()
        ext = shot_obj.cinema.comp_format.extension
        kwargs = self.option_widget.get_values()
        version = kwargs.get('version', 1)

        rendered = self.check_if_rendered(shot_obj, version)
        if not rendered:
            show_error('Unable to publish, no frames have been rendered for '
                       'version {0}.'.format(version), 'Publishing Error')
            return

        tmp_notes = str(self.notes.toPlainText())
        kwargs['notes'] = tmp_notes
        if tmp_notes == self.NOTES:
            kwargs['notes'] = ''
        wip_path = pipe_ctx.get_explicit_scene_path()
        scene_name = get_base_name(wip_path)
        new_scene_name = '%s%03d' % (scene_name[:-3],int(kwargs['version']))
        basedir = dirname(wip_path)
        kwargs['wip_path'] = '%s/%s.nk' % (basedir,new_scene_name)
        kwargs['output_path'] = \
            publish_utils.get_wip_output_path('sh_comp_wip_output_file',
                                              kwargs['version'],
                                              ext=ext,
                                              namespace='shot',
                                              cam='%v')

        # create a live link
        path = publish_utils.get_wip_output_path('sh_comp_output_dir',
                                                 kwargs['version'],
                                                 namespace='shot')
        if os.path.isdir(path) is True:
            live_lnk = split(path)[0] + '/live'
            safe_symlink(path,live_lnk,True)
        else:
            error = ('Failed to create a symlink!\n'
                     'Directory <%s> does not exist!' % (path))
            error_window(error)
            raise Exception(error)

        frame_seq = NukeSequence(kwargs['output_path'])

        # verify images
        wtf = FrameRange.parse('%s-%s' % (float(kwargs['first_frame']),float(kwargs['last_frame'])))
        print "FRAME SEQ: ", wtf
        img_exist = publish_utils.images_exist(frame_seq, frange=wtf)

        # pass off to media submission
        gtg = True
        if not img_exist:
            if not kwargs.get('stills'):
                error_window('Missing Frames! If you want to still publish, check on the \'stills\' option.')
                gtg = False
            else:
                left_result = frame_seq.fill_missing_frames(wtf)
                if left_result.is_failure():
                    error_window('Failed to symlink frames for left eye! {0}'.format(left_result.message))
                    gtg = False
                right_result = frame_seq.fill_missing_frames(wtf, StereoView.RIGHT)
                if right_result.is_failure():
                    error_window('Failed to symlink frames for right eye! {0}'.format(left_result.message))
                    gtg = False
        if gtg:
            self.farm_submission(**kwargs)
            self.close()
            if kwargs['version_up'] is True:
                script_utils.version_up()

    def farm_submission(self, **kwargs):
        """
        We can also send this information to the farm for media submission
        """
        # set up parameters to pass to the ReviewSubmitter
        pipe_ctx = PipeContext.from_env()
        pipe_obj = pipe_ctx.get_pipe_obj()
        description = kwargs['notes']
        output_path = kwargs['output_path']
        wip_path = kwargs['wip_path']
        hud_extended_res = pipe_obj.get_pre_hud_res()
        hud_res = hud_extended_res[0]
        extended_res = hud_extended_res[1]

        # Add the job dependencies as part of the settings for the render
        # submission jobs
        settings = {'discipline': Discipline.COMP,
        'priority': 1000,
        'wip_name': 'master',
        'sequence_submission': False,
        'version_up': False,
        'scratch': kwargs.get('scratch', True),
        'stills': kwargs.get('stills', False),
        'first_frame': kwargs.get('first_frame', 1),
        'last_frame': kwargs.get('last_frame', 1),
        'version': kwargs.get('version', 1),
        'ext_xres': extended_res[0],
        'ext_yres': extended_res[1],
        'wip_path': wip_path,
        'output_path': output_path,
        'description': '%s' % description[0:49],
        'left_eye': '',
        'right_eye': '',
        'job_dependencies': []}

        media_job = get_single_media_job(pipe_obj, **settings)

        # submit jobs
        submitter = QubeSubmitter()
        submitter.append(media_job)

        if kwargs['use_local_cpu'] is True:
            submission_result = submitter.submit_to_self()
        else:
            submission_result = submitter.submit()
        if not submission_result:
            submission_result.raise_exception()

        # show results
        show_results(submitter)

