
from math import atan, sin, cos, degrees

from PyQt4 import QtCore, QtGui

from util import ResetItem, CharItem
from svg import SvgFeatureItem, SvgItem


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
    def toArch(polygon, idx, divisor=1, invert=False):
        
        path = QtGui.QPainterPath()
        points = list(polygon)

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
        
        points = [QtCore.QPointF(*p) for p in points]
        poly = QtGui.QPolygonF(points)
        polygon = QtGui.QGraphicsPolygonItem(poly)
        return polygon

    def toTopIntersection(self, other):

        poly1 = self.toTop().polygon()
        poly2 = other.toTop().polygon()

        if list(poly1)[0] != list(poly2)[0]:
            raise ValueError
        
        if poly1[2].y() > poly2[2].y():
            smaller, larger = poly1, poly2
        else:
            smaller, larger = poly2, poly1
        
        l1 = QtCore.QLineF(smaller[1], smaller[2])
        l2 = QtCore.QLineF(larger[2], larger[3])

        intersection = QtCore.QPointF()
        if not l1.intersect(l2, intersection):
            raise ValueError('no intersection')

        points = [
            smaller[0],
            smaller[1],
            intersection,
            larger[3],
        ]
        poly = QtGui.QPolygonF(points)
        polygon = QtGui.QGraphicsPolygonItem(poly)
        return polygon




class FeatureItem(QtGui.QGraphicsPathItem, ResetItem):

    attrs = ('name', 'color')
    feature_name = None

    def __init__(self, parent, tile_width, use_svg):
        super(FeatureItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)
        self._use_svg = use_svg

        if use_svg:
            self.svg_item = SvgFeatureItem(self, tile_width)
            self.svg_item.setZValue(1)
            self.svg_item._flipped = False
        else:
            self.svg_item = None

    def reset(self, tile):
        super(FeatureItem, self).reset(tile)
        path = self.getPath(self.tile_width, self['name'])
        self.setPath(path)

        #g = self.getGradient(path, self['name'], self['color']) or self['color']
        self.setBrush(self.color)
        if self._use_svg:
            self.setPen(self.color)
        else:
            self.setPen(self.color.darker())

        if self.svg_item:
            item = self.svg_item
            flip, name = self.svg[self['name']]
            item.reset(tile, name, self.feature_name)
            if flip and not item._flipped:
                item.translate(item.boundingRect().width()/2, 0)
                item.scale(-1, 1)
                item._flipped = True

    def offset(self):
        return self.parentItem().background.offset()

    def center(self):
        return self.parentItem().background.center()

    @property
    def color(self):   
        return self['color']



class CharFeatureItem(QtGui.QGraphicsWidget, ResetItem):
    
    attrs = ('color', 'name')

    def __init__(self, parent, tile_width, use_svg):
        super(CharFeatureItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)
        self._use_svg = use_svg

        if use_svg:
            self.item = SvgItem(self, tile_width)
        else:
            self.item = CharItem(self, tile_width)
        self.svg_item = None

    def reset(self, tile):
        super(CharFeatureItem, self).reset(tile)
        self.item.reset(tile)

    def center(self):
        return self.parentItem().center()

    def offset(self):
        return self.parentItem().offset()



class WallItem(FeatureItem):
    
    attrs = ('name', 'direction', 'color')

    width = 3/8.
    height = 5/8.
    horizontal_flip = {
        'north wall': True,
        'south wall': True,
        'ne wall': True,
    }
    union = {
        'se wall': 'north wall',
    }
    intersection = {
        'nw wall': 'north wall'
    }

    svg = {
        'north wall': (False, 'north wall'),
        'east wall': (True, 'north wall'),
        'west wall': (False, 'west wall'),
        'south wall': (True, 'west wall'),
        'sw wall': (False, 'west wall'),
        'ne wall': (False, 'north wall'),
        'se wall': (False, 'se wall'),
        'nw wall': (False, 'nw wall'),

        'closed north door': (False, 'closed north door'),
        'closed east door': (True, 'closed north door'),
        'closed west door': (False, 'closed west door'),
        'closed south door': (True, 'closed west door'),

        'locked north door': (False, 'closed north door'),
        'locked east door': (True, 'closed north door'),
        'locked west door': (False, 'closed west door'),
        'locked south door': (True, 'closed west door'),

        'open north door': (False, 'open north door'),
        'open east door': (True, 'open north door'),
        'open west door': (False, 'open west door'),
        'open south door': (True, 'open west door'),
    }
    def reset(self, item):
        super(WallItem, self).reset(item)


class ArchItem(WallItem):

    feature_name = 'arch'

    def getPath(self, scale, direction):
    
        flip = self['direction'] in ['north', 'south']

        wall1 = IsoCube(h=self.width, y=-1+self.width, scale=scale)
        poly = wall1.toFace().polygon()
        if flip:
            poly = QtGui.QPolygonF([QtCore.QPointF(-p.x(), p.y()) for p in poly])
        path = IsoCube.toArch(poly, 3, invert=True)

        wall2 = IsoCube(w=self.width/3., h=self.width, y=-1+self.width, scale=scale)
        poly = wall2.toSide().polygon()
        if flip:
            poly = QtGui.QPolygonF([QtCore.QPointF(-p.x(), p.y()) for p in poly])
        path.addPolygon(poly)

        poly = wall1.toTopIntersection(wall2).polygon()
        if flip:
            poly = QtGui.QPolygonF([QtCore.QPointF(-p.x(), p.y()) for p in poly])
        path.addPolygon(poly)

        return path

class DoorItem(WallItem):

    feature_name = 'door'
    points = ((0,1), (1,.5), (1, -1/8.), (0, 3/8.))

    def getPath(self, scale, direction):
    
        flip = self['direction'] in ['north', 'south']
        path = QtGui.QPainterPath()
        points = self.points
        if flip:
            points = [(-x,y) for (x,y) in points]
        path.moveTo(points[0][0]*scale, points[0][1]*scale)
        path.lineTo(points[1][0]*scale, points[1][1]*scale)
        path.lineTo(points[2][0]*scale, points[2][1]*scale)

        p1 = QtCore.QPointF(points[2][0]*scale, points[2][1] - self.width*scale)
        p2 = QtCore.QPointF(points[3][0]*scale, points[3][1] - self.width*scale)
        p3 = QtCore.QPointF(*points[3])
        path.cubicTo(p1, p2, p3)
        path.closeSubpath()
        return path

    @property
    def color(self):
        return self['color'].darker()


class RoofItem(WallItem):

    feature_name = 'roof'

    @classmethod
    def getPath(cls, scale, direction):
    
        path = QtGui.QPainterPath()
        flip = cls.horizontal_flip.get(direction)

        wall1 = IsoCube(w=cls.width, h=cls.height, scale=scale)
        wall2 = IsoCube(h=cls.height, scale=scale)

        poly = wall1.toTopIntersection(wall2).polygon()
        if flip:
            poly = QtGui.QPolygonF([QtCore.QPointF(-p.x(), p.y()) for p in poly])
            offset = QtCore.QPointF(-scale / 48., -scale / 21.)
        else:
            offset = QtCore.QPointF(scale / 48., -scale / 21.)

        path = QtGui.QPainterPath()
        path.moveTo(poly[1])
        path.lineTo(poly[1]+offset)
        path.lineTo(poly[2]+offset)
        path.lineTo(poly[2])
        path.lineTo(poly[3])
        path.lineTo(poly[0])
        path.closeSubpath()

        xo, yo = -scale, -scale/2
        poly = (wall1.toFace() if flip else wall1.toSide()).polygon()
        path2 = IsoCube.toArch(poly, 3, divisor=4.)
        if flip:
            path2.translate(-scale, -scale*cls.height -scale/2)
        else:
            path2.translate(scale, -scale*cls.height -scale/2)

        path = path.united(path2)
        union = cls.union.get(direction)
        intersection = cls.intersection.get(direction)
        if union:
            path = path.united(cls.getPath(scale, union))
        elif intersection:
            path = path.intersected(cls.getPath(scale, intersection))
        return path


    
class FaceItem(WallItem):

    feature_name = 'face'

    @classmethod
    def getPath(cls, scale, direction):
        
        path = QtGui.QPainterPath()
        flip = cls.horizontal_flip.get(direction)
        wall = IsoCube(h=cls.height, scale=scale)

        if flip:
            poly = wall.toSide().polygon()
        else:
            poly = wall.toFace().polygon()

        path.addPolygon(poly)
        path.closeSubpath()

        union = cls.union.get(direction)
        intersection = cls.intersection.get(direction)
        if union:
            return path.united(cls.getPath(scale, union))
        elif intersection:
            return path.intersected(SideItem.getPath(scale, intersection))
        return path

    
class SideItem(WallItem):

    feature_name = 'side'

    @classmethod
    def getPath(cls, scale, direction):
        
        path = QtGui.QPainterPath()
        wall = IsoCube(w=cls.width, h=cls.height, scale=scale)
        flip = cls.horizontal_flip.get(direction)

        if flip or cls.union.get(direction):
            poly = wall.toFace().polygon()
        else:
            poly = wall.toSide().polygon()
        path.addPolygon(poly)
        path.closeSubpath()

        path2 = IsoCube.toArch(poly, 3, divisor=4.)
        path2.translate(0, -scale*cls.height)
        path.addPath(path2)
        return path




class StairsItem(QtGui.QGraphicsWidget, ResetItem):

    attrs = ('name', 'color')

    step_length = 3/8.
    step_width = 1/16.
    steps = 2

    def __init__(self, parent, tile_width, use_svg):
        super(StairsItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

    def reset(self, tile):
        super(StairsItem, self).reset(tile)

        w, l, s = self.step_width, self.step_length, self.tile_width
        for n in range(self.steps):
            box1 = IsoCube(w=l, h=w, scale=s)
            box2 = IsoCube(w=w, h=w, scale=s)
            face = box1.toFace()
            top = box1.toTopIntersection(box2)
            self._setPolygon(top, n)
            self._setPolygon(face, n)
            face.setBrush(self['color'].darker())

        x = w
        y = w*n*2-w
        w = w * 2 + w
        h = w
        box = IsoCube(y=y, x=x,  w=w, h=h, scale=s)
        side = box.toSide()
        side.setBrush(self['color'])
        side.setPen(self['color'].darker())
        side.setParentItem(self)
        side.setZValue(-1)


    def _setPolygon(self, item, n):
        item.setBrush(self['color'])
        item.setPen(self['color'].darker())
        item.setParentItem(self)
        x, y = self._getPosition(n)
        item.setPos(x, y)

    def _getPosition(self, n):
        x = self.step_width * self.tile_width * n
        y = self.step_width * 1.5 * self.tile_width * n
        return x, y


        



if __name__ == '__main__':

    class View(QtGui.QGraphicsView):
        
        def __init__(self, scene):
            super(View, self).__init__(scene)
            self.setRenderHint(QtGui.QPainter.Antialiasing)

        def keyPressEvent(self, event):
            
            if event.key() == QtCore.Qt.Key_Escape:
                self.close()
            else:
                event.ignore()

    class Tile(object):
        def __init__(self, name):
            
            self.name = name
            self.color = QtGui.QColor('orange')

    import sys

    app = QtGui.QApplication(sys.argv)
    scene = QtGui.QGraphicsScene()


    #roof = RoofItem(None, 128, False)
    #roof.reset(Tile('se wall'))
    #scene.addItem(roof)

    #scene.addItem(Roof(s, d))
    #scene.addItem(Face(s, d))
    #scene.addItem(Side(s, d))
    #scene.addItem(Door(s, d))
    #scene.addItem(Step(s, d))

    stairs = StairsItem(None, 512, False)
    stairs.reset(Tile('se wall'))
    scene.addItem(stairs)

    view = View(scene)
    view.setGeometry(0, 0, 600, 600)
    view.show()

    sys.exit(app.exec_())

