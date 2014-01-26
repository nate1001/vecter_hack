
from collections import OrderedDict
import logging
import os.path


class SystemFormatter(logging.Formatter): pass

class SystemFilterer(logging.Filterer):
    
    deny = (
        'model.generate',
        'model.ai',
        'model.level',
    )
    
    def filter(self, record):
        if record.module not in self.deny:
            return record


class SystemLogger(logging.Logger):
    
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    IMPOSSIBLE = 25
    WARN = logging.WARN
    FATAL = logging.FATAL

    def msg_debug(self, msg):
        self.debug(msg)
        self._run_callbacks(self.DEBUG, msg)

    def msg_info(self, msg):
        self.info(msg)
        self._run_callbacks(self.INFO, msg)

    def msg_impossible(self, msg):
        self.log(self.IMPOSSIBLE, msg)
        self._run_callbacks(self.IMPOSSIBLE, msg)

    def msg_warn(self, msg):
        self.warn(msg)
        self._run_callbacks(self.WARN, msg)

    def msg_fatal(self, msg):
        self.fatal(msg)
        self._run_callbacks(self.FATAL, msg)

    def _run_callbacks(self, level, msg):
        if level < self._game_level:
            return
        for c in self._callbacks:
            c(level, msg)
    
    def __init__(self, name):
        super(SystemLogger, self).__init__(name)

        self._callbacks = []
        self._game_level = self.INFO

        formatter = SystemFormatter('%(levelname)s: %(message)s')
        handler = logging.StreamHandler()
        self.addHandler(handler)
        handler.setFormatter(formatter)
        filterer = SystemFilterer()
        handler.addFilter(filterer)

    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None):
        fn = os.path.abspath(fn)
        d, p = os.path.split(fn)
        d = os.path.split(d)[1]
        name = '{}.{}'.format(d, os.path.splitext(os.path.basename(p))[0])
        record = super(SystemLogger, self).makeRecord(name, level, fn, lno, msg, args, exc_info)
        record.module = name
        return record

    def add_callback(self, callback):
        self._callbacks.append(callback)



class Direction(object):
    
    def __init__(self, key, name, abr, offset, opposite, iso):
        self.key = key
        self.name = name
        self.abr = abr
        self.offset = offset
        self.opposite = opposite
        self.iso = iso

    def bounce(self, axis):
        if axis == 'x':
            o = self.offset[0] * -1, self.offset[1]
        elif axis == 'y':
            o = self.offset[0], self.offset[1] * -1
        elif axis == 'xy':
            o = self.offset[0] * -1, self.offset[1] * -1
        else:
            raise ValueError(axis)
        for d in direction_by_abr.values():
            if o == d.offset:
                return d
        raise ValueError(o)
            
    def __repr__(self):
        return "<Direction {}>".format(self.abr)


direction_by_abr = {
    'n': Direction('k', 'north', 'n', ( 0, -1), 's', 'sw',),
    's': Direction('j', 'south', 's', ( 0,  1), 'n', 'ne'),
    'w': Direction('h', 'west',  'w', (-1,  0), 'e', 'nw',),
    'e': Direction('l', 'east',  'e', ( 1,  0), 'w', 'se'),
    'nw': Direction('y', 'northwest',  'nw', (-1, -1), 'se', 's'),
    'ne': Direction('u', 'northeast',  'ne', ( 1, -1), 'sw', 'w'),
    'sw': Direction('b', 'southwest',  'sw', (-1,  1), 'ne', 'e'),
    'se': Direction('n', 'southeast',  'se', ( 1,  1), 'nw', 'n'),
}


direction_by_name = OrderedDict((
    ('north', direction_by_abr['n']),
    ('south', direction_by_abr['s']),
    ('west', direction_by_abr['w']),
    ('east', direction_by_abr['e']),
    ('northwest', direction_by_abr['nw']),
    ('northeast', direction_by_abr['ne']),
    ('southwest', direction_by_abr['sw']),
    ('southeast', direction_by_abr['se']),
))

logger = SystemLogger('system')
