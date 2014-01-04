
from PyQt4 import QtCore, QtGui, QtSvg, QtXml

from util import ResetItem, ResetError
import config

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
    attrs = ('category', 'name', 'svg_extension')

    def __init__(self, parent, tile_width):
        super(SvgItem, self).__init__(parent)
        ResetItem.__init__(self, tile_width)
        self._svg_size = None
        self._allow_fallback = False
        self._offset = None

    def reset(self, item):
        super(SvgItem, self).reset(item)

        name = self['name'].replace(' ', '_') + self['svg_extension']
        category = self['category'].replace(' ', '_')

        renderer = self.renderers.get(category)
        if not renderer:
            fname = config.config['media_dir'] + category + '.svg'
            renderer = SvgRenderer(fname)
            if not renderer.isValid():
                raise ResetError('could not load renderer {}'.format(repr(fname)))
            self.renderers[category] = renderer
        self.setSharedRenderer(renderer)

        if not renderer.elementExists(name):
            if not self._allow_fallback:
                raise ResetError('could not render {}'.format(repr(name)))
        else:
            self.setElementId(name)
            rect = renderer.boundsOnElement(name)

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
        name = self['name'].replace(' ', '_')
        category = self['category'].replace(' ', '_')
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


class SvgSpeciesItem(SvgItem):

    attrs = ('genus', 'name')
    directions = {
        'sw': 'sw',
        's': 'sw',
        'nw': 'nw',
        'n': 'nw',
        'se': 'se',
        'e': 'se',
        'ne': 'ne',
        'w': 'ne',
    }

    def reset(self, item):
        super(SvgItem, self).reset(item)

        genus = self['genus']
        name =  self['name'].replace(' ', '_')

        renderer = self.renderers.get(genus)
        if not renderer:
            fname = config.config['media_dir'] + '/genus/' + genus + '.svg'
            renderer = SvgRenderer(fname)
            if not renderer.isValid():
                raise ResetError('could not load renderer {}'.format(repr(fname)))
            self.renderers[genus] = renderer
        self.setSharedRenderer(renderer)

        self.setDirection('sw')

        rect = renderer.boundsOnElement(name)
        xo, yo = - (round(rect.width()) % 128), - (round(rect.height()) % 64)
        self._offset = xo, yo

        self._svg_size = renderer.defaultSize()
        self._setPos()

        return True

    def setDirection(self, direction):

        d = self.directions[direction]
        renderer = self.renderers.get(self['genus'])
        name =  self['name'].replace(' ', '_')
        name_dir = name + '_' + d

        if renderer.elementExists(name_dir):
            self.setElementId(name_dir)
        elif renderer.elementExists(name):
            self.setElementId(name)
        else:
            raise ResetError('could not render {}'.format(repr(name)))


    def _setPos(self):

        s = self._svg_size
        scale = float(self.tile_width) / max(s.width(), s.height())
        self.setScale(scale)
        x,y  = self.parentItem().center()
        h,w = s.height() * scale, s.width() * scale
        rect = self.boundingRect()
        h,w = rect.height() * scale, rect.width() * scale
        height = self.tile_width / 2
        self.setPos(x-w/2,y-h + height / 2)


class SvgTransitionItem(SvgItem):

    def _setPos(self):
        size = self._svg_size
        scale = float(self.tile_width) / min(size.width(), size.height()) 
        self.setScale(scale)
        name = self['name'].replace(' ', '_')
        category = self['category'].replace(' ', '_')
        offset_scale = self._svg_size.width()

        try:
            xo, yo = self.renderers[category].getOffset(name)
        except TypeError:
            xo, yo = 0, offset_scale / -16 # -8

        # FIXME I cannot see why should not be zero?!
        origin = offset_scale / 2, offset_scale / -16 # 64, -8

        x  = (xo - origin[0]) * scale
        y  = (yo - origin[1]) * scale
        self.setPos(x,y)

class SvgEquipmentItem(SvgItem):
    pass

