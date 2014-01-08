

from PyQt4 import QtCore, QtGui

from svg import SvgIsoFloorItem, SvgTransitionItem
from util import ResetItem, ResetError, CharItem
import config


def transform_ns(item):

        t = item.transform()
        hscale = 1
        vscale = .894
        hshear = 0
        vshear = -.447
        t.setMatrix(hscale, hshear, 0, vshear, vscale, 0, 0, 0, 1)
        item.setTransform(t)

def transform_ew(item):

        t = item.transform()
        hscale = 1
        vscale = .894
        hshear = 0
        vshear = .447
        item.setMatrix(hscale, hshear, 0, vshear, vscale, 0, 0, 0, 1)
        item.setTransform(t)



#################################
### Items
#################################

class TransitionPoints(object):
    '''
        Of three (square or isometric) tiles: Tile, Adjacent, and Corner
        find the three points that will form a triangle through half of A
        with one side touching T and the other C

        ....x....
        . T . A .
        ....x...x
            . C .
            .....

    '''
    directions = {
        #isometric
        ((-1.0, -0.5), (-1.0, 0.5)): 'west', 
        ((-1.0, -0.5), (1.0, -0.5)): 'north',
        ((-1.0, 0.5), (1.0, 0.5)): 'south',
        ((1.0, -0.5), (1.0, 0.5)): 'east',

        #non-isometric
        ((0.0, -1.0), (1.0, 0.0)): 'northeast',
        ((0.0, 1.0), (1.0, 0.0)): 'southeast',
        ((-1.0, 0.0), (0.0, -1.0)): 'northwest',
        ((-1.0, 0.0), (0.0, 1.0)): 'southwest',
    }

    def __init__(self, tile_width, tile, corner, adjacent):

        self._tile_width = tile_width

        # get the shared points mapped to adjacent coords
        ao = corner.mapFromItem(adjacent, adjacent.pos())
        corner_side = [(adjacent.mapFromItem(corner, p)) for p in list(corner.polygon()) if p-ao in adjacent.polygon()]
        ao = tile.mapFromItem(adjacent, adjacent.pos())
        tile_side = [(adjacent.mapFromItem(tile, p)) for p in list(tile.polygon()) if p-ao in adjacent.polygon()]

        opposite = [p for p in list(adjacent.polygon()) if p not in (corner_side + tile_side)]

        if len(corner_side) != 2 or len(tile_side) != 2 or len(opposite) != 1:
            raise ValueError()
        self._opposite = opposite[0] / tile_width

        middle = [(p) for p in tile_side if p in corner_side]
        # reduce points to 'unit' points of original polygon
        # make sure we sort the other two so we can find identity later
        points = sorted([(p/tile_width) for p in (corner_side + tile_side) if p != middle[0]])
        if len(middle) != 1 or len(points) != 2:
            raise ValueError((len(middle), len(points)))

        middle = middle[0] / tile_width

        # see how far away the points are away from the origin
        # the middle point is always the right angle point

        x, y =  middle.x(), middle.y()
        self._offset = QtCore.QPointF(x,y)

        p = [(p - self._offset) for p in points]
        p1 = (p[0].x(), p[0].y())
        p2 = (p[1].x(), p[1].y())
        self._key = tuple(sorted([p1, p2]))

    
    @property
    def opposite(self):
        '''Return the 4th point that would create a rectangle out of a second congruent triangle.

            ....x...X
            . T . A .
            ....x...x
                . C .
                .....

                 .   .
                ... ...
               . T x C .
                ... ...
                 x A x
                  ...
                   X
        '''
        return self._opposite * self._tile_width


    @property
    def direction(self):
        return self.directions[self._key]

    @property
    def units(self):
        p1 = QtCore.QPointF(*self._key[0]) + self._offset
        p2 = self._offset
        p3 = QtCore.QPointF(*self._key[1]) + self._offset

        return (p1, p2, p3)

    @property
    def points(self):
        return tuple([(p*self._tile_width) for p in self.units])



class TransitionItem(QtGui.QGraphicsPathItem, ResetItem):

    attrs = ('state',)

    @classmethod
    def fromTiles(cls, tile, corner, adjacent):
        
        if tile.is_wall or corner.is_wall or adjacent.is_wall:
            return None

        if corner['name'] != tile['name'] or adjacent['name'] == tile['name']:
            return None

        #only add transitions when the object tile has higher presidence
        if adjacent['zval'] >= tile['zval']:
            return None

        points = TransitionPoints(tile.tile_width, tile, corner, adjacent)
        item = TransitionItem(adjacent, points, tile)
        return item

    def __init__(self, parent, points, other, out=False):
        #parent shall be the adjacent tile so we can set the transition ontop of it.
        
        super(TransitionItem, self).__init__(parent)
        ResetItem.__init__(self, None)

        self.setZValue(other['zval'])
        self._color = QtGui.QColor(other['background'])
        self._points = points
        self.setPoints(out)

    def setPoints(self, out=False):
        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.WindingFill)
        p = self._points.points
        path.moveTo(p[2])
        path.lineTo(p[1])
        path.lineTo(p[0])

        a = (p[0] + p[1]) / 2
        b = (p[2] + p[1]) / 2

        if out:
            c = self._points.opposite
        else:
            c = p[1]

        #path.cubicTo(c, c, p[2])
        path.cubicTo(a, b, p[2])

        path.closeSubpath()
        self.setPath(path)

    @property
    def direction(self):
        return self._points.direction

    def reset(self, tile):
        super(TransitionItem, self).reset(tile)

        color = {
            'see': self._color,
            'memorized': self._color.darker(),
            'unknown': QtGui.QColor(config.config['background'])
        }[tile.state]
        self.setBrush(color)
        self.setPen(QtGui.QPen(color, 1))



#################################
### Tile Items
#################################


class FloorDebugItem(QtGui.QGraphicsSimpleTextItem, ResetItem):
    
    attrs = ('x', 'y')
    
    def __init__(self, parent, tile_width):
        super(FloorDebugItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        self.setBrush(QtGui.QBrush(QtGui.QColor('white')))
        font = self.font()
        font.setFamily('monospace')
        font.setPixelSize(tile_width * .2)
        self.setFont(font)
        self.setZValue(2)
        self.setOpacity(.2)


    def reset(self, tile):
        super(FloorDebugItem, self).reset(tile)

        self.setText('{},{}'.format(self['x'], self['y']))
        x, y = self.parentItem().floor.center()
        xo = -self.boundingRect().width() / 2
        self.setPos(x+xo, y)



class FloorItem(QtGui.QGraphicsPolygonItem, ResetItem):
    
    use_iso = False
    attrs = ('name', 'color', 'background', 'state', 'zval', 'kind')
    points = [(0,0), (0,1),  (1,1), (1, 0)]
    nonsvg_klass = CharItem
    svg_klass = CharItem # no svg for non-iso

    svg = ('path', 'floor', 'door', 'stairs', 'rock')

    def __init__(self, parent, tile_width, use_svg, use_char):

        super(FloorItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        klass = self.svg_klass if use_svg else self.nonsvg_klass

        #turned off isosvg
        if (use_svg and self.use_iso):
            self.child = klass(parent, tile_width)
            #self.child = None

        elif not (use_svg and self.use_iso) and not use_char:
            self.child = None
        else:
            self.child = klass(self, tile_width)

        self._use_svg = use_svg
        self._transitions = {}
        self._adjacent_transitions = {}
        self._svg_transitions = {}

        points = [QtCore.QPointF(p[0]*self.tile_width, p[1]*self.tile_width) for p in self.points]
        poly = QtGui.QPolygonF(points)
        self.setPolygon(poly)

    @property
    def transitions(self):
        return self._transitions

    @property
    def idx(self):
        p = self.parentItem()
        return p.idx

    def reset(self, tile):
        super(FloorItem, self).reset(tile)

        self.setZValue(self['zval'])
        color = {
            'see':QtGui.QColor(self['background']),
            'memorized':QtGui.QColor(self['background']).darker(),
            'unknown':QtGui.QColor(config.config['background']),
        }[self['state']]
        self.setBrush(QtGui.QBrush(color))
        self.setPen(QtGui.QPen(color, .5))

        for t in self._adjacent_transitions.values():
            t.reset(tile)

        if self.child:
            if self._use_svg and self['kind'] in self.svg:
                self.child.reset(tile)
                self.child.setZValue(self['zval'])

    def setTransition(self, corner, adjacent, tile):

        ok = True
        if corner['name'] != self['name'] or adjacent['name'] == self['name']:
        #if corner['kind'] != self['kind'] or adjacent['kind'] == self['kind']:
            ok = False
        #only add transitions when the object tile has higher presidence
        if adjacent['zval'] >= self['zval']:
            ok = False

        item = self._transitions.get(adjacent.idx)
        if item:
            self.scene().removeItem(item)
            del self._transitions[adjacent.idx, corner.idx]
            del adjacent._adjacent_transitions[self.idx]
        item = self._svg_transitions.get(adjacent.idx)
        if item:
            self.scene().removeItem(item)
            del self._svg_transitions[adjacent.idx, corner.idx]

        # add it back if we need to
        if ok:
            points = TransitionPoints(self._tile_width, self, corner, adjacent)
            item = TransitionItem(adjacent, points, self)
            item.setZValue(adjacent['zval'])
            self._transitions[adjacent.idx, corner.idx] = item
            adjacent._adjacent_transitions[self.idx] = item
            item.reset(tile)

            if self._use_svg and self.use_iso:
            #if False:
                old = tile.name
                tile.name = tile.name + '_' + item.direction
                item = SvgTransitionItem(adjacent, self._tile_width)
                self._svg_transitions[adjacent.idx, corner.idx] = item
                item.reset(tile)
                # make sure svg is above standard transition
                item.setZValue(adjacent['zval']+1)
                tile.name = old
                
    def center(self):
        #center of paralellagram = (a+c)/2 or (b+d)/2
        poly = self.polygon()
        if not poly:
            raise ValueError('polygon not set')
        a,b,c,d = list(poly)
        p = (a+c)/2
        return p.x(), p.y()
        
    def offset(self):

        poly = self.polygon()
        if not poly:
            raise ValueError('polygon not set')
        r = self.boundingRect()
        x, y = r.x(), r.y()
        return x, y


class IsoFloorItem(FloorItem):
    use_iso = True
    svg_klass = SvgIsoFloorItem
    points = [(0,0), (1,.5),  (0,1), (-1, .5)]




