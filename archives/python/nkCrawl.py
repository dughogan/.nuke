import nuke
import nkEval as nke
import nkAlign
import nkSel

def main():
    '''retained for legacy'''
    print ('this does nothing')

def directOutputs(thisNode, pipe=None):
    '''returns a list of nodes that thisNode outputs to directly (not via expressions)'''
    dependNodes = thisNode.dependent(nuke.INPUTS)
    if pipe == None:
        return [n for n in dependNodes if n.Class() != 'Viewer']
    else:
        return [n for n in dependNodes if n.Class() != 'Viewer' and n.input(pipe) == thisNode]

def directInputs(thisNode):
    '''returns a list of nodes output to thisNode directly (not via expressions)'''
    dependNodes = thisNode.dependencies(nuke.INPUTS)
    return [d for d in dependNodes if d.Class() != 'Viewer']
  
def expOutputs(thisNode):
    '''returns a list of nodes that thisNode outputs through expressions'''
    dependNodes = thisNode.dependent(nuke.EXPRESSIONS)
    return [d for d in dependNodes if d.Class() != 'Viewer']

def expInputs(thisNode):
    '''returns a list of nodes that this node recieves information from through expressions'''
    dependNodes = thisNode.dependencies(nuke.EXPRESSIONS)
    return dependNodes

def oneUp(nodes=None, pipe=None):
    '''returns a list of nodes that are one level up-chain from the given node(s)'''
    nodes = nodes if nodes else nuke.selectedNodes()
    try:
        list(nodes)
    except:
        nodes = [nodes]
    if pipe == None:
        return [inNode for n in nodes for inNode in directInputs(n)]
    else:
        return [n.input(pipe) for n in nodes if n.input(pipe)]
  
def oneDown(nodes=None, pipe=None):
    '''returns a list of nodes that are one level down-chain from the given node(s)'''
    nList = []
    nodes = nodes if nodes else nuke.selectedNodes()
    try:
        list(nodes)
    except:
        nodes = [nodes]
    return [outNode for n in list(nodes) for outNode in list(directOutputs(n, pipe=pipe))]

def above(nodes=None, distReturn=False, pipe=None):
    '''returns a list of all nodes that are up-chain from the given node(s)'''
    nodes = nodes if nodes else nuke.selectedNodes()
    try:
        list(nodes)
    except:
        nodes = [nodes]
    aboveNodes = []
    distances = []
    dist=0
    while len(nodes) > 0:
	
        newNodes = oneUp(nodes, pipe=pipe)
        dist += 1
        new = filter(lambda a: a not in aboveNodes, newNodes)
        if len(new) == 0:
            break
        for n in new:
            if n not in aboveNodes:
                aboveNodes.append(n)
                distances.append(dist)
        nodes = new
    if distReturn:
        aboveNodes = zip(aboveNodes, distances)
    return aboveNodes
  
def below(nodes=None, distReturn=False, pipe=None):
    '''returns a list of all nodes that are up-chain from the given node(s)'''
    nodes = nodes if nodes else nuke.selectedNodes()
    try:
        list(nodes)
    except:
        nodes = [nodes]
    belowNodes = []
    distances = []
    dist=0
    while len(nodes) > 0:
        newNodes = oneDown(nodes, pipe=pipe)
        new = filter(lambda a: a not in belowNodes, newNodes)
        if len(new) == 0:
            break
        for n in new:
            if n not in belowNodes:
                belowNodes.append(n)
                distances.append(dist)
        nodes = new
        dist += 1
        if distReturn:
            aboveNodes = zip(aboveNodes, distances)
        return belowNodes

def firstCommonDesc(nodes=None, pipe=None):
    '''returns the first down-chain node common to the given nodes (NOT IMPLEMENTED)'''
    nodes = nodes if nodes else nuke.selectedNodes()
    nodeLists = [below(n, pipe=pipe) for n in nodes]
    if len(nodeLists) > 1:
        intSet = set(nodeLists[0])
        for nl in nodeLists[1:]:
            intSet.intersection_update(nl)
        tupList = [(len(above(n, pipe=pipe)),n) for n in intSet]
        tupList.sort()
        if tupList:
            return tupList[0][1]
        else:
            return []
    else:
        return []
	
def distBtwn(anode, bnode, pipe=None):
    '''returns the connected distance between two nodes'''
    anodeAbove = above(anode, pipe=pipe)
    bnodeAbove = above(bnode, pipe=pipe)
    dist = None
    if anode in bnodeAbove:
        aboveTups = above(bnode, distReturn=True, pipe=pipe)
        aboveTups.sort(key=lambda x: x[1])
        for distTup in aboveTups:
          if anode == distTup[0]:
            dist = distTup[1]
    elif bnode in anodeAbove:
        aboveTups = above(anode, distReturn=True, pipe=pipe)
        aboveTups.sort(key=lambda x: x[1])
        for distTup in above(anode, distReturn=True, pipe=pipe):
          if bnode == distTup[0]:
            dist = distTup[1]
    else:
        commonDesc = firstCommonDesc((anode, bnode))
        if commonDesc:
            distA = distBtwn(anode, commonDesc, pipe=pipe)
            distB = distBtwn(bnode, commonDesc, pipe=pipe)
            dist = distA + distB
        else:
            dist = None
    return dist

def nodesBetween(anode, bnode, pipe=None):
    '''returns the list of nodes connecting two nodes'''
    anodeAbove = above(anode, pipe=pipe)
    bnodeAbove = above(bnode, pipe=pipe)
    nodesBtwn = None
    if anode in bnodeAbove:
        aboveTups = above(bnode, pipe=pipe)
        nodesBtwn = list(set(below(anode, pipe=pipe)) & set(bnodeAbove))
    elif bnode in anodeAbove:
        aboveTups = above(anode)
        nodesBtwn = list(set(below(bnode, pipe=pipe)) & set(anodeAbove))
    else:
        commonDesc = firstCommonDesc((anode, bnode), pipe=pipe)
        if commonDesc:
            nodesA = nodesBetween(anode, commonDesc, pipe=pipe)
            nodesB = nodesBetween(bnode, commonDesc, pipe=pipe)
            nodesBtwn = nodesA.extend(nodesB)
        else:
            nodesBtwn = None
      
    return nodesBtwn

def mainComp():
    '''returns a list of all nodes in the largest tree in the comp, assumed to be the main comp'''
    allNodes = [n for n in nuke.allNodes() if n.Class() == 'Write']
    notMainNodes = [n for n in nuke.allNodes() if n not in allNodes and n.Class() != 'Viewer']
    aboveNodes = []
    aboveNodes = [(len(above(n)), n) for n in allNodes]
    bottomNode = max(aboveNodes)[1]
    mainCompNodes = above(bottomNode)
    mainCompNodes.extend([n for n in notMainNodes for d in above(n) if d in mainCompNodes and n not in mainCompNodes])
    mainCompNodes.append(bottomNode)
    return mainCompNodes

def notMainComp(mainCompNodes = None):
    '''returns a list of all non-disabled nodes outside the main comp (see mainComp)'''
    mainCompNodes = mainCompNodes if mainCompNodes else mainComp()
    nReturn = []
    allNodes = set([n for n in nke.byKnobValue('disable', False) if n.Class() != 'Viewer'])
    for n in mainCompNodes:
        if n in allNodes:
            allNodes.remove(n)
    nodes = list(allNodes)
    for n in nodes:
        try:
            if n['disable'].getValue() == True:
                allNodes.remove(n)
            else:
                pass
        except:
            pass
    nodeDict = nke.nodeClassDict(allNodes)
    nodeDict.pop('BackdropNode', None)
    nodeDict.pop('Viewer', None)
    nodeDict.pop('StickyNote', None)
    for k in nodeDict:
        nReturn.extend(nodeDict[k])
    return nReturn

def alongDir(direction, node=None):
    '''use nkAlign to return all nodes that are connected along a given cardinal direction
    direction is a one-character string (N, S, E, or W)'''
    node = node if node else nuke.selectedNode()
    alongList = [node]
    for n in alongList:
        for inp in directInputs(n):
            angle = nkAlign.getAngleBetween(n, inp)
            cardinal = nkAlign.getCardinalName(nkAlign.getClosestCardinal(angle))
            if cardinal == direction:
                alongList.append(inp)
        for inp in directOutputs(n):
            angle = nkAlign.getAngleBetween(n, inp)
            cardinal = nkAlign.getCardinalName(nkAlign.getClosestCardinal(angle))
            if cardinal == direction:
                alongList.append(inp)
    return alongList

def pipeAbove(pipe = 'B', node=None):
    '''return the node connected to the B-pipe of the given node'''
    node = node if node else nuke.selectedNode()
    inp = 0 if pipe == 'B' else 1 
    nodes = [node]
    bAbove = []
    for n in nodes:
        inputs = directInputs(n)
        if inputs:
            if n.Class() != 'DeepRecolor':
                nodes.append(inputs[inp])
            else:
                nodes.append(inputs[1-inp])
    return nodes

def getBDList(node=None):
    '''return a list in hierarchical order of every backdrop which contains the given node'''
    node = node if node else nuke.selectedNode()
    allBD = nke.byClass('BackdropNode')
    curSel = nuke.selectedNodes()
    bdList = []
    for bd in allBD:
        nkSel.deSelAll()
        bd.selectNodes()
        nodeList = nuke.selectedNodes()
        if node in nodeList:
            bdList.append((bd, nodeList))
    lengths = [len(nlist) for n, nlist in bdList]
    #if len(lengths) != len(set(lengths)):
        #raise Exception('bad hierarchy')
    bdListSorted = sorted(bdList, key = lambda x: len(x[1]))
    bdListSorted.reverse()
    nkSel.replace(curSel)
    return [n[0] for n in bdListSorted]

def firstNodeAboveIn(node, nodes, distReturn=True, pipe=None):
    '''pretty specific call to find the first node above the given node that is in a group of given nodes'''
    aboveNodes = above(node, distReturn=True, pipe=pipe)
    aboveIn = list(set(nodes) & set([an[0] for an in aboveNodes]))
    aboveDist = [(n[0], n[1]) for n in aboveNodes if n[0] in aboveIn]
    aboveDist.sort(key=lambda x: x[1])
    if aboveDist and distReturn:
        return aboveDist[0]
    elif aboveDist and not distReturn:
        return aboveDist[0][0]
    else:
        return None

def recurseGroups(level=0, parent=None):
    returnGrp = []
    if parent:
        groups = ['%s.%s' % (parent, n.name()) for n in nke.byClass('Group', nodes=nuke.allNodes())]
        returnGrp = groups
    else:
        groups = [n.name() for n in nke.byClass('Group', nodes=nuke.allNodes())]
        returnGrp = groups
    level += 1
    if groups:
        for g in groups:
            thisGrp = nuke.toNode(g)
            print(g)
            thisGrp.begin()
            returnGrp.extend(recurseGroups(parent=g))
            thisGrp.end()
    nuke.root().begin()
    return returnGrp

def allNodesRecurse(withGroups=False):
    nuke.root().begin()
    nodes = [(nuke.root(), nuke.allNodes())] if withGroups else nuke.allNodes()
    groupNames = recurseGroups()
    groups = [nuke.toNode(gn) for gn in groupNames]
    for g in groups:
        if withGroups:
            nodes.append((g, g.nodes()))
        else:
            nodes.extend(g.nodes())
    return nodes

def hackToRoot(origNodes):
    nodeGroups = allNodesRecurse(withGroups=True)
    newNodes = [n for g in nodeGroups for n in g[1]]
    ns = [n for n in newNodes if n not in origNodes]
    ngs = list(set([ng[0] for n in ns for ng in nodeGroups if n in ng[1]]))
    for ng in ngs:
        copyToRoot = True if ng != nuke.root() else False
        
        if copyToRoot:
            ng.begin()
            delNodes = [n for n in ng.nodes() if n in ns]
            nkSel.replace(ns)
            nuke.nodeCopy('%clipboard')
            nuke.root().begin()
            nkSel.deSelAll()
            nuke.nodePaste('%clipboard')
        else:
            pass
    nuke.root().begin()
    copiedNodes = [n for n in nuke.allNodes() if n not in origNodes]