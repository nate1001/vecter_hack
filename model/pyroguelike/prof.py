
import cProfile
from random import choice

class Tile(object):
    def __init__(self, is_open):
        self.is_open = is_open

size = 40,40
tiles = []
for y in range(size[1]):
    tiles.append([])
    for x in range(size[0]):
        tiles[-1].append(Tile(choice([True, False])))


def run_genray():

    from raycasting import Ray
    genray = Ray(20)
    for i in range(20):
        for ray in genray.rays((10,10), 5, (20,20)):
            print ray

def run_flags():
    
    from flags import Flags

    f = Flags.from_tiles_attr(tiles, 'is_open')
    o = Flags(size)
    for i in range(10**4):
        f[(10,10)]
        f[(11,11)] = False
        f & o
        f | o
        f ^ o
        ~f
    print f



#cProfile.run('run_genray()', 'profile.txt')
cProfile.run('run_flags()', 'profile.txt')

import pstats
p = pstats.Stats('profile.txt')
p.sort_stats('tottime').print_stats(10)
p.sort_stats('cumtime').print_stats(10)

