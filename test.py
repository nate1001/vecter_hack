

from PyQt4 import QtCore, QtGui, QtSvg, QtXml

from view.svg import SvgRenderer
from view.util import ResetItem, ResetError
from view.animation import OpacityAnimation
import config


class Menu(QtGui.QMenu):
    
    def __init__(self, name, commands, callback):
        name = '&' + name.capitalize()
        super(Menu, self)__init__(name)

        for keystroke, (name, args) in commands.items():
            action = Action(self, name, [keystroke], callback, args=(name, args))
            self.addAction(action)

        #action.setShortcutContext(QtCore.Qt.WidgetShortcut)

class MenuBar(QtGui.QMenuBar):
    #FIXME put order of menus somewhere closer to register commands
    #menus = [m['game'], m['move'], m['action'], m['info'], view.menu , m['settings'], m['wizard']]
    
    def __init__(self, commands, callback):
        super(MenuBar, self).__init__()

        menus = {}
        for name, value in commands.iteritems():
            menus[name] = Menu(name, value[name], callback)


        '''
        menu = QtGui.QMenu('&Settings')
        self.menus['settings'] = menu
        self.game_widget.menus['game'].addAction(Action(self, 'Quit', ['Ctrl+Q'], self.close))
        for name in settings.keys(self._settings_group):
            action = Action(self, name, ['Ctrl+' + name[0]], self._onSettingsChanged, args=(name,))
            action.setCheckable(True)
            action.setChecked(settings[self._settings_group, name])
            self.addAction(action)
            menu.addAction(action)
            self._onSettingsChanged(name)
        '''
            


if __name__ == '__main__':


    class View(QtGui.QGraphicsView):
        
        toggle = ('sw', 'se', 'ne', 'nw')
        
        def __init__(self, scene):
            super(View, self).__init__(scene)

        def keyPressEvent(self, event):
            
            if event.key() == QtCore.Qt.Key_Escape:
                self.close()
            else:
                event.ignore()
            super(View, self).keyPressEvent(event)



    import sys

    app = QtGui.QApplication(sys.argv)
    scene = QtGui.QGraphicsScene()

    item = InputWidget(None, "how are you?")

    view = View(scene)
    #view = QtGui.QGraphicsView(scene)
    scene.addItem(item)
    view.setGeometry(0, 0, 600, 600)
    view.show()

    sys.exit(app.exec_())

