import os
import sys
import shutil

from pipe_utils.file_system import safe_make_dir
from pipe_core.pipe_enums import Discipline
from pipe_utils.io import IO

import nuke

def on_root_knob_changed():
    """
    Callback when a knob on the root node is changed.
    """
    from app_manager import session_manager
    sm = session_manager.SessionManager.inst()

    node = nuke.thisNode()
    knob = nuke.thisKnob()
    if node != nuke.root() or knob.name() != 'name':
        return

    if not sm.scene_manager.opening_scene:
        if knob.value() in ('', nuke.untitled):
            # the scene was cleared, run scene clear callbacks
            on_scene_cleared()

def add_callbacks():

    nuke.callbacks.addOnScriptClose(on_scene_closed)
    nuke.callbacks.addOnScriptLoad(on_scene_opened)
    nuke.callbacks.addOnScriptSave(on_scene_saved)
    nuke.callbacks.addOnCreate(on_create)
    # nuke.callbacks.addKnobChanged(knob_changed)
    nuke.callbacks.addKnobChanged(on_root_knob_changed,
                                  nodeClass='Root', node=nuke.root())
    nuke.callbacks.addBeforeRender(before_render)

def on_create():
    from nuke_tools import node_utils

    node = nuke.thisNode()
    # node_utils.rename_file_node(node)

def knob_changed():
    from nuke_tools import node_utils

    knob = nuke.thisKnob()
    if knob.name() == 'file':
        node = nuke.thisNode()
        # node_utils.rename_file_node(node)

def on_scene_saved():
    """
    Callback method to be made when the user clears the current scene.
    """
    from nuke_tools import utils

    root = nuke.root()
    filename = root.name()
    if os.path.exists(filename):
        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)
        base, ext = os.path.splitext(basename)
        inc_dir = os.path.join(dirname, 'incrementalSaves')
        version_path = os.path.join(inc_dir, base)
        if not os.path.exists(version_path):
            safe_make_dir(version_path, make_all=True)

        version = utils.get_latest_inc_version(version_path)
        save_name = '{0}.v{1:04d}.nk'.format(base, version)
        inc_save = os.path.join(version_path, save_name)

        shutil.copy(filename, inc_save)

        sys.stderr.write('IncrementalSave Generated {0}\n'.format(inc_save))

def on_scene_opened():
    """
    Modify the comp and render formats to reflect
    the newly opened scene's configurations
    """

    root = nuke.root()
    if root.knobs().has_key('open_callbacks') and not root['open_callbacks'].value():
        sys.stderr.write('Not adding script open callbacks!\n')
        return

    # Set our luts
    root['monitorLut'].setValue('srgb')
    root['int8Lut'].setValue('srgb')
    root['int16Lut'].setValue('srgb')
    root['floatLut'].setValue('linear')

    import script_utils
    import camera_utils

    is_gui = nuke.env['gui']
    if is_gui:
        from nuke_tools import matte_utils, node_utils, import_all_reference
        # matte_utils.refresh_matte_painting()

        # script_utils.set_favourites()
        if os.environ.get('DISC_NAME') == Discipline.COMP:
            sys.stderr.write('Adding Compositing Callbacks\n')
            script_utils.refresh_formats()
            script_utils.refresh_reads()
            node_utils.refresh_writes()
            node_utils.refresh_write_paths()
            import_all_reference.import_all_reference(show_dialogs=False)
        # elif os.environ.get('DISC_NAME') == Discipline.MATTE:
        #     camera_utils.refresh_all_cameras()

def on_scene_closed():
    pass

def on_scene_cleared():
    pass

