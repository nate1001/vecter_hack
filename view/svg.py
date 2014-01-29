
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



#QtGui.QPixmapCache.setCacheLimit(10240*100)

#################################
### Svg Items
#################################


class SvgItem(QtSvg.QGraphicsSvgItem, ResetItem):
    
    renderers = {}
    attrs = ('category', 'name')

    @classmethod
    def centerItem(cls, item):

        renderer = item.renderer()
        rect = renderer.boundsOnElement(item.name())
        xo, yo = item.parentItem().center()
        w, h = rect.width(), rect.height()
        xo = xo - w * item._factor * .5
        yo = yo - (h * item._factor)
        return xo, yo

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

    def reset(self, item):
        super(SvgItem, self).reset(item)

        renderer = SvgRenderer.get(self['category'])
        name = self.name()
        self.setSharedRenderer(renderer)

        if not renderer.elementExists(name):
            raise ResetError('could not render {} from {}'.format(repr(name), repr(self['category'])))

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
        return self.centerItem(self)


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
        return self.centerItem(self)

class SvgIsoFloorItem(SvgItem):
    attrs = ('category', 'kind')
    def name(self):
        return self['kind'].replace(' ', '_')

class SvgTransitionItem(SvgItem):
    pass

class SvgSpellItem(SvgItem):
    pass


class ChibiPartItem(SvgItem):
    def __init__(self, parent, tile_width, side, name):
        
        super(ChibiPartItem, self).__init__(parent, tile_width)
        self._side = side
        self._name = name

    def name(self):
        return '{}_{}'.format(self._side, self._name)
    

class ChibiDirectionWidget(QtGui.QGraphicsWidget, ResetItem):
    
    attrs = ('using',)
    dirs = {
        'nw': ('back', False),
        'ne': ('back', True),
        'se': ('front', False),
        'sw': ('front', True),
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

        self.items = {}
        side, flip = self.dirs[self._direction]
        for part in self.parts[side]:
            item = ChibiPartItem(self, tile_width, side, part)
            self.items[part] = item

    def reset(self, being):
        super(ChibiDirectionWidget, self).reset(being)

        side, flip = self.dirs[self._direction]
        for part, item in self.items.items():
            item.reset(being)

            #FIXME figure better offset
            o = 10
            #size = item.renderer().defaultSize().width() * 2
            size = 0
            if part in self.optional:
                item.hide()
            if flip:
                item.scale(-1, 1)
                item.translate(-self.tile_width - o, -self.tile_width/4)
            else:
                item.translate(self.tile_width/2 + o, -self.tile_width/4)

    def setUsing(self, using):
        for key, item in using.items():
            name = item.name.replace(' ', '_')
            if key in self.optional and name:
                self.items[key].show()
            elif key in self.optional:
                self.items[key].hide()
            else:
                pass

    def center(self):
        return self.parentItem().center()
    
    def offset(self):
        return self.parentItem().offset()

