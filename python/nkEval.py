import nuke
import nukescripts
import _curveknob
import nkSel
import nkCrawl as crawl
import nkAlign as align

def main():
  print("this does nothing")

def extendList(classDict, dictKeys):
  '''given a dictionary of node class types, return only the nodes within the given classes'''
  keys = set([key for key in classDict if key in dictKeys])
  nList = set([n for key in keys for n in classDict[key]])
  return nList

def errors(nodes = None):
  '''return all nodes that throw errors'''
  nodes = nuke.allNodes() if nodes == None else nodes
  return set([n for n in nodes if n.hasError() == True])

def byClass(nType, nodes = None):
  '''return all nodes within a given class'''
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  nodeDict = nodeClassDict(nodes)
  return set([n for key in nodeDict for n in nodeDict[key] if key == nType])

def byClasses(nClasses, nodes = None):
  '''return all nodes of a given list of classes'''
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  nodeClasses = nodeClassDict(nodes)
  return extendList(nodeClasses, nClasses)

def nodeClassDict(nodes = None):
  '''return a dictionary in the format of {nodeClass1: node1, node2, ...}'''
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  nClasses = [(n.Class(), n) for n in nodes]
  nodeDict = {}
  for t in nClasses:
	  nodeDict[t[0]] = [n for (k,n) in nClasses if k == t[0]]
  return nodeDict

def endNodes(allNodes = None):
  '''return all nodes with no outputs and at least one input'''
  allNodes = set(crawl.mainComp()) if allNodes == None else allNodes
  writes = byClass('Write', allNodes)
  aboveNodes = set(crawl.above(writes))
  ignoreList = set(['Viewer', 'rfxStereoTools', 'ContactSheet', 'compAniCompare', 'Write'])
  return [n for n in allNodes if n not in aboveNodes and n.Class() not in ignoreList]
  
def topNodes():
  '''return all nodes with no inputs and at least one output'''
  allNodes = set(nuke.allNodes()) if allNodes == None else allNodes
  nodeDict = nodeClassDict(allNodes)
  ignoreList = set(['Viewer', 'BackdropNode', 'StickyNote'])
  nodes = [n for k in nodeDict for n in nodeDict[k] if k not in ignoreList]
  return [n for n in nodes if len(crawl.directOutputs(n)) != 0 and len(crawl.directInputs()) == 0]

def offAxis(allNodes = None):
  '''return all off-axis nodes'''
  allNodes = set(nuke.allNodes()) if allNodes == None else allNodes
  nodeDict = nodeClassDict(allNodes)
  ignoreList = set(['Viewer', 'BackdropNode', 'StickyNote', 'ContactSheet', 'Switch', 'StickyNote', 'DeepMerge', 'Camera2'])
  nodes = [n for k in nodeDict for n in nodeDict[k] if k not in ignoreList]
  return list(set([n for n in nodes for i in crawl.directInputs(n) if round(align.cardinalOffsetBetween(n, i)) != 0.0]))

def byKnobExists(knob, nodes = None):
  '''return all nodes that have the given knob'''
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  return [n for n in nodes if knob in set(n.knobs())]

def upstream(allNodes = None):
  '''return all nodes that have inputs located below themselves'''
  allNodes = set(nuke.allNodes()) if allNodes == None else allNodes
  nodeDict = nodeClassDict(allNodes)
  ignoreList = set(['Viewer', 'BackdropNode', 'StickyNote', 'ContactSheet', 'StickyNote', 'DeepMerge', 'Camera2'])
  nodes = [n for k in nodeDict for n in nodeDict[k] if k not in ignoreList]
  return [n for n in nodes for i in crawl.directInputs(n) if i and align.getXYCenter(i)[1] > align.getXYCenter(n)[1]]

def byKnobValue(knob, value, nodes = None):
  '''return all nodes that have the given value for the given knob'''
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  return [n for n in nodes for k in n.knobs() if k == knob and n[k].value() == value]

def byKnobValues(knobs, values, nodes = None):
    '''return all nodes that have the given value for the given knob'''
    nodes = set(nuke.allNodes()) if nodes == None else nodes
    nReturn = []
    for k,value in zip(knobs(), values):
            nReturn.extend(byKnobValue(k, value, nodes))
    return nReturn

def allColorManip(allNodes = None):
  '''return all grade nodes, color-corrects, hue-corrects, hueshifts, etc.'''
  allNodes = set(nuke.allNodes()) if allNodes == None else allNodes
  nodeDict = nodeClassDict(allNodes)
  nodes = extendList(nodeDict, ['Grade','ColorCorrect','HueCorrect','HueShift','Saturation'])
  return nodes

def premultedGrades(nodes = None):
  '''return all grades with unpremult set to "none"'''
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  return premulted(byClass('Grade', nodes))

def premulted(allNodes = None):
  '''return all nodes that both have an alpha and are not unpremulted'''
  allNodes = set(nuke.allNodes()) if allNodes == None else allNodes
  nodes = byKnobValue('unpremult', 'none', allColorManip(allNodes))
  rgbnodes = [n for n in nodes if n['channels'].value() == 'rgb']
  return [n for n in rgbnodes if 'rgba.alpha' in set(n.channels())]

def unlabeled(allNodes = None):
  '''return all nodes without labels'''
  nodeDict = nodeClassDict(allNodes)
  ignoreList = set(["Viewer", "Dot", "Shuffle", "Reformat", "Clamp", "Expression", "Switch", "rfxSkyController", "Unpremult", "Invert", "Copy", "Constant", "Merge2", "DeepMerge", "DeepReformat"])
  nodes = [n for k in nodeDict for n in nodeDict[k] if k not in ignoreList]
  return byKnobValue('label', '', nodes)

def checkedAlpha(nodes = None):
  '''return all merges that have "alpha" checked on input'''
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  merges = byClass('Merge2', nodes)
  rgbaMerges = byKnobValue('output', 'rgba', merges)
  return [n for n in rgbaMerges if n['operation'].value() not in ['over','under']]

def disabled(nodes = None):
  '''return a list of all disabled nodes'''
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  return byKnobValue('disable', True, nodes)

def unReformatted(nodes = None):
    '''return a list of all read nodes without a corresponding reformat node'''
    nodes = set(nuke.allNodes()) if nodes == None else nodes
    reads = [r for r in byClass('Read', nodes) if '_lit' in r['file'].getValue()]
    unreformatted = []
    for r in reads:
        children = crawl.oneDown(r)
        if len(children) > 0:
            grandChildren = crawl.oneDown(children)
            children.extend(grandChildren)
            if len(byClass('Reformat', children)) == 0:
                unreformatted.append(r)
    return unreformatted

def cropped(nodes = None):
    '''return a list of all read nodes that have crops directly below'''
    nodes = set(nuke.allNodes()) if nodes == None else nodes
    crops = byClass('Crop', nodes)
    cropped = []
    for c in crops:
        parents = crawl.oneUp(c)
        if len(parents) > 0:
            grandParents = crawl.oneUp(parents)
            parents.extend(grandParents)
            for r in byClass('Read', parents):
                cropped.append(r)
    return cropped

def noStereoOffset(nodes = None):
    '''return a list of all mask-type nodes without stereo offsets'''
    nodes = nodes if nodes else nuke.selectedNodes()
    sel = nuke.selectedNodes()
    allNodes = nodeClassDict(nodes)
    rotoNodes = byClasses(['Roto','RotoPaint','RotoPaint2'], nodes)
    print(rotoNodes)
    rampNodes = byClasses(['Ramp'], nodes)
    nReturn = list(rotoNodes)
    for roto in rotoNodes:
        try:
            nkSel.replace(roto)
            nukescripts.node_copypaste()
            r = nuke.selectedNode()
            gui = True
        except:
            r = roto
            gui = False
        defaultScript = r['curves'].toScript()
        noCurveSelected = '512'.join(defaultScript.split('576'))
        r['curves'].fromScript(noCurveSelected)
        curveSelList = r['curves'].toScript().split('512')
        for i in range(1,(len(curveSelList))):
            a = '512'.join(curveSelList[:i])
            b = '512'.join(curveSelList[i:])
            newSel = '576'.join([a,b])
            r['curves'].fromScript(newSel)
            r['stereo_offset'].setValue(5000, view='left')
            r['stereo_offset'].setValue(-5000, view='right')
        if r['stereo_offset'].value(view='left')[0] != r['stereo_offset'].value(view='right')[0]:
            nReturn.remove(roto)
            break
        if gui:
            nuke.delete(r)
    nkSel.replace(sel)
    testRampNodes = list(rampNodes)
    if len(testRampNodes) > 0:
        for r in testRampNodes:
            if r['p0'].getValue()[0] == r['p1'].getValue()[0]:
                rampNodes.remove(r)
    nReturn.extend(rampNodes)
    return nReturn

def staticReads(nodes = None):
  '''return all read nodes without %v switch'''
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  reads = byClasses(['Read', 'DeepRead'], nodes)
  staticReads = []
  return [r for r in reads if '%v' not in r['file'].value() and '_lit' in r['file'].value()]

def byLabel(name, nodes = None):
  '''return nodes with given label'''
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  namedNodes = []
  return [n for n in nodes if name in n['label'].value()]

def badStereoCams(nodes = None):
  '''return all stereoCams with mismatch BROKEN IN BOL WORKFLOW'''
  currentShot = nuke.root()['shot'].getValue()
  nodes = set(nuke.allNodes()) if nodes == None else nodes
  nReturn = []
  return [n for n in byClass('Camera2', nodes) if currentShot not in n.name() and currentShot not in n['label'].value()]
  
def mismatchMeta(allNodes = None):
  '''return all nodes with mismatched metadata BROKEN IN BOL WORKFLOW'''
  allNodes = set(nuke.allNodes()) if allNodes == None else allNodes
  nodes = [n for n in byClass('Read', allNodes) if '_lit' in n['file'].getValue()]
  rfxMeta = ['layername', 'aovpass', 'rlcname']
  return set([n for n in nodes for k in n.knobs() if k in rfxMeta and n[k].value() not in n['file'].value()])

def expansionNodes(nodes=None):
  '''return all nodes that expand the bounding box'''
  nodes = nodes if nodes else nuke.allNodes()
  expansionNodes = list(byClasses(['Dilate', 'Erode',
							  'FilterErode', 'Blur',
							  'EdgeBlur', 'Defocus',
							  'ZDefocus', 'LightWrap',
							  'Matrix', 'Glow', 'Median',
							  'VectorBlur', 'Godrays',
							  'VolumeRays', 'plateWrap',
							  'lumaGlow', 'lumaWrap',
							  'ZDefocus2']))
  expansionNodes.extend([n for n in byClass('Group') if 'lumaGlow' in n.name()])
  expansionNodes.extend([n for n in byClass('Group') if 'lumaWrap' in n.name()])
  return expansionNodes
 
def duplicateReads(allNodes = None):
  '''return all redundant read nodes, i.e. reads that are exactly the same as other reads'''
  allNodes = set(nuke.allNodes()) if allNodes == None else allNodes
  nodes = byClass('Read', allNodes)
  dupedReads = []
  allFileLocs = [n['file'].value() for n in nodes]
  return [n for n in nodes if allFileLocs.count(n['file'].value()) > 1]

def archivedReads(allNodes = None):
  '''return all reads that are not live'''
  allNodes = set(nuke.allNodes()) if allNodes == None else allNodes
  return [n for n in allNodes if n.Class() == 'Read' and 'live' not in n['file'].getValue() and '_lit' in n['file'].getValue()]