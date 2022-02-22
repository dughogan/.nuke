#!/usr/bin/env python
# -*- coding: utf-8 -*-

#PUBLISHTO /data/film/apps/reelfx/python/
#SETMODE 777

"""
NAME: scaleNodes.py
AUTHOR: Garrett Moring

Edited by Ed W. Apr 2013

Scale the position of selected nodes for
easy organization of node networks in Nuke.
"""

import nuke
import nukescripts

class scalePanel( nukescripts.PythonPanel ):
	def __init__( self, ):
		nukescripts.PythonPanel.__init__( self, 'Scale Nodes')
		self.setMinimumSize(500, 150)
		self.axisList = ["xy", "x", "y"]
		
		# CREATE KNOBS
		self.axis = nuke.Enumeration_Knob( 'scaleAxis', 'Scale Axis', self.axisList )
		self.topLeft = nuke.Boolean_Knob( 'topLeft', '' )
		self.topCenter = nuke.Boolean_Knob( 'topCenter', '' )
		self.topRight = nuke.Boolean_Knob( 'topRight', '' )
		self.midLeft = nuke.Boolean_Knob( 'midLeft', '' )
		self.midLeft.setFlag(nuke.STARTLINE)
		self.midCenter = nuke.Boolean_Knob( 'midCenter', '' )
		self.midRight = nuke.Boolean_Knob( 'midRight', '' )
		self.bottomLeft = nuke.Boolean_Knob( 'bottomLeft', '' )
		self.bottomLeft.setFlag(nuke.STARTLINE)
		self.bottomCenter = nuke.Boolean_Knob( 'bottomCenter', '' )
		self.bottomRight = nuke.Boolean_Knob( 'bottomRight', '' )
		self.blank = nuke.Text_Knob( '' )
		self.label = nuke.Text_Knob( 'Scale From:' )
		self.scale = nuke.Scale_Knob( 'scale', 'Scale' )
		self.scale.setFlag(0x00000002) # adds the slider
		self.scale.setFlag(0x04000000) # no numeric fields
		self.intScale = nuke.Double_Knob( 'intScale', '' )
		self.intScale.clearFlag(0x00000002)
		
		# Store list of check box knobs
		self.checkBoxes = [self.topLeft, self.topCenter,
						   self.topRight, self.midLeft,
						   self.midCenter, self.midRight,
						   self.bottomLeft, self.bottomCenter,
						   self.bottomRight]
		
		# ADD KNOBS
		self.addKnob(self.axis)
		self.addKnob(self.label)
		
		# loop through and add checkboxes - EdW
		for chk in self.checkBoxes:
		  self.addKnob(chk)
		
		self.addKnob(self.blank)
		self.addKnob(self.scale)
		self.addKnob(self.intScale)
		
		# Set scale default to 1
		self.scale.setValue(1)
		self.intScale.setValue(1)
		self.midCenter.setValue(1)
		self.scalePos = 'midCenter'
		self.selectedNodes = nuke.selectedNodes()
		self.positionDictionary = storePosition(self.selectedNodes)
	
	def uncheck( self ):
		for check in self.checkBoxes:
			check.setValue(0)
	
	def knobChanged( self, knob ):
		
		if knob == self.intScale:
			scaleNodes(self.positionDictionary, self.selectedNodes, self.scalePos, self.axis.value(), self.intScale.value())
			self.scale.setValue(self.intScale.value())
		
		if knob == self.scale:
			scaleNodes(self.positionDictionary, self.selectedNodes, self.scalePos, self.axis.value(), self.scale.value()[0])
			self.intScale.setValue(self.scale.value()[0])
			
		# uncheck all knobs and set changed knob
		elif knob in self.checkBoxes:
			self.uncheck()
			knob.setValue(1)
			self.scalePos = knob.name()
		
		else:
		  pass



def get_min_max(node_list):
	'''
	Returns the minimum & maximum
	x,y coords of nodes in the node_list
	'''
	first_node = node_list[0]
	
	x_min = first_node['xpos'].value()
	x_max = (first_node['xpos'].value() + first_node.screenWidth())
	
	y_min = (first_node['ypos'].value() - first_node.screenHeight())
	y_max = first_node['ypos'].value()
	
	# Find min/max
	for node in node_list:
		
		# check if this node is a backdrop node
		if node.Class() == "BackdropNode":
			if ( node['xpos'].value() + node['bdwidth'].value() ) > x_max:
				x_max = node['xpos'].value() + node['bdwidth'].value()
			
			if node['xpos'].value() < x_min:
				x_min = node['xpos'].value()
			
			if ( node['ypos'].value() + node['bdheight'].value() ) > y_max:
				y_max = node['ypos'].value() + node['bdheight'].value()
			
			if ( node['ypos'].value() - node['bdheight'].value() ) < y_min:
				y_min = node['ypos'].value() - node['bdheight'].value()
		
		else:
			if ( node['xpos'].value() + node.screenWidth() ) > x_max:
				x_max = node['xpos'].value() + node.screenWidth()
			
			if node['xpos'].value() < x_min:
				x_min = node['xpos'].value()
			
			if node['ypos'].value() > y_max:
				y_max = node['ypos'].value()
			
			if ( node['ypos'].value() - node.screenHeight() ) < y_min:
				y_min = node['ypos'].value() - node.screenHeight()
	
	return x_min, x_max, y_min, y_max


def seatRead(nodeList):
	'''
	seats Read nodes that have scaled positions too far away
	from their 'shuffle' counterparts
	'''
	for node in nodeList:
		
		# Only operate on Read nodes
		if node.Class() == 'Read':
			
			# Only operate if Read node has ONLY ONE Shuffle output
			if len(node.dependent()) > 0:
				if node.dependent()[0].Class() == 'Shuffle' and len(node.dependent()) == 1:
					
					readHeight = node.screenHeight()
					readWidth = node.screenWidth()
					shuffleHeight = node.screenHeight()
					shuffleWidth = node.screenWidth()
					shuffleX = node.dependent()[0].xpos()
					shuffleY = node.dependent()[0].ypos()
					readX = node.xpos()
					readY = node.ypos()
					offset = 7
					
					xDiff = readX - shuffleX
					yDiff = readY - shuffleY
					
					if xDiff < 0:
						xDiff *= -1
						
					if yDiff < 0:
						yDiff *= -1
						
					if xDiff < yDiff:
						# Vertical alignment- check if above or below dependent
						if readY < shuffleY:
							# Set the Y position of this read ABOVE the shuffle
							node['ypos'].setValue( shuffleY - offset - readHeight )
							
						else:
							# Set the Y position of this read BELOW the shuffle
							node['ypos'].setValue( shuffleY + offset + shuffleHeight )
						
					if yDiff < xDiff:
						# Horizontal alignment- check which side of dependent(l/r)
						if readX > shuffleX:
							# Set the X position of this read to the RIGHT of the shuffle
							node['xpos'].setValue( shuffleX + offset + shuffleWidth )
							
						else:
							# Set the X position of this read to the LEFT of the shuffle
							node['xpos'].setValue( shuffleX - offset - readWidth )



def rightAngler(dotNode):
	'''
	Reposition selected dot nodes to be at 90 degrees
	relative to it's input and output connections.
	
	There will be 2 possible solutions for these requirements.
	The correct solution will be determined by whichever is
	nearest to the original position.
	'''
	dotX = dotNode['xpos'].value()
	dotY = dotNode['ypos'].value()
	
	inputNode = dotNode.dependencies()[0]
	outputNode = dotNode.dependent()[0]
	
	inputX = inputNode['xpos'].value()
	inputY = inputNode['ypos'].value()
	inputW = inputNode.screenWidth()
	inputH = inputNode.screenHeight()
	
	outputX = outputNode['xpos'].value()
	outputY = outputNode['ypos'].value()
	outputW = outputNode.screenWidth()
	outputH = outputNode.screenHeight()
	
	


def storePosition(selection):
	'''
	Store selected node names & x/y pos in a dictionary
	'''
	positionDictionary = {}
	
	for node in selection:
		
		posList = []
		
		# get name/x/y
		name = node['name'].value()
		posList.append(node.xpos())
		posList.append(node.ypos())
		
		if node.Class() == 'BackdropNode':
			posList.append(node['bdwidth'].value())
			posList.append(node['bdheight'].value())
		
		# assign posList to name of node
		positionDictionary[name] = posList
	
	# Return dictionary
	return positionDictionary


def scaleNodes(positions, selection, scaleFrom, scaleAxis, scaleValue):
	
	scale = scaleValue
	
	# Find center of selected nodes
	x_min, x_max, y_min, y_max = get_min_max(selection)
	x_midPoint = ( x_max + x_min) / 2
	y_midPoint = ( y_max + y_min) / 2
	X_offset = x_midPoint
	Y_offset = y_midPoint
	
	# Determine the 'scaleFrom' position
	if scaleFrom == "topLeft":
		X_offset = x_min
		Y_offset = y_min
	
	elif scaleFrom == "topCenter":
		X_offset = x_midPoint
		Y_offset = y_min
	
	elif scaleFrom == "topRight":
		X_offset = x_max
		Y_offset = y_min
	
	elif scaleFrom == "midLeft":
		X_offset = x_min
		Y_offset = y_midPoint
	
	elif scaleFrom == "midCenter":
		X_offset = x_midPoint
		Y_offset = y_midPoint
	
	elif scaleFrom == "midRight":
		X_offset = x_max
		Y_offset = y_midPoint
	
	elif scaleFrom == "bottomLeft":
		X_offset = x_min
		Y_offset = y_max
	
	elif scaleFrom == "bottomCenter":
		X_offset = x_midPoint
		Y_offset = y_max
	
	elif scaleFrom == "bottomRight":
		X_offset = x_max
		Y_offset = y_max
	
	else:
		# this is the default if none is specified, or the entry doesn't exist
		X_offset = x_midPoint
		Y_offset = y_midPoint
	
	
	
	# Determine 'scaleAxis' & set default to False
	x_axis = 'False'
	y_axis = 'False'
	
	if scaleAxis == "x":
		x_axis = 'True'
	
	elif scaleAxis == "y":
		y_axis = 'True'
	
	elif scaleAxis == "xy":
		x_axis = 'True'
		y_axis = 'True'
	
	else:
		# this is the default if none is specified, or the entry doesn't exist
		x_axis = 'True'
		y_axis = 'True'
	
	
	'''
	Translate selection to the origin. (based on reference point)
	This determines from which point the group is scaled.
	Apply the scalar value, then return to original position
	relative to the reference point.
	'''
	
	for node in selection:
		
		# Get ORIGINAL positions (not current positions)
		if node.Class() != "BackdropNode":
			originalX = ( positions[node['name'].value()][0] + (node.screenWidth() / 2))
			originalY = ( positions[node['name'].value()][1] + (node.screenHeight() / 2))
			
		else:
			originalX = positions[node['name'].value()][0]
			originalY = positions[node['name'].value()][1]
			originalW = positions[node['name'].value()][2]
			originalH = positions[node['name'].value()][3]
		
		# Translate based on scaleFrom position
		if x_axis == 'True':
			translateX = originalX - X_offset
			scaledX = translateX * scale
			finalX = scaledX + X_offset
			
			if node.Class() == "BackdropNode":
				# scale width of bd node
				node['xpos'].setValue( finalX )
				node['bdwidth'].setValue(originalW * scale)
				
			
			else:
				node['xpos'].setValue( finalX - (node.screenWidth() / 2) )
		
		
		if y_axis == 'True':
			translateY = originalY - Y_offset
			scaledY = translateY * scale
			finalY = scaledY + Y_offset
			
			if node.Class() == "BackdropNode":
				# scale height of bd node
				node['ypos'].setValue( finalY )
				node['bdheight'].setValue(originalH * scale)
				
			
			else:
				node['ypos'].setValue( finalY - (node.screenHeight() / 2) )
	
	# adjust read node positions
	seatRead(selection)

def main():
	
	#check for no selection
	if len(nuke.selectedNodes()) == 0:
		nuke.message("Please select nodes to scale.")
	
	else:
		# call the scalePanel GUI
		newScale = scalePanel()
		newScale.show()

def runInBackground():
	newScale = scalePanel()













