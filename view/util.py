
from PyQt4 import QtCore, QtGui
from animation import OpacityAnimation
from animation import PropAnimation


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
    bg_color = QtGui.QColor(0,0,0,0)

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

