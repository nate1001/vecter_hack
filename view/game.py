import string
from collections import OrderedDict

from PyQt4 import QtCore, QtGui

from level import GameWidget, LevelScene, LevelView
from util import Action




class MainWindow(QtGui.QMainWindow):
    
    def __init__(self, game):
        super(MainWindow, self).__init__()

        self.game_widget = GameWidget(game)

        scene = LevelScene(self.game_widget)
        view = LevelView(scene)

        game.new()
        self.setCentralWidget(view)

        self.game_widget.menus['game'].addAction(Action(self, 'Quit', ['Ctrl+Q'], self.close))

        view = QtGui.QMenu('&View')
        for action in view.actions():
            view.addAction(action)

        m = self.game_widget.menus
        #FIXME put order of menus somewhere closer to register commands
        menus = [m['game'], m['move'], m['action'], m['info'], view, m['settings']]
        bar = self.menuBar()
        for menu in menus:
            bar.addMenu(menu)

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

