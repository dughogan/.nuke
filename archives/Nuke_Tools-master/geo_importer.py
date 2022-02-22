try:
    import nuke
except:
    pass
#Python standard lib modules
import os
import glob
import re
import sys

# Rfx modules
from pipe_core.pipe_context import WipContext, PipeContext
from pipe_core.pipe_enums import Discipline
from pipe_utils.io import IO
import nuke_tools.node_utils
from pipe_utils.response import Failure

def update_knobs(this_node=None):
    wip_ctx = WipContext.from_env()
    if not this_node:
        this_node = nuke.thisNode()
    with this_node:
        sequence_knob = this_node['Sequence']
        shot_knob = this_node['Shot']
        sequence_names = sorted([sequence.name for sequence in wip_ctx.get_project_obj().sequences.all()])
        sequence_knob.setValues(sequence_names)

def update_shot_knob(sequence_name):
    this_node = nuke.thisNode()
    wip_ctx = WipContext.from_env()
    project = wip_ctx.get_project_obj()
    sequence = project.find_sequence(sequence_name)
    shot_names = sorted([shot.name for shot in sequence.shots.all()])
    shot_knob = this_node['Shot']
    shot_knob.setValues(shot_names)


def knob_changed():
    this_node = nuke.thisNode()
    this_knob = nuke.thisKnob()
    with this_node:
        if this_knob.name() == 'Sequence':
            sequence_name = this_knob.value()
            update_shot_knob(sequence_name)
        elif this_knob.name() == 'break_out_btn':
            this_node.end()
            nuke.expandSelectedGroup()

def update_geo(this_node=None, show_dialogs=True):
    wip_ctx = WipContext.from_env()
    if not this_node:
        this_node = nuke.thisNode()
    sequence_knob = this_node['Sequence']
    shot_knob = this_node['Shot']
    shot_obj = wip_ctx.get_project_obj().find_sequence(sequence_knob.value()).find_shot(shot_knob.value())
    this_node['label'].setValue('Sequence: None Shot: None')
    with this_node:
        for node in (nuke.allNodes('ReadGeo2') + nuke.allNodes('Constant')):
            nuke.delete(node)
        geo_constant = nuke.nodes.Constant()  # @UndefinedVariable
        geo_color = this_node['geo_color'].getValue()
        geo_constant['color'].setValue(geo_color)
        geo_constant['disable'].setValue(this_node['disable_color'].getValue())
        scene = nuke.allNodes('Scene')[0]
        # Get the names of all the published assemblies associated with this shot
        published_assemblies = []
        for assembly_inst in shot_obj.assembly_instances:
          if not assembly_inst.active:
              continue
          assembly_override = assembly_inst.get_overrides()
          published_version = assembly_override.published_version
          if published_version:
              published_assemblies.append(published_version)
        assembly_names = []
        for assembly_version in published_assemblies:
          assembly_name = assembly_version.assembly_instance.name
          assembly_version_number = assembly_version.number
          assembly_names.append((assembly_name,assembly_version_number))
        # Get the directory which contains all of the cached alembic files
        pipe_ctx = PipeContext.from_pipe_obj(shot_obj)
        path_context = pipe_ctx.get_path_context()
        path_context.disc = 'matte'
        kwargs = {}
        store_dir = path_context.get_path('sh_comp_store_dir', **kwargs)
        dir_exists = _check_dir(store_dir, show_dialogs)
        if not dir_exists:
            return Failure(message='{0} does not exist.'.format(store_dir))
        cache_geo_dir = os.path.join(store_dir,'cache_geo')
        dir_exists = _check_dir(cache_geo_dir, show_dialogs)
        if not dir_exists:
            return Failure(message='{0} does not exist.'.format(cache_geo_dir))
        for assembly_name in assembly_names:
            name = assembly_name[0]
            assembly_dir = os.path.join(cache_geo_dir,name)
            dir_exists = _check_dir(assembly_dir, show_dialogs)
            if not dir_exists:
                return Failure(message='{0} does not exist.'.format(assembly_dir))
            cache_versions_glob = os.path.join(assembly_dir,'v*')
            versions = []
            for version_path in glob.glob(cache_versions_glob):
                version = int(re.match('.*v(\d{4})$',version_path).group(1))
                versions.append(version)
            last_version = sorted(versions)[-1]
            #latest_version_dir = os.path.join(assembly_dir,'v{0:04d}'.format(last_version))
            latest_version_dir = os.path.join(assembly_dir, 'published')
            dir_exists = _check_dir(latest_version_dir, show_dialogs)
            if not dir_exists:
                return Failure(message='{0} does not exist.'.format(latest_version_dir))
            alembic_glob = os.path.join(latest_version_dir,'*.abc')
            read_geo_nodes = []
            for alembic_file in glob.glob(alembic_glob):
                # If this isn't a hires alembic, and a hires alembic exists,
                # skip this file import
                if not re.match('^.*_hires.abc$', alembic_file):
                    hires_alembic_file = re.sub('.abc$', '_hires.abc',
                                                alembic_file)
                    if os.path.exists(hires_alembic_file):
                        continue
                read_geo_node = nuke.nodes.ReadGeo2()
                read_geo_node['file'].setValue(alembic_file)
                read_geo_node.setInput(0, geo_constant)
                scene.setInput(scene.inputs(),read_geo_node)
                read_geo_nodes.append(read_geo_node)
    this_node['label'].setValue('Sequence: {0} Shot: {1}'.format(sequence_knob.value(),shot_knob.value()))

def _check_dir(dir, show_dialogs):
    if not os.path.isdir(dir):
        message = 'Directory does not exist: {0}\nTry running geo_exporter again on the shot.'.format(dir)
        IO.error(message)
        if show_dialogs:
            from ui_lib.dialogs.popup import show_error
            show_error(message,"Update Geo Error")
        return False
    else:
        return True
