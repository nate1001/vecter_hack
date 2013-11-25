
from collections import OrderedDict

from PyQt4 import QtCore, QtGui
from animation import OpacityAnimation, ScaleAnimation, ViewScrollAnimation

from tile import TileWidget, IsoTileWidget
from info import LogWidget, InfoWidget, StatsWidget
from util import Action


#################################
### Level
#################################

class LevelWidget(QtGui.QGraphicsWidget):

    player_moved = QtCore.pyqtSignal(TileWidget)
    iso_tile = IsoTileWidget
    noniso_tile = TileWidget
    
    def __init__(self, tile_size):
        super(LevelWidget, self).__init__()

        self._tiles = {}
        self._tile_size = tile_size
        self._movement_waiting = {}
        self._opaciter = OpacityAnimation(self)

        self.setFlags(self.flags() | self.ItemIsFocusable)
        self.setFocusPolicy(QtCore.Qt.TabFocus)

    def setTiles(self, tiles, use_iso, use_svg, seethrough, debug):

        scene = self.scene()
        for tile in self._tiles.values():
            scene.removeItem(tile)
        self._tiles = {}

        klass = self.iso_tile if use_iso else self.noniso_tile
        for tile in tiles:
            widget = klass(self._tile_size, use_svg, seethrough, debug)
            widget.being_moved.connect(self._check_waiting)
            widget.setParentItem(self)
            widget.tile_clicked.connect(self._onTileClicked)
            self._tiles[tile.x, tile.y] = widget
        self.reset(tiles)

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

    def setEnabled(self, enabled):

        opacity = 1 if enabled else .5
        self._opaciter.fadeTo(opacity)
        #self.setOpacity(opacity)
        super(LevelWidget, self).setEnabled(enabled)

    def reset(self, tiles):
        update = [(t, self._tiles[t.x, t.y]) for t in tiles]
        for tile, widget in update:
            widget.reset(tile)

    def _onTileInventoryChanged(self, idx, inventory):
        tile = self._tiles[idx]
        game = self.parentItem()
        tile.inventory.change(inventory, game.use_svg, game.use_iso, game.seethrough)

    def _onTilesChangedState(self, tiles):

        game = self.parentItem()
        update = [(t, self._tiles[t.x, t.y]) for t in tiles]
        for tile, widget in update:
            widget.reset(tile)

    def _onBeingMeleed(self, old_idx, new_idx):
        being = self._tiles[old_idx].being
        tile = self._tiles[new_idx]
        if being is None:
            print 88, tile
            return
        being.melee.melee(tile)
            

    def _onBeingDied(self, tile_idx):
        tile = self._tiles[tile_idx]
        if tile.being is None:
            print 99, tile
            return
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
            if being['is_player']:
                self.player_moved.emit(new)


    def _check_waiting(self, being):

        # if another being is still in animation it will be 
        # temporarily reparented to this widget
        # so it can not be the right movement we want
        parent = being.parentItem().parentItem()
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

        self.level = LevelWidget(self.tile_size)
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
            self.addAction(action)
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
        game.events['tiles_changed_state'].connect(self.level._onTilesChangedState)

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
        for action in self.actions():
            if action.name == str(setting):
               self.game.set_setting(str(setting), action.isChecked())
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

    def _toggle(self):
        tiles = self.game.level_view.tiles()
        self.level.setTiles(tiles, self.use_iso, self.use_svg, self.seethrough, self.debug)

    def toggleSeethrough(self):
        self.seethrough = not self.seethrough
        self._toggle()

    def toggleIso(self):
        self.use_iso = not self.use_iso
        self._toggle()

    def toggleSvg(self):
        self.use_svg = not self.use_svg
        self._toggle()

    def toggleDebug(self):
        self.debug = not self.debug
        self._toggle()


    def _onLevelChanged(self, level):

        self.level.setTiles(level.tiles(), self.use_iso, self.use_svg, self.seethrough, self.debug)
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

    def _onViewportChanged(self, rect, scale):
        if rect is None:
            return

        of = 5

        self._stats.setPos(rect.x() + of, rect.y() + of)
        self._stats.setHtml()

        geom = self._stats.geometry()
        #size = self._log.sizeHint(QtCore.Qt.PreferredSize)
        self._log.setPos(rect.x() + geom.width() + of*2 , rect.y() + of)

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





