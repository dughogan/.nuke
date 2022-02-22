from collections import defaultdict
import re

import nuke

from pipe_utils.list_utils import to_list
from pipe_utils.dict_utils import printd
from nuke_tools import node_utils

def rgb_rebuild(nodes=None):
    nodes = to_list(nodes if nodes else nuke.selectedNodes())

    # This will pretty much give me everything back.
    main_ng = RNukeNodeGraph.from_script()
    for node in nodes:
        # Node Graph op
        ng_top = main_ng.create_node_graph(nodes=node)
        # position the node.
        node_utils.offset_relative(node, 'x', 1600, to_nodes=previous_nodes, exclude=node)
        node_utils.offset_relative(node, 'y', 0, to_nodes=previous_nodes, exclude=node)

        # All nodes created now will be relatively positioned
        channels = node.channels()
        channel_data = defaultdict(list)
        for channel in channels:
            # Channels are setup as follows
            # pass_name_image_plane
            # Example: joaquinChldCadet_ll_glint_aov
            # Match the image plane (glint_aov)
            match = re.search('([a-zA-Z]+_[a-zA-Z]+)\.', channel)
            if not match:
                # These not the channels we're looking for...
                continue
            # Now build a list of channel sets we can shuffle based on the type.
            channel_match = re.search('([a-zA-Z0-9_]+)\.', channel)
            if channel_match and not channel_match.group(1) in channel_data[match.group(1)]:
                channel_data[match.group(1)].append(channel_match.group(1))

        # We will change main pipe as we hook in merges and dots.
        main_in = node
        # Loop through the image plane types.
        previous_ip_nodes = [node]
        for ip_type in channel_data.keys():
            ip_nodes = []
            # Each image plane will always have a minimum of 3 dots and main pipe merge
            main_dot = node_utils.create_node('Dot')
            main_dot.setInput(0, main_in)
            ip_nodes.append(main_dot)
            node_utils.offset_relative(main_dot, 'x', (0 - main_in.screenWidth()), to_nodes=main_in)
            node_utils.offset_relative(main_dot, 'y', 150, to_nodes=main_in)

            # The dot is now our in to the main pipe
            main_in = main_dot

            # The items shifted to the side will use this dot as their access point
            branch_dot = node_utils.create_node('Dot')
            branch_dot.setInput(0, main_dot)
            ip_nodes.append(branch_dot)
            node_utils.offset_relative(branch_dot, 'x', -1000, to_nodes=main_dot)
            node_utils.offset_relative(branch_dot, 'y', 0, to_nodes=main_dot)

            master_in = None
            previous_dot = None
            previous_channel_nodes = [branch_dot]
            for i, channel in enumerate(channel_data.get(ip_type)):
                channel_nodes = []
                channel_dot = node_utils.create_node('Dot')
                channel_dot.setInput(0, (previous_dot if previous_dot else branch_dot))
                channel_nodes.append(channel_dot)
                previous_dot = channel_dot

                node_utils.offset_relative(channel_dot, 'x', (0 - branch_dot.screenWidth()), to_nodes=branch_dot)
                node_utils.offset_relative(channel_dot, 'y', 100, to_nodes=branch_dot)

                shuffle = node_utils.create_node('Shuffle')
                shuffle.setInput(0, channel_dot)
                shuffle['in'].setValue(channel)
                channel_nodes.append(shuffle)

                node_utils.offset_relative(shuffle, 'x', 50, to_nodes=channel_dot)
                node_utils.offset_relative(
                    shuffle, 'y', (0 - abs(shuffle.screenHeight() - channel_dot.screenHeight())/2), to_nodes=channel_dot)

                if i == 0:
                    hookup = node_utils.create_node('Dot')
                    node_utils.offset_relative(hookup, 'x', 100, to_nodes=shuffle)
                else:
                    hookup = node_utils.create_node('Merge')
                    hookup.setInput(1, master_in)
                    node_utils.offset_relative(hookup, 'x', 66, to_nodes=shuffle)

                hookup.setInput(0, shuffle)
                channel_nodes.append(hookup)

                master_in = hookup

                node_utils.offset_relative(hookup, 'y', (abs(shuffle.screenHeight() - hookup.screenHeight())/2), to_nodes=shuffle)

                node_utils.offset_relative(channel_nodes, 'y', 50, to_nodes=previous_channel_nodes)
                previous_channel_nodes = channel_nodes

                ip_nodes.extend(channel_nodes)

            node_utils.offset_relative(ip_nodes, 'y', 500, to_nodes=previous_ip_nodes)

            node_utils.create_backdrop(ip_nodes, extra_width=5, extra_height=5)

            previous_ip_nodes = ip_nodes

        previous_nodes = created_nodes