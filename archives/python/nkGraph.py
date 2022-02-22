import nuke
import nkAlign as align

def main():
  print "this does nothing"

def focusSelected():
  '''zoom to the currently selected node in the graph'''
  pos = align.getXYPos(nuke.selectedNode())
  nuke.zoom(1.5, (pos[0], pos[1]))

def focus(node):
  '''zoom to the given node in the graph'''
  pos = align.getXYPos(node)
  nuke.zoom(1.5, (pos[0], pos[1]))

def nextViewerLayer():
  v = nuke.activeViewer()
  inp = v.activeInput()
  vn = v.node()
  n = vn.input(0)
  curLayer = vn['channels'].value()
  if len(curLayer.split()) > 1:
	curLayer = curLayer.split()[0].split('.')[0]
  layers = [lyr for lyr in nuke.layers(n)]
  if curLayer not in layers:
	lyrIndex = 0
  else:
	lyrIndex = layers.index(curLayer)
  lyrIndex += 1
  if lyrIndex >= len(layers):
	lyrIndex = 0
  vn['channels'].setValue(layers[lyrIndex])
  print curLayer

def nextViewerChannel():
  v = nuke.activeViewer()
  inp = v.activeInput()
  vn = v.node()
  n = vn.input(0)
  curLayerChan = vn['channels'].value()
  if len(curLayerChan.split()) > 1:
	primaries = ['red','green','blue','alpha']
	curLayer = curLayerChan.split()[0].split('.')[0]
	if curLayer in primaries:
	  curLayer = 'rgba'
	curChan = curLayerChan.split()[-1]
	if curChan in primaries:
	  curChan = 'rgba.' + curChan
  else:
	curLayer = curLayerChan
	curChan = 'none'

  layers = [lyr for lyr in nuke.layers(n)]
  
  channels = n.channels()
  
  layerChans = []
  
  for ch in channels:
	if curLayer in ch:
	  layerChans.append(ch)
  
  if curChan not in layerChans:
	chIndex = 0
  
  else:
	chIndex = layerChans.index(curChan)
  
  chIndex += 1
  
  if chIndex > len(layerChans):
	chIndex = 0
  
  layerChans[-1] = layerChans[chIndex]
  
  vn['channels'].setValue(' '.join(layerChans))
  
  print layerChans