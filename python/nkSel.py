import nuke
import nkCrawl as crawl
import nkEval as nke


def main():
    ###maintained for legacy purposes###
    print ('this does nothing')

def deSelAll():
    """deselect all nodes"""
    for sn in nuke.selectedNodes(): 
        sn['selected'].setValue(False)

def sel(nodes):
    """select one or a list/tuple of nodes"""
    try:
        for n in nodes:
            try:
                n['selected'].setValue(True)
            except:
                pass
    except TypeError:
        nodes['selected'].setValue(True)
	
def deSel(nodes):
    """de-select one or a list/tuple of nodes"""
    try:
        for n in nodes:
            try:
                n['selected'].setValue(False)
            except:
                pass
    except TypeError:
        nodes['selected'].setValue(False)


def replace(nodes):
    """replace the current selection with one or more nodes"""
    deSelAll()
    sel(nodes)
  
def up():
    """replace current selection with nodes one level upstream"""
    selNodes = nuke.selectedNodes()
    upStream = crawl.oneUp(selNodes)
    replace(upStream)

def down():
    """replace current selection with nodes one level downstream"""
    selNodes = nuke.selectedNodes()
    downStream = crawl.oneDown(selNodes)
    replace(downStream)

def selEndNodes():
    """replace current selection with the endpoints of the current tree"""
    replace(nke.endNodes())
  
def selUpBd():
    """replace the current selection with the backdrop node that contains it, if any"""
    if nuke.selectedNode():
        replace(crawl.getBDList()[0])
        if nuke.selectedNode() and nuke.selectedNode().Class() == 'BackdropNode':
            nuke.selectedNode().selectNodes()
    else:
        pass