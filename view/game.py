import string
from collections import OrderedDict

from PyQt4 import QtCore, QtGui

from level import LevelWidget
from util import Action
from info import LogWidget, InfoWidget, StatsWidget
from animation import ScaleAnimation, ViewScrollAnimation
import config


class LevelScene(QtGui.QGraphicsScene):
    
    def __init__(self, game_widget):
        
        super(LevelScene, self).__init__()

        self.widget = game_widget
        self.addItem(self.widget)
        background_color = QtGui.QColor(config.config['background'])
        self.setBackgroundBrush(QtGui.QBrush(background_color))

class LevelView(QtGui.QGraphicsView):
    
    viewport_changed  = QtCore.pyqtSignal(QtCore.QRectF, float)
    scale_changed  = QtCore.pyqtSignal(float)

    def __init__(self, scene):
        super(LevelView, self).__init__(scene)

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        #self.setRenderHint(QtGui.QPainter.NonCosmeticDefaultPen)
        self.setFrameStyle(QtGui.QFrame.NoFrame)

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

        self.menu = QtGui.QMenu('&View')
        for action in self.actions():
            self.menu.addAction(action)

    def resizeEvent(self, event):
        self.centerPlayer()
        super(LevelView, self).resizeEvent(event)

    def showEvent(self, event):
        self.centerPlayer()
        super(LevelView, self).showEvent(event)

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



class GameWidget(QtGui.QGraphicsWidget):

    turn_started = QtCore.pyqtSignal()

    def __init__(self, game, settings):
        super(GameWidget, self).__init__()

        self.game = game

        game.events['game_started'].connect(self._onGameStarted)
        game.events['game_ended'].connect(self._onGameEnded)

        self.settings = settings

        self.level = LevelWidget(config.config['tile_size'])
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

        settings.beginGroup('game')
        for name in [str(name) for name in settings.childKeys()]:
            action = Action(self, name, ['Ctrl+' + name[0]], self._onSettingsChanged, args=(name,))
            action.setCheckable(True)
            action.setChecked(game.settings[name])
            self.addAction(action)
            menu.addAction(action)
        settings.endGroup()


    @property
    def player_tile(self): return self.level.player_tile
    @property
    def use_svg(self): 
        return True#; return self.settings['view/use_svg']
    @property
    def use_iso(self): return self.settings['view/use_iso']
    @property
    def seethrough(self): return self.settings['view/seethrough']
    @property
    def debug(self): return self.settings['view/debug']

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
        game.events['being_became_visible'].connect(self.level._onBeingBecameVisible)
        game.events['tile_inventory_changed'].connect(self.level._onTileInventoryChanged)
        game.events['tiles_changed_state'].connect(self.level._onTilesChangedState)

        game.events['action_happened_in_dungeon'].connect(self._log.appendDungeonMessage)
        game.events['turn_finished'].connect(self._log.onTurnFinished)
        player.events['action_happened_to_player'].connect(self._log.appendPlayerMessage)

        self.level.request_redraw.connect(game.redraw_level)
        self.turn_started.connect(self.level._onTurnStarted)

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
            self.turn_started.emit()
            self.game.player.dispatch_command(name)

    def advanceFocus(self):
        self._info.advanceFocus()


    def _toggle(self):
        level = self.game.level_view
        self.level.setTiles(level, self.use_iso, self.use_svg, self.seethrough, self.debug)

    def toggleSeethrough(self):
        self.settings['view/seethrough'] = not self.settings['view/seethrough']
        self._toggle()

    def toggleIso(self):
        self.settings['view/use_iso'] = not self.settings['view/use_iso']
        self._toggle()

    def toggleSvg(self):
        self.settings['view/use_svg'] = not self.settings['view/use_svg']
        self._toggle()

    def toggleDebug(self):
        self.debug = not self.debug
        self._toggle()

    def _onLevelChanged(self, level):

        #FIXME make new level
        self._toggle()
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






class MainWindow(QtGui.QMainWindow):
    
    def __init__(self, game, settings):
        super(MainWindow, self).__init__()

        self.game_widget = GameWidget(game, settings)
        self.settings = settings

        scene = LevelScene(self.game_widget)
        view = LevelView(scene)

        game.new()
        self.setCentralWidget(view)

        self.game_widget.menus['game'].addAction(Action(self, 'Quit', ['Ctrl+Q'], self.close))


        m = self.game_widget.menus
        #FIXME put order of menus somewhere closer to register commands
        menus = [m['game'], m['move'], m['action'], m['info'], view.menu , m['settings']]
        bar = self.menuBar()
        for menu in menus:
            bar.addMenu(menu)

    def showEvent(self, event):
        geom = self.settings.value('view/geometry').toByteArray()
        self.restoreGeometry(geom)

    def closeEvent(self, event):
        self.settings.setValue('view/geometry', self.saveGeometry())
        super(MainWindow, self).closeEvent(event)
        
    def _onAction(self, kind, name):
        if kind == 'game':
            getattr(self.game, name)()
        else:
            self.game.player.dispatch_command(name)

    def _onSettingsChanged(self, setting):
        for l in self.actions.values():
            for action in l:
                if action.name == str(setting):
                   self.game.set_setting(setting,action.isChecked())
                   return
        raise ValueError(setting)
