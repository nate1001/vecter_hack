
import cProfile


def run():

    from model.dungeon import Dungeon, Game
    dungeon = Dungeon(Game())
    dungeon.new(False)
    for i in range(10):
        dungeon.turn_done()


cProfile.run('run()', 'profile.txt')

import pstats
p = pstats.Stats('profile.txt')
p.sort_stats('tottime').print_stats(10)
p.sort_stats('cumtime').print_stats(10)

