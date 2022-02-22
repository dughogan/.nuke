import nuke
import nkSel
import nkGadget
import nkCrawl
import nkAlign
import re

def addpanels():
  
  n = nuke.thisNode()
  bns = nuke.toNode('builder_dot')
  bn = nkCrawl.oneUp(bns)[0]
  
  ###Get all the incoming channels
  allChannels = n.channels()

  ###Combine the channels into common layers
  layers = list(set([channel.split('.')[0] for channel in allChannels]))
  layers.sort()

  layerTypes = []
  lightPassPre = ['_dir', '_ind']
  lightPassPost = ['dif', 'cot', 'rfl']
  for pre in lightPassPre:
	for post in lightPassPost:
	  layerTypes.append('_'.join((pre,post)))

  ###Get Light Layers
  lightLayers = []
  for lt in layerTypes:
	pattern = ('\\' + lt + '$')
	lightLayers.extend([re.sub(pattern, '', l) for l in layers if l.endswith(lt)])
	lightLayers = list(set(lightLayers))
  for emi in ('ind_emi', 'dir_emi'):
	print emi
	if emi in layers:
	  lightLayers.append(emi)
  panelLights = []
  
  for light in lightLayers:
	lp = nuke.createNode('panel_light', inpanel=False)
	for emi in ('ind_emi', 'dir_emi'):
	  if emi == light:
		lp['curLight'].setValue(light)
		lp['add_light'].execute()
		lp['curLight'].setValue(light)
		bn = lp
		panelLights.append(lp)
	for layer in layers:
	  for lt in layerTypes:
		if str(light + lt) in layer:
		  lp['curLight'].setValue(layer)
		  lp['add_light'].execute()
		  lp['curLight'].setValue(light)
	lp.setInput(0, bn)
	bns.setInput(0,lp)
	nkAlign.alignUnder(lp, bn)
	bn = lp
	panelLights.append(lp)
  
  for l in panelLights:
	
	n.addKnob(nuke.Text_Knob((l.name()+'_divOne'), ''))
	lightLabel = nuke.Text_Knob((l.name() + '_label'), '')
	lightLabel.setValue(l['curLight'].value())
	lightLabel.setFlag(nuke.STARTLINE)
	n.addKnob(lightLabel)
	mult_link = nuke.Link_Knob((l.name() + '_multLink'), 'intensity')
	mult_link.setFlag(nuke.STARTLINE)
	mult_link.makeLink(l.name(), 'multiply')
	n.addKnob(mult_link)
	
	col_link = nuke.Link_Knob((l.name() + '_colLink'), 'color')
	col_link.setFlag(nuke.STARTLINE)
	col_link.makeLink(l.name(), 'white')
	n.addKnob(col_link)


def addLight(thru=False):
  
  n = nuke.thisNode()
  light_selection = n['curLight'].value()
  if light_selection not in existingChannels():
  
	bns = nuke.toNode('builder_dot')
	bn = nkCrawl.oneUp(bns)[0]
	gns = nuke.toNode('grade_dot')
	gn = nkCrawl.oneUp(gns)[0]
	aovg = nuke.toNode('aov_grade')
	nkSel.replace(bn)

	pn = nuke.createNode('Merge2', inpanel=False)
	pn['output'].setValue('rgb')
	pn['operation'].setValue('plus')
	pn.setInput(0, bn)

	nkSel.replace(gn)
	
	chGrade = nuke.createNode('Grade', inpanel=False)
	chGrade['channels'].setExpression('%s.Achannels' % pn.name())
	chGrade['disable'].setExpression('%s.disable' % pn.name())
	chGrade.setInput(0, gn)
	
	linkGrade(chGrade, aovg)
	nkAlign.alignUnder(chGrade, gn)

	link = nuke.Link_Knob((pn.name()+'_link'), 'light')
	link.setFlag(nuke.STARTLINE)
	link.makeLink(pn.name(), 'Achannels')

	disableLink = nuke.Link_Knob((pn.name()+'_disable_lnk'), 'mute')
	disableLink.clearFlag(nuke.STARTLINE)
	disableLink.makeLink(pn.name(), 'disable')

	n.addKnob(link)
	n.addKnob(disableLink)
	
	nkSel.replace(pn)
	
	pn['Achannels'].setValue(light_selection)
  
  else:
	pass

def existingChannels(node = None):
  n = node if node else nuke.thisNode()
  channelKnobs = [n[k].value() for k in n.knobs() if '_link' in k]
  return channelKnobs
	
def linkGrade(toNode, fromNode):
  knobList = ['white', 'multiply']
  for k in knobList:
	toNode[k].setExpression('%s.%s' % (fromNode.name(), k))