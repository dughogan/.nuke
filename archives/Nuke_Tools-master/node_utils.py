#!/usr/bin/env python

"""
@author:
    dhogan

@description:
    - Set of tools to create, manipulate, and query nodes in Nuke.

@applications
    - nuke

"""

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- IMPORTS --#
# builtin
from __future__ import with_statement
import sys
import re
import os
import glob
import string
import time
import subprocess
from collections import defaultdict
import random
import tempfile
from waflib.Logs import get_color

# third party
try:
    import nuke
except:
    pass

# internal
import script_utils

# external
from pipe_utils import file_system, list_utils, dict_utils
from pipe_utils.response import Success, Failure
from pipe_utils.io import IO

from pipe_api.env import get_pipe_context

from pipe_core import PipeContext, WipContext, Project
from pipe_core.model.wip_output_types import WipOutputType
from pipe_core.model.wip_output import WipOutputManager

from path_lib import PathContext
from path_lib.extractor import formula_extract
from path_lib.formula_manager import FORMULA_MANAGER

PROJ_NAME = Project.current().short_name
EXRCYCLER_PATH = '/data/film/apps/reelfx/apps/linux/exrcycler'
DJV_PATH = '/data/film/apps/reelfx/apps/linux/djv/djv'
RV_PATH = '/usr/local/tweak/rv/bin/rv'

AXIS_LUT = {'y':'ypos', 'x':'xpos'}
SPACE_LUT = {'y':'screenHeight', 'x':'screenWidth'}
#import rfxUtils
#import rfxGetPath
#import script_utils
#import nuke_gui

#import list_utils
#import pipeline
#import XmlDict
#from xml_imports import ElementTree

#----------------------------------------------------------------------------#
#--------------------------------------------------------------- FUNCTIONS --#
def create_node(node_type, custom_knobs=None, **kwargs):
    """
    Creates the requested node with the ability to pass in custom knobs and
    settings. The "is_rfx" Boolean_Knob is added by default.

    @type node_type: str
    @param node_type: The name of the Node Type.
    @type custom_knobs: dict
    @keyword custom_knobs: A dictionary containing all the custom String_Knobs
    that should be added at creation. The dictionary key will be the name of
    the knob and the dictionary's key value will be the value of the knob.

    @rtype: Node
    @returns: The requested node type with the requested knobs and values.

    """

    node = None
    root_node = get_root(kwargs.get('root'))
    with root_node:
        if kwargs.has_key('name'):
            if not kwargs.get('name'):
                del kwargs['name']
            else:
                kwargs['name'] = get_available_name(kwargs.get('name'))
        node_function = eval('nuke.nodes.{0}'.format(node_type))
        if node_type == 'DeepRead':
            node = node_function(file='file tmp')
        else:
            node = node_function()

        set_knobs(node, kwargs)
        if custom_knobs:
            add_knobs(node, custom_knobs)
        node['selected'].setValue(kwargs.get('selected'))


    return node


def insert_knob(node, knobs, prev_knob=None):
    knobs = list_utils.to_list(knobs)
    if prev_knob:
        if isinstance(prev_knob, str):
            prev_knob = node.get_knob(prev_knob)
        popped = []
        for i in xrange(node.numKnobs() - 1, -1, -1):
            tmp_knob = node.knob(i)
            if tmp_knob is prev_knob:
                break
            node.removeKnob(tmp_knob)
            popped.append(tmp_knob)
        for knob in knobs:
            if isinstance(knob, nuke.Knob):
                node.addKnob(knob)
            else:
                raise TypeError('Knob must be of type nuke.Knob not < {0}'
                                ' >'.format(type(knob)))

        while len(popped) > 0:
            tmp_knob = popped.pop()
            node.addKnob(tmp_knob)

    else:
        for knobs in knobs:
            node.addKnob(knob)

    return knob


def showPanel():
    this_node = nuke.thisNode()
    this_node.showControlPanel()


def add_knobs(node, custom_knobs):
    """
    Takes the given node and adds the specified knobs and sets their values.

    @type node: Node
    @param node: Nuke node to add knobs to.
    @type custom_knobs: dict
    @param custom_knobs: A dictionary containing all the custom String_Knobs
    that should be added to the node. The dictionary key will be the name of
    the knob and the dictionary's key value will be the value of the knob.

    @rtype: Boolean
    @returns: The Result

    """
    for key in custom_knobs.keys():
        tmp_knob = nuke.String_Knob(key)
        tmp_knob.setValue(custom_knobs[key])
        node.addKnob(tmp_knob)

    return True

def make_rfx(nodes=None):
    if nodes is None:
        nodes = get_selected_nodes()
    nodes = list_utils.to_list(nodes)
    for node in nodes:
        if not node.knobs().has_key('is_rfx'):
            knob = nuke.Boolean_Knob('is_rfx')
            node.addKnob(knob)

def duplicate_nodes(nodes=None):
    if nodes is None:
        nodes = get_selected_nodes()
    nodes = list_utils.to_list(nodes)

    ng = RNukeNodeGraph(nodes=nodes)

    tmp = tempfile.NamedTemporaryFile()
    nuke.nodeCopy(tmp.name)
    selection = clear_selection()
    nuke.nodePaste(tmp.name)
    new_nodes = get_selected_nodes()
    nng = RNukeNodeGraph(nodes=new_nodes)

    nng.align_top(ng)
    nng.snap_right(ng, additional=20)

    center_on_screen(nng.get_nodes())

    return new_nodes

def get_parent(node):

    return nuke.toNode('.'.join(node.fullName().split('.')[:-1])) or nuke.root()

def get_root(root=None):

    if not root:
        root = 'root'
    root_node = None
    if isinstance(root, str):
        root_node = nuke.toNode(root)
    elif isinstance(root, nuke.Node):
        root_node = root

    return root_node

def filter_nodes(nodes, **kwargs):

    inverse = kwargs.get('inverse')
    filters = list_utils.to_list(kwargs.get('filters'))
    nodes = list_utils.to_list(nodes)

    if not inverse:
        filtered_nodes = [node for node in nodes if node.Class() in filters]
    else:
        filtered_nodes = [node for node in nodes if not node.Class() in filters]

    return filtered_nodes

# def nuke_bullshittery():
#     # If you have a knob (in a variable `insertAfter`)
#     popped = []
#     for i in xrange(node.numKnobs() - 1, -1, -1):
#         knob = node.knob(i)
#         if knob is insertAfter:
#             break
#         node.removeKnob(knob)
#         popped.append(knob)

#     for knob in popped:
#         node.addKnob(knob)

def has_attrs(node, attrs):

    status = True
    for attr in list_utils.to_list(attrs):
        if not node.knobs().has_key(attr):
            status = False

        if not status:
            break


    return status

def check_attrs(node, attrs):

    status = True
    for attr in attrs.keys():
        if node.knobs().has_key(attr):
            status = node[attr].value() == attrs[attr]
        else:
            status = False

        if not status:
            break

    return status

def get_available_inputs(node):
    labels = {}
    with node:
        for inp in nuke.allNodes("Input"):
            num = int(inp['number'].value())
            name = inp.name()
            labels[name] = num

    return labels

def node_query(nodes=None, **kwargs):

    # This should be a dictionary of attributes you wish to check for.
    attrs = kwargs.get('attrs')
    # Filters you might want.
    filters = kwargs.get('filters', [])

    # Wildcard name match.
    name = None
    if kwargs.has_key('name'):
        name = re.compile('^{0}$'.format(kwargs.pop('name').replace('*', '.*')))

    # Inverse the selection.
    inverse = kwargs.get('inverse', False)
    # Recurse down into group.  This will return a dictionary in place of the node.
    recursive = kwargs.get('recursive', True)
    # Get the root node. It will default to 'root'.
    root_node = get_root(kwargs.get('root'))
    if not nodes:
        nodes = list_utils.to_list(nuke.allNodes(group=root_node))

    if recursive:
        for node in list_utils.to_list(nodes):
            if node.Class() == 'Group':
                group_kwargs = dict(kwargs)
                group_kwargs['root'] = node
                group_kwargs['nodes'] = None
                new_nodes = node_query(**group_kwargs)
                nodes.extend(new_nodes)

    if attrs and isinstance(attrs, dict):
        nodes = [node for node in nodes if check_attrs(node, attrs)]
    elif attrs and isinstance(attrs, (list, tuple, str)):
        nodes = [node for node in nodes if has_attrs(node, list_utils.to_list(attrs))]

    if name:
        nodes = [tmp for tmp in nodes if name.search(tmp.knob('name').value())]

    if filters:
        nodes = filter_nodes(nodes, filters=filters, inverse=inverse)

    if kwargs.get('active'):
        nodes = [tmp for tmp in nodes if tmp.knobs().has_key('disable') and not tmp['disable'].value()]

    return nodes

def add_rfx_tab(nodes=None):
    """
    Takes the selected nodes (or all nodes if none are selected) and
    adds the "is_rfx" knob (if not already present) to the node and sets it
    to True.

    @type nodes: list
    @param nodes: A list of Nuke nodes.

    @rtype: bool
    @returns: Success or Fail

    """
    if nodes is None:
        nodes = get_selected_nodes()
    elif not isinstance(nodes, list):
        nodes = [nodes]

    for node in nodes:
        if not node.knobs().has_key('rfx'):
            rfx_knob = nuke.Tab_Knob('rfx', 'RFX')
            node.addKnob(rfx_knob)

    return True

def get_rfx(nodes=None):
    """
    Takes the selected nodes (or all nodes if none are selected) and
    returns a list of nodes with is_rfx checked.

    @type nodes: list
    @param nodes: A list of Nuke nodes.

    @rtype: list
    @returns: List of nodes with is_rfx checked.

    """
    if nodes is None:
        nodes = get_all_nodes()
    elif not isinstance(nodes, list):
        nodes = [nodes]

    rfx_nodes = []
    for node in nodes:
        if is_rfx(node):
            rfx_nodes.append(node)

    return rfx_nodes

def is_rfx(node):
    """
    Check the state of the node, whether it is an RFX node or not.

    @type node: Node
    @param node: The node you want to check.

    @rtype: bool
    @returns: The result.

    """
    knob = 'is_rfx'
    return node.knobs().has_key(knob) and node[knob].value()


def align_backdrop_horizontally(nodes, backdrop_node):
    backdrop_xpos = backdrop_node.xpos()
    # When running build shot from the command line, Nuke doesn't calculate
    # the backdrop node's screenWidth properly, so this needs to be hard-coded
    # too. - lkelly
    backdrop_width = 355
    for node in nodes:
        node_xpos = node.xpos()
        # screenWidth doesn't evaluate during callback on creation so just
        # doing this as a workaround. - lkelly
        node_width = 80
        node_xpos = backdrop_xpos + (backdrop_width / 2) - (node_width / 2)
        node.setXpos(node_xpos)


def get_all_nodes(filters=None, active=False, in_groups=True):
    """
    Get all nodes in a script.

    @type filters: list, str
    @param filters: Pass into the nuke command to filter results.

    @rtype: list
    @returns: All nodes of the given type in the current script.

    """
    nodes = []
    all_nodes = nuke.allNodes()
    tmp = all_nodes
    if filters:
        tmp = filter_nodes(all_nodes, filters=filters)
    nodes.extend(tmp)

    groups = filter_nodes(all_nodes, filters='Group')
    if groups and in_groups:
        tmp = []
        for group in groups:
            with group:
                tmp.extend(get_all_nodes(filters=filters, active=active, in_groups=in_groups))
        if filters:
            tmp = filter_nodes(tmp, filters='Group')
        nodes.extend(tmp)

    if active:
        nodes = [node for node in nodes if not node['disable'].value()]

    return nodes

def get_selected_nodes(filters=None):
    """
    Gets all nodes that the user has selected.

    @type filters: list, str
    @param filters: Pass into the nuke command to filter results.

    @rtype: list
    @returns: All the selected nodes in the script.

    """
    nodes = []
    selected_nodes = nuke.selectedNodes()
    tmp = selected_nodes
    if selected_nodes:
        if filters:
            tmp = filter_nodes(selected_nodes, filters=filters)
        nodes.extend(tmp)

    groups = filter_nodes(selected_nodes, filters='Group')
    if groups:
        for group in groups:
            tmp = []
            with group:
                tmp.extend(nuke.selectedNodes())
                if not tmp:
                    tmp.extend(nuke.allNodes())
            if filters:
                tmp = filter_nodes(tmp, filters=filters)
            nodes.extend(tmp)

    return nodes

# def filter_nodes(filters, nodes, inverse=False):
#     """
#     Filter the selected nodes.

#     @type filters: list, str
#     @param filters: The type of nodes you want out of the given nodes.
#     @type nodes: list
#     @param nodes: The nodes you want to filter.
#     @type inverse: bool
#     @param inverse: Whether you want to inverse the effect of the node filter.

#     @rtype: list
#     @returns: The filtered node list.

#     """
#     filtered_nodes = []
#     filters = list_utils.to_list(filters)
#     for node_filter in filters:
#         for node in nodes:
#             if inverse:
#                 if not node.Class() == node_filter:
#                     filtered_nodes.append(node)
#             else:
#                 if node.Class() == node_filter:
#                     filtered_nodes.append(node)

#     return filtered_nodes

def clear_selection():
    """
    Clears the selected nodes.

    @rtype: list
    @returns: The previously selected nodes.

    """
    selected_nodes = get_selected_nodes()
    for node in selected_nodes:
        node['selected'].setValue(False)

    return selected_nodes

def add_to_selection(nodes):
    """
    Adds the given nodes to the current selection.

    @rtype: bool
    @returns: The result.

    """
    for node in nodes:
        try:
            node['selected'].setValue(True)
        except ValueError:
            continue

    return True

def get_bottom_pos():
    """
    Gets the bottom position of the entire script

    @rtype: list
    @returns: The buttom of the script in x and y.

    """
    bottom_xpos = 0
    bottom_ypos = 0
    nodes = get_selected_nodes()
    if not nodes:
        nodes = get_all_nodes()
    for node in nodes:
        if node['xpos'].value() > bottom_xpos:
            bottom_xpos = node['xpos'].value()
        if node['ypos'].value() > bottom_ypos:
            bottom_ypos = (node['ypos'].value() +
                    node.screenHeight() + 100)
    add_to_selection(selected_nodes)

    return [bottom_xpos, bottom_ypos]

def get_dimensions(nodes=None):

    nodes = list_utils.to_list(nodes if nodes else get_selected_nodes())

    dimensions = {}
    for axis in AXIS_LUT.keys():
        dimensions[axis] = {'min' : 0, 'max' : 0}


    for axis in dimensions.keys():
        values = []
        for node in nodes:
            if axis == 'y':
                height = node.screenHeight()
                value = height if height > 65 else 90
            else:
                width = node.screenWidth()
                value = width if width > 65 else 80

            values.append(node[AXIS_LUT.get(axis)].value())
            values.append(node[AXIS_LUT.get(axis)].value() + value)

        dimensions[axis]['min'] = min(values)
        dimensions[axis]['max'] = max(values)

    return dimensions

def get_min_max(nodes=None):
    """
    Gets the minimum and maximum positions of all the nodes given. If none
    are given, all nodes will be used.

    @type nodes: list
    @param nodes: The nodes you wish to gather position data from.

    @rtype: tuple
    @returns: The min/max x/y values for the given nodes.

    """
    xpos = []
    ypos = []
    xposes = []
    yposes = []

    if not nodes:
        nodes = get_all_nodes(in_groups=False)

    nodes = list_utils.to_list(nodes)
    for node in nodes:
        node.xpos()
        node.screenWidth()
        width = node.screenWidth()
        height = node.screenHeight()
        if width <= 65:
            width = 80
        if height <= 65:
            height = 90

        xposes.append(node['xpos'].value())
        yposes.append(node['ypos'].value())

        xposes.append(node['xpos'].value() + width)
        yposes.append(node['ypos'].value() + height)

    xpos.append(min(xposes))
    xpos.append(max(xposes))

    ypos.append(min(yposes))
    ypos.append(max(yposes))

    return xpos, ypos

def get_knobs(node, *args):
    """
    Check the given node for meta data knobs.

    @type node: Node
    @param node: The node you want to pull meta data from.

    @rtype: dict
    @returns: All the meta data requested. Given name is the key.

    """
    knob_values = {}

    for knob in args:
        if node.knobs().has_key(knob):
            knob_values[knob] = node[knob].value()
            continue
        knob_values[knob] = None

    return knob_values

def set_knobs(node, meta_knobs, add_knobs=False):
    """
    Takes the given node and sets the specified meta knobs. If the knobs
    do not exist, they are added as string knobs.

    @type node: Node
    @param node: Nuke node to add knobs to.
    @type meta_knobs: dict
    @param meta_knobs: A dictionary containing all the custom String_Knobs
    that should be added to the node. The dictionary key will be the name of
    the knob and the dictionary's key value will be the value of the knob.

    @rtype: bool
    @returns: The Result

    """
    for key in meta_knobs.keys():
        if not node.knobs().has_key(key):
            if add_knobs:
                if isinstance(meta_knobs[key], str):
                    tmp_knob = nuke.String_Knob(key)
                elif isinstance(meta_knobs[key], bool):
                    tmp_knob = nuke.Boolean_Knob(key)
                elif isinstance(meta_knobs[key], int):
                    tmp_knob = nuke.Int_Knob(key)
                elif isinstance(meta_knobs[key], float):
                    tmp_knob = nuke.Double_Knob(key)
                node.addKnob(tmp_knob)
                node[key].setValue(meta_knobs[key])
            continue
        node[key].setValue(meta_knobs[key])

    return True


# Of the nodes that match the given node type, return the node with the
# corresponding name. "nodeName" is a regular expression
def get_node_of_type(node_name, node_type):
    all_nodes = nuke.allNodes(node_type)
    listNodes = [node for node in all_nodes
            if re.match(node_name, node.name())]
    if len(listNodes) > 0:
        return listNodes[0]
    else:
        return None

def is_node_type(node, node_type):
    """
    Checks if the given node matches the specified type.
    :param node: The provided Nuke node
    :type node: nuke.Node
    :param node_type: The name of the node type to check
    :type node_type: str
    """
    node_name = node.name()
    is_type = bool(get_node_of_type(node_name, node_type))
    return is_type
    
def update_full_frame_range(nodes=None, first_frame=None, last_frame=None):
    """
    Grabs the full frame range and applies it to the node.

    @type nodes: list
    @param nodes: List of nodes you want to work on.
    @type first_frame: float
    @param first_frame: The frame you want the node to start on.
    @type last_frame: float
    @param last_frame: The frame you want the node to end on.

    @rtype: bool
    @returns: The Result

    """
    result = False
    if not nodes:
        nodes = get_selected_nodes(['Read', 'DeepRead'])
    if not nodes:
        nodes = get_all_nodes(['Read', 'DeepRead'])
    if not isinstance(nodes, list):
        nodes = [nodes]
    if nodes:
        for node in nodes:
            file_value = node['file'].value()

            if not file_value:
                continue

            pipe_context = get_pipe_context()
            frame_range = pipe_context.shot.get_frame_range()

            if not first_frame:
                first_frame = frame_range.start

            if not last_frame:
                last_frame = frame_range.end

            path = re.sub('\.\d+\.', '.%04d.', file_value)

            knobs = {'file':path, 'first':int(first_frame), 'last':int(last_frame)}
            set_knobs(node, knobs)
            result = True

    return result

def update_custom_frame_range(nodes=None):
    """
    Grabs the frame range, but allows the user to override it.

    @type nodes: list
    @param nodes: List of nodes you want to work on.

    @rtype: bool
    @returns: The Result

    """
    result = False

    if not nodes:
        nodes = get_selected_nodes(['Read', 'DeepRead'])
    if not nodes:
        nodes = get_all_nodes(['Read', 'DeepRead'])
    if not isinstance(nodes, list):
        nodes = [nodes]

    if nodes:
        for node in nodes:
            path = node.knob('file').value()
            if not path:
                continue
            first_frame = 1
            last_frame = 1

            # extract a path context from the file path of the node
            #
            response = formula_extract('sh_dir', path)
            if not response:
                continue
            path_context = response.payload
            pipe_context = PipeContext.from_path_context(path_ctx)
            frame_range = pipe_context.shot.get_frame_range()
            first_frame = frame_range.start
            last_frame = frame_range.end
            if first_frame != 1 or last_frame != 1:
                break

        range_panel = nuke.Panel('Custom frame range')
        range_panel.setWidth(300)
        range_panel.addSingleLineInput('First', first_frame)
        range_panel.addSingleLineInput('Last', last_frame)
        prompt = range_panel.show()

    if prompt:
        first_frame = range_panel.value('First')
        last_frame = range_panel.value('Last')
        for node in nodes:
            path = node.knob('file').value()
            path = re.sub('\.\d+\.', '.%04d.', path)
            knobs = {'file':path, 'first':int(first_frame), 'last':int(last_frame)}
            set_knobs(node, knobs)
            result = True

    return result

def get_available_name(name, number=None):
    """
    Find the name available for the given name.

    @type name: str
    @param name: The name you want to get a usable variance of.
    @type name: int
    @param name: The number to use when starting the function.

    @rtype: str
    @returns: The first available name.

    """
    nodes = get_selected_nodes('Group')
    if not nodes:
        nodes = get_all_nodes('Group')
    if not number:
        number = 0
    tmp_name = name
    if number:
        tmp_name = '%s%d'%(name, number)
    tmp = nuke.toNode(tmp_name)
    if not tmp:
        for group in nodes:
            with group:
                tmp = nuke.toNode(tmp_name)
            if tmp:
                number += 1
                tmp_name = get_available_name(name, number)
    else:
        number += 1
        tmp_name = get_available_name(name, number)

    return tmp_name

def create_read_from_write(nodes=None):
    """
    Create a read node that points at the selected write nodes' path.

    @type nodes: list
    @param nodes: The nodes you wish to read nodes for.

    @rtype: bool
    @returns: The Result

    """
    result = False

    root = nuke.toNode('root')
    first_frame = int(root['first_frame'].value())
    last_frame = int(root['last_frame'].value())
    reads = []

    if not nodes:
        nodes = get_selected_nodes('Write')
    for node in nodes:
        name = node['name'].value()
        node_name = get_available_name('%s_WriteRead' % (name))
        path = node['file'].value()
        if node.knob('namespace'):
            namespace = node['namespace'].value()
            path = re.sub('\[value\ this\.namespace\]', namespace, path, count=1)
        xpos = node['xpos'].value() + 100
        ypos = node['ypos'].value()
        read = create_node('Read', file=path, name=node_name, first=first_frame, last=last_frame,
                xpos=xpos, ypos=ypos, raw=False, colorspace=1)
        reads.append(read)

    if reads:
        result=True

    return result

def create_rfx_read(render_obj_version=None, render_obj=None,
        hidden_knobs=None, **knobs):
    if render_obj_version is None and render_obj is None:
        raise Exception('render_obj_version or render_obj must be specified.')
    elif render_obj_version is not None:
        render_obj = render_obj_version.parent()
    elif render_obj is not None:
        render_obj_version = render_obj.versions.get_last()

    pipe_context = WipContext.from_pipe_obj(render_obj.parent)
    pipe_obj = pipe_context.get_pipe_obj()

    # create read node
    #
    knobs.setdefault('name', 'rfxRead')
    knobs['raw'] = True
    knobs['first'] = pipe_obj.frame_range.start
    knobs['last'] = pipe_obj.frame_range.end
    knobs['format'] = str(script_utils.Format.RENDER)
    knobs['proxy_format'] = str(script_utils.Format.RENDER)
    read_node = create_node('Read', **knobs)

    # tag the node as an rfx node and add some knobs to control the image path
    #
    add_rfx_tab(read_node)
    version_knob = nuke.Int_Knob('render_version', 'render version')
    version_knob.setValue(render_obj_version.number)
    read_node.addKnob(version_knob)

    wip_knob = nuke.String_Knob('render_wip', 'render wip')
    wip_knob.setValue(render_obj.parent.name)
    read_node.addKnob(wip_knob)

    namespace_knob = nuke.String_Knob('render_namespace', 'render namespace')
    namespace_knob.setValue(render_obj.namespace)
    read_node.addKnob(namespace_knob)

    slice_knob = nuke.String_Knob('render_slice', 'render slice')
    read_node.addKnob(slice_knob)

    # get the padding that should be applied
    # to the frame and version variables
    #
    formula = FORMULA_MANAGER.get_formula('sh_wip_output_file')
    base_vars = formula.get_base_vars()
    frame_padding = 4
    version_padding = 3
    for var in base_vars:
        if var == 'frame':
            frame_padding = var.padding
        elif var == 'version':
            version_padding = var.padding

    # get a path context that will pull all of
    # it's variables from env and knob values
    #
    path_context = render_obj_version.get_path_context()
    path_context.work_root = '[getenv RENDER_ROOT]'
    path_context.proj_name = '[getenv PROJ_NAME]'
    path_context.seq_name = '[getenv SEQ_NAME]'
    path_context.shot_name = '[getenv SHOT_NAME]'
    path_context.wip_name = '[value render_wip]'
    path_context.namespace = '[value render_namespace]'
    path_context.version = (
            '[format %%0%dd [value render_version]' % version_padding)
    if render_obj_version.is_sliced:
        path_context.slice = '[value render_slice]'
    if render_obj_version.is_sequence:
        path_context.frame = '%%0%dd' % frame_padding

    # set the file knob for the read node
    #
    path = path_context.get_path('sh_wip_output_file')
    read_node['file'].setValue(path)

    # hide knobs
    #
    hidden_knobs = list_utils.to_list(hidden_knobs)
    hidden_knobs.extend(['file', 'format', 'proxy', 'proxy_format',
            'first', 'last', 'colorspace', 'premultiplied', 'raw'])
    for knob in hidden_knobs:
        read_node[knob].setVisible(False)

    return read_node

def get_comp_version(*args, **kwargs):
    file_name = nuke.root().name()
    status = formula_extract('sh_wip_file', file_name)
    version = 1
    if status:
        payload = status.payload
        version = int(payload['version'])
    else:
        version = os.environ['WIP_VERSION']

    return version


def create_shot_write(*args, **kwargs):
    namespace = kwargs.get('namespace', 'shot')
    context = kwargs.get('pipe_context')
    if not context:
        context = get_pipe_context()

    writes = get_all_nodes(filters='Write', active=True)
    if namespace == 'shot':
        knob_name = 'is_rfx'
    elif namespace == 'precomp':
        knob_name = 'is_rfx_precomp'
    is_shot_write = lambda n: True if knob_name in n.knobs() and \
                                      n[knob_name].value() else False 
    shot_writes = filter(is_shot_write, writes)
    pipe_obj = context.get_pipe_obj()
    ext = pipe_obj.cinema.comp_format.extension
    if not shot_writes:

        version = get_comp_version()
        if kwargs.has_key('version'):
            version = int(kwargs.get('version'))

        wip = context.get_wip_obj()

        wcontext = wip.get_path_context()
        # NOTE: Switching this out with a new path
        # out_path = wcontext.get_path('sh_comp_output_file', version=version, eye='%v', ext=ext)
        out_path = wcontext.get_path('sh_comp_wip_output_file',
                                     version=version, eye='%v',
                                     ext=ext,
                                     namespace='[value this.namespace]')

        image_dir = wcontext.get_path('sh_image_disc_dir')
        file_system.safe_make_dir(image_dir, make_all=True)

        knob_kwargs = {}
        #-- Set creation kwargs.  These knobs will get set on the write node when
        #-- it is created.
        if namespace == 'shot':
            knob_kwargs['name'] = 'rfxWrite'
        elif namespace == 'precomp':
            knob_kwargs['name'] = 'rfxPrecompWrite'
        knob_kwargs['colorspace'] = str(pipe_obj.cinema.comp_colorspace)
        knob_kwargs['file_type'] = str(pipe_obj.cinema.comp_format.extension)
        if knob_kwargs['file_type'] == 'exr':
            knob_kwargs['autocrop'] = True

        knob_kwargs['xpos'] = 0
        knob_kwargs['ypos'] = 0
        knob_kwargs['channels'] = 'rgb'
        custom_knobs = {knob_name : True}
        if pipe_obj.cinema.comp_format.bit_depth is not None:
            knob_kwargs['datatype'] = pipe_obj.cinema.comp_format.bit_depth

        knob_kwargs['file'] = out_path
        knob_kwargs['proxy'] = out_path

        # create the node
        #
        write_node = create_node('Write', **knob_kwargs)

        namespace_knob = nuke.String_Knob('namespace')
        namespace_knob.setValue(namespace)
        write_node.addKnob(namespace_knob)

        is_rfx = nuke.Boolean_Knob(knob_name)
        is_rfx.setValue(True)
        write_node.addKnob(is_rfx)

        knob_kwargs = {}
        knob_kwargs['xpos'] = write_node['xpos'].getValue()
        knob_kwargs['ypos'] = write_node['ypos'].getValue() - 100
        #knob_kwargs['format'] = '{0}_comp'.format(PROJ_NAME)
        if PROJ_NAME == 'MINION':
            minion_node = create_node('MINION_Res', **knob_kwargs)
            write_node.setInput(0, minion_node)
        else:
            knob_kwargs['format'] = 'RFX_RENDER'
            reformat_node = create_node('Reformat', **knob_kwargs)
            write_node.setInput(0, reformat_node)
        

    else:
        write_node = shot_writes[0]

    if write_node:
        center_on_screen(write_node)

    return write_node

def center_on_screen(nodes):

    selection = clear_selection()

    for node in list_utils.to_list(nodes):
        node['selected'].setValue(True)

    nuke.zoomToFitSelected()

    clear_selection()

    for node in selection:
        node['selected'].setValue(True)

    return 0

def create_sequence_sheet(*args, **kwargs):
    context = kwargs.get('pipe_context')
    if not context:
        context = get_pipe_context()

    sequence_sheet = get_all_nodes(filters='rfxSequence_Sheet', active=True)
    sequence_sheets = [precomp for precomp in sequence_sheet if precomp.knobs().has_key('is_rfxSheet') and precomp['is_rfxSheet'].value()]

    sequence_for_sheet = context.get_sequence_obj()
    project_for_sheet = context.get_project_obj()

    if not sequence_sheets:

        knob_kwargs = {}
        #-- Set creation kwargs.  These knobs will get set on the write node when
        #-- it is created.
        knob_kwargs['name'] = 'rfxSequence_Sheet'
        knob_kwargs['xpos'] = 0
        knob_kwargs['ypos'] = 0
        knob_kwargs['file'] = ('/work/%s/sequences/%s/reference/%s_contact_sheet.nk' % (project_for_sheet.name , sequence_for_sheet.name, sequence_for_sheet.name))
        knob_kwargs['reading'] = True
        knob_kwargs['tile_color'] = 11993343
        knob_kwargs['on_error'] = 'black'
        custom_knobs = {'is_rfxSheet' : True}

        # create the node
        #
        # knob_kwargs.update(kwargs)
        sequence_sheet_node = create_node('Precomp', **knob_kwargs)

        is_rfx = nuke.Boolean_Knob('is_rfxSheet')
        is_rfx.setValue(True)
        sequence_sheet_node.addKnob(is_rfxSheet)

    else:
        sequence_sheet_node = sequence_sheets[0]

    return sequence_sheet_node

def create_backdrop(nodes=None, label=None, extra_height=300, extra_width=200, **kwargs):
    """
    Create a backdrop to encapsulate the passed in nodes.

    @type nodes: list
    @param nodes: The nodes to create a backdrop for.
    @type label: str
    @param label: The label to apply to the backdrop.
    @type extra_height: int
    @param extra_height: The additional height to apply to backdrop.
    @type extra_width: int
    @param extra_width: The additional width to apply to backdrop.

    @rtype: Node
    @returns: The backdrop created.

    """
    if not nodes:
        nodes = get_selected_nodes()

    if nodes:
        xy_poses = get_min_max(nodes)

        xpos = xy_poses[0][0] - (extra_width/2)
        ypos = xy_poses[1][0] - (extra_height/2) - extra_height/2

        bdwidth = (xy_poses[0][1] - xy_poses[0][0]) + extra_width
        bdheight = (xy_poses[1][1] - xy_poses[1][0]) + extra_height + (extra_height/2)

        node = create_node('BackdropNode', label=label, note_font_size=48,
                xpos=float(xpos), ypos=float(ypos), bdwidth=float(bdwidth),
                bdheight=float(bdheight), **kwargs)

    return node

def stereo_switch():
    """
    Switch the eye denoter in paths to %v.

    @rtype: bool
    @returns: The Result

    """
    result = False

    nodes = get_selected_nodes(filters=None)
    reads = filter_nodes(nodes, filters=['Read', 'DeepRead'])
    hou = filter_nodes(nodes, filters='rfxReadSequence')

    if reads:
        for node in reads:
            filename = node['file'].getValue()
            if re.findall('[\._/][lr][\./]', filename):
                filename = re.sub('([\._/])[lr]([\./])', r'\1%v\2', filename)
            node['file'].setValue(filename)
        result = True

    if hou:
        for node in hou:
            filename = node['file'].getValue()
            if re.findall('[\._/][lr][\./]', filename):
                filename = re.sub('([\._/])[lr]([\./])', r'\1%v\2', filename)
            node['file'].setValue(filename)
        result = True

    return result

def incept_this(node, nodes=None):
    """
    Take the given node and trace it's dependencies, We need to go deeper!

    @type node: Node
    @param node: The node to incept.
    @type node: Nodes
    @param node: The nodes we're filtering with.

    @rtype: list
    @returns: The dependencies

    """
    dependent = []
    tmp_dependent = node.dependent()
    if tmp_dependent:
        for tmp in tmp_dependent:
            if nodes:
                if tmp in nodes:
                    dependent.append(tmp)
                    children = incept_this(tmp, nodes)
                    if children:
                        dependent.append(children)
                continue
            dependent.append(tmp)
            children = incept_this(tmp, nodes)
            if children:
                dependent.append(children)

    return dependent

# def refresh_formats(half_res=False):
#     """
#     #Goes through the rfx nodes/root and updates their formats.

#     #@rtype: bool
#     #@returns: The Result

#     """
#     comp_format = None
#     default_format = None

#     #department, project, seq, shot, version = script_utils.Nuke_Utils().get_root_knobs()

#     nuke_formats = nuke.formats()
#     comp_format_name = 'RFX_COMP'
#     default_format_name = 'RFX_RENDER'
#     if half_res:

#         comp_width, comp_height, comp_aspect, comp_pixel_aspect, comp_overscan = script_utils.get_resolution(res_type='half_comp_res', seq=seq, shot=shot)
#         #default_width, default_height, default_aspect, default_pixel_aspect, default_overscan = script_utils.Nuke_Utils().get_resolution(res_type='half_res', seq=seq, shot=shot)
#     #else:
#         #comp_width, comp_height, comp_aspect, comp_pixel_aspect, comp_overscan = script_utils.Nuke_Utils().get_resolution(res_type='comp', seq=seq, shot=shot)
#         #default_width, default_height, default_aspect, default_pixel_aspect, default_overscan = script_utils.Nuke_Utils().get_resolution(res_type='default', seq=seq, shot=shot)

#     #for tmp_format in nuke_formats:
#         #name = tmp_format.name()
#         #if comp_format_name == name:
#             #comp_format = tmp_format
#             #continue
#         #if default_format_name == name:
#             #default_format = tmp_format
#             #continue
#     #if not comp_format:
#         #comp_format = nuke.addFormat('%s %s %s %s' % (comp_width, comp_height, comp_pixel_aspect, comp_format_name))
#     #else:
#         #if not comp_format.width() == comp_width:
#             #comp_format.setWidth(int(comp_width))
#         #if not comp_format.height() == comp_height:
#             #comp_format.setHeight(int(comp_height))
#         #if not comp_format.pixelAspect() == comp_pixel_aspect:
#             #comp_format.setPixelAspect(float(comp_pixel_aspect))

#     #if not default_format:
#         #default_format = nuke.addFormat('%s %s %s %s' % (default_width, default_height, default_pixel_aspect, default_format_name))
#     #else:
#         #if not default_format.width() == default_width:
#             #default_format.setWidth(int(default_width))
#         #if not default_format.height() == default_height:
#             #default_format.setHeight(int(default_height))
#         #if not default_format.pixelAspect() == default_pixel_aspect:
#             #default_format.setPixelAspect(int(default_pixel_aspect))

#     #orig_nodes = clear_selection()
#     #nodes = get_rfx()
#     #if nodes:
#         #for node in nodes:
#             #if node.knobs().has_key('format'):
#                 #node['format'].setValue(default_format)
#     #root = nuke.toNode('root')
#     #root['format'].setValue(comp_format)
#     #add_to_selection(orig_nodes)

#     #sys.stderr.write('Finished: Refresh Formats\n')

#     #return True

def refresh_write_paths(*args, **kwargs):
    context = kwargs.get('pipe_context')
    if not context:
        context = get_pipe_context()

    wip = context.get_wip_obj()

    if wip is None:
        sys.stderr.write('Not in a WIP Context! Couldn\'t refresh write paths.')
        return

    version = get_comp_version()

    writes = get_all_nodes(filters='Write', active=True)
    pipe_obj = context.get_pipe_obj()
    ext = pipe_obj.cinema.comp_format.extension
    shot_writes = [write for write in writes if write.knobs().has_key('is_rfx') and write['is_rfx'].value()]
    for write in shot_writes:
        wcontext = wip.get_path_context()

        # NOTE: Switching this out with a new path
        # out_path = wcontext.get_path('sh_comp_output_file', version=version, eye='%v', ext=ext)
        out_path = wcontext.get_path('sh_comp_wip_output_file',
                                     version=version, eye='%v', ext=ext,
                                     namespace='[value this.namespace]')

        write['file'].setValue(out_path)
        write['proxy'].setValue(out_path)

    sys.stderr.write('Finished: Refresh Write Paths\n')

    return shot_writes

def refresh_writes():
    pipe_ = get_pipe_context()
    config_obj = pipe_.get_pipe_obj().cinema

    orig_nodes = clear_selection()

    writes = get_all_nodes(filters='Write', active=True)
    shot_writes = [write for write in writes if write.knobs().has_key('is_rfx') and write['is_rfx'].value()]

    for write in writes:
        write_knobs = {}

        format = config_obj.comp_format
        if write.knobs().has_key('precomp') and write['precomp'].value():
            format = config_obj.render_format
        write_knobs['file_type'] = format.extension

        if format.bit_depth is not None:
            write_knobs['datatype'] = format.bit_depth

        if write_knobs['file_type'] in ['dpx', 'tif']:
            frame_rate = int(round(config_obj.frame_rate.fps))
            timecode = (
                    '[format %%02d [expr [frame] / ({frame_rate} * 60 * 60)]]'
                    '[format %%02d [expr [frame] / ({frame_rate}*60)]]'
                    '[format %%02d [expr [frame] / {frame_rate}]]'
                    '[format %%02d [expr [frame] %% {frame_rate}]]')
            write_knobs['timecode'] = timecode.format(frame_rate=frame_rate)

        #if config_obj.stereo:
        #    write_knobs['views'] = 'left right'

        set_knobs(write, write_knobs)

    add_to_selection(orig_nodes)

    print 'Finished: Refresh Writes'
    return (len(writes) > 0)

# TODO: port this
#def refresh_read_paths():
    #"""
    #Loop through the rfx read nodes and refresh their paths.

    #@rtype: bool
    #@returns: The Result

    #"""
    #result = False

    #department, project, seq, shot, version = script_utils.Nuke_Utils().get_root_knobs()

    #pipe = pipeline.Pipeline(project)

    #maya_file = '%s_%s_lit' % (seq, shot)
    #is_stereo = rfxUtils.get_project_stereoscopic(project_path, seq, shot)
    #render_extension = rfxUtils.get_project_render_format(project_path, seq, shot)

    #stereo_addition = ''
    #if is_stereo:
        #stereo_addition = '%v/'

    #nodes = get_rfx()
    #nodes = filter_nodes(filters=['Read', 'DeepRead'], nodes=nodes)
    #if nodes:
        #for node in nodes:
            #render_layer_dir = rfxGetPath.rfxGetPath(['RenderLayerDirNew',
                #project_path, seq, shot, maya_file, rlc, layername, tmp_pass])
            #data = get_knobs(node, 'rlcname', 'layername', 'passtype', 'aovpass')
            #rlcname = data['rlcname']
            #layername = data['layername']
            #passtype = data['passtype']
            #aovpass = data['aovpass']
            #if passtype == 'beauty' and aovpass:
                #passtype = aovpass
            #if passtype == 'deepOpacity':
                #render_extension = 'dshd'
            #render_layer_dir = pipe.render_layer_dir_new(seq, shot, maya_file, rlc,
                    #layername, passtype)
            #filename = '%s/live/%s%s_%s.%%04d.%s' % (render_layer_dir, stereo_addition,
                    #layername, passtype, render_extension)
            #set_knobs(node, {'file':filename})

        #result = True

    #return result

def reload_reads(nodes=None):
    result = False

    nodes = nodes if nodes else node_query(filters=['Read', 'DeepRead'], active=True)
    if nodes:
        for node in nodes:
            node['reload'].execute()

        result = True

    return result


def color_nodes(nodes=None, color=0):
    result = False

    if not nodes:
        nodes = get_rfx()
    if not isinstance(nodes, list):
        nodes = [nodes]

    if nodes:
        for node in nodes:
            node['tile_color'].setValue(int(color))
        result = True

    return result


# Given a color value in the range of 0-1, will return a string representing
# the 8-bit version of the value in binary.
def get_color_value(color_value):
    if not isinstance(color_value, (float, int)):
        return Failure(message='The color value must be an float or int.')
    elif color_value < 0 or color_value > 1:
        return Failure(message='Provided color value must be in the range '
                               '0-1.')
    else:
        value = int(color_value * 255)
        return bin(value)[2:].zfill(8)


def get_tile_color(red, green, blue, alpha=1):
    red_value = get_color_value(red)
    if isinstance(red_value, Failure):
        IO.error(red_value.message)
        return
    green_value = get_color_value(green)
    if isinstance(green_value, Failure):
        IO.error(red_value.message)
        return
    blue_value = get_color_value(blue)
    if isinstance(blue_value, Failure):
        IO.error(red_value.message)
        return
    alpha_value = get_color_value(alpha)
    if isinstance(alpha_value, Failure):
        IO.error(red_value.message)
        return
    return int('{0}{1}{2}{3}'.format(red_value, green_value, blue_value,
                                      alpha_value), 2)


def shuffle_channels(nodes=None, return_shuffles=False):
    shuffle_nodes = []
    if not nodes:
        nodes = []
        nodes.extend(get_selected_nodes('Read'))
        nodes.extend(get_selected_nodes('rfxReadSequence'))
    x, y = get_min_max()
    if nodes:
        for node in nodes:
            all_shuffles = []

            # Get our starting point
            x, y_throwaway = get_min_max()
            # Starting x should be max(x) + 20
            starting_x = x[1] + 300
            # We'll use the mininimum Y position of any node
            # and move the rest of the nodes down 75 pixels
            ypos = y[0]
            channel_ypos = ypos + 100

            node_name = node['name'].value()

            channels = node.channels()
            channels = [tmp for tmp in channels if not re.match('^rgba\.\w+', tmp)]
            condensed_channels = defaultdict(list)
            for channel in channels:
                name_split = channel.split('.')
                condensed_channels[name_split[0]].append(name_split[1])

            uniq_channels = len(condensed_channels.keys()) - 1

            for key in condensed_channels.keys():
                if len(condensed_channels[key]) >= 3 and len(condensed_channels[key]) <=4:
                    shuffle = create_node('Shuffle',
                            name = '%s_%s_shuffle' % (node_name, key),
                            # custom_knobs=custom_knobs,
                            ypos=channel_ypos,
                            xpos=starting_x)
                    starting_x += 150
                    shuffle['postage_stamp'].setValue(True)
                    shuffle['in2'].setValue('alpha')
                    shuffle['alpha'].setValue('red2')
                    shuffle.connectInput(0, node)
                    shuffle['in'].setValue(key)
                    all_shuffles.append(shuffle)

            shuffle_x, shuffle_y = get_min_max(all_shuffles)
            middle = shuffle_x[0] + ((shuffle_x[1] - shuffle_x[0])/2)
            node['xpos'].setValue(middle)
            node['ypos'].setValue(ypos)

            # x, y = get_min_max()
            # tmp_xpos = node['xpos'].value()
            # offset = tmp_xpos - x[0]
            # final_xpos = offset + 100 + x[1]
            # node['xpos'].setValue(final_xpos)

            shuffle_nodes.append(all_shuffles)
            create_backdrop(nodes=all_shuffles, label='%s_shuffled' % (node_name), extra_height=150)

    if return_shuffles:
        shuffle_list = []
        for each in shuffle_nodes:
            for s in each:
                shuffle_list.append(s)
        return shuffle_list
    return nodes

# TODO: port this
#def substitute_knobs():
    #result = False

    #d_channel_knobs = ['ChannelMask_Knob', 'Channel_Knob']

    #nodes = get_selected_nodes()
    #if nodes:
        #knob_list = []
        #for node in nodes:
            #for knob in node.knobs().keys():
                #if isinstance(node[knob], nuke.String_Knob):
                    #if not knob in knob_list:
                        #knob_list.append(knob)

        #prompt = nuke_gui.Substitute(knob_list)
        #prompt.centerWidget()
        #prompt.exec_()

        #knobs = prompt.knobs
        #search = prompt.search
        #replace = prompt.replace

        #for node in nodes:
            #for knob in knobs:
                #if node.knobs().has_key(knob):
                    #tmp = node[knob].value()
                    #sub = re.sub(search, replace, tmp)
                    #node[knob].setValue(sub)

    #return 0

def autoplace_nodes(nodes):
    for node in nodes:
        if isinstance(node, RNukeNode):
            node = node.get_node()
        nuke.autoplace(node)

def get_leaf_nodes(nodes):
    leaf_nodes = []
    ascendents = get_ascendents(nodes, inverse=True)
    for ascendent in ascendents:
        depend_nodes = ascendent.dependencies()
        if depend_nodes:
            continue
        leaf_nodes.append(ascendent)

    return leaf_nodes


def get_ascendents(nodes=None, previous=None, filters=None, inverse=False, inputs=None):
    nodes = list_utils.to_list(nodes)
    previous = list_utils.to_list(previous)
    filters = list_utils.to_list(filters)
    inputs = list_utils.to_list(inputs)

    new_nodes = []
    for node in nodes:
        if node in previous:
            continue
        previous.append(node)
        new_nodes.append(node)

        if inputs:
            depend_nodes = []
            for index in inputs:
                depend_node = node.input(index)
                if depend_node:
                    depend_nodes.append(depend_node)

        else:
            depend_nodes = node.dependencies()

        new_nodes.extend(get_ascendents(nodes=depend_nodes,
                                        previous=previous,
                                        filters=filters,
                                        inverse=inverse))

    if filters:
        new_nodes = filter_nodes(new_nodes, filters=filters, inverse=inverse)

    return new_nodes

def find_used_reads():
    writes = get_all_nodes(['Write'])
    used_reads = list(set(get_ascendents(nodes=writes,
                                         filters=['Read', 'DeepRead'])))
    used_data = {}
    for read in used_reads:
        used_data[read['name'].value()] = get_knobs(
            read, 'aovpass', 'layername', 'rlcname', 'passtype', 'file')
        used_data[read['name'].value()]['class'] = read.Class()

    return used_data

def find_unused_reads():
    used_data = find_used_reads()

    all_reads = get_all_nodes(['Read', 'DeepRead'])
    all_data = {}
    for read in all_reads:
        all_data[read['name'].value()] = get_knobs(
            read, 'aovpass', 'layername', 'rlcname', 'passtype', 'file')

    unused_aovs = {}

    for name in all_data.keys():
        data = all_data.get(name)
        if name in used_data.keys():
            continue
        elif not data.get('aovpass'):
            continue

        matched = False
        for key, used in used_data.iteritems():
            if data == used:
                matched = True

        if not matched:
            unused_aovs[name] = used

    return unused_aovs

def djv_this(node, start, end, incr, view):

    if not os.access(DJV_PATH, os.X_OK):
        raise RuntimeError('DJV cannot be executed (%s).' % (DJV_PATH,))

    filename = nuke.filename(node)
    if filename is None or filename == "":
        raise RuntimeError('DJV cannot be executed on "%s", expected to find a filename and there was none.' % (node.fullName(),))

    sequence_interval = '%04d-%04d' % (start, end)

    (filename, subs) = re.subn('(%[0-9]+)d', sequence_interval, filename)

    ## This is a test to see if the regex worked.  If it did not, subs will be 0 and we will set the filename to .#.
    if subs == 0:
        (filename, subs) = re.subn('(%[0-9]+)d', '#', filename)

    ## Normalize paths in case we ever go back into windows
    os.path.normpath(filename)
    os.path.normpath(DJV_PATH)

    args = []
    args.append(DJV_PATH)
    args.append(filename)

    nuke.IrToken()
    os.spawnv(os.P_NOWAITO, DJV_PATH, args)

def exrcycler_this(node, start, end, incr, view):

    if not os.access(EXRCYCLER_PATH, os.X_OK):
        raise RuntimeError('exrcycler cannot be executed (%s).' % (EXRCYCLER_PATH))

    filename = nuke.filename(node)
    if filename is None or filename == "":
        raise RuntimeError('exrcycler cannot be executed on "%s", expected to find a filename and there was none.' % (node.fullName(),))

    os.path.normpath(filename)
    os.path.normpath(EXRCYCLER_PATH)

    args = []
    args.append(EXRCYCLER_PATH)
    args.append(filename)
    if start and end:
        args.append(str(start))
        args.append(str(end))

    nuke.IrToken()
    os.spawnv(os.P_NOWAITO, EXRCYCLER_PATH, args)

def rv_this(node, start, end, incr, views):
    available_colorspaces = ['rec709', 'sRGB']
    stereo=False

    pcontext = get_pipe_context()
    shot = pcontext.get_shot_obj()
    out_colorspace = str(shot.cinema.comp_colorspace)

    filename = nuke.selectedNode()['file'].value()

    if filename is None or filename == "":
        raise RuntimeError('RV cannot be executed on "%s", expected to find a filename and there was none.' % (node.fullName()))

    if '%v' in filename:
        stereo = True
        left_filename = filename.replace('%v', 'l')
        right_filename = filename.replace('%v', 'r')

    frame_range = '%04d-%04d' % (start, end)

    args = []
    args.append(RV_PATH)
    if stereo:
        args.append('[')
        if 'right' in views:
            args.append(right_filename)
            args.append(frame_range)
        if 'left' in views:
            args.append(left_filename)
            args.append(frame_range)
        args.append(']')
        if len(views) == 2:
            args.append('-stereo')
            args.append('mirror')
    else:
        args.append(filename)
        args.append(frame_range)

    if out_colorspace in available_colorspaces:
        pass
    args.append('-ns')
    args.append('-play')
    args.append('-c')

    subprocess.Popen(args)

def load_live_frames(nodes=None):
    result = False

    if not nodes:
        nodes = get_selected_nodes(filters=['Read', 'DeepRead'])

    nodes = list_utils.to_list(nodes)

    for node in nodes:
        path = node['file'].value()
        if re.search('(/)v\d{4}(/)', path) or re.search('(/)live(/)', path):
            path = re.sub('(/)v\d{4}(/)', r'\1live\2', path)
            path = re.sub('\.\d{4}\.', r'.%04d.', path)
            if not os.path.exists(os.path.dirname(path).strip('%v')):
                sys.stderr.write('The path %s does not exist!!\n' % (path))
                continue
            node['file'].setValue(path)
            node['tile_color'].setValue(0xFFFFFFAA)

        result = True

    return result

def load_latest_frames(nodes=None):
    """
    This function finds the latest directory based on the version number
    Compare to load_newest_frames()
    """
    result = False

    if not nodes:
        nodes = get_selected_nodes(filters=['Read', 'DeepRead'])

    nodes = list_utils.to_list(nodes)

    for node in nodes:
        path = node['file'].value()
        if re.search(r'/v\d{4}/|/live/', path):
            versions = []
            tmp_dir = os.path.dirname(path)
            if re.search(r'/r/|/l/|/%v/', path):
                tmp_dir = os.path.abspath(os.path.join(tmp_dir, '../..'))
            else:
                tmp_dir = os.path.abspath(os.path.join(tmp_dir, '..'))
            glob_dir = os.path.join(tmp_dir, '*')
            glob_result = glob.glob(glob_dir)
            for tmp in glob_result:
                tmp = os.path.basename(tmp)
                if re.search('v\d{4}', tmp):
                    versions.append(tmp)

            if versions:
                versions.sort()
                path = re.sub(r'/v\d{4}/|/live/', '/%s/' % (versions[-1]), path)
                node['file'].setValue(path)
                node['tile_color'].setValue(0xff0000ff)

        result = True

    return result

def load_newest_frames(nodes=None):
    """
    This function finds the latest directory based on the modified time
    Compare to load_latest_frames()
    """
    result = False

    if not nodes:
        nodes = get_selected_nodes(filters=['Read', 'DeepRead'])

    nodes = list_utils.to_list(nodes)

    for node in nodes:
        path = node['file'].value()
        file_name = os.path.basename(path)
        ext = os.path.splitext(file_name)[-1]
        if re.search(r'/v\d{4}/|/live/', path):
            versions = []
            tmp_dir = os.path.dirname(path)
            if re.search(r'/r/|/l/|/%v/', path):
                tmp_dir = os.path.abspath(os.path.join(tmp_dir, '../..'))
            else:
                tmp_dir = os.path.abspath(os.path.join(tmp_dir, '..'))
            glob_dir = os.path.join(tmp_dir, '*')
            glob_result = glob.glob(glob_dir)
            if not glob_result:
                continue

            newest_dir = None
            for tmp in glob_result:
                if not newest_dir:
                    if glob.glob(os.path.join(tmp, '*{0}'.format(ext))):
                        newest_dir = tmp

                elif os.path.getmtime(tmp) > os.path.getmtime(newest_dir):
                    if glob.glob(os.path.join(tmp, '*{0}'.format(ext))):
                        newest_dir = tmp
            if not newest_dir:
                continue

            newest_path = os.path.join(newest_dir, file_name)
            node['file'].setValue(newest_path)
            node['tile_color'].setValue(0xff0000ff)

        result = True

    return result

def load_archive_frames(nodes=None):
    result = False

    if not nodes:
        nodes = get_selected_nodes(filters=['Read', 'DeepRead'])

    nodes = list_utils.to_list(nodes)
    if nodes:
        for node in nodes:
            is_live = False
            path = node['file'].value()
            if re.search(r'/live/', path):
                is_live = True
            if re.search(r'/v\d{4}/|/live/', path):
                tmp_dir = os.path.dirname(path)
                version = re.search('/v(\d{4})', os.path.realpath(tmp_dir))
                if version:
                    version = version.group(1)
                    old_version = int(version) - 1
                    if old_version < 1:
                        old_version = 1
                    path = check_version(path, old_version, is_live)
                    if path:
                        node['file'].setValue(path)
                        node['tile_color'].setValue(
                                0xff0000ff)
                        result = True
                else:
                    sys.stderr.write('Does not have a version number or '
                            'live path\n')

    return result

def align_horizontally(nodes):

    nodes = list_utils.to_list(nodes if nodes else nuke.selectedNodes())
    align_nodes(nodes, axis='y')

def align_vertically(nodes):

    nodes = list_utils.to_list(nodes if nodes else nuke.selectedNodes())
    align_nodes(nodes, axis='x')

def align_nodes(nodes, axis):

    nodes = list_utils.to_list(nodes if nodes else nuke.selectedNodes())
    axis = (axis if axis else 'x')
    attr = AXIS_LUT.get(axis)
    if attr:
        value = 0
        for node in nodes:
            value += node[attr].value()

        value = value/len(nodes)

        for node in nodes:
            node[attr].setValue(value)

def distribute_nodes(nodes=None, axis='x', spacing=None, minimum=5):

    nodes = list_utils.to_list(nodes if nodes else nuke.selectedNodes())
    attr = AXIS_LUT.get(axis)
    space_func = SPACE_LUT.get(axis)
    dimensions = get_dimensions(nodes)
    if attr and space_func:
        total_space = dimensions[axis]['max'] - dimensions[axis]['min']
        node_space = 0
        for node in nodes:
            node_space += eval('node.{0}()'.format(space_func))

        spacing = ((total_space - node_space)/len(nodes) if
                   spacing is None else spacing)
        spacing = spacing if spacing > minimum else minimum

        xpos = nodes[0][attr].value() + eval('nodes[0].{0}()'.format(space_func))
        for node in nodes[1:]:
            pos = node[attr].value()
            xpos = pos if xpos is None else xpos
            new_pos = xpos + spacing
            node[attr].setValue(new_pos)

            xpos = new_pos + eval('node.{0}()'.format(space_func))

def offset_nodes(nodes, axis, value):
    position_nodes(nodes, axis, value, absolute=False)

def offset_relative(nodes, axis, offset_value, to_nodes=None):

    axis = (axis if axis else 'x')
    from_x, from_y = get_min_max(nodes)
    to_x, to_y = get_min_max(to_nodes)

    if axis == 'x':
        position_value = to_x[1] - from_x[0]
    else:
        position_value = to_y[0] - from_y[0]

    position_nodes(nodes, axis, position_value, absolute=False)
    offset_nodes(nodes, axis, offset_value)

def position_nodes(nodes, axis, value, absolute=True):
    nodes = list_utils.to_list(nodes if nodes else nuke.selectedNodes())
    axis = (axis if axis else 'x')
    for node in nodes:
        attr = AXIS_LUT.get(axis)
        if attr:
            if not absolute:
                node[attr].setValue(node[attr].value() + value)
            else:
                node[attr].setValue(value)

def find_all_archive_nodes():
    clear_selection()
    nodes = get_all_nodes(filters=['Read', 'DeepRead'])
    archive_nodes = []
    for node in nodes:
        path = node.knob('file').value()
        if re.search('/v\d{4}/', path):
            archive_nodes.append(node)

    add_to_selection(archive_nodes)

    return archive_nodes

def show_all_archive_nodes():
    result = False
    nodes = find_all_archive_nodes()
    if nodes:
        for node in nodes:
            node.knob('tile_color').setValue(0xff0000ff)
            old_label = node.knob('label').value()
            new_label = old_label.split('\n')[0] + '\n' + 'ARCHIVE'
            node.knob('label').setValue(new_label)
        result = True

    return result

def check_version(path, version, live=False):
    result = None
    # We need to nullify the frame place holder so we can evaluate the version.
    path = re.sub('%04d', '%%04d', path)
    path = re.sub('%v', '%%v', path)
    if live:
        path = re.sub('/live/', '/v%04d/', path)
    else:
        path = re.sub('/v\d{4}/', '/v%04d/', path)

    sys.stderr.write('PATH: %s\n' % (path))
    path = path % (version)

    dirname = os.path.dirname(path)
    stripped_eye = re.sub('/[rl%v]+$', '', dirname)

    if not os.path.exists(stripped_eye):
        version -= 1
        if not version < 1:
            path = check_version(path, version, False)
        else:
            path = None

    return path

def create_camera_switch():
    node = nuke.nodes.rCameraSwitch()
    for i, tmp in enumerate(get_selected_nodes(filters='JoinViews')):
        node.setInput(i, tmp)

def select_channel():
    """
    Allows a lighting artist to easily select and set channel knobs on a node.

    @rtype: bool
    @returns: The result.

    """
    from nuke_tools.ui import select_channel
    result = False

    d_channel_knobs = ['ChannelMask_Knob', 'Channel_Knob']

    node = get_selected_nodes()
    if node:
        if len(node) > 1:
            sys.stderr.write('More than one node selected. Defaulting to first\n')
        node = node[0]
        channels = node.channels()
        childs = node.dependencies()
        for child in childs:
            channels.extend(child.channels())
        channels = list(set(channels))
        channel_knobs = []

        name = node['name'].value()
        knobs = node.knobs()
        knob_names = []
        for knob in knobs.keys():
            knob_class = node[knob].Class()
            knob_vis = node[knob].visible()
            knob_name = node[knob].name()
            if knob_class in d_channel_knobs and knob_vis and not knob_name in knob_names:
                knob_names.append(knob_name)
                channel_knobs.append(knob_name)

        title = 'Channel selection for %s' % (name)
        prompt = select_channel.ChannelBrowser(channel_knobs, channels, title)
        prompt.exec_()

        if prompt.left and prompt.right:
            sys.stderr.write('Setting { %s.%s } to { %s }\n' % (name, prompt.left, prompt.right))
            node[prompt.left].setVisible(True)
            node[prompt.left].setValue(prompt.right)
            result = True

    return result

def rename_file_node(node):
    if node.knobs().has_key('file'):
        knob = node.knob('file')
        value = knob.evaluate()
        if value and value.strip() and not ':' in value:
            basename = os.path.basename(value)

            filename = os.path.splitext(basename)[0]
            new_name = get_available_name(filename)

            node['name'].setValue(new_name)

class RNukeNodeGraphObject(object):

    def __init__(self, *args, **kwargs):
        if kwargs.has_key('root'):
            self.set_root(kwargs.get('root'))
        self._root = nuke.root()

    def get_root(self):
        return self._root

    def set_root(self, root):
        if isinstance(root, str) and nuke.toNode(root):
            self._root = nuke.toNode(root)
        elif isinstance(root, nuke.Node) and root.Class() in ['Root', 'Group']:
            self._root = root
        else:
            raise TypeError('Root given is of wrong type or does not exist <{0}>\n'.format(root))

    def get_position(self):

        return self.get_top_left()

    def get_bottom_right(self):
        xpos, ypos = self.get_top_left()
        width = self.get_width()
        height = self.get_height()

        xpos = xpos + width
        ypos = ypos - height

        return xpos, ypos

    def get_bottom_left(self):
        xpos, ypos = self.get_top_left()
        height = self.get_height()

        ypos = ypos - height

        return xpos, ypos

    def get_top_right(self):
        xpos, ypos = self.get_top_left()
        width = self.get_width()

        xpos = xpos + width

        return xpos, ypos

    def get_top_left(self):
        xpos = self.get_xpos()
        ypos = self.get_ypos()

        return xpos, ypos

    def get_center(self):
        position = self.get_position()
        width = abs(self.get_width()/2)
        height = abs(self.get_height()/2)

        return (position[0] + width, position[1] + height)

    def set_center(self, center):
        width = abs(self.get_width() / 2)
        height = abs(self.get_height() / 2)
        position = (center[0] - width, center[1] - height)
        self.set_position(position)

    def get_area(self):

        return self.get_width() * self.get_height()

    def get_xpos(self):
        dimensions = self.get_screen_space()

        return dimensions['x']['min']

    def get_ypos(self):
        dimensions = self.get_screen_space()

        return dimensions['y']['min']

    def get_width(self):
        dimensions = self.get_screen_space()

        width = dimensions['x']['max'] - dimensions['x']['min']

        return width

    def get_height(self):
        dimensions = self.get_screen_space()

        height = dimensions['y']['max'] - dimensions['y']['min']

        return height

    def snap_center(self, nodes, axis):
        if isinstance(nodes, (list, tuple)):
            nodes = RNukeNodeGraph(nodes=nodes)

        nodes_center = nodes.get_center()
        center = self.get_center()
        if axis == 'x':
            offset = nodes_center[0] - center[0]
            self.offset_x(offset)
        else:
            offset = nodes_center[1] - center[1]
            self.offset_y(offset)

    def snap_center_x(self, nodes):
        self.snap_center(nodes, axis='x')

    def snap_center_y(self, nodes):
        self.snap_center(nodes, axis='y')

    def snap_to(self, nodes):
        if isinstance(nodes, (list, tuple)):
            nodes = RNukeNodeGraph(nodes=nodes)

        position = nodes.get_position()
        self.set_position(position)

    def snap_top(self, nodes, additional=0):
        if isinstance(nodes, (list, tuple)):
            nodes = RNukeNodeGraph(nodes=nodes)

        node_dimensions = nodes.get_screen_space()
        dimensions = self.get_screen_space()

        position_y = node_dimensions['y']['min'] - dimensions['y']['max']

        self.offset_y(position_y - additional)

    def snap_bottom(self, nodes, additional=0):
        if isinstance(nodes, (list, tuple)):
            nodes = RNukeNodeGraph(nodes=nodes)

        node_dimensions = nodes.get_screen_space()
        dimensions = self.get_screen_space()

        position_y = node_dimensions['y']['max'] - dimensions['y']['min']

        self.offset_y(position_y + additional)

    def snap_left(self, nodes, additional=0):
        if isinstance(nodes, (list, tuple)):
            nodes = RNukeNodeGraph(nodes=nodes)

        node_dimensions = nodes.get_screen_space()
        dimensions = self.get_screen_space()

        position_x = node_dimensions['x']['min'] - dimensions['x']['max']

        self.offset_x(position_x - additional)

    def snap_right(self, nodes, additional=0):
        if isinstance(nodes, (list, tuple)):
            nodes = RNukeNodeGraph(nodes=nodes)

        node_dimensions = nodes.get_screen_space()
        dimensions = self.get_screen_space()

        position_x = node_dimensions['x']['max'] - dimensions['x']['min']

        self.offset_x(position_x + additional)

    def align(self, nodes, axis='x', value='min', additional=0):
        if isinstance(nodes, (list, tuple)):
            nodes = RNukeNodeGraph(nodes=nodes)

        node_dimensions = nodes.get_screen_space()
        dimensions = self.get_screen_space()
        offset = node_dimensions[axis][value] - dimensions[axis][value]
        func = eval('self.offset_{0}'.format(axis))
        func(offset + additional)

    def align_left(self, nodes, additional=0):
        self.align(nodes, axis='x', value='min', additional=additional)

    def align_right(self, nodes, additional=0):
        self.align(nodes, axis='x', value='max', additional=additional)

    def align_top(self, nodes, additional=0):
        self.align(nodes, axis='y', value='min', additional=additional)

    def align_bottom(self, nodes, additional=0):
        self.align(nodes, axis='y', value='max', additional=additional)

    def offset(self, value):
        self.set_position(value, relative=True)

    def offset_x(self, value):
        value_tuple = (value, 0)
        self.set_position(value_tuple, relative=True)

    def offset_y(self, value):
        value_tuple = (0, value)
        self.set_position(value_tuple, relative=True)

class RNukeNode(RNukeNodeGraphObject):
    def __init__(self, *args, **kwargs):
        self._node = None
        if kwargs.has_key('node'):
            node = kwargs.pop('node')
            self.set_node(node)
        super(RNukeNode, self).__init__(self, *args, **kwargs)

    def is_valid(self):
        result = True
        try:
            self._node['name'].value()
        except ValueError:
            result = False

        return result

    def get_node(self):

        return self._node

    def set_node(self, node):
        if isinstance(node, nuke.Node):
            self._node = node
        elif isinstance(node, str) and nuke.toNode(node):
            self._node = nuke.toNode(node)
        else:
            raise TypeError('{0} is of type {1}. Must be of type nuke.Node'.format(type(node), repr(node)))

    def get_xpos(self):

        return self.get_node()['xpos'].value()

    def get_ypos(self):

        return self.get_node()['ypos'].value()

    def get_width(self):
        xpos = self.get_node().xpos()
        ypos = self.get_node().ypos()
        self.get_node().autoplace()
        self.get_node().xpos()
        self.get_node().setXpos(xpos)
        self.get_node().setYpos(ypos)
        width = self.get_node().screenWidth()
        if not width:
            width = 80

        return width

    def get_height(self):
        xpos = self.get_node().xpos()
        ypos = self.get_node().ypos()
        self.get_node().autoplace()
        self.get_node().ypos()
        self.get_node().setXpos(xpos)
        self.get_node().setYpos(ypos)
        height = self.get_node().screenHeight()
        if not height:
            height = 66

        return height

    def get_screen_space(self):

        dimensions = {}
        for axis in AXIS_LUT.keys():
            dimensions[axis] = {'min' : 0, 'max' : 0}

        for axis in dimensions.keys():
            if axis == 'x':
                value = self.get_xpos()
                additional = self.get_width()
            else:
                value = self.get_ypos()
                additional = self.get_height()

            dimensions[axis]['min'] = value
            dimensions[axis]['max'] = value + additional

        return dimensions

    def set_position(self, position, relative=False):
        if isinstance(position, (tuple, list)) and len(position) == 2:
            node = self.get_node()
            if relative:
                node['xpos'].setValue(node['xpos'].value() + position[0])
                node['ypos'].setValue(node['ypos'].value() + position[1])
            else:
                node['xpos'].setValue(position[0])
                node['ypos'].setValue(position[1])
        else:
            raise TypeError('Position argument must be a tuple/list with a length of two.')

    def set_knobs(self, knobs, add=False):
        node = self.get_node()
        for key in knobs.keys():
            if not node.knobs().has_key(key):
                if add:
                    if isinstance(knobs[key], str):
                        knob = nuke.String_Knob(key)
                    elif isinstance(knobs[key], bool):
                        knob = nuke.Boolean_Knob(key)
                    elif isinstance(knobs[key], int):
                        knob = nuke.Int_Knob(key)
                    elif isinstance(knobs[key], float):
                        knob = nuke.Double_Knob(key)
                    node.addKnob(knob)
                    node[key].setValue(knobs[key])
                continue
            node[key].setValue(knobs[key])

        return True

    @staticmethod
    def from_selection():
        node = RNukeNode(node=nuke.selectedNode())

        return node

    def __getattr__(self, attr):

        attr_value = None
        if not self.__dict__.has_key(attr):
            node = self.get_node()
            attr_value = node.__getattribute__(attr)
            if not attr_value:
                raise AttributeError('\'{0}\' object has no attribute \'{1}\''.format(type(self), attr))
        else:
            attr_value = self.__dict__.get(attr)

        return attr_value

    def __getitem__(self, key):
        node = self.get_node()
        knob = None
        if node:
            knob = node.knobs().get(key)

        return knob

class RNukeNodeGraph(RNukeNodeGraphObject):
    def __init__(self, *args, **kwargs):
        self._nodes = []
        self._new_node_position = None
        if kwargs.has_key('nodes'):
            nodes = kwargs.pop('nodes')
            self.set_nodes(nodes)
        super(RNukeNodeGraph, self).__init__(self, *args, **kwargs)

    def set_position(self, position, relative=False):
        # We want all the nodes to stay in the same place relative to each other
        # so we will do a little 2d math to prepare the positions for these nodes.
        if isinstance(position, (tuple, list)) and len(position) == 2:
            if relative:
                for node in self:
                    # Get the position of our node
                    x, y = node.get_position()
                    # Add the position to the node position
                    motion_x = x + position[0]
                    motion_y = y + position[1]
                    # Tell the node to move there
                    node.set_position((motion_x, motion_y))
            else:
                # Get the vector of our node graph
                x, y = self.get_position()
                # Remove the location of our node graph from the equation
                # so we can get a vector.
                motion_x = position[0] - x
                motion_y = position[1] - y
                self.set_position((motion_x, motion_y), relative=True)
        else:
            raise TypeError('Position argument must be a tuple/list with a length of two.')

    def get_screen_space(self):

        dimensions = {}
        for axis in AXIS_LUT.keys():
            dimensions[axis] = {'min' : 0, 'max' : 0}

        for axis in dimensions.keys():
            values = []

            for node in self:
                position = eval('node.get_{0}()'.format(AXIS_LUT[axis]))
                values.append(position)
                if axis == 'x':
                    additional = node.get_width()
                else:
                    additional = node.get_height()

                values.append(position + additional)

            if values:
                dimensions[axis]['min'] = min(values)
                dimensions[axis]['max'] = max(values)

        return dimensions

    def add_node(self, node):
        if not isinstance(node, (RNukeNodeGraph)):
            if isinstance(node, nuke.Node):
                node = RNukeNode(node=node)
            elif isinstance(node, str):
                node = nuke.toNode(node)

            if not node in self:
                self._nodes.append(node)
        else:
            self.add_nodes(node.get_nodes())

        return True

    def remove_node(self, node):
        if isinstance(node, str):
            node = nuke.toNode(node)
            if node:
                self.remove_node(node)

        if node in self._nodes:
            self._nodes.remove(node)

        return True

    def remove_nodes(self, nodes):

        for node in list_utils.to_list(nodes):
            self.remove_node(node)

    def add_nodes(self, nodes):

        for node in list_utils.to_list(nodes):
            self.add_node(node)

    def set_nodes(self, nodes):

        self.clear_nodes()
        self.add_nodes(nodes)

        return True

    def clear_nodes(self):

        self._nodes = []

    def get_nodes(self):

        self.remove_invalids()

        return self._nodes

    def get_backdrop_node(self):
        is_backdrop = lambda n: True if n.Class() == 'BackdropNode' else False
        nodes = filter(is_backdrop, self._nodes)
        if len(nodes) > 0:
            return nodes[0].get_node()

    def get_scanline_render_node(self):
        is_scanline_render = lambda n: True if n.Class() == 'ScanlineRender'\
            else False
        nodes = filter(is_scanline_render, self._nodes)
        if len(nodes) > 0:
            return nodes[0].get_node()
        else:
            return Failure(message='No ScanlineRender node found in node'
                                   ' graph.')

    def is_valid(self):
        result = True
        for node in self:
            if not node.is_valid():
                result = False
                break

        return result

    def remove_invalids(self):
        invalids = []
        for node in self._nodes:
            if not node.is_valid():
                invalids.append(node)

        self.remove_nodes(invalids)

    def select(self):
        for node in self:
            node.select()

    def deselect(self):
        for node in self:
            node.deselect()

    def enable(self):
        for node in self:
            node.enable()

    def disable(self):
        for node in self:
            node.disable()

    def get_new_node_position(self):
        if not self._new_node_position:
            self._new_node_position = self.get_position()

        return self._new_node_position

    def create_node(self, node_type, **kwargs):

        position = self.get_new_node_position()
        kwargs['xpos'] = kwargs.get('xpos', position[0])
        kwargs['ypos'] = kwargs.get('ypos', position[1])
        rnode = None
        custom_knobs = {}
        name = node_type
        if kwargs.has_key('custom_knobs'):
            custom_knobs = kwargs.pop('custom_knobs')
        if kwargs.has_key('name'):
            name = kwargs.pop('name')

        kwargs['name'] = get_available_name(name)
        parent_node = kwargs.pop('parent_node', self.get_root())

        node_class = eval('nuke.nodes.%s' % (node_type))

        with parent_node:
            node = node_class(**kwargs)
            rnode = RNukeNode(node=node)
            rnode.set_knobs(custom_knobs, add=True)

            self.add_node(rnode)

        if rnode:
            ng_position = self.get_position()
            new_x = (position[0] + rnode.get_width() + 30)
            new_y = position[1]
            if new_x >= (ng_position[0] + self.get_width()):
                new_x = ng_position[0]
                new_y = (position[1] + rnode.get_height() + 30)
            new_position = (new_x, new_y)
            self.set_new_node_position(new_position)

        return rnode

    def create_node_graph(self, nodes=None):
        node_graph = RNukeNodeGraph(nodes=nodes)
        node_graph.set_parent(self)
        self.add_node(node_graph)

        return node_graph

    def create_backdrop(self, top=10, bottom=10, left=10, right=10, **kwargs):
        position = self.get_position()
        width = self.get_width()
        height = self.get_height()

        min_x = position[0] - left
        max_x = width + right + left
        min_y = position[1] - top
        max_y = height + bottom + top

        r = lambda: random.randint(0,255)

        if not kwargs.has_key('tile_color'):
            kwargs['tile_color'] = '{0:02}{1:02}{2:02}'.format(r(), r(), r())
        kwargs['xpos'] = min_x
        kwargs['ypos'] = min_y
        kwargs['bdwidth'] = max_x
        kwargs['bdheight'] = max_y
        kwargs['note_font_size'] = kwargs.get('note_font_size', 48)

        rnode = self.create_node('BackdropNode', **kwargs)

        return rnode

    def shuffle_backdrops(self):
        # First let's get all our backdrops
        backdrops = []
        for node in self:
            if node.get_node().Class() == 'BackdropNode':
                backdrops.append(node)

        # Next let's sort the backdrops by size. Largest to smallest.
        backdrops = sorted(backdrops, key=lambda x: x.get_area())
        # Now we just select the nodes to raise it up
        for backdrop in backdrops:
            backdrop.get_node().selectNodes()

    def resize_backdrop(self, top=10, bottom=10, left=10, right=10, **kwargs):
        "This is not implemented yet.  I need to work out removing the backdrop from the calculation so it can be done correctly."

        return

        if not self._backdrop:
            self.create_backdrop(top=top, buttom=bottom, left=left, right=right, **kwargs)
        else:
            position = self.get_position()
            width = self.get_width()
            height = self.get_height()

            min_x = position[0] - left
            max_x = width + right + left
            min_y = position[1] - top
            max_y = height + bottom + top

            kwargs['xpos'] = min_x
            kwargs['ypos'] = min_y
            kwargs['bdwidth'] = max_x
            kwargs['bdheight'] = max_y
            kwargs['note_font_size'] = kwargs.get('note_font_size', 48)

            set_knobs(self._backdrop.get_node(), kwargs)

    def get_root(self):

        return self._root

    def set_new_node_position(self, position):
        if isinstance(position, (tuple, list)) and len(position) == 2:
            self._new_node_position = position
        else:
            raise TypeError('Position argument must be a tuple/list with a length of two.')

    @staticmethod
    def from_selection():
        rnode_graph = RNukeNodeGraph(nodes=nuke.selectedNodes())

        return rnode_graph

    @staticmethod
    def from_script():
        rnode_graph = RNukeNodeGraph(nodes=nuke.allNodes())

        return rnode_graph

    @staticmethod
    def from_file(path):
        rnode_graph = None
        if os.path.exists(path):
            nuke.nodePaste(path)
            rnode_graph = RNukeNodeGraph.from_selection()

        return rnode_graph

    def __iter__(self):
        self.remove_invalids()
        for node in self._nodes:
            yield node

    def __getitem__(self, index):
        return self._nodes[index]

    def __len__(self):

        return len(self._nodes)

    def __str__(self):

        print_str = '{0}\nNodeGraph\n'.format('-' * 50)
        # print_str = '{0}\nParent:\n'.format(print_str)
        # print_str = '{0}\t{1}\n'.format(print_str, self.get_parent())
        print_str = '{0}\nRoot:\n'.format(print_str)
        print_str = '{0}\t{1}\n'.format(print_str, self.get_root()['name'].value())
        print_str = '{0}\nNodes::\n'.format(print_str)
        for node in self:
            print_str = '{0}\t{1}\n'.format(print_str, node['name'].value())
        print_str = '{0}\nDimensions:\n'.format(print_str)
        dimensions = self.get_screen_space()
        for axis in dimensions.keys():
            print_str = '{0}\t{1}:\n'.format(print_str, axis)
            for value in dimensions[axis]:
                print_str = '{0}\t\t{1}: {2}\n'.format(print_str, value, dimensions[axis][value])
                # print_str = '{0}\t\t\t{1}\n'.format(print_str, )

        print_str = '{0}{1}\n'.format(print_str, '-' * 50)

        return print_str



