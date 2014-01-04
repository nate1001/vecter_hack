

from PyQt4 import QtCore, QtGui

from svg import InkscapeHandler, SvgRenderer, SvgIsoFloorItem, SvgEquipmentItem, SvgSpeciesItem, SvgTransitionItem
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


class IsoPartItem(QtGui.QGraphicsPathItem, ResetItem):
    
    def __init__(self, parent, tile_width, use_svg):
        super(IsoPartItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        if use_svg:
            self.svg = []
            for i in range(2):
                self.svg.append(SvgIsoFloorItem(self, tile_width))
        else:
            self.svg = None


    def resetSvg(self, item, tile):

        if item.svg and not item.no_svg.get(tile.name):
            for idx, name in enumerate(item.svg_name.get(tile.name, (tile.name,))):
                old = tile.name
                tile.name = name
                tile.svg_extension = item.svg_extension
                item.svg[idx].reset(tile)
                tile.name = old
                tile.svg_extension = ''


    def getArch(self, points, reverse=False):
        #FIXME bug or something with Qt.WINDING_FILL
        #if self.roof.second_points.get(self['name']):
        #    self.roof2.reset(tile, second=True)

        _offset = (
            (0, -1/8.),
            (1/8., -1/4.)
        )
        
        if not reverse:
            mult = 1 if points[0].x() > 0 else -1
        else:
            mult = -1 if points[0].x() > 0 else 1

        s = self.tile_width
        xo, yo = _offset[0]
        a = QtCore.QPointF(points[0].x() +  xo*mult*s, points[0].y() + yo*s)
        xo, yo = _offset[1]
        b = QtCore.QPointF(points[1].x() + xo*mult*s, points[0].y() + yo*s)
        return (a, b)


class IsoPartStairsItem(IsoPartItem):
    attrs = ('name', 'color', 'background')

    points = {
        'staircase up': ((0, 0), (-3/8., 3/16.)),
        'staircase down': ((1/4., 9/16.), (-1/8., 3/4.)),
    }
    iterations = {
        'staircase up': 6,
        'staircase down': 4,
    }
    polygon= {
        'staircase down': True,
    }
    offset = (1/16., 1/16.)
        

    class TopStep(QtGui.QGraphicsPathItem):
        
        def __init__(self, parent, points, offset, down, iterations):
            super(IsoPartStairsItem.TopStep, self).__init__(parent)

            path = QtGui.QPainterPath()
            p0 = points[0]
            p1 = points[1]
            for i in range(iterations):
                path.moveTo(p0)
                path.lineTo(p1)
                path.lineTo(p1 + offset)
                path.lineTo(p0 + offset)
                path.lineTo(p0)
                p0 = p0 + offset + down
                p1 = p1 + offset + down
            self.setPath(path)
            self.setPen(QtGui.QPen(QtCore.Qt.NoPen))

    class SideStep(QtGui.QGraphicsPathItem):
        
        def __init__(self, parent, points, offset, down, iterations):
            super(IsoPartStairsItem.SideStep, self).__init__(parent)

            path = QtGui.QPainterPath()
            p0 = points[0]
            p1 = points[1]
            for i in range(iterations):
                path.moveTo(p0 + offset)
                path.lineTo(p0 + offset + down)
                path.lineTo(p1 + offset + down)
                path.lineTo(p1 + offset)
                path.lineTo(p0 + offset)
                p0 = p0 + offset + down
                p1 = p1 + offset + down
            self.setPath(path)
            self.setPen(QtGui.QPen(QtCore.Qt.NoPen))


    class Side(QtGui.QGraphicsPathItem):
        
        def __init__(self, parent, points, offset, down, iterations):
            super(IsoPartStairsItem.Side, self).__init__(parent)

            path = QtGui.QPainterPath()
            path.moveTo(points[0])
            path.lineTo(points[1])
            path.lineTo(points[1].x(), points[0].y() + (down.y() + offset.y())*iterations)
            path.lineTo(points[0].x(), (points[0].y() + down.y() + offset.y())*(iterations+1) + down.y())
            self.setPath(path)
            self.setPen(QtGui.QPen(QtCore.Qt.NoPen))
    
    def reset(self, tile):
        super(IsoPartStairsItem, self).reset(tile)

        points = [QtCore.QPointF(*p)*self.tile_width for p in self.points[self['name']]]
        offset = QtCore.QPointF(*self.offset)*self.tile_width
        down = QtCore.QPointF(0, self.offset[1])*self.tile_width
        iterations = self.iterations[self['name']]


        if self.polygon.get(self['name']):
            p1 = QtCore.QPointF(-offset.x(), offset.y()/2.)
            p2 = QtCore.QPointF(offset.x(), offset.y()/2.)
            poly = QtGui.QGraphicsPolygonItem(QtGui.QPolygonF([
                points[0],
                points[0] + p1*9,
                points[0] + p1*9 + p2*5,
                points[0] + p2*5,
            ]))
            poly.setParentItem(self)
            poly.setBrush(self['background'].darker())
            poly.setZValue(-1)

        side = self.Side(self, points, offset, down, iterations)
        top_steps = self.TopStep(self, points, offset, down, iterations)
        side_steps = self.SideStep(self, points, offset, down, iterations)

        color = self['color'].darker()
        side_steps.setBrush(color)
        top_steps.setBrush(self['color'])
        top_steps.setPen(color)
        side.setBrush(self['color'])
        #self.setPen(QtGui.QPen(QtCore.Qt.NoPen))


class IsoPartSideItem(IsoPartItem):

    svg_extension = '_side'
    attrs = ('name', 'color')

    _points = ((0, 3/8.), (-3/8., 3/16.), (-3/8., 13/16.), (0,1),)
    points = {
        'west wall': _points,
        'east wall': _points,
        'north wall': tuple([(-p[0], p[1]) for p in _points]),
        'south wall': tuple([(-p[0], p[1]) for p in _points]),
        'nw wall': ((0, 3/8.), (-3/8., 3/16.), (-3/8.,13/16.), (0,1)),
    }
    points['sw wall'] = points['west wall']
    points['ne wall'] = points['north wall']
    points['se wall'] = points['north wall']

    svg_name = {
        'east wall': ('west wall',),
        'south wall': ('north wall',),
        'se wall': ('north_wall',),
        'nw wall': ('north wall', 'west_wall'),
        'sw wall': ('west wall',),
        'ne wall': ('north wall',),
    }

    no_svg = {
    }

    def reset(self, tile):
        super(IsoPartSideItem, self).reset(tile)

        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.WindingFill)

        points = [QtCore.QPointF(*p)*self.tile_width for p in self.points[self['name']]]
        if not points:
            return

        path.moveTo(points[0])
        reverse = True if points[1].x() < 0 else False
        a, b = self.getArch(points, reverse=reverse)
        path.cubicTo(a, b, points[1])
        for point in points[2:]:
            path.lineTo(point)

        color = self['color'].darker()
        self.setPath(path)
        self.setBrush(self['color'])
        self.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        #self.setPen(QtGui.QPen(self['color'], .5))

        self.resetSvg(self, tile)


class IsoPartFaceItem(IsoPartItem):

    svg_extension = '_face'
    attrs = ('name', 'color')

    points = ((0, 3/8.), (1, -1/8.), (1, .5), (0,1))
    special_points = {
        'se wall': ((0, 3/8.), (1, -1/8.), (1,.5), (0,1), (-1,.5), (-1,-1/8.)),
        'nw wall': ((0, 3/8.), (3/8., 3/16.), (3/8.,13/16.), (0,1)),
    }

    horizontal_flip = {
        'north wall': True,
        'south wall': True,
        'ne wall': True,
    }

    svg_name = {
        'sw wall': ('west wall',),
        'ne wall': ('west wall',),
        'east wall': ('west wall',),
        'south wall': ('west wall',),
        'north wall': ('west wall',),
        'se wall': ('north wall', 'west_wall'),
    }

    no_svg = {'nw wall': True}

    def reset(self, tile):
        super(IsoPartFaceItem, self).reset(tile)

        path = QtGui.QPainterPath()
        points = self.special_points.get(self['name']) or self.points
        points = [QtCore.QPointF(*p)*self.tile_width for p in points]
        polygon = QtGui.QPolygonF(points)
        path.addPolygon(polygon)
        self.setPath(path)

        self.setBrush(self['color'])
        self.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        self.resetSvg(self, tile)
        if self.horizontal_flip.get(self['name']):
            self.scale(-1, 1)


class IsoPartRoofItem(IsoPartItem):

    attrs = ('name', 'color')
    svg_extension = '_roof'

    points = ((1, -1/8.), (5/8., -5/16.),(-3/8., 3/16.), (0, 3/8.),)
    special_points = {
        'nw wall':  ((3/8., 3/16.), (0,0), (-3/8., 3/16.), (0,3/8.), ),
    }

    horizontal_flip = {
        'north wall': True,
        'south wall': True,
        'ne wall': True,
    }

    svg_name = {
        'east wall': ('west wall',),
        'south wall': ('west wall',),
        'north wall': ('west wall',),
        'se wall': ('west wall', 'north_wall'),
        'ne wall': ('west wall',),
        'sw wall': ('west wall',),
    }

    no_svg = {
        'nw wall': True,
    }

    def reset(self, tile):
        super(IsoPartRoofItem, self).reset(tile)

        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.WindingFill)

        points = self.special_points.get(self['name']) or self.points
        self._setPoints(path, points)

        if self['name'] == 'se wall':
            points = [(-x,y) for (x,y) in points]
            self._setPoints(path, points)
            
        self.setPath(path)
        self.setBrush(self['color'].darker())
        self.setPen(QtGui.QPen(self['color'].darker().darker(), 1))
        self.resetSvg(self, tile)
        if self.horizontal_flip.get(self['name']):
            self.scale(-1, 1)

    def _setPoints(self, path, points):

        points = [QtCore.QPointF(*p)*self.tile_width for p in points]
        path.moveTo(points[0])
        a, b = self.getArch(points)
        path.cubicTo(a, b, points[1])
        for point in points[2:]:
            path.lineTo(point)
        path.lineTo(points[0])


class IsoPartDoorItem(IsoPartItem):

    attrs = ('name', 'color')
    svg_extension = ''

    points = ((0,0), (1, -.5), (1, -1/8.), (0, 3/8.))
    offset = (-1/8., -1/16.)

    horizontal_flip = {
        'south door': True,
        'north door': True,
    }

    svg_name = {
        'east door': ('west door',),
        'north door': ('west door',),
        'south door': ('west door',),
    }

    no_svg = {}


    def reset(self, tile, second=False):
        super(IsoPartDoorItem, self).reset(tile)

        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.WindingFill)
        name = self['name']

        points = [QtCore.QPointF(*p)*self.tile_width for p in self.points]
        offset = QtCore.QPointF(*self.offset) * self.tile_width

        #top
        path.moveTo(points[0])
        path.lineTo(points[1])
        path.lineTo(points[1]+offset)
        path.lineTo(points[0]+offset)
        path.lineTo(points[0])

        #side
        path.moveTo(points[0])
        path.lineTo(points[3])
        path.lineTo(points[3]+offset)
        path.lineTo(points[0]+offset)
        path.lineTo(points[0])

        #face - arch
        path.moveTo(points[0])
        for point in points[:2]:
            path.lineTo(point)
        path.lineTo(points[2])
        path.cubicTo(points[1], points[0], points[3])
        path.lineTo(points[0])

        self.setPath(path)
        self.setBrush(self['color'])
        self.setPen(QtGui.QPen(self['color'].darker().darker(), 1))

        self.resetSvg(self, tile)

        if self.horizontal_flip.get(self['name']):
            self.scale(-1, 1)




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
        #x,y = self.parentItem().center()
        #self.setPos(x, y)

    def reset(self, tile):
        super(FloorDebugItem, self).reset(tile)

        self.setText('{},{}'.format(self['x'], self['y']))



class FloorItem(QtGui.QGraphicsPolygonItem, ResetItem):
    
    use_iso = False
    attrs = ('name', 'color', 'background', 'state', 'zval')
    points = [(0,0), (0,1),  (1,1), (1, 0)]
    nonsvg_klass = CharItem
    svg_klass = CharItem # no svg for non-iso

    def __init__(self, parent, tile_width, use_svg, use_char):

        super(FloorItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        klass = self.svg_klass if use_svg else self.nonsvg_klass

        #turned off isosvg
        if (use_svg and self.use_iso):
            self.child = None

        elif not (use_svg and self.use_iso) and not use_char:
            self.child = None
        else:
            self.child = klass(parent, tile_width)
            self.child.setZValue(1)

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
            self.child.reset(tile)

    def setTransition(self, corner, adjacent, tile):

        ok = True
        if corner['name'] != self['name'] or adjacent['name'] == self['name']:
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
            self._transitions[adjacent.idx, corner.idx] = item
            adjacent._adjacent_transitions[self.idx] = item
            item.reset(tile)

            if self._use_svg:
                old = tile.name
                tile.name = tile.name + '_' + item.direction
                item = SvgTransitionItem(adjacent, self._tile_width)
                self._svg_transitions[adjacent.idx, corner.idx] = item
                #FIXME svg non-iso
                try:
                    item.reset(tile)
                except ResetError:
                    pass
                # make sure svg is above standard transition
                item.setZValue(self['zval'])
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




