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
#import labelAutobackdrop
import CameraToCard
#import expManager
import bakeExpressions
#import readManager
import unpremult_selected
#import shortcuteditor
import animatedSnap3D
#import clearExpression

## DUG Menu
nuke.menu("Nuke").addMenu("DUG/3D Tools").addCommand("Camera to Card", "CameraToCard.CameraToCard()", '')
nuke.menu("Nuke").addMenu("DUG/Image Tools").addCommand("AtmoTool", "nuke.createNode('atmotool.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Image Tools").addCommand("EyeTool", "nuke.createNode('eyetool.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Image Tools").addCommand("MetaGrade", "nuke.createNode('metagrade.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Image Tools").addCommand("RimLight", "nuke.createNode('rimlight.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Image Tools").addCommand("Vignette", "nuke.createNode('vignette.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Image Tools/Utilities").addCommand("PointMatte", "nuke.createNode('pointmatte.gizmo')")
nuke.menu("Nuke").addMenu("DUG/Node Tools/Utilities").addCommand("Make Read From Write", "writeRead.writeRead()", 'alt+r')
nuke.menu("Nuke").addMenu("DUG/Script Tools/Utilities/Backdrops").addCommand("Create Backdrop Around Selected", "autobackdropRandomColor.autobackdropRandomColor()", 'alt+b')
#nuke.menu("Nuke").addMenu("DUG/Script Tools/Utilities/Backdrops").addCommand("Create Backdrop Around Selected w Auto Label", "labelAutobackdrop.autoBackdrop()", '')
#nuke.menu("Nuke").addMenu("DUG/Script Tools/Utilities/Expressions").addCommand("Expression Manager", "expManager.main()", '')
nuke.menu("Nuke").addMenu("DUG/Script Tools/Utilities/Expressions").addCommand("Bake Expressions", "bakeExpressions.main()", '')
#nuke.menu("Nuke").addMenu("DUG/Script Tools/Utilities/Expressions").addCommand("Clear Expressions", "clearExpression.main()", '')
#nuke.menu("Nuke").addMenu("DUG/Script Tools/Utilities/Reads").addCommand("Read Manager", "readManager.main()", '')
nuke.menu("Nuke").addMenu("DUG/Script Tools/Utilities").addCommand("Unpremult Selected", "unpremult_selected.main()", '')

## DUG Toolbar
nuke.toolbar("Nodes").addMenu("DUG", "dug_logo.png")
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