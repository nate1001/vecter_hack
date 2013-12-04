
import os
import ConfigParser

from util import SumOfDiceDist

class AttrConfig(object):
    
    def __init__(self, name):
        reader = AttrReader(self.__class__.__name__.lower(), self.attrs)
        values = reader.read()[name]
        self.name = name
        for key, value in values.iteritems():
            setattr(self, key.replace(' ', '_'), value)

def qt_color(name):
    
    from PyQt4 import QtGui
    color = QtGui.QColor(name)
    if not color.isValid():
        raise ValueError('{} is not a valid qt color name'.format(repr(name)))
    return color


def textlist(text):
    return [a.strip() for a in text.split(',')]


class AttrReader(object):
    extended_types = {
        'dice': SumOfDiceDist.parse_from_text,
        'qtcolor': qt_color,
        'textlist': textlist
    }
    _cache = {}
        
    
    def __init__(self, name, attrs):

        self.name = name
        self.attrs = attrs

    @classmethod
    def items_from_klass(cls, item_klass):
        return [item_klass(name) for name in AttrReader(item_klass.__name__.lower(), item_klass.attrs).read().keys()]

    def read(self):
        # dont read file every time
        # should be ok as files should not change while code is running
        if self._cache.get(self.name):
            return self._cache[self.name]

        fname = 'data/' + self.name + '.cfg'
        os.stat(fname)
        
        parser = ConfigParser.RawConfigParser()
        parser.read(fname)
        headers = {}

        for section in parser.sections():
            headers[section] = {}
            for attr in self.attrs:
                name, type_ = attr

                if type_ == 'int':
                    value = section, parser.getint(section, name)
                elif type_ == 'float':
                    value = section, parser.getfloat(section, name)
                elif type_ == 'boolean':
                    value = section, parser.getboolean(section, name)
                elif type_ == 'text':
                    value = section, parser.get(section, name)
                else:
                    ok = False
                    for type__ in self.extended_types:
                        if type_ == type__:
                            value = section, parser.get(section, name)
                            value = type__, self.extended_types[type_](value[1])
                            ok = True
                    if not ok:
                        raise TypeError('unsupported type: ' + type_)

                headers[section][name] = value[1]
        self._cache[self.name] = headers
        return headers



if __name__ == '__main__':
    
    attrs = (('hit points', 'int'),)
    reader = AttrReader('species', attrs)
    print reader.read()
