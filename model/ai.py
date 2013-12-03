
from logging import StreamHandler, Handler
from random import choice

from config import logger


class AI(object):
    
    def __init__(self, send_msg):
        self._send_msg = send_msg
    
    def send_msg(self, monster, msg):
        new = 'The {} on {} {}'.format(monster, monster.tile.idx, msg)
        logger.info(new)
        self._send_msg(1, monster, None, new)

    def _should_wake_up(self, level, player, monster):

        # dont bother to update fov (as expensive) if were out of euclidean distance
        if monster.tile.distance(player.tile) <= monster.stats.vision:
            level.set_fov(monster)
            can_see = monster.vision.can_see_other(player)
        else:
            can_see = False
        can_sense = monster.vision.can_sense_other(player)

        if can_sense or can_see:
            if can_sense and can_see:
                self.send_msg(monster,'woke up from sensing and seeing you.'.format(monster))
            elif can_see:
                self.send_msg(monster,'woke up from seeing you.'.format(monster))
            elif can_sense:
                self.send_msg(monster,'woke up from sensing you.'.format(monster))

        return can_sense or can_see

    def move_monsters(self, level, player, monsters):

        for monster in monsters:
            self.make_move(level, player, monster)
        
    def make_move(self, level, player, monster):

        if monster.condition.asleep:
            monster.condition.asleep = not self._should_wake_up(level, player, monster)
            return True

        level.set_fov(monster)

        # if were next to player then attack
        if monster.tile.distance(player.tile) < 2:
            offset = monster.tile.get_offset(player.tile)
            self.send_msg(monster,'attacks you.'.format(monster))
            monster.controller.melee(monster, offset)
            return True

        tile = level.chase_player(monster)

        # if we cant chase move randomly
        if not tile:
            self.send_msg(monster,'could not chase you.'.format(monster))
            tile = self._random_walk(player, level, monster)

        # if we cant move randomly giveup
        if not tile:
            self.send_msg(monster,'cound not find a tile to move to.'.format(monster))
            return False

        offset = monster.tile.get_offset(tile)

        # dont attack other monsters
        if tile.being:
            self.send_msg(monster,'tried to attack another monster.'.format(monster))
            return False

        # else just moveto the square
        else:

            self.send_msg(monster,'is chasing you.'.format(monster))
            monster.controller.move(monster, offset)
        return True

    def _random_walk(self, player, level, monster):

        tiles = [t for t in level.get_all_adjacent(monster.tile) if t.tiletype.is_open]
        tile = choice(tiles)
        return tile


