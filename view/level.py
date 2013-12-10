
from itertools import product
from collections import OrderedDict

from PyQt4 import QtCore, QtGui
from animation import OpacityAnimation
import animation

from tile import TileWidget, IsoTileWidget, TransitionItem, TransitionPoints
from util import Action



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

    def setTiles(self, level, use_iso, use_svg, seethrough, debug):

        scene = self.scene()
        for tile in self._tiles.values():
            scene.removeItem(tile)
        self._tiles = {}

        klass = self.iso_tile if use_iso else self.noniso_tile
        for tile in level.tiles():
            widget = klass(self._tile_size, use_svg, seethrough, debug)
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


