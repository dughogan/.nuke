#!/usr/bin/env python

"""
@author:
    dhogan

@description:
    - This is a set of general utilities for working in Nuke.

"""

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- IMPORTS --#
# built-in
import re
import os
import sys
import json
import shutil
import string
from collections import defaultdict
from glob import glob

# third party
try:
    import nuke  # IGNORE:F0401
except:
    pass  # IGNORE:W0702

# external
from app_manager import wip_manager
from app_manager.session_manager import SessionManager

from path_lib import get_path, split, formula_extract

from pipe_api.env import get_pipe_context

from pipe_core.pipe_context import PipeContext, WipContext
from pipe_core.pipe_enums import Discipline

from pipe_utils.response import Success, Failure
from pipe_utils.enumeration import EnumGroup, Enum
from pipe_utils.list_utils import to_list
from pipe_utils.dict_utils import printd

import node_utils
from nuke_tools import utils

#----------------------------------------------------------------------------#
#------------------------------------------------------------- ENUMERATORS --#
class Format(EnumGroup):
    """
    Enumeration of custom nuke format labels.
    """
    RENDER = Enum(0, 'RFX_RENDER')
    COMP = Enum(1, 'RFX_COMP')

#----------------------------------------------------------------------------#
#--------------------------------------------------------------- FUNCTIONS --#

#-----------------------------------------------------------------------------
#-------------------------------------------------- Nuke Script Cleaning Tools
#-----------------------------------------------------------------------------
def is_script_clean():
    """
    Checks for any nodes in the scene that are not there by default.
    """
    for node in nuke.allNodes():
        if node.Class() != 'Viewer':
            return False

    return True

def clean_script(silent=False, check=True, prompt=True):
    """
    Clears the current script and opens a blank scene.

    @type silent: bool
    @keyword silent: When true, this will bypass the
            on_script_clear callback on the session manager

    @type check: bool
    @keyword check: When true, this will check the script to see
            if it is already clean before taking any action and
            exit if it is already clean.

    @type prompt: bool
    @keyword prompt: When true, this will prompt the user and ask
            them if they want to clear the script before taking any
            action.  This only applies when nuke as a gui.
    """
    # if check is True, check that the script isn't
    # already clean before cleaning it.
    #
    if check:
        if is_script_clean():
            # if we are already clean then exit
            return Success('The script is already clean')
        elif prompt and nuke.env['gui']:
            # if we are not clean, prompt is enabled,
            # and nuke is not in batch mode, then prompt the user
            # if they want to clean the script.
            #
            from ui_lib.dialogs import popup
            prompt_result = popup.show_yes_no(
                    'Current script is not clean. Clear it?', 'Clear Script')
            if not prompt_result:
                return Failure('You decided not to clear the script')

    # clear the script and re-create the root node
    #
    nodes = nuke.allNodes()
    for n in nodes:
        nuke.delete(n)

    return Success('Successfully cleaned the script')

def choose_read_wip(pipe_ctx=None):

    from ui_lib.dialogs import popup
    from ui_lib.rnuke.old_widgets import RFXChoose

    if pipe_ctx == None:
        pipe_ctx = get_pipe_context()

    shot_obj = pipe_ctx.get_shot_obj()
    wips = shot_obj.find_wips(disc=Discipline.LIT).all()

    if len(wips) == 1:
        return wips[0].name

    title = "Choose Render WIP"
    msg = "Choose which WIP to pull render passes from."
    choices = []
    for w in wips:
        choices.append(w.name)

    choices.sort()

    prompt = RFXChoose(title, msg, choices)
    prompt.center_window()
    prompt.exec_()
    result = prompt.result
    return result

def version_up(pipe_ctx=None):
    """
    """
    # save the scene by versioning up the wip
    wmanager = wip_manager.WipManager.instance()
    response = wmanager.version_up()
    if not response:
        return response
    node_utils.refresh_writes()
    node_utils.refresh_write_paths()
    set_frame_range()
    return Success()

def set_favourites():
    wip = WipContext.from_env()

    directory = None
    context = wip.get_path_context()
    if context.has_vars('shot_name'):
        if context.has_vars('disc'):
            nuke.addFavoriteDir('{0} {2} {1} WORK'.format(context['seq_name'], context['shot_name'], context['disc']), context.get_path('sh_disc_dir'))
            nuke.addFavoriteDir('{0} {2} {1} RENDER'.format(context['seq_name'], context['shot_name'], context['disc']), context.get_render_path('sh_disc_dir'))
        if context.has_vars('wip_name'):
            nuke.addFavoriteDir('{0} {2} {1} WORK'.format(context['seq_name'], context['shot_name'], context['wip_name']), context.get_path('sh_wip_dir'))
            nuke.addFavoriteDir('{0} {2} {1} RENDER'.format(context['seq_name'], context['shot_name'], context['wip_name']), context.get_render_path('sh_wip_dir'))

    if context.has_vars('disc'):
        nuke.addFavoriteDir('{0} {1} WORK'.format(context['seq_name'], context['disc']), context.get_path('sq_disc_dir'))
    if context.has_vars('wip_name'):
        nuke.addFavoriteDir('{0} {1} WORK'.format(context['seq_name'], context['wip_name']), context.get_path('sq_wip_dir'))

#-----------------------------------------------------------------------------
#----------------------------------------------------------- Frame Range Tools
#-----------------------------------------------------------------------------
def set_frame_range(pipe_ctx=None):
    # get pipe context
    #
    if pipe_ctx is None:
        pipe_ctx = get_pipe_context()

    # get the shot's frame range
    #
    shot = pipe_ctx.get_shot_obj()
    frame_range = shot.get_frame_range()

    # set the frame range
    #
    root = nuke.toNode('root')
    current_frame = root['frame'].value()

    root['first_frame'].setValue(float(frame_range.start))
    root['last_frame'].setValue(float(frame_range.end))
    root['lock_range'].setValue('1')

    # set the current frame to the start frame
    #
    if not current_frame in xrange(frame_range.start, frame_range.end + 1):
        nuke.frame(int(frame_range.start))

    ## go to the first key frame.  If one is
    ## not set then go to the first frame
    ## NOTE: we are simply doing this to try and get to a frame
    ##   this is so that we can pull AOVs and shuffle them out.
    ##
    #if len(shot.key_frames):
        #frame = shot.key_frames[0]
    #else:
        #frame = frame_range.start
    #nuke.frame(int(frame))

    return Success('Successfully set the frame range', frame_range)

#def set_key_frames(pipe_ctx=None):
    ## get pipe context
    ##
    #if pipe_ctx is None:
        #pipe_ctx = get_pipe_context()

    ## get the shot's frame range
    ##
    #shot = pipe_ctx.get_shot_obj()
    #frame_range = shot.key_frames

    #key_frames = rfxUtils.getShotKeyFrames(department, project, seq, shot).split(',')
    #if key_frames:
        #nuke.frame(int(key_frames[0]))

def set_frame_rate(pipe_ctx=None):
    # get pipe context
    #
    if pipe_ctx is None:
        pipe_ctx = get_pipe_context()

    # get the shot's frame range
    #
    shot = pipe_ctx.get_shot_obj()
    frame_rate = shot.cinema.frame_rate

    # set the frame rate
    #
    root = nuke.toNode('root')
    root['fps'].setValue(float(frame_rate.fps))

def script_get_type():
    from ui_lib.dialogs import popup

    msg = 'Please choose a script type:'
    title = 'Script Type'
    buttons = ['shot', 'pre_comp', 'contact_sheet', 'misc']
    prompt_result = popup.show_options(msg= msg, title=title, buttons=buttons)
    return prompt_result

def script_check_type():
    root = nuke.toNode('root')
    script_types = ['shot', 'pre_comp', 'contact_sheet', 'misc']

    if not 'script_type' in root.knobs():
        return 0
    else:
        script_type = root['script_type'].value()
        if not script_type in script_types:
            return 0
    return script_type


def script_write_type(type_arg = None):
    root = nuke.toNode('root')

    script_type = type_arg
    if not 'RFX' in root.knobs():
        tab = nuke.Tab_Knob('RFX')
        root.addKnob(tab)
    if not 'script_type' in root.knobs():
        type_knob = nuke.String_Knob('script_type')
        root.addKnob(type_knob)
    if script_type:
        root['script_type'].setValue(script_type.lower())
    else:
        sys.stderr.write("Script type attribute not set on the class. Getting it from user\n")
        script_type = get_script_type()

    if not script_type:
        return 0

    root['script_type'].setValue(script_type.lower())
    return script_type

def make_stereo():
    """
    Delete the default main view and add a left and right.
    """
    if 'main' in nuke.views():
        nuke.deleteView('main')
    if not 'left' in nuke.views():
        nuke.addView('left')
    if not 'right' in nuke.views():
        nuke.addView('right')

    return True

def make_not_stereo():
    """
    Remove the left and right eye views from a script
    and re-add the default main view.
    """
    if 'left' in nuke.views():
        nuke.deleteView('left')
    if 'right' in nuke.views():
        nuke.deleteView('right')
    if not 'main' in nuke.views():
        nuke.addView('main')

    for node in node_utils.get_all_nodes(node_filters=['Read', 'DeepRead']):
        filename = node['file'].value()
        new_filename = re.sub('[\._]%v\.', '', filename)
        node['file'].setValue(new_filename)
        if node.Class() == 'Write':
            node['views'].setValue('main')

def get_format(name=None, pipe_context=None):
    if not name:
        name = Format.RENDER
    result = False
    if pipe_context is None:
        pipe_context = get_pipe_context()
    pipe_obj = pipe_context.get_pipe_obj()
    if pipe_obj is None:
        return result

    render_format = None
    #Adjust Render Format if Disable Format Resolution Global is used
    root = nuke.root()
    if root.knobs().has_key('open_callbacks') and not root['open_callbacks'].value():
        render_format = root['format'].value()
        return render_format
    #Check for Global Format if no override      
    formats = nuke.formats()
    formats.reverse()
    for nformat in formats:
        print nformat
        if nformat.name() == name:
            render_format = nformat
            break
    # If the render res format doesn't exist, create it.
    # Otherwise, edit it
    if render_format is None:
        render_format = nuke.addFormat('%s %s %s %s' % (pipe_obj.render.render_res.width,
                                                        pipe_obj.render.render_res.height,
                                                        1, Format.RENDER))
    else:  
        render_format.setWidth(pipe_obj.render.render_res.width)
        render_format.setHeight(pipe_obj.render.render_res.height)
        render_format.setPixelAspect(1)

    return render_format

def refresh_formats(pipe_context=None):

    render_format = get_format(pipe_context=pipe_context)
    nodes = nuke.allNodes()
    for node in nodes:
        if node.Class() == 'Read' or node.Class() == 'DeepRead':
            if render_format is not None:
                node['format'].setValue(render_format)
                node['proxy_format'].setValue(render_format)
    root = nuke.root()
    root['format'].setValue(render_format)

def refresh_reads():

    nodes = node_utils.node_query(filters=['Read', 'DeepRead'])
    for node in nodes:
        node['proxy'].setValue('')

#-----------------------------------------------------------------------------
#----------------------------------------------------------------- Other Tools
#-----------------------------------------------------------------------------


def get_seq_shot_dictionary(pipe_ctx = None, only_active = True):
    if pipe_ctx is None:
        pipe_ctx = get_pipe_context()

    active = only_active

    proj_obj = pipe_ctx.get_project_obj()

    sequences = proj_obj.get_sequences_in_edit_order(only_active = active)
    seq_and_shots = {}

    for s in sequences:
        seq_and_shots[s.name] = []
        shots = s.get_shots_in_edit_order(only_active = False)
        for sh in shots:
            seq_and_shots[s.name].append(sh.name)

    return seq_and_shots

def get_latest_output_version(pipe_ctx=None):
    if pipe_ctx is None:
        pipe_ctx = get_pipe_context()

    path_ctx = pipe_ctx.get_path_context()
    path = path_ctx.get_path('sh_comp_output_dir', version='[0-9]*',
                             namespace='shot')
    version_paths = sorted([tmp for tmp in glob(path) if os.path.isdir(tmp)])
    if not len(version_paths):
        return 0

    response = formula_extract('sh_comp_output_dir', version_paths[-1],
                               namespace='shot',)
    if not response:
        response.raise_exception()

    return response.payload.version

def find_missing_comp_frames(pipe_ctx=None):
    if pipe_ctx is None:
        pipe_ctx = get_pipe_context()
    path_ctx = pipe_ctx.get_path_context()
    path = path_ctx.get_path('sh_comp_wip_output_file', eye='%v', ext='exr', namespace='shot')
    sequence = utils.RSequence(path=path)
    pipe_obj = pipe_ctx.get_pipe_obj()
    missing = sequence.find_missing_frames(start_frame=pipe_obj.frame_range.start,
                                           end_frame=pipe_obj.frame_range.end)
    return missing

def find_missing_frames():
    missing = defaultdict(dict)
    filters = ['Read', 'DeepRead']
    nodes = node_utils.get_selected_nodes(filters=filters)
    if not nodes:
        nodes = node_utils.node_query(filters=filters)
    for node in nodes:
        first_frame = node['first'].value()
        last_frame = node['last'].value()
        path = node['file'].value()

        sequence = utils.RSequence(path=path)
        node_missing = sequence.find_missing_frames(start_frame=node['first'].value(), end_frame=node['last'].value())
        if node_missing:
            name = node['name'].value()
            missing[name] = defaultdict(dict)
            missing[name]['path'] = path
            missing[name]['missing'] = node_missing

    missing_string = ''
    tab = ' ' * 4
    for key in missing.keys():
        missing_string = '{0}Node: {1}:\n'.format(missing_string, key)
        path = missing[key]['path']
        missing_string = '{0}{tab}Path: \n{tab}{tab}{1}:\n'.format(missing_string, path, tab=tab)
        for eye in missing[key]['missing']:
            missing_string = '{0}{tab}Eye: {1}\n'.format(missing_string, eye, tab=tab)
            for missing_range in missing[key]['missing'][eye]:
                missing_string = '{0}{tab}{tab}{1}-{2}\n'.format(missing_string, missing_range[0], missing_range[1], tab=tab)

    if not missing_string:
        missing_string = 'No Missing Frames'

    panel = nuke.Panel('Missing Frame Report')
    panel.setWidth(750)
    panel.addMultilineTextInput('Missing Frames:', missing_string)
    panel.show()

