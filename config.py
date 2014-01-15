
from collections import OrderedDict
from logging import Logger, StreamHandler, Formatter, INFO, DEBUG


__NAME__ = 'Rogue'

logger = Logger(__NAME__)
handler = StreamHandler()
#handler.setFormatter(Formatter('%(turn_number):%(levelname)s: %(module)s: %(message)s'))
handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(funcName)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(INFO)
logger.setLevel(DEBUG)

game_logger = Logger('game')
handler = StreamHandler()
handler.setFormatter(Formatter('GAME: %(message)s'))
game_logger.addHandler(handler)
game_logger.setLevel(INFO)
game_logger.setLevel(DEBUG)
game_logger.setLevel(100)


BASE  = '/home/starling/src/rogue'
config = {}
config['media_dir'] = BASE + '/share/media/'
config['data_dir'] = BASE + '/share/data/'
config['background'] = 'black'
config['tile_size'] = 32

defaults = {}
defaults['view/use_svg'] = (True, bool, 'use vector graphics')
defaults['view/use_iso'] = (True, bool, 'use isometric graphics')
defaults['view/use_char'] = (True, bool, 'use character tiles')
defaults['view/seethrough'] = (False, bool, 'use seethrough walls')
defaults['view/debug'] = (False, bool, 'debug mode')
defaults['view/scale'] = (1, float, 'scale')

defaults['model/wizard'] = (False, bool, 'Wizard Mode')

map_defaults = defaults.copy()
map_defaults['view/use_svg'] = (False, bool, 'use vector graphics')
map_defaults['view/use_iso'] = (False, bool, 'use isometric graphics')



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
        

