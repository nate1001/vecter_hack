
from PyQt4 import QtCore, QtGui
from animation import OpacityAnimation
from animation import PropAnimation


class Direction(object):

    svg_viewed = ('sw', 'nw', 'se', 'ne')
    nonsvg_viewed = ('sw',)

    directions = {
        'ne': 'ne',
        'sw': 'sw',
        'se': 'se',
        'nw': 'nw',

        'n': 'ne',
        's': 'sw',

        'e': 'se',
        'w': 'nw',
    }


    @classmethod
    def toViewed(cls, direction):
        return cls.directions[direction]

    @classmethod
    def viewable(cls, use_svg):
        if use_svg:
            return cls.svg_viewed
        else:
            return cls.nonsvg_viewed


class ResetError(Exception):pass

class ResetItem(object):

    def __init__(self, tile_width):
        
        self._tile_width = tile_width
        self._attrs = {}
        for attr in self.attrs:
            self._attrs[attr] = None

    @property
    def tile_width(self): return self._tile_width

    def __getitem__(self, key):
        if key not in self._attrs.keys():
            raise ResetError("No attribute named {} for {}".format(repr(key), self))
        return self._attrs[key]

    def reset(self, item):
        self._initial = False
        for attr in self._attrs:
            self._attrs[attr] = getattr(item, attr)


class CharItem(QtGui.QGraphicsSimpleTextItem, ResetItem):
    
    attrs = ('color', 'char')
    
    def __init__(self, parent, tile_width, direction=None):
        super(CharItem, self).__init__('', parent)
        ResetItem.__init__(self, tile_width)

        font = self.font()
        font.setFamily('monospace')
        font.setPixelSize(tile_width * .8)
        self.setFont(font)

    def setBold(self):
        font = self.font()
        font.setWeight(QtGui.QFont.Black)
        self.setFont(font)

    def reset(self, item):
        super(CharItem, self).reset(item)

        self.setBrush(self['color'])
        self.setText(self['char'])

        s = float(self.tile_width)
        x,y = self.parentItem().center()
        off = self.font().pixelSize() / 2
        self.setPos(x - off/2, y - off)


class Action(QtGui.QAction):

    
    def __init__(self, parent, name, keys, callback, args=None):
        super(Action, self).__init__(name, parent)
        self.setShortcuts([QtGui.QKeySequence(k) for k in keys])
        self.callback = callback
        self._args = args
        self.triggered.connect(self._onTriggered)
        self.name = name
        self.keys = keys

    def _onTriggered(self):
        if self._args:
            self.callback(*self._args)
        else:
            self.callback()


class TextItem(QtGui.QGraphicsTextItem):
    point_size = 14
    def __init__(self, parent):
        super(TextItem, self).__init__(parent)
        font = self.font()
        font.setPointSize(self.point_size)
        self.setFont(font)


class TextWidget(QtGui.QGraphicsWidget):
    faded_opacity = .4
    padding = 3
    bg_color = QtGui.QColor(64,64,64,255)
    bg_color = QtGui.QColor('black')

    def __init__(self, timeout_seconds=0):
        super(TextWidget, self).__init__()

        self.setOpacity(self.faded_opacity)
        self.opaciter = OpacityAnimation(self)
        
        self.background = QtGui.QGraphicsRectItem(self)
        self.background.setBrush(QtGui.QBrush(self.bg_color))
        self.background.setPen(QtGui.QPen(QtGui.QColor(0,0,0,0)))

        self.item = TextItem(self)

        self._timer = None
        self.timeout_seconds = timeout_seconds


    def sizeHint(self, which, constraint=None):

        if which == QtCore.Qt.PreferredSize:
            rect = self.item.boundingRect()
            size = QtCore.QSizeF(rect.width(), rect.height())
        else:
            size = super(TextWidget, self).sizeHint(which, constraint)
        return size

    def setHtml(self, html):
        of = self.padding
        self.item.setHtml(html)
        rect = self.item.boundingRect()
        self.background.setRect(rect)
        self.updateGeometry()

    def show(self):
        if not self.opaciter.fadeTo(self.faded_opacity):
            self.opaciter.stop()
            self.opaciter.fadeTo(self.faded_opacity)
            
        if self.timeout_seconds:
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(self._hide)
            self.timer.setSingleShot(True)
            self.timer.start(self.timeout_seconds * 1000)

    def hide(self):
        if not self.opaciter.fadeTo(0):
            self.opaciter.stop()
            self.opaciter.fadeTo(0)


class TitledTextWidget(QtGui.QGraphicsWidget):
    
    padding = 5
    bg_color = QtGui.QColor('gray')
    bg_color.setAlpha(128)

    focus_pen = QtGui.QPen(QtGui.QColor('yellow'))
    focus_pen.color().setAlpha(128)

    focusable = True
    selectable = True

    lost_focus = QtCore.pyqtSignal(QtGui.QGraphicsWidget)
    gained_focus = QtCore.pyqtSignal(QtGui.QGraphicsWidget)
    
    def __init__(self, title, bg_color=bg_color):
        super(TitledTextWidget, self).__init__()

        self.title = title
        self.body = ''
        self.background = QtGui.QGraphicsRectItem(self)
        self.sizer = PropAnimation(self, 'size', force=True)

        if self.focusable:
            self.background.setPen(self.focus_pen)
            self._body_hidden = True
            if self.selectable:
                self.setFocusPolicy(QtCore.Qt.StrongFocus)
        else:
            self._body_hidden = False

        self._body_text = TextWidget()
        self._body_text.setParentItem(self)

        self._title_text = TextWidget()
        self._title_text.setParentItem(self)

        self.background.setBrush(QtGui.QBrush(bg_color))
        self.setHtml()

    def mousePressEvent(self, event):
        if not self.focusable:
            return
        if self._body_hidden:
            self.focusInEvent(None)
        else:
            self.focusOutEvent(None)

    def getSize(self): 
        return self.background.boundingRect().size()
    def setSize(self, size): 
        r = self.background.boundingRect()
        self.background.setRect(r.x(), r.y(), size.width(), size.height())
        self.updateGeometry()
    size = QtCore.pyqtProperty(QtCore.QSizeF, getSize, setSize)

    def focusInEvent(self, event):
        self._body_hidden = False
        self.background.setPen(self.focus_pen)
        self.setHtml()
        self.gained_focus.emit(self)

    def focusOutEvent(self, event):
        self._body_hidden = True
        self.background.setPen(QtGui.QPen(QtGui.QColor(0,0,0,0)))
        self.setHtml()
        self.lost_focus.emit(self)

    def sizeHint(self, which, constraint=None):

        rect = self.background.rect()
        size = QtCore.QSizeF(rect.width(), rect.height())
        return size

    def setHtml(self):

        self._title_text.setHtml(self.title)
        self._body_text.setHtml(self.body)

        tbox = self._title_text.item.boundingRect()
        bbox = self._body_text.item.boundingRect()

        x, y = min(tbox.x(), bbox.x()), min(tbox.y(), bbox.y())
        w = max(tbox.width(), bbox.width())
        h1, h2 = tbox.height(), bbox.height()

        if self._body_hidden:
            self._body_text.hide()
            h2, pad = 0, 0
        else:
            self._body_text.show()
            pad = self.padding

        self._body_text.setPos(self.padding, h1)
        rect = QtCore.QRectF(x, y, w, h1 + pad + h2)
        size = QtCore.QSizeF(rect.width(), rect.height())
        self.sizer.setup(size)
        self.sizer.start()





class SettingsWidget(QtGui.QTabWidget):
    
    def __init__(self):
        super(SettingsWidget, self).__init__()

        name = __NAME__.lower()
        self._qsettings = QtCore.QSettings(name, name)
        self._settings = []

        sections = {}
        for key in settings.keys():
            section = key.split('/')[0]
            sections[section] = None

        for section in sections.keys():
            self.addTab(section)

    def addTab(self, name):

        tab= QtGui.QWidget()
        layout = QtGui.QGridLayout()
        tab.setLayout(layout)

        i = 0
        for key, (value, klass, label) in settings.items():
            if key.split('/')[0] == name:
                self.addSetting(layout, key, value, klass, label, i)
                i += 1
        super(SettingsWidget, self).addTab(tab, name)

    def save(self):
        for setting in self._settings:
            self._qsettings.setValue(setting.key, setting.value)


    def addSetting(self, layout, key, value, klass, label, rownum):
        
        saved = self._qsettings.value(key)
        isnull = saved.isNull()

        # get the saved value or default to hard coded config
        if klass is int:
            value, ok = (settings[key], True) if isnull else saved.toInt() 
            if not ok:
                raise ValueError(value)
            widget = IntSettingWidget(key, value, klass, label)
        elif klass is str:
            value = settings[key] if isnull else saved.toString() 
            widget = TextSettingWidget(key, value, klass, label)
        elif klass is file:
            value = settings[key] if isnull else saved.toString() 
            widget = FileSettingWidget(key, value, klass, label)
        elif klass is bool:
            value = settings[key] if isnull else saved.toBool() 
            widget = BoolSettingWidget(key, value, klass, label)
        else:
            raise ValueError(klass)

        layout.addWidget(widget.text, rownum, 0)
        layout.addWidget(widget.edit, rownum, 1)
        self._settings.append(widget)


class SettingWidget(QtGui.QWidget):

    def __init__(self, key, value, klass, label):
        super(SettingWidget, self).__init__()

        self._key = key
        self._klass = klass
        self.text = QtGui.QLabel(label)

    @property
    def key(self):
        return self._key

    def value(self):
        raise NotImplementedError()


class TextSettingWidget(SettingWidget):
    def __init__(self, key, value, klass, label):
        self.edit = QtGui.QLineEdit(str(value))
        super(TextSettingWidget, self).__init__(key, value, klass, label)

    @property
    def value(self):
        return str(self.edit.text())

class FileSettingWidget(SettingWidget):
    
    class LineEdit(QtGui.QLineEdit):
        
        def __init__(self, text):
            super(FileSettingWidget.LineEdit, self).__init__(text)
            self.dialog = QtGui.QFileDialog()

            p = self.palette()
            self._valid = p.color(p.Text)
            self._invalid = QtGui.QColor('red')
            self.textChanged.connect(self._onTextChanged)

            try:
                os.stat(text)
                self.dialog.setDirectory(text)
            except OSError:
                pwd = os.getcwd()
                self.dialog.setDirectory(pwd)
                p.setColor(p.Text, self._invalid)
                self.setPalette(p)

            self.dialog.setOption(self.dialog.ShowDirsOnly)
            self.dialog.setFileMode(self.dialog.Directory)

        def _onTextChanged(self, text):
            p = self.palette()
            p.setColor(p.Text, self._valid)
            self.setPalette(p)


        def mousePressEvent(self, event):
            self.dialog.show()

    def __init__(self, key, value, klass, label):
        self.edit = self.LineEdit(str(value))
        self.edit.setReadOnly(True)
        self.edit.dialog.accepted.connect(self._onAccepted)
        super(FileSettingWidget, self).__init__(key, value, klass, label)

    def _onAccepted(self):
        path =  list(self.edit.dialog.selectedFiles())[0]
        self.edit.setText(path)

    @property
    def value(self):
        return str(self.edit.text())


class IntSettingWidget(SettingWidget):
    def __init__(self, key, value, klass, label):
        self.edit = QtGui.QLineEdit(str(value))
        validator = QtGui.QIntValidator()
        self.edit.setValidator(validator)
        super(IntSettingWidget, self).__init__(key, value, klass, label)

    @property
    def value(self):
        return str(self.edit.text())


class BoolSettingWidget(SettingWidget):
    def __init__(self, key, value, klass, label):
        self.edit = QtGui.QCheckBox()
        state = QtCore.Qt.Checked if value else QtCore.Qt.Unchecked
        self.edit.setCheckState(state)
        super(BoolSettingWidget, self).__init__(key, value, klass, label)

    @property
    def value(self):
        return bool(self.edit.checkState())


class SettingsForm(QtGui.QWidget):
    
    def __init__(self):
        super(SettingsForm, self).__init__()

        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.settings = SettingsWidget()

        button = QtGui.QPushButton('save')
        button.pressed.connect(self._onSave)

        layout.addWidget(self.settings)
        layout.addWidget(button)

    def _onSave(self):
        self.settings.save()



class Settings(QtCore.QSettings):
    
    def __init__(self, name, default):
        super(Settings, self).__init__(name, name)

        self._dic = {}
        for key in default:
            value, klass, label = default[key]
            self._dic[key] = (klass, label)
            if not self.contains(key):
                self.setValue(key, value)

    def beginGroup(self, group):
        raise NotImplementedError()

    def endGroup(self):
        raise NotImplementedError()

    def keys(self, group):

        super(Settings, self).beginGroup(group)
        keys = [str(name) for name in self.childKeys()]
        super(Settings, self).endGroup()
        return keys

    def __getitem__(self, args):
        
        group, key = args
        key = group + '/' + key
        
        if not self.contains(key):
            raise KeyError(key)

        value = self.value(key)
        klass, label = self._dic[key]
        ok = True
        if klass is int:
            value, ok = value.toInt()
        elif klass is float:
            value, ok = value.toFloat()
        elif klass is str:
            value = value.toString()
        elif klass is bool:
            value = value.toBool()
        else:
            raise ValueError(klass)

        if not ok:
            raise ValueError(value)

        return value

    def __setitem__(self, args, value):

        group, key = args
        key = group + '/' + key
        if not self.contains(key):
            raise KeyError(key)
        self.setValue(key, value)




