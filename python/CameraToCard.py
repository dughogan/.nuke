import re
import nuke

def clear(nodes = None):
    nodes = nodes if nodes else nuke.selectedNodes()
    
    animatedKnobs = [node[knob] for node in nodes for knob in node.knobs() if node[knob].isAnimated()]
    
    for k in animatedKnobs:
        k.clearAnimated()
    
    return

def CameraToCard():
  
  #store selections
  camSelect = nuke.selectedNodes( "Camera" )
  camSelectPosY = nuke.selectedNode().ypos()
  camName = nuke.selectedNode().name()

  nuke.nodeCopy('%clipboard%')
  
  #create Group
  GroupVar = nuke.nodes.Group()
  GroupVar.begin()
  VarIn = nuke.nodes.Input()
  CamIn = nuke.nodes.Input()
  VarOut = nuke.nodes.Output() 
  inputName = 'img'
  caminputName = 'camera'
  info = nuke.Text_Knob('instructions', '', '<br></br>Sample the Z value of your EXRs Depth AOV <br></br>in the spot you want the card to track from. <br></br>Some adjustment may be required of this<br></br> value if a tighter track is needed! <br></br>So check multiple frames if you have an animated camera. ')
  divider = nuke.Text_Knob('divider', ' ', ' ')
  z_depth = nuke.Double_Knob('card_depth', 'Set Card Z-Depth')
  
  #set knob values
  z_depth.setRange(1,5000)
  
  #create Group user knobs
  GroupVar.addKnob(info)
  GroupVar.addKnob(divider)
  GroupVar.addKnob(z_depth)
  

  #create the nodes
  mkcam = nuke.nodePaste('%clipboard%')
  clear()
  mkproj = nuke.nodes.Project3D()
  mkcard = nuke.nodes.Card()
  mktrans = nuke.nodes.TransformGeo()
  mkdot = nuke.nodes.Dot()
  mkscanline = nuke.nodes.ScanlineRender()
  mkmotionblur = nuke.nodes.MotionBlur3D()
  mkvector = nuke.nodes.VectorBlur()
  

  #count the projCams
  i = 0
  projName = 'ProjCam0'
  while nuke.toNode('ProjCam%s' % i):
    i += 1
    projName = 'ProjCam%s' % i
  
  #count the groups
  i = 1
  groupName = 'rfxDepthCard1' 
  while nuke.toNode('rfxDepthCard%s' % i):
    i += 1
    groupName = 'rfxDepthCard%s' % i     

  #store current frame
  curFrame = nuke.frame()

  #set values
  mkcam['label'].setValue( '%s' % curFrame )
  mkcam['name'].setValue(projName)
  mkcam['tile_color'].setValue(169550)
  mkcam['gl_color'].setValue(169550)
  mkcard['z'].setValue(100)
  mktrans['scaling'].setValue(1.1)
  GroupVar['name'].setValue(groupName)
  GroupVar['label'].setValue( '%s' % curFrame )
  GroupVar['tile_color'].setValue(169550)
  GroupVar['gl_color'].setValue(169550)
  VarIn['name'].setValue(inputName)
  CamIn['name'].setValue(caminputName)
  GroupVar['card_depth'].setValue(1)
  mkvector['uv'].setValue('motion')

  #set card expressions
  mkcard['z'].setExpression('parent.card_depth')
  mkcard['lens_in_focal'].setExpression('%s.focal' % projName)
  mkcard['lens_in_haperture'].setExpression('%s.haperture' % projName)
  
  #set vector expressions
  mkmotionblur['distance'].setExpression('parent.card_depth')

  #setup the inputs
  mkcam.setInput(0, None)
  mkproj.setInput(1, mkcam)
  mkcard.setInput(0, mkproj)
  mktrans.setInput(1, mkdot)
  mkdot.setInput(0, mkcam)
  mktrans.setInput(0, mkcard)
  mkproj.setInput(0, VarIn) 
  mkscanline.setInput(1, mktrans)
  mkscanline.setInput(2, CamIn)
  mkmotionblur.setInput(0, mkscanline)
  mkmotionblur.setInput(1, CamIn)
  mkvector.setInput(0, mkmotionblur)
  VarOut.setInput(0, mkvector)  

  #select the newly created nodes
  mkcam.knob('selected').setValue(True) 
  mkproj.knob('selected').setValue(True) 
  mkcard.knob('selected').setValue(True) 
  mktrans.knob('selected').setValue(True) 
  mkdot.knob('selected').setValue(True)
  mkscanline.knob('selected').setValue(True)
  VarIn.knob('selected').setValue(True)
  VarOut.knob('selected').setValue(True)
  CamIn.knob('selected').setValue(True)

  #store node positions
  cardPosY = mkcard.ypos()
  transPosY = mktrans.ypos()
  projPosY = mkproj.ypos()
  dotPosX = mkdot.xpos()
  dotPosY = mkdot.ypos()
  VarInX = VarIn.xpos()
  VarInY = VarIn.ypos()
  VarOutX = VarIn.xpos()
  VarOutY = VarIn.ypos()
  CamInX = CamIn.xpos()
  CamInY = CamIn.ypos()
  scanlineX = mkscanline.xpos()
  scanlineY = mkscanline.ypos()

  #position the nodes
  mkcard['ypos'].setValue( cardPosY + 40 )
  mktrans['ypos'].setValue( transPosY + 80 )
  mkdot['ypos'].setValue( dotPosY + 80 )
  VarIn['ypos'].setValue( projPosY + 40 )
  mkscanline['ypos'].setValue( transPosY + 40 )
  CamIn['ypos'].setValue( scanlineY + 40 )
  CamIn['xpos'].setValue ( scanlineX + 40 )
  VarOut['ypos'].setValue( scanlineY + 40 )

  GroupVar.end()

  #deselect all the new nodes
  mkcam.knob('selected').setValue(False) 
  mkproj.knob('selected').setValue(False) 
  mkcard.knob('selected').setValue(False) 
  mktrans.knob('selected').setValue(False) 
  mkdot.knob('selected').setValue(False)
  mkscanline.knob('selected').setValue(False)
  VarIn.knob('selected').setValue(False)
  VarOut.knob('selected').setValue(False)
  CamIn.knob('selected').setValue(False)

  #restore original selection
  n = nuke.toNode('%s' % camName)
  n['selected'].setValue(True)  
  
  return

def cardfromcamera():  
  CameraToCard()