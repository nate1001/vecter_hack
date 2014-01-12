
from messenger import Messenger, Signal
from attack import CombatArena
from action import Action
from spell import registered_spells

from config import game_logger



class Controller(Messenger):
    
    __signals__ = [
            Signal('action_happened_in_game', ('log level', 'is_player', 'msg')),
            Signal('level_changed', ('level',), 'The current level has changed.'),
            Signal('map_changed', ('level',), 'The map has changed it visual representation.'),

            Signal('being_moved', ('old_idx', 'new_idx', 'guid', 'direction'), 'A Monster has moved to a different tile.'),
            Signal('being_meleed', ('source_idx', 'target_idx', 'guid', 'direction'), 'A Monster has attacked another tile.'),
            Signal('being_spell_damage', ('name', 'guid'), 'A Monster has taken damage from magic.'),
            Signal('being_died', ('source_idx', 'guid'), 'A Monster has died.'),
            Signal('being_became_visible', ('tile',), 'A Monster just became visible to the player.'),

            Signal('tile_inventory_changed', ('source_idx', 'inventory'), ''),
            Signal('tiles_changed_state', ('changed_tiles',), ''),

            Signal('wand_zapped', ('wand', 'tiles', 'direction'), ''),
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
        t = self.game.level.tile_for(being)
        self.game.level.kill_being(being)
        if self.game.player is being:
            self.game.die()
        self.events['being_died'].emit(t.idx, being.guid)
        self._send_msg(10, being, "You died!", 'The {} dies.'.format(being.name))
        return True
    
    def melee(self, subject, target, direc):

        if not target:
            self._send_msg(5, being, "There is no tile to fight there.")
            return False

        if not target.being:
            self._send_msg(5, being, 
                "There is no monster to fight there.", 
                "The {} tries to attack nothing.".format(being.name))
            return False

        self.events['being_meleed'].emit(subject.idx, target.idx, subject.being.guid, direc.abr)
        self.combat_arena.melee(subject.being, target.being)
        self.turn_done(subject.being)
        return True

    def move(self, subject, target):

        if target.being:
            self._send_msg(5, subject.being, "There is a monster on that square.")
            return False

        if not target:
            self._send_msg(5, subject.being, "There is no tile to move there.")
            return False

        if not target.tiletype.is_open:
            self._send_msg(5, subject.being, "You cannot move through {}.".format(target.tiletype))
            return False

        self.game.level.move_being(subject, target)

        player = self.game.player
        vision = player.vision
        # if a monster just walked out of the dark
        if not subject.being is player and (vision.can_see(target) and not vision.can_see(subject)):
            self.events['being_became_visible'].emit(target.view(player))
        # else if its moving around but we cannot see it
        elif not subject.being is player and not vision.can_see(target):
            pass
        else:
            self.events['being_moved'].emit(subject.idx, target.idx, target.being.guid, target.being.direction)

        thing = target.ontop(nobeing=True)
        self._send_msg(2, target.being,
            "You are standing on {}.".format(thing.description),
            "The {} is standing on {}.".format(target.being.name, thing.description))

        self.turn_done(target.being)
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
        tile = self.game.level.tile_for(being)
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
        tile = self.game.level.tile_for(being)
        item = being.inventory.pop()
        tile.inventory.append(item)
        self.events['tile_inventory_changed'].emit(tile.idx, tile.inventory.view())
        self._send_msg(5, being,
            "You drop the {}.".format(item), 
            "The {} drops the {}.".format(being.name, item))
        self.turn_done(being)
        return True

    def zap(self, being, wand, direction):
        
        tile = self.game.level.tile_for(being)
        spell = registered_spells[wand.spell]
        if wand.kind in ['ray' or 'beam']:
            tiles = self.game.level.get_ray(tile, direction, 10)
            print 33, tiles
            tiles = tiles[1:]
        else:
            tiles = []
        self.events['wand_zapped'].emit(wand.view(), [t.idx for t in tiles], direction)
        return spell.apply(being, tiles, self.combat_arena)
