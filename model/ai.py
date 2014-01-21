
from logging import StreamHandler, Handler
from random import choice
from config import logger, direction_by_name


class AI(object):
    
    def __init__(self, send_msg):
        self._send_msg = send_msg
    
    def send_msg(self, monster, level, msg):
        idx = level.tile_for(monster).idx
        new = 'The {} on {} {}'.format(str(monster), idx, msg)
        logger.info(new)
        self._send_msg(1, monster, None, new)

    def _should_wake_up(self, level, player, monster):

        # dont bother to update fov (as expensive) if were out of euclidean distance
        tile = level.tile_for(player)
        m_tile = level.tile_for(monster)
        if level.being_distance(player, monster) <= monster.stats.vision:
            level.set_fov(monster)
            can_see = monster.vision.can_see(tile)
        else:
            can_see = False
        #can_sense = monster.vision.can_sense_other(player)
        can_sense = False

        if can_sense or can_see:
            if can_sense and can_see:
                logger.debug('The {} on {} woke up from sensing and seeing you.'.format(monster, m_tile))
            elif can_see:
                logger.debug('The {} on {} woke up from seeing you.'.format(monster, m_tile))
            elif can_sense:
                logger.debug('The {} on {} woke up from sensing you.'.format(monster, m_tile))

        return can_sense or can_see

    def move_monsters(self, level, player, monsters):

        for monster in monsters:
            if not player.is_dead:
                self.make_move(level, player, monster)
        
    def make_move(self, level, player, monster):
        
        if monster.has_condition('paralyzed'):
            return

        if monster.has_condition('asleep'):
            if self._should_wake_up(level, player, monster):
                monster.clear_condition('asleep')
            return True

        level.set_fov(monster)

        m_tile = level.tile_for(monster)
        p_tile = level.tile_for(player)

        # if we can fight
        if hasattr(monster.actions, 'melee'):

            # if were next to player then attack
            #FIXME being_distance seems to be high by 1
            if level.being_distance(player, monster) < 2:
                logger.debug('The {} on {} melees with you.'.format(monster, m_tile))
                monster.actions.melee(p_tile)
                return True

        # if we cant even move give up
        if not hasattr(monster.actions, 'move'):
            return False

        #chase if we are not confused
        if not monster.has_condition('confused'):
            logger.debug('The {} on {} is chasing you.'.format(monster, m_tile))
            tile = level.chase_player(monster)
        else:
            tile = None

        # if we cant chase move randomly
        if not tile:
            logger.debug('The {} on {} could not chase you.'.format(monster, m_tile))
            tile = self._random_walk(player, level, monster)

        # if we cant move giveup
        if not tile:
            logger.debug('The {} on {} could not find a tile to move to.'.format(monster, m_tile))
            return False

        # dont attack other monsters
        if tile.being:
            logger.debug('The {} on {} tried to attack another monster.'.format(monster, m_tile))
            return False
        # else just move to the square
        else:
            monster.actions.move(tile)
        return True

    def _random_walk(self, player, level, monster):

        t = level.tile_for(monster)
        tiles = [t for t in level.adjacent_tiles(t) if t.tiletype.is_open]
        tile = choice(tiles)
        return tile


