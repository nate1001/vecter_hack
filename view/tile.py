

from PyQt4 import QtCore, QtGui, QtSvg

from animation import MovementAnimation, MeleeAnimation, PosAnimation, OpacityAnimation
from svg import InkscapeHandler, SvgRenderer
import config

import gc
gc.set_debug(gc.DEBUG_UNCOLLECTABLE)


class ResetError(Exception):pass

class ResetItem(object):

    def __init__(self, size):
        #super(ResetItem, self).__init__()
        
        self.size = size
        self._attrs = {}
        for attr in self.attrs:
            self._attrs[attr] = None

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

class TransitionItem(QtGui.QGraphicsPathItem, ResetItem):
    
    attrs = ('background', 'zval')
    
    @classmethod
    def getPoints(cls, tile, corner, adjacent):
        
        if tile.is_wall or corner.is_wall or adjacent.is_wall:
            return None

        if corner['name'] != tile['name'] or adjacent['name'] == tile['name']:
            return None

        #only add transitions when the object tile has higher presidence
        if adjacent['zval'] >= tile['zval']:
            return None

        # get the shared points mapped to adjacent coords
        ao = corner.mapFromItem(adjacent, adjacent.pos())
        corner_side = [(adjacent.mapFromItem(corner, p)) for p in list(corner.polygon()) if p-ao in adjacent.polygon()]
        ao = tile.mapFromItem(adjacent, adjacent.pos())
        tile_side = [(adjacent.mapFromItem(tile, p)) for p in list(tile.polygon()) if p-ao in adjacent.polygon()]

        if len(corner_side) != 2 or len(tile_side) != 2:
            raise ValueError()

        middle = [p for p in tile_side if p in corner_side]
        points = [p for p in (corner_side + tile_side) if p != middle[0]]

        if len(middle) != 1 or len(points) != 2:
            raise ValueError

        return (points[0], middle[0], points[1])
    
    def __init__(self, parent, points, other):
        
        super(TransitionItem, self).__init__(parent)
        ResetItem.__init__(self, None)

        self._background = other['background']
        self._current = self._background
        self.setZValue(other['zval'])

        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.WindingFill)
        path.moveTo(points[0])
        path.lineTo(points[1])
        path.lineTo(points[2])
        path.cubicTo(points[1], points[1], points[0])
        #p1 = self._in(points[1], points[2])
        #p2 = self._in(points[1], points[0])
        #path.cubicTo(p1, p2, points[0])
        path.closeSubpath()
        self.setPath(path)

    def _in(self, p1, p2):
        x = p2.x() - p1.x()
        y = p2.y() - p1.y()
        return QtCore.QPointF(x * 1.5, y / 2)

    def _out(self, p1, p2):
        x = p2.x() - p1.x()
        y = p2.y() - p1.y()
        return QtCore.QPointF(x / 1.5, y / 2)

    def resetLit(self, tile):

        #FIXME this will probably race with other reset on occasion
        color = {
            'see': self._background,
            'memorized': self._background.darker(),
            'unknown': config.colors['background']
        }[tile.state]
        self._current = color


    def paint(self, painter, option, widget):
        #painter.setRenderHint(painter.Antialiasing)
        painter.setBrush(QtGui.QBrush(self._current))
        painter.setPen(self._current)
        painter.pen().setWidth(0)
        painter.drawPath(self.path())



class CharItem(QtGui.QGraphicsSimpleTextItem, ResetItem):
    
    attrs = ('color', 'char')
    
    def __init__(self, parent, size):
        super(CharItem, self).__init__('', parent)
        ResetItem.__init__(self, size)

        font = self.font()
        font.setFamily('monospace')
        font.setPixelSize(size *.8)
        self.setFont(font)

    def setBold(self):
        font = self.font()
        font.setWeight(QtGui.QFont.Black)
        self.setFont(font)

    def reset(self, item):
        super(CharItem, self).reset(item)

        self.setBrush(self['color'])
        self.setText(self['char'])

        s = float(self.size)
        x,y = self.parentItem().center()
        off = self.font().pixelSize() / 2
        self.setPos(x - off/2, y - off)


#################################
### Svg Items
#################################


class SvgItem(QtSvg.QGraphicsSvgItem, ResetItem):
    
    renderers = {}

    attrs = ('category', 'name')

    def __init__(self, parent, size):
        super(SvgItem, self).__init__(parent)
        ResetItem.__init__(self, size)
        self._svg_size = None
        self._allow_fallback = False

    def reset(self, item):
        super(SvgItem, self).reset(item)

        name = self['name'].replace(' ', '_')
        category = self['category'].replace(' ', '_')

        renderer = self.renderers.get(category)
        if not renderer:
            renderer = SvgRenderer(config.MEDIA_DIR + category + '.svg')
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
        scale = float(self.size) / max(s.width(), s.height())
        self.setScale(scale)
        x,y  = self.parentItem().center()
        h,w = s.height() * scale, s.width() * scale
        self.setPos(x-w/2,y-h/2)


class SvgIsoTileItem(SvgItem):

    offset_scale = 128 # tile width size used for tile offsets

    def _setPos(self):

        size = self._svg_size
        scale = float(self.size) / min(size.width(), size.height()) 
        self.setScale(scale)
        name = self['name'].replace(' ', '_')
        category = self['category'].replace(' ', '_')

        try:
            xo, yo = self.renderers[category].getOffset(name)
        except TypeError:
            xo, yo = 0, self.offset_scale / -16 # -8

        # FIXME I cannot see why should not be zero?!
        origin = self.offset_scale / 2, self.offset_scale / -16 # 64, -8

        x  = (xo - origin[0]) * scale
        y  = (yo - origin[1]) * scale
        self.setPos(x,y)


class SvgSpeciesItem(SvgItem):
    pass
class SvgEquipmentItem(SvgItem):
    pass
class SvgTransitionItem(SvgItem):
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


    def __init__(self, parent, size, use_svg, seethrough, debug, floor=False):

        super(TileItem, self).__init__(parent)
        ResetItem.__init__(self, size)

        klass = self.svg_klass if use_svg else self.nonsvg_klass
        self.child = klass(parent, size)
        self._seethrough = seethrough
        self._debug = debug
        self._iswall = None
        self._floor = floor

        self.debug_item = QtGui.QGraphicsSimpleTextItem(self)
        self.debug_item.setBrush(QtGui.QBrush(QtGui.QColor('white')))
        self.debug_item.setPos(-size/5, size/3)
        self.debug_item.setZValue(2)
        if debug:
            self._debug_pen = QtGui.QColor('white')
            self.debug_item.show()

        self._transitions = {}
        self._svg_transitions = []


    @property
    def is_wall(self):
        return self._iswall

    def setTransition(self, idx, other, points):
        if not self._transitions.get(idx):
            item = TransitionItem(self, points, other)
            self._transitions[idx] = item

    def clearTransition(self, idx):
        item = self._transitions.get(idx)
        if item:
            self.scene().removeItem(item)
            del self._transitions[idx]

    def clearTransitions(self):
        for key, item in self._transitions.items():
            self.scene().removeItem(item)
            del self._transitions[key]

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

    def reset(self, tile):
        super(TileItem, self).reset(tile)

        if self._debug:
            self.debug_item.setText('{}, {}'.format(tile.x, tile.y))

        color = QtGui.QColor(self['background'])
        if self['state'] == 'memorized':
            color = QtGui.QColor(color.darker())
        pen_color = color if not self._debug else self._debug_pen

        for t in self._transitions.values():
            t.resetLit(tile)

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
        size = self.size
        points = [QtCore.QPointF(p[0]*size, p[1]*size) for p in points]
        poly = QtGui.QPolygonF(points)
        self.setPolygon(poly)
        self.setPen(QtGui.QPen(pen_color, 0))
        color.setAlpha(opacity)
        self.setBrush(QtGui.QBrush(color))

        # if want to hide the corners in iso view
        if not self._seethrough and self.no_child.get(self['name']):
            self.child.hide()
        else:
            self.child.show()
            self.child.reset(tile)






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
    svg_klass = CharItem
    
    def __init__(self, parent, size, use_svg):
        super(InventoryWidget, self).__init__(parent)
        ResetItem.__init__(self, size)

        klass = self.svg_klass if use_svg else self.nonsvg_klass
        self.item = klass(self, size)

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

    def __init__(self, parent, size, use_svg):
        super(BeingWidget, self).__init__(parent)
        ResetItem.__init__(self, size)

        klass = self.svg_klass if use_svg else self.nonsvg_klass
        self.item = klass(self, size)

        if use_svg:
            self.item._allow_fallback = True
        else:
            self.item.setBold()

        self._opaciter = OpacityAnimation(self)
        self._meleer = MeleeAnimation(self)
        self._movement = MovementAnimation(self)

    def __repr__(self):
        return '<BeingWidget #{}>'.format(self['guid'])

    def __del__(self):
        config.logger.debug('Deleting Being #{}.'.format(self['guid']))

    def reset(self, being):
        super(BeingWidget, self).reset(being)
        self.item.reset(being)
        self.setPos(0,0)
        config.logger.debug('Resetting Being #{}.'.format(being.guid))

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

    def __init__(self, parent, size, use_svg, seethrough, debug):
        super(BackgroundWidget, self).__init__(parent)
        self.item = self.tile_klass(self, size, use_svg, seethrough, debug)
        if self.tile_klass.use_iso and not seethrough:
            self.floor = self.tile_klass(self, size, use_svg, seethrough, debug, floor=True)
        else:
            self.floor = None

    def reset(self, tile):
        self.item.reset(tile)
        if self.item.is_wall and self.floor:
            self.floor.reset(tile)

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
    
    def __init__(self, size, use_svg, seethrough, debug):
        super(TileWidget, self).__init__()
        ResetItem.__init__(self, size)

        self.being = None
        self.background = self.background_klass(self, size, use_svg, seethrough, debug)
        self.inventory = InventoryWidget(self, size, use_svg)
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
            being = BeingWidget(self, self.size, self._use_svg)
            self.being = being
            being.reset(tile.being)

    def offset(self):
        return (self['x'] * self.size, self['y'] * self.size)

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
            (self['x'] - self['y']) * float(self.size), 
            ((self['x'] + self['y']) / 2.) * self.size
        )





