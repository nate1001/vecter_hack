
from PyQt4 import QtCore, QtGui, QtSvg, QtXml

from util import ResetItem, ResetError
import config


class SvgRenderer(QtSvg.QSvgRenderer):
    
    cached = {}

    @classmethod
    def get(cls, category):
        
        category = category.replace(' ', '_')
        renderer = cls.cached.get(category)
        if not renderer:
            fname = config.config['media_dir'] + category + '.svg'
            renderer = cls(fname)
            if not renderer.isValid():
                raise ResetError('could not load renderer {}'.format(repr(fname)))
            cls.cached[category] = renderer
        return renderer
    
    def __init__(self, name):
        super(SvgRenderer, self).__init__(name)



#################################
### Svg Items
#################################


class SvgItem(QtSvg.QGraphicsSvgItem, ResetItem):
    
    renderers = {}
    attrs = ('category', 'name')

    def __init__(self, parent, tile_width):
        super(SvgItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)

        self._factor = None
        self._size = None

    def name(self):
        return self['name'].replace(' ', '_')

    def offset(self):

        renderer = self.renderer()
        rect = renderer.boundsOnElement(self.name())
        xo, yo = self.parentItem().offset()
        #FIXME this will break on non-iso
        if rect.height() * self._factor > self.tile_width / 2.:
            yo += self.tile_width - rect.height() * self._factor
        return xo, yo

    def centerItem(self):

        renderer = self.renderer()
        rect = renderer.boundsOnElement(self.name())
        xo, yo = self.parentItem().center()
        w, h = rect.width(), rect.height()
        xo = xo - w * self._factor * .5
        yo = yo - (h * self._factor)
        return xo, yo


    def reset(self, item):
        super(SvgItem, self).reset(item)

        renderer = SvgRenderer.get(self['category'])
        name = self.name()
        self.setSharedRenderer(renderer)

        if not renderer.elementExists(name):
            raise ResetError('could not render {}'.format(repr(name)))

        self.setElementId(name)
        self.setScale()
        self._setPos()

        return True

    def setScale(self):

        renderer = self.renderer()
        self._size = renderer.defaultSize()
        #XXX why does this work for height? (should it not be width?)
        self._factor = float(self.tile_width) / self._size.height() 
        super(SvgItem, self).setScale(self._factor)

    def _setPos(self):

        renderer = self.renderer()
        rect = renderer.boundsOnElement(self.name())
        x, y = self.offset()
        self.setPos(x, y)


class SvgSpeciesItem(SvgItem):

    def __init__(self, parent, tile_width, direction):
        self._direction = direction
        super(SvgSpeciesItem, self).__init__(parent, tile_width)

    def name(self):
        return self['name'].replace(' ', '_') + '_' + self._direction

    def offset(self):
        return self.centerItem()


class SvgFeatureItem(SvgItem):

    def __init__(self, parent, tile_width):
        self._feature = None
        self._real_name = None
        super(SvgFeatureItem, self).__init__(parent, tile_width)

    def reset(self, tile, real_name, feature):
        self._feature = feature
        self._real_name = real_name.replace(' ', '_')
        super(SvgFeatureItem, self).reset(tile)

    def name(self):
        return '{}_{}'.format(self._real_name, self._feature)


class SvgEquipmentItem(SvgItem):

    def offset(self):
        return self.centerItem()

class SvgIsoFloorItem(SvgItem):
    attrs = ('category', 'kind')
    def name(self):
        return self['kind']

class SvgTransitionItem(SvgItem):
    pass

class ChibiPartItem(QtSvg.QGraphicsSvgItem):
    
    renderer = SvgRenderer(config.config['media_dir'] + 'chibi.svg')
    def __init__(self, parent, tile_width, name):
        super(ChibiPartItem, self).__init__(parent)
        self.setSharedRenderer(self.renderer)
        self.setElementId(name)


class ChibiDirectionWidget(QtGui.QGraphicsWidget, ResetItem):
    
    attrs = ('melee', 'boot', 'armor')
    dirs = {
        'sw': ('front', True),
        'se': ('front', False),
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
        #self.animation = OpacityAnimation(self, force=True)

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

            yo = -self.tile_width/4
            if flip:
                chibi_item.scale(-1, 1)
                #chibi_item.setPos(self.tile_width/2+size, 0)
                chibi_item.setPos(0,yo)
            else:
                #chibi_item.setPos(self.tile_width/2-size, 0)
                chibi_item.setPos(0,yo)


