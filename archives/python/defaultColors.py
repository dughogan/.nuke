#!/usr/bin/env python
# -*- coding: utf-8 -*-

#PUBLISHTO /data/film/apps/reelfx/python/
#SETMODE 777

"""
NAME: defaultColors.py
AUTHOR: Garrett Moring
DATE: June 2012

Usage:
- Select some nodes
- run the script
- Selected nodes will return the default
  colors as defined in preferences

"""
import nuke

def main():
	
	for node in nuke.selectedNodes():
		if node.Class() != "BackdropNode" and node.Class() != "StickyNote":
			defCol = nuke.defaultNodeColor(node.Class())
			node['tile_color'].setValue(defCol)
		
		else:
			# fix crazy bright backdrop nodes from auto-reference section
			if node['tile_color'].value() == 640065791: node['tile_color'].setValue(1061126143)
			elif node['tile_color'].value() == 1000684543: node['tile_color'].setValue(1065304063)
			elif node['tile_color'].value() == 3469620735: node['tile_color'].setValue(2139045887)
			elif node['tile_color'].value() == 2350192127: node['tile_color'].setValue(2134851583)
			elif node['tile_color'].value() == 1351204095: node['tile_color'].setValue(1715300095)
    
	print "\nDone\n"
	