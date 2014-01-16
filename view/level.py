
from itertools import product
from collections import OrderedDict

from PyQt4 import QtCore, QtGui
from animation import BeingAnimation, PosAnimation, OpacityAnimation, FadeInOutAnimation, RayAnimation

from tile import TransitionItem, TransitionPoints
from tile import FloorItem, IsoFloorItem, FloorDebugItem
from feature import FaceItem, RoofItem, SideItem, ArchItem, DoorItem, CharFeatureItem

from util import Action, ResetItem, CharItem, Direction
from svg import SvgEquipmentItem, SvgSpeciesItem, ChibiDirectionWidget, SvgFeatureItem, SvgSpellItem

from config import direction_by_abr


class DummyItem(ResetItem):
    attrs = tuple()
    def __init__(self, tile_width, *args):
        super(DummyItem, self).__init__(tile_width)
    def setZValue(self, val):pass
    def reset(self, item, *args):pass
    def show(self): pass
    def hide(self): pass
    def setOpacity(self, o): pass

        

#################################
### Widget Items
#################################

class RayItem(QtGui.QGraphicsPathItem, ResetItem):

    attrs = ('color',)
    corners = {
        'n' :   (.5,0),
        'ne':   (0,1),
        'e':    (1, .5),
        'se':   (1,1),
        's':    (.5,1),
        'sw':   (0, 1),
        'w':    (0, .5),
        'nw':   (0,0)
    }
    
    def __init__(self, parent, tile_width, direction):
        super(RayItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        path = QtGui.QPainterPath()
        w = tile_width
        d = self.wandDirection(direction)
        xo, yo = self.corners[d.opposite]
        path.moveTo(xo*w,  yo*w)
        xo, yo = self.corners[d.abr]
        path.lineTo(xo*w, yo*w)
        self.setPath(path)

    def wandDirection(self, direction):
        return direction

    def reset(self, spell):
        super(RayItem, self).reset(spell)
        self.setPen(QtGui.QPen(QtGui.QColor(self['color']), 1))


class IsoRayItem(RayItem):

    corners = {
        'n' :   (0,0),
        'ne':   (.5, .25),
        'e':    (1, .5),    
        'se':   (.5, .75),
        's':    (0,1),
        'sw':   (-.5, .75),
        'w':    (-1, .5),
        'nw':   (-.5, .25)
    }

    def wandDirection(self, direction):
        return direction_by_abr[direction.iso]


class RayWidget(QtGui.QGraphicsWidget):

    ray_klass = RayItem

    def __init__(self, parent, tile_width, direction):
        super(RayWidget, self).__init__(parent)

        self.animation = RayAnimation(self)
        self.item = self.ray_klass(self, tile_width, direction)

    def cast(self, wand, start, end):
        self.animation = RayAnimation(self)
        self.item.reset(wand)
        start = QtCore.QPointF(*start)
        end = QtCore.QPointF(*end)
        self.setPos(start)
        self.animation.setup(end)
            
class IsoRayWidget(RayWidget):
    ray_klass = IsoRayItem


class ZapWidget(QtGui.QGraphicsWidget):
    ray_klass = RayWidget

    def __init__(self, parent, tile_width):
        super(ZapWidget, self).__init__(parent)

        self.animation = QtCore.QSequentialAnimationGroup(self)
        self.animation.finished.connect(self._onFinished)
        self.widgets = {}
        for abr, direction in direction_by_abr.items():
            self.widgets[abr] = self.ray_klass(self, tile_width, direction)
            self.widgets[abr].hide()

    def cast(self, spell, direction, start, end):

        widget = self.widgets[direction.abr]
        widget.cast(spell, start, end)
        self.animation.addAnimation(widget.animation)
        self.animation.start()

    def _onFinished(self):
        self.animation.clear()
        

class IsoZapWidget(ZapWidget):
    ray_klass = IsoRayWidget


class SpellWidget(QtGui.QGraphicsWidget):

    def __init__(self, parent, tile_width, use_svg):

        super(SpellWidget, self).__init__(parent)

        if use_svg:
            self.spell = SvgSpellItem(self, tile_width)
            self.animation = FadeInOutAnimation(self)
        else:
            self.spell = None

    def show(self, spell):
        if self.spell:
            self.spell.reset(spell)
            self.animation.fade()

    def offset(self):
        return self.parentItem().offset()


class BaseItemWidget(QtGui.QGraphicsWidget, ResetItem):
    item_clicked = QtCore.pyqtSignal(QtGui.QGraphicsWidget)

    def __init__(self, parent, tile_width):
        super(BaseItemWidget, self).__init__(parent)
        self._animations = QtCore.QSequentialAnimationGroup()

    def _onItemClicked(self, event, gitem):
        self.item_clicked.emit(self)

    def offset(self):
        return self.parentItem().background.floor.offset()

    def center(self):
        return self.parentItem().background.floor.center()


class InventoryWidget(BaseItemWidget, ResetItem):
    
    attrs = tuple()

    nonsvg_klass = CharItem
    svg_klass = SvgEquipmentItem
    
    def __init__(self, parent, tile_width, use_svg):
        super(InventoryWidget, self).__init__(parent, tile_width)
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

    attrs = ('is_player', 'direction', 'guid')

    svg_klass = SvgSpeciesItem
    player_svg_klass = ChibiDirectionWidget
    nonsvg_klass = CharItem

    def __init__(self, parent, tile_width, use_svg, is_player):
        super(BeingWidget, self).__init__(parent, tile_width)
        ResetItem.__init__(self, tile_width)

        if use_svg and is_player:
            klass = ChibiDirectionWidget
        elif use_svg:
            klass = SvgSpeciesItem
        else:
            klass = CharItem

        self._current = None
        self.items = {}
        for direction in Direction.viewable(use_svg):
            self.items[direction] = klass(self, tile_width, direction)
            #FIXME figure out some other place to do this
            if not use_svg:
                self.items[direction].setBold()

        self.animation = BeingAnimation(self)

    def __repr__(self):
        return '<BeingWidget #{}>'.format(self['guid'])

    def reset(self, being):
        super(BeingWidget, self).reset(being)

        for direc, widget in self.items.items():
            widget.reset(being)
            widget.setOpacity(0)

        direc = Direction.toViewed(self['direction'])
        self.setDirection(direc)

    def updateUsing(self, using):
        for widget in self.items.values():
            widget.setUsing(using)

    def die(self):
        self.animation.die()

    def melee(self, tile, direc):
        direc = Direction.toViewed(direc)
        self.setDirection(direc)
        self.animation.melee(tile)

    def walk(self, old_tile, new_tile, level, direction):
        direc = Direction.toViewed(direction)
        self.setDirection(direc)
        self.animation.walk(old_tile, new_tile, level)

    def setDirection(self, direction):
        if not self.items.get(direction):
            return

        if self._current:
            #self.widgets[self._current].animation.fadeTo(0)
            self.items[self._current].setOpacity(0)
        self.items[direction].setOpacity(1) 
        self._current = direction




class BackgroundWidget(BaseItemWidget, ResetItem):
    
    attrs = ('name',)
    floor_klass = FloorItem

    def __init__(self, parent, tile_width, use_svg, seethrough, debug, use_char):
        super(BackgroundWidget, self).__init__(parent, tile_width)
        ResetItem.__init__(self, tile_width)

        self.floor = self.floor_klass(self, tile_width, use_svg, use_char)
        self.debug = FloorDebugItem(self, tile_width) if debug else None

        self.spell = SpellWidget(self, tile_width, use_svg)
        self.spell.setZValue(100)
            
    def reset(self, tile):
        super(BackgroundWidget, self).reset(tile)
        
        self.floor.reset(tile)
        if self.debug:
            self.debug.reset(tile)
            self.floor.setPen(QtGui.QColor('white'))

    @property
    def idx(self):
        p = self.parentItem()
        return (p['x'], p['y'])

    def setTransition(self, corner, adjacent, tile):
        self.floor.setTransition(corner.floor, adjacent.floor, tile)

class IsoBackgroundWidget(BackgroundWidget):
    floor_klass = IsoFloorItem




#################################
### Tile Widget
#################################



class TileWidget(QtGui.QGraphicsWidget, ResetItem):
    
    attrs = ('x', 'y', 'features')

    tile_clicked = QtCore.pyqtSignal(QtGui.QGraphicsWidget)
    being_moved = QtCore.pyqtSignal(BeingWidget)
    background_klass = BackgroundWidget
    feature_klasses = {
        'face': DummyItem,
        'roof': DummyItem,
        'side': DummyItem,
        'arch': DummyItem,
        'door': DummyItem,
        'stairs': CharItem,
    }
    svg_feature_klass = DummyItem
    
    def __init__(self, tile_width, use_svg, seethrough, debug, use_char):
        super(TileWidget, self).__init__()
        ResetItem.__init__(self, tile_width)

        self._seethrough = seethrough
        self._use_svg = use_svg
        self.being = None
        self.background = self.background_klass(self, tile_width, use_svg, seethrough, debug, use_char)
        self.inventory = InventoryWidget(self, tile_width, use_svg)
        self.features = {}
        for name, klass in self.feature_klasses.items():
            self.features[name] = klass(self, tile_width, use_svg)
            self.features[name].setZValue(2)

    def __repr__(self):
        return "<TileWidget ({},{}) {}>".format(self['x'], self['y'], self.being)

    def reset(self, tile):
        super(TileWidget, self).reset(tile)

        self.setPos(*self.offset())
        self.background.reset(tile)
        self.inventory.reset(tile.inventory)

        if self.being:
            self.scene() and self.scene().removeItem(self.being)
            self.being = None

        if tile.being:
            being = BeingWidget(self, self.tile_width, self._use_svg, tile.being.is_player)
            self.being = being
            being.reset(tile.being)
            self.being.show()

        for feature, item in self.features.items():
            if self._seethrough:
                item.hide()
            elif feature in self['features']:
                item.reset(tile)
                item.show()
            else:
                item.hide()

    def offset(self):
        return (self['x'] * self.tile_width, self['y'] * self.tile_width)

    def center(self):
        return self.background.center()

    def teleport_being_away(self):
        self.being.animation.teleport_away()
        #FIXME we should delete the being after the animation is done


class IsoTileWidget(TileWidget):

    background_klass = IsoBackgroundWidget
    feature_klasses = {
        'face': FaceItem,
        'roof': RoofItem,
        'side': SideItem,
        'arch': ArchItem,
        'door': DoorItem,
        #'stairs': StairsItem,
        'stairs': CharFeatureItem,
    }
    svg_feature_klass = SvgFeatureItem

    def offset(self):
        return (
            (self['x'] - self['y']) * float(self.tile_width), 
            ((self['x'] + self['y']) / 2.) * self.tile_width
        )



#################################
### Level
#################################

class LevelWidget(QtGui.QGraphicsWidget):

    menu_names = ['move', 'action', 'info']

    player_moved = QtCore.pyqtSignal(TileWidget)
    request_redraw = QtCore.pyqtSignal()
    iso_tile = IsoTileWidget
    noniso_tile = TileWidget

    faded_opacity = .5
    
    def __init__(self, tile_size):
        super(LevelWidget, self).__init__()

        self._tiles = {}
        self._tile_size = tile_size
        self._beings = {}
        self._opaciter = OpacityAnimation(self)
        self._width, self._height = None, None

        self.setFlags(self.flags() | self.ItemIsFocusable)
        self.setFocusPolicy(QtCore.Qt.TabFocus)

    @property
    def player_tile(self):
        try:
            return [t for t in self._tiles.values() if t.being and t.being['is_player']][-1]
        except IndexError:
            return None

    def centerTile(self):
        return self._tiles[self._width / 2, self._height / 2]

    @property
    def offset(self):
        if self._use_iso:
            return (self.size[0] * self._tile_size) / -2, 0
        else:
            return 0, 0

    def setTiles(self, level, use_iso, use_svg, seethrough, debug, use_char):

        scene = self.scene()
        for tile in self._tiles.values():
            scene.removeItem(tile)
        self._tiles = {}

        klass = self.iso_tile if use_iso else self.noniso_tile
        for tile in level.tiles():
            widget = klass(self._tile_size, use_svg, seethrough, debug, use_char)
            widget.setParentItem(self)
            self._tiles[tile.x, tile.y] = widget

        self.reset(level.tiles())
        # need for tiles to be reset once before we set transitions
        self._setTransitions(level.tiles())

        self._width = max([t['x'] for t in self._tiles.values()]) + 1
        self._height = max([t['y'] for t in self._tiles.values()]) + 1

        self._beings = {}
        for being in [t.being for t in self._tiles.values() if t.being]:
            self._beings[being['guid']] = being

        klass = IsoZapWidget if use_iso else ZapWidget
        self.zap = klass(self, self._tile_size)

    def reset(self, tiles):
        update = [(t, self._tiles[t.x, t.y]) for t in tiles]
        for tile, widget in update:
            widget.reset(tile)
            if widget.being:
                self._beings[widget.being['guid']] = widget.being

    def _setTransitions(self, tiles):

        for (x,y), tile, t in [((t.x, t.y), (self._tiles[t.x, t.y]), t) for t in tiles]:
            #get the corners to this tile
            for xo, yo in [(-1,-1), (1,1), (-1,1), (1,-1)]:
                corner = self._tiles.get((x + xo, y + yo))
                if not corner:
                    continue
                # corner tile will have two other adjacent tiles to our object tile
                #if we zero out one of the coords then we will get the two adjacent tiles
                for i in range(2):
                    idx = (0, yo) if i == 0 else (xo, 0)
                    adjacent = self._tiles[x + idx[0], y + idx[1]]
                    tile.background.setTransition(corner.background, adjacent.background, t)

    def setEnabled(self, enabled):

        #FIXME this takes to long
        #opacity = 1 if enabled else self.faded_opacity
        #self._opaciter.fadeTo(opacity)
        #self.setOpacity(opacity)
        for action in self.actions():
            action.setEnabled(enabled)
        super(LevelWidget, self).setEnabled(enabled)

    def _onTilesChangedState(self, tiles):
        self.reset(tiles)

    def _onTileChanged(self, tile):
        self.reset([tile])

    def _onTileInventoryChanged(self, idx, inventory):
        tile = self._tiles[idx]
        game = self.parentItem()
        tile.inventory.change(inventory, game.use_svg, game.use_iso, game.seethrough)

    def _onBeingMeleed(self, old_idx, new_idx, guid, direction):
        being = self._beings[guid]
        tile = self._tiles[new_idx]
        being.melee(tile, direction)

    def _onBeingKicked(self, old_idx, new_idx, guid, direction):
        pass

    def _onBeingDied(self, tile_idx, guid):
        being = self._beings[guid]
        being.die()
        self._beings.pop(guid)

    def _onBeingMoved(self, old_idx, new_idx, guid, direction):
        being = self._beings[guid]
        new = self._tiles[new_idx]
        old = self._tiles[old_idx]
        being.walk(old, new, self, direction)

        if being['is_player']:
            self.player_moved.emit(new)

    def _onBeingTeleported(self, old_idx, new_idx, guid):
        being = self._beings[guid]
        new = self._tiles[new_idx]
        old = self._tiles[old_idx]
        old.teleport_being_away()
        if being['is_player']:
            self.player_moved.emit(new)

    def _onBeingBecameVisible(self, new_tile):
        self.reset([new_tile])

    def _onUsingUpdated(self, using):
        tile = self.player_tile
        if tile:
            tile.being.updateUsing(using)

    def _onBeingSpellDamage(self, idx, guid, spell):
        tile = self._tiles[idx]
        tile.background.spell.show(spell)

    def _onBeingSpellResistance(self, idx, guid, spell):
        pass

    def _onWandZapped(self, spell, idxs, direction):

        if not spell.color:
            return
        start = self._tiles[idxs[0]]
        end = self._tiles[idxs[-1]]
        self.zap.cast(spell, direction, start.offset(), end.offset())

    def _onTurnStarted(self):
        return

