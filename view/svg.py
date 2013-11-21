
from PyQt4 import QtCore, QtGui, QtSvg, QtXml

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
