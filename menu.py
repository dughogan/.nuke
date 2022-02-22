###################
# Brazen Nuke Menu #
###################

import os
import os.path
import sys
import nuke
import time
import subprocess

##custom ./python tools to import
import writeRead
import autobackdropRandomColor

## DUG Menu
nuke.menu("Nuke").addMenu("DUG/Image Tools").addCommand("AtmoTool", "nuke.createNode('atmotool.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Image Tools").addCommand("EyeTool", "nuke.createNode('eyetool.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Image Tools").addCommand("MetaGrade", "nuke.createNode('metagrade.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Image Tools").addCommand("RimLight", "nuke.createNode('rimlight.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Image Tools").addCommand("Vignette", "nuke.createNode('vignette.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Image Tools/Utilities").addCommand("PointMatte", "nuke.createNode('pointmatte.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Node Tools/Utilities").addCommand("Make Read From Write", "writeRead.writeRead()", 'alt+r')
nuke.menu("Nuke").addMenu("DUG/Script Tools/Utilities").addCommand("Create Backdrop Around Selected", "autobackdropRandomColor.autobackdropRandomColor()", 'alt+b')

## DUG Toolbar
nuke.toolbar("Nodes").addMenu("DUG", ".png")
nuke.toolbar("Nodes").addCommand("DUG/Image Tools/AtmoTool", "nuke.createNode('atmotool.gizmo')")
nuke.toolbar("Nodes").addCommand("DUG/Image Tools/EyeTool", "nuke.createNode('eyetool.gizmo')")
nuke.toolbar("Nodes").addCommand("DUG/Image Tools/MetaGrade", "nuke.createNode('metagrade.gizmo')")
nuke.toolbar("Nodes").addCommand("DUG/Image Tools/RimLight", "nuke.createNode('rimlight.gizmo')")
nuke.toolbar("Nodes").addCommand("DUG/Image Tools/Vignette", "nuke.createNode('vignette.gizmo')")
nuke.toolbar("Nodes").addCommand("DUG/Image Tools/Utilities/PointMatte", "nuke.createNode('pointmatte.gizmo')")

## Knob defaults
nuke.knobDefault("Write.create_directories", 'true')

##speed boost for larger scripts
def killViewers():
    for v in nuke.allNodes("Viewer"):
        nuke.delete(v)
nuke.addOnScriptLoad(killViewers)