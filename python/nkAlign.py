import nuke
import nukescripts
import nkEval
import math
import nkCrawl
import nkSel


def main():
    print("this does nothing")

def getXYPos(thisNode = None):
    ###returns the XY position of the node.  Corresponds to top-left pixel of node
    ###input: node object
    ###return type: [x,y] list
    ###
    thisNode = thisNode if thisNode else nuke.selectedNode
    xposition = thisNode['xpos'].value()
    yposition = thisNode['ypos'].value()
    return (xposition, yposition)

def getBB(node = None):
    node = node if node else nuke.selectedNode()
    ###get the maximum and minimum x,y coordinates of the given node
    ###input: node list
    ###returns (xmin, ymin, xmax, ymax) tuple
    xmin, ymin = getXYPos(node)
    xmax = getTrueWidth(node) + xmin
    ymax = getTrueHeight(node) + ymin
    return (xmin, ymin, xmax, ymax)

def doesCollide(thisNode=None, thatNode=None):
    thisNode = thisNode if thisNode else nuke.selectedNodes()[0]
    thatNode = thatNode if thatNode else nuke.selectedNodes()[1]
    thisBB = getBB(thisNode)
    thisMinX = thisBB[0]
    thisMinY = thisBB[1]
    thisMaxX = thisBB[2]
    thisMaxY = thisBB[3]
    thatBB = getBB(thatNode)
    thatMinX = thatBB[0]
    thatMinY = thatBB[1]
    thatMaxX = thatBB[2]
    thatMaxY = thatBB[3]
    overlap = True
    if (thisMaxX < thatMinX):
        overlap = False
    if (thisMinX > thatMaxX):
        overlap = False
    if (thisMaxY < thatMinY):
        overlap = False
    if (thisMinY > thatMaxY):
        overlap = False
    return overlap

def getBBGrp(nodes=None):
    ###get the maximum and minimum x,y coordinates of the given nodes
    ###input: node list
    ###returns (xmin, ymin, xmax, ymax) tuple
    nodes = nodes if nodes else nuke.selectedNodes()
    xmin = min([node.xpos() for node in nodes])
    ymin = min([node.ypos() for node in nodes])
    xmax = max([node.xpos() + getTrueWidth(node) for node in nodes])
    ymax = max([node.ypos() + getTrueHeight(node) for node in nodes])
    return (xmin, ymin, xmax, ymax)

def getBBGrpCenters(nodes=None):
    ###get the maximum and minimum x,y coordinates of the given nodes, using the node centers instead of top-left pixel
    ###input: node list
    ###returns (xmin, ymin, xmax, ymax) tuple
    nodes = nodes if nodes else nuke.selectedNodes()
    xycenters = [getXYCenter(node) for node in nodes]
    xmin = min([xycenter[0] for xycenter in xycenters])
    ymin = min([xycenter[1] for xycenter in xycenters])
    xmax = max([xycenter[0] for xycenter in xycenters])
    ymax = max([xycenter[1] for xycenter in xycenters])
    bdNodes = nkEval.byClass('BackdropNode', nodes)
    if len(bdNodes) > 0:
        bdxmin, bdymin, bdxmax, bdymax = getBBGrp(bdNodes)
        xmin = min(xmin, bdxmin)
        ymin = min(ymin, bdymin)
        ymax = max(ymax, bdymax)
        xmax = max(xmax, bdxmax)
    return (xmin, ymin, xmax, ymax)

def getCollides(point, bb):
    ###return whether a point is within a node's screen bounding box.
    print("this does nothing")

def getXYCenter(thisNode):
    ###return the X,Y center of the given node
    xposStart = thisNode.xpos()
    yposStart = thisNode.ypos()
    divHeight = (getTrueHeight(thisNode) / 2)
    divWidth = (getTrueWidth(thisNode) / 2)
    xposFinal = xposStart + divWidth
    yposFinal = yposStart + divHeight
    return [xposFinal, yposFinal]

def getTrueWidth(node = None):
    ###get the screen width of the node, even in batch mode
    node = node if node else nuke.selectedNode()
    w = node.screenWidth()
    if w == 0:
        nClass = node.Class()
        if nClass == 'Dot':
            w = 12
        elif nClass in set(['Camera', 'Camera2', 'Scene', 'Light2', 'Light', 'Environment', 'Spotlight', 'DirectLight']):
            w = 60
        else:
            w = 80
    return w

def getTrueHeight(node = None):
    ###get the screen height of the node, even in batch mode
    node = node if node else nuke.selectedNode()
    knobs = node.knobs()
    nClass = node.Class()
    baseHeight = 18
    perLine = 12
    line1 = 0
    line2 = 0
    line3 = 0
    line4 = 0
    line5 = 0
    postage = 0
    if nClass == 'Dot':
        finalHeight = 12
    elif nClass in set(['BackdropNode', 'StickyNote']):
        finalHeight = node.screenHeight()
    elif nClass in set(['Camera', 'Camera2', 'Scene', 'Light2', 'Light', 'Environment', 'Spotlight', 'DirectLight']):
        finalHeight = 60
    else:
        if 'channels' in knobs and node['channels'].value() not in set(['rgb','rgba']):
            line1 = 1
        if 'mask' in knobs and node['mask'].value() != 'none':
            line1 = 1
        if 'unpremult' in knobs and node['unpremult'].value() != 'none':
            line1 = 1
        if nClass in set(['Read', 'DeepRead']) and 'file' in knobs and node['file'].value() != '':
            line2 = 1
        if 'label' in knobs and node['label'].value():
            line3 = len([n for n in node['label'].value().split('\n') if n != ''])
        if 'raw' in knobs and node['raw'].value():
            line4 = 1
        if 'colorspace' in knobs and 'default' not in node['colorspace'].value():
            line4 = 1
        if nClass in set(['Reformat', 'DeepReformat']) and 'format' in knobs and node['format'] != 'root.format':
            line5 = 1
        if 'postage_stamp' in knobs and node['postage_stamp'].value():
            postage = 46
        finalHeight = baseHeight + ((line1 + line2 + line3 + line4 + line5) * perLine) + postage
    finalHeight = node.screenHeight() if finalHeight < node.screenHeight() else finalHeight
    return finalHeight

def moveNodeBy(thisNode, xshift, yshift):
    ###move the specified node relative to its current position
    ###input: node object, int, int
    ###returns the new position
    ###return type: [x,y] list
    currentPosition = getXYPos(thisNode)
    moveRelX = int((currentPosition[0] + xshift))
    moveRelY = int((currentPosition[1] + yshift))
    thisNode.setXpos(moveRelX)
    thisNode.setYpos(moveRelY)
    return [moveRelX, moveRelY]

def nudge(xshift, yshift, nodes=None):
    ###move the specified node relative to its current position
    ###input: node object, int, int
    nodes = nodes if nodes else nuke.selectedNodes()
    for thisNode in nodes:
        currentPosition = getXYPos(thisNode)
        moveRelX = int((currentPosition[0] + xshift))
        moveRelY = int((currentPosition[1] + yshift))
        thisNode.setXpos(moveRelX)
        thisNode.setYpos(moveRelY)

def moveNodeTo(thisNode, xpos, ypos):
    ###move the specified node to an absolute position
    ###input: node object, int, int
    currentPosition = getXYCenter(thisNode)
    moveRelX = int((xpos - currentPosition[0]))
    moveRelY = int((ypos -currentPosition[1]))
    moveNodeBy(thisNode, moveRelX, moveRelY)

def moveNodeCorner(thisNode, xpos, ypos):
    ###move the specified node relative to its current position, from the default top-left corner
    ###input: node object, int, int
    currentPosition = getXYPos(thisNode)
    moveRelX = int((xpos - currentPosition[0]))
    moveRelY = int((ypos - currentPosition[1]))
    moveNodeBy(thisNode, moveRelX, moveRelY)

def alignOnY(thisNode, thatNode):
    ###aligns thisNode on the Y-axis with thatNode
    ###input: node object, node object
    ###returns the new position of the node
    ###return type: [x,y] list
    thisNodePos = getXYCenter(thisNode)
    parentPos = getXYCenter(thatNode)
    posDiff = parentPos[0] - thisNodePos[0]
    moveNodeBy(thisNode, posDiff, 0)
    newPos = getXYPos(thisNode)
    return newPos;

def alignOnYInput(thisNode):
    ###aligns the specified node on the Y-axis with its 0th input node
    ###input: node object
    ###returns the new position of the node
    ###return type: [x,y] list
    thisNodePos = getXYCenter(thisNode)
    if thisNode.inputs() > 0:
        parentNode = thisNode.input(0)
        alignOnY(thisNode, parentNode)
    newPos = getXYPos(thisNode)
    return newPos;

def alignOnX(thisNode, thatNode):
    ###aligns the specified node on the X-axis with another node (thatNode)
    ###input: node object, node object
    ###returns the new position of the node
    ###return type: [x,y] list
    thisNodePos = getXYCenter(thisNode)
    parentPos = getXYCenter(thatNode)
    posDiff = parentPos[1] - thisNodePos[1]
    moveNodeBy(thisNode, 0, int(posDiff))
    newPos = getXYPos(thisNode)
    return newPos;

def alignOnXInput(thisNode):
    ###aligns the specified node on the X-axis with its 0th input node
    ###input: node object
    ###returns the new position of the node
    ###return type: [x,y] list
    thisNodePos = getXYCenter(thisNode)
    if thisNode.inputs() > 0:
        parentNode = thisNode.input(0)
        alignOnX(thisNode, parentNode)
    newPos = getXYPos(thisNode)
    return newPos;

def alignUnder(thisNode, thatNode):
    ###aligns thisNode on the Y-axis, underneath thatNode, with a 20-pixel buffer
    ###input: node object
    ###returns the new position of the node
    ###return type: [x,y] list
    parentNode = thisNode.input(0)
    alignOnX(thisNode, thatNode)
    alignOnY(thisNode, thatNode)
    offsetY = ( (getTrueHeight(thisNode) / 2) + (getTrueHeight(thatNode) / 2) ) + 20
    moveNodeBy(thisNode, 0, offsetY)
    newPos = getXYPos(thisNode)
    return newPos;

def alignAbove(thisNode, thatNode):
    ###aligns thisNode on the Y-axis, above thatNode, with a 20-pixel buffer
    ###input: node object
    ###returns the new position of the node
    ###return type: [x,y] list
    parentNode = thisNode.input(0)
    alignOnX(thisNode, thatNode)
    alignOnY(thisNode, thatNode)
    offsetY = ( (getTrueHeight(thisNode) / 2) + (getTrueHeight(thatNode) / 2) ) + 20
    moveNodeBy(thisNode, 0, -offsetY)
    newPos = getXYPos(thisNode)
    return newPos;

def alignLeft(thisNode, thatNode):
    ###aligns thisNode on the Y-axis, to the left of thatNode, with a 20-pixel buffer
    ###input: node object
    ###returns the new position of the node
    ###return type: [x,y] list
    parentNode = thisNode.input(0)
    alignOnX(thisNode, thatNode)
    alignOnY(thisNode, thatNode)
    offsetX = ( (getTrueWidth(thisNode) / 2) + (getTrueWidth(thatNode) / 2) ) + 20
    moveNodeBy(thisNode, -offsetX, 0)
    newPos = getXYPos(thisNode)
    return newPos;

def alignRight(thisNode, thatNode):
    ###aligns thisNode on the Y-axis, to the right of thatNode, with a 20-pixel buffer
    ###input: node object
    ###returns the new position of the node
    ###return type: [x,y] list
    parentNode = thisNode.input(0)
    alignOnX(thisNode, thatNode)
    alignOnY(thisNode, thatNode)
    offsetX = ( (getTrueWidth(thisNode) / 2) + (getTrueWidth(thatNode) / 2) ) + 20
    moveNodeBy(thisNode, offsetX, 0)
    newPos = getXYPos(thisNode)
    return newPos;

def alignUnderInput(thisNode):
    ###aligns the specified node on the Y-axis, underneath its 0th input
    ###input: node object
    ###returns the new position of the node
    ###return type: [x,y] list
    if thisNode.inputs() > 0:
        parentNode = thisNode.input(0)
        alignUnder(thisNode, parentNode)
    newPos = getXYPos(thisNode)
    return newPos;

def alignAB(thisNode):
    ###aligns the specified node on the X-axis of the 0th input, and the Y axis of the 1th input
    ###input: node object
    ###returns the new position of the node
    ###return type: [x,y] list
    if thisNode.inputs() > 0:
        parentNodeB = thisNode.input(0)
        if parentNodeB is None:
            print("null on B Pipe")
        elif parentNodeB:
            alignOnY(thisNode, parentNodeB)
        else:
            print("failure on parsing B Pipe")
    if thisNode.inputs() > 1:
        parentNodeA = thisNode.input(1)
        if parentNodeA is None:
            print("null on A Pipe")
        elif parentNodeA:
            alignOnX(thisNode, parentNodeA)
        else:
            print("failure on parsing A Pipe")
    newPos = getXYPos(thisNode)
    return newPos;

def alignBA(thisNode):
    ###aligns the specified node on the Y-axis of the 0th input, and the X axis of the 1th input
    ###input: node object
    ###returns the new position of the node
    ###return type: [x,y] list
    if thisNode.inputs() > 0:
        parentNodeB = thisNode.input(0)
        if parentNodeB is None:
            print("null on B Pipe")
        elif parentNodeB:
            alignOnX(thisNode, parentNodeB)
        else:
            print("failure on parsing B Pipe")
    if thisNode.inputs() > 1:
        parentNodeA = thisNode.input(1)
        if parentNodeA is None:
            print("null on A Pipe")
        elif parentNodeA:
            alignOnY(thisNode, parentNodeA)
        else:
            print("failure on parsing A Pipe")
    newPos = getXYPos(thisNode)
    return newPos;

def alignChain():
    ###aligns the B-pipe (0th input) chain.
    bottomNode = nuke.selectedNode()
    currentNode = bottomNode
    nodeList = [bottomNode]
    escapeVariable = 0
    if bottomNode.inputs() > 0:
        while escapeVariable == 0:
            nextNode = currentNode.input(0)
            nodeList.append(nextNode)
            if nextNode.inputs() > 0:
                currentNode = nextNode
            else:
                escapeVariable = 1
        nodeList.reverse()
        for thisNode in nodeList:
            alignAB(thisNode)
    else:
        print("no chain to align!")
    return;

def stackNodes():
    ###stacks a set of selected nodes on the Y axis
    ###input: requires at least two selected nodes
    nodeList = nuke.selectedNodes()
    nodeIndex = 0
    nodeList.reverse()
    nextNode = nodeList[1]
    for thisNode in nodeList:
        currentNode = nodeList[nodeIndex]
        alignUnder(currentNode, nextNode)
        nextNode = currentNode
        nodeIndex = nodeIndex + 1
    return;

def alignGrpY(nodes=None):
    ###aligns a set of selected nodes on the Y axis of last selected node
    ###input: requires at least two selected nodes
    nodeList = nodes if nodes else nuke.selectedNodes()
    thatNode = nodeList[0]
    for thisNode in nodeList:
        alignOnY(thisNode, thatNode)
    return;

def alignGrpX(nodes=None):
    ###aligns a set of selected nodes on the X axis of last selected node
    ###input: requires at least two selected nodes
    nodeList = nodes if nodes else nuke.selectedNodes()
    thatNode = nodeList[0]
    for thisNode in nodeList:
        alignOnX(thisNode, thatNode)
    return;

def getVectorBetween(thisNode, thatNode):
    ###returns the difference between two node positions
    ###input: Node object, Node object
    ###return type: [x,y] list
    thisNodePos = getXYCenter(thisNode)
    thatNodePos = getXYCenter(thatNode)
    vector = [(thatNodePos[0] - thisNodePos[0]), (thatNodePos[1] - thisNodePos[1])]
    return vector

def getOutputInputs(thisNode, checkNode):
    ###return the input nodes that thisNode outputs to - required for other Align tools
    nodeInputs = thisNode.inputs()
    nthInputs = []
    for i in range(nodeInputs):
        if thisNode.input(i) == checkNode:
            nthInputs.append(i)
    return nthInputs

def getAngleBetween(thisNode, thatNode):
    ###get the angle in degrees between thisNode and thatNode, if 0 degrees is directly east of thisNode
    vector = getVectorBetween(thisNode, thatNode)
    angleBetween = math.degrees(math.asin(((vector[1]) / (math.sqrt((float(vector[0]*vector[0])) + float((vector[1]*vector[1])))))))
    return angleBetween

def getAveragePosition(theseNodes):
    ###return the average position of all nodes in theseNodes list
    xAvg = 0
    yAvg = 0
    if (len(theseNodes) == 1):
        xAvg = getXYCenter(theseNodes[0])[0]
        yAvg = getXYCenter(theseNodes[0])[1]
    else:
        for thisNode in theseNodes:
            xyPos = getXYCenter(thisNode)
            xAvg += xyPos[0]
            yAvg += xyPos[1]
        xAvg = (xAvg / len(theseNodes))
        yAvg = (yAvg / len(theseNodes))

    return (xAvg, yAvg)

def getAngleBetween(thisNode, thatNode):
    ###returns the angle between the first and second node position
    ###input: Node object, Node object
    ###return type: float angular value
    v = getVectorBetween(thisNode, thatNode)
    angle = math.atan2(v[0],v[1])*180/math.pi
    return angle

def getClosestCardinal(angle):
    ###returns the closest 90-degree angle to the given angle
    ###input: float angle
    ###return type: float angular value
    c = int(round(angle/90)*90)
    return c

def getCardinalName(angle):
    ###given an angle rounded to the nearest 90, return the N S E W cardinal direction as a string
    if angle == 0:
        return 'S'
    elif angle == 90:
        return 'E'
    elif abs(angle) == 180:
        return 'N'
    elif angle == -90:
        return 'W'

def getOffCardinalAmt(angle):
    ###returns the offset angle between the given angle and the closest 90-degree
    ###input: float angle
    ###return type: float angular value
    c = getClosestCardinal(angle)
    offset = angle - c
    return offset

def cardinalOffsetBetween(thisNode, thatNode):
    ###returns the "off-axis" amount between two nodes
    ###input: Node object, Node object
    ###return type: float angular value
    return getOffCardinalAmt(getAngleBetween(thisNode, thatNode))

def getXMostNode(dirKey, minMax, nodes=None):
    ###returns the node furthest in one direction on the graph
    ###inputs: direction('X' or 'Y'), minMax('min' or 'max'), node object list
    nodes = nodes if nodes else nuke.selectedNodes()
    nodesByX = [(n[dirKey].getValue(),n) for n in nodes]
    nodesByX.sort()
    if minMax == 'max':
        index = -1
    elif minMax == 'min':
        index = 0
    return nodesByX[index][1]

def nudgeWithBuffer(direction, nodes=None):
    ###nudge the nodes with an awareness of other nodes in the hierarchy.
    nodes = nodes if nodes else nuke.selectedNodes()
    curSel = nuke.selectedNodes()
    if direction == 'up':
        dirKey = 'ypos'
        minMax = ('min', 'max')
        nudgeAmt = (0,-15)
    elif direction == 'down':
        dirKey = 'ypos'
        minMax = ('max', 'min')
        nudgeAmt = (0, 15)
    elif direction == 'left':
        dirKey = 'xpos'
        minMax = ('min', 'max')
        nudgeAmt = (-15, 0)
    elif direction == 'right':
        dirKey = 'xpos'
        minMax = ('max', 'min')
        nudgeAmt = (15, 0)
    keynode = getXMostNode(dirKey, minMax[1], nodes)
    bdNodes = nkCrawl.getBDList(keynode)
    if bdNodes:
        nkSel.deSelAll()
        bdNodes[-1].selectNodes()
        nodeScope = nuke.selectedNodes()
        nkSel.replace(curSel)
    else:
        nodeScope = nuke.allNodes()
    i = None
    if direction == 'up':
        i = 3
    elif direction == 'down':
        i = 1
    elif direction == 'left':
        i = 2
    else:
        i = 0
    keypos = getBB(keynode)[i]
    if minMax[0] == 'min':
            nudgeNodes = [n for n in nodeScope if getBB(n)[i] <= keypos]
    elif minMax[0] == 'max':
        nudgeNodes = [n for n in nodeScope if getBB(n)[i] >= keypos]

    nudge(nudgeAmt[0], nudgeAmt[1], nudgeNodes)

    for bdn in bdNodes:
        if direction in ('down', 'right'):
            bdn['bdheight'].setValue((bdn['bdheight'].value() + nudgeAmt[1]))
            bdn['bdwidth'].setValue((bdn['bdwidth'].value() + nudgeAmt[0]))








