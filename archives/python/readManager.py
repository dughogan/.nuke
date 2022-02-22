# -*- coding: utf-8 -*-
'''
Created on May 31, 2012

@author: Doris Wang

readManager:
Allows the users to modify read node settings on all selected reads
'''

import sys
import nuke

userInput = {}

def gui():
    window = nuke.Panel("Read Manager", 400)
    window.addSingleLineInput("Frame Range", "")
    window.addEnumerationPulldown("Before the first frame: ", "default hold loop bounce black")
    window.addEnumerationPulldown("After the last frame: ", "default hold loop bounce black")  
    window.addSingleLineInput("Freeze Frame: ", "") 
    window.addEnumerationPulldown("Missing Frames: ", "default error black checkerboard nearest_frame") 
    window.addBooleanCheckBox("Remove Freeze Frame", False)
    result = window.show()
    
    if result == 1:
        if window.value("Frame Range"):
            startFrame = window.value("Frame Range").split("-")[0]
            lastFrame = window.value("Frame Range").split("-")[1]
            
            userInput['startFrame'] = startFrame
            userInput['lastFrame'] = lastFrame
            
        if window.value("Before the first frame: ") is not "default":
            before = window.value("Before the first frame: ")
            
            userInput['before'] = before

        if window.value("After the last frame: ") is not "default":
            after = window.value("After the last frame: ")
            
            userInput['after'] = after
            
        if window.value("Freeze Frame: ") and not window.value("Remove Freeze Frame"):
            frame = window.value("Freeze Frame: ")
            
            userInput['frame'] = frame
            
        elif window.value("Remove Freeze Frame") and not window.value("Freeze Frame: "):
            userInput['frame'] = ""
            
        if window.value("Missing Frames: ") is not "default":
            onError = window.value("Missing Frames: ")
            
            if onError == "nearest_frame":
                onError = "nearest frame"
                
            userInput['onError'] = onError   
        
    return userInput
       
def modReads(inputs):
    node_types = ['Read', 'DeepRead']
    
    all_nodes = nuke.selectedNodes()        
    
    if all_nodes:
      for each_node in all_nodes:
	
	  node_class = each_node.Class()
	  
	  if node_class in node_types:
	
	    cStartFrame = each_node['first'].value()
	    cLastFrame = each_node['last'].value()
	    cBefore = each_node['before'].value()
	    cAfter = each_node['after'].value()
	    cFreezeFrame = each_node['frame'].value()
	    cError = each_node['on_error'].value()
	    
	    if inputs.has_key("startFrame"):
		each_node['first'].setValue(int(inputs['startFrame']))
	    else:
		each_node['first'].setValue(int(cStartFrame))
	    
	    if inputs.has_key('lastFrame'):
		each_node['last'].setValue(int(inputs['lastFrame']))
	    else:
		each_node['last'].setValue(int(cLastFrame))
		
	    if inputs.has_key('before'):
		each_node['before'].setValue(inputs['before'])
	    else:
		each_node['before'].setValue(cBefore)
		
	    if inputs.has_key('after'):
		each_node['after'].setValue(inputs['after'])
	    else:
		each_node['after'].setValue(cAfter)
		
	    if inputs.has_key('frame'):
		each_node['frame'].setValue(inputs['frame'])
	    else:
		each_node['frame'].setValue(cFreezeFrame)
		
	    if inputs.has_key('onError'):
		each_node['on_error'].setValue(inputs['onError'])
	    else:
		each_node['on_error'].setValue(cError)
    
def main():    
    inputs = gui()
    modReads(inputs)
    