import nuke
import nkShowDefs
import nkEval
import nkReport
import nukescripts
import nkSel
import nkCrawl
import nkAutoAlign
import nkAlign
import os
import re
from nuke_tools import node_utils


def main():
  print "this does nothing"

def simpleRV():
    n = nuke.selectedNode()
    f = n['first'].value()
    l = n['last'].value()
    b = 1
    v = 'left'
    node_utils.rv_this(n, f, l, b, v)

def alt(nodes = None):
  nodes = nodes if nodes else nuke.selectedNodes()
  print nodes
  if 0 < len(nodes) < 2:
	altNode(nodes[0])
  else:
	altGrp(nodes)

def altNode(node = None):
  addAltView()
  writeAlt()
  node = node if node else nuke.selectedNode()
  info = nkAutoAlign.nodeInfo(node)
  if info['inOutType'] != 'SISO':
	nuke.message('this tool requires a node with exactly one input' 
				 '\nand one output. You can hook up masks later')
  else:
	curSel = nuke.selectedNodes()
	d = dot(node)
	nkSel.replace(node)
	nukescripts.node_copypaste()
	copyNode = nuke.selectedNode()
	nkSel.replace(curSel)
	xprime, yprime = nkAlign.getXYCenter(d)
	if info['sandwichCardinal'] in set(['N', 'S']):
	  xview = xprime + 200
	  yview = yprime
	  xcopy = info['x'] + 200
	  ycopy = info['y']
	  xjoin = info['x']
	  yjoin = info['y'] + 100
	  xdot = xjoin + 200
	  ydot = yjoin
	else:
	  xview = xprime
	  yview = yprime + 200
	  xcopy = info['x']
	  ycopy = info['y'] + 200
	  xjoin = info['x'] + 100
	  yjoin = info['y']
	  xdot = xjoin
	  ydot = yjoin + 200
	altView = nuke.nodes.OneView()
	altView['view'].setValue('left_alt')
	altView.setInput(0, d)
	copyNode.setInput(0, altView)
	altDot = nuke.nodes.Dot()
	altDot.setInput(0, copyNode)
	altJoin = nuke.nodes.JoinViews()
	altJoin.setInput(0, node)
	altJoin.setInput(1, node)
	altJoin.setInput(2, altDot)
	nkAlign.moveNodeTo(altView, xview, yview)
	nkAlign.moveNodeTo(altDot, xdot, ydot)
	nkAlign.moveNodeTo(altJoin, xjoin, yjoin)
	nkAlign.moveNodeTo(copyNode, xcopy, ycopy)
	outp = info['outputs'][0]
	for i, inp in enumerate(nkCrawl.directInputs(outp)):
	  if inp == node:
		outp.setInput(i, altJoin)
	
def altGrp(nodes = None):
  addAltView()
  writeAlt()
  nodes = nodes if nodes else nuke.selectedNodes()
  direction = nkAutoAlign.mindRead(nodes)
  aboveNodes = []
  aboveNodes = [(len(nkCrawl.above(n)), n) for n in nodes]
  bottomNode = max(aboveNodes)[1]
  bottomInfo = nkAutoAlign.nodeInfo(bottomNode)
  topNode = min(aboveNodes)[1]
  topInfo = nkAutoAlign.nodeInfo(topNode)
  d = dot(topNode)
  xprime, yprime = nkAlign.getXYCenter(d)
  if direction == ['Y']:
	xview = xprime + 200
	yview = yprime
	xjoin = bottomInfo['x']
	yjoin = bottomInfo['y'] + 100
	xdot = xjoin + 200
	ydot = yjoin
  else:
	xview = xprime
	yview = yprime + 200
	xjoin = bottomInfo['x'] + 100
	yjoin = bottomInfo['y']
	xdot = xjoin
	ydot = yjoin + 200
  altView = nuke.nodes.OneView()
  altView['view'].setValue('left_alt')
  altView.setInput(0, d)
  altDot = nuke.nodes.Dot()
  altDot.setInput(0, altView)
  altJoin = nuke.nodes.JoinViews()
  altJoin.setInput(0, bottomNode)
  altJoin.setInput(1, bottomNode)
  altJoin.setInput(2, altDot)
  nkAlign.moveNodeTo(altView, xview, yview)
  nkAlign.moveNodeTo(altDot, xdot, ydot)
  nkAlign.moveNodeTo(altJoin, xjoin, yjoin)
  outp = bottomInfo['outputs'][0]
  for i, inp in enumerate(nkCrawl.directInputs(outp)):
	if inp == bottomNode:
	  outp.setInput(i, altJoin)

def addAltView():
  nuke.root()['views'].fromScript('{left ""}\n{right ""}\n{left_alt "#FF00FF"}')
  nuke.root()['views_colours'].setValue(True)

def writeAlt():
  if not nkEval.byKnobExists('altWrite'):
	allNodes = [n for n in nuke.allNodes() if n.Class() == 'Write']
	aboveNodes = []
	aboveNodes = [(len(nkCrawl.above(n)), n) for n in allNodes]
	bottomNode = max(aboveNodes)[1]
	d = dot(bottomNode)
	x, y = nkAlign.getXYCenter(d)
	altWrite = nuke.nodes.Write()
	altWrite['file'].setValue('/data/entertainment/18842_turkeys_production/cg/sequences/'
							  'sq[value root.seq]/sh[value root.shot]/images/comp/'
							  '[value root.seq]_[value root.shot]_v[value root.scriptVersion]/'
							  '[value root.seq]_[value root.shot]_v[value root.scriptVersion]_a.%04d.dpx'
							   )
	altWrite['disable'].setValue(True)
	altWrite['channels'].setValue('rgb')
	altWrite['colorspace'].setValue('sRGB')
	altWrite['views'].setValue('left_alt')
	altWrite['file_type'].setValue('dpx')
	altWrite['datatype'].setValue('10 bit')
	altWrite['bigEndian'].setValue(True)
	altWrite['label'].setValue('ALT')
	altWrite.addKnob(nuke.Text_Knob('altWrite', 'write to alt view'))
	altView = nuke.nodes.OneView()
	altView['view'].setValue('left_alt')
	nkAlign.moveNodeTo(altView, x - 200, y)
	nkAlign.moveNodeTo(altWrite, x - 200, y + 50)
	altWrite.setInput(0, altView)
	altView.setInput(0, d)

def holdFrames(keyframes=None):
  n = nuke.createNode('FrameHold', inpanel=False)
  n['first_frame'].setAnimated()
  if not keyframes:
	keyframeString = nuke.getInput('keyframes').replace(',',' ')
	keyframes = keyframeString.split()
  numKeys = len(keyframes)
  for i in range(0,numKeys):
	key = float(keyframes[i])
	prevKey = float(keyframes[i-1]) if i > 0 else float(keyframes[i])
	n['first_frame'].setValueAt(key, (key+1))
	n['first_frame'].setValueAt(key, key)
	n['first_frame'].setValueAt(prevKey,(key-1))
  fhAnims = n['first_frame'].animation(0)
  for key in fhAnims.keys():
	key.interpolation = nuke.CONSTANT

def holdFramesEven(keyframes=None):
  n = nuke.createNode('FrameHold', inpanel=False)
  n['first_frame'].setAnimated()
  if not keyframes:
	keyframeString = nuke.getInput('keyframes').replace(',',' ')
	keyframes = keyframeString.split()
  numKeys = len(keyframes)
  fframe = nuke.root()['first_frame'].value()
  lframe = nuke.root()['last_frame'].value()
  interval = ((int(lframe) - int(fframe)) / numKeys)
  for i in range(0,numKeys):
	key = float(keyframes[i])
	prevKey = float(keyframes[i-1]) if i > 0 else float(keyframes[i])
	n['first_frame'].setValueAt(key, ((interval*i)+1))
	n['first_frame'].setValueAt(key, (interval*i))
	n['first_frame'].setValueAt(prevKey,((interval*i)-1))
  fhAnims = n['first_frame'].animation(0)
  for key in fhAnims.keys():
	key.interpolation = nuke.CONSTANT

def dot(node = None, mode = 'onB', avg=True):
  node = node if node else nuke.selectedNode()
  info = nkAutoAlign.nodeInfo(node)
  d = nuke.nodes.Dot()
  d.setInput(0, info['inputs'][0])
  node.setInput(0, d)
  if avg:
	x, y = nkAlign.getAveragePosition([node, info['inputs'][0]])
	nkAlign.moveNodeTo(d, x, y)
  else:
	nkAlign.alignAbove(d, node)
  return d

def swap(nodes = None):
  nodes = nodes if nodes else [nuke.selectedNodes()[0], nuke.selectedNodes()[1]]
  flip = nodes[0]
  flop = nodes[1]
  flipInfo = nkAutoAlign.nodeInfo(flip)
  flopInfo = nkAutoAlign.nodeInfo(flop)
  flipConnect = []
  flopConnect = []
  for i, n in enumerate(flipInfo['inputs']):
	if n != flop:
	  flopConnect.append((flop, n, i))
	print (flip, n, i)
  for i, n in enumerate(flopInfo['inputs']):
	if n != flip:
	  flipConnect.append((flip, n, i))
	print (flop, n, i)
  for n in flipInfo['outputs']:
	for i, inp in enumerate(nkCrawl.directInputs(n)):
	  if inp == flip and n != flop:
		flopConnect.append((n, flop, i))
	  elif inp == flip and n == flop:
		flopConnect.append((flip, flop, i))
  for n in flopInfo['outputs']:
	for i, inp in enumerate(nkCrawl.directInputs(n)):
	  if inp == flop and n != flip:
		flipConnect.append((n, flip, i))
	  elif inp == flop and n == flip:
		flopConnect.append((flop, flip, i))
  print flipConnect
  print flopConnect
  for i in range(0,flip.inputs()):
	flip.setInput(i, None)
  for i in range(0,flop.inputs()):
	flop.setInput(i, None)
  for outp, inp, i in flopConnect:
	outp.setInput(i, inp)
  for outp, inp, i in flipConnect:
	outp.setInput(i, inp)
  nkAlign.moveNodeTo(flip, flopInfo['x'], flopInfo['y'])
  nkAlign.moveNodeTo(flop, flipInfo['x'], flipInfo['y'])

def shrinkWrap(nodes = None):
  nodes = nodes if nodes else nuke.selectedNodes()
  sel = nuke.selectedNodes()
  nkSel.deSelAll()
  bdList = nkCrawl.getBDList(nodes[-1])
  if len(bdList) > 0:
	bdn = bdList[-1]
	bdn.selectNodes()
	xmin, ymin, xmax, ymax = nkAlign.getBBGrp(nuke.selectedNodes())
	left, top, right, bottom = (-50, -120, 50, 50) 
	xmin += left 
	ymin += top 
	xmax += right 
	ymax += bottom 
	bdn['xpos'].setValue(xmin)
	bdn['ypos'].setValue(ymin)
	bdn['bdheight'].setValue(ymax - ymin)
	bdn['bdwidth'].setValue(xmax - xmin)
  nkSel.replace(sel)

def expandBD(nodes = None):
  nodes = nodes if nodes else nuke.selectedNodes()
  sel = nuke.selectedNodes()
  if len(nodes) == 1:
	shrinkWrap(nodes)
  else:
	sel = nuke.selectedNodes()
	nkSel.deSelAll()
	bdList = nkCrawl.getBDList(nodes[-1])
	if len(bdList) > 0:
	  bdn = bdList[-1]
	  bdn.selectNodes()
	  nodes.extend(nuke.selectedNodes())
	  xmin, ymin, xmax, ymax = nkAlign.getBBGrp(nodes)
	  left, top, right, bottom = (-50, -120, 50, 50)
	  xmin += left 
	  ymin += top 
	  xmax += right 
	  ymax += bottom 
	  bdn['xpos'].setValue(xmin)
	  bdn['ypos'].setValue(ymin)
	  bdn['bdheight'].setValue(ymax - ymin)
	  bdn['bdwidth'].setValue(xmax - xmin)
  nkSel.replace(sel)

def expandContract(direction, expCon, amt = .1, nodes = None):
  '''expands a set of nodes in a given direction'''
  nodes = nodes if nodes else nuke.selectedNodes()
  if direction in ('left', 'right', 'up', 'down'):
	graphNodes = [n for n in nodes if n.Class() != 'BackdropNode']
	backdropNodes = [n for n in nodes if n.Class() == 'BackdropNode']
	xmin, ymin, xmax, ymax = nkAlign.getBBGrpCenters(nodes)
	
	
	if expCon == 'expand':
	  amt = 1 + amt
	else:
	  amt = 1 - amt
	if direction == 'down':
	  total = ymax - ymin
	  target = (total * amt) - total
	  offsetter = 1
	  anchor = ymin
	
	if direction == 'up':
	  total = ymax - ymin
	  target = -1 * ((total * amt) - total)
	  offsetter = 1
	  anchor = ymax

	if direction == 'left':
	  total = xmax - xmin
	  target = -1 * ((total * amt) - total)
	  offsetter = 0
	  anchor = xmax
	
	if direction == 'right':
	  total = xmax - xmin
	  target = (total * amt) - total
	  offsetter = 0
	  anchor = xmin
	
	if total == 0:
	  
	  pass
	
	else:
	  
	  for n in graphNodes:
		offAxis = nkAlign.getXYCenter(n)[offsetter]
		offset = abs(offAxis - anchor)
		offsetRatio = float(offset) / float(total)
		offsetBy = target * offsetRatio
		n[('xpos', 'ypos')[offsetter]].setValue(int(n[('xpos', 'ypos')[offsetter]].getValue() + offsetBy))
	  
	  for bn in backdropNodes:
		if direction == 'down' or direction == 'up':
		  offsetTop = abs(bn['ypos'].getValue() - anchor)
		  otRatio = offsetTop / total
		  offsetBottom = abs((bn['ypos'].getValue() + bn['bdheight'].getValue()) - anchor)
		  obRatio = offsetBottom / total
		  
		  offsetTopBy = target * otRatio
		  offsetBottomBy = (target * obRatio) - offsetTopBy
		  
		  bn['ypos'].setValue(int(bn['ypos'].getValue() + offsetTopBy))
		  bn['bdheight'].setValue(int(bn['bdheight'].getValue() + offsetBottomBy))
		  
		if direction == 'left' or direction == 'right':
		  offsetLeft = abs(bn['xpos'].getValue() - anchor)
		  olRatio = offsetLeft / total
		  offsetRight = abs((bn['xpos'].getValue() + bn['bdwidth'].getValue()) - anchor)
		  orRatio = offsetRight / total
		  
		  offsetLeftBy = target * olRatio
		  offsetRightBy = (target * orRatio) - offsetLeftBy
		  
		  bn['xpos'].setValue(int(bn['xpos'].getValue() + offsetLeftBy))
		  bn['bdwidth'].setValue(int(bn['bdwidth'].getValue() + offsetRightBy))
  
  elif direction == 'yaxis':
	expandContract('up', expCon, (float(amt)/2.0), nodes)
	expandContract('down', expCon, (float(amt)/2.0), nodes)
  elif direction == 'xaxis':
	expandContract('left', expCon, (float(amt)/2.0), nodes)
	expandContract('right', expCon, (float(amt)/2.0), nodes)
  elif direction == 'botright':
	expandContract('left', expCon, amt, nodes)
	expandContract('up', expCon, amt, nodes)
  elif direction == 'botleft':
	expandContract('right', expCon, amt, nodes)
	expandContract('up', expCon, amt, nodes)
  elif direction == 'topleft':
	expandContract('right', expCon, amt, nodes)
	expandContract('down', expCon, amt, nodes)
  elif direction == 'topleft':
	expandContract('right', expCon, amt, nodes)
	expandContract('down', expCon, amt, nodes)
  elif direction == 'topright':
	expandContract('left', expCon, amt, nodes)
	expandContract('down', expCon, amt, nodes)
  elif direction == 'center':
	expandContract('left', expCon, (float(amt)/2.0), nodes)
	expandContract('right', expCon, (float(amt)/2.0), nodes)
	expandContract('up', expCon, (float(amt)/2.0), nodes)
	expandContract('down', expCon, (float(amt)/2.0), nodes)
  else:
	pass

def getVersions():
  fullShotNum, seqNum, shotNum, write = getShotFromWrite()
  fileName = nuke.filename(write)
  verSearch = re.search(r'v\d\d\d', fileName)
  verWithV = verSearch.group()
  verNum = re.search(r'\d\d\d', verWithV).group()
  vers = [str(v).zfill(3) for v in range(1,int(verNum))]
  vers.append(verNum)
  vers.reverse()
  print vers
  fframe = int(nuke.root()['first_frame'].value())
  lframe = int(nuke.root()['last_frame'].value())
  bdName = ('%s_versions_backdrop' % shotNum)
  exBackdrop = nuke.toNode(bdName)
  if exBackdrop:
	wPos = list(nkAlign.getXYPos(exBackdrop))
	wPos[0] += 50
	wPos[1] += 100
	nuke.delete(exBackdrop)
	exBackdrop = True
  else:
	wPos = list(nkAlign.getXYCenter(write))
	wPos[0] += 200
  firstRun = True
  reads = []
  for ver in vers:
	nodeName = ('%s_v%s_comp' % (shotNum, ver))
	exNode = nuke.toNode(nodeName)
	print (seqNum, shotNum, ver)
	nodePath = nkShowDefs.compFramePath(seq = seqNum, shot = shotNum, ver = ver)
	print nodePath
	nodePath = nodePath if nodePath else 'noFileFound'
	if exNode: nuke.delete(exNode)
	r = nuke.nodes.Read()
	if exBackdrop:
	  nkAlign.moveNodeCorner(r, wPos[0], wPos[1])
	else:
	  nkAlign.moveNodeTo(r, wPos[0], wPos[1])
	r['name'].setValue(nodeName)
	r['first'].setValue(fframe)
	r['last'].setValue(lframe)
	r['file'].setValue(nodePath)
	if firstRun:
	  r['on_error'].setValue(1)
	else:
	  r['on_error'].setValue(3)
	r['label'].setValue(ver)
	reads.append(r)
	wPos[0] += 120
	if firstRun:
	  wPos[0] += 50
	  firstRun = False
  finalReads = list(reads)
  for read in reads:
	if read.hasError():
	  nuke.delete(read)
	  finalReads.remove(read)
  bdn = wrapBackdrop(wrapNodes=finalReads)
  bdn['name'].setValue(bdName)
  bdn['label'].setValue('%s Versions\n\n          CURRENT         |        PREVIOUS' % shotNum)
  bdn['note_font_size'].setValue(16)
  bdn['note_font'].setValue('DejaVu Sans Bold')

def getColorKeys():
  fullShotNum, seqNum, shotNum, write = getShotFromWrite()
  fileName = nuke.filename(write)
  fframe = 1
  lframe = 1
  bdName = ('%s_ColorKeys_backdrop' % shotNum)
  exBackdrop = nuke.toNode(bdName)
  if exBackdrop:
	wPos = list(nkAlign.getXYPos(exBackdrop))
	wPos[0] += 50
	wPos[1] += 100
	nuke.delete(exBackdrop)
	exBackdrop = True
  else:
	wPos = list(nkAlign.getXYCenter(write))
	wPos[0] += 200
	wPos[1] += 265
  firstRun = True
  reads = []
  colorKeyPath = nkShowDefs.colorKeyPath(seq=seqNum, base=True)
  ckeys = [cs for cs in os.listdir(colorKeyPath) if cs[-3:] in ('exr','tif','jpg')]
  keyVal = 0
  for ckey in ckeys:
	keyVal += 1
	nodeName = '%s_KEY_%s' % (seqNum, keyVal)
	exNode = nuke.toNode(nodeName)
	nodePath = '%s%s' % (colorKeyPath, ckey)
	print nodePath
	nodePath = nodePath if nodePath else 'noFileFound'
	if exNode: nuke.delete(exNode)
	r = nuke.nodes.Read()
	if exBackdrop:
	  nkAlign.moveNodeCorner(r, wPos[0], wPos[1])
	else:
	  nkAlign.moveNodeTo(r, wPos[0], wPos[1])
	r['name'].setValue(nodeName)
	r['first'].setValue(fframe)
	r['last'].setValue(lframe)
	r['file'].setValue(nodePath)
	r['label'].setValue('COLOR KEY')
	reads.append(r)
	wPos[0] += 120
  finalReads = list(reads)
  bdn = wrapBackdrop(wrapNodes=finalReads)
  bdn['name'].setValue(bdName)
  bdn['label'].setValue('%s Color Keys' % seqNum)
  bdn['note_font_size'].setValue(16)
  bdn['note_font'].setValue('DejaVu Sans Bold')

def getContactSheet():
  fullShotNum, seqNum, shotNum, write = getShotFromWrite()
  fileName = nuke.filename(write)
  fframe = 1
  lframe = 1
  bdName = ('%s_ContactSheet_backdrop' % shotNum)
  exBackdrop = nuke.toNode(bdName)
  if exBackdrop:
	wPos = list(nkAlign.getXYPos(exBackdrop))
	wPos[0] += 50
	wPos[1] += 100
	nuke.delete(exBackdrop)
	exBackdrop = True
  else:
	wPos = list(nkAlign.getXYCenter(write))
	wPos[0] += 0
	wPos[1] += 200
  firstRun = True
  reads = []
  contactPath = nkShowDefs.contSheetPath(seq=seqNum, base=True)
  ckeys = [cs for cs in os.listdir(contactPath) if cs[-3:] in ('exr','tif','jpg')]
  ckeys.insert(0,'ALL')
  picked = nkShowDefs.getFromPulldown(ckeys, 'Contact Sheet')
  if picked == 'ALL':
	ckeys = ckeys[1:]
  else:
	ckeys = [picked]
  keyVal = 0
  for ckey in ckeys:
	keyVal += 1
	nodeName = '%s_SHEET_%s' % (seqNum, keyVal)
	exNode = nuke.toNode(nodeName)
	nodePath = '%s%s' % (contactPath, ckey)
	print nodePath
	nodePath = nodePath if nodePath else 'noFileFound'
	if exNode: nuke.delete(exNode)
	r = nuke.nodes.Read()
	if exBackdrop:
	  nkAlign.moveNodeCorner(r, wPos[0], wPos[1])
	else:
	  nkAlign.moveNodeTo(r, wPos[0], wPos[1])
	r['name'].setValue(nodeName)
	r['first'].setValue(fframe)
	r['last'].setValue(lframe)
	r['file'].setValue(nodePath)
	r['label'].setValue('CONTACT SHEETS')
	reads.append(r)
	wPos[1] += 120
  finalReads = list(reads)
  bdn = wrapBackdrop(wrapNodes=finalReads)
  bdn['name'].setValue(bdName)
  bdn['label'].setValue('%s Contact Sheets' % seqNum)
  bdn['note_font_size'].setValue(16)
  bdn['note_font'].setValue('DejaVu Sans Bold')

def getLatestAni():
  fullShotNum, seqNum, shotNum, write = getShotFromWrite()
  animFile = nkShowDefs.aniPath(seq=seqNum, shot=shotNum, getLatest=True)
  if animFile:
	wPos = list(nkAlign.getXYCenter(write))
	wPos[0] -= 200
	filePath = (animFile)
	print filePath
	nodeName = ('%s_HERO_ANI' % fullShotNum)
	bdname = ('%s_HERO_ANI_Backdrop' % fullShotNum)
	exBackdrop = nuke.toNode(bdname)
	exNode = nuke.toNode(nodeName)
	if exBackdrop and exNode:
	  r = exNode
	  bdn = exBackdrop
	elif exNode and not exBackdrop: 
	  nuke.delete(exNode)
	  r = nuke.nodes.Read()
	  nkAlign.moveNodeTo(r, wPos[0], wPos[1])
	  bdn = wrapBackdrop(wrapNodes=[r])
	elif exBackdrop and not exNode:
	  r = nuke.nodes.Read()
	  xpos, ypos = nkAlign.getXYPos(exBackdrop)
	  nkAlign.moveNodeCorner(r, (xpos+50), (ypos+100))
	  bdn = wrapBackdrop(bdNode=exBackdrop, wrapNodes=[r])
	else:
	  r = nuke.nodes.Read()
	  nkAlign.moveNodeTo(r, wPos[0], wPos[1])
	  bdn = wrapBackdrop(wrapNodes=[r])
	r['name'].setValue(nodeName)
	loadFullFrames([r])
	r['file'].setValue(filePath)
	r['label'].setValue(('%s HERO ANI' % fullShotNum))
	bdn['name'].setValue(bdname)
	bdn['label'].setValue('HERO ANI \n%s' % fullShotNum)
	bdn['note_font_size'].setValue(16)
	bdn['note_font'].setValue('DejaVu Sans Bold')

def wrapBackdrop(bdNode=None, wrapNodes=None):
  wrapNodes = wrapNodes if wrapNodes else nuke.selectedNodes()
  bdn = bdNode if bdNode else nuke.nodes.BackdropNode()
  xmin, ymin, xmax, ymax = nkAlign.getBBGrp(wrapNodes)
  left, top, right, bottom = (-50, -100, 50, 50)
  xmin += left
  ymin += top
  xmax += right
  ymax += bottom
  bdn['xpos'].setValue(xmin)
  bdn['ypos'].setValue(ymin)
  bdn['bdheight'].setValue(ymax - ymin)
  bdn['bdwidth'].setValue(xmax - xmin)
  return bdn

def loadFullFrames(nodes = None):
  nodes = nodes if nodes else nuke.selectedNodes()
  root = nuke.root()
  first = int(root['first_frame'].value())
  last = int(root['last_frame'].value())
  reads = nkEval.byClass('Read', nodes)
  for r in reads:
	r['first'].setValue(first)
	r['last'].setValue(last)

def getShotFromWrite():
  writes = [w for w in nkEval.byClass('Write') if 'rfxWrite' in w.name() and w['disable'].value()==False]
  write = writes[0]
  path = nuke.filename(write)
  fullShotNum, seqNum, shotNum = nkShowDefs.getShotFromPath(path)
  return (fullShotNum, seqNum, shotNum, write)

def loadRead(node=None, currentShot=False):
  try:
	if nuke.selectedNode().Class() == 'Read' and not node:
	  node = nuke.selectedNode()
  except:
	pass
  node = node if node else nuke.createNode('Read', inpanel=False)
  if currentShot:
	fullShotNum, seqNum, shotNum, write = nkShowDefs.getShotFromPath(nuke.filename(nuke.root()))
  else:
	fullShotNum, seqNum, shotNum, write = (None, None, None, None)
  path = nkShowDefs.getFilePath(seqNum, shotNum)
  if 'contact' not in path and 'colorKey' not in path:
	fframe, mframe, lframe = nkShowDefs.getAvailFrames(path)
  else:
	fframe, mframe, lframe = (1,1,1)
  node['file'].setValue(path)
  node['first'].setValue(fframe)
  node['last'].setValue(lframe)
  
def loadReadCurrent():
  loadRead(currentShot=True)