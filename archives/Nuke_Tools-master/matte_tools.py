import os
import re
import sys
import datetime
import glob

import nuke
from PyQt4 import QtGui, QtCore

from pipe_api.env import get_pipe_context

from path_lib.extractor import extract

from pipe_core.pipe_context import WipContext
from pipe_core.pipe_enums import Discipline

from ui.widgets import ROptionWidget, RSearchableListWidget,\
                       RDisplayResponseList

from pipe_utils.list_utils import to_list
from pipe_utils.system_utils import get_user
from pipe_utils.email_utils import sendmail
from pipe_utils.io import IO
from pipe_utils.response import Success, Failure, Response

from ui_lib.window import RWindow, RWidget
from ui_lib.dialogs.pipe_obj_explorer import RShotExplorer
from ui_lib.dialogs.popup import show_message, show_error, show_yes_no,\
                                 show_options

from nuke_tools.ui.progress_dialog import RProgressDialog
from nuke_tools import validation
import node_utils
import matte_utils
import farm_utils
import camera_utils
from pipe_utils.response import ResponseList

from app_manager import wip_manager

MATTE_USERS = ['dhogan', 'ymartel', 'fmillett']


RECEIVERS = ['lighting@reelfx.com',
             'mattepainting@reelfx.com']

OPTIONS = {'priority': {'label': 'priority', 'value': 1000, 'minimum': 1000,
                        'maximum': 5000},
           'cpus': {'label': 'cpus', 'value': 15, 'minimum': 1, 'maximum': 30},
           'heavy': {'label': 'heavy_render', 'value': False},
           'sequence_sub': {'label': 'sequence_submission', 'value': False},
           'scratch': {'label': 'scratch', 'value': True},
           'chunksize': {'label': 'chunksize', 'value': 1, 'minimum': 1},
           'cache': {'label': 'cache', 'value': 2650, 'minimum': 0,
                     'maximum': 2650},
           'threads': {'label': 'threads', 'value': 2, 'minimum': 1,
                       'maximum': 6},
           'retry': {'label': 'retry_work', 'value': 2, 'minimum': 0,
                     'maximum': 4},
           'wait': {'label': 'wait_for', 'value': ''},
           'submit_media': {'label': 'submit_media', 'value': True},
           'submit_media_merged': {'label': 'submit_media_merged',
                                   'value': True},
           'submit_media_painting': {'label': 'submit_media_painting',
                                     'value': True},
           'version_up': {'label': 'version_up', 'value': True},
           'merged': {'label': 'merged', 'value': True},
           'painting': {'label': 'painting', 'value': True},
           'notes': {'label': 'notes', 'value': 'terse notes',
                     'type': 'RTextEdit', 'value_function': 'toPlainText'},
           'frames': {'label': 'frames', 'value': '',
                      'regex': '(\d+(,|\-\d+(,|x\d+,)))*'}}


class FarmSubmission(RWindow):
    """
    Qube submission tool for Nuke
    """
    PREF_NAME = 'matte_painting_farm_submission'
    TITLE = 'Matte Painting Farm Submission'

    def __init__(self, *args, **kwargs):
        self.pipe_context = None
        if 'pipe_context' in kwargs:
            self.pipe_context = kwargs.pop('pipe_context')
        RWindow.__init__(self, *args, **kwargs)

        self._option_widgets = {}

        self.options = []

        self.set_size(450, 360)

        if not self.pipe_context:
            self.pipe_context = get_pipe_context()

        self.widgets = {}
        self.shot_list = {}

        self.build_ui()

    def build_ui(self, *args, **kwargs):  # IGNORE:W0613

        main_layout = QtGui.QVBoxLayout(self)
        content_layout = QtGui.QHBoxLayout()
        button_layout = QtGui.QHBoxLayout()
        main_layout.addLayout(content_layout)
        main_layout.addLayout(button_layout)

        shots_layout = QtGui.QVBoxLayout()
        self.setLayout(main_layout)
        content_layout.addLayout(shots_layout)

        self.build_shot_list(shots_layout)
        if self._option_groups:
            options_layout = QtGui.QVBoxLayout()
            content_layout.addLayout(options_layout)
            self.build_options(options_layout)
        self.build_buttons(button_layout)

    def build_shot_list(self, layout):
        shot_list = []
        sequence = self.pipe_context.get_sequence_obj()
        shots = sequence.get_shots_in_edit_order()
        for shot in shots:
            matte_painting_path = matte_utils.get_latest_matte_painting(shot)
            shot_name = '{0}_{1}'.format(sequence.name, shot.name)
            if matte_painting_path:
                context = extract(matte_painting_path)
                if context.has_vars('shot_name') and not\
                   context.get('shot_name') == 'matte':
                    shot_name = '{0} (one-off)'.format(shot_name)

            shot_list.append(shot_name)
            self.shot_list[shot_name] = shot

        widget = RSearchableListWidget(contents=shot_list)
        widget.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        layout.addWidget(widget)

        self.widgets['shot_list'] = widget

        self.connect(widget, QtCore.SIGNAL('customContextMenuRequested'),
                     self.right_click)

    def right_click(self, widget, point):
        right_click_menu = QtGui.QMenu('Right Click Menu')

        select_all = right_click_menu.addAction('Select All')
        _clear_selection = right_click_menu.addAction('Clear Selection')

        qaction = right_click_menu.exec_(widget.list_widget.mapToGlobal(point))

        if qaction:
            if qaction is select_all:
                status = True
            else:
                status = False

            for i in xrange(widget.list_widget.count()):
                item = widget.list_widget.item(i)
                item.setSelected(status)

    def build_options(self, layout):
        for group in self._option_groups:
            option_widget = ROptionWidget(**group)

            self._option_widgets[group.get('title')] = option_widget

            layout.addWidget(option_widget)

    def build_buttons(self, layout):
        submit = QtGui.QPushButton('submit')
        close = QtGui.QPushButton('close')

        layout.addWidget(submit)
        layout.addWidget(close)

        signal = QtCore.SIGNAL('clicked()')
        self.connect(close, signal, self.close)
        self.connect(submit, signal, self.submit)

    def get_settings(self):

        settings = {}
        for key in self._option_widgets.keys():
            widget = self._option_widgets.get(key)
            settings.update(widget.get_values())

        return settings

    def get_shots(self):
        shots = []
        selected_shots = self.widgets['shot_list'].selectedItems()
        for selected_shot in selected_shots:
            text = str(selected_shot.text())
            shot = self.shot_list.get(text)
            shots.append(shot)

        return shots

    def submit(self):

        shots = self.get_shots()
        settings = self.get_settings()

        if not shots:
            show_error('Please select a shot!', 'Select Shots')
            raise Exception('Please select a shot!')
        else:
            return shots, settings


class MattePaintingMediaSubmission(FarmSubmission):
    """
    Qube submission tool for Nuke
    """
    PREF_NAME = 'matte_painting_media_submission'
    TITLE = 'Matte Painting Media Submission'

    def __init__(self, *args, **kwargs):
        self._option_groups = [{'title': 'basic_options',
                                'options': [OPTIONS.get('priority'),
                                           OPTIONS.get('scratch'),
                                           OPTIONS.get('version_up'),
                                           OPTIONS.get('painting'),
                                           OPTIONS.get('merged'),
                                           OPTIONS.get('wait')]}]
        super(MattePaintingMediaSubmission, self).__init__(*args, **kwargs)

        self.start()

    def submit(self):
        shots, settings = super(MattePaintingMediaSubmission, self).submit()
        responses = matte_utils.media_submission(shots=shots, **settings)

        _widget = RDisplayResponseList(responses=responses)


class MattePaintingRenderSubmission(FarmSubmission):
    """
    Qube submission tool for Nuke
    """
    PREF_NAME = 'matte_painting_render_submission'
    TITLE = 'Matte Painting Render Submission'

    class RenderOptions:
        SKIP = 'Skip render'
        RENDER = 'Render at version'
        VERSION_UP = 'Version up to'
        SKIP_ALL = 'Skip all renders'

    def __init__(self, *args, **kwargs):
        self._option_groups = \
            [{'title': 'basic_options',
              'options': [OPTIONS.get('version_up'),
                          OPTIONS.get('submit_media_merged'),
                          OPTIONS.get('submit_media_painting'),
                          OPTIONS.get('priority'),
                          OPTIONS.get('cpus'),
                          OPTIONS.get('heavy'),
                          OPTIONS.get('sequence_sub'),
                          OPTIONS.get('frames')]},
             {'title': 'advanced_options',
              'options': [OPTIONS.get('chunksize'),
                          OPTIONS.get('cache'),
                          OPTIONS.get('threads'),
                          OPTIONS.get('retry'),
                          OPTIONS.get('wait')],
              'checkable': True,
              'checked': False}]
        super(MattePaintingRenderSubmission, self).__init__(*args, **kwargs)

        self.start()

    def build_buttons(self, layout):
        submit = QtGui.QPushButton('submit')
        close = QtGui.QPushButton('close')

        layout.addWidget(submit)
        layout.addWidget(close)

        signal = QtCore.SIGNAL('clicked()')
        self.connect(close, signal, self.close)
        self.connect(submit, signal, self.submit)
        seq_sub_checkbox = self._option_widgets['basic_options']\
            ._widgets['sequence_submission']
        seq_sub_checkbox.stateChanged\
            .connect(self.sequence_submission_box_changed)

    def sequence_submission_box_changed(self, check_state):
        for i in xrange(self.widgets['shot_list'].list_widget.count()):
            item = self.widgets['shot_list'].list_widget.item(i)
            if re.match('^.*one-off', item.text()):
                item.setSelected(False)
                item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEnabled)
                item.setFlags(item.flags() ^ QtCore.Qt.ItemIsSelectable)

    def skip_submission_dialog(self, response):
                    message = '{0}\nSkipping render submission.'\
                        .format(response.message)
                    for info in to_list(response.payload):
                        if isinstance(info, str):
                            message = '{0}\n{1}'.format(message, info)
                    IO.warning(message)
                    show_message(message, 'Aborting Render Submission',
                                 center_on_screen=True)

    def submit(self):
        nuke.scriptSave()
        wip = WipContext.from_env()
        wmanager = wip_manager.WipManager.instance()
        shots, settings = super(MattePaintingRenderSubmission, self).submit()
        settings['wip_name'] = wip.wip
        settings['discipline'] = Discipline.MATTE
        remove_shots = []
        try:
            for shot in shots:
                last_version, _is_seq = \
                    matte_utils.get_latest_matte_painting_wip(shot,
                        wip_name=wip.wip,
                        use_sequence=settings['sequence_submission'])
                wip_context = WipContext.from_pipe_obj(last_version)
                wip_context.shot = shot.name
                wmanager.open_wip_context(wip_context)
                sequence_submission = settings['sequence_submission']
                response = self.check_write_nodes(wip_context,
                    sequence_submission)
                if isinstance(response, Failure):
                    self.skip_submission_dialog(response)
                    return
                response = validation.write_node_views(wip_context,
                                                       sequence_submission)
                if isinstance(response, Failure):
                    self.skip_submission_dialog(response)
                    return
                response = validation.read_node_filenames(wip_context,
                                                          sequence_submission)
                if isinstance(response, Failure):
                    self.skip_submission_dialog(response)
                    return
                result = self.check_rendered_versions(wip_context, shot,
                                                      **settings)
                if result.message == self.RenderOptions.SKIP:
                    remove_shots.append(shot)
                    continue
                elif result.message == self.RenderOptions.SKIP_ALL:
                    show_message('No shots rendered.',
                         'Render Submission Notification')
                    return
                elif re.match('^{0}'.format(self.RenderOptions.VERSION_UP),
                              result.message):
                    wmanager = wip_manager.WipManager.instance()
                    next_number = result.payload
                    wip_kwargs = {}
                    wip_kwargs['application'] = 'NUKE'
                    wip_kwargs['owner'] = get_user()
                    response = wmanager.version_up(next_number, wip_context,
                                                   **wip_kwargs)
                    if response.is_failure():
                        response.print_message()
                        return response
                    shot.skip_version_up = True
        finally:
            wmanager.open_wip_context(wip)
        # For any shots that were aborted, remove them from the list
        for shot in remove_shots:
            shots.remove(shot)
        if len(shots) == 0:
            show_message('No shots rendered.',
                         'Render Submission Notification')
            return
        else:
            responses = farm_utils.submit_discipline_render(shots=shots,
                                                            **settings)
            _widget = RDisplayResponseList(responses=responses)

    # Checks if any frames have already been rendered for this or future WIP
    # versions. If so, a dialog is presented which allows the user to version
    # up to the next highest non-rendered version.
    def check_rendered_versions(self, wip_context, shot, **settings):
        seq_sub = settings['sequence_submission']
        version_up = settings['version_up']
        path_context = shot.get_path_context()
        path_context.disc = 'matte'
        painting_render_dir = path_context\
            .get_render_path('sh_wip_output_base_dir', namespace='painting')
        merged_render_dir = path_context\
            .get_render_path('sh_wip_output_base_dir', namespace='merged')
        if not os.path.isdir(painting_render_dir):
            message = '{0} is not a valid directory.'\
                      .format(painting_render_dir)
            return Failure(message)
        if not os.path.isdir(merged_render_dir):
            message = '{0} is not a valid directory.'.format(merged_render_dir)
            return Failure(message)
        version_numbers = []
        for version_folder in glob.glob('{0}/v*/'.format(painting_render_dir)):
            version_num = int(re.match('^.*v(\d*)/$', version_folder).group(1))
            version_numbers.append(version_num)
        for version_folder in glob.glob('{0}/v*/'.format(merged_render_dir)):
            version_num = int(re.match('^.*v(\d*)/$', version_folder).group(1))
            version_numbers.append(version_num)
        version_numbers = set(version_numbers)
        wip_version = wip_context.get_wip_version_obj()
        wip_version = wip_version.number + 1 if version_up else \
                      wip_version.number
        if seq_sub:
            source_version_info = 'Sequence version will be {0}'\
                                  .format(wip_version)
        else:
            source_version_info = 'Shot version will be {0}'\
                                  .format(wip_version)
        max_number = max(version_numbers)
        if max_number >= wip_version:
            next_number = max_number + 1
            buttons = ['{0} {1} and render'\
                       .format(self.RenderOptions.VERSION_UP, next_number),
                       '{0} {1}'.format(self.RenderOptions.RENDER,
                                        wip_version),
                       self.RenderOptions.SKIP, self.RenderOptions.SKIP_ALL]
            option = show_options('Rendered frames for Sequence: {0}, Shot: '
                         '{1} WIP version: {2} already exist. {3}. What would '
                         'you like to do?'.format(shot.sequence.name,
                                                  shot.name,
                                                  max_number,
                                                  source_version_info),
                         'WIP version conflict', buttons)
            response = Response(success=False, message=option)
            response.payload = next_number
            return response
        return Success()

    # Checks write nodes of the nuke file at file_path to determine if any
    # Write nodes besides painting, geometry, and merged are enabled.
    def check_write_nodes(self, wip_context, seq_sub):
        writes = node_utils.get_all_nodes('Write', True, False)
        ordered_writes = sorted(writes,
                                key=lambda x: x['render_order'].value())
        if len(ordered_writes) == 0:
            message = 'No write nodes exist in the scene for Sequence: {0} '\
                'Shot: {1} WIP: {2} WIP Version: {3}'\
                .format(wip_context.sequence, wip_context.shot,
                        wip_context.name, wip_context.wip_version)
            return Failure(message)
        valid_write_nodes = ["painting", "merged", "geometry"]
        for node in ordered_writes:
            name = node.name()
            if seq_sub:
                context_name = 'Sequence: {0} WIP: {1} WIP Version: {2}'\
                    .format(wip_context.sequence, wip_context.name,
                            wip_context.wip_version)
            else:
                context_name = 'Sequence: {0} Shot: {1} WIP: {2} WIP Version:'\
                    ' {3}'.format(wip_context.sequence, wip_context.shot,
                                  wip_context.wip, wip_context.wip_version)
            if name not in valid_write_nodes:
                message = 'Non-standard write node named {1} detected in '\
                          '{0}\n'.format(context_name, name)
                yes_no_result = show_yes_no('{0}Continue render submission?'\
                                            .format(message),
                                            "Write node check")
                if not yes_no_result:
                    return Failure(message, payload=node)
            views = node.knob('views').value()
            if views != 'left right':
                message = 'Left and right views were not selected for Write '\
                    'node named {0} in {1}'.format(name, context_name)
                return Failure(message, payload=node)
        return Success()


class MattePaintingPublishUI(FarmSubmission):
    """
    Qube submission tool for Nuke
    """
    PREF_NAME = 'matte_painting_publish_ui'
    TITLE = 'Matte Painting Publish UI'

    def __init__(self, *args, **kwargs):
        self._option_groups = [{'title': 'basic_options',
                                'options': [OPTIONS.get('sequence_sub'),
                                            OPTIONS.get('notes')]}]
        super(MattePaintingPublishUI, self).__init__(*args, **kwargs)

        self.start()

    def build_buttons(self, layout):
        submit = QtGui.QPushButton('publish')
        close = QtGui.QPushButton('close')

        layout.addWidget(submit)
        layout.addWidget(close)

        signal = QtCore.SIGNAL('clicked()')
        self.connect(close, signal, self.close)
        self.connect(submit, signal, self.submit)
        seq_sub_checkbox = self._option_widgets['basic_options']\
            ._widgets['sequence_submission']
        seq_sub_checkbox.stateChanged\
            .connect(self.sequence_submission_box_changed)

    def sequence_submission_box_changed(self, check_state):
        if check_state:
            self.widgets['shot_list'].setEnabled(False)
        else:
            self.widgets['shot_list'].setEnabled(True)

    def submit(self):
        # shots, settings = super(MattePaintingPublishUI, self).submit()
        pipe_objs = self.get_shots()
        settings = self.get_settings()
        if settings.get('sequence_submission'):
            pipe_objs = self.pipe_context.get_sequence_obj()
        elif not pipe_objs:
            show_error('Sequence submission not selected, and no shots were'
                       ' selected. Please select one or the other to perform'
                       ' a publish.', 'Publish Matte Setup Error')
            return

        publish_paths = matte_utils.publish_matte_painting(pipe_objs)
        if isinstance(publish_paths, Failure):
            show_error(publish_paths.message, 'Publish Matte Setup Error')
            return

        if settings.get('notes') == OPTIONS.get('notes').get('value'):
            settings['notes'] = ''

        send_confirmation_emails(publish_paths, **settings)

        message = '\n'.join(publish_paths)
        message += '\nEmail updates sent to:\n'
        message += '\n'.join(RECEIVERS)

        show_message(message, 'Publish Completed!',
                     center_on_screen=True)


class TiffFileUI(RWindow):
    def __init__(self, *args, **kwargs):  # IGNORE:W0613
        super(TiffFileUI, self).__init__(width=300, height=200)

        wip_context = WipContext.from_env()
        wip_context.discipline = Discipline.MATTE
        if not wip_context.wip:
            # Default to master only if we aren't in a wip already
            wip_context.wip = 'master'

        path_context = wip_context.get_path_context()
        paint_dir = os.path.join(path_context.get_path('sq_wip_dir'), 'proj')
        if path_context.has_vars('shot_name'):
            paint_dir = os.path.join(path_context.get_path('sh_wip_dir'),
                                     "proj")

        filenames = QtGui.QFileDialog.getOpenFileNames(
            self, 'Open Render Setup File', paint_dir,
            'Render Setup Files (*.tif);;All Files(*)', '',
            QtGui.QFileDialog.DontUseNativeDialog)

        files = []
        for item in filenames:
            files.append(str(item))

        if files:
            main_ng = node_utils.RNukeNodeGraph.from_script()
            ng = node_utils.RNukeNodeGraph()
            previous = None
            for tmp in files:
                node = ng.create_node('Read', file=tmp)
                # Set the image format to the correct value, since it does
                # when the Read node is created through the GUI but not when
                # created via Python
                image_format = nuke.addFormat('{0} {1}'
                                        .format(node.format().width(),
                                                node.format().height()))
                node['format'].setValue(image_format)
                node['premultiplied'].setValue(True)
                if not previous:
                    previous = node
                    continue
                node.snap_right(previous, additional=50)
                node.align_top(previous)
                previous = node

            ng.snap_right(main_ng, additional=100)
            ng.align_top(main_ng)
            ng.create_backdrop(50, 30, 30, 30, name='matte_painting_tifs')

            nodes = [node.get_node() for node in ng]
            node_utils.center_on_screen(nodes)


def import_matte_painting_choice_ui():
    options = ['EXR Images', 'Nuke Setup']
    option = show_options('Import Matte Painting EXR images or Nuke setup?',
                          'Matte Painting Import', options,)
    if option == 'Nuke Setup':
        show_message('Importing the matte painting Nuke setup will get the '
                     'latest current version, but risks going out of sync in'
                     ' the future. In order to more easily obtain the latest '
                     'output from matte painting, import EXR images instead.',
                     'Matte Painting Nuke Setup Warning', icon='Warning',
                     center_on_screen=True)
        ng = matte_utils.import_shot_matte_painting()
        if isinstance(ng, Failure):
            show_error(ng.message, 'Import Matte Painting Error')
            return
    elif option == 'EXR Images':
        response = matte_utils.import_shot_matte_painting_render()
        if isinstance(response, Failure):
            show_error(response.message, 'Import Matte Painting Error')
            return


def import_matte_painting_ui():
    context = get_pipe_context()

    publish_dialog = RShotExplorer(allow_multiple_selection=True)
    publish_dialog.explore_project(context.get_project_obj())
    result = publish_dialog.exec_()
    if result:
        sequences = to_list(publish_dialog.get_sequence_objs())
        shots = to_list(publish_dialog.get_shot_objs())
        import_sequence_matte_paintings(sequences=sequences, shots=shots)


def create_one_off_ui():
    if len(nuke.selectedNodes()) == 0:
        show_message('No nodes selected to create one off.',
                     'Create One-off Failure', center_on_screen=True)
        return
    context = get_pipe_context()
    dialog = RShotExplorer(allow_multiple_selection=True)
    label = 'Create One Off'
    dialog.setWindowTitle(label)
    dialog.explore_project(context.get_project_obj())
    result = dialog.exec_()
    if result:
        pipe_objs = dialog.get_pipe_objs()
        response = matte_utils.create_one_off(pipe_objs)
        if response is None:
            message = 'No valid target WIP was found. Make sure that the '\
                'target shot has a WIP with the same name as the source WIP.'
            IO.error(message)
            show_error(message, 'Target WIP Not Found')
            return
        if isinstance(response, Failure):
            show_error(response.payload, 'WIP Creation Failed')
            return
        elif isinstance(response, Success):
            t_wips = response.payload
            for t_wip in t_wips:
                show_message('Sequence: {0}\nShot: {1}\nWIP name: {2}\n'\
                'WIP Version: {3}'.format(t_wip.parent.sequence.name,
                                          t_wip.parent.name,
                                          t_wip.name,
                                          t_wip.versions.get_last().number),
                'Create One-off Completed!',
                center_on_screen=True)
            return


def publish_ui():

    user = get_user()
    if not user in MATTE_USERS:
        show_error('You are not authorized to publish matte paintings.  Please'
                   ' speak with a Matte Painting department member.',
                   'Not Authorized')
        return

    context = get_pipe_context()

    dialog = RShotExplorer(allow_multiple_selection=True)
    label = 'Publish Matte Painting'
    dialog.setWindowTitle(label)
    dialog.explore_project(context.get_project_obj())
    result = dialog.exec_()
    pipe_objs = []
    _publish_paths = []
    if result:
        sequences = to_list(dialog.get_sequence_objs())
        shots = to_list(dialog.get_shot_objs())
        if sequences and not shots:
            pipe_objs = sequences
        else:
            pipe_objs = shots

        nodes = node_utils.get_selected_nodes()
        _publish_paths = matte_utils.publish_matte_painting(pipe_objs,
                                                            nodes=nodes)


def send_confirmation_emails(publish_paths, **kwargs):

    current = datetime.datetime.today()
    formatted_time = current.strftime('%d-%m-%Y %H:%M:%S')

    path = publish_paths[0]
    context = extract(path)
    sequence = 'None'
    if context.has_vars('seq_name'):
        sequence = context.get('seq_name')
    else:
        sys.stderr.write('Could not extract a sequence from < {0} >\n'
                         .format(path))

    email_formatted = ''
    notes = kwargs.get('notes', '')
    email_formatted = '{0}Notes: \n\t{1}\n\nPublished Files:\n'\
        .format(email_formatted, notes)
    for path in publish_paths:
        email_formatted = '{0}\t{1}\n'.format(email_formatted, path)

    sendmail(RECEIVERS, 'MP Publish: SEQUENCE: {0} TIME: {1}'\
             .format(sequence, formatted_time), email_formatted)


def import_sequence_matte_paintings(sequences=None, shots=None):
    node_utils.clear_selection()

    if sequences and not shots:
        shots = []
        for sequence in sequences:
            shots.extend(sequence.get_shots_in_edit_order())

    shots = sorted([tmp for tmp in shots if re.search('^\d+$', tmp.name)],
                   key=lambda x: int(x.name))

    dialog = RProgressDialog(message='Importing sequence matte paintings',
                             minimum=1, maximum=len(shots))
    dialog.setValue(0)

    for i, shot in enumerate(shots):
        dialog.setLabelText('Working on shot: %s (%s of %s)' %
                            (shot.name, i + 1, len(shots)))
        sequence = shot.sequence
        ng = matte_utils.import_shot_matte_painting(shot=shot)

        if isinstance(ng, Failure):
            show_error(ng.message, 'Import Matte Painting Error')
            return
        ng.create_backdrop(label='SQ: {0} SH: {1}'.format(shot.name,
                                                          shot.sequence.name))
        dialog.setValue(i + 1)
    dialog.setValue(len(shots))


def create_contact_sheet_ui():
    context = get_pipe_context()
    publish_dialog = RShotExplorer(allow_multiple_selection=True)
    publish_dialog.explore_project(context.get_project_obj())
    result = publish_dialog.exec_()
    _pipe_objs = []
    if result:
        sequences = to_list(publish_dialog.get_sequence_objs())
        shots = to_list(publish_dialog.get_shot_objs())
        if not sequences and not shots:
            sequences = to_list(context.get_sequence_obj())

        if sequences and not shots:
            shots = []
            for sequence in to_list(sequences):
                shots.extend(sequence.get_shots_in_edit_order())

        matte_utils.create_contact_sheet(shots=shots)


def validate_caches_ui():
    response_list = matte_utils.validate_caches()
    _list_window = RDisplayResponseList(responses=response_list,
                                        no_payloads=True)


class CheckResultType:
    failure = 0
    success = 1


class ValidationWindow(RWindow):
    """
    Validation tool for Nuke, checks the current scene against various tests.
    """
    def __init__(self, *args, **kwargs):  # IGNORE:W0613
        kwargs['title'] = 'Validation Checks'
        super(ValidationWindow, self).__init__(*args, **kwargs)

        # Run the checks
        is_sequence = True if not os.environ['SHOT_NAME'] else False
        self.responses = validation.run_checks(is_sequence)

        # Build the rest of the GUI based on the responses
        main_layout = QtGui.QVBoxLayout(self)
        self.success_widget = \
            RValidationCheck(check_type=CheckResultType.success)
        self.failure_widget = \
            RValidationCheck(check_type=CheckResultType.failure)
        self.add_result_items()
        main_layout.addWidget(self.success_widget)
        main_layout.addWidget(self.failure_widget)
        self.start()

    def add_result_items(self):
        for response in self.responses:
            if type(response) is Success:
                item = QtGui.QStandardItem(response.message)
                self.success_widget.add_list_item(item, response)
            elif type(response) is Failure:
                item = QtGui.QStandardItem(response.message)
                if response.payload:
                    for payload_item in to_list(response.payload):
                        if not type(payload_item) is str:
                            continue
                        child_item = QtGui.QStandardItem(payload_item)
                        item.appendRow(child_item)
                self.failure_widget.add_list_item(item, response)


class RValidationCheck(RWidget):
    def __init__(self, *args, **kwargs):
        self.responses = ResponseList()
        if 'check_type' in kwargs:
            self.check_type = kwargs.pop('check_type')
        else:
            self.check_type = None
        super(RValidationCheck, self).__init__(*args, **kwargs)
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)

        if self.check_type == CheckResultType.success:
            self.label = QtGui.QPushButton('Successes')
            self.label.setStyleSheet('QPushButton {background-color: green; '
                                'color: black}')
        elif self.check_type == CheckResultType.failure:
            self.label = QtGui.QPushButton('Failures')
            self.label.setStyleSheet('QPushButton {background-color: red; '
                                'color: black}')
        else:
            self.label = QtGui.QPushButton('Invalid CheckResultType')
            self.label.setStyleSheet('QPushButton {background-color: orange; '
                                'color: black')
        self.search = QtGui.QLineEdit()
        self.connect(self.search, QtCore.SIGNAL("textChanged(QString)"),
                     self.search_changed)
        self.connect(self.search, QtCore.SIGNAL("textEdited(QString)"),
                     self.search_changed)
        self.tree = QtGui.QTreeView()
        self.tree.setHeaderHidden(True)
        self.model = QtGui.QStandardItemModel(0, 1)
        self.tree.setModel(self.model)

        layout.addWidget(self.label)
        layout.addWidget(self.search)
        layout.addWidget(self.tree)

    def search_changed(self, value):
        value = str(value)
        if value:
            self.model.clear()
            regex = re.compile('%s' % (value), re.I)
            for response in self.responses:
                add_item = False
                item = QtGui.QStandardItem(response.message)
                # Search the payload items first
                if response.payload:
                    for payload_item in to_list(response.payload):
                        if not type(payload_item) is str:
                            continue
                        # Only add a payload item as a child if it matches.
                        # Also flag the item to be added to the model.
                        if regex.search(payload_item):
                            child_item = QtGui.QStandardItem(payload_item)
                            item.appendRow(child_item)
                            add_item = True
                # If a payload matches, or the response message matches, add
                # the item
                if add_item or regex.search(response.message):
                    self.model.appendRow(item)
        else:
            self.model.clear()
            for response in self.responses:
                item = QtGui.QStandardItem(response.message)
                for payload_item in to_list(response.payload):
                    if not type(payload_item) is str:
                        continue
                    child_item = QtGui.QStandardItem(payload_item)
                    item.appendRow(child_item)
                self.model.appendRow(item)

    def add_list_item(self, item, response):
        self.model.appendRow(item)
        self.responses.append(response)

    def clear_items(self):
        self.model.clear()


class RevertCamera(RWindow):
    def __init__(self, *args, **kwargs):  # IGNORE:W0613
        node_is_valid = self.node_validation()
        if isinstance(node_is_valid, Failure):
            show_message(node_is_valid.message, 'Revert Camera Error')
            return
        kwargs['title'] = 'Revert Camera Version'
        kwargs['width'] = 300
        kwargs['height'] = 200
        super(RevertCamera, self).__init__(*args, **kwargs)
        main_layout = QtGui.QVBoxLayout(self)
        self.label = QtGui.QLabel('Published Versions:')
        self.version_list = QtGui.QListWidget()
        self.camera_versions = self.get_camera_versions()
        for version in self.camera_versions:
            self.version_list.addItem(str(version.number))
        button_layout = QtGui.QHBoxLayout()
        self.revert_button = QtGui.QPushButton('Revert to Version')
        self.revert_button.setEnabled(False)
        self.cancel_button = QtGui.QPushButton('Cancel')
        button_layout.addWidget(self.revert_button)
        button_layout.addWidget(self.cancel_button)
        self.connect_signals()
        main_layout.addWidget(self.label)
        main_layout.addWidget(self.version_list)
        main_layout.addLayout(button_layout)
        self.start()

    def node_validation(self):
        if not nuke.nodesSelected():
            return Failure('Please select a camera node to revert.')
        self.node = nuke.selectedNode()
        if self.node.Class() != 'Camera2' or not self.node.knob('RCameraData'):
            return Failure('Please select a valid camera node to revert.')
        camera_name = self.node['name'].value()
        match = camera_utils.CAMERA_REGEX.search(camera_name)
        if not match:
            return Failure('Camera node name is not valid.')
        matches = match.groups()
        if not len(matches) == 3:
            return Failure('Number of regex matches for camera node name did'
                           ' not match expected value.')
        self.sequence_name, self.shot_name, self.eye_name = matches
        return Success()

    def get_camera_versions(self):
        pipe_context = get_pipe_context()
        self.project = pipe_context.get_project_obj()
        self.sequence = self.project.sequences.where(name=self.sequence_name)\
                        .first()
        self.shot = self.sequence.shots.where(name=self.shot_name).first()
        return camera_utils.get_all_anim_versions(self.shot)

    def connect_signals(self):
        item_clicked_func = lambda: self.revert_button.setEnabled(True)
        signal = QtCore.SIGNAL('clicked()')
        self.connect(self.cancel_button, signal, self.close)
        self.connect(self.revert_button, signal, self.revert)
        self.version_list.itemClicked.connect(item_clicked_func)

    def revert(self):
        camera_version = [version for version in self.camera_versions if \
            version.number == int(self.version_list.currentItem().text())][0]

        context = camera_version.get_path_context()
        chan_dir = context.get_path('sh_camera_version_dir')
        attrs, data, _shot_camera = camera_utils\
            .parse_chan_file(self.shot, chan_dir=chan_dir)
        if attrs and data:
            index = camera_utils.EYE_INDEX[self.eye_name]
            camera_utils.apply_chan_data(self.node, attrs[index], data[index])

            knobs = {}
            knobs['Cache Version'] = camera_version.number
            knobs['Cache Dir'] = chan_dir
            camera_utils.refresh_meta_knobs(self.node, **knobs)
        show_message('{0} reverted to version {1}'
                     .format(self.node.name(), camera_version.number),
                     'Revert Camera Notification')
        self.close()
