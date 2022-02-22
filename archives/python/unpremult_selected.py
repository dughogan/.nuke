#!/usr/bin/env python
# -*- coding: utf-8 -*-

#PUBLISHTO /data/film/apps/reelfx/python/
#SETMODE 777

"""
NAME: groupInstance.py
AUTHOR: Doug Hogan
Edit: Garrett Moring

"""

import sys
import nuke

def main():
	
	# Nodes we want to effect
	node_types = ['Grade', 'ColorCorrect', 'HueCorrect', 'HueShift', 'Saturation', 'Histogram', 'EXPTool']
	
	# If nodes are selected then get our selection
	all_nodes = nuke.selectedNodes()
	
	# Check if we have nodes in the scene
	if all_nodes:
		# Smart search for node types
		for each_node in all_nodes:
			
			# Get node type
			node_class = each_node.Class()
			
			# Check if it's a valid node listed in "node_types"
			if node_class in node_types:
				# Set the unpremult knob
				each_node['unpremult'].setValue('rgba.alpha')
				sys.stderr.write('Premult Applied to: %s\n' % (each_node['name'].value()))