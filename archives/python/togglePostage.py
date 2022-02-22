

'''

Toggles the postage stamp knob of all Read nodes

'''

import nuke
import nukescripts

class simplePanel( nukescripts.PythonPanel ):
	def __init__( self ):
		nukescripts.PythonPanel.__init__( self, 'Toggle Postage Stamp')

		# CREATE KNOBS
		self.blank = nuke.Text_Knob('')
		self.showAll = nuke.PyScript_Knob('showAll', 'Show postage')
		self.hideAll = nuke.PyScript_Knob('hideAll', 'Hide postage')
		self.addKnob(self.blank)
		self.addKnob(self.showAll)
		self.addKnob(self.hideAll)
		self.addKnob(self.blank)

	def toggle( self, boolean ):
		for node in nuke.selectedNodes("Shuffle"):
			node['postage_stamp'].setValue(boolean)

	def knobChanged( self, knob ):
		if knob == self.showAll:
			print "Showing postage"
			self.toggle( 1 )

		elif knob == self.hideAll:
			print "Hiding postage"
			self.toggle( 0 )


def main():

	newPanel = simplePanel()
	newPanel.show()#ModalDialog()

