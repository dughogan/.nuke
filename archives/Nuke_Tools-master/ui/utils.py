#!/usr/bin/env python

"""
@author:
    tpitts

@description:
    - Set of ui utility functions

@applications
    - nuke

"""

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- IMPORTS --#
# builtin

# third party
import nuke

# internal
from nuke_tools import node_utils

# external
from pipe_utils.list_utils import to_list
from pipe_utils.io import IO
from ui_lib.dialogs import popup
from ui_lib.rnuke.old_widgets import ChannelBrowser

#----------------------------------------------------------------------------#
#--------------------------------------------------------------- FUNCTIONS --#
def display_read_node_paths():
    """
    Queries the selected/all read node paths and displays them.

    @rtype: str
    @returns: The string representation of the node paths.

    """
    nodes = node_utils.get_selected_nodes(filters=['Read', 'DeepRead'])
    if not nodes:
        nodes = node_utils.get_all_nodes(filters=['Read', 'DeepRead'])
    return display_node_paths(nodes, title='Read Node Paths')

def display_node_paths(nodes, title='Node Paths'):
    nodes = to_list(nodes)
    node_objs = []
    for node in nodes:
        if isinstance(node, nuke.Node):
            node_objs.append(node)
        else:
            node_objs.append(nuke.toNode(node))

    node_paths = []
    for node in node_objs:
        node_paths.append(node['file'].evaluate())
    out = ''
    for path in node_paths:
        out = '%s\n%s' % (out, path)

    popup.show_message(out, title, center_on_screen=True)

    return out

def select_channel():
    """
    Allows a lighting artist to easily select and set channel knobs on a node.

    @rtype: bool
    @returns: The result.

    """
    result = False

    d_channel_knobs = ['ChannelMask_Knob', 'Channel_Knob']

    node = node_utils.get_selected_nodes()
    if node:
        if len(node) > 1:
            IO.info('More than one node selected. Defaulting to first')
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
        prompt = ChannelBrowser(channel_knobs, channels, title)

        if prompt.left and prompt.right:
            IO.info('Setting { %s.%s } to { %s }' % (name, prompt.left, prompt.right))
            node[prompt.left].setVisible(True)
            node[prompt.left].setValue(prompt.right)
            result = True

    return result

