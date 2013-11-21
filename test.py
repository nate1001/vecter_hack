

from PyQt4 import QtCore, QtGui, QtSvg, QtXml
from view.animation import OpacityAnimation
from view.animation import PropAnimation


class TextItem(QtGui.QGraphicsTextItem):
    point_size = 14
    def __init__(self, parent):
        super(TextItem, self).__init__(parent)
        font = self.font()
        font.setPointSize(self.point_size)
        self.setFont(font)


class TextWidget(QtGui.QGraphicsWidget):
    faded_opacity = .7
    padding = 3

    def __init__(self, timeout_seconds=0):
        super(TextWidget, self).__init__()

        self.setOpacity(self.faded_opacity)
        self.opaciter = OpacityAnimation(self)
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
    bg_color = QtGui.QColor('blue')
    bg_color.setAlpha(128)

    focus_pen = QtGui.QPen(QtGui.QColor('yellow'))
    focus_pen.color().setAlpha(128)
    
    def __init__(self, title, body, bg_color=bg_color):
        super(TitledTextWidget, self).__init__()

        self.title = title
        self.body = body
        self.background = QtGui.QGraphicsRectItem(self)
        self.sizer = PropAnimation(self, 'size')

        self._body_text = TextWidget()
        self._body_text.setParentItem(self)
        self._body_hidden = True

        self._title_text = TextWidget()
        self._title_text.setParentItem(self)

        self.background.setBrush(QtGui.QBrush(bg_color))
        self.background.setPen(self.focus_pen)
        self.setHtml()

        self.setFlags(self.flags() | self.ItemIsFocusable)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

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

    def focusOutEvent(self, event):
        self._body_hidden = True
        self.background.setPen(QtGui.QPen(QtGui.QColor(0,0,0,0)))
        self.setHtml()

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


            
        

class TextHolderWidget(QtGui.QGraphicsWidget):
    
    def __init__(self, title, html):
        
        super(TextHolderWidget, self).__init__()
        
        layout = QtGui.QGraphicsLinearLayout()
        layout.setOrientation(QtCore.Qt.Vertical)
        self._widgets = []
        for i in range(3):
            widget = TitledTextWidget(title, html)
            layout.addItem(widget)

        self.setLayout(layout)


class View(QtGui.QGraphicsView):

    def keyPressEvent(self, event):
        
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        else:
            event.ignore()



import sys

title = '<b>Title</b>'
body = '''
    <span>hello!</span>
    <ul>
        <li>one</li>
        <li>two</li>
        <li>three</li>
    </ul>
'''

app = QtGui.QApplication(sys.argv)

scene = QtGui.QGraphicsScene()
widget = TextHolderWidget(title, body)
scene.addItem(widget)
view = View(scene)
view.setGeometry(0, 0, 600, 600)
view.show()

sys.exit(app.exec_())
