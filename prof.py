
import cProfile


def run():

    from view.util import Settings
    from model.game import Game
    from config import defaults, __NAME__

    settings = Settings(__NAME__.lower(), defaults)
    game = Game(settings)
    game.new()
    for i in range(10):
        game.turn_done()


def run_gui():
    import qtrogue


cProfile.run('run_gui()', 'profile.txt')

import pstats
p = pstats.Stats('profile.txt')
p.sort_stats('tottime').print_stats(20)
p.sort_stats('cumtime').print_stats(20)

