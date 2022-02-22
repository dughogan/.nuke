import re
import os
import sys
import glob
import math
import time
import shutil
from collections import defaultdict
from xml.etree import cElementTree
from pipe_data.field import DateTimeField
from path_lib.extractor import formula_extract

try:
    from nuke_tools import node_utils, utils, script_utils
    import nuke 
except:
    pass 
from tempfile import NamedTemporaryFile

try:
    import camera_utils
except:
    pass

from pipe_core import Sequence, Shot
from pipe_core.pipe_enums import Discipline, ContextType
from pipe_core.pipe_context import WipContext, PipeContext
from pipe_core.model.wip_version import WipVersion
from pipe_core.model.media_obj import MediaVersion

from pipe_api.env import get_pipe_context
from path_lib.utils import join

from pipe_utils.list_utils import to_list
from pipe_utils.system_utils import get_user
from pipe_utils.sequence import FrameRange, FrameSequence, FrameSet
from pipe_utils.response import Success, Failure, ResponseList
from pipe_utils.response import Warning  # IGNORE:W0622
from pipe_utils import xml_utils
from pipe_utils import file_system
from pipe_utils.email_utils import get_email_address
from pipe_utils.io import IO
from pipe_utils.application import Application

from app_manager import wip_manager
from app_manager.cmd_executer import CmdExecuter
from app_manager.nuke_executer import NukeExecuter
from app_manager.session_manager import SessionManager

from farm_lib.qube_job import QubeJob
from farm_lib.farm_enums import JobType, QubeLanguage, FrameDistribution
import farm_lib.farm_utils as farm_utils
from farm_lib.farm_utils import QubeAgenda

DEFAULT_RENDER_FARM_SETTINGS = {'cpus': 5,
                                'chunksize': 1,
                                'cache': 2650,
                                'threads': '2',
                                'retrywork': 2,
                                'heavy_render': False,
                                'priority': 2000,
                                'clusters': 'nuke_matte'}

DEFAULT_MEDIA_FARM_SETTINGS = {'allow_local': True,
                               }

MEDIA_SUBMISION_TOOL = \
    'python $PKG_NUKE_TOOLS/batch/matte_media_submission.py'
RENDER_TOOL = '$PKG_NUKE_TOOLS/batch/matte_render.py'

ANSI_COLORS = {'red': '\033[91m',
               'yellow': '\033[93m',
               'green': '\033[92m',
               'end_color': '\033[0m'}

NO_ANSI_COLORS = {'red': '', 'yellow': '', 'green': '', 'end_color': ''}


def switch_camera_switches(name):
    camera_switches = node_utils.node_query(filters='Group', attrs=['shot'])
    check = re.compile('{0}.*'.format(name))
    for switch in camera_switches:
        items = switch['shot'].values()
        for item in items:
            if check.search(item):
                switch['shot'].setValue(item)
                break


def create_one_off(t_pipe_objs, **kwargs):
    tmp_handle = NamedTemporaryFile('rw')
    nuke.nodeCopy(tmp_handle.name)
    s_wipc = WipContext.from_env()
    s_wip = s_wipc.get_wip_obj()
    wmanager = wip_manager.WipManager.instance()
    if len(nuke.selectedNodes()) == 0:
        message = "No nodes selected to create one-off."
        IO.error(message)
        return Failure(message)

    nuke.scriptSave()

    t_wips = []

    for t_pipe_obj in t_pipe_objs:
        # Determine what the version number should be before we create the wip
        # file so that we know what to name it
        t_wip = t_pipe_obj.wips.where(name=s_wip.name, disc='MATTE').first()
        if t_wip:
            if len(t_wip.versions) > 0:
                version = t_wip.versions.get_last().number + 1
            else:
                version = 1
        else:
            version = 1

        wip_kwargs = {}
        wip_kwargs['application'] = 'NUKE'
        if s_wipc.context_type == ContextType.SHOT:
            wip_kwargs['note'] = 'One-off from {0}_{1} WIP: {2} version: {3}'\
                .format(s_wip.parent.sequence.name, s_wip.parent.name,
                        s_wip.name, s_wipc.get_wip_version_obj().number)
        elif s_wipc.context_type == ContextType.SEQUENCE:
            wip_kwargs['note'] = 'One-off from {0} WIP: {1} version: {2}'\
                .format(s_wip.parent.name, s_wip.name,
                        s_wipc.get_wip_version_obj().number)
        wip_kwargs['owner'] = get_user()

        # If the WIP object exists, version it up as the next highest version
        # from the source WIP's version
        t_wip_ctx = None
        if t_wip:
            t_wip_ctx = WipContext.from_pipe_obj(t_wip)

            # Create the WIP file before we make the actual WIP so that file
            # paths can be repointed, and the Root node info can be added in
            wip_file = create_wip_file(t_pipe_obj, version, tmp_handle)
            nuke.scriptClear()
            nuke.scriptOpen(wip_file)
            if version > 1:
                response = wmanager.version_up(version, t_wip_ctx,
                                               **wip_kwargs)
                if response.is_success():
                    t_wip_ctx = response.payload
                else:
                    response.print_message()
                    return response
            else:
                wip_version = t_wip.versions.new(1, note=wip_kwargs['note'])
                t_wip.save()
                t_wip_ctx.set_wip_version_obj(wip_version)
                wmanager.save_wip_version(t_wip_ctx)
            t_wip = t_wip_ctx.get_wip_obj()
        else:
            wip_context = WipContext.from_pipe_obj(t_pipe_obj)
            wip_context.wip = s_wip.name
            wip_context.discipline = 'MATTE'
            wip_context.wip_version = version
            args = (wip_context, True)
            # This always returns a wip context at version one...
            app = Application.NUKE
            versions_dict = wmanager.get_app_version_dict()
            app_version = versions_dict.get(app)
            kwargs = {}
            kwargs['application'] = app
            kwargs['note'] = 'Main Nuke WIP for Matte Painting'
            kwargs['owner'] = get_user()
            if app_version is not None:
                kwargs['app_version'] = app_version.name
            response = wmanager.create_wip_context(*args, **kwargs)
            if isinstance(response, Failure):
                IO.error('{0}\n'.format(str(response)))
                return response
            t_wip_ctx = response.payload
            # Create the WIP file before we make the actual WIP so that file
            # paths can be repointed, and the Root node info can be added in
            wip_file = create_wip_file(t_pipe_obj, version, tmp_handle)
            # create_wip_context opens up the new file for the first wip
            # version. In order to prevent version_up from over-writing the wip
            # version we actually care about, it needs to be open before
            # version_up runs.
            nuke.scriptClear()
            nuke.scriptOpen(wip_file)
            t_wip = t_wip_ctx.get_wip_obj()
            wip_version = t_wip.versions.get_last()
            t_wip_ctx.set_wip_version_obj(wip_version)

            t_wip = t_wip_ctx.get_wip_obj()  # IGNORE:E1103
        t_wips.append(t_wip)

        # Update the launcher to reflect the new wip context
        session_mgr = SessionManager.inst()
        if session_mgr:
            session_mgr.on_context_changed(t_wip_ctx)

    response = Success('One-off(s) successfully created.', payload=t_wips)
    return response


def create_wip_file(t_pipe_obj, version, tmp_handle):
    kwargs = {'version': '{0:03d}'.format(version), 'publish_type': 'setup',
              'wip_name': 'master', 'disc': 'matte', 'ext': 'nk'}

    path_context = t_pipe_obj.get_path_context()
    if t_pipe_obj.CONTEXT_TYPE == ContextType.SHOT:
        wip_file = path_context.get_path('sh_wip_file', **kwargs)
        wip_dir = path_context.get_path('sh_wip_dir', **kwargs)
    elif t_pipe_obj.CONTEXT_TYPE == ContextType.SEQUENCE:
        wip_file = path_context.get_path('sq_wip_file', **kwargs)
        wip_dir = path_context.get_path('sq_wip_dir', **kwargs)
    if not os.path.exists(wip_dir):
        os.makedirs(wip_dir)

    if os.path.exists(wip_file):
        os.remove(wip_file)

    paint_dir = os.path.join(wip_dir, 'paint')
    if not os.path.exists(paint_dir):
        os.mkdir(paint_dir)

    psd_files = []
    # Create the new WIP file before the WIP objects are made or versioned up
    scene_handle = open(wip_file, 'w')
    tmp_handle.seek(0)
    for line in tmp_handle.readlines():
        new_line = line
        if re.match('^\w*file\w*', line.strip()):
            knob_name = re.match('(^\w*file\w*)', line.strip()).group(1)
            split = line.split()
            path = ' '.join(split[1:]).strip('"')
            tmp_path = utils.RPath(path=path)
            if re.match('.*[\[\]].*', path) or path == '' or \
            knob_name == 'file_type':
                scene_handle.write(new_line)
                continue
            base_name = tmp_path.get_basename()
            new_path = get_target_path(tmp_path.get_path(), wip_dir)
            new_line = ' {0} {1}'.format(knob_name,new_path)
            # If the base name contains # symbols, it is a sequence of images
            if re.match('.*\.####\....$', base_name):
                name_prefix = re.match('(.*\.)####\....$', path).group(1)
                name_postfix = re.match('.*\.####(\....$)', path).group(1)
                images_glob = '{0}*{1}'.format(name_prefix, name_postfix)
                for image_path in glob.glob(images_glob):
                    new_image_path = get_target_path(image_path, wip_dir)
                    try:
                        shutil.copyfile(image_path, new_image_path)
                    except IOError:
                        IO.error('Could not find file at {0}'
                                 .format(image_path))
            # This is just a single image
            else:
                try:
                    if path != new_path:
                        shutil.copyfile(path, new_path)
                except IOError:
                    IO.error('Could not find file at {0}'.format(path))
            #get the PSD file path
            psd_glob = os.path.join(os.path.dirname(path), '*.psd')
            for psd_path in glob.glob(psd_glob):
                psd_files.append(psd_path)

        scene_handle.write(new_line)
        # Insert our root node information into the new file
        if new_line.startswith('version'):
            scene_handle.write('Root {\n')
            scene_handle.write(' inputs 0\n')
            scene_handle.write(' name {0}\n'.format(wip_file))
            frame_num = int(nuke.root().knob('frame').value())
            scene_handle.write(' frame {0}\n'.format(frame_num))
            format_line = ' format \"{0} {1} 0 0 {0} {1} 1 {2}\"\n'\
                .format(nuke.root().format().width(),
                        nuke.root().format().height(),
                        nuke.root().format().name())
            scene_handle.write(format_line)
            scene_handle.write(' views \"left #ff0000\nright #00ff00\"\n')
            scene_handle.write('}\n')

    scene_handle.flush()
    scene_handle.close()

    # Uniquify the list of PSD files
    psd_files = set(psd_files)

    # Copy all psd files to the new directory
    for psd_file in psd_files:
        file_name = os.path.basename(psd_file)
        new_psd_file = os.path.join(paint_dir, file_name)
        shutil.copyfile(psd_file, new_psd_file)

    return wip_file


def get_latest_matte_painting_wip(shot_obj=None, wip_name='master',
                                  use_sequence=False):
    if wip_name is None:
        wip_name = 'master'

    wip = shot_obj.wips.where(disc='MATTE', name=wip_name).first()
    is_seq = False
    if not wip or use_sequence:
        wip = shot_obj.sequence.wips.where(disc='MATTE', name=wip_name).first()
        is_seq = True
    if not wip:
        raise Exception('No Sequence or Shot level {1} wip for '
                        'this pipe object type < {0} > '
                        .format(shot_obj, wip_name))

    wip_version = wip.versions.get_last()
    if not wip_version:
        raise Exception('No wip version found for the {0} wip of this pipe '
                        'object type {1}'.format(wip_name, shot_obj))

    return wip_version, is_seq


def get_latest_matte_painting(pipe_obj=None, wip_name='master'):
    publish_types = ['setup', 'projection', 'sky']
    sequence_obj = None
    shot_obj = None
    result = None

    for publish_type in publish_types:
        # matte_publish = 'setup'
        # old_types = ['projection', 'sky']
        if not pipe_obj:
            context = get_pipe_context()
            pipe_obj = context.get_pipe_obj()

        # NOTE: Only going to support sequence and shot level matte paintings
        shot_matte = None
        sequence_matte = None
        if isinstance(pipe_obj, Shot):
            sequence_obj = pipe_obj.sequence
            shot_obj = pipe_obj
        elif isinstance(pipe_obj, Sequence):
            sequence_obj = pipe_obj

        if shot_obj and sequence_obj:
            if shot_obj:
                path_context = shot_obj.get_path_context()
                path_context['publish_type'] = publish_type
                path_context['disc'] = 'matte'
                path_context['wip_name'] = wip_name
                path_context['publish_type'] = publish_type
                tmp = path_context.get_path('sh_matte_publish_live_file')
                if os.path.exists(tmp):
                    shot_matte = tmp

            if sequence_obj:
                path_context = sequence_obj.get_path_context()
                path_context['wip_name'] = wip_name
                path_context['disc'] = 'matte'
                path_context['publish_type'] = publish_type
                tmp = path_context.get_path('sq_matte_publish_live_file')
                if os.path.exists(tmp):
                    sequence_matte = tmp

        # Always use the shot if it's there. Matte painting will disable
        # the live link on the shot level if necessary
        if shot_matte:
            result = shot_matte
        elif sequence_matte:
            result = sequence_matte

        if result:
            break

    return result


def publish_matte_painting(pipe_objs, nodes=None):
    pipe_objs = to_list(pipe_objs)

    if not nodes:
        nodes = node_utils.get_selected_nodes()
    if len(nodes) < 1:
        message = 'No nodes were selected for publishing, skipping publish.'
        return Failure(message=message)

    for node in [tmp for tmp in nodes if not \
                 'is_matte_painting' in tmp.knobs()]:
        knob = nuke.Boolean_Knob('is_matte_painting')
        node.addKnob(knob)
    for node in nodes:
        node['is_matte_painting'].setValue(True)

    publish_paths = []

    for pipe_obj in pipe_objs:
        path_context = pipe_obj.get_path_context()
        wip = WipContext.from_env()

        kwargs = {'version': '%03d', 'publish_type': 'setup',
                  'wip_name': wip.wip, 'disc': 'matte'}

        if path_context.get('shot_name'):
            publish_dir = path_context.get_path('sh_matte_publish_version_dir',
                                                **kwargs)
            publish_file = \
                path_context.get_path('sh_matte_publish_version_file',
                                      **kwargs)
        elif path_context.get('seq_name'):
            publish_dir = path_context.get_path('sq_matte_publish_version_dir',
                                                **kwargs)
            publish_file = \
                path_context.get_path('sq_matte_publish_version_file',
                                      **kwargs)

        publish_dir = utils.RPath(path=publish_dir)
        publish_dir.version_up()
        publish_dir.make()
        publish_dir.make_live()
        version = publish_dir.get_version()
        publish_file = publish_file % (int(version))

        publish_paths.append(publish_file)
        nuke.nodeCopy(publish_file)

        # This is hacky, but to get around the pop up stuff we'll need to
        # open the exported file and repoint the paths.
        tmp_file = '{0}.tmp'.format(publish_file)
        handle = open(publish_file, 'r')
        handle.seek(0)
        tmp_handle = open(tmp_file, 'w')
        for line in handle.readlines():
            new_line = line
            if re.match('^\w*file\w*', line.strip()):
                knob_name = re.match('(^\w*file\w*)', line.strip()).group(1)
                split = line.split()
                path = ' '.join(split[1:]).strip('"')
                #path = re.sub('[^[\]] ','\ ',path)
                if re.match('.*[\[\]].*', path) or path == '' or \
                knob_name == 'file_type':
                    new_line = line
                else:
                    tmp_path = utils.RPath(path=path)
                    base_name = tmp_path.get_basename()
                    new_path = join(str(publish_dir), base_name)
                    if re.match('.*####', path) or re.match('.*%04d', path) \
                        or re.match('.*%v', path):
                        glob_path = re.sub('####', '*', path)
                        glob_path = re.sub('%04d', '*', glob_path)
                        glob_path = re.sub('%v', '*', glob_path)
                        for image_path in glob.glob(glob_path):
                            tmp_image_path = utils.RPath(path=image_path)
                            base_image_name = tmp_image_path.get_basename()
                            new_image_path = join(str(publish_dir),
                                                  base_image_name)
                            if os.path.isfile(image_path):
                                shutil.copyfile(image_path, new_image_path)
                    else:
                        if os.path.isfile(path):
                            shutil.copyfile(path, new_path)
                    new_line = ' {0} "{1}"\n'.format(knob_name, new_path)

            tmp_handle.write(new_line)

        tmp_handle.flush()
        tmp_handle.close()
        shutil.copyfile(tmp_file, publish_file)

        # Remove that tmp file we don't need
        os.remove(tmp_file)

    return publish_paths


def get_latest_renders(context=None):
    version_re = re.compile('/v(\d+)')
    if not context:
        pcontext = get_pipe_context()
        context = pcontext.get_path_context()

    shot = context.get('shot_name')

    if shot:
        start = 'sh'
    else:
        start = 'sq'

    glob_path = context.get_render_path('{0}_wip_output_dir'.format(start),
                                        version='*')
    versions = glob.glob(glob_path)
    version = None
    if versions:
        for path in versions:
            match = version_re.search(path)
            if match:
                tmp = int(match.group(1))
                if tmp > version:
                    version = tmp
    return version


def create_instructions(xml_file, **kwargs):

    # create xml root
    root = cElementTree.Element('instructions')
    for key in kwargs.keys():
        value = kwargs.get(key)
        if value is None:
            value = ''

        element = cElementTree.SubElement(root, key)
        if re.search('sequence|range', key, re.I):
            element.text = str(value)
        else:
            element.text = repr(value)

    xml_utils.indent(root)

    # create directory that contains the xml file
    xml_dir = os.path.dirname(xml_file)
    if not os.path.exists(xml_dir):
        file_system.safe_make_dir(xml_dir, make_all=True)

    # save the xml file
    cElementTree.ElementTree(root).write(xml_file)

    result = xml_file
    if not os.path.exists(xml_file):
        result = None

    return result


def read_instructions(xml_file):
    instructions = {}
    if os.path.exists(xml_file):
        tree = cElementTree.parse(xml_file)
        root = tree.getroot()
        for tmp in root:
            if re.search('sequence', tmp.tag, re.I):
                if tmp.text:
                    instructions[tmp.tag] = FrameSequence(path=tmp.text)
            elif re.search('range', tmp.tag, re.I):
                instructions[tmp.tag] = FrameRange.parse(tmp.text)
            else:
                instructions[tmp.tag] = eval(tmp.text)
    else:
        sys.stderr.write('XML does not exist! < {0} >\n'.format(xml_file))

    return instructions


def media_submission(shots=None, use_version=None, **kwargs):
    if use_version:
        path_context = shots[0].get_path_context()
        pipe_context = PipeContext.from_path_context(path_context)
        wip_obj = shots[0].wips.where(disc=Discipline.MATTE,
                                      name='master').first()
    else:
        pipe_context = get_pipe_context()
        path_context = pipe_context.get_path_context()
        wip_obj = pipe_context.get_wip_obj()
    wip_context = wip_obj.get_path_context()
    if not shots:
        shot_obj = pipe_context.get_shot_obj()
        # We won't allow auto submission of a whole sequence yet.
        if shot_obj:
            shots = [shot_obj]
        else:
            seq = pipe_context.get_sequence_obj()
            shots = seq.shots.get_shots_in_edit_order()
            # shots = [seq.shots.where(name='0030').first()]

    # need to create a job for each one of these and then submit them.
    media_jobs = []
    responses = ResponseList()
    for shot in shots:

        _hudded_res, extended_res = shot.get_pre_hud_res()
        if use_version:
            sp_context = wip_obj.get_path_context()
        else:
            sp_context = shot.get_path_context()
        sp_context['disc'] = wip_context['disc']
        wip = WipContext.from_path_context(sp_context)
        namespaces = []
        if kwargs['painting']:
            namespaces.append('painting')
        if kwargs['merged']:
            namespaces.append('merged')
        for namespace in namespaces:
            sp_context['namespace'] = namespace
            if use_version:
                version = int(use_version)
            else:
                version = get_latest_renders(sp_context)
            if not version:
                message = '< {0} > does not have any < {1} > images'\
                    .format(shot.name, namespace)
                warning = Warning(message)
                responses.append(warning)
                continue

            wip.wip_name = namespace
            wip.wip_version = version

            output_dir = sp_context.get_render_path('sh_wip_output_dir',
                                                    version=version,
                                                    namespace=namespace)

            frame_range = FrameRange.parse('%s-%s' % (shot.frame_range.start,
                                                      shot.frame_range.end))
            sequences = []
            if os.path.isdir(output_dir):
                sequences = FrameSequence.get_sequences_from_dir(output_dir)
            if len(sequences) == 0:
                IO.error('No rendered frames were found for Seq: {0} Shot: '
                         '{1} WIP Version: {2} Media Type: {3}'
                         .format(shot.sequence.name, shot.name, use_version,
                               namespace))
                return
            image_sequences = {}
            for sequence in sequences:
                missing = sequence.get_missing_frames(frame_range)
                if missing:
                    message = '< {0} > is missing frames: \n{1}'\
                        .format(shot.name, '\n\t'.join(
                        [str(miss) for miss in missing]))
                    sys.stderr.write('{0}\n'.format(message))
                    warning = Warning(message)
                    responses.append(warning)
                    sequence.fill_missing_frames(frame_range)
                if re.search('\.l\.', str(sequence)):
                    image_sequences['l'] = sequence
                else:
                    image_sequences['r'] = sequence

            sub_kwargs = {}
            audio_file = sp_context.get_path('sh_audio_file')
            if 'description' in kwargs:
                sub_kwargs['description'] = kwargs.get('description')
            if 'scratch' in kwargs:
                sub_kwargs['scratch'] = kwargs.get('scratch')
            if 'hud' in kwargs:
                sub_kwargs['hud'] = kwargs.get('hud')

            sub_kwargs['extended_width'] = int(extended_res[0])
            sub_kwargs['extended_height'] = int(extended_res[1])
            sub_kwargs['audio_file_path'] = audio_file
            sub_kwargs['left_eye'] = 'matteleft'
            sub_kwargs['right_eye'] = 'matteright'
            sub_kwargs['version'] = version
            sub_kwargs['wip'] = namespace
            sub_kwargs['right_frame_sequence'] = image_sequences.get('r')
            sub_kwargs['left_frame_sequence'] = image_sequences.get('l')

            label = 'media_submission'

            sp_context = wip.get_path_context()
            if sp_context.has_vars('shot_name'):
                instruction_xml_path = \
                    sp_context.get_path('sh_matte_store_instruction_file',
                                        label=label, version=version,
                                        wip_name=namespace)
            elif sp_context.has_vars('seq_name'):
                instruction_xml_path = \
                    sp_context.get_path('sq_matte_store_instruction_file',
                                        label=label, version=version,
                                        wip_name=namespace)
            else:
                message = 'Must be in a sequence or shot level context'
                failure = Failure(message)
                responses.append(failure)
                continue

            instruction_xml = create_instructions(instruction_xml_path,\
                                                  **sub_kwargs)

            media_job = create_matte_media_job(instruction_xml, wip, **kwargs)
            media_jobs.append(media_job)

            message = 'Successful Submission. Sequence: {0} Shot: {1} '
            'Type: {2}'.format(shot.sequence.name, shot.name, namespace)
            success = Success(message, payload=media_job)
            responses.append(success)

    for job in media_jobs:
        job.submit()
        IO.info('Job has been successfully submitted to the farm...job # {0}'\
                .format(job.job_id))

    return responses


def create_matte_media_job(instruction_xml, wip_context, **kwargs):

    job_settings = dict(DEFAULT_MEDIA_FARM_SETTINGS)
    job_settings.update(kwargs)
    job_settings['user'] = get_user()

    # This will be the thing that gets executed on the farm.
    executer = CmdExecuter(wip_context)
    executer.pipe_ctx = wip_context
    executer.set_command_and_arg_list([MEDIA_SUBMISION_TOOL, instruction_xml])

    qube_job = QubeJob(executer,
                       'media', 'MEDIA',
                       'scripts',
                       **job_settings)

    # setup email
    lang = QubeLanguage.get_enum('mail')
    code = ''
    user = get_user()
    email = get_email_address(user)
    qube_job.add_callback(code,
                          farm_utils.QubeTrigger.get_fail_self_trigger(),
                          language=lang)
    qube_job.add_callback(code,
                          farm_utils.QubeTrigger.get_kill_self_trigger(),
                          language=lang)

    qube_job.job['mailaddress'] = email

    return qube_job


def render_submission(shots=None, **kwargs):
    wip_name = kwargs.pop('wip_name', 'master')
    wmanager = wip_manager.WipManager.instance()

    render_jobs = []
    media_jobs = []

    render_responses = ResponseList()
    media_responses = ResponseList()
    seq_sub = kwargs.pop('sequence_submission', False)
    #If this is a sequence WIP, and it has been versioned up
    seq_versioned = False
    for shot in shots:
        last_version, is_seq = \
            get_latest_matte_painting_wip(shot, wip_name=wip_name,
                                          use_sequence=seq_sub)
        wip_context = WipContext.from_pipe_obj(last_version)
        wip_context.shot = shot.name

        # Version up the wip if the option is enabled
        if kwargs['version_up'] and not seq_versioned:
            # Open the appropriate WIP context before versioning up
            wmanager.open_wip_context(wip_context)
            version = last_version.number + 1
            wip_kwargs = {}
            wip_kwargs['application'] = 'NUKE'
            wip_kwargs['owner'] = get_user()
            response = wmanager.version_up(version, wip_context, **wip_kwargs)
            if response.is_success():
                wip_context = response.payload
                wip_context.shot = shot.name
            else:
                response.print_message()
                return None
            wip_object = wip_context.get_wip_obj()
            last_version = wip_object.versions.get_last()
            if is_seq:
                seq_versioned = True

        context = last_version.get_path_context()
        path = last_version.get_path()

        archive_scene = utils.create_script_archive(path, context)
        kwargs['archive_scene'] = archive_scene

        render_job = create_matte_render_job(wip_context, **kwargs)
        render_jobs.append(render_job)

        message = 'Successful Submission. Sequence: {0} Shot: {1}'.format(
            shot.sequence.name, shot.name)
        success = Success(message, payload=render_job)
        render_responses.append(success)

    # Submit all render jobs to the farm before submitting the media jobs so
    # that we can reference the job id of the render jobs in the dependency of
    # the media job
    for job in render_jobs:
        job.submit()
        IO.info('Render job has been successfully submitted to the farm...job '
                '# {0}'.format(job.job_id))
    # Also submit the media submission job if the option is enabled
    if kwargs['submit_media_merged'] or kwargs['submit_media_painting']:
        for response in render_responses:
            render_job = response.payload
            wip_ctx = render_job.executer.pipe_ctx
            shot = wip_ctx.get_shot_obj()
            _hudded_res, extended_res = shot.get_pre_hud_res()
            sp_context = shot.get_path_context()
            wip_path_context = wip_ctx.get_wip_obj().get_path_context()
            sp_context['disc'] = wip_path_context['disc']
            version = wip_ctx.wip_version
            namespaces = []
            if kwargs['submit_media_painting']:
                namespaces.append('painting')
            if kwargs['submit_media_merged']:
                namespaces.append('merged')
            for namespace in namespaces:
                wip_ctx.wip_name = namespace
                wip_ctx.wip_version = version
                sp_context['namespace'] = namespace
                audio_file = sp_context.get_path('sh_audio_file')
                version_str = str(version).zfill(4)
                image_sequences = {}
                output_dir = sp_context.get_render_path('sh_wip_output_dir',
                                                        version=version,
                                                        namespace=namespace)
                left_seq_name = '{0}_{1}_{2}_{3}_v{4}.l.%04d.exr'\
                    .format(shot.sequence.name, shot.name, namespace, wip_name,
                            version_str)
                right_seq_name = '{0}_{1}_{2}_{3}_v{4}.r.%04d.exr'\
                    .format(shot.sequence.name, shot.name, namespace, wip_name,
                            version_str)
                image_sequences['l'] = os.path.join(output_dir, left_seq_name)
                image_sequences['r'] = os.path.join(output_dir, right_seq_name)
                print 'output_dir = {0}'.format(output_dir)
                sub_kwargs = {}
                sub_kwargs['extended_width'] = int(extended_res[0])
                sub_kwargs['extended_height'] = int(extended_res[1])
                sub_kwargs['audio_file_path'] = audio_file
                sub_kwargs['left_eye'] = 'matteleft'
                sub_kwargs['right_eye'] = 'matteright'
                sub_kwargs['version'] = version
                sub_kwargs['wip'] = namespace
                sub_kwargs['right_frame_sequence'] = image_sequences.get('r')
                sub_kwargs['left_frame_sequence'] = image_sequences.get('l')
                label = 'media_submission'
                if sp_context.has_vars('shot_name'):
                    instruction_xml_path = \
                        sp_context.get_path('sh_matte_store_instruction_file',
                                            label=label, version=version,
                                            wip_name=namespace)
                elif sp_context.has_vars('seq_name'):
                    instruction_xml_path = \
                        sp_context.get_path('sq_matte_store_instruction_file',
                                            label=label, version=version,
                                            wip_name=namespace)
                else:
                    message = 'Must be in a sequence or shot level context'
                    failure = Failure(message)
                    media_responses.append(failure)
                    continue
                instruction_xml = create_instructions(instruction_xml_path,
                                                      **sub_kwargs)
                media_kwargs = {}
                media_kwargs['priority'] = kwargs['priority']
                media_job = create_matte_media_job(instruction_xml, wip_ctx,
                                                   **media_kwargs)
                media_job.add_dependency_id(render_job.job_id)
                media_jobs.append(media_job)
                message = 'Successful Submission. Sequence: {0} Shot: {1} '
                'Type: {2}'.format(shot.sequence.name, shot.name, namespace)
                success = Success(message, payload=media_job)
                media_responses.append(success)

    for job in media_jobs:
        job.submit()
        IO.info('Media job has been successfully submitted to the farm...job #'
                ' {0}'.format(job.job_id))

    render_responses.extend(media_responses)

    return render_responses


def create_matte_render_job(wip_context, **kwargs):

    job_settings = dict(DEFAULT_RENDER_FARM_SETTINGS)
    job_settings.update(kwargs)
    job_settings['user'] = get_user()

    shot_obj = wip_context.get_shot_obj()

    # Handle chunking and such!
    chunksize = job_settings.pop('chunksize', 1)
    frames = job_settings['frames']
    if frames == '':
        frames = '{0}-{1}'.format(shot_obj.frame_range.start,
                                                  shot_obj.frame_range.end)
    frame_set = FrameSet.parse(frames)
    heavy = job_settings.pop('heavy_render', False)
    job_settings['reservations'] = ['host.processors=3']
    if heavy:
        job_settings['reservations'] = ['host.processors=3+']
        job_settings['requirements'] = ['host.memory.total>=23000']
        job_settings['clusters'] = 'nuke_24'

    frame_sets = frame_set.subdivide(int(chunksize))
    job_settings['agendas'] = \
        QubeAgenda.gen_frame_set_tasks(frame_sets, FrameDistribution.FULL)

    executer = NukeExecuter(wip_context)
    executer.batch_mode = True
    executer.py_script = RENDER_TOOL
    executer.startup_scene = job_settings.pop('archive_scene')

    qube_job = QubeJob(executer, 'MatteRender', JobType.MATTE,
                       **job_settings)

    # setup email
    lang = QubeLanguage.get_enum('mail')
    user = get_user()
    email = get_email_address(user)
    code = ''
    qube_job.add_callback(code, farm_utils.QubeTrigger.get_fail_self_trigger(),
                          language=lang)
    qube_job.add_callback(code, farm_utils.QubeTrigger.get_kill_self_trigger(),
                          language=lang)

    version = wip_context.wip_version
    sp_context = wip_context.get_path_context()
    sp_context.shot_name = wip_context.shot
    message = ''
    for namespace in ['painting', 'merged']:
        path = sp_context.get_render_path('sh_wip_output_dir', version=version,
                                          namespace=namespace)
        message = 'Frames {0} rendered to: {1}\\n'.format(frames, path)
    recipient = get_email_address(get_user())
    email_code = 'from email.mime.text import MIMEText;'\
                 'import smtplib;'\
                 'import os;'\
                 'job_id = qb.jobid();'\
                 'msg = MIMEText(\'{0}\');'\
                 'msg[\'Subject\'] = \'[Matte Painting] Render Submission: '\
                 '{1} {2}, Job \'+str(job_id)+\' Complete\';'\
                 'msg[\'From\'] = \'qube@reelfx.com\';'\
                 'msg[\'To\'] = \'{3}\';'\
                 's = smtplib.SMTP(\'webmail.reelfx.com\');'\
                 's.sendmail(msg[\'From\'],msg[\'To\'],msg.as_string());'\
                 's.quit()'\
                 .format(message, shot_obj.sequence.name, shot_obj.name,
                         recipient)
    qube_job.add_callback(email_code,
                          farm_utils.QubeTrigger.get_complete_self_trigger())

    qube_job.job['mailaddress'] = email

    return qube_job


def create_shot_read(shot, namespace='painting'):  # IGNORE:W0613
    pass


def version_up():
    pass


def create_write_setup():
    context = get_pipe_context()
    path_context = context.get_path_context()

    sequence = '[getenv SEQ_NAME]'
    shot = '[getenv SHOT_NAME]'
    wip = '[getenv WIP_NAME]'
    namespace = '[value name]'
    version = '[getenv WIP_VERSION_PADDED]'
    path_context['seq_name'] = sequence
    path_context['shot_name'] = shot
    path_context['wip_name'] = wip
    path_context['namespace'] = namespace

    # Time for hack city!
    path_context['version'] = 0

    for node in node_utils.node_query(attrs={'is_matte_painting_write': True}):
        nuke.delete(node)

    ng = node_utils.RNukeNodeGraph.from_script()
    w_ng = node_utils.RNukeNodeGraph()

    custom_knobs = {'is_matte_painting_write': True}

    basename = '{0}_{1}_{2}_{3}_{4}.%v.%04d.exr'

    painting_path = os.path.join(
        path_context.get_render_path('sh_wip_output_dir'),
        basename.format(sequence, shot, namespace, wip, version))

    merged_path = os.path.join(
        path_context.get_render_path('sh_wip_output_dir'),
        basename.format(sequence, shot, namespace, wip, version))

    # We need to get rid of the v in the path since the v is also in the
    # WIP_VERSION_PADDED env var
    painting_path = re.sub('v0000', version, painting_path)
    merged_path = re.sub('v0000', version, merged_path)

    # Geometry is handled a bit differently.  It doesn't use version the same
    # way everything else does.
    version = 1
    geometry_path = os.path.join(
        path_context.get_render_path('sh_wip_output_dir', version=version),
        basename.format(sequence, shot, namespace, wip,
                        'v{0:04d}'.format(version)))

    # Been setting the namespace, let's remove
    del(path_context['namespace'])

    existing_writes = node_utils.node_query(filters='Write',
                                            name='merged*|painting*|geometry*')
    for node in existing_writes:
        name = node['name'].value()
        node['name'].setValue('{0}_backup'.format(name))

    painting = w_ng.create_node('Write',
                                name='painting',
                                file=painting_path,
                                render_order=1,
                                file_type='exr',
                                channels='all',
                                custom_knobs=custom_knobs)

    painting_read = w_ng.create_node('Read',
                                     name='painting_read',
                                     custom_knobs=custom_knobs)

    painting_read.snap_center_x(painting)
    painting_read.snap_bottom(painting)

    painting_read['file'].setValue('[value {0}.file]'\
                                   .format(painting['name'].value()))

    geometry = w_ng.create_node('Write', render_order=1,
                                name='geometry',
                                file=geometry_path,
                                file_type='exr',
                                channels='all',
                                custom_knobs=custom_knobs)

    geometry.align_top(painting)
    geometry.snap_left(painting, additional=35)

    geometry_read = w_ng.create_node('Read',
                                     name='geometry_read',
                                     custom_knobs=custom_knobs)

    geometry_read.snap_center_x(geometry)
    geometry_read.snap_bottom(geometry)

    geometry_read['file'].setValue('[value {0}.file]'\
                                   .format(geometry['name'].value()))

    merge = w_ng.create_node('Merge', custom_knobs=custom_knobs)
    merge.snap_center_x([geometry_read, painting_read])
    merge.snap_bottom([geometry_read, painting_read], additional=50)

    merged = w_ng.create_node('Write',
                              render_order=2,
                              name='merged',
                              file=merged_path,
                              file_type='exr',
                              channels='all',
                              custom_knobs=custom_knobs)

    merge.setInput(1, geometry_read.get_node())
    merge.setInput(0, painting_read.get_node())

    merged.snap_bottom(merge)
    merged.snap_center_x(merge)
    merged.setInput(0, merge.get_node())

    w_ng.align_top(ng)
    w_ng.snap_right(ng, additional=50)

    nodes = [painting.get_node(),
             geometry.get_node(),
             merged.get_node(),
             merge.get_node()]

    node_utils.center_on_screen(nodes)

    return nodes


def import_shot_matte_painting_render(pipe_obj=None, wip_name='master'):
    mng = node_utils.RNukeNodeGraph.from_script()
    if not pipe_obj:
        context = get_pipe_context()
        pipe_obj = context.get_pipe_obj()
    path_context = pipe_obj.get_path_context()
    if isinstance(pipe_obj, Shot):
        matte_painting_render_path = \
            path_context.get_path('sh_matte_render_dir', disc='matte',
                                  wip_name='master', element='painting')
    else:
        message = 'Could not find a valid render path'\
                  'for {0}'.format(pipe_obj)
        return Failure(message=message)
    if not os.path.exists(matte_painting_render_path):
        message = 'Render path does not exist: {0}\n'\
                  'Try re-rendering the matte painting Nuke scene.'\
                  .format(matte_painting_render_path)
        return Failure(message=message)
    read_node = nuke.nodes.Read()  # @UndefinedVariable
    sequence_name = pipe_obj.sequence.name
    shot_name = pipe_obj.name
    read_node.setName('Matte_Painting_{0}_{1}'.format(sequence_name,
                                                      shot_name))
    version_expression_knob = nuke.EvalString_Knob('version_expression')
    version_expression = '[lindex [regexp -inline {.*_v(\d+).*} [lindex '\
        '[glob %s/%s_%s_painting_master_v*] 0]] 1]'\
        % (matte_painting_render_path, sequence_name, shot_name)
    version_expression_knob.setValue(version_expression)
    version_expression_knob.setVisible(False)
    read_node.addKnob(version_expression_knob)
    file_name = '{0}_{1}_painting_master_v[value this.version_expression]'\
        '.%v.%04d.exr'.format(sequence_name, shot_name)
    file_path = os.path.join(matte_painting_render_path, file_name)
    read_node['file'].setValue(file_path)
    read_node['first'].setValue(pipe_obj.frame_range.start)
    read_node['last'].setValue(pipe_obj.frame_range.end)
    read_node['origfirst'].setValue(pipe_obj.frame_range.start)
    read_node['origlast'].setValue(pipe_obj.frame_range.end)
    read_is_matte_knob = nuke.Boolean_Knob('is_matte_painting')
    read_is_matte_knob.setValue(True)
    read_node.addKnob(read_is_matte_knob)
    # Create the extra motion blur nodes
    motion_blur_node, vector_blur_node = create_blur_nodes(read_node)
    node_graph = node_utils.RNukeNodeGraph(nodes=[read_node,
                                                  motion_blur_node,
                                                  vector_blur_node])
    backdrop_node = node_graph.create_backdrop(50, 50, 50, 50)
    backdrop_node_name = 'Matte_Painting_from_Sequence_{0}_Shot_{1}'\
        .format(sequence_name, shot_name)
    backdrop_node.setName(backdrop_node_name)
    backdrop_is_matte_knob = nuke.Boolean_Knob('is_matte_painting')
    backdrop_is_matte_knob.setValue(True)
    backdrop_node.addKnob(backdrop_is_matte_knob)
    node_graph.add_node(backdrop_node)
    node_graph.snap_right(mng, additional=100)
    node_graph.align_top(mng)
    node_utils.center_on_screen(backdrop_node)
    return node_graph


def create_blur_nodes(input_node):
    # Create the MotionBlur3D node
    motion_blur_node = nuke.nodes.MotionBlur3D()  # @UndefinedVariable
    motion_blur_node['distance'].setValue(7000)
    motion_blur_node.setInput(0, input_node)
    motion_blur_node.setXpos(input_node.xpos())
    motion_blur_node.setYpos(input_node.ypos() + 150)
    motion_blur_is_matte_knob = nuke.Boolean_Knob('is_matte_painting')
    motion_blur_is_matte_knob.setValue(True)
    motion_blur_node.addKnob(motion_blur_is_matte_knob)
    # Create the VectorBlur node
    vector_blur_node = nuke.nodes.VectorBlur()  # @UndefinedVariable
    vector_blur_node.setInput(0, motion_blur_node)
    vector_blur_is_matte_knob = nuke.Boolean_Knob('is_matte_painting')
    vector_blur_is_matte_knob.setValue(True)
    vector_blur_node.addKnob(vector_blur_is_matte_knob)
    vector_blur_node.setXpos(motion_blur_node.xpos())
    vector_blur_node.setYpos(motion_blur_node.ypos() + 100)
    return motion_blur_node, vector_blur_node


def import_shot_matte_painting(shot=None, wip_name='master'):
    if not shot:
        context = get_pipe_context()
        shot = context.get_shot_obj()

    matte_painting_path = get_latest_matte_painting(shot, wip_name)
    print 'matte_painting_path = ', matte_painting_path
    if not matte_painting_path:
        message = 'No published matte painting exists for Seq: {0} Shot: {1} '\
                  'WIP: {2}'.format(shot.sequence.name, shot.name, wip_name)
        IO.error(message)
        return Failure(message=message)

    mng = node_utils.RNukeNodeGraph.from_script()
    nuke.nodePaste(matte_painting_path)
    ng = node_utils.RNukeNodeGraph.from_selection()
    backdrop_node = ng.get_backdrop_node()
    scanline_render_node = ng.get_scanline_render_node()
    if not isinstance(scanline_render_node, Failure):
        # Create the extra motion blur nodes
        motion_blur_node, vector_blur_node = \
            create_blur_nodes(scanline_render_node)
        ng.add_nodes([motion_blur_node, vector_blur_node])
        backdrop_node['bdheight'].setValue(backdrop_node['bdheight'].value() +
                                           250)
    response = formula_extract('sh_matte_publish_live_file',
                               matte_painting_path)
    if response.success:
        backdrop_node_name = 'Matte_Painting_from_Sequence_{0}_Shot_{1}'\
                             .format(shot.sequence.name, shot.name)
    else:
        response = formula_extract('sq_matte_publish_live_file',
                                   matte_painting_path)
        if response.success:
            backdrop_node_name = 'Matte_Painting_from_Sequence_{0}'\
                                 .format(shot.sequence.name)
        else:
            message = 'Failed to find a live matte painting setup for either '\
                      'Seq: {0} or Seq: {0} Shot: {1}.'\
                      .format(shot.sequence.name, shot.name)
            return Failure(message=message)
    backdrop_node.setName(backdrop_node_name)

    nodes = [node.get_node() for node in ng]
    sky_controllers = node_utils.node_query(nodes, filters='bolSkyController')
    for controller in sky_controllers:
        if 'is_matte_painting' in controller.knobs():
            controller['is_matte_painting'].setValue(False)

    ng.snap_right(mng, additional=100)
    ng.align_top(mng)
    node_utils.center_on_screen(backdrop_node)

    node_utils.clear_selection()

    return ng


def refresh_matte_painting():

    context = get_pipe_context()
    path_context = context.get_path_context()

    wip = WipContext.from_path_context(path_context)
    if not wip.discipline == Discipline.COMP:
        return

    previous_selection = node_utils.clear_selection()

    pipe_obj = context.get_pipe_obj()
    matte_painting_path = get_latest_matte_painting(pipe_obj)
    sys.stderr.write('Latest Matte Painting < {0} >\n'\
                     .format(matte_painting_path))

    if matte_painting_path:
        node_graph = node_utils.RNukeNodeGraph.from_script()
        matte_node_graph = None
        matte_nodes = node_utils.node_query(attrs='is_matte_painting')
        no_sync_matte_nodes = \
            node_utils.node_query(attrs={'is_matte_painting': False})

        nodes_dict = defaultdict(dict)
        position = node_graph.get_top_right()
        if matte_nodes:
            matte_node_graph = node_utils.RNukeNodeGraph()
            matte_node_graph.add_nodes(matte_nodes)
            position = matte_node_graph.get_position()

            for node in matte_nodes:
                node_dict = defaultdict(dict)
                nodes_dict[node['name'].value()] = node_dict
                dependencies = node.dependencies()
                dependent = node.dependent()

                node_dict['dependencies'] = defaultdict(dict)
                node_dict['dependent'] = defaultdict(dict)
                node_dict['bdwidth'] = node['bdwidth'].value() if \
                    'bdwidth' in node.knobs() else None
                node_dict['bdheight'] = node['bdheight'].value() if \
                    'bdheight' in node.knobs() else None
                node_dict['position'] = (node['xpos'].value(),
                                         node['ypos'].value())

                if dependencies:
                    for i in xrange(node.inputs()):
                        node_in = node.input(i)
                        if not node_in:
                            continue
                        if not 'is_matte_painting' in node_in.knobs():
                            node_dict['dependencies'][node_in['name'].value()]\
                            = i

                if dependent:
                    for depend in dependent:
                        for i in xrange(depend.inputs()):
                            in_node = depend.input(i)
                            if in_node == node:
                                node_dict['dependent'][depend['name'].value()]\
                                = i

        # We'll temporarily copy off the original nodes and bring them back
        # afterwards. Get a copy of their names first
        no_sync_names = [node['name'].value() for node in no_sync_matte_nodes]
        for node in no_sync_matte_nodes:
            node['selected'].setValue(True)

        tempfile = NamedTemporaryFile('rw')
        if len(nuke.selectedNodes()) > 0:
            nuke.nodeCopy(tempfile.name)
        # no_sync_matte_nodes is now invalid, so is the original matte_nodes
        for node in no_sync_matte_nodes:
            nuke.delete(node)

        matte_nodes = node_utils.node_query(attrs={'is_matte_painting': True})
        for node in matte_nodes:
            nuke.delete(node)

        # Paste in our new nodes
        nuke.nodePaste(matte_painting_path)

        # Clear the selection and get the nodes
        unclean_nodes = node_utils.clear_selection()

        # This returns a bunch of RNodes, we want to get our nuke node out
        clean_nodes = []
        for node in unclean_nodes:
            if node['name'].value() in no_sync_names:
                nuke.delete(node)
                continue
            clean_nodes.append(node)

        # We've cleaned out our existing nodes, let's bring in the nodes we
        # removed earlier
        nuke.nodePaste(tempfile.name)
        pasted = node_utils.clear_selection()
        clean_nodes.extend(pasted)

        sky_controllers = node_utils.node_query(clean_nodes,
                                                filters='bolSkyController')
        for controller in sky_controllers:
            if 'is_matte_painting' in controller.knobs():
                controller['is_matte_painting'].setValue(False)

        new_matte_node_graph = node_utils.RNukeNodeGraph(nodes=clean_nodes)
        new_matte_node_graph.set_position(position)

        for name in nodes_dict.keys():
            node = nuke.toNode(name)
            if node:
                for d_name in nodes_dict[name]['dependencies'].keys():
                    dependency = nuke.toNode(d_name)
                    if dependency:
                        node.setInput(nodes_dict[name]['dependencies'][d_name],
                                      dependency)

                for d_name in nodes_dict[name]['dependent'].keys():
                    dependent = nuke.toNode(d_name)
                    if dependent:
                        dependent\
                        .setInput(nodes_dict[name]['dependent'][d_name], node)

                if nodes_dict[name]['bdwidth']:
                    node['bdwidth'].setValue(nodes_dict[name]['bdwidth'])
                    node['bdheight'].setValue(nodes_dict[name]['bdheight'])
                if nodes_dict[name]['position']:
                    node['xpos'].setValue(nodes_dict[name]['position'][0])
                    node['ypos'].setValue(nodes_dict[name]['position'][1])
            else:
                sys.stderr.write('Node does not exist! {0}\n'.format(name))

        node_utils.clear_selection()
    else:
        sys.stderr.write('No matte painting for this shot!\n')

    node_utils.add_to_selection(previous_selection)

    sys.stderr.write('Done refreshing matte paintings\n')


def create_contact_sheet(shots):

    contact_sheet_ng = node_utils.RNukeNodeGraph()
    contact_sheet = \
        contact_sheet_ng.create_node('ContactSheet',
                                     name='{0}_contactSheet'\
                                        .format(shots[0].sequence.name),
                                     roworder='Top Bottom}')

    # knobs = []
    # node_utils.set_knobs(contact_sheet.get_node(), knobs, add_knobs=True)
    i = 0
    previous_node = None
    nodes = node_utils.RNukeNodeGraph()
    for shot in shots:
        node = create_shot(shot, contact_sheet_ng)
        if node:
            if previous_node:
                node.align_top(previous_node)
                node.snap_right(previous_node, additional=30)

            contact_sheet.snap_bottom(node, additional=30)

            nodes.add_node(node)

            contact_sheet.setInput(i, node.get_node())

            previous_node = node
            i += 1

    contact_sheet.snap_center_x(nodes)
    contact_sheet.snap_bottom(nodes, additional=30)

    contact_sheet_ng.create_backdrop(75, 10, 10, 10,
                                     label='{0} Matte Contact Sheet'\
                                        .format(shots[0].sequence.name),
                                     name='{0}_contactSheetBackdrop'\
                                        .format(shots[0].sequence.name))

    contact_sheet_ng.snap_right(contact_sheet_ng, additional=30)
    contact_sheet_ng.align_top(contact_sheet_ng)

    grid = math.sqrt(i)
    columns = math.ceil(grid)
    grid_size = math.modf(grid)[0]
    if grid_size > 0.5:
        rows = math.ceil(grid)
    else:
        rows = math.floor(grid)

    width = previous_node.width()
    height = previous_node.height()

    # contact_sheet_node = contact_sheet.get_node()
    if not 'scale' in contact_sheet.knobs().keys():
        contact_sheet.addKnob(nuke.Double_Knob('scale', 'scale'))
    contact_sheet['scale'].setRange(0, 1)
    contact_sheet['scale'].setValue(0.5)

    if not 'rez' in contact_sheet.knobs().keys():
        contact_sheet.addKnob(nuke.WH_Knob('rez', 'rez'))
    contact_sheet['rez'].setValue(width, 0)
    contact_sheet['rez'].setValue(height, 1)

    cs_height = 'rez.h * scale * rows'
    cs_width = 'rez.w * scale * columns'
    contact_sheet['height'].setExpression(cs_height, 0)
    contact_sheet['width'].setExpression(cs_width, 0)

    contact_sheet['rows'].setValue(rows)
    contact_sheet['columns'].setValue(columns)

    matte_format = None
    formats = nuke.formats()
    formats.reverse()
    for nformat in formats:
        if nformat.name() == 'MATTE':
            matte_format = nformat
            break
    if matte_format is None:
        matte_format = nuke.addFormat('%s %s %s %s' % (width,
                                                        height,
                                                        1, 'MATTE'))
    else:
        matte_format.setWidth(width)
        matte_format.setHeight(height)
        matte_format.setPixelAspect(1)

    for node in nodes:
        node['format'].setValue(matte_format)
    contact_sheet['rez'].setValue(width, 0)
    contact_sheet['rez'].setValue(height, 1)

    return contact_sheet_ng


def create_shot(shot, node_graph, element='merged'):
    path_pattern = ''
    media = shot.media.where(disc=Discipline.MATTE, element=element).first()
    if media:
        media_version = media.versions.get_last()
        if shot.cinema.stereo:
            script_utils.make_stereo()
            path_pattern = media_version.get_stereo_pattern()
            path_pattern = re.sub('%s', '%v', path_pattern)

    node = node_graph.create_node('Read',
                                  name='{0}_{1}_csr'.format(shot.sequence.name,
                                                            shot.name),
                                  first=shot.frame_range.start,
                                  last=shot.frame_range.end,
                                  file=path_pattern)

    return node


# This will import TIFF files exported from individual layers of a photoshop
# file, generated from the photoshop script for automatically exporting TIFFs
# Arguments:
#     dirPath = Path to a directory containing versioned matte painting TIFFs
def import_tif_layers(dirPath):
    lastVersion = 0
    lastFolder = None
    for filename in os.listdir(dirPath):
        version_rex = re.match('v(\d*)', filename)
        if version_rex:
            version = int(version_rex.group(1))
            if lastVersion < version:
                lastVersion = version
                lastFolder = filename
    for filename in os.listdir('%s/%s' % (dirPath, lastFolder)):
        tif_name_rex = re.match('(\d*)_(\S*)\.tif', filename)
        if tif_name_rex:
            readName = '%s_%s' % (tif_name_rex.group(2), tif_name_rex.group(1))
            read_node = nuke.nodes.Read()
            read_node.setName(readName)
            read_node_file_knob = read_node.knob('file')
            read_node_file_knob.setValue('/people/lkelly/Marissa_file/%s/%s' %
                                         (lastFolder, filename))


def create_overscan_camera(camera=None, overscan_ratio=1):
    from nuke_tools.camera_utils import copy_camera_values
    new_camera = None
    if not camera:
        nodes = node_utils.get_selected_nodes(filters=['Camera2',
                                                       'RAlembicCamera'])
        if nodes:
            camera = nodes[0]
    if camera:
        new_camera = nuke.nodes.Camera2()  # @UndefinedVariable
        copy_camera_values(camera, new_camera)

        old_name = camera['name'].value()
        new_name = \
            node_utils.get_available_name('{0}Overscan'.format(old_name))
        new_camera['name'].setValue(new_name)
        new_camera['label'].setValue('overscan ratio: [value overscan_ratio]')
        new_camera['tile_color'].setValue(4278255615)

        tab = nuke.Tab_Knob('overscan_settings')
        overscan = nuke.Double_Knob('overscan_ratio')
        overscan.setValue(overscan_ratio)

        new_camera.addKnob(tab)
        new_camera.addKnob(overscan)

        new_camera['focal'].setExpression('1/overscan_ratio * curve')

    return new_camera


# Determines if the painting and merged media have been submitted for each
# version of a particular shot, and prints the result.
def list_submitted_media(shot_obj, discipline=Discipline.MATTE,
                         ansi_color=True):
    if ansi_color:
        colors = ANSI_COLORS
    else:
        colors = NO_ANSI_COLORS
    painting_versions = {}
    merged_versions = {}
    master_versions = {}
    media = shot_obj.media.where(disc=discipline).all()
    for media_type in media:
        if discipline == Discipline.MATTE:
            if media_type.element == 'painting':
                media_versions = painting_versions
            elif media_type.element == 'merged':
                media_versions = merged_versions
        elif discipline == Discipline.COMP:
            media_versions = master_versions
        for version in media_type.versions.all():
            media_versions[version.number] = version
    wip = shot_obj.wips.where(disc=discipline, name='master').first()
    wip_versions = {}
    if wip:
        for wip_version in wip.versions.all():
            wip_versions[wip_version.number] = wip_version
    all_versions = {}
    for version_num, wip_version in wip_versions.iteritems():
        all_versions[version_num] = wip_version
    for version_num, version in painting_versions.iteritems():
        if not version_num in all_versions.iterkeys():
            all_versions[version_num] = version
    if len(all_versions) == 0:
        IO.warning('No media or wip versions exist for this pipe object.')
        return
    last_version = sorted(all_versions)[-1]
    for version_num in range(1, last_version + 1):
        if version_num not in all_versions.keys():
            all_versions[version_num] = 'dir'
    IO.info('\nSubmission status for master WIP versions:')
    IO.info('{0:=^95}'.format(''))
    if discipline == Discipline.MATTE:
        IO.info('|{0:^15}|{1:^38}|{2:^38}|'.format('WIP Version', 'Painting',
                                                   'Merged'))
    elif discipline == Discipline.COMP:
        IO.info('|{0:^15}|{1:^77}|'.format('WIP Version', 'Master'))
    IO.info('|{0:=^93}|'.format(''))
    for version_num, version in all_versions.iteritems():
        if discipline == Discipline.MATTE:
            wip_version = None
            media_version = None
            if isinstance(version, WipVersion):
                wip_version = version
            elif isinstance(version, MediaVersion):
                media_version = version
            painting_rendered = False
            merged_rendered = False
            if wip_version:
                painting_render_dir = wip_version.get_path_context().\
                    get_render_path('sh_wip_output_dir', namespace='painting')
            elif media_version:
                painting_render_dir = media_version.get_frame_path()
            else:
                sp_context = shot_obj.get_path_context()
                sp_context['disc'] = 'matte'
                sp_context['wip_name'] = 'master'
                painting_render_dir = \
                    sp_context.get_render_path('sh_wip_output_dir',
                                               version=version_num,
                                               namespace='painting')
            if os.path.isdir(painting_render_dir):
                painting_sequences = \
                    FrameSequence.get_sequences_from_dir(painting_render_dir)
                painting_rendered = len(painting_sequences) > 0
            if wip_version:
                merged_render_dir = wip_version.get_path_context().\
                    get_render_path('sh_wip_output_dir', namespace='merged')
            elif media_version:
                merged_render_dir = re.sub('painting', 'merged',
                                           painting_render_dir)
            else:
                sp_context = shot_obj.get_path_context()
                sp_context['wip_name'] = 'master'
                sp_context['disc'] = 'matte'
                merged_render_dir = \
                    sp_context.get_render_path('sh_wip_output_dir',
                                               version=version_num,
                                               namespace='merged')
                if os.path.isdir(merged_render_dir):
                    merged_sequences = \
                        FrameSequence.get_sequences_from_dir(merged_render_dir)
                    merged_rendered = len(merged_sequences) > 0
        elif discipline == Discipline.COMP:
            master_rendered = False
            sp_context = shot_obj.get_path_context()
            sp_context['wip_name'] = 'master'
            sp_context['disc'] = 'comp'
            master_render_dir = \
                sp_context.get_render_path('sh_comp_output_dir',
                                           version=version_num,
                                           namespace='shot')
            if os.path.isdir(master_render_dir):
                master_sequence = \
                    FrameSequence.get_sequences_from_dir(master_render_dir)
                master_rendered = len(master_sequence) > 0
        if discipline == Discipline.MATTE:
            painting_status = _get_wip_version_status(version_num,
                                                      painting_versions,
                                                      painting_rendered,
                                                      painting_render_dir,
                                                      colors)
            merged_status = _get_wip_version_status(version_num,
                                                    merged_versions,
                                                    merged_rendered,
                                                    merged_render_dir,
                                                    colors)
            if ansi_color:
                IO.info('|{0:^15}|{1:^47}|{2:^47}|'.format(version_num,
                                                           painting_status,
                                                           merged_status))
            else:
                IO.info('|{0:^15}|{1:^38}|{2:^38}|'.format(version_num,
                                                           painting_status,
                                                           merged_status))
        elif discipline == Discipline.COMP:
            master_status = _get_wip_version_status(version_num,
                                                    master_versions,
                                                    master_rendered,
                                                    master_render_dir,
                                                    colors)
            if ansi_color:
                IO.info('|{0:^15}|{1:^86}|'.format(version_num, master_status))
            else:
                IO.info('|{0:^15}|{1:^68}|'.format(version_num, master_status))
    IO.info('{0:=^95}'.format(''))


def _get_wip_version_status(version_num, wip_versions, rendered,
                            render_dir, colors):
    not_rendered = '{0}Not Rendered{1}'.format(colors['red'],
                                               colors['end_color'])
    if version_num in wip_versions:
        time_field = DateTimeField()
        timestamp = \
            time_field.to_human_readable(wip_versions[version_num]
                                         .modified_at)
        wip_status = '{0}Submitted ({1}){2}'\
            .format(colors['green'], timestamp, colors['end_color'])
    elif rendered:
        seconds = os.path.getmtime(render_dir)
        time_struct = time.localtime(seconds)
        time_field = DateTimeField()
        timestamp = \
            time_field.to_human_readable(time_field
                                         .serialize(time_struct))
        wip_status = \
            '{0}Rendered ({1}){2}'.format(colors['yellow'],
                                          timestamp,
                                          colors['end_color'])
    else:
        wip_status = not_rendered
    return wip_status


# For each shot in a sequence, determines if the painting and merged media have
# been submitted for the latest wip version of the shot, and prints the
# results.
def list_sequence_media(seq_obj, discipline=Discipline.MATTE,
                        ansi_color=True):  # IGNORE:W0613
    IO.info('\nLatest submitted master WIP versions for sequence {0}:'\
            .format(seq_obj.name))
    IO.info('{0:=^80}'.format(''))
    IO.info('|{0:^15}|{1:^15}|{2:^15}|{3:^30}|'.format('Shot Name',
                                                       'Media Type',
                                                       'Version', 'Date'))
    IO.info('|{0:=^78}|'.format(''))
    sorted_shots = sorted([shot for shot in seq_obj.shots.all() if
                    len(shot.media.where(disc=discipline).all()) > 0])
    for shot_obj in sorted_shots:
        media = shot_obj.media.where(disc=discipline).all()
        for media_type in sorted(media, key=lambda media: media.element):
            media_version = media_type.versions.get_last()
            if media_type.element == 'merged' or\
               media_type.element == 'master':
                shot_name = shot_obj.name
            else:
                shot_name = ''
            time_field = DateTimeField()
            timestamp = time_field.to_human_readable(media_version.modified_at)
            IO.info('|{0:^15}|{1:^15}|{2:^15}|{3:^30}|'\
                    .format(shot_name, media_type.element,
                            media_version.number, timestamp))
        if len(media) > 0 and shot_obj.name != sorted_shots[-1].name:
            IO.info('|{0:-^78}|'.format(''))
    IO.info('{0:=^80}'.format(''))


# Check cameras and geometry in the nuke scene to see if they are up to date
# with the cached versions.
def validate_caches():
    response_list = ResponseList()
    con = PipeContext.from_env()
    anim = camera_utils.get_latest_anim(con.get_shot_obj())
    camera_published_version = anim.camera_anim.published_number
    camera_nodes = nuke.allNodes('Camera2')
    for camera in camera_nodes:
        node_version = int(camera.knob('Version').value())
        if camera_published_version > node_version:
            fail = Failure('Camera {0} version is out of date'\
                           .format(camera.name()))
            response_list.append(fail)
        else:
            success = Success('Camera {0} is up to date.'\
                              .format(camera.name()))
            response_list.append(success)
    read_geo_nodes = nuke.allNodes('ReadGeo2')
    # Build the list of published assemblies to check against.
    published_geo = {}
    for assembly_inst in con.get_shot_obj().assembly_instances:
        if not assembly_inst.active:
            continue
        assembly_override = assembly_inst.get_overrides()
        published_version = assembly_override.published_version
        if published_version:
            assembly_name = published_version.assembly_instance.name
            published_geo[assembly_name] = published_version
    for read_geo in read_geo_nodes:
        file_path = read_geo.knob('file').value()
        geo_rex = re.match('.*\/(.*)\/v(\d+)\/.*\.abc', file_path)
        if not geo_rex:
            continue
        assembly_name = geo_rex.group(1)
        assembly_version = int(geo_rex.group(2))
        if assembly_name in published_geo:
            published_version = published_geo[assembly_name]
            published_version_num = published_version.number
            if published_version_num > assembly_version:
                fail = Failure('ReadGeo {0} version is out of date.'\
                               .format(read_geo.name()))
                response_list.append(fail)
            else:
                success = Success('ReadGeo {0} is up to date.'\
                                  .format(read_geo.name()))
                response_list.append(success)
        else:
            fail = Failure('ReadGeo {0} does not correspond to a published '
                           'assembly.'.format(read_geo.name()))
            response_list.append(fail)

    return response_list


# Create reflection map node set for latlong exr
def ReflectionMapNodes():
    #create the nodes
    stepone = nuke.nodes.rfxSphericalCams()
    steptwo = nuke.nodes.rfxReflectionMap()

    #select the nodes
    stepone.knob('selected').setValue(True)
    steptwo.knob('selected').setValue(True)

    #store the node positions
    steponePosX = stepone.xpos()
    steptwoPosX = steptwo.xpos()

    #position the nodes
    stepone['xpos'].setValue(steponePosX + 40)
    steptwo['xpos'].setValue(steptwoPosX + 60)

    #deselect the nodes
    stepone.knob('selected').setValue(False)
    steptwo.knob('selected').setValue(False)

    return


def rfxMPwrite():
  with nuke.root():
    nuke.nodePaste('/code/global/nuke/gizmos/9.0v5/mattepainting/toolsets/Mattepainting_Write.nk')

# Replaces all rCustomChannel nodes in a scene with
# copy channel nodes, which create a channel set of
# the same name as the rCustomChannel node.
def replace_custom_channel_nodes():
    def set_up_channel(copy_node, num, channel_name):
        layer_command = '{0} {0}.{1}'.format(new_name, channel_name)
        nuke.tcl('add_layer {%s}' % layer_command)
        from_knob = copy_node.knob('from{0}'.format(num))
        from_knob.setValue('rgba.' + channel_name)
        to_knob = copy_node.knob('to{0}'.format(num))
        to_knob.setValue('{0}.{1}'.format(new_name, channel_name))
    for node in nuke.allNodes('rCustomChannel'):
        rgba_value = node.knob('rgba_knob').value()
        # Set up node new_name and position
        name = node.name()
        # Fix up bad names
        new_name = re.sub('\W', '_', name).lower()
        xpos = node.xpos()
        ypos = node.ypos()
        copy_channel_node = nuke.nodes.Copy()  # @UndefinedVariable
        copy_channel_node.setName('{0}_copy_channel'.format(new_name))
        copy_channel_node.setXpos(xpos)
        copy_channel_node.setYpos(ypos)
        # Set node input and output
        input_node = node.input(0)
        output_node = node.dependent()[0]
        node.setInput(0, None)
        copy_channel_node.setInput(0, input_node)
        input_num = 0
        for num in range(output_node.inputs()):
            input_node = output_node.input(num)
            if input_node is node:
                input_num = num
        output_node.setInput(input_num, copy_channel_node)
        nuke.delete(node)
        # Set channel inputs on copy node
        if re.match('.*r.*', rgba_value) or rgba_value == "all":
            set_up_channel(copy_channel_node, 0, 'red')
        if re.match('.*g.*', rgba_value) or rgba_value == "all":
            set_up_channel(copy_channel_node, 1, 'green')
        if re.match('.*b.*', rgba_value) or rgba_value == "all":
            set_up_channel(copy_channel_node, 2, 'blue')
        if re.match('.*a.*', rgba_value) or rgba_value == "all":
            set_up_channel(copy_channel_node, 3, 'alpha')
        IO.error('rCustomChannel node "{0}" replaced with Copy node "{1}"'\
                 .format(name, copy_channel_node.name()))


def get_target_path(file_path, wip_dir):
    dir_names = os.path.dirname(file_path)
    subdir_names = []
    while os.path.split(dir_names)[1] != '':
        subdir_name = os.path.split(dir_names)[1]
        dir_names = os.path.split(dir_names)[0]
        if subdir_name != 'master':
            subdir_names.append(subdir_name)
        else:
            dir_names = ''
    new_path = wip_dir
    while len(subdir_names) > 0:
        new_path = os.path.join(new_path, subdir_names.pop())
    new_path = os.path.join(new_path, os.path.basename(file_path))
    if not os.path.exists(os.path.dirname(new_path)):
        os.makedirs(os.path.dirname(new_path))
    return new_path
