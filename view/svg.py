
from PyQt4 import QtCore, QtGui, QtSvg, QtXml

from util import ResetItem, ResetError
import config




#archaic ... maybe should remove?
class InkscapeHandler(QtXml.QXmlContentHandler):
    
    def __init__(self):
        super(InkscapeHandler, self).__init__()
        
        self.props = {}

    def setDocumentLocator(self, l): pass
    def errorString(self): return 'Error'
    def processingInstruction(self, t, d): return True
    def startPrefixMapping(self, p, uri): return True
    def endPrefixMapping(self, *args): return True
    def endDocument(self, *args): return True
    def endElement(self, namespace, lname, qname): return True
    def characters(self, ch): return True


    def startDocument(self):
        self.props.clear()
        return True

    def startElement(self, namespace, lname, qname, attrs):

        key, value = None, None
        for i in range(attrs.count()):
            name = attrs.qName(i)
            if str(name) == 'id':
                key = str(attrs.value(i))
            if str(name) == 'inkscape:label':
                value = (str(attrs.value(i)))

        if key and value:
            self.props[key]= self._parse_label(value)
        return True

    def _parse_label(self, label):
        d = {'offset':None}
        for attr in label.split(';'):  
            if attr.find(':') > -1:
                try:
                    key, value = attr.split(':')
                    key, value = key.strip(), value.strip()
                    if key in d.keys():
                        value = getattr(self, '_handle_' + key)(value)
                        d[key]= value
                except ValueError:
                    pass
        return d
            

    def _handle_offset(self, offset):
        x, y = offset.split(',')
        x = float(x.strip())
        # inkscape puts view box in 1st quad
        # while qt works in 4th
        y = float(y.strip()) * -1
        return x, y


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
        handler = InkscapeHandler()
        reader = QtXml.QXmlSimpleReader()
        reader.setContentHandler(handler)
        f = QtCore.QFile(name)
        s = QtXml.QXmlInputSource(f)
        reader.parse(s)
        self._props = handler.props.copy()
    
    def getOffset(self, id):
        return self._props[id]['offset']




#################################
### Svg Items
#################################


class SvgItem(QtSvg.QGraphicsSvgItem, ResetItem):
    
    renderers = {}
    attrs = ('category', 'name')

    def __init__(self, parent, tile_width):
        super(SvgItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)
        self._svg_size = None
        self._allow_fallback = False
        self._offset = None

    @property
    def name(self):
        return self['name'].replace(' ', '_')

    def reset(self, item):
        super(SvgItem, self).reset(item)

        renderer = SvgRenderer.get(self['category'])
        self.setSharedRenderer(renderer)

        #FIXME
        #if not renderer.elementExists(name):
        #    #if not self._allow_fallback:
        #    raise ResetError('could not render {}'.format(repr(name)))
        self.setElementId(self.name)

        rect = renderer.boundsOnElement(self.name)
        xo, yo = - (round(rect.width()) % 128), - (round(rect.height()) % 64)
        self._offset = xo, yo
        self._svg_size = renderer.defaultSize()
        self._setPos()

        return True

    def _setPos(self):

        s = self._svg_size
        scale = float(self.tile_width) / max(s.width(), s.height())
        self.setScale(scale)
        x,y  = self.parentItem().center()
        h,w = s.height() * scale, s.width() * scale
        self.setPos(x-w/2,y-h/2)


class SvgIsoFloorItem(SvgItem):

    def _setPos(self):

        size = self._svg_size
        scale = float(self.tile_width) / min(size.width(), size.height()) 
        self.setScale(scale)
        offset_scale = self._svg_size.width()

        if self._offset:
            xo, yo = self._offset
        origin = offset_scale / 2, 0
        x  = (xo - origin[0]) * scale
        y  = (yo - origin[1]) * scale
        self.setPos(x,y)

    def reset(self, item):
        try:
            super(SvgIsoFloorItem, self).reset(item)
        except ResetError:
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


class SvgTransitionItem(SvgItem):

    def _setPos(self):
        size = self._svg_size
        scale = float(self.tile_width) / min(size.width(), size.height()) 
        self.setScale(scale)
        name = self['name'].replace(' ', '_')
        category = self['category'].replace(' ', '_')
        offset_scale = self._svg_size.width()

        try:
            xo, yo = SvgRenderer.cached[category].getOffset(name)
        except TypeError:
            xo, yo = 0, offset_scale / -16 # -8

        # FIXME I cannot see why should not be zero?!
        origin = offset_scale / 2, offset_scale / -16 # 64, -8

        x  = (xo - origin[0]) * scale
        y  = (yo - origin[1]) * scale
        self.setPos(x,y)



class SvgSpeciesItem(SvgItem):

    def __init__(self, parent, tile_width, direction):
        self._direction = direction
        super(SvgSpeciesItem, self).__init__(parent, tile_width)

    @property
    def name(self):
        return self['name'].replace(' ', '_') + '_' + self._direction


class SvgEquipmentItem(SvgItem):
    pass

