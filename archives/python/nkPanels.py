import nuke
import nukescripts
import threading
import nkReport as report
import nkEval as nke
import nkGraph as graph
import nkSel as select
import nkFixit

def main():
  print "this does nothing"

def reportPanel(listType, nlist, tips_text, fixit_tool, isReport = True):
  niceNames = []
  for n in nlist:
	niceNames.append(n.name())
  class ReportPanel(nukescripts.PythonPanel):
	def __init__(self):
	  nukescripts.PythonPanel.__init__(self, 'Node Report')
	  self.firstRun = False
	  if isReport:
		self.reportTxt1 = nuke.Text_Knob('reportTxt1', '', str(len(nlist)) + ' nodes found \n')
		self.addKnob(self.reportTxt1)
	  self.selectButton = nuke.PyScript_Knob('selectButton', ' Select All Nodes ')
	  self.whiteListButton = nuke.PyScript_Knob('whtlstButton', ' Add Node(s) to Whitelist ')
	  self.greyListButton = nuke.PyScript_Knob('greylstButton', ' Remove From Whitelist ')
	  self.descTxt = nuke.Text_Knob('desctxt', '', listType)
	  self.enumList = nuke.Enumeration_Knob('nodeListPanel', '', niceNames)
	  self.prevBtn = nuke.PyScript_Knob('prevbtn', ' << Zoom to Prev ')
	  self.nextBtn = nuke.PyScript_Knob('nextbtn', ' Zoom to Next >> ')
	  self.divider = nuke.Text_Knob('divider', ' ')
	  self.addKnob(self.descTxt)
	  self.addKnob(self.enumList)
	  self.enumList.setFlag(nuke.STARTLINE)
	  self.addKnob(self.prevBtn)
	  self.prevBtn.setFlag(nuke.STARTLINE)
	  self.addKnob(self.nextBtn)
	  self.addKnob(self.selectButton)
	  self.selectButton.setFlag(nuke.STARTLINE)
	  if fixit_tool:
	    self.fixitButton = nuke.PyScript_Knob('fixit', fixit_tool[1], fixit_tool[0])
	    self.addKnob(self.fixitButton)
	    self.fixitButton.setFlag(nuke.STARTLINE)
	  self.addKnob(self.whiteListButton)
	  self.whiteListButton.setFlag(nuke.STARTLINE)
	  self.addKnob(self.greyListButton)
	  self.addKnob(self.divider)
	  self.divider.setFlag(nuke.STARTLINE)
	  if isReport:
		tipsTextList = tips_text.split('<br>')
		print tipsTextList
		for i, tips in enumerate(tipsTextList):
		  self.reportTxt2 = nuke.Text_Knob('rtxt2', '', tips )
		  self.addKnob(self.reportTxt2)
		self.reportEnd = nuke.Text_Knob('')
		self.addKnob(self.reportEnd)
	  

	  
	def knobChanged(self, knob):
	  if len(self.enumList.values()) > 0:
		i = self.enumList.values().index(self.enumList.value())
		if knob == self.prevBtn:
		  i = i - 1
		  if i < 0:
			i = len(self.enumList.values()) - 1
		  self.enumList.setValue(i)
		  n = nuke.toNode(self.enumList.value())
		  try:
			graph.focus(n)
			select.replace(n)
		  except:
			pass
		if knob == self.nextBtn:
		  i = i + 1
		  if i > len(self.enumList.values()) - 1:
			i = 0
		  self.enumList.setValue(i)
		  n = nuke.toNode(self.enumList.value())
		  try:
			graph.focus(n)
			select.replace(n)
		  except:
			pass
		if knob == self.selectButton:
		  select.replace(nlist)
		if knob == self.enumList:
		  if not self.firstRun:
			n = nuke.toNode(self.enumList.value())
			graph.focus(n)
			select.replace(n)
		  else:
			self.firstRun = False
		if knob == self.whiteListButton:
		  nodes = nuke.selectedNodes()
		  if nodes:
			for n in nodes:
			  if 'whitelist' in set(n.knobs()):
				n['whitelist'].setValue(True)
				n['whitelist'].setFlag(nuke.DISABLED)
				n['whitelist'].setFlag(nuke.ALWAYS_SAVE)
			  else:
				k = nuke.Boolean_Knob('whitelist', 'O+R White List', True)
				k.setFlag(nuke.DISABLED)
				k.setFlag(nuke.ALWAYS_SAVE)
				n.addKnob(k)
		if knob == self.greyListButton:
		  nodes = nuke.selectedNodes()
		  if nodes:
			for n in nodes:
			  if 'whitelist' in set(n.knobs()):
				n.removeKnob(n['whitelist'])
			  else:
				pass

  p = ReportPanel()
  return p

