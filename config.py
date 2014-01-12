
from collections import OrderedDict
from logging import Logger, StreamHandler, Formatter, INFO, DEBUG


__NAME__ = 'Rogue'

logger = Logger(__NAME__)
handler = StreamHandler()
#handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(funcName)s: %(message)s'))
handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(INFO)
logger.setLevel(DEBUG)

game_logger = Logger('game')
handler = StreamHandler()
handler.setFormatter(Formatter('GAME: %(message)s'))
game_logger.addHandler(handler)
game_logger.setLevel(INFO)
game_logger.setLevel(DEBUG)


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
defaults['view/seethrough'] = (True, bool, 'use seethrough walls')
defaults['view/debug'] = (False, bool, 'debug mode')
defaults['view/scale'] = (1, float, 'scale')

defaults['model/wizard'] = (False, bool, 'Wizard Mode')


class Direction(object):
    
    def __init__(self, key, name, abr, offset, opposite):
        self.key = key
        self.name = name
        self.abr = abr
        self.offset = offset
        self.opposite = opposite

    def __repr__(self):
        return "<Direction {}>".format(self.abr)


direction_by_abr = {
    'n': Direction('k', 'north', 'n', ( 0, -1), 's'),
    's': Direction('j', 'south', 's', ( 0,  1), 'n'),
    'w': Direction('h', 'west',  'w', (-1,  0), 'e'),
    'e': Direction('l', 'east',  'e', ( 1,  0), 'w'),
    'nw': Direction('y', 'northwest',  'nw', (-1, -1), 'se'),
    'ne': Direction('u', 'northeast',  'ne', ( 1, -1), 'sw'),
    'sw': Direction('b', 'southwest',  'sw', (-1,  1), 'ne'),
    'se': Direction('n', 'southeast',  'se', ( 1,  1), 'nw'),
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
        

