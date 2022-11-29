#!/usr/bin/env python
#----------------------------------------------------------------------------#
#------------------------------------------------------------ HEADER_START --#

"""
@author:
    doug.hogan

@description:
    - Super simple same-as script

@applications:
    - nuke

"""
#----------------------------------------------------------------------------#
#-------------------------------------------------------------- HEADER_END --#

#----------------------------------------------------------------------------#
#----------------------------------------------------------------- IMPORTS --#
import nuke_internal as nuke
import nuke
import nukescripts
import re
import string
import glob
import os
import os.path
import sys
from os import walk

#----------------------------------------------------------------------------#
#-------------------------------------------------------- UTIL DEFINITIONS --#
def __NodeHasKnobWithName(node, name):
  try:
    node[name]
  except NameError:
    return False
  else:
    return True

def __NodeHasFileKnob(node):
  return __NodeHasKnobWithName(node, 'file')

def __ReplaceKnobValue(sourceStr, newStr, knob):
  v = knob.value()
  if v:
    repl = re.sub(sourceStr, newStr, v)
    knob.setValue(repl)
    
#----------------------------------------------------------------------------#
#------------------------------------------------ VERSION TOOL DEFINITIONS --#
def version_get(string, prefix, suffix = None):

  if string is None:
    raise ValueError("Empty version string - no match")

  regex = "[/_.]"+prefix+"\d+"
  matches = re.findall(regex, string, re.IGNORECASE)
  if not len(matches):
    msg = "No \"_"+prefix+"#\" found in \""+string+"\""
    raise ValueError(msg)
  return (matches[-1:][0][1], re.search("\d+", matches[-1:][0]).group())


def version_set(string, prefix, oldintval, newintval):

  regex = "[/_.]"+prefix+"\d+"
  matches = re.findall(regex, string, re.IGNORECASE)
  if not len(matches):
    return ""

  # Filter to retain only version strings with matching numbers
  matches = [s for s in matches if int(s[2:]) == oldintval]

  # Replace all version strings with matching numbers
  for match in matches:
    # use expression instead of expr so 0 prefix does not make octal
    fmt = "%%(#)0%dd" % (len(match) - 2)
    newfullvalue = match[0] + prefix + str(fmt % {"#": newintval})
    string = re.sub(match, newfullvalue, string)
  return string


def version_up():

  n = nuke.selectedNodes()
  for i in n:
    _class = i.Class()
    # check to make sure this is a read or write op
    if _class in __NODES_FOR_VERSION:
      fileKnob = i['file']
      proxyKnob = i.knob('proxy')
      try:
        (prefix, v) = version_get(fileKnob.value(), 'v')
        v = int(v)
        fileKnob.setValue(version_set(fileKnob.value(), prefix, v, v + 1))
      except ValueError:
        # We land here if there was no version number in the file knob.
        # If there's none in the proxy knob either, just show the exception to the user.
        # Otherwise just update the proxy knob
        if proxyKnob and proxyKnob.value():
          (prefix, v) = version_get(proxyKnob.value(), 'v')
          v = int(v)

      if proxyKnob and proxyKnob.value():
        proxyKnob.setValue(version_set(proxyKnob.value(), prefix, v, v + 1))

      nuke.root().setModified(True)


def version_down():

  n = nuke.selectedNodes()
  for i in n:
    _class = i.Class()
    # check to make sure this is a read or write op
    if _class in __NODES_FOR_VERSION:
      fileKnob = i['file']
      proxyKnob = i.knob('proxy')
      try:
        (prefix, v) = version_get(fileKnob.value(), 'v')
        v = int(v)
        fileKnob.setValue(version_set(fileKnob.value(), prefix, v, v - 1))
      except ValueError:
        # We land here if there was no version number in the file knob.
        # If there's none in the proxy knob either, just show the exception to the user.
        # Otherwise just update the proxy knob
        if proxyKnob and proxyKnob.value():
          (prefix, v) = version_get(proxyKnob.value(), 'v')
          v = int(v)
      if proxyKnob and proxyKnob.value():
        proxyKnob.setValue(version_set(proxyKnob.value(), prefix, v, v - 1))
      nuke.root().setModified(True)


def version_latest():

  class __KnobValueReplacer(object):
    def loop(self, knob):
      while True:
        oVersion = knob.value()
        try:
          (prefix, v) = version_get(oVersion, 'v')
          v = int(v)
          nVersion = version_set(oVersion, prefix, v, v + 1)
          knob.setValue(nVersion)
          if not os.path.exists(knob.evaluate()):
            knob.setValue(oVersion)
            return
          nuke.root().setModified(True)
        except ValueError:
          return

  nodes = nuke.selectedNodes()
  if not nodes: nodes = nuke.allNodes()
  ##Version to latest for Read nodes
  n = [i for i in nodes if i.Class() == "Read"]
  for i in n:
    __KnobValueReplacer().loop(i['file'])
    __KnobValueReplacer().loop(i['proxy'])
  ##Version to latest for Camera nodes  
  n = [i for i in nodes if i.Class() == "Camera3"]
  for i in n:
    __KnobValueReplacer().loop(i['file_link'])
    
  #Need to add logic for Write nodes to be reset based on the version of the script

    
#----------------------------------------------------------------------------#
#--------------------------------------------------------------- MAIN TOOL --#
def same_as_shot_tool():
  fileKnobNodes = [i for i in nuke.allNodes() if __NodeHasFileKnob(i)]
  if not fileKnobNodes: raise ValueError("No nodes detected. First open up a script to be same-as'd.")

  # Gets the file path and splits it
  fullPath = nuke.root().name()
  # Splits the Path by /
  splitPath = fullPath.split('/')
  # Gets the script file name and splits it again
  fileName = splitPath[-1]
  newFileName = fileName.split('_')
  
  # Stores the extracted Sequence Number
  seq = newFileName[0]
  # Stores the extracted Shot Number
  shot = newFileName[1]
  seq_shot = newFileName[0]+'_'+newFileName[1]
  # Stores the base Version variable
  version = 1
  
  ##Setup the UI
  p = nuke.Panel("Same-As Shot Tool")
  p.addSingleLineInput("Parent Shot #:", "%s" % seq_shot)
  p.addSingleLineInput("Child Shot #:", "")
  p.addSingleLineInput("New Frame Range", "")
  p.addBooleanCheckBox("Save New File?", True)
  
  success = p.show()
  
  if success == 1:
    sourceStr = p.value("Parent Shot #:")
    newStr = p.value("Child Shot #:")   
    startFrame = p.value("New Frame Range").split("-")[0]
    lastFrame = p.value("New Frame Range").split("-")[1]
    newSeqStr =  p.value("Child Shot #:").split("_")[0]
    newShotStr =  p.value("Child Shot #:").split("_")[1]     

    ## Replaces all the file paths to the new child shot
    for i in fileKnobNodes: __ReplaceKnobValue(sourceStr, newStr, i['file'])
    for i in nuke.allNodes(): __ReplaceKnobValue(sourceStr, newStr, i['label'])
    
    ## Replaces first and last frame ranges on Read nodes
    # with new user defined ones
    all_nodes = nuke.allNodes()  
    node_types = ['Read', 'DeepRead']    
    if all_nodes:
      for each_node in all_nodes:	
        node_class = each_node.Class()          
        if node_class in node_types:
          each_node['first'].setValue(int(startFrame))
          each_node['last'].setValue(int(lastFrame))
          each_node['origfirst'].setValue(int(startFrame))
          each_node['origlast'].setValue(int(lastFrame))

    # Change Project Settings frame ranges
    nuke.knob('root.first_frame', startFrame)
    nuke.knob('root.last_frame', lastFrame) 

    # Update all reads to the latest version available
    version_latest()
    
    ## Save the new same-as'd script in it's proper directory
    # This is a little clunky and is not folder structure agnostic. It's tailored to a specific studio pipeline and will need to be modified to work with another directory structure.
    saveAsPath = splitPath[0]+'/'+splitPath[1]+'/'+splitPath[2]+'/'+splitPath[3]+'/'+splitPath[4]+'/'+splitPath[5]+'/'+newSeqStr+'/'+newSeqStr+'_'+newShotStr+'/'+splitPath[8]+'/'+splitPath[9]+'/'
    saveAsFile = newSeqStr+'_'+newShotStr+'_comp_main'+'.'+'v001'+'.nk'
    pathAndFile = saveAsPath+saveAsFile
    
    fileSaved = False
    if p.value("Save New File?") == True:
        nuke.scriptSaveAs(pathAndFile)
        nuke.message('Same-as Shot Made and Saved!')
    else:
        nuke.message('Same-as Shot Made!')
    
    return True