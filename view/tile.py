
from collections import namedtuple
from collections import OrderedDict

from PyQt4 import QtCore, QtGui, QtSvg

from util import Action
from animation import ScaleAnimation, MovementAnimation, ViewScrollAnimation, MeleeAnimation, PosAnimation, OpacityAnimation
from svg import InkscapeHandler, SvgRenderer
from info import LogWidget, InfoWidget, StatsWidget
import config



class ResetError(Exception):pass

#################################
### Items
#################################

class TransitionItem(QtGui.QGraphicsPathItem):
    
    points = {
        'sw-s': ((0,1), (-1,.5), (-2,1)),
        'sw-w': ((0,0), (-1,.5), (-2,0)),
        'nw-w': ((-1, -.5), (0,0), (-1, .5)),
        'nw-n': ((1, -.5), (0,0), (1, .5)),
        'ne-n': ((0,0), (1,.5), (2,0)),
        'ne-e': ((2,1), (1,.5), (0,1)),
        'se-e': ((1,.5), (0,1), (1,1.5)),
        'se-s': ((-1,.5), (0,1), (-1,1.5)),
    }
    def __init__(self, parent, size, transition):

        super(TransitionItem, self).__init__(parent)
        self._size = size
        self._color = transition.color

        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.WindingFill)

        x, y = transition.offset
        x = x - y
        y = (x + y) / 2.

        offset = QtCore.QPointF(x, y)
        points = [
            ((QtCore.QPointF(*p) + offset) *size) 
            for p in self.points[transition.direction]]

        path.moveTo(points[0])
        path.lineTo(points[1])
        path.lineTo(points[2])
        path.cubicTo(points[1], points[0], points[0])
        path.closeSubpath()

        self.setPath(path)
        self.path = path
        self.setZValue(transition.zval)

    def paint(self, painter, option, widget):
        
        painter.setBrush(self._color)
        painter.setPen(QtGui.QColor(0,0,0,0))

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.drawPath(self.path)

class SvgTransitionItem(QtSvg.QGraphicsSvgItem):
    
    renderer = SvgRenderer(config.MEDIA_DIR + 'dungeon.svg')
    offset_scale = 128 # tile width size used for tile offsets

    def __init__(self, parent, size, transition):
        super(SvgTransitionItem, self).__init__(parent)
        self._size = size
        self.setZValue(transition.zval)


        d = transition.direction.split('-')[1]
        xo, yo = 0, 0

        #FIXME fugly
        fix = {
        'se-e': ('e', (-1, 0)),
        'sw-w': ('n', (-1, .5)),
        'ne-e': ('s', (-1, 0)),
        }

        if fix.get(transition.direction):
            d, (xo, yo) = fix.get(transition.direction)
        name = transition.name + '_t_' + d

        if not self.renderer.elementExists(name):
            return
            raise ResetError('could not find element {}'.format(name))

        self.setSharedRenderer(self.renderer)
        self.setElementId(name)

        size = self.renderer.defaultSize()
        scale = float(self._size) / min(size.width(), size.height()) 
        self.setScale(scale)
        
        self.setPos(xo*self._size, yo*self._size)

        


class TileItem(QtGui.QGraphicsPolygonItem):
    
    square = [(0,0), (0,1),  (1,1), (1, 0)]
    parallelogram = [(0,0), (1,.5),  (0,1), (-1, .5)]

    walls = {
        'north wall':[(0,0), (0,  1),  (-1, .5), (-1, -.5)],
        'south wall':[(0,0), (0, -1),  ( 1,-.5), ( 1,  .5)],
        'west wall': [(0,0), (1,-.5),  ( 1, .5), ( 0,  1)],
        'east wall': [(0,0), (0, -1),  (-1,-.5), (-1,  .5)],
    }

    opacity = {
        'south wall': 64,
        'east wall': 64,
        'north wall': 255,
        'west wall': 255,
    }

    def __init__(self, parent, size):

        super(TileItem, self).__init__(parent)

        self._size = size
        self._transitions = []
        self._svg_transitions = []

        self._name = None
        self._color= None
        self._background = None
        self._is_open = None

        self.char = CharItem(self, size)
        self.svg = SvgIsoTileItem(self, size)

    def equiv(self, other):
        return self._dungeon == other._dungeon and self._svg == other._svg

    def center(self):
        #center of paralellagram
        # (a+c)/2, (b+d)/2
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

    def _showTransitions(self, use_iso, use_svg):
        
        if not use_iso:
            hide = self._transitions + self._svg_transitions
            show = []
        elif use_svg:
            show = self._transitions + self._svg_transitions
            hide = []
        else:
            show = self._transitions
            hide = self._svg_transitions

        for h in hide:
            h.hide()
        for s in show:
            s.show()


    def reset(self, tile, use_svg, use_iso, seethrough, floor=False):

        if tile is None and self._name is None:
            raise ResetError('Inital reset without tile')

        if tile is not None:
            self._name = tile.name
            self._color = tile.color
            self._background = tile.background
            self._is_open = tile.is_open

            for transition in [t for t in tile.transitions if t.zval > tile.zval]:
                t = TransitionItem(self, self._size, transition)
                svg = SvgTransitionItem(self, self._size, transition)
                self._transitions.append(t)
                self._svg_transitions.append(svg)

        color = QtGui.QColor(self._background)

        if use_iso and not seethrough:
            # set opacity if we want seethrough walls
            opacity = self.opacity.get(self._name, 255)   
            #  make the walls a little lighter than wall floors
            if self.opacity.get(self._name) and not floor:
                color = color.lighter()
        else:
            opacity = 255

        color.setAlpha(opacity)
        self.setBrush(QtGui.QBrush(color))
        self.setPen(QtGui.QPen(QtGui.QColor(0,0,0,0)))

        if use_iso and seethrough:
            points = self.parallelogram
        elif use_iso:
            points = self.walls.get(self._name, self.parallelogram)
            if points != self.parallelogram:
                self.setPen(QtGui.QPen(color.darker()))
        else:
            points = self.square

        #scale the polygon to size
        size = self._size
        points = [QtCore.QPointF(p[0]*size, p[1]*size) for p in points]
        poly = QtGui.QPolygonF(points)
        self.setPolygon(poly)

        self.char.reset(tile, use_svg, use_iso, seethrough)
        svg_ok = self.svg.reset(tile, use_svg, use_iso, seethrough)

        #dungeon svg is only iso right now
        if use_iso:
            if use_svg and svg_ok:
                self.char.hide()
                self.svg.show()
            elif use_svg and not svg_ok:
                self.svg.hide()
                self.char.show()
            else:
                self.svg.hide()
                self.char.show()
        else:
            self.svg.hide()
            self.char.show()

        # dont put character on walls
        if use_iso and not self._is_open and not floor:
            self.char.hide()

        #remove svg walls when seethrough
        if seethrough and not self._is_open:
            self.svg.hide()

        self._showTransitions(use_iso, use_svg)


    def mousePressEvent(self, event):
        self.parentItem()._onItemClicked(event, self)





class SvgIsoTileItem(QtSvg.QGraphicsSvgItem):
    
    dungeon  = SvgRenderer(config.MEDIA_DIR + 'dungeon.svg')
    offset_scale = 128 # tile width size used for tile offsets

    def __init__(self, parent, size):
        super(SvgIsoTileItem, self).__init__(parent)
        self._size = size
        self._name = None

    def reset(self, tile, use_svg, use_iso, seethrough):
        
        if tile is None and self._name is None:
            raise ResetError('Inital reset without tile')
        
        if tile is not None:
            self._name = tile.name.replace(' ', '_')

        if not self.dungeon.elementExists(self._name):
            return False
            #raise ResetError('could not find element {}'.format(tile.svg))

        self.setSharedRenderer(self.dungeon)
        self.setElementId(self._name)
        self._setPos()
        return True

    def _setPos(self):

        size = self.dungeon.defaultSize()
        scale = float(self._size) / min(size.width(), size.height()) 
        self.setScale(scale)

        try:
            xo, yo = self.dungeon.getOffset(self._name)
        except TypeError:
            xo, yo = 0, self.offset_scale / -16 # -8

        # FIXME I cannot see why should not be zero?!
        origin = self.offset_scale / 2, self.offset_scale / -16 # 64, -8

        x  = (xo - origin[0]) * scale
        y  = (yo - origin[1]) * scale
        self.setPos(x,y)

    def _onItemClicked(self, item):
        self.parentItem()._onItemClicked(event, self)


    
class CharItem(QtGui.QGraphicsSimpleTextItem):
    
    def __init__(self, parent, size):
        super(CharItem, self).__init__('', parent)

        self._size = size
        self._color = None
        self._char = None

        font = self.font()
        font.setFamily('monospace')
        font.setPixelSize(size)
        self.setFont(font)
        #self.setPen(QtGui.QPen(QtGui.QColor('black')))

    def _setPos(self):
        s = float(self._size)
        x,y = self.parentItem().center()
        off = self.font().pixelSize() / 2
        self.setPos(x - off/2, y - off)

    def reset(self, item, use_svg, use_iso, seethrough, bold=False):

        if item is None and self._char is None:
            raise ResetError('Inital reset without tile')
        elif item is None:
            self._char = ''

        if item is not None:
            self._char = item.char
            self._color = item.color

        font = self.font()
        if bold:
            font.setWeight(QtGui.QFont.Black)
        else:
            font.setWeight(QtGui.QFont.Normal)
        self.setFont(font)

        self.setBrush(self._color)
        self.setText(self._char)
        self._setPos()



class SvgSpeciesItem(QtSvg.QGraphicsSvgItem):

    
    genus = {}
    genus['human'] = QtSvg.QSvgRenderer(config.MEDIA_DIR + 'genus/human.svg')
    genus['orc'] = QtSvg.QSvgRenderer(config.MEDIA_DIR + 'genus/orc.svg')


    def __init__(self, parent, size):
        super(SvgSpeciesItem, self).__init__(parent)
        self._size = size
        self._svg_size = None
        self._genus = None
        self._species = None


    def reset(self, tile, use_svg, use_iso, seethrough):

        
        if tile is None and self._genus is None:
            raise ResetError('Inital reset without tile')
        
        if tile is not None:
            self._genus = tile.genus
            self._species = tile.species

        g = self._genus and self._genus.replace(' ', '_')
        s = self._species and self._species.replace(' ', '_')
        self._svg_size = self.genus[g].defaultSize()

        if not self.genus.has_key(g):
            raise ResetError('Could not find svg item {}'.format(g))

        self.setSharedRenderer(self.genus[g])

        # if we have the species: set it to that.
        if s and self.genus[g].elementExists(s):
            self.setElementId(s)

        self._setPos()

    def _setPos(self):

        s = self._svg_size
        scale = float(self._size) / max(s.width(), s.height())
        self.setScale(scale)
        x,y  = self.parentItem().center()
        h,w = s.height() * scale, s.width() * scale
        self.setPos(x-w/2,y-h/2)

    def mousePressEvent(self, event):
        self.parentItem()._onItemClicked(event, self)


class SvgEquipmentItem(QtSvg.QGraphicsSvgItem):

    
    #genus = {}
    #genus['human'] = QtSvg.QSvgRenderer(config.MEDIA_DIR + 'genus/human.svg')
    #genus['orc'] = QtSvg.QSvgRenderer(config.MEDIA_DIR + 'genus/orc.svg')


    def __init__(self, parent, size):
        super(SvgEquipmentItem, self).__init__(parent)
        self._size = size
        self._svg_size = None


    def reset(self, item, use_svg, use_iso, seethrough):

        
        if item is None and self._name is None:
            raise ResetError('Inital reset without tile')
        
        if item is not None:
            self._name = item.name.replace(' ', '_')
        return False

        #self._svg_size = self.genus[g].defaultSize()

        if not self.genus.has_key(g):
            raise ResetError('Could not find svg item {}'.format(g))

        self.setSharedRenderer(self.genus[g])

        # if we have the species: set it to that.
        if s and self.genus[g].elementExists(s):
            self.setElementId(s)

        self._setPos()

    def _setPos(self):

        s = self._svg_size
        scale = float(self._size) / max(s.width(), s.height())
        self.setScale(scale)
        x,y  = self.parentItem().center()
        h,w = s.height() * scale, s.width() * scale
        self.setPos(x-w/2,y-h/2)

    def mousePressEvent(self, event):
        self.parentItem()._onItemClicked(event, self)



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

class InventoryWidget(BaseItemWidget):

    def __init__(self, parent, size):
        super(InventoryWidget, self).__init__(parent)

        self.char = CharItem(self, size)
        self.svg = SvgEquipmentItem(self, size)
        self.opaciter = OpacityAnimation(self)
        self.__args = None

    def reset(self, inventory, use_svg, use_iso, seethrough):
        if inventory is not None:
            self._inventory = inventory

        if use_svg:
            self.char.hide()
            self.svg.show()
        else:
            self.char.show()
            self.svg.hide()

        if self._inventory:
            item = self._inventory[-1]
            self.char.reset(item, use_svg, use_iso, seethrough, bold=True)
            ok = self.svg.reset(item, use_svg, use_iso, seethrough)
            if use_svg and not ok:
                self.char.show()
        else:
            self.char.hide()
            self.svg.hide()

    def _onFadeOutDone(self):
        self.reset(*self.__args)
        self.opaciter.finished.disconnect()

    def change(self, inventory, use_svg, use_iso, seethrough):
        
        if inventory is None:
            raise ValueError
        
        if inventory and not self._inventory:
            self.reset(inventory, use_svg, use_iso, seethrough)
            self.setOpacity(0)
            self.opaciter.fadeTo(1)
        elif self._inventory and not inventory:
            self.opaciter.fadeTo(0)
            self.__args = (inventory, use_svg, use_iso, seethrough)
            self.opaciter.finished.connect(self._onFadeOutDone)
        else:
            self.reset(inventory, use_svg, use_iso, seethrough)


        
class BeingWidget(BaseItemWidget):

    finished_moving = QtCore.pyqtSignal(QtGui.QGraphicsWidget)

    def __init__(self, parent, size):
        super(BeingWidget, self).__init__(parent)

        self.char = CharItem(self, size)
        self.svg = SvgSpeciesItem(self, size)

        #if 1:#use_shadow:
        #    shadow = QtGui.QGraphicsDropShadowEffect()
        #    shadow.setOffset(-4, -8)
        #    shadow.setColor(QtGui.QColor(0,0,0, 20))
        #    self.item.setGraphicsEffect(shadow)

        #blur = QtGui.QGraphicsBlurEffect()
        #blur.setBlurRadius(1)
        #self.item.setGraphicsEffect(blur)

        self.movement = MovementAnimation(self)
        self.movement.finished.connect(self._onDoneMoving)

        self.opaciter = OpacityAnimation(self)

        self.melee = MeleeAnimation(self)
        self.is_player = None

    def _onDoneMoving(self):
        self.finished_moving.emit(self)

    def _onDoneDying(self):
        self.scene().removeItem(self)

    def die(self):
        self.opaciter.finished.connect(self._onDoneDying)
        self.opaciter.fadeTo(0)

    def reset(self, tile, use_svg, use_iso, seethrough):
        
        if tile is None and self.is_player is None:
            raise ResetError('Inital reset without tile')

        if tile:
            self.is_player = tile.being and tile.being.is_player

        self.svg.reset(tile and tile.being, use_svg, use_iso, seethrough)
        self.char.reset(tile and tile.being, use_svg, use_iso, seethrough, bold=True)

        if use_svg:
            self.char.hide()
            self.svg.show()
        else:
            self.svg.hide()
            self.char.show()
        self.setPos(0,0)



class BackgroundWidget(BaseItemWidget):

    def __init__(self, parent, size):
        super(BackgroundWidget, self).__init__(parent)

        self.floor = TileItem(self, size)
        self.floor.setZValue(-1)
        self.item = TileItem(self, size)

        self._is_open = None
        self._x = None
        self._y = None

    @property
    def x(self): return self._x
    @property
    def y(self): return self._y
    @property
    def idx(self): return self._x, self._y

    def reset(self, tile, use_svg, use_iso, seethrough):
        if tile:
            self._is_open = tile.is_open
            self._x = tile.x
            self._y = tile.y

        if not self._is_open:
            self.floor.reset(tile, use_svg, use_iso, True, floor=True)
        self.item.reset(tile, use_svg, use_iso, seethrough)





#################################
### Tile Widget
#################################



class TileWidget(QtGui.QGraphicsWidget):

    tile_clicked = QtCore.pyqtSignal(QtGui.QGraphicsWidget)
    being_moved = QtCore.pyqtSignal(BeingWidget)
    
    def __init__(self, size):
        super(TileWidget, self).__init__()

        self._size = size
        self._x = None
        self._y = None

        self._use_iso = None
        self._use_svg = None
        self._use_iso = None
        self_seethrough = None

        self.being = None

        self.background = BackgroundWidget(self, size)
        self.background.item_clicked.connect(self._onItemClicked)

        self.inventory = InventoryWidget(self, size)

        self.debug_item = QtGui.QGraphicsSimpleTextItem(self)
        self.debug_item.setBrush(QtGui.QBrush(QtGui.QColor('white')))
        self.debug_item.setPos(0, size/4)

    def __str__(self):
        return "<TileWidget ({},{})>".format(self._x, self._y)

    @property
    def x(self): 
        if not self._use_iso:
            return self._x * self._size
        else:
            return (self._x - self._y) * float(self._size)

    @property
    def y(self): 
        if not self._use_iso:
            return self._y * self._size
        else:
            return ((self._x + self._y) / 2.) * self._size

    #def offset(self): return self._size / -2.

    def reset(self, tile, use_svg, use_iso, seethrough, debug):

        if tile is None and self._x is None:
            raise ValueError('Forced reset without initial tile')

        if tile is not None:
            self._x = tile.x
            self._y = tile.y

        self._use_svg = use_svg
        self._use_iso = use_iso
        self._seethrough = seethrough

        xo, yo = self.parentItem().offset
        self.setPos(self.x + xo, self.y + yo)
        self.background.reset(tile, use_svg, use_iso, seethrough)
        self.inventory.reset(tile and tile.inventory, use_svg, use_iso, seethrough)

        if tile and tile.being:
            if self.being:
                self.scene().removeItem(self.being)
                self.being = None

            being = BeingWidget(self, self._size)
            being.finished_moving.connect(self.being_moved.emit)
            self.being = being
            being.reset(tile, use_svg, use_iso, seethrough)

        elif self.being:
            self.being.reset(None, use_svg, use_iso, seethrough)

        self.debug_item.setText('{}, {}'.format(self._x, self._y))

        if debug:
            self.debug_item.show()
            self.background.item.setPen(QtGui.QPen(QtGui.QColor('white')))
        else:
            self.debug_item.hide()
            self.background.item.setPen(QtGui.QPen(QtGui.QColor(0,0,0,0)))


    def center(self):
        #FIXME
        xo, yo = self.background.center()
        xo, yo = self.background.offset()
        p = self.pos()
        return p.x(), p.y()


    def _onItemClicked(self, item):
        self.tile_clicked.emit(self)





#################################
### Level
#################################

class LevelError(Exception): pass

class LevelWidget(QtGui.QGraphicsWidget):

    player_moved = QtCore.pyqtSignal(TileWidget)
    
    def __init__(self, tile_size, use_svg=True, use_iso=True):
        super(LevelWidget, self).__init__()

        self._tiles = {}
        self._tile_size = tile_size
        self.size = None
        self._use_iso = use_iso
        self._use_svg = use_svg
        self._debug = False
        self._seethrough=False
        self._movement_waiting = {}
        self._opaciter = OpacityAnimation(self)

        self.setFlags(self.flags() | self.ItemIsFocusable)
        self.setFocusPolicy(QtCore.Qt.TabFocus)

    def setTiles(self, tiles):

        scene = self.scene()
        for tile in self._tiles.values():
            scene.removeItem(tile)
            
        self._tiles = {}
        w, h = 0, 0
        for tile in tiles:
            widget = TileWidget(self._tile_size)
            widget.being_moved.connect(self._check_waiting)
            widget.setParentItem(self)
            widget.tile_clicked.connect(self._onTileClicked)
            self._tiles[tile.x, tile.y] = widget
            w = max(w, tile.x + 1)
            h = max(h, tile.y + 1)

        self.size = (w,h)

        self.reset(tiles)

    @property
    def player_tile(self):
        try:
            return [t for t in self._tiles.values() if t.being and t.being.is_player][-1]
        except IndexError:
            return None

    @property
    def offset(self):
        if self._use_iso:
            return (self.size[0] * self._tile_size) / -2, 0
        else:
            return 0, 0

    def setEnabled(self, enabled):

        opacity = 1 if enabled else .5
        self._opaciter.fadeTo(opacity)
        #self.setOpacity(opacity)
        super(LevelWidget, self).setEnabled(enabled)

    def reset(self, tiles):
        
        class Transition(object): # FIXME move this to its own class
            
            def __init__(self, name, direction, offset, color, zval):
                self.name = name
                self.direction = direction
                self.offset = offset
                self.color = color
                self.zval = zval
        
        if tiles is not None:
            direcs = {
                'ne': ('e',),# 'e'),
                'se': ('e',),# 'e'),
                'sw': ('w',),# 'w'),
                'nw': ('w',),# 'w'),
            }
            for y in range(self.size[1]):
                for x in range(self.size[0]):
                    tile = tiles[y * self.size[1] + x]
                    if False:#tile.name != 'path':
                        continue

                    for direc in direcs:
                        if tile.neighbors[direc] and tile.name == tile.neighbors[direc].name:
                            for d in direcs[direc]:
                                # if we have a transition
                                n = tile.neighbors[d]
                                if n.name != tile.name:
                                    t = Transition(tile.name, direc + '-' + d, (tile.x - n.x, tile.y - n.y), tile.background, tile.zval)
                                    n.transitions.append(t)

                    
        
        game = self.parentItem()

        if tiles is None:
            update = [(None, w) for w in self._tiles.values()]
        else:
            #FIXME check if it changed
            update = [(t, self._tiles[t.x, t.y]) for t in tiles]

        for tile, widget in update:
            widget.reset(tile, game.use_svg, game.use_iso, game.seethrough, game.debug)

    def _onTileInventoryChanged(self, idx, inventory):
        tile = self._tiles[idx]
        game = self.parentItem()
        tile.inventory.change(inventory, game.use_svg, game.use_iso, game.seethrough)

    def _onBeingMeleed(self, old_idx, new_idx):
        being = self._tiles[old_idx].being
        tile = self._tiles[new_idx]
        being.melee.melee(tile)

    def _onBeingDied(self, tile_idx):
        tile = self._tiles[tile_idx]
        tile.being.die()
        tile.being = None

    def _onBeingMoved(self, old_idx, new_idx):
        old = self._tiles[old_idx]
        new = self._tiles[new_idx]
        being = old.being

        if not being:
            self._movement_waiting[(old_idx, new_idx)] = None
        else:
            being.movement.walk(new)
            if being.is_player:
                self.player_moved.emit(new)


    def _check_waiting(self, being):

        # if another being is still in animation it will be 
        # temporarily reparented to this widget
        # so it can not be the right movement we want
        parent = being.parentItem()
        if not hasattr(parent, 'background'):
            return
            
        for (old, new) in self._movement_waiting.keys():
            if old == parent.background.idx:
                self._onBeingMoved(old, new)
                del self._movement_waiting[(old, new)]



    def _onTileClicked(self, tile):

        player = self.player_tile
        new = player.pos() - tile.pos() + self.pos()
        #self.move.setup(new)
        #self.move.start()

        player.being.walk_anima.walk(tile)


class GameWidget(QtGui.QGraphicsWidget):

    def __init__(self, game):
        super(GameWidget, self).__init__()

        self.game = game

        game.events['game_started'].connect(self._onGameStarted)
        game.events['game_ended'].connect(self._onGameEnded)

        self.tile_size = 64
        self.use_svg = False
        self.use_iso = True
        self.seethrough = False
        self.debug = False

        self.level = LevelWidget(self.tile_size, self.use_svg, self.use_iso)
        self.level.setParentItem(self)
        self.level.setFocus()

        self._info = InfoWidget()
        self._info.setZValue(1)
        self._info.setParentItem(self)
        self._info.resize_event.connect(self._onInfoResizeEvent)
        self._info.gained_focus.connect(self._onWidgetGainedFocus)
        self._info.lost_focus.connect(self._onWidgetLostFocus)

        self._stats = StatsWidget()
        self._stats.setZValue(1)
        self._stats.setParentItem(self)

        self._log = LogWidget()
        self._log.setZValue(1)
        self._log.setParentItem(self)

        self._last_viewport_rect = None
        self._last_viewport_scale = None
        
        self.menus = OrderedDict()

        for name, value in game.commands.iteritems():
            self.menus[name] = QtGui.QMenu('&' + name.capitalize())
            for keystroke, value in game.commands[name].items():
                action = Action(self, value[0], [keystroke], self._onAction, args=(name, value[1]))

                if name == 'game':
                    self.addAction(action)
                else:
                    action.setShortcutContext(QtCore.Qt.WidgetShortcut)
                    self.level.addAction(action)
                self.menus[name].addAction(action)

        menu = QtGui.QMenu('&Settings')
        self.menus['settings'] = menu
        for name in game.settings:
            action = Action(self, name, ['Ctrl+' + name[0]], self._onSettingsChanged, args=(name,))
            action.setCheckable(True)
            action.setChecked(game.settings[name])
            menu.addAction(action)

    def _onGameStarted(self, level):

        player = self.game.player
        game = self.game
        self._info.setPlayer(player)
        self._stats.setPlayer(player)

        #XXX these events are re-instatiated every time a new dungeon is created ... e.g a new game
        #    so events will not fire if not reconnected each time
        game.events['level_changed'].connect(self._onLevelChanged)
        game.events['map_changed'].connect(self._onMapChanged)
        game.events['being_moved'].connect(self.level._onBeingMoved)
        game.events['being_meleed'].connect(self.level._onBeingMeleed)
        game.events['being_died'].connect(self.level._onBeingDied)
        game.events['tile_inventory_changed'].connect(self.level._onTileInventoryChanged)

        game.events['action_happened_in_dungeon'].connect(self._log.appendDungeonMessage)
        game.events['turn_finished'].connect(self._log.onTurnFinished)
        player.events['action_happened_to_player'].connect(self._log.appendPlayerMessage)

        self._onLevelChanged(level)
        self.level.setEnabled(True)
        self.level.setFocus()
        player.emit_info()

    def _onGameEnded(self):
        self.level.setEnabled(False)

    def _onSettingsChanged(self, setting):
        for l in self.actions.values():
            for action in l:
                if action.name == str(setting):
                   self.game.set_setting(setting,action.isChecked())
                   return
        raise ValueError(setting)


    def _onAction(self, kind, name):
        if kind == 'game':
            getattr(self.game, name)()
        else:
            self.game.player.dispatch_command(name)

    @property
    def player_tile(self):
        return self.level.player_tile

    def advanceFocus(self):
        self._info.advanceFocus()

    def toggleSeethrough(self):
        self.seethrough = not self.seethrough
        self.level.reset(None)

    def toggleIso(self):
        self.use_iso = not self.use_iso
        self.level.reset(None)

    def toggleSvg(self):
        self.use_svg = not self.use_svg
        self.level.reset(None)

    def toggleDebug(self):
        self.debug = not self.debug
        self.level.reset(None)

    #def toggleLog(self):
    #    self._log.toggleAlwaysShow()


    def _onLevelChanged(self, level):
        self.level.setTiles(level.tiles())
        self.level.player_moved.emit(self.player_tile)

    def _onMapChanged(self, level):
        self.level.reset(level.tiles())

    def _onWidgetGainedFocus(self, widget):
        if widget.selectable:
            self.level.setEnabled(False)
        else:
            self.level.setEnabled(True)

    def _onWidgetLostFocus(self, widget):
        if widget.selectable:
            self.level.setEnabled(True)
            self.level.setFocus()

    def _onViewportChanged(self, rect, scale):
        of = 5

        self._stats.setPos(rect.x() + of, rect.y() + of)
        self._stats.setHtml()

        geom = self._log.geometry()
        size = self._log.sizeHint(QtCore.Qt.PreferredSize)
        self._log.setPos(rect.x(), rect.y() + rect.height() - geom.height() - size.height())

        geom = self._info.geometry()
        self._info.setPos(rect.x() + rect.width() - geom.width() * (1/scale) - of, rect.y() + of)

        self._last_viewport_rect = rect
        self._last_viewport_scale = scale

    def _onInfoResizeEvent(self):
        self._onViewportChanged(self._last_viewport_rect, self._last_viewport_scale)
            
    def _onViewScaleChanged(self, factor):
        for widget in [self._log, self._info, self._stats]:
            widget.setScale(1 / factor)


#################################
### Scene
#################################

        
class LevelScene(QtGui.QGraphicsScene):
    
    background_color = QtGui.QColor('black')

    def __init__(self, game_widget):
        
        super(LevelScene, self).__init__()

        self.widget = game_widget
        self.addItem(self.widget)
        self.setBackgroundBrush(QtGui.QBrush(self.background_color))


class LevelView(QtGui.QGraphicsView):
    
    viewport_changed  = QtCore.pyqtSignal(QtCore.QRectF, float)
    scale_changed  = QtCore.pyqtSignal(float)

    def __init__(self, scene):
        super(LevelView, self).__init__(scene)

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.scaler = ScaleAnimation(self)
        self.scroller = ViewScrollAnimation(self)

        self.horizontalScrollBar().valueChanged.connect(self._onValueChanged)
        self.verticalScrollBar().valueChanged.connect(self._onValueChanged)
        self.viewport_changed.connect(scene.widget._onViewportChanged)
        self.scale_changed.connect(scene.widget._onViewScaleChanged)

        scene.widget.level.player_moved.connect(self.centerPlayer)

        step = 5
        self.addActions([
            Action(self, 'Zoom Out', ['-'], self.scaler.scale, (.8,)),
            Action(self, 'Zoom In', ['+'], self.scaler.scale, (1.25,)),
            Action(self, 'Zoom 1', ['='], self.scaler.scaleToOne),
            Action(self, 'Scroll Left', ['Shift+H'], self.scroller.scroll, ('west',)),
            Action(self, 'Scroll Right', ['Shift+L'], self.scroller.scroll, ('east',)),
            Action(self, 'Scroll Up', ['Shift+K'], self.scroller.scroll, ('north',)),
            Action(self, 'Scroll Down', ['Shift+J'], self.scroller.scroll, ('south',)),
            Action(self, 'Center on Player', ['4'], self.centerPlayer),

            Action(self, 'Toggle Iso', ['F1'], self._onToggleIso),
            Action(self, 'Toggle Svg', ['F2'], scene.widget.toggleSvg),
            Action(self, 'Toggle Seethrough', ['F3'], scene.widget.toggleSeethrough),
            #Action(self, 'Toggle Log', ['F4'], scene.widget.toggleLog),
            Action(self, 'Toggle Debug', ['F12'], scene.widget.toggleDebug),
            Action(self, 'Change Focus', ['Tab'], scene.widget.advanceFocus),
        ])

    def resizeEvent(self, event):
        self.centerPlayer()

    def _onToggleIso(self):
        self.scene().widget.toggleIso()
        self.centerOn(self.scene().widget.player_tile)

    def _onValueChanged(self, value):

        rect = self.viewport().geometry()
        new = self.mapToScene(rect).boundingRect()
        self.viewport_changed.emit(new, self.getScale())

    def getScale(self):
        t = self.transform()
        sx, sy = t.m11(), t.m22()
        if sx != sy:
            raise ValueError('Aspect Ratio Corrupt')
        return sx
    def setScale(self, factor):
        t = QtGui.QTransform.fromScale(1, 1)
        t.scale(factor, factor)
        self.setTransform(t)
        self.scale_changed.emit(factor)
    scale = QtCore.pyqtProperty('float', getScale, setScale)

    def getHpos(self): return self.horizontalScrollBar().value()
    def setHpos(self, value): return self.horizontalScrollBar().setValue(value)
    hpos = QtCore.pyqtProperty('int', getHpos, setHpos)

    def getVpos(self): return self.verticalScrollBar().value()
    def setVpos(self, value): return self.verticalScrollBar().setValue(value)
    vpos = QtCore.pyqtProperty('int', getVpos, setVpos)

    def centerPlayer(self, tile=None):

        scene = self.scene()
        if not scene:
            return
        if not tile:
            tile = scene.widget.player_tile
        if not tile:
            return
        pos = tile.pos()
        self.scroller.position(pos)



#################################
### test
#################################





