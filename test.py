

from PyQt4 import QtCore, QtGui, QtSvg, QtXml

from view.svg import SvgRenderer
from view.util import ResetItem, ResetError
from view.animation import OpacityAnimation
import config


class ChibiPartItem(QtSvg.QGraphicsSvgItem):
    
    renderer = SvgRenderer(config.config['media_dir'] + 'chibi.svg')

    def __init__(self, parent, tile_width, name):
        super(ChibiPartItem, self).__init__(parent)
        self.setSharedRenderer(self.renderer)
        self.setElementId(name)


class ChibiDirectionWidget(QtGui.QGraphicsWidget, ResetItem):
    
    attrs = ('melee', 'boot', 'armor')
    dirs = {
        'sw': ('front', False),
        'se': ('front', True),
        'ne': ('back', False),
        'nw': ('back', True),
    }
    parts = {
        'front':(
            'body', 'pants', 'armor',
            'boot',
            'head', 'ear', 'eyes', 'mouth', 'nose', 'hair',
            'hand', 'melee', 'thumb',
        ),
        'back':(
            'body', 'pants', 'armor',
            'boot',
            'ear', 'eyes', 'mouth', 'nose',
            'thumb', 'melee', 'hand',
            'head',  'hair',
        ),
    }
    optional = (
        'melee', 'boot', 'armor'
    )

    def __init__(self, parent, tile_width, direction):
        super(ChibiDirectionWidget, self).__init__(parent)
        ResetItem.__init__(self, tile_width)
        self._direction = direction
        self.animation = OpacityAnimation(self, force=True)

    def reset(self, item):
        super(ChibiDirectionWidget, self).reset(item)

        for child in self.childItems():
            self.scene().removeItem(child)

        side, flip = self.dirs[self._direction]
        for part in self.parts[side]:

            if part in self.optional and not self[part]:
                continue

            name = side + '_' + part
            chibi_item = ChibiPartItem(self, self.tile_width, name)

            #XXX chibis should only use half the regular width
            size = chibi_item.renderer.defaultSize().width() * 2
            scale = float(self.tile_width) / size
            chibi_item.scale(scale, scale)

            if flip:
                chibi_item.scale(-1, 1)
                chibi_item.setPos(self.tile_width/2+size, 0)
            else:
                chibi_item.setPos(self.tile_width/2-size, 0)


class ChibiWidget(QtGui.QGraphicsWidget, ResetItem):

    attrs = ('direction',)

    def __init__(self, parent, tile_width):
        super(ChibiWidget, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        self._current = None
        self.widgets = {}
        for direction in ChibiDirectionWidget.dirs:
            self.widgets[direction] = ChibiDirectionWidget(self, tile_width, direction)

    def reset(self, item):
        super(ChibiWidget, self).reset(item)
        for widget in self.widgets.values():
            widget.reset(item)
            widget.setOpacity(0)
        self.setDirection(self['direction'])

    def setDirection(self, direction):
        
        if self._current:
            self.widgets[self._current].animation.fadeTo(0)
        self.widgets[direction].animation.fadeTo(1) 
        self._current = direction
        

            


if __name__ == '__main__':

    class Chibi(object):
        
        def __init__(self, d, melee, boot, armor):
            self.direction = d
            self.melee = melee
            self.boot = boot
            self.armor = armor


    class View(QtGui.QGraphicsView):
        
        toggle = ('sw', 'se', 'ne', 'nw')
        
        def __init__(self, scene, size):
            super(View, self).__init__(scene)
            self._state_idx = -1
            self.chibi = ChibiWidget(None, size)
            item = Chibi('sw', '', 'boot', 'armor')
            self.chibi.reset(item)
            scene.addItem(self.chibi)

            self.advance_state()

        def keyPressEvent(self, event):
            
            if event.key() == QtCore.Qt.Key_Escape:
                self.close()
            elif event.key() == QtCore.Qt.Key_Space:
                self.advance_state()
            else:
                event.ignore()

        def advance_state(self):
            
            if self._state_idx == len(self.toggle) - 1:
                self._state_idx = 0
            else:
                self._state_idx += 1
            direction = self.toggle[self._state_idx]
            self.chibi.setDirection(direction)


    import sys

    app = QtGui.QApplication(sys.argv)
    scene = QtGui.QGraphicsScene()

    view = View(scene, 512)
    rect = QtGui.QGraphicsRectItem(0, 0, 512, 512)
    scene.addItem(rect)
    view.setGeometry(0, 0, 600, 600)
    view.show()

    sys.exit(app.exec_())

