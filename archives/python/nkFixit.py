import nuke
import nkCrawl as crawl
import nkAlign as align
import nkEval
import nkPanels as panel
import nkSel
import nukescripts
import os
import sys
from operator import mul

###FIXIT TOOL TEMPLATE###
#
#def toolName(nodes = None):
#  '''Description of what this tool does'''
#  nodes = getNodes(nodes)
#
#  copy tool code here


#Check if any nodes are selected
def main():
  print "this does nothing"

def getNodes(nodes=None):
  nodes = nodes if nodes else nuke.selectedNodes()
  try:
	list(nodes)
  except:
	nodes = [nodes]
  #If not
  if not nodes:
    nuke.message('Nothing is selected.')  
  return nodes

def fixUnpremult(nodes = None):
  '''Unpremults selected color correction nodes'''
  nodes = getNodes(nodes)
  # Nodes we want to effect
  node_types = set(['Grade', 'ColorCorrect', 'HueCorrect', 'HueShift', 'Saturation', 'Histogram', 'EXPTool'])
  # narrow selection by class
  nodes = [n for n in nodes if n.Class() in node_types]
  # Set the unpremult knob
  for n in nodes:
	n['unpremult'].setValue('rgba.alpha')
	# write output
	sys.stdout.write('Premult Applied to: %s\n' % (n['name'].value()))

def fixMetaMismatch(nodes = None):
  '''Fixes any duplicate reads. Helps correct faulty metadata'''
  nodes = getNodes(nodes)
  # get reads with metadata
  reads = [n for n in nkEval.byClass('Read', nodes) if 'passtype' in n.knobs()]
  for r in reads:
	fullPath = r['file'].value()
	rlcName = fullPath.split("/")[-6]
	layerName = fullPath.split("/")[-5]
	aovpass = fullPath.split("/")[-4]
	nonBtyList = set(["whiteLambert", "shadow", "ColorSep", "ambientOcclusion"])
	if aovpass not in nonBtyList:
	  passType = "beauty"
	else: 
	  passType = aovpass
	read_rlcName = r['rlcname'].value()
	read_layerName = r['layername'].value()
	read_passType = r['passtype'].value()
	if 'aovpass' in n.knobs():
	  read_aov = r['aovpass'].value()
	  if aovpass != read_aov:
		r['aovpass'].setValue(aovpass)
	if layerName != read_layerName:
	  r['layername'].setValue(layerName)
	if rlcName != read_rlcName:
	  r['rlcname'].setValue(rlcName)
	print passType
	print read_passType
	if passType != read_passType:
	  r['passtype'].setValue(passType)
	sys.stdout.write('mismatches fixed: %s\n' % (r['name'].value()))

def fixReformat(nodes = None):
  '''adds a reformat node under any reads that do not have them'''
  nodes = [n for n in getNodes(nodes) if n.Class() == 'Read']
  reformats = []
  for n in nodes:
	outputs = crawl.directOutputs(n)
	reformatted = True
	for o in outputs:
	  oclass = o.Class()
	  if oclass != 'Reformat':
		reformatted = False 
	  if oclass == 'rfxSkyController':
		reformatted = True
		break
	if reformatted == False:
	  align.moveNodeBy(n, 0, -65)
	  for o in outputs:
		if o.Class() == 'Reformat':
		  nuke.delete(o)
		  print ('cleaning up mixed outputs: ' + n.name())
		elif o.Class() == 'Crop':
		  nuke.delete(o)
		  print ('cleaning up crops: ' + n.name())
		else:
		  print ('node is reformatted correctly: ' + n.name())
	  nkSel.replace(n)
	  r = nuke.createNode('Reformat', inpanel = False)
	  r['format'].setValue("18842_turkeys_production_renderRes")
	  r['label'].setValue("Render Res")
	  r['filter'].setValue("Impulse")
	  align.alignUnder(r,n)
	  reformats.append(r)
	  sys.stdout.write('reformatting ' + n.name())
  return reformats

def fixAlphaChecked(nodes = None):
  '''Changes the output of the merge node to just RGB instead of RGBA.'''
  nodes = getNodes(nodes)       
  # Set the knob
  for n in nodes:
	n['output'].setValue('rgb')
  sys.stderr.write('RGB Output set to: %s\n' % (n['name'].value()))

def fixAlignment(nodes = None):
  '''Attempts to auto-align nodes'''
  import nkAutoAlign
  nodes = getNodes(nodes)
  nkAutoAlign.alignNode(nodes[0])

def fixArchive():
  import nuke_archive_utils
  nuke_archive_utils.load_live_frames()
  
def fixStereoSwitch():
  import nuke_node_utils
  nuke_node_utils.NodeUtils.stereo_switch()

def fixStereoCams():
  import nuke_cameras
  nuke_cameras.NukeCameras().load_camera_data()

def commonprefix(m):
    "Given a list of pathnames, returns the longest common leading component"
    if not m: return ''
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1

def labelHelper(nodes=None):
  '''helps to label colorcorrect nodes'''
  import colorsys
  nodes = getNodes()
  for n in nodes:
	p = nuke.Panel('label helper!')
	defLabel = ''
	gainValue = [1.0,1.0,1.0]
	multValue = [1.0,1.0,1.0]
	gammaValue = [1.0, 1.0, 1.0]
	brightnessChange = 'none'
	hueShift = 'none'
	satmodifier = 'none'
	changedThing = 'none'
	affectedLights = 'none'
	affectedLights_sh = ''
	commonLightType = 'none'
	satChange = 'none'
	
	knobs = n.knobs()
	
	if 'saturation' in knobs:
	  if n['saturation'].value() < 1:
		satChange = 'slight desat'
		satChange_sh = 'dsat'
		if n['saturation'].value() < .8:
		  satChange = 'desat'
	  elif n['saturation'].value() > 1:
		satChange = 'slight upsat'
		satChange_sh = '+sat'
		if n['saturation'].value() > 1.2:
		  satChange = 'upsat'
	  else:
		satChange = 'none'
	
	if n.Class() == 'Group' and 'multiAOV' in n.name():
	  channelKnobs = [n[k].value() for k in n.knobs() if '_link' in k]
	  allChs = list(channelKnobs)
	  channelKnobs = [ck.split('_ind_')[0] for ck in channelKnobs]
	  channelKnobs = [ck.split('_dir_')[0] for ck in channelKnobs]
	  affectedLights = list(set(channelKnobs))
	  rvLights = [al[::-1] for al in allChs]
	  common = commonprefix(rvLights)
	  if common:
		commonLightType = '%s' % common[::-1][-3:]
	  
	  affectedLights_sh_lst = [al.lower() for al in list(affectedLights)]
	  
	  affectedLights = ', '.join(affectedLights) if affectedLights else 'none'
	  
	  affectedLights_sh = []
	  
	  for al in affectedLights_sh_lst:
		if al.endswith('s'):
		  al = al[:-1]
		for typ in ('ibl', 'key', 'fill', 'rim'):
		  al = al.replace(typ, typ.upper())
		al = al.replace('ight', 't')
		al = al.replace('ght', 't')
		al = al.replace('left', 'l')
		al = al.replace('_', '.')
		for v in 'aeiou':
		  al = al.replace(v, '')
		affectedLights_sh.append(al.lower())
	  affectedLights_sh = '/'.join(affectedLights_sh) if len(affectedLights_sh) else ''
	  
			
	elif n.Class() == 'Grade':
	  affectedLights = 'all'
	  affectedLights_sh = ''
	if 'white' in n.knobs():
	  gainValue = n['white'].value()
	  try:
		list(gainValue)
	  except:
		gainValue = [gainValue, gainValue, gainValue]
	if 'multiply' in n.knobs():
	  multValue = n['multiply'].value()
	  try:
		list(multValue)
	  except:
		multValue = [multValue, multValue, multValue]
	if 'gamma' in n.knobs():
	  gammaValue = n['gamma'].value()
	  try:
		list(gammaValue)
	  except:
		gammaValue = [gammaValue, gammaValue, gammaValue]
	totalValue = [(gainValue[0] * multValue[0] * gammaValue[0]), (gainValue[1] * multValue[1] * gammaValue[1]), (gainValue[2] * multValue[2] * gammaValue[2])]
	lumTotal = (totalValue[0]*.20) + (totalValue[1]*.73) + (totalValue[2]*.07)
	if lumTotal > 1:
	  brightnessChange = 'brighten'
	  brightnessChange_sh = 'up'
	elif 0 < lumTotal < 1:
	  brightnessChange = 'dim'
	  brightnessChange_sh = 'dwn'
	elif lumTotal <= 0:
	  brightnessChange = 'zero out'
	  brightnessChange_sh = 'off'
	else:
	  brightnessChange = 'none'
	if len(set(totalValue)) == 1:
	  hueShift = 'none'
	else:
	  avgCast = max(totalValue)
	  
	  redness = (totalValue[0] / avgCast) if totalValue[0] > 0.0 else 0.0
	  blueness = (totalValue[1] / avgCast) if totalValue[1] > 0.0 else 0.0
	  greenness = (totalValue[2] / avgCast) if totalValue[2] > 0.0 else 0.0
	  h, saturation, v = colorsys.rgb_to_hsv(redness, blueness, greenness)
	  if 0.0 <= h <= .01:
		hueShift = 'red'
		hueShift_sh = 'r'
	  elif 0.01 < h <= 0.05:
		hueShift = 'red-orange'
		hueShift_sh = 'r/or'
	  elif 0.05 < h <= 0.085:
		hueShift = 'orange'
		hueShift_sh = 'or'
	  elif 0.085 < h <= 0.13:
		hueShift = 'ylw-orange'
		hueShift_sh = 'y/or'
	  elif 0.13 < h <= 0.177:
		hueShift = 'yellow'
		hueShift_sh = 'y'
	  elif 0.177 < h <= 0.28:
		hueShift = 'ylw-green'
		hueShift_sh = 'y/g'
	  elif 0.28 < h <= 0.37:
		hueShift = 'green'
		hueShift_sh = 'g'
	  elif 0.37 < h <= 0.445:
		hueShift = 'grn-cyan'
		hueShift_sh = 'g/cy'
	  elif 0.445 < h <= 0.525:
		hueShift = 'cyan'
		hueShift_sh = 'cy'
	  elif 0.525 < h <= 0.59:
		hueShift = 'cyn-blue'
		hueShift_sh = 'cy/b'
	  elif 0.59 < h <= 0.694:
		hueShift = 'blue'
		hueShift_sh = 'b'
	  elif 0.694 < h <= 0.792:
		hueShift = 'purple'
		hueShift_sh = 'pur'
	  elif 0.792 < h <= 0.889:
		hueShift = 'magenta'
		hueShift_sh = 'mg'
	  elif 0.889 < h <= 0.945:
		hueShift = 'mgnta-red'
		hueShift_sh = 'mg/r'
	  elif 0.945 < h <= 1.0:
		hueShift = 'red'
		hueShift_sh = 'r'
	  
	  if 0.08 <= saturation <= 0.5:
		satmodifier = 'slight'
		satmodifier_sh = '~'
	  elif 0.5 < saturation <= .68:
		satmodifier = 'somewhat'
		satmodifier_sh = '+'
	  elif 0.68 <= saturation <= 1.0:
		satmodifier = 'very'
		satmodifier_sh = '++'
	
	luminanceText = ''
	luminanceText_sh = ''
	
	if brightnessChange != 'none':
	  luminanceText = brightnessChange
	  luminanceText_sh = brightnessChange_sh
	else:
	  luminanceText = 'no change to'
	  luminanceText_sh = ''
	if affectedLights != 'none':
	  luminanceText = '%s %s' % (luminanceText, affectedLights)
	  if affectedLights_sh:
		luminanceText_sh = '%s %s' % (luminanceText_sh, affectedLights_sh)
	if commonLightType != 'none':
	  luminanceText = '%s %s' % (luminanceText, commonLightType)
	  luminanceText_sh = '%s %s' % (luminanceText_sh, commonLightType)
	if lumTotal != 1.0 and lumTotal != 0.0:
	  luminanceText = '%s by %.2f' % (luminanceText, lumTotal)
	
	masks = getMatteChannels(n)
	masks_sh_lst = [m.lower() for m in list(masks)] if masks else []
	masks_sh = []
	
	for m in masks_sh_lst:
	  for item in ('eye', 'manolo'):
		m = m.replace(item, item.upper())
	  m = m.replace('_', '.')
	  for v in 'aeiou':
		m = m.replace(v, '')
	  masks_sh.append(m.lower())
	
	maskText = ''
	maskText_sh = ''
	if masks:
	  if 'invert_mask' in n.knobs() and n['invert_mask'].value() == True:
		maskText = 'masked by all but %s' % ', '.join(masks)
	  else:
		maskText = 'masked by %s' % ', '.join(masks)
		maskText_sh = 'on %s' % '/'.join(masks_sh)
	
	colorText = ''
	colorText_sh = ''
	if satmodifier != 'none':
	  colorText = '%s %s tint' % (satmodifier, hueShift)
	  colorText_sh = '%s%s' % (satmodifier_sh, hueShift_sh)
	satText = ''
	satText_sh = ''
	if satChange != 'none':
	  satText = satChange
	  satText_sh = satChange_sh
	textValues = [txt for txt in (luminanceText, maskText, colorText, satText) if txt != '']
	textValues_sh = [txt for txt in (luminanceText_sh, maskText_sh, colorText_sh, satText_sh) if txt != '']
	p.setWidth(680)
	p.addMultilineTextInput('plain english', '\n'.join(textValues))
	p.addMultilineTextInput('your label', ' '.join(textValues_sh))
	canceled = (1 - p.show())
	if canceled:
	  return
	else:
	  n['label'].setValue(p.value('your label'))

def getMattePrefix(channels=None):
  channels = channels if channels else nuke.selectedNode().channels()
  matteChannels = [c.split('other.')[1] for c in channels if 'other.' in c]
  commonMatteNames = []
  layers = list(set([c.split('_')[0] for c in matteChannels]))
  finalGroups = []
  for l in layers:
	testChannels = [c for c in matteChannels if l in c]
	cont = True
	while cont:
	  for i in range(len(testChannels)):
		pfix = commonprefix((testChannels[i], testChannels[i-1]))
		if pfix != '':
		  commonMatteNames.append(pfix)
	  print commonMatteNames
	  testList = list(commonMatteNames)
	  commonMatteNames = list(set(commonMatteNames))
	  if len(testList) == len(commonMatteNames):
		cont = False
		finalGroups.extend(commonMatteNames)
	  else:
		cont = True
		testChannels = list(commonMatteNames)
		commonMatteNames = []
  print list(set(finalGroups))

def getMatteChannels(node=None):
  n = node if node else nuke.selectedNode()
  
  mask = None
  
  #channels that mean more work:
  
  pipeChans = ['none', 'red', 'green', 'blue', 'alpha']
  
  #check for internal mattes:
  
  mci = n['maskChannelInput'].value()
  mcm = n['maskChannelMask'].value()
  
  #set mask to internal mattes if they exist
  
  if mci not in pipeChans:
	mask = mci
	return [mask.split('other.')[1]]
  elif mcm not in pipeChans:
	mask = mcm
	return [mask.split('other.')[1]]
  else:
	pass
  
  if not mask and not n.input(1):
	return mask
  else:
	return extractMattes(node = n.input(1))

def extractMattes(node=None):
  n = node if node else nuke.selectedNode()
  channels = []
  while n.Class() == 'Dot':
	n = n.input(0)
  if n.Class() == 'matteCombiner':
	channels = [n[k].value() for k in n.knobs() if k.startswith('from') and n[k].value() != 'none']
	channels = [c.split('other.')[1] for c in channels if 'other.' in c]
  elif n.Class() == 'Group' and 'multiMatte' in n.name():
	channels = [n[k].value() for k in n.knobs() if '_label' in k]
  else:
	channels = ['something']
  return channels

def fixExpansionCrops():
  expansionNodes = nkEval.expansionNodes(crawl.mainComp())
  allNodes = list(expansionNodes)
  allNodes.extend(nkEval.byClass('Crop'))
  cropped = False
  for en in expansionNodes:
	print 'cropping %s' % en.name()
	testNode = crawl.firstNodeAboveIn(en, allNodes, distReturn=False, pipe=0)
	if testNode and testNode.Class() == 'Crop':
	  cropped = True
	  c = testNode
	else:
	  c = nuke.nodes.Crop()
	  c.setInput(0, en.input(0))
	  en.setInput(0,c)
	c['crop'].setValue(False)
	c['intersect'].setValue(True)
	c['reformat'].setValue(True)
	rf = nuke.root().format()
	c['box'].setValue((rf.x(), rf.y(), rf.width(), rf.height()))

def fixWriteCrop():
  writes = nkEval.byClass('Write', crawl.mainComp())
  for w in writes:
	print 'cropping %s' % w.name()
	inpOne = w.input(0)
	inpTwo = inpOne.input(0)
	if inpOne.Class() == 'Crop' or inpTwo.Class() == 'Crop':
	  cropped = True
	  c = list(nkEval.byClass('Crop', nodes=(inpOne, inpTwo)))[0]
	else:
	  c = nuke.nodes.Crop()
	  c.setInput(0, w.input(0))
	  w.setInput(0,c)
	c['crop'].setValue(False)
	c['intersect'].setValue(True)
	c['reformat'].setValue(True)
	rf = nuke.root().format()
	c['box'].setValue((rf.x(), rf.y(), rf.width(), rf.height()))

def fixCrops():
  fixExpansionCrops()
  fixWriteCrop()

def fixChannelCount():
  from nkPreflight import extraChannels
  import shutil

  curFile = nuke.root().name()
  newFile = curFile[:-3] + '_chFix.nk'
  shutil.copy(curFile, newFile)
  editFile = open(newFile, 'r')
  fileString = editFile.read()
  fileStringList = fileString.split(' ')

  removeThings = [c for c in extraChannels(allChannels=True, channelsUsed=True) if 'other.' in c]

  for f in list(fileStringList):
	if f in removeThings:
	  fileStringList.remove(f)
  returnString = ' '.join(fileStringList)
  editFile.close()
  return_textFile = open(newFile, 'w')
  return_textFile.write(returnString)
  return_textFile.close()

	