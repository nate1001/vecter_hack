
import cProfile
from generate import LevelGenerator


def run_genlevel():

    generator = LevelGenerator()
    tries = 1

    for i in range(tries):
        tiles, grid = generator.generate()


cProfile.run('run_genlevel()', 'profile.txt')

import pstats
p = pstats.Stats('profile.txt')
p.sort_stats('tottime').print_stats(10)
p.sort_stats('cumtime').print_stats(10)

