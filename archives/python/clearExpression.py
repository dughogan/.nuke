#!/usr/bin/env python
# -*- coding: utf-8 -*-

#PUBLISHTO /data/film/apps/reelfx/python/
#SETMODE 777

"""
NAME: clearExpression.py
AUTHOR: Doug Hogan (based on Garrett Morring's clearAnimation)

Removes ALL expressions on ALL knobs of seleected nodes
"""

import nuke

def main():
	
	clearedList = []
	
	for node in nuke.selectedNodes():
		for knob in node.knobs():
			if node[knob].isAnimated():
				node[knob].clearAnimated()
				clearedList.append(node['name'].value())
				print "%s cleared" % node['name'].value()
	
	if len(clearedList) == 1:
		finishedMessage = "Expression cleared"
	
	else:
		finishedMessage = "%d nodes with expressions have been cleared" % len(clearedList)
	
	nuke.message(finishedMessage)