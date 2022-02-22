import nuke
import nkEval
import nkAlign
import nkSel
import nkCrawl
import re

def defocus(onOff):
  #disable is opposite day!
  onOff = False if onOff == True else True  
  defoci = nkEval.byClasses(('ZDefocus', 'ZDefocus2', 'Defocus', 'ZBlur'))
  for d in defoci:
	d['disable'].setValue(onOff)

#def mblur(onOff):
  #skies = nkEval.byClass('bolSkyController')
  #for s in skies:
	#s['motion_blur_on'].setValue(onOff)

#def skySwitch(onOff):
  #onOff = 1 if onOff == True else 0 
  #switches = nkEval.byKnobExists('skySwitch')
  #if not switches:
	#switches = makeSkySwitch()
  #if switches:
	#for sw in switches:
	  #sw['which'].setValue(onOff)

def oneView(onOff):
  #disable is opposite day!
  onOff = False if onOff == True else True  
  oneViews = nkEval.byClass('OneView', nodes=nkCrawl.mainComp())
  if not oneViews:
	oneViews = makeOneView()
  for onev in oneViews:
	onev['disable'].setValue(onOff)

def setThreads(threads=8):
  nuke.tcl('set threads %s' % threads)
  return threads

def setPrev(level):
  viewers = nkEval.byClass('Viewer')
  for viewer in viewers:
	viewer['downrez'].setValue(level)

def makeOneView(node=None):
  rfxwrites = nkEval.byKnobExists('is_rfx', nodes=nkEval.byClass('Write'))
  oneViews = []
  if rfxwrites:
	for write in rfxwrites:
	  nkSel.replace(nkCrawl.oneUp(write))
	  if nuke.selectedNodes():
		onev = nuke.createNode('OneView')
		oneViews.append(onev)
  return oneViews

def makePrecompWrite():
  rfxwrites = nkEval.byKnobExists('is_rfx', nodes=nkEval.byClass('Write'))
  if rfxwrites:
	rfxwrite = rfxwrites[0]
	filename = nuke.filename(rfxwrite)
	newPath = re.sub('/comp/', '/precomp/', filename)
  return newPath

#def makeSkySwitch():
  #skies = nkEval.byClass('bolSkyController')
  #sswitches = []
  #curSel = nuke.selectedNodes()
  #if nkEval.byKnobExists('skySwitch'):
	#pass
  #else:
	#for sky in skies:
	  #nkSel.replace(sky)
	  #switch = nuke.createNode('Switch', inpanel=False)
	  #ssKnob = nuke.Boolean_Knob('skySwitch', 'sky switch', True)
	  #switch.addKnob(ssKnob)
	  #nkSel.deSelAll()
	  #constant = nuke.createNode('Rectangle')
	  #colors = avgSample(sky)
	  #bot_color = [colors[0][0], colors[1][0], colors[2][0]]
	  #top_color = [colors[0][1], colors[1][1], colors[2][1]]
	  #positionY = colors[3][1]
	  #bot_color.append(1.0)
	  #top_color.append(1.0)
	  #constant['color'].setValue(bot_color)
	  #constant['output'].setValue('rgba')
	  #rf = nuke.root().format()
	  #constant['area'].setValue((rf.x(), rf.y(), rf.width(), rf.height()))
	  #constant['ramp'].setValue('smooth0')
	  #constant['color0'].setValue(top_color)
	  #constant['p0'].setValue((0,rf.height()))
	  #constant['p1'].setValue((0,positionY))
	  #switch.setInput(1,constant)
	  #switch['which'].setValue(1)
	  #nkAlign.alignUnder(switch, sky)
	  #nkAlign.alignRight(constant, switch)
	  #sswitches.append(sky)
  #nkSel.replace(curSel)
  #return sswitches

def avgSample(node, samples=25):
  mblurSet = False
  ###get this node
  n = node if node else nuke.selectedNode()
  if node.Class() == 'bolSkyController' and node['motion_blur_on'].value():
	node['motion_blur_on'].setValue(False)
	mblurSet = True
  ###get sampler position
  dx = n.width()
  dy = n.height()
  xpos = 0
  ypos = 0
  divisionsH = samples
  divisionsW = samples
  divW = dx / divisionsH
  divH = dy / divisionsW
  positionList = [((ix*divW), (iy*divH)) for iy in range(0,(divisionsH+1)) for ix in range(0,(divisionsW+1))]
  
  reds = []
  blues = []
  greens = []       
  positions = list(positionList)
  for pos in positionList:
	xpos, ypos = pos
	ch_r = n.sample('rgba.red', xpos, ypos)
	if ch_r != float(0):
	  reds.append(ch_r)
	ch_g = n.sample('rgba.green', xpos, ypos)
	if ch_g != float(0):
	  greens.append(ch_g)
	ch_b = n.sample('rgba.blue', xpos, ypos)
	if ch_b != float(0):
	  blues.append(ch_b)
	if ch_r == 0.0 and ch_g == 0.0 and ch_r == 0.0:
	  positions.remove(pos)
  
  rmp = len(reds)/8
  redAvg_a = sum(reds[:rmp]) / len(reds[:rmp])
  redAvg_b = sum(reds[-rmp:]) / len(reds[-rmp:])
  gmp = len(greens)/8
  greenAvg_a = sum(greens[:gmp]) / len(greens[:gmp])
  greenAvg_b = sum(greens[-gmp:]) / len(greens[-gmp:])
  bmp = len(blues)/8
  blueAvg_a = sum(blues[:bmp]) / len(blues[:bmp])
  blueAvg_b = sum(blues[-bmp:]) / len(blues[-bmp:])
  if mblurSet:
	node['motion_blur_on'].setValue(True)
  
  return [(redAvg_a, redAvg_b), (greenAvg_a, greenAvg_b), (blueAvg_a, blueAvg_b), positions[0]]
  