
#!/usr/bin/env python
#------------------------------------------------------------------------------#
#-------------------------------------------------------------------- HEADER --#

"""
:author:
    lkelly

:description:
    A brief one or two line description of this module.

A long description of this module which includes example usages and help for
a developer who is looking at this code for the first time.
"""

#------------------------------------------------------------------------------#
#------------------------------------------------------------------- IMPORTS --#

# built-in
import os
import re

# third-party
import nuke  # @UnresolvedImport

# internal
from nuke_tools.ui.progress_dialog import RProgressDialog

# external
import node_utils
from pipe_api.env import get_pipe_context
from pipe_core.pipe_enums import Discipline
from pipe_utils.io import IO
from pipe_utils.list_utils import to_list
from pipe_utils.response import Success, Failure
from ui_lib.dialogs.pipe_obj_explorer import RShotExplorer
from ui_lib.dialogs.popup import show_error

#------------------------------------------------------------------------------#
#------------------------------------------------------------------- GLOBALS --#

#------------------------------------------------------------------------------#
#----------------------------------------------------------------- FUNCTIONS --#

def import_matte_plates_ui():
    """
    Open a shot explorer dialog and impor the matte painting plates to a Read
    node from the selected shot(s).
    """
    context = get_pipe_context()

    source_dialog = RShotExplorer(allow_multiple_selection=True,
                                  active_only=True)
    source_dialog.explore_project(context.get_project_obj())
    result = source_dialog.exec_()
    if result:
        sequences = source_dialog.get_sequence_objs()
        shots = source_dialog.get_shot_objs()
        import_matte_plates(sequences, shots)
        
def import_matte_plates(sequences=None, shots=None):
    """
    Imports matte painting plates from the selected sequence(s) and shot(s).
    :param sequences: List of sequences
    :type sequences: List of pipe_core.model.pipe_obj.Sequence
    :param shots: List of shots
    :type shots: List of pipe_core.model.pipe_object.Shot
    """
    shots = to_list(shots)
    
    # Get all of the shots from the sequences
    if sequences:
        sequences = to_list(sequences)
        for sequence in sequences:
            shots.extend(sequence.shots.where(active=True).all())
    shots = sorted([tmp for tmp in shots if re.search('^\d+$', tmp.name)],
                   key=lambda x: int(x.name))
    
    # Show progress dialog as matte plates are imported
    dialog = RProgressDialog(message='Importing matte painting plates...',
                             minimum=1,
                             maximum=len(shots))
    dialog.setValue(0)
    
    # Used for creating the backdrop node which contains all of the matte
    # plate render Read nodes.
    matte_plates_ng = node_utils.RNukeNodeGraph()
    
    for i, shot in enumerate(shots):
        IO.info('Creating Read node for matte plate render Seq: {0} Shot: {1}'
                .format(shot.sequence.name, shot.name))
        dialog.setLabelText('Working on shot: {0} ({1} of {2})'
                            .format(shot.name, i + 1, len(shots)))
        # Create the Read node for the matte plate render.
        response = create_matte_plate_read(shot)
        if isinstance(response, Failure):
            show_error(response.message, "Matte Painting Plate Import: Error")
        else:
            read_node = response.payload
            matte_plates_ng.add_node(read_node)
        node_utils.clear_selection()
        dialog.setValue(i + 1)
    matte_plates_ng.create_backdrop(top=75, bottom=25, left=75, right=75,
                                    label='Matte Plate Renders',
                                    name='matte_plate_renders_backdrop',
                                    note_font_size=24)
    dialog.setValue(len(shots))
    

def create_matte_plate_read(shot):
    """
    Creates a Read node and sets it to the frame sequence for the given shot's
    matte painting plates.
    :param shot: The shot pipe object
    :type shot: pipe_core.model.pipe_object.Shot
    """
    wip = shot.wips.where(disc=Discipline.COMP, name='master').first()
    wcontext = wip.get_path_context()
    ext = shot.cinema.comp_format.extension
    plate_dir = wcontext.get_path('sh_matte_plate_dir',
                                  eye='%v',
                                  ext=ext,
                                  namespace='shot')
    if not os.path.exists(plate_dir):
        message = 'No matte painting plates exist for Seq: {0} Shot: {1} in '\
                  'directory {2}. Skipping Read node creation.'\
                  .format(shot.sequence.name, shot.name, plate_dir)
        IO.error(message)
        return Failure(message)
    
    plate_path = wcontext.get_path('sh_matte_plate_file',
                                 eye='%v',
                                 ext=ext,
                                 namespace='shot')
    read_name = 'Matte_Plate_Render_Seq_{0}_Shot_{1}'.format(shot.sequence.name,
                                                             shot.name)
    # Using nuke.createNode so that the nodes are created at the position last
    # clicked.
    read_node = nuke.createNode('Read')
    read_node['name'].setValue(read_name)
    read_node['first'].setValue(shot.frame_range.start)
    read_node['last'].setValue(shot.frame_range.end)
    read_node['file'].setValue(plate_path)
    return Success(payload=read_node)
    
    

#------------------------------------------------------------------------------#
#------------------------------------------------------------------- CLASSES --#

#------------------------------------------------------------------------------#
#-------------------------------------------------------- COMMAND-LINE ENTRY --#
