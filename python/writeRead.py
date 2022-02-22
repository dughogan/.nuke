import os
import nuke

#####################################################################################    
#####     Original plug-in written by Diogo Girondi (diogogirondi@gmail.com)    #####
#####     Rewritten and Modified by Doug Hogan for Speedshape Inc. (10/17/08)   #####
##################################################################################### 

def writeRead():

############################################    
###### Creates Read nodes from Writes ######
############################################ 
    
    n = nuke.selectedNodes("Write")

    if n != []:
        for i in n:
            
            ## get values from Write knobs
            file = i.knob('file').value()
            proxy = i.knob('proxy').value()
            colorspace = i.knob('colorspace').value()
            premult = i.knob('premultiplied').value()
            rawdata = i.knob('raw').value()
            xpos = i.knob('xpos').value()
            ypos = i.knob('ypos').value()
            
            ## Checks if there is an output set in the node
            if file == '' and proxy == '':
                continue
                
            ## Temp.knobs
            firstk = nuke.Int_Knob("first", "F")
            lastk = nuke.Int_Knob("last", "L")
            first = i.addKnob(firstk)
            last = i.addKnob(lastk)
            i.knob('first').setExpression('input.first_frame', 0)
            i.knob('last').setExpression('input.last_frame', 0)
            firstk = i['first']
            lastk = i['last']
            tab = i['User']
            label = ("[value first]-[value last]")
            
            ## First and Last frames
            firstFrame = nuke.expression( nuke.selectedNode().name() + '.first_frame' )
            lastFrame = nuke.expression( nuke.selectedNode().name() + '.last_frame' )
                        
            ## Removes Temp.knobs
            i.removeKnob(firstk)
            i.removeKnob(lastk)
            i.removeKnob(tab)
            
            ## Brings args to nuke.createNode()
            args = 'file {%s} proxy {%s} first %s last %s colorspace %s premultiplied %s raw %s' % (file, proxy, firstFrame, lastFrame, colorspace, premult, rawdata)
            
            ## Creates the Read node and moves it below the Write node
            write = nuke.createNode('Read', args)
            nuke.inputs(write,0)
            write.knob('label').setValue(label)
            write.knob('xpos').setValue(xpos)
            write.knob('ypos').setValue(ypos + 80)
            
    else:
        nuke.message("writeRead Error:\n\nNo Write nodes selected!")