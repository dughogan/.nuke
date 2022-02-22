#!/usr/bin/env python
# -*- coding: utf-8 -*-

#PUBLISHTO /data/film/apps/reelfx/python/
#SETMODE 777

"""
NAME: showMixValue.py
AUTHOR: Garrett Moring

Sets the label of selected nodes to
reflect their respective mix values
"""

import sys
import nuke

def main():
	
	# If nodes are selected then get our selection
	selected = nuke.selectedNodes()
	
	# Check if we have nodes in the scene
	if selected:
		
		for each_node in selected:
			# Check if it has a mix knob
			if "mix" in each_node.knobs():
				# Set the knob
				if each_node['label'].value() != "":
					if each_node['label'].value().count('[value mix]') > 0:
						# remove tcl
						newLabel = each_node['label'].value().split('[value mix]')
						labelString = ""
						for item in newLabel:
							labelString = labelString + item
						each_node['label'].setValue(labelString)
					else:
						each_node['label'].setValue(each_node['label'].value() + "\n[value mix]")
						sys.stderr.write('Label of %s matches its mix value\n' % (each_node['name'].value()))
				else:
					each_node['label'].setValue('[value mix]')
					sys.stderr.write('Label of %s matches its mix value\n' % (each_node['name'].value()))