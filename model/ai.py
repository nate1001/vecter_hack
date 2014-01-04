
from logging import StreamHandler, Handler
from random import choice
from config import logger


class AI(object):
    
    def __init__(self, send_msg):
        self._send_msg = send_msg
    
    def send_msg(self, monster, level, msg):
        idx = level.tile_for(monster).idx
        new = 'The {} on {} {}'.format(monster, idx, msg)
        logger.info(new)
        self._send_msg(1, monster, None, new)

    def _should_wake_up(self, level, player, monster):

        # dont bother to update fov (as expensive) if were out of euclidean distance
        tile = level.tile_for(player)
        if level.being_distance(player, monster) <= monster.stats.vision:
            level.set_fov(monster)
            can_see = monster.vision.can_see(tile)
        else:
            can_see = False
        #can_sense = monster.vision.can_sense_other(player)
        can_sense = False

        if can_sense or can_see:
            if can_sense and can_see:
                self.send_msg(monster, level, 'woke up from sensing and seeing you.')
            elif can_see:
                self.send_msg(monster, level, 'woke up from seeing you.')
            elif can_sense:
                self.send_msg(monster, level, 'woke up from sensing you.')

        return can_sense or can_see

    def move_monsters(self, level, player, monsters):

        for monster in monsters:
            if not player.is_dead:
                self.make_move(level, player, monster)
        
    def make_move(self, level, player, monster):

        if monster.condition.asleep:
            monster.condition.asleep = not self._should_wake_up(level, player, monster)
            return True

        level.set_fov(monster)

        m_tile = level.tile_for(monster)
        p_tile = level.tile_for(player)
        offset = m_tile.get_offset(p_tile)

        # if were next to player then attack
        #FIXME being_distance seems to be high by 1
        if level.being_distance(player, monster) < 2:
            self.send_msg(monster, level, 'attacks you.')
            monster.controller.melee(monster, offset)
            return True

        tile = level.chase_player(monster)

        # if we cant chase move randomly
        if not tile:
            self.send_msg(monster, level, 'could not chase you.')
            tile = self._random_walk(player, level, monster)

        # if we cant move randomly giveup
        if not tile:
            self.send_msg(monster, level, 'cound not find a tile to move to.')
            return False

        # dont attack other monsters
        if tile.being:
            self.send_msg(monster, level, 'tried to attack another monster.')
            return False

        # else just move to the square
        else:
            offset = m_tile.get_offset(tile)
            self.send_msg(monster, level, 'is chasing you.')
            monster.controller.move(monster, offset)
        return True

    def _random_walk(self, player, level, monster):

        t = level.tile_for(monster)
        tiles = [t for t in level.get_all_adjacent(t) if t.tiletype.is_open]
        tile = choice(tiles)
        return tile


