
import sys
import re

from PyQt4 import QtGui, QtCore

from pipe_utils import string_utils
from ui_lib.window import RWidget
import ui_lib.utils

class RTextEdit(QtGui.QTextEdit):
    """
    Text Edit widget
    """
    def __init__(self, text=None, parent=None):
        if not text:
            text = ''
        QtGui.QTextEdit.__init__(self, text, parent)
        self.default_text = text
        #self.setTextColor(QtGui.QColor(150, 150, 150))
        #self.setFontItalic(True)
        self.setText(self.default_text)
        self.is_new = True

    def focusInEvent(self, event):
        QtGui.QTextEdit.focusInEvent(self,event)
        text = str(self.toPlainText())
        if text == self.default_text:
            self.setText('')
            self.is_new = False

class ROptionWidget(RWidget):
    """
    Custom widget to easily create a table of fields and their labels.
    Takes a list of one item dictionaries and creates a widget of corresponding
    QLabels and QDoubleSpinBox/QSpinBox/QLineEdit widgets.  The dictionary
    key represents the label and the value will be the value of the item.

    """
    def __init__(self, *args, **kwargs):
        """
        Instantiates an RFXOptionListWidget widget.

        @type options: list
        @param options: List of widgets and their values in dictionary form.
        @type parent: QtObject
        @param parent: The parent of this widget instance.

        """
        self._widgets = {}
        self._value = {}
        self.options = kwargs.pop('options')
        self.title = kwargs.pop('title', 'Options')
        checkable = kwargs.pop('checkable', False)
        checked = kwargs.pop('checked', True)
        RWidget.__init__(self, *args, **kwargs)

        group_box = QtGui.QGroupBox(self.title)
        if checkable is True:
            group_box.setCheckable(True)
            group_box.setChecked(checked)

        main_layout = QtGui.QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.addWidget(group_box)
        layout = QtGui.QFormLayout()
        group_box.setLayout(layout)

        # iterate thorugh the options
        for option in self.options:

            # check for dict data types only
            if not isinstance(option, dict):
                continue

            custom_type = option.get('type')
            label = option.get('label')
            label_widget = QtGui.QLabel(string_utils.totitle(label))

            if self.has_widget(label):
                continue
            value = option.get('value')
            if custom_type:
                custom_class = eval(custom_type)
                value_widget = custom_class(value)
                value_function = eval('value_widget.{0}'.format(option.get('value_function')))
            elif isinstance(value, str):
                value_widget = QtGui.QLineEdit(value)
                value_function = value_widget.text
                if 'regex' in option:
                    reg = QtCore.QRegExp(option.get('regex'))
                    framerangevalidator = QtGui.QRegExpValidator()
                    framerangevalidator.setRegExp(reg)
                    value_widget.setValidator(framerangevalidator)
            elif isinstance(value, float):
                value_widget = QtGui.QDoubleSpinBox()
                decimals = 1
                split = str(value).split('.')
                if len(split) > 1:
                    decimals = len(str(value).split('.')[-1])
                value_widget.setDecimals(decimals)
                value_widget.setRange(option.get('minimum', 0),
                                option.get('maximum', (value + value)))
                value_widget.setValue(value)
                value_function = value_widget.value
            elif isinstance(value, bool):
                value_widget = QtGui.QCheckBox()
                value_widget.setChecked(value)
                value_function = value_widget.isChecked
            elif isinstance(value, int):
                value_widget = QtGui.QSpinBox()
                value_widget.setRange(option.get('minimum', 0),
                                option.get('maximum', (value + value)))
                value_widget.setValue(value)
                value_function = value_widget.value
            elif isinstance(value, list):
                value_widget = QtGui.QComboBox()
                value_widget.addItems(value)
                value_function = value_widget.currentText

            layout.addRow(label_widget, value_widget)

            self._widgets[label] = value_widget
            self._value[label] = value_function

    def get_widget(self, item, default=None):
        result = default
        if item in self:
            result = self._widgets.get(item)

        return result

    def get_value(self, item, default=None):
        tmp = self._value.get(item)
        value = tmp()
        if isinstance(value, QtCore.QString):
            value = str(value)

        return value

    def get_values(self):
        values = {}
        for label in self.labels():
            values[label] = self.get_value(label)

        return values

    def has_widget(self, label):

        return label in self.labels()

    def labels(self):
        return self._widgets.keys()

    def __contains__(self, item):
        result = False
        if isinstance(item, str):
            result = item in self.labels()

        return result

class RSearchableListWidget(RWidget):
    def __init__(self, *args, **kwargs):
        self.contents = []
        if kwargs.has_key('contents'):
            self.contents = kwargs.pop('contents')
        super(RWidget, self).__init__(*args, **kwargs)

        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)

        if not kwargs.get('spacing') == None:
            self.setSpacing(kwargs.get('spacing'))
        if not kwargs.get('margin') == None:
            margin = kwargs.get('margin')
            if isinstance(margin, (list, tuple)):
                self.setContentsMargins(*margin)
            elif isinstance(margin, (int, float)):
                self.setMargin(margin)

        self.line_edit = QtGui.QLineEdit(self)
        self.list_widget = QtGui.QListWidget(self)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.list_widget)

        self.connect(self.line_edit, QtCore.SIGNAL("textChanged(QString)"),
                     self.line_edit_changed)
        self.connect(self.line_edit, QtCore.SIGNAL("textEdited(QString)"),
                     self.line_edit_changed)

        self.connect(self.list_widget, QtCore.SIGNAL("itemSelectionChanged()"), self.selection_changed)

        self.list_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self.list_widget, QtCore.SIGNAL('customContextMenuRequested(const QPoint&)'),
                     self.right_click)

        self.setContents()

    def setSpacing(self, spacing):
        self.layout().setSpacing(spacing)

        return 0

    def setContentsMargins(self, *args):
        # Left, Right, Top, Bottom
        self.layout().setContentsMargins(args[0], args[1], args[2], args[3])

        return 0

    def setMargin(self, *args):
        self.layout().setMargin(args[0])

        return 0

    def right_click(self, point):
        signal = QtCore.SIGNAL('customContextMenuRequested')
        self.emit(signal, self, point)

    def selection_changed(self):
        selected = self.selected()

        signal = QtCore.SIGNAL('selectionChanged')
        self.emit(signal, self, selected)

    def setContents(self, contents=None):
        if contents:
            self.contents = contents
        self.list_widget.clear()
        for item in self.contents:
            if isinstance(item, str):
                self.list_widget.addItem(item)
            elif isinstance(item, dict):
                name = item.get('name')
                tip = item.get('tooltip')
                background = item.get('background')
                foreground = item.get('foreground')
                widget = QtGui.QListWidgetItem(name)
                if tip:
                    widget.setToolTip(tip)
                if background:
                    color = QtGui.QColor(background[0], background[1], background[2], background[3])
                    brush = QtGui.QBrush(color)
                    widget.setBackground(brush)
                if foreground:
                    color = QtGui.QColor(foreground[0], foreground[1], foreground[2], foreground[3])
                    brush = QtGui.QBrush(color)
                    widget.setForeground(brush)
                self.list_widget.addItem(widget)

    def setVisible(self, visible=None):
        if isinstance(visible, (list, tuple)):
            self.list_widget.clear()
            for item in visible:
                widget = item
                if isinstance(item, dict):
                    name = item.get('name')
                    tip = item.get('tooltip')
                    background = item.get('background')
                    foreground = item.get('foreground')
                    widget = QtGui.QListWidgetItem(name)
                    if tip:
                        widget.setToolTip(tip)
                    if background:
                        color = QtGui.QColor(background[0], background[1], background[2], background[3])
                        brush = QtGui.QBrush(color)
                        widget.setBackground(brush)
                    if foreground:
                        color = QtGui.QColor(foreground[0], foreground[1], foreground[2], foreground[3])
                        brush = QtGui.QBrush(color)
                        widget.setForeground(brush)

                self.list_widget.addItem(widget)

        elif isinstance(visible, bool):
            super(RSearchableListWidget, self).setVisible(visible)

    def addItem(self, item):
        self.contents.append(item)
        self.setContents()

    def line_edit_changed(self, value):

        value = str(value)
        if value:
            regex = re.compile('%s' % (value), re.I)
            new_list = []
            for item in self.contents:
                name = item
                if isinstance(item, dict):
                    name = item.get('name')

                if regex.search(name):
                    new_list.append(item)

            self.setVisible(visible=new_list)
        else:
            self.setContents()

    def selectionMode(self):
        return self.list_widget.selectionMode()

    def clear(self):
        return self.list_widget.clear()

    def setCurrentIndex(self, index):
        return self.list_widget.setCurrentIndex(index)

    def currentItem(self):
        return self.list_widget.currentItem()

    def insertItem(self, i, item):
        return self.list_widget.insertItem(i, item)

    def setSelectionMode(self, selection_mode):
        self.list_widget.setSelectionMode(selection_mode)

    def selected(self):
        items = self.list_widget.selectedItems()
        names = [str(tmp.text()) for tmp in items]

        return names

    def selectedItems(self):
        items = self.list_widget.selectedItems()

        return self.list_widget.selectedItems()

    @classmethod
    def GetUserSelection(self, contents, multi_selection=True):
        dialog = ui_lib.BaseDialog()
        layout = QtGui.QVBoxLayout()
        dialog.setLayout(layout)

        list_widget = RSearchableListWidget(contents=contents)
        list_widget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        if multi_selection:
            list_widget.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        layout.addWidget(list_widget)

        ok_button = QtGui.QPushButton('ok')
        layout.addWidget(ok_button)

        dialog.connect(ok_button, QtCore.SIGNAL('clicked()'), dialog.close)

        dialog.exec_()

        return list_widget.selected()

class RDisplayResponseList(RWidget):
    def __init__(self, *args, **kwargs):
        self.responses = kwargs.pop('responses')
        if 'no_payloads' in kwargs:
            self.no_payloads = kwargs.pop('no_payloads')
        else:
            self.no_payloads = None
        super(RWidget, self).__init__(*args, **kwargs)

        main_layout = QtGui.QVBoxLayout(self)
        self.contents_layout = QtGui.QVBoxLayout()
        self.button_layout = QtGui.QHBoxLayout()

        main_layout.addLayout(self.contents_layout)
        main_layout.addLayout(self.button_layout)

        self.build_fail_widget()
        self.build_warning_widget()
        self.build_success_widget()
        self.build_buttons()

        main_layout.setSpacing(0)
        main_layout.setMargin(0)
        self.contents_layout.setSpacing(0)
        self.contents_layout.setMargin(0)
        self.button_layout.setSpacing(5)
        self.button_layout.setMargin(5)

        self.resize(1150, 520)

        self.center_window()

        self.start()

    def center_window(self):
        center_point = ui_lib.utils.get_screen_center(0)

        half_size = QtCore.QPoint(self.width()/2, self.height()/2)
        def_position = center_point - half_size
        self.move(def_position)
        # self.move(0, 0)

    def build_buttons(self):
        close = QtGui.QPushButton('close')

        self.button_layout.addWidget(close)

        signal = QtCore.SIGNAL('clicked()')
        self.connect(close, signal, self.close)

    def build_fail_widget(self):

        failures = self.responses.failures()
        fail_button = QtGui.QPushButton('Failures ( {0} )'.format(len(failures)))
        text_items = [item.message for item in failures]
        fail_widget = RSearchableListWidget(contents=text_items)

        self.contents_layout.addWidget(fail_button)
        self.contents_layout.addWidget(fail_widget)

        fail_button.setStyleSheet("QPushButton {background-color : red; color: black}")
        # signal = QtCore.SIGNAL('clicked()')
        # self.connect(fail_button, signal, fail_widget.toggle_visibility)

    def build_warning_widget(self):

        warnings = self.responses.warnings()
        warning_button = QtGui.QPushButton('Warnings ( {0} )'.format(len(warnings)))
        text_items = [item.message for item in warnings]
        warning_widget = RSearchableListWidget(contents=text_items)

        self.contents_layout.addWidget(warning_button)
        self.contents_layout.addWidget(warning_widget)

        warning_button.setStyleSheet("QPushButton {background-color : orange; color: black}")

        # signal = QtCore.SIGNAL('clicked()')
        # self.connect(warning_button, signal, warning_widget.toggle_visibility)

    def build_success_widget(self):

        successes = self.responses.successes()
        success_button = QtGui.QPushButton('Successes ( {0} )'.format(len(successes)))
        if self.no_payloads:
            text_items = ['{0}'.format(item.message) for item in successes]
        else:
            text_items = ['{0} ID {1}'.format(item.message, item.payload.job_id) for item in successes]
        success_widget = RSearchableListWidget(contents=text_items)

        self.contents_layout.addWidget(success_button)
        self.contents_layout.addWidget(success_widget)

        success_button.setStyleSheet("QPushButton {background-color : green; color : black}")
        # signal = QtCore.SIGNAL('clicked()')
        # self.connect(success_button, signal, success_widget.toggle_visibility)

    def resize_position(self, value):

        position = self.position()
        width = self.width()
        height = self.height()

