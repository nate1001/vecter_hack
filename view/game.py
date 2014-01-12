import string
from collections import OrderedDict

from PyQt4 import QtCore, QtGui

from level import LevelWidget
from util import Action
from svg import SvgRenderer
from info import LogWidget, InfoWidget, StatsWidget, InputWidget
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
    menu_names = ['view']

    def __init__(self, scene, settings):
        super(LevelView, self).__init__(scene)

        self.settings = settings
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        #self.setRenderHint(QtGui.QPainter.NonCosmeticDefaultPen)
        self.setFrameStyle(QtGui.QFrame.NoFrame)

        self.scaler = ScaleAnimation(self)
        self.scroller = ViewScrollAnimation(self)

        scale = settings['view', 'scale']
        t = QtGui.QTransform.fromScale(scale, scale)
        self.setTransform(t)

        self.horizontalScrollBar().valueChanged.connect(self._onValueChanged)
        self.verticalScrollBar().valueChanged.connect(self._onValueChanged)
        self.viewport_changed.connect(scene.widget._onViewportChanged)
        self.scale_changed.connect(scene.widget._onViewScaleChanged)

        scene.widget.level.player_moved.connect(self.centerPlayer)

        step = 5
        self.addActions([
            Action(self, 'Zoom Out', ['-'], self.scaler.scale, (.8,)),
            Action(self, 'Zoom In', ['+'], self.scaler.scale, (1.25,)),

            Action(self, 'Zoom 1x', ['1'], self.scaler.scaleTo, (1,)),
            Action(self, 'Zoom 2x', ['2'], self.scaler.scaleTo, (2,)),
            Action(self, 'Zoom 3x', ['3'], self.scaler.scaleTo, (3,)),
            Action(self, 'Zoom 4x', ['4'], self.scaler.scaleTo, (4,)),
            Action(self, 'Zoom 1/2x', ['5'], self.scaler.scaleTo, (.5,)),
            Action(self, 'Center on Player', ['6'], self.centerPlayer),

            Action(self, 'Scroll Left', ['Shift+H'], self.scroller.scroll, ('west',)),
            Action(self, 'Scroll Right', ['Shift+L'], self.scroller.scroll, ('east',)),
            Action(self, 'Scroll Up', ['Shift+K'], self.scroller.scroll, ('north',)),
            Action(self, 'Scroll Down', ['Shift+J'], self.scroller.scroll, ('south',)),


            Action(self, 'Toggle Iso', ['F1'], self._onToggleIso),
            Action(self, 'Toggle Svg', ['F2'], scene.widget.toggleSvg),
            Action(self, 'Toggle Seethrough', ['F3'], scene.widget.toggleSeethrough),
            Action(self, 'Toggle Char', ['F4'], scene.widget.toggleChar),

            Action(self, 'Toggle Log', ['F11'], scene.widget.toggleLog),
            Action(self, 'Toggle Stats', ['F10'], scene.widget.toggleStats),

            Action(self, 'Toggle Debug', ['F12'], scene.widget.toggleDebug),
            Action(self, 'Change Focus', ['Tab'], scene.widget.advanceFocus),
        ])

        self.menu = QtGui.QMenu('&View')
        for action in self.actions():
            self.menu.addAction(action)

    def resizeEvent(self, event):
        self.centerPlayer()
        super(LevelView, self).resizeEvent(event)

    def _onFinishedLoading(self):
        def hi():
            s = self.scale
            # create a scaling event so the scene will scale the info screen
            self.setScale(s + .00000000001)
            self.centerPlayer()
        # wait a little more for things to settle down
        timer = QtCore.QTimer.singleShot(500, hi)


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
        self.settings['view', 'scale'] = t.m11()
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

    menu_names = ['game', 'wizard', 'settings']

    turn_started = QtCore.pyqtSignal()
    _settings_group = 'model'

    def __init__(self, game, settings):
        super(GameWidget, self).__init__()

        self.settings = settings
        self.game = game

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

        self._question = InputWidget(self)
        self._question.setZValue(1)
        self._question.finished.connect(self._onAnswerRecieved)
        self._question.canceled.connect(self._onAnswerRecieved)

        self._log = LogWidget()
        self._log.setZValue(1)
        self._log.setParentItem(self)

        self._last_viewport_rect = None
        self._last_viewport_scale = None
        
        for group, commands in game.commands.items():
            for command in commands.values():
                parent = self if group in self.menu_names else self.level
                action = Action(
                    parent, 
                    command.desc, 
                    [command.key], 
                    self._onAction,
                    args=(group, command.name)
                )
                parent.addAction(action)

        for name in self.settings.keys(self._settings_group):
            action = Action(self, name, ['Ctrl+' + name[0]], self._onSettingsChanged, args=('settings', name))
            action.setCheckable(True)
            action.setChecked(settings[self._settings_group, name])
            self.addAction(action)
            self._onSettingsChanged('settings', name)


        game.events['game_started'].connect(self._onGameStarted)
        game.events['game_ended'].connect(self._onGameEnded)
        game.events['level_changed'].connect(self._onLevelChanged)
        game.events['map_changed'].connect(self._onMapChanged)
        game.events['being_moved'].connect(self.level._onBeingMoved)
        game.events['being_meleed'].connect(self.level._onBeingMeleed)
        game.events['being_spell_damage'].connect(self.level._onBeingSpellDamage)
        game.events['being_died'].connect(self.level._onBeingDied)
        game.events['being_became_visible'].connect(self.level._onBeingBecameVisible)
        game.events['tile_inventory_changed'].connect(self.level._onTileInventoryChanged)
        game.events['tiles_changed_state'].connect(self.level._onTilesChangedState)
        game.events['wand_zapped'].connect(self.level._onWandZapped)

        game.events['action_happened_in_game'].connect(self._log.appendDungeonMessage)
        game.events['turn_finished'].connect(self._onTurnFinished)
        game.events['redraw'].connect(self._onRedraw)


    @property
    def player_tile(self): return self.level.player_tile
    @property
    def use_svg(self): return self.settings['view', 'use_svg']
    @property
    def use_iso(self): return self.settings['view', 'use_iso']
    @property
    def use_char(self): return self.settings['view', 'use_char']
    @property
    def seethrough(self): return self.settings['view', 'seethrough']
    @property
    def debug(self): return self.settings['view', 'debug']

    def _onAction(self, kind, name):
        if kind == 'game':
            getattr(self.game, name)()
        else:
            self.turn_started.emit()
            self.game.player.dispatch_command(name)

    def _onGameStarted(self, level):

        player = self.game.player
        game = self.game
        self._info.setPlayer(player)
        self._stats.setPlayer(player)

        player.events['action_happened_to_player'].connect(self._log.appendPlayerMessage)
        player.events['using_updated'].connect(self.level._onUsingUpdated)
        player.events['answer_requested'].connect(self._onAnswerRequested)

        self.turn_started.connect(self.level._onTurnStarted)

        self.level.setEnabled(True)
        self.level.setFocus()
        player.emit_info()
        self._onLevelChanged(level)

    def _onGameEnded(self):
        self.level.setEnabled(False)

    def advanceFocus(self):
        self._info.advanceFocus()

    def toggleSeethrough(self):
        self.settings['view', 'seethrough'] = not self.seethrough
        self._toggle()

    def toggleIso(self):
        self.settings['view', 'use_iso'] = not self.use_iso
        self._toggle()

    def toggleChar(self):
        self.settings['view', 'use_char'] = not self.use_char
        self._toggle()

    def toggleSvg(self):
        self.settings['view', 'use_svg'] = not self.use_svg
        self._toggle()

    def toggleDebug(self):
        self.settings['view', 'debug'] = not self.debug
        self._toggle()

    def toggleLog(self):
        if self._log._on:
            self._log.hide()
            self._log._on = False
        else:
            self._log._on = True
            self._log.show()

    def toggleStats(self):
        if self._stats.isVisible():
            self._stats.hide()
        else:
            self._stats.show()

    def _toggle(self, level=None):
        if not level:
            level = self.game.level
        self.level.setTiles(level, self.use_iso, self.use_svg, self.seethrough, self.debug, self.use_char)

    def _onSettingsChanged(self, _nothing, setting):

        setting = str(setting)
        for action in self.actions():
            if action.name == setting:
                checked = action.isChecked()  
                self.game.set_setting(setting, checked)
                return
        raise ValueError(setting)

    def _onLevelChanged(self, level):
        self._toggle(level)

    def _onAnswerRequested(self, question, callback):
        self._question.ask(question, callback)
        self.level.setEnabled(False)

    def _onAnswerRecieved(self):
        self.level.setEnabled(True)

    def _onTurnFinished(self, number):
        self._log.onTurnFinished(number)
        self._onViewportChanged(self._last_viewport_rect, self._last_viewport_scale)

    def _onRedraw(self, level):
        SvgRenderer.cached.clear()
        self._toggle(level)

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
        if not scale:
            return

        factor = (1 / scale)
        of = 5 * factor

        self._stats.setPos(rect.x() + of, rect.y() + of)
        self._stats.setHtml()

        geom = self._log.geometry()
        size = self._log.sizeHint(QtCore.Qt.PreferredSize)
        self._log.setPos(rect.x() + of, rect.y() + rect.height() - geom.height() * factor - of)

        geom = self._info.geometry()
        self._info.setPos(rect.x() + rect.width() - geom.width() * (1/scale) - of, rect.y() + of)

        self._question.setPos(rect.x() + of, rect.y() + rect.height() / 2)

        self._last_viewport_rect = rect
        self._last_viewport_scale = scale

    def _onInfoResizeEvent(self):
        self._onViewportChanged(self._last_viewport_rect, self._last_viewport_scale)

    def _onViewScaleChanged(self, factor):
        for widget in [self._log, self._info, self._stats, self._question]:
            widget.setScale(1 / factor)



class MainWindow(QtGui.QMainWindow):

    finished_loading = QtCore.pyqtSignal()

    
    def __init__(self, name, game, settings, options):
        super(MainWindow, self).__init__()

        # game
        self.game_widget = GameWidget(game, settings)
        self.settings = settings
        self.options = options
        scene = LevelScene(self.game_widget)
        view = LevelView(scene, settings)
        self.finished_loading.connect(view._onFinishedLoading)

        # set menu bar
        self.bar = self.menuBar()
        self.menus = OrderedDict()
        for name in self.game_widget.menu_names + self.game_widget.level.menu_names + view.menu_names:
            self.menus[name] = QtGui.QMenu('&' + name.capitalize())
            self.bar.addMenu(self.menus[name])

        for action in self.game_widget.actions() + self.game_widget.level.actions():
            group, name = action.args
            self.menus[group].addAction(action)

        group = view.menu_names[0]
        for action in view.actions():
            self.menus[group].addAction(action)

        action = Action(self, 'Quit', ['Ctrl+Q'], self.close)
        self.addAction(action)
        group = self.game_widget.menu_names[0]
        self.menus[group].addAction(action)


        game.new()
        self.setCentralWidget(view)
        self.setWindowTitle(name)

    def event(self, event): 
        # if we have finished loading all the graphics and are ready for input
        if event.type() == QtCore.QEvent.WindowActivate:
            if self.options['quit after startup']:
                self.close()
            self.finished_loading.emit()
        return super(MainWindow, self).event(event)

    def showEvent(self, event):
        geom = self.settings.value('view/geometry').toByteArray()
        self.restoreGeometry(geom)

    def closeEvent(self, event):
        self.settings.setValue('view/geometry', self.saveGeometry())
        super(MainWindow, self).closeEvent(event)
        
