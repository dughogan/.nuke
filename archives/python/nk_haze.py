import nuke

def nodeChanged():
  k = nuke.thisKnob().name()
  if k in ('near_dist_setter', 'far_dist_setter'):
    updateDist(k)
  else:
    pass

def updateDist(k):
  
  n = nuke.thisNode()
  zn = nuke.toNode("Shuffle_Z")
  g = nuke.toNode("Grade_depth")
  
  near_xpos = n['near_dist_setter'].value()[0]
  near_ypos = n['near_dist_setter'].value()[1]
  
  far_xpos = n['far_dist_setter'].value()[0]
  far_ypos = n['far_dist_setter'].value()[1]
  
  z_near = zn.sample('rgba.red', near_xpos, near_ypos)
  z_far = zn.sample('rgba.red', far_xpos, far_ypos)
  
  if k == 'near_dist_setter':
    g['blackpoint'].setValue(z_near)
  else:
    g['whitepoint'].setValue(z_far)