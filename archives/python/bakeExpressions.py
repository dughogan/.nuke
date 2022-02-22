# Bake Expressions
# By Nathan Rusch
# Updated August 23, 2010

import nuke
import re

def bakeExpressions(startFrame = nuke.root().firstFrame(), endFrame = nuke.root().lastFrame()):
	'''
	Bakes all expression-driven knobs/knob components to keyframes over given input range
	To Do:
	- Add support for multiple views
	'''

	if not nuke.selectedNodes():
		return
	for node in nuke.selectedNodes():
		for knob in node.knobs().values():
			if knob.hasExpression():
				if knob.singleValue():
					aSize = 1
				else:
					aSize = knob.arraySize()
				for index in range(aSize):
					if knob.hasExpression(index):
						anim = knob.animation(index)
						f = startFrame
						while f <= endFrame:
							knob.setValueAt(anim.evaluate(f), f, index)
							f += 1
						knob.setExpression("curve", index)
						if knob.animation(index).constant():
							knob.clearAnimated(index)


def main():
	'''
	GUI wrapper for bakeExpressions function
	'''

	input = nuke.getFramesAndViews("Range to Bake", "%d-%d" % (nuke.root().firstFrame(), nuke.root().lastFrame()))
	range = input[0]
	if not re.match("^\d+-\d+$", range):
		return
	first, last = range.split("-")
	bakeExpressions(int(first), int(last))