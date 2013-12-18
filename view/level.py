
from itertools import product
from collections import OrderedDict

from PyQt4 import QtCore, QtGui
from animation import OpacityAnimation
from animation import BeingAnimation, PosAnimation, OpacityAnimation
import animation

from tile import TransitionItem, TransitionPoints
from tile import FloorItem, IsoFloorItem, FloorDebugItem
from tile import IsoPartFaceItem, IsoPartRoofItem, IsoPartSideItem, IsoPartDoorItem

from util import Action, ResetItem, CharItem
from svg import SvgEquipmentItem, SvgSpeciesItem


#################################
### Widget Items
#################################


class BaseItemWidget(QtGui.QGraphicsWidget):
    item_clicked = QtCore.pyqtSignal(QtGui.QGraphicsWidget)

    def __init__(self, parent):
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

        self.animation = BeingAnimation(self)

    def __repr__(self):
        return '<BeingWidget #{}>'.format(self['guid'])

    def reset(self, being):
        super(BeingWidget, self).reset(being)
        self.item.reset(being)
        self.setPos(0,0)


    def die(self):
        self.animation.die()

    def melee(self, tile):
        self.animation.melee(tile)

    def walk(self, old_tile, new_tile, level):
        self.animation.walk(old_tile, new_tile, level)


class BackgroundWidget(BaseItemWidget, ResetItem):
    
    attrs = ('name', 'parts')
    floor_klass = FloorItem

    part_klasses = {
        'wall': None,
        'roof': None,
        'side': None,
        'door': None,
        'stairs': None,
    }

    def __init__(self, parent, tile_width, use_svg, seethrough, debug, use_char):
        super(BackgroundWidget, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        self._use_svg = use_svg
        self._tile_width = tile_width

        self.floor= self.floor_klass(self, tile_width, use_svg, use_char)
        self.debug = FloorDebugItem(self, tile_width) if debug else None
        self.parts = None

    def reset(self, tile):
        super(BackgroundWidget, self).reset(tile)
        
        #if this is our first reset
        if self.parts is None:
            self.parts = []
            for part in self['parts']:
                klass = self.part_klasses[part]
                if klass:
                    self.parts.append(klass(self, self._tile_width, self._use_svg))

        self.floor.reset(tile)
        for part in self.parts:
            part.reset(tile)
        if self.debug:
            self.debug.reset(tile)

    @property
    def idx(self):
        p = self.parentItem()
        return (p['x'], p['y'])

    def setTransition(self, corner, adjacent, tile):
        self.floor.setTransition(corner.floor, adjacent.floor, tile)

class IsoBackgroundWidget(BackgroundWidget):
    floor_klass = IsoFloorItem

    part_klasses = {
        'face': IsoPartFaceItem,
        'roof': IsoPartRoofItem,
        'side': IsoPartSideItem,
        'door': IsoPartDoorItem,
        'stairs': None,
    }




#################################
### Tile Widget
#################################



class TileWidget(QtGui.QGraphicsWidget, ResetItem):
    
    attrs = ('x', 'y')

    tile_clicked = QtCore.pyqtSignal(QtGui.QGraphicsWidget)
    being_moved = QtCore.pyqtSignal(BeingWidget)
    background_klass = BackgroundWidget
    
    def __init__(self, tile_width, use_svg, seethrough, debug, use_char):
        super(TileWidget, self).__init__()
        ResetItem.__init__(self, tile_width)

        self.being = None
        self.background = self.background_klass(self, tile_width, use_svg, seethrough, debug, use_char)
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
            self.scene() and self.scene().removeItem(self.being)
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



#################################
### Level
#################################

class LevelWidget(QtGui.QGraphicsWidget):

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

        self.setFlags(self.flags() | self.ItemIsFocusable)
        self.setFocusPolicy(QtCore.Qt.TabFocus)

    @property
    def player_tile(self):
        try:
            return [t for t in self._tiles.values() if t.being and t.being['is_player']][-1]
        except IndexError:
            return None

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

        self._beings = {}
        for being in [t.being for t in self._tiles.values() if t.being]:
            self._beings[being['guid']] = being


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

        opacity = 1 if enabled else self.faded_opacity
        self._opaciter.fadeTo(opacity)
        super(LevelWidget, self).setEnabled(enabled)

    def _onTilesChangedState(self, tiles):
        self.reset(tiles)

    def _onTileInventoryChanged(self, idx, inventory):
        tile = self._tiles[idx]
        game = self.parentItem()
        tile.inventory.change(inventory, game.use_svg, game.use_iso, game.seethrough)

    def _onBeingMeleed(self, old_idx, new_idx, guid):
        being = self._beings[guid]
        tile = self._tiles[new_idx]
        being.melee(tile)

    def _onBeingDied(self, tile_idx, guid):
        being = self._beings[guid]
        being.die()
        self._beings.pop(guid)

    def _onBeingMoved(self, old_idx, new_idx, guid):
        being = self._beings[guid]
        new = self._tiles[new_idx]
        old = self._tiles[old_idx]
        being.walk(old, new, self)

        if being['is_player']:
            self.player_moved.emit(new)

    def _onBeingBecameVisible(self, new_tile):
        self.reset([new_tile])

    def _onTurnStarted(self):
        return


