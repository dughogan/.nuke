import re

from PyQt4 import QtGui, QtCore

from ui_lib.window import RDialog
from ui_lib import utils
from pipe_utils.list_utils import to_list

class RFXSearchableList(RDialog):
    """
    Searchable list of items.

    """
    def __init__(self, items=None, label='Searchable List', multi=False,
                parent=None):
        """
        Initialize an RFXSearchableList class.

        @type items: list
        @param items: List of items to display.
        @type label: str
        @param label: Label for the list.
        @type multi: bool
        @param multi: Whether to allow multiple selection or not.
        @type parent: QObject
        @param parent: Parent gui object.

        """
        super(RFXSearchableList, self).__init__()
        self.name = 'RFXSearchableList'
        self.items = items
        self.list_items = []

        filter_on = utils.get_icon('filters_on.png')
        self.filter_icon_on = QtGui.QIcon(filter_on)

        filter_off = utils.get_icon('filters_off.png')
        self.filter_icon_off = QtGui.QIcon(filter_off)

        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.sub_layout = QtGui.QHBoxLayout()
        self.sub_layout.setContentsMargins(0, 0, 0, 0)

        self.filter_button = QtGui.QPushButton()
        self.filter_button.setIcon(self.filter_icon_off)
        self.filter_button.setFixedSize(22, 22)
        self.filter_button.setFlat(True)

        self.isearch = QtGui.QLineEdit()

        self.ilist = QtGui.QListWidget()
        self.ilist.setSortingEnabled(True)
        if multi:
            self.ilist.setSelectionMode(
                    QtGui.QAbstractItemView.ExtendedSelection)
        else:
            self.ilist.setSelectionMode(
                    QtGui.QAbstractItemView.SingleSelection)

        self.main_layout.addLayout(self.sub_layout)
        self.main_layout.addWidget(self.ilist)
        self.sub_layout.addWidget(self.filter_button)
        self.sub_layout.addWidget(self.isearch)

        group_box = QtGui.QGroupBox(label)
        group_box.setLayout(self.main_layout)
        self.layout.addWidget(group_box)
        self.setLayout(self.layout)

        self.connect(self.filter_button, QtCore.SIGNAL('released()'),
                self.clear_filter)
        self.connect(self.isearch, QtCore.SIGNAL('textChanged(QString)'),
                self.filter_list)

        self.refresh_list()

        # self.centerWidget()

        self.start()

    def activate_filter_icon(self):
        """
        Activate the filter icon.

        @rtype: bool
        @returns: The result

        """
        if not self.filter_button.icon == self.filter_icon_on:
            self.filter_button.setIcon(self.filter_icon_on)

        return True

    def deactivate_filter_icon(self):
        """
        Deactivate the filter icon.

        @rtype: bool
        @returns: The result

        """
        if not self.filter_button.icon == self.filter_icon_off:
            self.filter_button.setIcon(self.filter_icon_off)

        return True

    def refresh_list(self):
        """
        Refresh the list of items with no filter.

        @rtype: bool
        @returns: The result

        """
        self.filter_list(None)

        return True

    def clear_filter(self):
        """
        Clear the filter field.

        @rtype: bool
        @returns: The result

        """
        self.isearch.setText('')
        self.filter_list('')

        return True

    def filter_list(self, s):
        """
        Filter the list based on the given text.

        @type s:str
        @param s: The string/expression to filter with.

        @rtype: bool
        @returns: The result

        """
        self.list_items = []
        regex = None
        if self.items:
            if s:
                s = '%s' % s.toAscii()
                if not s.endswith('\\'):
                    s.replace('*', '.*')
                    regex = re.compile(s, re.IGNORECASE)
                    self.activate_filter_icon()

            for item in self.items:
                if not regex or regex.search(str(item)):
                    list_item = QtGui.QListWidgetItem(str(item))
                    self.list_items.append(list_item)

        if regex:
            self.activate_filter_icon()
        else:
            self.deactivate_filter_icon()

        self.ilist.clear()
        for list_item in self.list_items:
            self.ilist.addItem(list_item)
        self.ilist.setCurrentRow(0, QtGui.QItemSelectionModel.ClearAndSelect)

        return True

    def get_selection(self):
        """
        Return the selected item(s).

        @rtype: list
        @returns: The item(s) selected.

        """
        result = []
        items = to_list(self.ilist.selectedItems())
        for item in items:
            as_string = item.text()
            if as_string:
                as_string = '%s' % as_string.toAscii()
            if as_string:
                result.append(as_string)

        return result

    def get_current_item(self):
        """
        Get a single selected object. The last object selected.

        @rtype: str
        @returns: The selected object.

        """
        result = None
        item = self.ilist.currentItem()
        if item:
            as_string = item.text()
            if as_string:
                as_string = '%s' % as_string.toAscii()
            if as_string:
                result = as_string

        return result

class ChannelBrowser(RDialog):
    def __init__(self, left, right, title='Channel Browser'):
        super(ChannelBrowser, self).__init__()
        self.name = 'ChannelBrowser'
        self.title=title
        self.setWindowTitle(self.title)

        self.left = None
        self.right = None

        self.main_layout = QtGui.QVBoxLayout()
        self.sub_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.sub_layout)
        self.left_widget = RFXSearchableList(left, 'Channel Knobs')
        self.right_widget = RFXSearchableList(right, 'All Channels')
        self.sub_layout.addWidget(self.left_widget)
        self.sub_layout.addWidget(self.right_widget)
        self.add_buttons()
        self.setLayout(self.main_layout)
        self.left_widget.isearch.setFocus()
        self.setTabOrder(self.left_widget.isearch, self.left_widget.ilist)
        self.setTabOrder(self.left_widget.ilist, self.right_widget.isearch)
        self.setTabOrder(self.right_widget.isearch, self.right_widget.ilist)

        # self.centerWidget()

        self.start()


    def add_buttons(self):
        """
        Add buttons to the channel browser. This can be overridden to nest
        the widget in another.

        @rtype: bool
        @returns: The result

        """
        self.ok_button = QtGui.QPushButton('ok')
        self.cancel_button = QtGui.QPushButton('cancel')
        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.button_layout)
        self.setTabOrder(self.right_widget.ilist, self.ok_button)
        self.connect(self.ok_button, QtCore.SIGNAL("clicked()"), self.ok)
        self.connect(self.cancel_button,
                QtCore.SIGNAL("clicked()"), self.cancel)

        return True

    def ok(self):
        """
        Slot called when ok button is activated.

        @rtype: bool
        @returns: The result

        """
        self.left = '%s' % (
                self.left_widget.ilist.currentItem().text().toAscii())
        self.right = '%s' % (
                self.right_widget.ilist.currentItem().text().toAscii())
        self.close()

        return True

    def cancel(self):
        """
        Slot called when cancel button activated.

        @rtype: bool
        @returns: The result

        """
        self.close()

        return True

