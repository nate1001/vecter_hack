
import os
import ConfigParser

from util import SumOfDiceDist, Chance, Verb
from __init__ import config

class AttrReaderError(Exception): pass

class AttrConfig(object):
    
    '''
        Adds atrributes to classes from dos style config files e.g... ConfigParser.

        All classes that inerit this class are expected to have
        'attr' and 'name' attribute set at initializiation.

        attrs should be sequence of sequences in the form of
        (name, type), ... or (name, type, optional), ... 
        If optional is not given it assumed that the attribute is not optional
    '''

    @classmethod
    def values(cls):
        return AttrReader.items_from_klass(cls)
    
    def __init__(self, name):
        reader = AttrReader(self.__class__.__name__.lower(), self.attrs)
        try:
            values = reader.read()[name]
        except KeyError:
            raise AttrReaderError('No entry {} for {}.'.format(repr(name), self.__class__))
        self.name = name
        for key, value in values.iteritems():
            setattr(self, key.replace(' ', '_'), value)

    def __eq__(self, other):
        return type(self) is type(other) and self.name == other.name

    def __hash__(self):
        return id(type(self)) + hash(self.name)



def qt_color(name):
    
    from PyQt4 import QtGui
    color = QtGui.QColor(name)
    if not color.isValid():
        raise ValueError('{} is not a valid qt color name'.format(repr(name)))
    return color

def textlist(text):
    if not text:
        return []
    return [a.strip() for a in text.split(',') if a.strip()]

def chance(number):
    if number < 0 or number > 1:
        raise ValueError(number)
    return float(number)


class AttrReader(object):
    extended_types = {
        'dice': SumOfDiceDist.from_text,
        'qtcolor': qt_color,
        'textlist': textlist,
        'chance': Chance,
        'verb': Verb.from_text,
        'msg': lambda x : x if x else '',
    }
    __cache = {}
    __index = []
        
    def __init__(self, name, attrs):

        self.name = name
        self.attrs = attrs
        self.__index = []
        self.cache = 'hello'

    @classmethod
    def items_from_klass(cls, item_klass):
        return [item_klass(name) for name in AttrReader(item_klass.__name__.lower(), item_klass.attrs).read().keys()]

    def read(self):
        # dont read file every time
        # should be ok as files should not change while code is running
        if self.__cache.get(self.name):
            return self.__cache[self.name]

        #FIXME put direc path in config
        fname = config.config['data_dir'] + self.name + '.cfg'

        os.stat(fname)
        
        parser = ConfigParser.RawConfigParser()
        parser.read(fname)
        headers = {}

        for section in parser.sections():
            self.__index.append(section)
            unknown = [item[0]for item in parser.items(section) if item[0] not in [a[0] for a in self.attrs]]
            for item in unknown:
                raise AttrReaderError('unknown attribute {} for {} in section {}, file {}'.format(
                    repr(item), repr(self.name), repr(section), fname))
            headers[section] = {}
            for attr in self.attrs:
                try:
                    name, type_, optional = attr
                except ValueError:
                    name, type_ = attr
                    optional = False

                try:
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
                            raise AttrReaderError('unsupported type {} for {}'.format(repr(type_), repr(self.name)))

                    headers[section][name] = value[1]
                except ConfigParser.NoOptionError, e:
                    if optional:
                        headers[section][name] = None
                    else:
                        raise AttrReaderError('No attribute {} set in section {} in {}'.format(repr(name), repr(section), fname))

        self.__cache[self.name] = headers
        return headers



if __name__ == '__main__':
    
    attrs = (('hit points', 'int'),)
    reader = AttrReader('species', attrs)
    print reader.read()
