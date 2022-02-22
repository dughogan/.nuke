from PyQt4 import QtCore, QtGui
from ui_lib.utils import center_window_on

class RProgressDialog(QtGui.QProgressDialog):
    def __init__(self, message='', cancel=None, minimum=0,
                maximum=100):
        if not cancel:
            cancel = QtCore.QString()
        QtGui.QProgressDialog.__init__(self, message, cancel, minimum, maximum)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setMinimumDuration(0)
        screen = QtGui.QDesktopWidget().screenGeometry()
        size = self.geometry()
        center_window_on(self)

    def setLabelText(self, text):
        QtGui.QProgressDialog.setLabelText(self, text)
        QtCore.QCoreApplication.processEvents()

    def setValue(self, value):
        QtGui.QProgressDialog.setValue(self, value)
        QtCore.QCoreApplication.processEvents()
