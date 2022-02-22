#

import nuke
import nukescripts


class contactToolPanel(nukescripts.PythonPanel):

    def __init__(self):
        nukescripts.PythonPanel.__init__(
            self, 'Contact Sheet Controls', 'com.ohufx.contactSheet_toolsPanel')

        # ----------------------#
        #  Contact Sheets Tool  #
        # ----------------------#
        # ============================================#
        self.tab_contact = nuke.Tab_Knob('Sheet Tools')

        self.btn_updateReads = nuke.PyScript_Knob('updateReads', 'Update Selected Shots')
        self.btn_updateReads.setCommand(
            "import plutonium.contact_sheets.nk_contactSheet_utils as nk_contactSheet_utils;nk_contactSheet_utils.updateSelectedReads()")
        self.btn_recordInsightArtist = nuke.PyScript_Knob(
            'recordInsightArtist', 'Update Selected Artist Labels')
        self.btn_recordInsightArtist.setCommand(
            "import plutonium.contact_sheets.nk_contactSheet_utils as nk_contactSheet_utils;nk_contactSheet_utils.updateArtist()")
        # Divider
        self.sep2 = nuke.Text_Knob('', '@b;Sorting')
        self.sep2.setFlag(nuke.STARTLINE)

        self.btn_sortArtist = nuke.PyScript_Knob(
            'sortArtist', 'Create Artist Shot Groups')
        self.btn_sortArtist.setCommand(
            "import plutonium.contact_sheets.nk_contactSheet_utils as nk_contactSheet_utils;nk_contactSheet_utils.groupByArtist()")
        self.btn_sortArtist.clearFlag(nuke.STARTLINE)
        # Divider
        self.sep6 = nuke.Text_Knob('', '@b;HUD Toggles')

        self.btn_hud_sbs = nuke.PyScript_Knob('hud_sbs', 'SBS First / Last Frame')
        self.btn_hud_sbs.setCommand(
            "import plutonium.contact_sheets.nk_contactSheet_utils as nk_contactSheet_utils;nk_contactSheet_utils.SideBySide()")

        self.btn_hud_swap = nuke.PyScript_Knob('hud_sbs', 'SWAP First / Last Frame')
        self.btn_hud_swap.setCommand(
            "import plutonium.contact_sheets.nk_contactSheet_utils as nk_contactSheet_utils;nk_contactSheet_utils.FirstLastSwap()")

        self.btn_hud_color = nuke.PyScript_Knob('hud_color', 'Status Border')
        self.btn_hud_color.setCommand(
            "import plutonium.contact_sheets.nk_contactSheet_utils as nk_contactSheet_utils;nk_contactSheet_utils.InsightColorBorder()")

        self.btn_hud_warning = nuke.PyScript_Knob('hud_warning', 'Warning Border')
        self.btn_hud_warning.setCommand(
            "import plutonium.contact_sheets.nk_contactSheet_utils as nk_contactSheet_utils;nk_contactSheet_utils.WarningBorder()")
        self.btn_hud_warning.setFlag(nuke.STARTLINE)

        self.btn_hud_reset = nuke.PyScript_Knob('hud_reset', '@b;Reset HUDs')
        self.btn_hud_reset.setCommand(
            "import plutonium.contact_sheets.nk_contactSheet_utils as nk_contactSheet_utils;nk_contactSheet_utils.hud_reset()")
        self.btn_hud_reset.clearFlag(nuke.STARTLINE)
        # Divider
        self.sep3 = nuke.Text_Knob('', '@b;Insight')

        self.btn_openBrowser = nuke.PyScript_Knob(
            'openBrowser', 'Open Selected in Insight')
        self.btn_openBrowser.setFlag(nuke.STARTLINE)
        self.taskKnob = nuke.Enumeration_Knob('task', '', ['lit', 'comp'])
        self.taskKnob.clearFlag(nuke.STARTLINE)

        self.btn_addComment = nuke.PyScript_Knob('addComment', 'Give Artist Notes')
        self.btn_addComment.setCommand(
            "import plutonium.contact_sheets.nk_contactSheet_utils as nk_contactSheet_utils;nk_contactSheet_utils.insightComment()")

        # Add the knobs for "contactSheets" tab
        self.addKnob(self.tab_contact)
        self.addKnob(self.btn_updateReads)
        self.addKnob(self.btn_recordInsightArtist)
        self.addKnob(self.sep2)  # Divider
        self.addKnob(self.btn_sortArtist)
        self.addKnob(self.sep6)  # Divider
        self.addKnob(self.btn_hud_sbs)
        self.addKnob(self.btn_hud_swap)
        self.addKnob(self.btn_hud_color)
        self.addKnob(self.btn_hud_warning)
        self.addKnob(self.btn_hud_reset)
        self.addKnob(self.sep3)  # Divider
        self.addKnob(self.btn_openBrowser)
        self.addKnob(self.taskKnob)
        self.addKnob(self.btn_addComment)

    def knobChanged(self, knob):

        if nuke.thisKnob().name() == 'openBrowser':
            import plutonium.contact_sheets.nk_contactSheet_utils as cs
            task = int(self.taskKnob.getValue())
            cs.insightWeb(task)

def main():
    p = contactToolPanel()
    p.setMinimumSize(600, 400)
    p.show()
