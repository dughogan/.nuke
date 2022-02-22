#!/usr/bin/python

"""
@author:
    dhogan

@description:
    utilities for rendering scripts

"""

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- IMPORTS --#
# built-in
import re
import os
import sys
import shutil
import glob

# third-party
import nuke

# internal
# from nuke_tools import script_utils, node_utils, utils
from nuke_tools import node_utils, script_utils, utils

# external
from app_manager import nuke_executer
from path_lib import collapse_env_vars
from pipe_api.env import get_pipe_context, ENV
from pipe_core.pipe_enums import RenderVenue
from pipe_core.pipe_context import PipeContext
from pipe_utils import file_system, xml_utils
from pipe_utils.response import Success, Failure
from pipe_utils.xml_utils import ElementTree as ET
from pipe_core import PipeContext
from pipe_core.model.config_utils import ImageFormat


#----------------------------------------------------------------------------#
#------------------------------------------------------------------FARM LIBS-#
from farm_lib.qube_job import QubeJob
from farm_lib.qube_submitter import QubeSubmitter
from farm_lib.farm_utils import QubeAgenda
from farm_lib.farm_enums import FrameDistribution, JobType, QubeLanguage
from pipe_utils.email_utils import get_email_address
from pipe_utils.system_utils import get_user
import farm_lib.farm_utils as fu

VALID_PATH = re.compile('^[/0-9a-zA-Z\.]+$')

#----------------------------------------------------------------------------#
#--------------------------------------------------------------- FUNCTIONS --#
def get_rfx_write_nodes():
    # find all enabled rfx write nodes
    #
    write_nodes = []
    for node in node_utils.get_all_nodes('Write'):
        if node['disable'].value():
            continue
        #if node_utils.is_rfx():
            #write_nodes.append(node)
        write_nodes.append(node)

    return write_nodes

def check_scene(multiple_writes=False):
    # test if the current script has a name
    #
    root = nuke.root()
    orig_script_name = root.name()
    if orig_script_name == 'Root':
        return Failure('The script has no name.  Please name your '
                'script before submitting it to the farm.')

    # find all enabled rfx write nodes
    #
    write_nodes = get_rfx_write_nodes()

    # check the number of write nodes for errors
    #
    count = len(write_nodes)
    if count == 0:
        return Failure('You do not have any Write nodes enabled '
                'in this script putz. Please enable one Write '
                'node and check it\'s path')
    elif len(write_nodes) > 1 and not multiple_writes:
        return Failure('You have too many Write nodes '
                'enabled in this script putz. Please '
                'disable all but one Write node')

    # check for write nodes with the same output paths
    #
    output_paths = []
    for node in write_nodes:
        #if node['file_type'].value() == 'dpx':
            #time_code_value = (
                    #'[format %02d [expr [frame] / ({fps} * 60 * 60)]]'
                    #'[format %02d [expr [frame] / ({fps} * 60)]]'
                    #'[format %02d [expr [frame] / {fps}]]'
                    #'[format %02d [expr [frame] % {fps}]]')
            #time_code_value = time_code_value.format(
                    #fps=int(round(float(root['fps'].value()))))
            #node['timecode'].setValue(time_code_value)
        output_path = node['file'].value()
        # if output_path in output_paths:
        #     return Failure('Two or more write nodes have the same path: %s' %
        #             output_path)
        output_paths.append(output_path)

    return Success()

def create_instructions(xml_file, **kwargs):
    # create xml root
    #
    root = ET.Element('renderInstructions', **kwargs)
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

def submit(pipe_ctx=None, venue=RenderVenue.FARM, **kwargs):
    """
    Submission to Qube from Nuke
    """
    if venue is not RenderVenue.FARM:
        raise NotImplementedError(
                'Support has not been added for local submissions.')

    # get a pipe context
    #
    if pipe_ctx is None:
        pipe_ctx = get_pipe_context()

    # error if this is not a wip context
    #
    if not isinstance(pipe_ctx, PipeContext):
        raise TypeError('"%s" is not a wip context' % pipe_ctx)

    # check the current scene for errors
    #
    response = check_scene(
            multiple_writes=kwargs.get('multiple_writes', False))
    if response.success is False:
        return response

    # retrieve the scene name
    #
    root = nuke.root()
    script_name = root.name()

    # version up if the user has the version up
    # checkbox selected
    if kwargs['version_up'] is True:
        script_utils.version_up(pipe_ctx)
        # wip_manager.WipManager.instance().version_up()

    nuke.scriptSave()
    py_script = ENV.get_pkg_file('nuke_tools', 'render.py')

    job_settings = kwargs.copy()
    job_settings['user'] = get_user()
    job_settings['padding'] = '4'
    job_settings['callbacks'] = []
    job_settings['frame_range'] = None
    # can only run 1 core in local mode
    if job_settings['allow_local'] is True:
        job_settings['cpus'] = 1
        job_settings['reservations'] = ['host.processors=1']
    elif job_settings['heavy_render']:
        job_settings['reservations'] = ['host.processors=4+']
    else:
        job_settings['reservations'] = ['host.processors=2']

    if job_settings['interactive'] is True:
        job_settings['clusters'] = 'nukex'


    if job_settings['wait_for'] != '':
        job_settings['dependency'] = \
            'complete-job-%s' % job_settings['wait_for']

    # get a path to the scene and store the script file
    # elsewhere (i.e. scene archiving).
    path_ctx = pipe_ctx.get_path_context()
    pipe_obj = pipe_ctx.get_shot_obj()
    if not pipe_obj:
        pipe_obj = pipe_ctx.get_sequence_obj()
    if not pipe_obj:
        pipe_obj = pipe_ctx.get_project_obj()

    script_basename = os.path.basename(script_name)
    wip_filename = os.path.splitext(script_basename)[0]
    label = job_settings.get('label')
    if not label:
        label = 'standard'

    # Now time to repoint the read nodes to their actual paths.
    reads = node_utils.node_query(filters='Read')
    original_paths = []
    for read in reads:
        path = read['file'].value()
        dirname = os.path.dirname(path)
        if VALID_PATH.search(dirname):
            realdir = os.path.realpath(dirname)
            basename = os.path.basename(path)

            new_path = os.path.join(realdir, basename)
            read['file'].setValue(new_path)

        original_paths.append(path)

    nuke.scriptSave()

    cache_scene = get_cache_scene_info(path_ctx, wip_filename, script_name,
                                       label)

    for i, read in enumerate(reads):
        read['file'].setValue(original_paths[i])

    nuke.scriptSave()

    # find all enabled rfx write nodes
    write_nodes = get_rfx_write_nodes()

    # create the write node directories.
    for node in write_nodes:
        # get the base directory
        render_dir = file_system.split(node['file'].evaluate())[0]

        # get render scene path and copy the current scene to that location
        if not os.path.exists(render_dir):
            file_system.safe_make_dir(render_dir, make_all=True)

    # create a nuke executer to pass to the qube job
    executer = nuke_executer.NukeExecuter(pipe_ctx)
    executer.batch_mode = True
    executer.py_script = py_script
    executer.startup_scene = collapse_env_vars(cache_scene)
    executer._init_versions()

    # create a qube job for this write node

    executer.threads = job_settings['threads']

    # set up frame sets
    frame_set = job_settings['frame_sets']
    chunksize = job_settings.pop('chunksize')
    frame_sets = frame_set.subdivide(int(chunksize))
    job_settings['agendas'] = \
        QubeAgenda.gen_frame_set_tasks(frame_sets, FrameDistribution.FULL)

    # label
    # pipe_ctx = WipContext.from_path_context(path_ctx)
    ver = pipe_ctx.wip_version
    job_settings['output_version'] = ver
    qube_job = QubeJob(executer, 'NukeRender', JobType.COMP, **job_settings)
    qube_job.add_work_retries(job_settings.get('retrywork', 2))

    # setup email
    lang = QubeLanguage.get_enum('mail')
    user = get_user()
    email = get_email_address(user)
    code = ''
    qube_job.add_callback(code, fu.QubeTrigger.get_fail_self_trigger(),
                          language=lang)
    qube_job.add_callback(code, fu.QubeTrigger.get_complete_self_trigger(),
                          language=lang)
    qube_job.add_callback(code, fu.QubeTrigger.get_kill_self_trigger(),
                          language=lang)

    qube_job.job['mailaddress'] = email

    create_matte_plates = kwargs.pop('create_matte_plates', False)
    # Create the matte painting plate render job
    if create_matte_plates:
        matte_plate_job = create_matte_painting_plate_job(pipe_ctx,
                                                          job_settings,
                                                          script_name)

    # submit jobs
    submitter = QubeSubmitter()
    submitter.append(qube_job)
    if create_matte_plates:
        submitter.append(matte_plate_job)
    if job_settings['allow_local'] is True:
        submission_result = submitter.submit_to_self()
    else:
        submission_result = submitter.submit()
        if not submission_result:
            submission_result.raise_exception()

    return submitter

def create_matte_painting_plate_job(pipe_ctx, job_settings, script_name):
    """
    Creates the Qube job for generating matte painting plates which the painters
    can use to preview the lighting comp over their mattes.
    """
    script_basename = os.path.basename(script_name)
    wip_filename = os.path.splitext(script_basename)[0]
    path_ctx = pipe_ctx.get_path_context()
    cache_scene = get_cache_scene_info(path_ctx, wip_filename, script_name,
                                       label='matteplate')

    matte_plate_subpath = os.path.join('batch', 'matte_plate_render.py')
    plate_script = ENV.get_pkg_file('nuke_tools', matte_plate_subpath)
    # Create a nuke executer to pass to the qube job
    executer = nuke_executer.NukeExecuter(pipe_ctx)
    executer.batch_mode = True
    executer.py_script = plate_script
    executer.startup_scene = collapse_env_vars(cache_scene)
    executer._init_versions()
    # Create the Qube job to run on the farm
    qube_job = QubeJob(executer, 'NukeMattePlateRender', JobType.MATTE,
                       **job_settings)
    qube_job.add_work_retries(job_settings.get('retrywork', 2))
    return qube_job

def get_cache_scene_info(path_ctx, wip_filename, script_name, label):
    """
    Returns the file path to the cached version of the scene to use for the farm
    jobs, and creates the directory structure to it if it doesn't exist.
    """
    if path_ctx.has_vars('shot_name'):
        cache_dir = path_ctx.get_path('sh_comp_store_script_dir',
                                      wip_filename=wip_filename)
        version = utils.get_latest_inc_version(cache_dir)
        cache_scene = path_ctx.get_path('sh_comp_store_script_file',
                                        wip_filename=wip_filename,
                                        label=label,
                                        version=version)
    elif path_ctx.has_vars('seq_name'):
        cache_dir = path_ctx.get_path('sq_comp_store_script_dir',
                                      wip_filename=wip_filename)
        version = utils.get_latest_inc_version(cache_dir)
        cache_scene = path_ctx.get_path('sq_comp_store_script_file',
                                        wip_filename=wip_filename,
                                        label=label,
                                        version=version)
    else:
        cache_dir = path_ctx.get_path('pr_comp_store_script_dir',
                                      wip_filename=wip_filename)
        version = utils.get_latest_inc_version(cache_dir)
        cache_scene = path_ctx.get_path('pr_comp_store_script_file',
                                        wip_filename=wip_filename,
                                        label=label,
                                        version=version)
    # If the directory structure doesn't exist, create it.
    if not os.path.exists(cache_dir):
        file_system.safe_make_dir(cache_dir, make_all=True)
    # Create the cache scene file
    shutil.copy(script_name, cache_scene)
    sys.stderr.write('Creating Cached Scene: {0}\n'.format(cache_scene))
    return cache_scene

def main(*args, **kwargs):
    """
    Main entry point for Nuke.
    Get all the write nodes and render them in order of execution.
    """
    sys.stderr.write('Beginning render\n')
    writes = node_utils.get_all_nodes('Write', True, False)
    ordered_writes = sorted(writes, key=lambda x: x['render_order'].value())
    #print ordered_writes
    rformat = script_utils.get_format()
    crop_node = node_utils.create_node('Crop')
    crop_node['box'].setValue(rformat.x(), 0)
    crop_node['box'].setValue(rformat.y(), 1)
    crop_node['box'].setValue(rformat.r(), 2)
    crop_node['box'].setValue(rformat.t(), 3)
    
    #print format info for Render Info
    print 'Format Name: {0}'.format(rformat.name())
    print 'Height: {0}'.format(rformat.height())
    print 'Width: {0}'.format(rformat.width())
    
    result = 0
    # node_input = None
    for node in ordered_writes:
        node_input = None
        sys.stderr.write('Rendering from Write: {0}\n'
                         .format(node['name'].value()))

        # Don't hookup the crop node!
        if node_utils.is_rfx(node):
            node_input = node.input(0)
            if node_utils.is_node_type(node_input, 'Reformat'):
                format_name = '{0}_render'.format(node_utils.PROJ_NAME)
                sys.stderr.write('Setting {0}\'s format to {1}.\n'
                                 .format(node_input.name(), format_name))
                node_input['format'].setValue(format_name)
            node.setInput(0, crop_node)
            crop_node.setInput(0, node_input)
            
        agenda = QubeAgenda.from_env()
        frame_list = agenda.to_frame_range_list()

        # get path to image
        write = node['name'].value()
        
        # get extension of image
        filetype = node['file_type'].value()
        extension = ImageFormat.get_enum(filetype).extension

        # for rfxwrite nodes
        regex = re.search("rfxw", write, re.I)
        pipe_ctx = PipeContext.from_env()
        pipe_obj = pipe_ctx.get_pipe_obj()
        path_ctx = pipe_ctx.get_path_context()
        path = path_ctx.get_path('sh_comp_wip_output_file', eye='*',
                                 ext=extension, namespace='shot')
        re_path = re.sub('%04d', '*', path)
        # for normal write nodes
        if not regex:
            node_path = nuke.toNode(node['name'].value())
            path = node_path['file'].getValue()
            re_path = re.sub('%04d', '*', str(path))
            re_path = re.sub('%v', '*', re_path)
        # check if frames exist
        for frng in frame_list:
            try:
                nuke.execute(node, frng.start, frng.end, frng.inc)
            except RuntimeError, err:
                sys.stderr.write('ERROR: {0}\n'.format(err))
                print "Test1"
                result += 1
            frame_exist = False
            for glob_path in glob.glob(re_path):
                rex = re.match('.*\.(\d+)\.[a-zA-Z][a-zA-Z][a-zA-Z]', glob_path)
                frame_num = int(rex.group(1))
                if frame_num >= frng.start and frame_num <= frng.end:
                    frame_exist = True
            if not frame_exist:
                sys.stderr.write('ERROR: frames between {0} '
                                 'and {1} missing:'.format(frng.start,
                                                           frng.end))
                result += 1
                print "Test2"
            if result > 0:
                print 'Failed to execute Nuke node: %s' % node
        if node_input:
            node.setInput(0, node_input)
            if node_utils.is_node_type(node_input, 'Reformat'):
                format_name = '{0}_comp'.format(node_utils.PROJ_NAME)
                sys.stderr.write('Setting {0}\'s format to {1}.\n'
                                 .format(node_input.name(), format_name))
                node_input['format'].setValue(format_name)

    nuke.delete(crop_node)

    sys.stderr.write('Finished render\n')

    sys.exit(result)

