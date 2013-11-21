
import cProfile



def tile():
    from tile import test
    test(40)


cProfile.run('tile()', 'profile.txt')

import pstats
p = pstats.Stats('profile.txt')
p.sort_stats('tottime').print_stats(10)
p.sort_stats('cumtime').print_stats(10)

