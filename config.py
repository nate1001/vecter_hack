

from util import direction_by_abr, direction_by_name, logger

__NAME__ = 'Rogue'

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



        

