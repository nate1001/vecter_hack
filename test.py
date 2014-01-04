

from PyQt4 import QtCore, QtGui, QtSvg, QtXml

from math import atan, sin, cos, degrees

class iiiIsoCoord(object):
    
    # a 'isometric' (dimetric) line that will grow horizontally twice 
    # as fast as it will vertically
    angle_a = (atan(.5)) #radians
    kludge = 1 / cos(atan(.5))

    def __init__(self, x, y, z, size=1):
        
        # ne edge
        self.x_w = x
        # nw edge
        self.y_w = y
        # elevation
        self.z_w = z

        self.size = size

    def x_s(self):
        '''x screen coordinate.'''
        
        a = self.angle_a
        s = self.size
        x, z  = self.x_w, self.z_w
        return (x-z)*cos(a)*s*self.kludge

    def y_s(self):
        '''y screen coordinate.'''

        a = self.angle_a
        s = self.size
        x, y, z  = self.x_w, self.y_w, self.z_w
        return ((x+z)*sin(a)-y)*s*self.kludge

    @property
    def screen(self):
        return self.x_s(), self.y_s()


class IsoCoord(object):
    
    # a 'isometric' (dimetric) line that will grow horizontally twice 
    # as fast as it will vertically
    angle_a = (atan(.5)) #radians

    def __init__(self, x, y, size=1):
        
        self.x_w = x
        self.y_w = y
        self.size = size

    def x_s(self):
        '''x screen coordinate.'''
        
        a = self.angle_a
        s = self.size
        x, z  = self.x_w, self.z_w
        return (x-z)*cos(a)*s

    def y_s(self):
        '''y screen coordinate.'''

        return self.x_w 
        a = self.angle_a
        s = self.size
        x, y, z  = self.x_w, self.y_w, self.z_w
        return ((x+z)*sin(a)-y)*s

    @property
    def screen(self):
        return (
            (self.x_w - self.y_w) * float(self.size), 
            ((self.x_w + self.y_w) / 2.) * self.size
        )



class IsoCube(object):
    
    def __init__(self, x=0, y=0, w=1, h=1, scale=1):

        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.scale = scale

    @staticmethod
    def toArch(polygon_item, idx, divisor=1, invert=False):
        
        path = QtGui.QPainterPath()
        points = list(polygon_item.polygon())

        bottom = points[idx], points[idx-1]
        arch = points[idx-2], points[idx-3]

        o1 = (arch[1] - bottom[0]) / divisor
        o2 = (arch[0] - bottom[1]) / divisor

        path.moveTo(bottom[0])

        if not invert:
            path.lineTo(bottom[1])
            path.cubicTo(bottom[1] + o1, bottom[0] + o2, bottom[0])
        else:
            path.lineTo(arch[1])
            path.lineTo(arch[0])
            path.lineTo(bottom[1])
            path.cubicTo(bottom[1] + o1, bottom[0] + o2, bottom[0])

        return path

    def toFace(self):
        return self._toPolygon('face')

    def toSide(self):
        return self._toPolygon('side')

    def toTop(self):
        return self._toPolygon('top')

    def _toPolygon(self, typ):

        w,h = self.w-1, self.h-1
        x,y = self.x, self.y
        scale = self.scale
        ox = x+y
        oy = -x+y

        p1 = IsoCoord(ox-h, oy-h, scale).screen #orgin
        if typ == 'face':
            p2 = IsoCoord(ox-h, oy-1-w-h,  scale).screen #ne
            p3 = IsoCoord(ox+1, oy-w, scale).screen #se
            p4 = IsoCoord(ox+1, oy+1, scale).screen #sw
        elif typ == 'side':
            p2 = IsoCoord(ox-h-1-w, oy-h,  scale).screen #nw
            p3 = IsoCoord(ox-w, oy+1, scale).screen #sw
            p4 = IsoCoord(ox+1, oy+1, scale).screen #se
        elif typ == 'top':
            ox = 1-self.h+self.y+self.x
            oy = 1-self.h+self.y-self.x
            w = -1*self.w
            p2 = IsoCoord(w+ox, oy, scale).screen #left
            p3 = IsoCoord(w+ox, w+oy,  scale).screen #top
            p4 = IsoCoord(ox, w+oy , scale).screen #right
        else:
            raise ValueError(typ)

        points = [p1, p2, p3, p4]
        print 22, typ, points
        
        points = [QtCore.QPointF(*p) for p in points]
        poly = QtGui.QPolygonF(points)
        polygon = QtGui.QGraphicsPolygonItem(poly)
        return polygon





class View(QtGui.QGraphicsView):

    def keyPressEvent(self, event):
        
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        else:
            event.ignore()


import sys

app = QtGui.QApplication(sys.argv)
scene = QtGui.QGraphicsScene()

'''
wall = IsoCube(x=1, scale=64)
poly = wall.toFace()
poly.setPen(QtGui.QPen(QtGui.QColor('magenta'), 5))
scene.addItem(poly)
poly = wall.toSide()
poly.setPen(QtGui.QPen(QtGui.QColor('magenta'), 5))
scene.addItem(poly)
poly = wall.toTop()
poly.setPen(QtGui.QPen(QtGui.QColor('magenta'), 5))
scene.addItem(poly)
'''

wall = IsoCube(w=.5, scale=64)

poly = wall.toTop()
poly.setPen(QtGui.QPen(QtGui.QColor('red'), 5))
scene.addItem(poly)

poly = wall.toFace()
scene.addItem(poly)
poly.setPen(QtGui.QPen(QtGui.QColor('blue'), 5))

poly = wall.toSide()
poly.setPen(QtGui.QPen(QtGui.QColor('yellow'), 5))
scene.addItem(poly)

arch = IsoCube.toArch(wall.toFace(), 3, .5, invert=True)
item = QtGui.QGraphicsPathItem(arch)
item.setPen(QtGui.QPen(QtGui.QColor('green'), 5))
item.setBrush((QtGui.QColor('green')))
item.setPos(0, -64)
scene.addItem(item)

view = View(scene)
view.setGeometry(0, 0, 600, 600)
view.show()


sys.exit(app.exec_())

