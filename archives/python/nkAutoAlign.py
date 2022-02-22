import nkAlign
import nkCrawl
import nuke
import threading
import time
from math import sqrt

def main():
    print "this does nothing"

def getNodes(nodes):
    if nodes:
        try:
            list(nodes)
        except:
            nodes = [nodes]
    else:
        try:
            nodes = nuke.selectedNodes()
        except:
            nuke.message('nothing selected')
    return nodes

def getNode(node):
    if node:
        try:
            node = node[0]
        except:
            pass
    else:
        try:
            node = nuke.selectedNode()
        except:
            nuke.message('nothing selected')
    return node

def align(nodes=None):
    nodes = getNodes(nodes)
    if nodes and len(nodes) == 1:
        alignNode(nodes[0])
    elif nodes and len(nodes) > 1:
        direction = mindRead(nodes)
        if direction == ['X']:
            nkAlign.alignGrpX(nodes)
        elif direction == ['Y']:
            nkAlign.alignGrpY(nodes)
        else:
            for n in nodes:
                alignNode(n)

def alignNode(node=None):
    node = getNode(node)
    info = nodeInfo(node)
    if info['inOutType'] == 'SISO':
        if info['dirType'] in set(['inline', 'broken', 'corner']):
            if info['sandwichAngle'] == 0.0:
                nudgeInline(info)
        if info['dirType'] in ['corner','broken'] and info['sandwichAngle'] != 0.0:
            moveToCorner(info)
    elif info['inOutType'] in set(['DISO', 'SIDO']):
        if info['dirType'] in set(['inputOutputInlineB', 'inputOutputInlineA']):
            if info['sandwichAngle'] == 0.0:
                nudgeIOInline(info)
    elif info['inOutType'] in set(['NISO', 'SINO']):
        snapTo(info)

def snapTo(info):
    node = info['node']
    if info['inOutType'] == 'NISO':
        outInfo = info
        if outInfo['outCardinal'] == 'N':
            nkAlign.alignUnder(node, info['outputs'][0])
        if outInfo['outCardinal'] == 'S':
            nkAlign.alignAbove(node, info['outputs'][0])
        if outInfo['outCardinal'] == 'E':
            nkAlign.alignLeft(node, info['outputs'][0])
        if outInfo['outCardinal'] == 'W':
            nkAlign.alignRight(node, info['outputs'][0])
    else:
        inInfo = info
        if inInfo['inCardinal'] == 'N':
            nkAlign.alignAbove(node, info['inputs'][0])
        if inInfo['inCardinal'] == 'S':
            nkAlign.alignUnder(node, info['inputs'][0])
        if inInfo['inCardinal'] == 'E':
            nkAlign.alignRight(node, info['inputs'][0])
        if inInfo['inCardinal'] == 'W':
            nkAlign.alignLeft(node, info['inputs'][0])

def nudgeIOInline(info):
    node = info['node']
    if info['inOutType'] == 'DISO':
        alignTo = info['inputs']
    else:
        alignTo = info['outputs']
    if info['dirType'] == 'inputOutputInlineB':
        if info['sandwichCardinal'] in set(['S', 'N']):
            nkAlign.alignOnX(node, alignTo[1])
            nkAlign.alignOnY(node, alignTo[0])
        elif info['sandwichCardinal'] in set(['E', 'W']):
            nkAlign.alignOnY(node, alignTo[1])
            nkAlign.alignOnX(node, alignTo[0])
    elif info['dirType'] == 'inputOutputInlineA':
        if info['sandwichCardinal'] in set(['S', 'N']):
            nkAlign.alignOnX(node, alignTo[0])
            nkAlign.alignOnY(node, alignTo[1])
        elif info['sandwichCardinal'] in set(['E', 'W']):
            nkAlign.alignOnY(node, alignTo[0])
            nkAlign.alignOnX(node, alignTo[1])

def nudgeInline(info):
    node = info['node']
    nodeInput = info['inputs'][0]
    nodeOutput = info['outputs'][0]
    avg = nkAlign.getAveragePosition([nodeInput, info['outputs'][0]])
    if info['sandwichCardinal'] in set(['S','N']):
        nkAlign.alignOnY(node, nodeInput)
    elif info['sandwichCardinal'] in set(['E','W']):
        nkAlign.alignOnX(node, nodeInput)
    if info['sandwichCardinal'] == 'S':
        if nkAlign.doesCollide(node, nodeInput) or node['ypos'].value() < nodeInput['ypos'].value():
            nkAlign.alignUnder(node, nodeInput)
        if nkAlign.doesCollide(node, nodeOutput) or node['ypos'].value() > nodeOutput['ypos'].value():
            nkAlign.alignAbove(node, nodeOutput)
    if info['sandwichCardinal'] == 'N':
        if nkAlign.doesCollide(node, nodeInput) or node['ypos'].value() > nodeInput['ypos'].value():
            nkAlign.alignAbove(node, nodeInput)
        if nkAlign.doesCollide(node, nodeOutput) or node['ypos'].value() < nodeOutput['ypos'].value():
            nkAlign.alignUnder(node, nodeOutput)
    if info['sandwichCardinal'] == 'W':
        if nkAlign.doesCollide(node, nodeInput) or node['xpos'].value() > nodeInput['xpos'].value():
            nkAlign.alignLeft(node, nodeInput)
        if nkAlign.doesCollide(node, nodeOutput) or node['xpos'].value() < nodeOutput['xpos'].value():
            nkAlign.alignRight(node, nodeOutput)
    if info['sandwichCardinal'] == 'E':
        if nkAlign.doesCollide(node, nodeInput) or node['xpos'].value() < nodeInput['xpos'].value():
            nkAlign.alignRight(node, nodeInput)
        if nkAlign.doesCollide(node, nodeOutput) or node['xpos'].value() > nodeOutput['xpos'].value():
            nkAlign.alignLeft(node, nodeOutput)

def moveToCorner(info):
    node = info['node']
    nodeInput = info['inputs'][0]
    nodeOutput = info['outputs'][0]
    nx = info['x']
    ny = info['y']
    inx = nkAlign.getXYCenter(nodeInput)[0]
    iny = nkAlign.getXYCenter(nodeInput)[1]
    outx = nkAlign.getXYCenter(nodeOutput)[0]
    outy = nkAlign.getXYCenter(nodeOutput)[1]
    solOne = distForm((nx,ny),(inx,outy))
    solTwo = distForm((nx,ny),(outx, iny))
    checkOuts = nkCrawl.directOutputs(nodeOutput)
    checkOuts.extend(nkCrawl.directOutputs(nodeInput))
    checkOuts.extend(nkCrawl.directInputs(nodeInput))
    checkOuts.extend(nkCrawl.directInputs(nodeOutput))
    if solOne < solTwo:
        nkAlign.moveNodeTo(node, inx, outy)
        for out in checkOuts:
            if nkAlign.doesCollide(node, out) and out != node:
                nkAlign.moveNodeTo(node, outx, iny)
                break
    else:
        nkAlign.moveNodeTo(node, outx, iny)
        for out in checkOuts:
            if nkAlign.doesCollide(node, out) and out!=node:
                nkAlign.moveNodeTo(node, inx, outy)
                break

def distForm(thisPos, thatPos):
    return sqrt(((thisPos[0] - thatPos[0])**2) + ((thisPos[1] - thatPos[1])**2))

def nodeInfo(n):
    info = {}
    info['node'] = n
    info['name'] = n.name()
    info['class'] = n.Class()
    xypos = nkAlign.getXYCenter(n)
    info['xy'] = xypos
    info['x'] = xypos[0]
    info['y'] = xypos[1]
    info['inputs'] = nkCrawl.directInputs(n)
    if len(info['inputs']) > 1:
        if info['class'] in set(['Merge', 'Merge2', 'Copy', 'ChannelMerge', 'DeepMerge']):
            info['bpipe'] = info['inputs'][0]
            info['apipe'] = info['inputs'][1]
            if len(info['inputs']) > 2:
                info['mask'] = info['inputs'][2]
        elif info['class'] in set(['Grade', 'ColorCorrect', 'ColorLookup', 'HueShift', 'HueCorrect', 'Invert', 'Saturation', 'Defocus']):
            info['mask'] = info['inputs'][1]
    info['outputs'] = nkCrawl.directOutputs(n)
    info['inOutType'] = inOutType(info)
    addAngles(info)
    return info

def inOutType(nInfo):
    inp = len(nInfo['inputs'])
    outp = len(nInfo['outputs'])
    if inp == 0:
        inpS = 'N'
    elif inp == 1:
        inpS = 'S'
    elif inp == 2:
        inpS = 'D'
    else:
        inpS = 'X'
    if outp == 0:
        outpS = 'N'
    elif outp == 1:
        outpS = 'S'
    elif outp == 2:
        outpS = 'D'
    else:
        outpS = 'X'
    return '%sI%sO' % (inpS, outpS)

def addAngles(nInfo):
    n = nInfo['node']

    if nInfo['inOutType'] in set(['SISO', 'SIDO', 'SINO']):
        inp = nInfo['inputs'][0]
        inangle = nkAlign.getAngleBetween(inp, n)
        nInfo['inAngle'] = nkAlign.getOffCardinalAmt(inangle)
        nInfo['inCardinal'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(inangle))
    if nInfo['inOutType'] in set(['SISO', 'NISO', 'DISO']):
        outp = nInfo['outputs'][0]
        outangle = nkAlign.getAngleBetween(n, outp)
        nInfo['outAngle'] = nkAlign.getOffCardinalAmt(outangle)
        nInfo['outCardinal'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(outangle))
    if nInfo['inOutType'] in set(['DISO', 'DIDO', 'DINO']):
        inpA = nInfo['inputs'][1]
        inpAngleA = nkAlign.getAngleBetween(inpA, n)
        inpB = nInfo['inputs'][0]
        inpAngleB = nkAlign.getAngleBetween(inpB, n)
        nInfo['inAngleA'] = nkAlign.getOffCardinalAmt(inpAngleA)
        nInfo['inCardinalA'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(inpAngleA))
        nInfo['inAngleB'] = nkAlign.getOffCardinalAmt(inpAngleB)
        nInfo['inCardinalB'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(inpAngleB))
    if nInfo['inOutType'] in set(['SIDO', 'DIDO', 'NIDO']):
        outpA = nInfo['outputs'][0]
        outpAngleA = nkAlign.getAngleBetween(n, outpA)
        outpB = nInfo['outputs'][1]
        outpAngleB = nkAlign.getAngleBetween(n, outpB)
        nInfo['outAngleA'] = nkAlign.getOffCardinalAmt(outpAngleA)
        nInfo['outCardinalA'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(outpAngleA))
        nInfo['outAngleB'] = nkAlign.getOffCardinalAmt(outpAngleB)
        nInfo['outCardinalB'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(outpAngleB))
    #SISO - Single Input, Single Output
    if nInfo['inOutType'] == 'SISO':
        direction = '%s%s' % (nInfo['inCardinal'], nInfo['outCardinal'])
        nInfo['dir'] = direction
        if direction in set(['SS','EE','WW','NN']):
            nInfo['dirType'] = 'inline'
        elif direction in set(['SW', 'SE', 'ES', 'EN', 'NE', 'NW', 'WN', 'WS']):
            nInfo['dirType'] = 'corner'
        else:
            nInfo['dirType'] = 'broken'
        sandwAngle = nkAlign.getAngleBetween(inp, outp)
        nInfo['sandwichAngle'] = nkAlign.getOffCardinalAmt(sandwAngle)
        nInfo['sandwichCardinal'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(sandwAngle))
    #DISO - Double Input, Single Output
    if nInfo['inOutType'] == 'DISO':
        direction = '%s%s%s' % (nInfo['inCardinalA'], nInfo['inCardinalB'], nInfo['outCardinal'])
        nInfo['dir'] = direction
        if direction in set(['EWS', 'EWN', 'WEN', 'WES', 'NSE', 'NSW', 'SNW', 'SNE']):
            nInfo['dirType'] = 'inputsInline'
            sandwAngle = nkAlign.getAngleBetween(nInfo['inputs'][0], nInfo['inputs'][1])
            nInfo['sandwichAngle'] = nkAlign.getOffCardinalAmt(sandwAngle)
            nInfo['sandwichCardinal'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(sandwAngle))
        elif direction in set(['ENE', 'ESE', 'WNW', 'WSW', 'NWN', 'NEN', 'SES', 'SWS']):
            nInfo['dirType'] = 'inputOutputInlineA'
            sandwAngle = nkAlign.getAngleBetween(nInfo['inputs'][1], nInfo['outputs'][0])
            nInfo['sandwichAngle'] = nkAlign.getOffCardinalAmt(sandwAngle)
            nInfo['sandwichCardinal'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(sandwAngle))
        elif direction in set(['ENN', 'ESS', 'WNN', 'WSS', 'NEE', 'NWW', 'SEE', 'SWW']):
            nInfo['dirType'] = 'inputOutputInlineB'
            sandwAngle = nkAlign.getAngleBetween(nInfo['inputs'][0], nInfo['outputs'][0])
            nInfo['sandwichAngle'] = nkAlign.getOffCardinalAmt(sandwAngle)
            nInfo['sandwichCardinal'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(sandwAngle))
        else:
            nInfo['dirType'] = 'broken'
    #SIDO - Double Input, Single Output
    if nInfo['inOutType'] == 'SIDO':
        direction = '%s%s%s' % (nInfo['inCardinal'], nInfo['outCardinalA'], nInfo['outCardinalB'])
        nInfo['dir'] = direction
        if direction in set(['ESN', 'WSN', 'ENS', 'WNS', 'SEW', 'NEW', 'SWE', 'NWE']):
            nInfo['dirType'] = 'outputsInline'
            sandwAngle = nkAlign.getAngleBetween(nInfo['outputs'][0], nInfo['outputs'][1])
            nInfo['sandwichAngle'] = nkAlign.getOffCardinalAmt(sandwAngle)
            nInfo['sandwichCardinal'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(sandwAngle))
        elif direction in set(['ENE', 'ESE', 'WNW', 'WSW', 'NWN', 'NEN', 'SES', 'SWS']):
            nInfo['dirType'] = 'inputOutputInlineA'
            sandwAngle = nkAlign.getAngleBetween(nInfo['inputs'][0], nInfo['outputs'][1])
            nInfo['sandwichAngle'] = nkAlign.getOffCardinalAmt(sandwAngle)
            nInfo['sandwichCardinal'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(sandwAngle))
        elif direction in set(['NNE', 'SSE', 'NNW', 'SSW', 'EEN', 'WWN', 'EES', 'WWS']):
            nInfo['dirType'] = 'inputOutputInlineB'
            sandwAngle = nkAlign.getAngleBetween(nInfo['inputs'][0], nInfo['outputs'][0])
            nInfo['sandwichAngle'] = nkAlign.getOffCardinalAmt(sandwAngle)
            nInfo['sandwichCardinal'] = nkAlign.getCardinalName(nkAlign.getClosestCardinal(sandwAngle))
        else:
            nInfo['dirType'] = 'broken'

def mindRead(nodes):
    node = nodes[0]
    nodes = nodes[1:]
    directions = []
    for n in nodes:
        angle = nkAlign.getAngleBetween(n,node)
        cardinal = nkAlign.getCardinalName(nkAlign.getClosestCardinal(angle))
        direction = 'Y' if 'N' in cardinal or 'S' in cardinal else 'X'
        directions.append(direction)
    return list(set(directions))


