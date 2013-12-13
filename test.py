

from PyQt4 import QtCore, QtGui, QtSvg, QtXml
from view.animation import OpacityAnimation
from view.animation import PropAnimation

class Circle(QtGui.QGraphicsEllipseItem):
    
    def __init__(self):
        super(Circle, self).__init__(50, 50, 100, 100)

        self.setBrush(QtGui.QColor('blue'))

        t = self.transform()
        print 11, t.m11()
        print 12, t.m12()
        print 13, t.m13()
        print 21, t.m21()
        print 22, t.m22()
        print 23, t.m23()
        print 31, t.m31()
        print 32, t.m32()
        print 33, t.m33()

        hscale = 1
        vscale = .894
        hshear = 0
        vshear = -.447
        t.setMatrix(hscale, hshear, 0, vshear, vscale, 0, 0, 0, 1)
        self.setTransform(t)






class View(QtGui.QGraphicsView):

    def keyPressEvent(self, event):
        
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        else:
            event.ignore()



import sys

app = QtGui.QApplication(sys.argv)
scene = QtGui.QGraphicsScene()
widget = Circle()
scene.addItem(widget)
view = View(scene)
view.setGeometry(0, 0, 600, 600)
view.show()

sys.exit(app.exec_())

