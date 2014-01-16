
from random import random

from messenger import Messenger, Signal
from attack import CombatArena
from action import Action

from config import game_logger, logger


class Controller(Messenger):
    
    __signals__ = [
            Signal('action_happened_in_game', ('log level', 'is_player', 'msg')),
            Signal('level_changed', ('level',), 'The current level has changed.'),
            Signal('map_changed', ('level',), 'The map has changed it visual representation.'),

            Signal('being_moved', ('old_idx', 'new_idx', 'guid', 'direction'), 'A Monster has moved to a different tile.'),
            Signal('being_teleported', ('old_idx', 'new_idx', 'guid',), 'A Monster has telported to a new tile.'),
            Signal('being_meleed', ('source_idx', 'target_idx', 'guid', 'direction'), 'A Monster has attacked another tile.'),
            Signal('being_kicked', ('source_idx', 'target_idx', 'guid', 'direction'), 'A Monster has kicked another tile.'),
            Signal('being_spell_damage', ('idx', 'guid', 'spell'), 'A Monster has taken damage from magic.'),
            Signal('being_spell_resistance', ('idx', 'guid', 'spell'), 'A Monster has resisted magic.'),
            Signal('being_died', ('source_idx', 'guid'), 'A Monster has died.'),
            Signal('being_became_visible', ('tile',), 'A Monster just became visible to the player.'),

            Signal('tile_changed', ('tile',), ''),
            Signal('tile_inventory_changed', ('source_idx', 'inventory'), ''),
            Signal('tiles_changed_state', ('changed_tiles',), ''),

            Signal('wand_zapped', ('wand', 'tiles', 'direction'), ''),
    ]


    def __init__(self):
        super(Controller, self).__init__()

        self.game = None
        self.combat_arena = CombatArena(self)

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

        self.events['being_died'].emit(t.idx, being.guid)
        if self.game.player is being:
            self.game.die()
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
            "You pick up {}.".format(item), 
            "The {} picks up {}.".format(being.name, item))
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
            "You drop {}.".format(item), 
            "The {} drops {}.".format(being.name, item))
        self.turn_done(being)
        return True

    def kick(self, source, target, direction):
        #FIXME do bad stuff to legs when we dont succeed
        self.events['being_kicked'].emit(source.idx, target.idx, source.being.guid, direction)
        if target.breakable:
            # chance to break the door
            if random() > .5: #FIXME
                door = str(target)
                self.game.level.break_door(target)
                self._send_msg(5, source.being,
                    "As you kick {}, it crashes open!".format(door),
                    "The {} kicks {} down!".format(source.being, door))
                self.events['tile_changed'].emit(target.view(self.game.player))
            # else we just hit the door
            else:
                self._send_msg(5, source.being, "Wham!", "Wham.")
        # else it was not a closed door
        else:
            if target.tiletype.is_open:
                self._send_msg(5, source.being, "You kick at empty space", None)
            else:
                self._send_msg(5, source.being, "Ouch that hurts.", None)

    def zap(self, being, wand, direction):
        
        if wand.charges < 1:
            self._send_msg(5, being,
                "The {} has no charges.".format(wand), 
                "The {} has no charges.".format(wand))
            return False
        wand.item.charges -= 1

        tile = self.game.level.tile_for(being)
        spell = wand.spell
        first = True
        ok = False

        # if its ray we now know it.
        if not wand.item.known and wand.kind.bounce:
            wand.item.known = True

        # if we have a ray or a beam
        if wand.kind.ray_dice:
            length = wand.kind.ray_dice.roll()
            while length > 0:
                tiles = self.game.level.get_ray(tile, direction, length+1, all_types=wand.item.can_tunnel)
                if first:
                    tiles = tiles[1:]
                length -= len(tiles)
                self.events['wand_zapped'].emit(spell.view(), [t.idx for t in tiles], direction)

                for t in tiles:
                    other = tile.being
                    if spell.damage and t.being:
                        self._send_msg(5, being,
                            "The {} hits the {}.".format(wand.item.zap, t.being),
                            "The {} hits you.".format(wand.item.zap),)
                        if self.combat_arena.spell_attack(tile, t, spell):
                            wand.item.known = True

                    if spell.method and spell.handle(self.game, t):
                        wand.item.known = True
                        self.handle_spell(spell, t, other)

                # if the wand does not bounce or the tiletype does not bouce then stop
                if not (tiles[-1].tiletype.bounce and wand.kind.bounce):
                    break
                direction = direction.bounce(tiles[-1].tiletype.bounce)
                tile = self.game.level.adjacent_tile(tiles[-1], direction)
                first = False
        elif spell.method and spell.handle(self.game, tile):
            wand.item.known = True
            self.handle_spell(spell, tile, being)
        self.turn_done(being)
        return True

    def quaff(self, being, potion):
        tile = self.game.level.tile_for(being)
        being = tile.being
        if potion.spell.handle(self.game, tile):
            self.handle_spell(potion.spell, tile, being)
        potion.count -= 1
        self.turn_done(being)
        return True

    def read(self, being, scroll):
        tile = self.game.level.tile_for(being)
        being = tile.being
        if scroll.spell.handle(self.game, tile):
            self.handle_spell(scroll.spell, tile, being)
        scroll.count -= 1
        self.turn_done(being)
        return True

    
    def open(self, being, target):
        name = target.tiletype.kind
        if target.openable:
            ok = self.game.level.open_door(target)
            if ok:
                self._send_msg(5, being, 
                    "You open the {}.".format(name),
                    "The {} opens the {}.".format(being, name))
                self.events['tile_changed'].emit(target.view(self.game.player))
            else:
                self._send_msg(5, being, 
                    "The {} does not open.".format(name),
                    "The {} cannot open the {}.".format(being, name))
            self.turn_done(being)
            return True
        else:
            self._send_msg(5, being, 
                "You cannot open a {}.".format(name),
                "The {} cannot open a {}.".format(being, name))
            return False

    def close(self, being, target):
        name = target.tiletype.kind
        if target.closable:
            ok = self.game.level.close_door(target)
            if ok:
                self._send_msg(5, being, 
                    "You close the {}.".format(name),
                    "The {} closes the {}.".format(being, name))
                self.events['tile_changed'].emit(target.view(self.game.player))
            else:
                self._send_msg(5, being, 
                    "The {} does not close.".format(name),
                    "The {} cannot close the {}.".format(being, name))
            self.turn_done(being)
            return True
        else:
            self._send_msg(5, being, 
                "You cannot close a {}.".format(name),
                "The {} cannot close a {}.".format(being, name))
            return False

    #######################
    #spell handlers
    #######################

    def get_spell_handler(self, spell):
        return getattr(self, 'on_spell_' + spell.name)

    def handle_spell(self, spell, tile, being):
        self.get_spell_handler(spell)(spell, tile, being)

    def on_spell_teleportation(self, spell, tile, being):
        target = self.game.level.tile_for(being)
        self.events['being_teleported'].emit(tile.idx, target.idx, being.guid)
        self.events['being_became_visible'].emit(target.view(self.game.player))

    def on_spell_healing(self, spell, tile, being):
        self._send_msg(5, being, 
            "You feel better.", 
            "{} looks better.".format(being.name))

    def on_spell_create_monster(self, spell, tile, being):
        self.events['being_became_visible'].emit(spell.target.view(self.game.player))

    def on_spell_death(self, spell, tile, being):
        self.die(tile.being)

    def on_spell_digging(self, spell, tile, being):
        self.events['tile_changed'].emit(tile.view(self.game.player))

    def on_spell_confusor(self, spell, tile, being):
        self._send_msg(5, being, 
            "Your hands begin to glow red.",
            "The {} begin to glow red.".format(being.name))

    def on_spell_confusion(self, spell, tile, being):
        self._send_msg(5, being, "Huh, what? Where am I?", None)
        
    def on_spell_opening(self, spell, tile, being):
        self._send_msg(5, being, spell.msg, spell.msg)
        self.events['tile_changed'].emit(tile.view(self.game.player))

    def on_spell_locking(self, spell, tile, being):
        self._send_msg(5, being, spell.msg, spell.msg)
        self.events['tile_changed'].emit(tile.view(self.game.player))

    def on_spell_lightning_blind(self, spell, tile, being):pass
    def on_spell_sleep(self, spell, tile, being):pass
    def on_spell_striking(self, spell, tile, being): pass
    def on_spell_fire(self, spell, tile, being): pass
    def on_spell_magic_missile(self, spell, tile, being): pass
    def on_spell_lightning(self, spell, tile, being): pass
    def on_spell_cold(self, spell, tile, being): pass

