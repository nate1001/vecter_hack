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

    def removeItem(self, item):
        super(LevelScene, self).removeItem(item)

class ScalingView(QtGui.QGraphicsView):

    scale_changed  = QtCore.pyqtSignal(float)
    viewport_changed  = QtCore.pyqtSignal(QtCore.QRectF, float)

    def __init__(self, scene):
        super(ScalingView, self).__init__(scene)

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.scaler = ScaleAnimation(self)
        self.scroller = ViewScrollAnimation(self)

        self.viewport_changed.connect(scene.widget._onViewportChanged)
        self.scale_changed.connect(scene.widget._onViewScaleChanged)
        self.horizontalScrollBar().valueChanged.connect(self._onValueChanged)
        self.verticalScrollBar().valueChanged.connect(self._onValueChanged)

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



class LevelView(ScalingView):
    
    menu_names = ['view']

    def __init__(self, scene, settings):
        super(LevelView, self).__init__(scene)

        self.settings = settings
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        #self.setRenderHint(QtGui.QPainter.NonCosmeticDefaultPen)
        self.setFrameStyle(QtGui.QFrame.NoFrame)

        scene.widget.game_widget.level.player_moved.connect(self.centerPlayer)

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
            Action(self, 'Toggle Svg', ['F2'], self._onToggleSvg),
            Action(self, 'Toggle Seethrough', ['F3'], self._onToggleSeethrough),
            Action(self, 'Toggle Char', ['F4'], self._onToggleChar),
            Action(self, 'Toggle Debug', ['F12'], self._onToggleDebug),

            Action(self, 'Toggle Map', ['Space'], scene.widget.toggleMap),
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
        self.scene().widget.active.toggleIso()
        self.centerOn(self.scene().widget.active.level.player_tile)

    def _onToggleSvg(self):
        self.scene().widget.active.toggleSvg()

    def _onToggleSeethrough(self):
        self.scene().widget.active.toggleSeethrough()

    def _onToggleChar(self):
        self.scene().widget.active.toggleChar()

    def _onToggleDebug(self):
        self.scene().widget.active.toggleDebug()

    def centerPlayer(self, tile=None):
        scene = self.scene()
        if not scene:
            return
        if scene.widget.game_widget is not scene.widget.active:
            return
        if not tile:
            tile = scene.widget.game_widget.player_tile
        if not tile:
            return
        pos = tile.pos()
        self.scroller.position(pos)


class ScalingWidget(QtGui.QGraphicsWidget):
    positions = ['top_left', 'top_right', 'bottom_left', 'bottom_right', 'middle_left']
    def __init__(self):
        super(ScalingWidget, self).__init__()

        self._last_viewport_rect = None
        self._last_viewport_scale = None
        self.widgets = {}

    def setWidget(self, position, widget):
        if position not in self.positions:
            raise ValueError(position)
        self.widgets[position] = widget
        widget.setParentItem(self)
        widget.setZValue(1)

    def _onViewportChanged(self, rect, scale):
        if not scale:
            return

        factor = (1 / scale)
        of = 5 * factor

        tl = self.widgets.get('top_left')
        if tl:
            tl.setPos(rect.x() + of, rect.y() + of)
        

        bl = self.widgets.get('bottom_left')
        if bl:
            geom = bl.geometry()
            size = bl.sizeHint(QtCore.Qt.PreferredSize)
            bl.setPos(rect.x() + of, rect.y() + rect.height() - geom.height() * factor - of)

        tr =  self.widgets.get('top_right')
        if tr:
            geom = tr.geometry()
            tr.setPos(rect.x() + rect.width() - geom.width() * (1/scale) - of, rect.y() + of)

        ml = self.widgets.get('middle_right')
        if ml:
            ml.setPos(rect.x() + of, rect.y() + rect.height() / 2)

        br = self.widgets.get('bottom_right')
        if br:
            geom = br.geometry()
            size = br.sizeHint(QtCore.Qt.PreferredSize)
            br.setPos(
                rect.x() + rect.width() - geom.width() * (1/scale) - of, 
                rect.y() + rect.height() - geom.height() * factor - of)

        self._last_viewport_rect = rect
        self._last_viewport_scale = scale

    def _onViewScaleChanged(self, factor):
        for widget in self.widgets.values():
            widget.setScale(1 / factor)


class GameWidget(QtGui.QGraphicsWidget):

    turn_started = QtCore.pyqtSignal()
    menu_names = ['game', 'wizard', 'settings']

    def __init__(self, game, settings):

        super(GameWidget, self).__init__()

        self.game = game
        self.level = LevelWidget(config.config['tile_size'])
        self.level.setParentItem(self)
        self.settings = settings

        self.turn_started.connect(self.level._onTurnStarted)

        game.events['game_started'].connect(self._onGameStarted)
        game.events['game_ended'].connect(self._onGameEnded)
        game.events['level_changed'].connect(self._onLevelChanged)
        game.events['map_changed'].connect(self._onMapChanged)

        game.events['being_moved'].connect(self.level._onBeingMoved)
        game.events['being_teleported'].connect(self.level._onBeingTeleported)
        game.events['being_meleed'].connect(self.level._onBeingMeleed)
        game.events['being_kicked'].connect(self.level._onBeingKicked)
        game.events['being_spell_damage'].connect(self.level._onBeingSpellDamage)
        game.events['being_spell_resistance'].connect(self.level._onBeingSpellResistance)
        game.events['being_died'].connect(self.level._onBeingDied)
        game.events['being_became_visible'].connect(self.level._onBeingBecameVisible)

        game.events['tile_inventory_changed'].connect(self.level._onTileInventoryChanged)
        game.events['tiles_changed_state'].connect(self.level._onTilesChangedState)
        game.events['tile_changed'].connect(self.level._onTileChanged)

        game.events['wand_zapped'].connect(self.level._onWandZapped)

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
        self.level.setEnabled(True)
        self._onLevelChanged(level)

    def _onGameEnded(self):
        self.level.setEnabled(False)

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


    def _onLevelChanged(self, level):
        self._toggle(level)

    def _onRedraw(self, level):
        SvgRenderer.cached.clear()
        self._toggle(level)

    def _onMapChanged(self, level):
        self.level.reset(level.tiles())

    def _toggle(self, level=None):
        if not level:
            level = self.game.level
        self.level.setTiles(level, self.use_iso, self.use_svg, self.seethrough, self.debug, self.use_char)


class ViewWidget(ScalingWidget):

    _settings_group = 'model'

    def __init__(self, game, settings, map_settings):
        super(ViewWidget, self).__init__()

        self.game = game

        self.map_widget = GameWidget(game, map_settings)
        self.map_widget.setParentItem(self)
        self.map_widget.hide()

        self.game_widget = GameWidget(game, settings)
        self.game_widget.setParentItem(self)
        self.active = self.game_widget
        self.levels = [self.game_widget.level, self.map_widget.level]

        self._info = InfoWidget()
        self.setWidget('top_right', self._info)
        self._info.resize_event.connect(self._onInfoResizeEvent)
        self._info.gained_focus.connect(self._onWidgetGainedFocus)
        self._info.lost_focus.connect(self._onWidgetLostFocus)

        self._question = InputWidget(self)
        self.setWidget('middle_left', self._question)
        self._question.finished.connect(self._onAnswerRecieved)
        self._question.canceled.connect(self._onAnswerRecieved)

        self._stats = StatsWidget()
        self.setWidget('bottom_left', self._stats)

        self._log = LogWidget()
        self.setWidget('top_left', self._log)
        game.events['action_happened_in_game'].connect(self._log.appendDungeonMessage)

        game.events['game_started'].connect(self._onGameStarted)
        game.events['turn_finished'].connect(self._onTurnFinished)

        for group, commands in game.commands.items():
            for command in commands.values():
                parent = self if group in self.game_widget.menu_names else self.game_widget.level
                action = Action(
                    parent, 
                    command.desc, 
                    [command.key], 
                    self.game_widget._onAction,
                    args=(group, command.name)
                )
                parent.addAction(action)

        for name in self.game_widget.settings.keys(self._settings_group):
            action = Action(self, name, ['Ctrl+' + name[0]], self._onSettingsChanged, args=('settings', name))
            action.setCheckable(True)
            action.setChecked(settings[self._settings_group, name])
            self.addAction(action)
            self._onSettingsChanged('settings', name)


    def toggleMap(self):
        view = self.map_widget.scene().views()[0]
        if self.active is self.game_widget:
            self.game_widget.hide()
            self.map_widget.show()
            self._last_scale = view.scale

            view.setScale(1)
            view.centerOn(self.map_widget.level.centerTile())
            self.active = self.map_widget

        else:
            self.game_widget.show()
            self.map_widget.hide()
            view.setScale(self._last_scale)
            view.centerOn(self.game_widget.level.player_tile)
            self.active = self.game_widget

    def advanceFocus(self):
        self._info.advanceFocus()

    def _onGameStarted(self, level):
        player = self.game.player
        self._info.setPlayer(player)
        self._stats.setPlayer(player)
        player.events['action_happened_to_player'].connect(self._log.appendPlayerMessage)
        player.events['using_updated'].connect(self.game_widget.level._onUsingUpdated)
        player.events['answer_requested'].connect(self._onAnswerRequested)
        self.game.player.emit_info()

    def _onInfoResizeEvent(self):
        self._onViewportChanged(self._last_viewport_rect, self._last_viewport_scale)

    def _onWidgetGainedFocus(self, widget):
        for level in self.levels:
            if widget.selectable:
                level.setEnabled(False)
            else:
                level.setEnabled(True)

    def _onWidgetLostFocus(self, widget):
        for level in self.levels:
            if widget.selectable:
                level.setEnabled(True)
                level.setFocus()

    def _onAnswerRequested(self, question, callback):
        self._question.ask(question, callback)
        for level in self.levels:
            level.setEnabled(False)

    def _onAnswerRecieved(self):
        for level in self.levels:
            level.setEnabled(True)

    def _onFinishedLoading(self):
        self.active.level.setFocus()

    def _onTurnFinished(self, number):
        self._log.onTurnFinished(number)

    def _onSettingsChanged(self, _nothing, setting):

        setting = str(setting)
        for action in self.actions():
            if action.name == setting:
                checked = action.isChecked()  
                self.game.set_setting(setting, checked)
                return
        raise ValueError(setting)






class MainWindow(QtGui.QMainWindow):

    finished_loading = QtCore.pyqtSignal()
    
    def __init__(self, name, game, settings, map_settings, options):
        super(MainWindow, self).__init__()

        self.setWindowTitle(name)
        # game
        self.view_widget = ViewWidget(game, settings, map_settings)
        self.settings = settings
        self.options = options
        scene = LevelScene(self.view_widget)
        view = LevelView(scene, settings)
        view.scale_changed.connect(self._onLevelViewScaleChanged)
        scale = settings['view', 'scale']
        t = QtGui.QTransform.fromScale(scale, scale)
        view.setTransform(t)

        self.finished_loading.connect(view._onFinishedLoading)
        self.finished_loading.connect(self.view_widget._onFinishedLoading)

        game_widget = self.view_widget.game_widget
        # set menu bar
        self.bar = self.menuBar()
        self.menus = OrderedDict()
        for name in game_widget.menu_names + game_widget.level.menu_names + view.menu_names:
            self.menus[name] = QtGui.QMenu('&' + name.capitalize())
            self.bar.addMenu(self.menus[name])

        for action in game_widget.actions() + game_widget.level.actions():
            group, name = action.args
            self.menus[group].addAction(action)

        group = view.menu_names[0]
        for action in view.actions():
            self.menus[group].addAction(action)

        action = Action(self, 'Quit', ['Ctrl+Q'], self.close)
        self.addAction(action)
        group = game_widget.menu_names[0]
        self.menus[group].addAction(action)

        game.new()
        self.setCentralWidget(view)

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

    def _onLevelViewScaleChanged(self, new):
        self.settings['view', 'scale'] = new
        
