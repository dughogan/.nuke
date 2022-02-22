#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
NAME: mrExp.py
AUTHOR: Doug Hogan

"""

import sys
import nuke

userInput = {}

def gui():
    window = nuke.Panel("Mr. Expression", 400)
    window.addMultilineTextInput("Expression: ", "") 
    knobList = sorted(nuke.selectedNode().knobs())
    window.addEnumerationPulldown( 'Knob:', ' '.join( knobList ) )
    
    result = window.show()
    
    if result == 1:
            
        if window.value("Expression: ") and not window.value("Remove Expression"):
            set_expression = window.value("Expression: ")
            set_knob = window.value("Knob:")
            
            userInput['set_expression'] = set_expression
            userInput['set_knob'] = set_knob
        
    return userInput
       
def modExpression(inputs):
    allNodes = nuke.selectedNodes()        
        
    for node in allNodes:
          
        if inputs.has_key('set_expression'):
            node[inputs['set_knob']].setExpression(inputs['set_expression'])
        else:
            try: 
	      node[inputs['set_knob']].setExpression(inputs['set_expression'])
	    except:
	      pass

def main():    
    inputs = gui()
    modExpression(inputs)