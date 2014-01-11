
from messenger import Messenger, Signal
from attack import CombatArena
from action import Action

from config import game_logger


class Controller(Messenger):
    
    __signals__ = [
            Signal('action_happened_in_game', ('log level', 'is_player', 'msg')),
            Signal('level_changed', ('level',), 'The current level has changed.'),
            Signal('map_changed', ('level',), 'The map has changed it visual representation.'),

            Signal('being_moved', ('old_idx', 'new_idx', 'guid', 'direction'), 'A Monster has moved to a different tile.'),
            Signal('being_meleed', ('source_idx', 'target_idx', 'guid', 'direction'), 'A Monster has attacked another tile.'),
            Signal('being_died', ('source_idx', 'guid'), 'A Monster has died.'),
            Signal('being_became_visible', ('tile',), 'A Monster just became visible to the player.'),

            Signal('tile_inventory_changed', ('source_idx', 'inventory'), ''),
            Signal('tiles_changed_state', ('changed_tiles',), ''),
    ]


    def __init__(self):
        super(Controller, self).__init__()

        self.game = None
        self.combat_arena = CombatArena(self)

    def actions_from_being(self, being):
        return Action.from_being(being)

    def set_game(self, game):
        self.game = game


    def _send_msg(self, loglevel, being, msg, third_person=None):

        is_player = being is self.game.player

        if is_player:
            self.events['action_happened_in_game'].emit(loglevel, is_player, msg)
            game_logger.info(msg)
        else:
            if third_person is None:
                raise ValueError
            self.events['action_happened_in_game'].emit(loglevel, is_player, third_person)
            game_logger.info('{}: {}'.format(being, third_person))


    def has_monster(self, being, offset):
        new_tile = self.game.get_adjacent_for(being, offset)
        if new_tile and new_tile.being:
            return True
        return False

    def turn_done(self, being):
        player = self.game.player
        if being.is_dead:
            return False

        if being is player:
            self.game.turn_done()
            changed = [t.view(player) for t in self.game._current_level.values() if player.vision.has_changed(t)]
            if changed:
                self.events['tiles_changed_state'].emit(changed)

        return True

    def die(self, being):
        t = self.game.tile_for(being)
        self.game._current_level.kill_being(being)
        if self.game.player is being:
            self.game.die()
        self.events['being_died'].emit(t.idx, being.guid)
        self._send_msg(10, being, "You died!", 'The {} dies.'.format(being.name))
        return True
    
    def melee(self, being, offset):

        if not self.has_monster(being, offset):
            self._send_msg(5, being, 
                "There is no monster to fight there.", 
                "The {} tries to attack nothing.".format(being.name))
            return False

        t = self.game.tile_for(being)
        new_tile = self.game._current_level.get_adjacent(t, offset)
        if not new_tile:
            self._send_msg(5, being, "There is no tile to fight there.")
            return False

        monster = new_tile.being
        self.combat_arena.melee(being, monster)

        # make sure we fire melee before maybe killing the oponent
        t = self.game.tile_for(being)
        direc = self.game._current_level.direction_from(being, new_tile)
        self.events['being_meleed'].emit(t.idx, new_tile.idx, being.guid, direc)

        if monster.is_dead:
            self.die(monster)
            being.stats.experience += int(monster.value)

        self.turn_done(being)
        return True

    def move(self, being, offset):

        old_tile = self.game.tile_for(being)
        new_tile = self.game.get_adjacent_for(being, offset)

        if self.has_monster(being, offset):
            self._send_msg(5, being, "There is a monster on that square.")
            return False

        if not new_tile:
            self._send_msg(5, being, "There is no tile to move there.")
            return False

        if not new_tile.tiletype.is_open:
            self._send_msg(5, being, "You cannot move through {}.".format(new_tile.tiletype))
            return False

        self.game.move_being(new_tile, being)

        player = self.game.player
        vision = player.vision
        # if a monster just walked out of the dark
        if not being is player and (vision.can_see(new_tile) and not vision.can_see(old_tile)):
            self.events['being_became_visible'].emit(new_tile.view(player))
        # else if its moving around but we cannot see it
        elif not being is player and not vision.can_see(new_tile):
            pass
        else:
            self.events['being_moved'].emit(old_tile.idx, new_tile.idx, being.guid, being.direction)

        thing = new_tile.ontop(nobeing=True)
        self._send_msg(2, being,
            "You are standing on {}.".format(thing.description),
            "The {} is standing on {}.".format(being.name, thing.description))

        self.turn_done(being)
        return True

    def _move_staircase(self, being, staircase):
        #FIXME
        if being.tile.tiletype.name != staircase:
            self._send_msg(5, being, "There is no {} here.".format(staircase))
            return False
        level = being.tile.level.leave_level(being)
        msg = 'You enter a new level.'
        if level.visited:
            msg += ' This place seems familiar ...'
        self._send_msg(8, being, msg)
        self.turn_done(being)
        self.events['level_changed'].emit(LevelView(level))
        return True

    def move_up(self, being):
        return self._move_staircase(being, 'staircase up')

    def move_down(self, being):
        return self._move_staircase(being, 'staircase down')

    def pickup_item(self, being):
        tile = self.game.tile_for(being)
        try:
            item = tile.inventory.pop()
        except IndexError:
            self._send_msg(5, being, "There is nothing to pickup")
            return False

        being.inventory.append(item)
        self.events['tile_inventory_changed'].emit(tile.idx, tile.inventory.view())
        self._send_msg(5, being,
            "You pick up the {}.".format(item), 
            "The {} picks up the {}.".format(being.name, item))
        self.turn_done(being)
        return True

    def drop_item(self, being):

        if not being.inventory:
            return False
        tile = self.game.tile_for(being)
        item = being.inventory.pop()
        tile.inventory.append(item)
        self.events['tile_inventory_changed'].emit(tile.idx, tile.inventory.view())
        self._send_msg(5, being,
            "You drop the {}.".format(item), 
            "The {} drops the {}.".format(being.name, item))
        self.turn_done(being)
        return True



