import nuke
import nkSel
import nkCrawl
import nkAlign
import re

def addLight(thru=False):
  
    n = nuke.thisNode()
      
    light_selection = 'none'
    skip = False
      
    bns = nuke.toNode('builder_dot')
    bn = nkCrawl.oneUp(bns)[0]
    cns = nuke.toNode('copy_dot')
    cfd = nuke.toNode('copyfrom_dot')
    cn = nkCrawl.oneUp(cns)[0]
    nkSel.replace(bn)

    pn = nuke.createNode('Merge2', inpanel=False)
    pn['output'].setValue('rgb')
    pn['operation'].setValue('plus')
    pn.setInput(0, bn)

    nkSel.replace(cn)

    cpmerge = nuke.createNode('Merge2', inpanel=False)
    cpmerge['Achannels'].setExpression('%s.Achannels' % pn.name())
    cpmerge['Bchannels'].setValue('none')
    cpmerge['output'].setExpression('%s.Achannels' % pn.name())
    cpmerge['disable'].setExpression('%s.disable' % pn.name())
    cpmerge['operation'].setValue('copy')
    cpmerge.setInput(0, cn)
    cpmerge.setInput(1, cfd)

    nkAlign.alignUnder(cpmerge, cn)

    link = nuke.Link_Knob((pn.name()+'_link'), 'light')
    link.clearFlag(nuke.STARTLINE)
    link.makeLink(pn.name(), 'Achannels')

    disableLink = nuke.Link_Knob((pn.name()+'_disable_lnk'), 'mute')
    disableLink.clearFlag(nuke.STARTLINE)
    disableLink.makeLink(pn.name(), 'disable')

    rmb = nuke.PyScript_Knob((pn.name() + "_rmb"), 'X')
    rmb.setValue('import nk_maovg\nnk_maovg.removeLight(\''+ pn.name()+'\',\''+cpmerge.name()+'\')')
    rmb.setFlag(nuke.STARTLINE)

    n.addKnob(rmb)
    n.addKnob(link)
    n.addKnob(disableLink)

    nkSel.replace(pn)

    pn['Achannels'].setValue(light_selection)

def removeLight(pn, cpmerge):
    n = nuke.thisNode()
    n.removeKnob(n.knobs()[(pn+'_disable_lnk')])
    n.removeKnob(n.knobs()[(pn+'_link')])
    n.removeKnob(n.knobs()[(pn+'_rmb')])   
    nuke.delete(nuke.toNode(pn))
    nuke.delete(nuke.toNode(cpmerge))

def addFromSearch(channelsInput=None):
    ### Define Current Node
    ### Define Current Node
    n = nuke.thisNode()

    ###Grab the user input
    channelsInput = channelsInput if channelsInput else nuke.getInput('Search for AOV', '')
    channelsInput = '_' if channelsInput == '' else channelsInput
    if channelsInput:
        searchPieces = channelsInput.split()

        ###Get all the incoming channels
        allChannels = n.channels()

        ###Combine the channels into common layers
        layers = list(set([channel.split('.')[0] for channel in allChannels]))
        layers.sort()

        ###Setup counter for search term being found in layers
        foundCount = 0

        ###Copy the layers list to a duplicate list for iterating
        tmpLayers = list(layers)

        ###Remove layers from list that aren't a match
        for term in searchPieces:
            for layer in layers:
                if term in layer or term in layer.lower():
                    foundCount = 1
                else:
                    if layer in tmpLayers: 
                        tmpLayers.remove(layer)

        layers = tmpLayers
        tmpLayers = list(layers)


        ###If no matches, display a message
        if foundCount == 0:
            if len(channelsInput) == 0: nuke.message('empty string')
            else: nuke.message(str(channelsInput) + ' not in channels')

        ###add layers
        existingChan = existingChannels()
        for layer in layers:
            if layer not in existingChan:
                n['add_light_thru'].execute()
                nuke.selectedNode()['Achannels'].setValue(layer)

def addFromSample():
    ###get this node
    n = nuke.thisNode()

    ###get sampler position
    xpos = n['sample_pos'].value()[0]
    ypos = n['sample_pos'].value()[1]

    ###Get all the incoming channels
    allChannels = n.channels()

    ###Combine the channels into common layers
    layers = list(set([channel.split('.')[0] for channel in allChannels]))
    layers.sort()


    ###cull layers
    removelayers = ['rgb', 'rgba', 'alpha', 'depth', 'Z', 'clear_coat_direct', 'clear_coat_indirect', 'direct_diffuse', 'direct_specular', 'indirect_diffuse', 'indirect_specular', 'cputime', 'ID', 'opacity', 'motionvector', 'raycount', 'Normal', 'N', 'Normal_Camera_Space', 'Normal_World_Space', 'Pref', 'P', 'P_Camera_Space', 'P_World_Space', 'diffuse_color', 'direct_reflectivity', 'backlighting', 'caustics', 'glint', 'sheen_direct', 'other']

    for lyr in removelayers:
        if lyr in layers: layers.remove(lyr)

    ###Get RGB sum:
    rgbr = n.sample('rgb.red', xpos, ypos)
    rgbg = n.sample('rgb.green', xpos, ypos)
    rgbb = n.sample('rgb.blue', xpos, ypos)
    rgbsum = rgbr+rgbg+rgbb

    ###Get Layer Contributions
    contribs = []
    for layer in layers:
        chr = n.sample('.'.join([layer, 'red']), xpos, ypos)
        chg = n.sample('.'.join([layer, 'green']), xpos, ypos)
        chb = n.sample('.'.join([layer, 'blue']), xpos, ypos)
        chsum = chr + chg + chb
        ratio = (chsum / rgbsum) * 100
        if ratio > float(0.5):
            contribs.append(layer)

    ###add layers
    existingChan = existingChannels()
    for layer in contribs:
        if layer not in existingChan:
            n['add_light_thru'].execute()
            nuke.selectedNode()['Achannels'].setValue(layer)

def existingChannels():
    n = nuke.thisNode()
    channelKnobs = [n[k].value() for k in n.knobs() if '_link' in k]
    return channelKnobs
  
def makeMatte(node=None, method='single'):
    import nkGadget
    node = node if node else nuke.thisNode()
    with nuke.root():
        curSel = nuke.selectedNodes()
        nkSel.deSelAll()
        matte = None
        dot = nkGadget.dot(node=node, avg=False)
        if method == 'single':
              
            matteChans = matteChannels(node=node)
            p = nuke.Panel('pick matte')
            p.addEnumerationPulldown('mattes', ' '.join([matte for matte in matteChans]))
              
            cancelled = 1-p.show()
              
            if not cancelled:
                matte = nuke.nodes.Expression()
                matte['channel0'].setValue('rgba')
                matte['expr0'].setValue(p.value('mattes'))
          
        elif method == 'multi':
            matte = nuke.createNode('rfxMultiMatte')
        elif method == 'eye':
            matte = nuke.createNode('rfxEyeMatte')
        elif method == 'n':
            matte = nuke.createNode('NMatte')
        elif method == 'p':
            matte = nuke.createNode('rfxPointMatte')
        else:
            pass
        if matte:
            nkAlign.alignLeft(matte, node)
            matte.setInput(0, dot)
            node.setInput(1, matte)
            node['maskChannelMask'].setValue('rgba.alpha')
              
            n = node
            n.knobs()['maskChannelMask'].setVisible(True)
            n.knobs()['maskChannelInput'].setVisible(False)
            n['maskChannelInput'].setValue('none')
          
        nkSel.replace(curSel)
        return matte

def setMask(node=None):
    node = node if node else nuke.thisNode()
    with nuke.root():
        curSel = nuke.selectedNodes()
        nkSel.deSelAll()
        matte = None
        matteChans = matteChannels(node=node)
        p = nuke.Panel('pick matte')
        p.addEnumerationPulldown('mattes', ' '.join([matte for matte in matteChans]))
        cancelled = 1-p.show()
        
        if not cancelled:
            node['maskChannelInput'].setValue(p.value('mattes'))
            n = node
            n.knobs()['maskChannelMask'].setVisible(False)
            n.knobs()['maskChannelInput'].setVisible(True)
            n['maskChannelMask'].setValue('none')
        nkSel.replace(curSel)
  
def matteChannels(node=None):
    n = node if node else nuke.selectedNode()
    ###Get all the incoming channels
    allChannels = n.channels()

    ###Get Matte Layers
    matteChans = [''.join(chan.split('.')[1:]) for chan in allChannels if chan.startswith('other.')]
      
    rmPzlayers = list(matteChans)

    for layer in rmPzlayers:
        if 'Pz' in layer or 'PZ' in layer:
            if layer in matteChans: matteChans.remove(layer)
      
    return matteChans
  
