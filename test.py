

from PyQt4 import QtCore, QtGui, QtSvg, QtXml
from view.animation import OpacityAnimation
from view.animation import PropAnimation

class TransitionItem(QtGui.QGraphicsPathItem):
    
    def __init__(self):
        super(TransitionItem, self).__init__()

        size = 16
        self.setBrush(QtGui.QColor('blue'))


        points = [
            QtCore.QPointF(-8, 4) * size,
            QtCore.QPointF(0, 0) * size,
            QtCore.QPointF(-8, -4) * size,
        ]

        points = [
            QtCore.QPointF(-8, 4) * size,
            QtCore.QPointF(0, 0) * size,
            QtCore.QPointF(8, 4) * size,
        ]

        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.WindingFill)

        path.moveTo(points[0])
        path.lineTo(points[1])
        path.lineTo(points[2])
        #path.cubicTo((points[2] + points[1]) / 2, (points[0] + points[1]) / 2, points[0])
        p1 = self.out(points[1], points[2])
        p2 = self.out(points[1], points[0])
        path.cubicTo(p1, p2, points[0])
        path.closeSubpath()
        self.setPath(path)

    def out(self, p1, p2):
        x = p2.x() - p1.x()
        y = p2.y() - p1.y()
        return QtCore.QPointF(x * 1.5, y / 2)

    def in_(self, p1, p2):
        x = p2.x() - p1.x()
        y = p2.y() - p1.y()
        return QtCore.QPointF(x / 1.5, y / 2)

    def distance(self, p1, p2):
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        return ((x2 - x1)**2 + (y2 - y1)**2)**.5



class View(QtGui.QGraphicsView):

    def keyPressEvent(self, event):
        
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        else:
            event.ignore()



import sys


'''
app = QtGui.QApplication(sys.argv)

scene = QtGui.QGraphicsScene()
widget = TransitionItem()
scene.addItem(widget)
view = View(scene)
view.setGeometry(0, 0, 600, 600)
view.show()

sys.exit(app.exec_())
'''

class A(object):
    
    def __del__(self):
        print 33, 'del'

class B(object):
    
    def __init__(self):
        
        self.a = A()

a = A()
del a

b = B()
del b

