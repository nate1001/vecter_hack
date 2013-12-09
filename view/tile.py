

from PyQt4 import QtCore, QtGui, QtSvg

from animation import MovementAnimation, MeleeAnimation, PosAnimation, OpacityAnimation
from svg import InkscapeHandler, SvgRenderer
import config


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


class CharItem(QtGui.QGraphicsSimpleTextItem, ResetItem):
    
    attrs = ('color', 'char')
    
    def __init__(self, parent, tile_width):
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


#################################
### Svg Items
#################################


class SvgItem(QtSvg.QGraphicsSvgItem, ResetItem):
    
    renderers = {}
    attrs = ('category', 'name')

    def __init__(self, parent, tile_width):
        super(SvgItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)
        self._svg_size = None
        self._allow_fallback = False

    def reset(self, item):
        super(SvgItem, self).reset(item)

        name = self['name'].replace(' ', '_')
        category = self['category'].replace(' ', '_')

        renderer = self.renderers.get(category)
        if not renderer:
            fname = config.config['media_dir'] + category + '.svg'
            renderer = SvgRenderer(fname)
            if not renderer.isValid():
                raise ResetError('could not load renderer {}'.format(repr(fname)))
            self.renderers[category] = renderer

        self.setSharedRenderer(renderer)

        if not renderer.elementExists(name):
            if not self._allow_fallback:
                raise ResetError('could not render {}'.format(repr(name)))
        else:
            self.setElementId(name)

        self._svg_size = renderer.defaultSize()
        self._setPos()
        return True

    def _setPos(self):

        s = self._svg_size
        scale = float(self.tile_width) / max(s.width(), s.height())
        self.setScale(scale)
        x,y  = self.parentItem().center()
        h,w = s.height() * scale, s.width() * scale
        self.setPos(x-w/2,y-h/2)


class SvgIsoTileItem(SvgItem):

    def _setPos(self):

        size = self._svg_size
        scale = float(self.tile_width) / min(size.width(), size.height()) 
        self.setScale(scale)
        name = self['name'].replace(' ', '_')
        category = self['category'].replace(' ', '_')
        offset_scale = config.config['svg_tile_width']

        try:
            xo, yo = self.renderers[category].getOffset(name)
        except TypeError:
            xo, yo = 0, offset_scale / -16 # -8

        # FIXME I cannot see why should not be zero?!
        origin = offset_scale / 2, offset_scale / -16 # 64, -8

        x  = (xo - origin[0]) * scale
        y  = (yo - origin[1]) * scale
        self.setPos(x,y)


class SvgSpeciesItem(SvgItem):

    def _setPos(self):

        s = self._svg_size
        scale = float(self.tile_width) / max(s.width(), s.height())
        self.setScale(scale)
        x,y  = self.parentItem().center()
        h,w = s.height() * scale, s.width() * scale
        self.setPos(x-w/2,-y/2)


class SvgTransitionItem(SvgItem):

    def _setPos(self):
        size = self._svg_size
        scale = float(self.tile_width) / min(size.width(), size.height()) 
        self.setScale(scale)
        name = self['name'].replace(' ', '_')
        category = self['category'].replace(' ', '_')
        offset_scale = config.config['svg_tile_width']

        try:
            xo, yo = self.renderers[category].getOffset(name)
        except TypeError:
            xo, yo = 0, offset_scale / -16 # -8

        # FIXME I cannot see why should not be zero?!
        origin = offset_scale / 2, offset_scale / -16 # 64, -8

        x  = (xo - origin[0]) * scale
        y  = (yo - origin[1]) * scale
        self.setPos(x,y)

class SvgEquipmentItem(SvgItem):
    pass


#################################
### Tile Items
#################################


class TileItem(QtGui.QGraphicsPolygonItem, ResetItem):
    
    use_iso = False
    attrs = ('name', 'color', 'background', 'is_open', 'state', 'zval', 'category')

    points = [(0,0), (0,1),  (1,1), (1, 0)]
    opacity = {}
    walls = {}
    no_child = {}

    nonsvg_klass = CharItem
    svg_klass = CharItem # no svg for non-iso

    def __init__(self, parent, tile_width, use_svg, seethrough, debug, floor=False):

        super(TileItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        klass = self.svg_klass if use_svg else self.nonsvg_klass
        self.child = klass(parent, tile_width)
        self._seethrough = seethrough
        self._debug = debug
        self._iswall = None
        self._floor = floor
        self._use_svg = use_svg

        self.debug_item = QtGui.QGraphicsSimpleTextItem(self)
        self.debug_item.setBrush(QtGui.QBrush(QtGui.QColor('white')))
        self.debug_item.setZValue(2)
        font = self.debug_item.font()
        font.setFamily('monospace')
        font.setPixelSize(tile_width * .2)
        self.debug_item.setFont(font)
        if debug:
            self.debug_item.show()
            self.debug_item.setOpacity(.2)

        self._transitions = {}
        self._adjacent_transitions = {}
        self._svg_transitions = {}

    @property
    def idx(self):
        p = self.parentItem()
        return p.idx

    @property
    def is_wall(self):
        return self._iswall

    def reset(self, tile):
        super(TileItem, self).reset(tile)

        if self._debug:
            self.debug_item.setText('{},{}'.format(tile.x, tile.y))

        color = QtGui.QColor(self['background'])
        if self['state'] == 'see':
            pass
        elif self['state'] == 'memorized':
            color = QtGui.QColor(color.darker())
        elif self['state'] == 'unknown':
            color = QtGui.QColor(config.config['background'])
        else:
            raise ValueError(self['state'])

        pen_color = color

        for t in self._adjacent_transitions.values():
            t.reset(tile)

        # if we do not walls
        if self._seethrough or self._floor:
            points = self.points
            opacity = 255
        else:
            opacity = self.opacity.get(self['name'], 255)   
            points = self.walls.get(self['name'], self.points)
            # if we found a wall
            if points != self.points:
                # make the color darker
                pen_color = color.darker()

        self._iswall = (points != self.points)

        #scale the polygon to size
        s = self.tile_width
        points = [QtCore.QPointF(p[0]*s, p[1]*s) for p in points]
        poly = QtGui.QPolygonF(points)
        self.setPolygon(poly)
        self.setPen(QtGui.QPen(pen_color, 1))
        color.setAlpha(opacity)

        #if self['name'] != 'path':
        if self._debug:
            color.setAlpha(0)

        self.setBrush(QtGui.QBrush(color))

        # if want to hide the corners in iso view
        if not self._seethrough and self.no_child.get(self['name']):
            self.child.hide()
        else:
            self.child.show()
            self.child.reset(tile)

    @property
    def transitions(self):
        return self._transitions

    def setTransition(self, corner, adjacent, tile):

        ok = True
        if self.is_wall or corner.is_wall or adjacent.is_wall:
            ok = False

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
                item.setZValue(self['zval'] + 1)
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



class IsoTileItem(TileItem):

    use_iso = True
    svg_klass = SvgIsoTileItem
    points = [(0,0), (1,.5),  (0,1), (-1, .5)]
    walls = {
        'north wall':[(0,0), (0,  1),  (-1, .5), (-1, -.5)],
        'south wall':[(0,0), (0, -1),  ( 1,-.5), ( 1,  .5)],
        'west wall': [(0,0), (1,-.5),  ( 1, .5), ( 0,  1)],
        'east wall': [(0,0), (0, -1),  (-1,-.5), (-1,  .5)],

        'ne wall':[(0,0), (0,  0),  (0, 0), (0, 0)],
        'nw wall':[(0,0), (0,  0),  (0, 0), (0, 0)],
        'sw wall':[(0,0), (0,  0),  (0, 0), (0, 0)],
        'se wall':[(0,0), (0,  0),  (0, 0), (0, 0)],
    }
    opacity = {
        'south wall': 64,
        'east wall': 64,
        'north wall': 192,
        'west wall': 192,

    }
    no_child = {
        'ne wall':True,
        'nw wall':True,
        'sw wall':True,
        'se wall':True,
    }

    def __init__(self, parent, tile_width, use_svg, seethrough, debug, floor=False):

        super(IsoTileItem, self).__init__(parent, tile_width, use_svg, seethrough, debug, floor=False)
        self.debug_item.setPos(-tile_width/5, tile_width/3)



#################################
### Widget Items
#################################


class BaseItemWidget(QtGui.QGraphicsWidget):
    item_clicked = QtCore.pyqtSignal(QtGui.QGraphicsWidget)

    def _onItemClicked(self, event, gitem):
        self.item_clicked.emit(self)

    def offset(self):
        return self.parentItem().background.item.offset()

    def center(self):
        return self.parentItem().background.item.center()


class InventoryWidget(BaseItemWidget, ResetItem):
    
    attrs = tuple()

    nonsvg_klass = CharItem
    svg_klass = SvgEquipmentItem
    
    def __init__(self, parent, tile_width, use_svg):
        super(InventoryWidget, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        klass = self.svg_klass if use_svg else self.nonsvg_klass
        self.item = klass(self, tile_width)
        self.item._allow_fallback = True

        self.opaciter = OpacityAnimation(self)
        self._inventory = None
        self.__args = None

    def reset(self, inventory):
        #FIXME call superclass reset
        item = inventory and inventory[-1]
        if item:
            self.item.reset(item)
        self._inventory = inventory

    def _onFadeOutDone(self):
        self.reset(self._inventory)
        self.opaciter.finished.disconnect(self._onFadeOutDone)

    def change(self, inventory, use_svg, use_iso, seethrough):
        
        if inventory is None:
            raise ValueError
        
        if inventory and not self._inventory:
            self.reset(inventory)
            self.setOpacity(0)
            self.opaciter.fadeTo(1)
        elif self._inventory and not inventory:
            self._inventory = inventory
            self.opaciter.fadeTo(0)
            self.opaciter.finished.connect(self._onFadeOutDone)
        else:
            self.reset(inventory)


        
class BeingWidget(BaseItemWidget, ResetItem):

    attrs = ('is_player', 'guid')

    svg_klass = SvgSpeciesItem
    nonsvg_klass = CharItem

    def __init__(self, parent, tile_width, use_svg):
        super(BeingWidget, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        klass = self.svg_klass if use_svg else self.nonsvg_klass
        self.item = klass(self, tile_width)

        if use_svg:
            self.item._allow_fallback = True
        else:
            self.item.setBold()

        self._opaciter = OpacityAnimation(self)
        self._meleer = MeleeAnimation(self)
        self._movement = MovementAnimation(self)

    def __repr__(self):
        return '<BeingWidget #{}>'.format(self['guid'])

    def reset(self, being):
        super(BeingWidget, self).reset(being)
        self.item.reset(being)
        self.setPos(0,0)

    def _onDoneDying(self):

        self.scene().removeItem(self.item)
        self.scene().removeItem(self)

        del self._opaciter
        del self._movement
        del self.item
        self._meleer.del_()
        del self._meleer

    def die(self):
        self._opaciter.finished.connect(self._onDoneDying)
        self._opaciter.fadeTo(0)

    def melee(self, tile):
        self._meleer.melee(tile)

    def walk(self, tile):
        self._movement.walk(tile)


class BackgroundWidget(BaseItemWidget):
    
    tile_klass = TileItem

    def __init__(self, parent, tile_width, use_svg, seethrough, debug):
        super(BackgroundWidget, self).__init__(parent)
        self.item = self.tile_klass(self, tile_width, use_svg, seethrough, debug)
        if self.tile_klass.use_iso and not seethrough:
            self.floor = self.tile_klass(self, tile_width, use_svg, seethrough, debug, floor=True)
        else:
            self.floor = None

    def reset(self, tile):
        self.item.reset(tile)
        if self.item.is_wall and self.floor:
            self.floor.reset(tile)

    @property
    def idx(self):
        p = self.parentItem()
        return (p['x'], p['y'])

    def setTransition(self, corner, adjacent, tile):
        self.item.setTransition(corner.item, adjacent.item, tile)

class IsoBackgroundWidget(BackgroundWidget):
    tile_klass = IsoTileItem




#################################
### Tile Widget
#################################



class TileWidget(QtGui.QGraphicsWidget, ResetItem):
    
    attrs = ('x', 'y')

    tile_clicked = QtCore.pyqtSignal(QtGui.QGraphicsWidget)
    being_moved = QtCore.pyqtSignal(BeingWidget)
    background_klass = BackgroundWidget
    
    def __init__(self, tile_width, use_svg, seethrough, debug):
        super(TileWidget, self).__init__()
        ResetItem.__init__(self, tile_width)

        self.being = None
        self.background = self.background_klass(self, tile_width, use_svg, seethrough, debug)
        self.inventory = InventoryWidget(self, tile_width, use_svg)
        self._use_svg = use_svg


    def __repr__(self):
        return "<TileWidget ({},{}) {}>".format(self['x'], self['y'], self.being)

    def reset(self, tile):
        super(TileWidget, self).reset(tile)

        self.setPos(*self.offset())
        self.background.reset(tile)
        self.inventory.reset(tile.inventory)

        if self.being:
            self.scene().removeItem(self.being)
            self.being = None

        if tile.being:
            being = BeingWidget(self, self.tile_width, self._use_svg)
            self.being = being
            being.reset(tile.being)

    def offset(self):
        return (self['x'] * self.tile_width, self['y'] * self.tile_width)

    def center(self):
        #FIXME
        #xo, yo = self.background.center()
        #xo, yo = self.background.offset()
        p = self.pos()
        return p.x(), p.y()


class IsoTileWidget(TileWidget):

    background_klass = IsoBackgroundWidget

    def offset(self):
        return (
            (self['x'] - self['y']) * float(self.tile_width), 
            ((self['x'] + self['y']) / 2.) * self.tile_width
        )

