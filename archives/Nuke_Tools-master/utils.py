#!/usr/bin/python

import re
import os
import sys
import glob
from collections import defaultdict
import itertools

from pipe_utils.file_system import safe_make_dir, relative_link
from path_lib import utils, PathContext
from path_lib.extractor import extract

VERSION_REGEX = re.compile('\.v(\d+).nk')
FILE_REGEX = re.compile('^\w*file\s+(.*)$')
FILENAME_REGEX = None
PATH_REGEX = None

def get_filename_regex():
    namespace = '(?P<namespace>\w+)'
    eye = '(?P<eye>%v|l|r)'
    frame = '(?P<frame>%04d|####|[0-9]+)'
    extension = '(?P<extension>[a-zA-Z]+)'

    regex = '{0}.{1}.{2}.{3}'.format(namespace, eye, frame, extension)

    return re.compile(regex)

def get_path_regex():
    root = '(?P<root>render|work|store)'
    project = '(?P<project>\w+)'
    sequence = '(?P<sequence>[a-zA-Z0-9]+)'
    shot = '(?P<shot>[a-zA-Z0-9]+)'
    discipline = '(?P<discipline>[a-zA-Z]+)'
    wip = '(?P<wip>\w+)'
    namespace = '(?P<namespace>\w+)'
    version = '(?P<version>v[0-9]+|live)'

    keys = ['/', root, project, 'sequences', sequence, shot, discipline, wip, namespace, version]
    regex = os.path.join(*keys)

    return re.compile(regex)

class RPath(object):
    VERSION_REGEX = re.compile('(?<=v)(%\d{2}d)|(?<=v)(\d+)')
    FRAME_REGEX = re.compile('(?<=\.)(%\d{2}d)(?=\.)|(?<=\.)(#+)(?=\.)|(?<=\.)(\d{4})(?=\.)')
    EYE_REGEX = re.compile('(?<=\.)(%v)(?=\.)|(?<=\.)([l,r])(?=\.)')
    def __init__(self, *args, **kwargs):
        self._path = None
        if kwargs.has_key('path'):
            self.set_path(kwargs.get('path'))

    def set_path(self, path):
        self._path = path

    def get_path(self):

        return self._path

    def get_basename(self):
        path = self.get_path()
        result = None
        if path:
            result = os.path.basename(path)

        return result

    def get_dirname(self):
        path = self.get_path()
        result = None
        if path:
            split = os.path.splitext(path)
            result = split[0]
            if split[-1]:
                result = os.path.dirname(path)

        return result

    def islink(self):
        path = self.get_path()
        result = None
        if path:
            result = os.path.islink(path)

        return result

    def exists(self):
        path = self.get_path()
        result = None
        if path:
            realpath = os.path.realpath(path)
            result = os.path.exists(path)

        return result

    def make(self):

        directory = self.get_dirname()
        safe_make_dir(directory, make_all=True)

        return directory

    def make_live(self):

        # regex = self.get_version_regex()
        directory = self.get_version_dir()

        base_dir = os.path.dirname(directory)

        relative_link(directory, utils.join(base_dir, 'live'))

    def get_regex(self, type=None, pattern=None):
        regex = None
        if pattern is None and type:
            regex = eval('self.{0}_REGEX'.format(type.upper()))
        elif pattern:
            regex = re.compile(pattern)

        return regex

    def get_frame_regex(self):

        return self.get_regex(type='frame')

    def get_eye_regex(self):

        return self.get_regex(type='eye')

    def get_version_regex(self):

        return self.get_regex(type='version')

    def get_match_data(self, match):
        group = None
        if match:
            groups = [g for g in match.groups() if not g is None]

            if groups:
                group = groups[0]

        return group

    def get_path_context(self):
        context = None
        path = self.get_path()
        if path:
            context = extract(path)

        return context

    def extract_formula(self, formula):
        context = None
        path = self.get_path()
        if path:
            result = formula_extract(formula, path)
            if result:
                context = result.payload
            else:
                sys.stderr.write('{0}\n'.format(result))

        return context

    def set_eye(self, eye, path=None):
        regex = self.get_eye_regex()

        if path:
            path = regex.sub(eye, path)
        else:
            orig_path = self.get_path()
            path = regex.sub(eye, orig_path)
            self.set_path(path)

        return path

    def set_frame(self, frame, path=None):
        regex = self.get_frame_regex()

        if path:
            path = regex.sub(frame, path)
        else:
            path = self.get_path()
            path = regex.sub(eye, orig_path)
            self.set_path(path)

        return path

    def set_version(self, version, path=None):
        regex = self.get_version_regex()

        if path:
            path = regex.sub('{0:03d}'.format(version), path)
        else:
            path = self.get_path()
            path = regex.sub('{0:03d}'.format(version), path)
            self.set_path(path)

        return path

    def has(self, type, path=None):
        regex = self.get_regex(type=type)
        if not path:
            path = self.get_path()

        result = False
        if regex.search(path):
            result = True

        return result

    def version_up(self):
        version = self.get_next_version()
        self.set_version(version)

        return version

    def get_extension(self):
        ext = None
        path = self.get_path()
        if path:
            ext = os.path.splitext(path)[-1]

        return ext

    def get_frame(self, path=None):
        regex = self.get_frame_regex()
        if not path:
            path = self.get_path()

        frame = None
        if path:
            match = regex.search(path)
            frame = self.get_match_data(match)

        return frame

    def get_version_dir(self, path=None):
        regex = self.get_version_regex()
        if not path:
            path = self.get_path()

        split = path.split('/')
        repiece = []
        for item in split:
            repiece.append(item)
            if regex.search(item):
                break

        version_dir = utils.join(*repiece)

        return version_dir

    def get_version(self, path=None):
        regex = self.get_version_regex()
        if not path:
            path = self.get_path()

        version = None
        if path:
            match = regex.search(path)
            version = self.get_match_data(match)

        return version

    def get_eye(self, path=None):
        regex = self.get_eye_regex()
        if not path:
            path = self.get_path()

        eye = None
        if path:
            match = regex.search(path)
            eye = self.get_match_data(match)

        return eye

    def get_latest_version(self):
        version = None
        regex = self.get_version_regex()

        path = self.get_path()
        dirname = self.get_version_dir()
        if dirname:
            glob_path = regex.sub('*', dirname)
            directories = glob.glob(glob_path)
            if directories:
                version = max([int(self.get_version(tmp)) for tmp in directories])

        return version

    def get_next_version(self):
        version = 1
        tmp_version = self.get_latest_version()
        if tmp_version:
            version = tmp_version + 1

        return version

    def has_frame(self, path=None):

        return self.has('frame', path)

    def has_version(self, path=None):

        return self.has('version', path)

    def has_eye(self, path=None):

        return self.has('eye', path)

    def __str__(self):
        return self.get_path()

# VERSION_REGEX = re.compile('(?<=v)(%\d{2}d)|(?<=v)(\d{3})')
# FRAME_REGEX = re.compile('(?<=\.)(%\d{2}d)(?=\.)|(?<=\.)(#+)(?=\.)|(?<=\.)(\d{4})(?=\.)')
# EYE_REGEX = re.compile('(?<=\.)(%v)(?=\.)|(?<=\.)([l,r])(?=\.)')
class RSequence(RPath):
    def __init__(self, *args, **kwargs):
        super(RSequence, self).__init__(*args, **kwargs)

        self._files = []

    def find_files(self):
        path = self.get_path()
        if self.has_frame():
            path = self.set_frame('*', path=path)
        if self.has_eye():
            path = self.set_eye('*', path=path)

        files = glob.glob(path)
        self.set_files(files)

        return files

    def set_files(self, files):

        self._files = files

    def get_files(self):

        return self._files

    def find_missing_frames(self, start_frame=None, end_frame=None):

        files = self.get_files()
        missing_frames = {}
        if not files:
            files = self.find_files()

        if files:
            frames = defaultdict(list)
            for tmp in files:
                eye = self.get_eye(path=tmp)
                eye = eye if eye else 'm'
                if self.has_frame():
                    frame = int(self.get_frame(path=tmp))
                    frames[eye].append(frame)

            full_set = None
            if start_frame or end_frame:
                full_set = set(xrange(start_frame, end_frame + 1))

            for key in frames.keys():
                key_set = full_set
                if not key_set:
                    key_set = set(xrange(min(frames[key]), max(frames[key]) + 1))

                original_set = set(frames[key])
                missing_set = sorted(list(key_set - original_set))
                if missing_set:
                    missing_frames[key] = ranges(missing_set)

        return missing_frames

def get_latest_inc_version(path):
    version = 1
    versions = []
    all_scripts = glob.glob('%s/*.nk' % (path))
    if not all_scripts:
        return version
    for script in all_scripts:
        match = VERSION_REGEX.search(script)
        if match:
            versions.append(int(match.group(1)))

    if not versions:
        return version

    versions.sort()
    latest = versions[-1]
    version = latest + 1

    return version

def extract_path_data(path):
    global PATH_REGEX
    global FILENAME_REGEX

    result = None

    if not PATH_REGEX or not FILENAME_REGEX:

        PATH_REGEX = get_path_regex()
        FILENAME_REGEX = get_filename_regex()

    split = path.split('/')
    if len(split) == 11:

        directory = os.path.dirname(path)
        basename = os.path.basename(path)

        path_match = PATH_REGEX.search(directory)
        base_match = FILENAME_REGEX.search(basename)

        if path_match and base_match:
            result = PathContext()

            result['root'] = path_match.group('root')
            result['proj_name'] = path_match.group('project')
            result['seq_name'] = path_match.group('sequence')
            result['shot_name'] = path_match.group('shot')
            result['disc'] = path_match.group('discipline')
            result['wip_name'] = path_match.group('wip')
            result['namespace'] = path_match.group('namespace')
            result['version'] = path_match.group('version')

            result['eye'] = base_match.group('eye')
            result['frame'] = base_match.group('frame')
            result['ext'] = base_match.group('extension')

    return result

def ranges(i):
    ranges = []
    for a, b in itertools.groupby(enumerate(i), lambda (x, y): y - x):
        b = list(b)
        ranges.append((b[0][1], b[-1][1]))

    return ranges

def create_script_archive(script_name, path_context=None, label='standard'):

    if path_context is None:
        path_context = extract(script_name)

    script_basename = os.path.basename(script_name)
    wip_filename = os.path.splitext(script_basename)[0]
    if path_context.has_vars('shot_name'):
        cache_dir = path_context.get_path('sh_comp_store_script_dir',
                                      wip_filename=wip_filename)
        version = get_latest_inc_version(cache_dir)
        cache_scene = path_context.get_path('sh_comp_store_script_file',
                                        wip_filename=wip_filename,
                                        label=label,
                                        version=version)
    elif path_context.has_vars('seq_name'):
        cache_dir = path_context.get_path('sq_comp_store_script_dir',
                                      wip_filename=wip_filename)
        version = get_latest_inc_version(cache_dir)
        cache_scene = path_context.get_path('sq_comp_store_script_file',
                                        wip_filename=wip_filename,
                                        label=label,
                                        version=version)
    else:
        cache_dir = path_context.get_path('pr_comp_store_script_dir',
                                      wip_filename=wip_filename)
        version = get_latest_inc_version(cache_dir)
        cache_scene = path_context.get_path('pr_comp_store_script_file',
                                        wip_filename=wip_filename,
                                        label=label,
                                        version=version)
    if not os.path.exists(cache_dir):
        safe_make_dir(cache_dir, make_all=True)

    write_handle = open(cache_scene, 'w')
    handle = open(script_name, 'r')
    handle.seek(0)

    for line in handle.readlines():
        match = FILE_REGEX.search(line.strip())
        if not match:
            write_handle.write(line)
            continue

        path = match.group(1)
        path = re.sub(r'(\(|\))', r'\\\1', path)
        dirname = os.path.dirname(path)
        realdir = os.path.realpath(dirname)
        basename = os.path.basename(path)

        new_path = os.path.join(realdir, basename)
        new_line = re.sub(path, new_path, line)
        write_handle.write(new_line)

    handle.close()
    write_handle.flush()
    write_handle.close()

    return cache_scene

if __name__ == '__main__':
    path_string = '/store/19318_BOL/sequences/0800/matte/master/sky/v%03d'
    path = RPath(path=path_string)

    path_string = '/store/19318_BOL/sequences/0800/matte/master/sky/v001'
    path = RPath(path=path_string)

    print 'Version', path.get_version()
    print 'Has version', path.has_version()
    print 'Has frame', path.has_frame()
    print 'Has eye', path.has_eye()
    print

    path_string = '/store/19318_BOL/sequences/0800/matte/master/sky/v001/my_filename.%04d.%v.exr'
    path = RPath(path=path_string)
    print 'Version', path.get_version()
    print 'Frame', path.get_frame()
    print 'Eye', path.get_eye()
    print 'Has frame', path.has_frame()
    print

    path_string = '/store/19318_BOL/sequences/0800/matte/master/sky/v001/my_filename.0101.l.exr'
    path = RPath(path=path_string)
    print 'Version', path.get_version()
    print 'Frame', path.get_frame()
    print 'Eye', path.get_eye()
    print

    print 'Latest', path.get_latest_version()
    print 'Next', path.get_next_version()
    print

    path_string = '/store/19318_BOL/sequences/0700/matte/master/sky/v001/my_filename.0101.l.exr'
    path = RPath(path=path_string)

    print 'Latest', path.get_latest_version()
    print 'Next', path.get_next_version()
    print 'Version Up', path.version_up()
    print 'Has version', path.has_version()
    print 'Has frame', path.has_frame()
    print 'Has eye', path.has_eye()
    print 'Version dir', path.get_version_dir()
    print

