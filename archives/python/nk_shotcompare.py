import nkCrawl
import nuke

def nodeUpdate(knob):
  k = knob.name()
  n = nuke.thisNode()
  if k == 'inputChange':
	for i in range(n.inputs()):
	  fframe = n.input(i).firstFrame() if n.input(i) else 0
	  lframe = n.input(i).lastFrame() if n.input(i) else 1
	  if i == 0:
		n['one_frm_slider'].setRange(fframe, lframe)
	  else:
		n['two_frm_slider'].setRange(fframe, lframe)
  if k == 'spotcheck_chk':
	if knob.value() == True:
	  n['spot'].setVisible(True)
	else:
	  n['spot'].setVisible(False)
  if k == 'colorcheck_chk':
	if knob.value() == True:
	  n['color'].setVisible(True)
	else:
	  n['color'].setVisible(False)
  if k == 'outmode':
	if knob.value() == 'Interleaved':
	  n['interleaf_grp'].setVisible(True)
	else:
	  n['interleaf_grp'].setVisible(False)
		