
from random import random

from messenger import Messenger, Signal
from attack import CombatArena
from action import Action

from config import logger


class Controller(Messenger):
    
    __signals__ = [
            Signal('action_happened_in_game', ('log level', 'is_player', 'msg')),
            Signal('level_changed', ('level',), 'The current level has changed.'),
            Signal('map_changed', ('level',), 'The map has changed it visual representation.'), #obsolete

            Signal('being_moved', ('old_idx', 'new_idx', 'guid', 'direction'), 
                                                'A being has moved to a different tile.'),
            Signal('being_became_visible', ('target_idx', 'being',), 
                                                'A being just became visible to the player.'),
            Signal('being_became_invisible', ('guid',), 
                                                'A being just became invisible to the player.'),
            Signal('being_meleed', ('source_idx', 'target_idx', 'guid', 'direction'), 
                                                'A being has attacked another tile.'),
            Signal('being_kicked', ('source_idx', 'target_idx', 'guid', 'direction'), 
                                                'A being has kicked another tile.'),
            Signal('being_spell_damage', ('idx', 'guid', 'spell'), 
                                                'A being has taken damage from magic.'),
            Signal('being_spell_resistance', ('idx', 'guid', 'spell'), 
                                                'A being has resisted magic.'),
            Signal('being_died', ('source_idx', 'guid'), 
                                                'A being has died.'),

            Signal('tile_inventory_changed', ('source_idx', 'inventory'), ''),
            Signal('tiles_changed_state', ('changed_tiles',), ''),
            Signal('tile_changed', ('tile',), ''),

            Signal('wand_zapped', ('wand', 'tiles', 'direction'), ''),
    ]


    def __init__(self):
        super(Controller, self).__init__()

        self.game = None
        self.combat_arena = CombatArena(self)
        logger.add_callback(self._send_msg)

    def player_can_see(self, tile):
        return self.game.player.vision.can_see(tile)

    def set_game(self, game):
        self.game = game

    def _send_msg(self, loglevel, msg):
        self.events['action_happened_in_game'].emit(loglevel, False, msg)

    def turn_done(self, being):
        if being.is_dead:
            return False

        player = self.game.player
        vision = player.vision

        if being is player:
            self.game.turn_done()

            changed = [t for t in self.game.level.values() if vision.has_changed(t)]
            if changed:
                self.events['tiles_changed_state'].emit([t.view(player) for t in changed])

            for tile in [t for t in changed if t.being]:
                if self.player_can_see(tile):
                    logger.ddebug('!!! {} became visible on {}.'.format(tile.being.words.You, tile))
                    self.events['being_became_visible'].emit(tile.idx, tile.being.view())
                    tile.being.has_been_seen = True
                else:
                    logger.ddebug('!!! {} became invisible on {}.'.format(tile.being.words.You, tile))
                    self.events['being_became_invisible'].emit(tile.being.guid)
        return True


    def die(self, being, attacker=None):

        t = self.game.level.tile_for(being)

        if attacker:
            attacker.experience += int(being.value)

        if self.player_can_see(t):
            if attacker:
                target = being.words.your_self if being is attacker else being.words.you
                logger.msg_fatal('{ar.You} {ar.kill} {target}!'.format(ar=attacker.words, target=target))
            else:
                logger.msg_fatal('{You_are} killed!'.format(**being.words_dict))
        else:
            logger.ddebug('An unseen {} dies!'.format(being))

        self.game.level.kill_being(being)

        if being.has_been_seen:
            self.events['being_died'].emit(t.idx, being.guid)
        if self.game.player is being:
            self.game.die()
        return True
    
    def attack(self, subject, target, direc):

        if not target:
            logger.msg_impossible('{You} {try} to attack nothing.'.format(**being.words_dict))
            return False
        elif not target.being:
            logger.msg_impossible('{You} {try} to attack empty space.'.format(**being.words_dict))
            return False
        self.events['being_meleed'].emit(subject.idx, target.idx, subject.being.guid, direc.abr)
        self.combat_arena.attack(subject.being, target.being)
        self.turn_done(subject.being)
        return True

    def move(self, subject, target):

        if not target:
            logger.msg_impossible("There is no tile for {you} to move there.".format(**subject.being.words_dict))
            return False
        elif target.being:
            logger.msg_impossible("{You} cannot move into a square with a monster!".format(**subject.being.words_dict))
            return False
        elif not target.tiletype.is_open:
            logger.msg_impossible("{You} cannot move through {tiletype}.".format(tiletype=target.tiletype, **subject.being.words_dict))
            return False

        being = subject.being
        self.game.level.move_being(subject, target)
        target_seen = self.player_can_see(target)
        subject_seen = self.player_can_see(subject)

        # if we are the player we always know about it
        if being.is_player:

            if not target.inventory:
                logger.debug('{You} {move} to {}.'.format(target, **being.words_dict))
            else:
                logger.msg_info('{You_are} standing on {}.'.format(target.inventory, **being.words_dict))
            self.events['being_moved'].emit(subject.idx, target.idx, being.guid, being.direction)

        # else if a monster just walked out of the dark
        elif target_seen and not subject_seen:
            logger.ddebug('{} came out of the dark onto {}.'.format(being.words.You, target))
            self.events['being_became_visible'].emit(subject.idx, being.view())
            self.events['being_moved'].emit(subject.idx, target.idx, being.guid, being.direction)
            being.has_been_seen = True

        # else if a monster just walked into the dark
        elif subject_seen and not target_seen:
            logger.ddebug('{} went into the dark onto {}.'.format(being.words.You, target))
            self.events['being_moved'].emit(subject.idx, target.idx, being.guid, being.direction)
            self.events['being_became_invisible'].emit(being.guid)

        # else if we watched the monster move
        elif subject_seen and target_seen:
            logger.ddebug('The player watched {} move onto {}.'.format(target.being, target))
            self.events['being_moved'].emit(subject.idx, target.idx, being.guid, being.direction)
        else:
            logger.ddebug('{} moved to {}, but the player did not see it.'.format(target.being.words.You, target))
        self.turn_done(target.being)
        return True

    #def _FXIME_move_staircase(self, being, staircase):
    #    if being.tile.tiletype.name != staircase:
    #        self._send_msg(5, being, "There is no {} here.".format(staircase))
    #        return False
    #    level = being.tile.level.leave_level(being)
    #    msg = 'You enter a new level.'
    #    if level.visited:
    #        msg += ' This place seems familiar ...'
    #    self._send_msg(8, being, msg)
    #    self.turn_done(being)
    #    self.events['level_changed'].emit(LevelView(level))
    #    return True
    #def move_up(self, being):
    #    return self._move_staircase(being, 'staircase up')
    #def move_down(self, being):
    #    return self._move_staircase(being, 'staircase down')

    def pickup_item(self, being):
        tile = self.game.level.tile_for(being)
        try:
            item = tile.inventory.pop()
        except IndexError:
            logger.msg_impossible("There is nothing for {you} to pickup".format(subject.being.words_dict))
            return False

        being.inventory.append(item)
        self.events['tile_inventory_changed'].emit(tile.idx, tile.inventory.view())
        logger.msg_info("{You} {pick} up {item}".format(item=item, **being.words_dict))
        self.turn_done(being)
        return True

    def drop_item(self, being):

        if not being.inventory:
            return False
        tile = self.game.level.tile_for(being)
        item = being.inventory.pop()
        tile.inventory.append(item)
        self.events['tile_inventory_changed'].emit(tile.idx, tile.inventory.view())
        logger.msg_info("{You} {drop} {item}".format(item=item, **being.words_dict))
        self.turn_done(being)
        return True

    def kick(self, source, target, direction):
        #FIXME do bad stuff to legs when we dont succeed
        self.events['being_kicked'].emit(source.idx, target.idx, source.being.guid, direction)
        being = source.being
        if target.breakable:
            # chance to break the door
            if random() > .5: #FIXME
                door = str(target)
                self.game.level.break_door(target)
                logger.msg_info("{You} {kick} {door} down!".format(door=target.tiletyp, **being.words_dict))
                self.events['tile_changed'].emit(target.view(self.game.player))
            # else we just hit the door
            else:
                logger.msg_info("Wham! Wham!")
        # else it was not a closed door
        else:
            if target.tiletype.is_open:
                logger.msg_info('{You} {kick} at empty space.'.format(**subject.being.words_dict))
            else:
                if subject.being.is_player:
                    logger.msg_info('Ouch! That hurts.')

    def zap(self, being, wand, direction):
        
        if wand.charges < 1:
            logger.msg_info('{You} cannot zap a wand without charges.'.format(**being.words_dict))
            return False
        wand.item.charges -= 1

        tile = self.game.level.tile_for(being)
        spell = wand.spell
        first = True

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
                    logger.ddebug('A {} passes through {}.'.format(wand.item.zap, t))
                    other = tile.being
                    if spell.damage and t.being:
                        if self.player_can_see(t):
                            logger.msg_warn("The {zap} hits {you}.".format(zap=wand.item.zap, **t.being.words_dict))
                        else:
                            logger.ddebug("The (unseen) {zap} hits {you}.".format(zap=wand.item.zap, **t.being.words_dict))
                        if self.combat_arena.spell_attack(tile, t, spell):
                            wand.item.known = True

                    if spell.method and spell.handle(self.game, t):
                        wand.item.known = True
                        logger.msg_warn('The wand {} {}.'.format(spell.verb.she, t.being))
                        self.handle_spell(spell, t, other, tile.being)

                # if the wand does not bounce or the tiletype does not bouce then stop
                if not (tiles[-1].tiletype.bounce and wand.kind.bounce):
                    break
                direction = direction.bounce(tiles[-1].tiletype.bounce)
                tile = self.game.level.adjacent_tile(tiles[-1], direction)
                first = False
        elif spell.method and spell.handle(self.game, tile):
            wand.item.known = True
            self.handle_spell(spell, tile, being)

        if not being.is_dead:
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
                logger.msg_info('{You} {open} {}'.format(name, **being.words_dict))
                self.events['tile_changed'].emit(target.view(self.game.player))
            else:
                if being.is_player:
                    logger.msg_info("The {} does not open.".format(name))
                else:
                    logger.msg_info("{You} cannot open the {}.".format(name, **being.words_dict))
            self.turn_done(being)
            return True
        else:
            logger.msg_impossible("{You} cannot open a {}.".format(name, **being.words_dict))
            return False

    def close(self, being, target):
        name = target.tiletype.kind
        if target.closable:
            ok = self.game.level.close_door(target)
            if ok:
                logger.msg_info('{You} {close} {}'.format(name, **being.words_dict))
                self.events['tile_changed'].emit(target.view(self.game.player))
            else:
                logger.msg_info('{You} {do} not {close} {}'.format(name, **being.words_dict))
            self.turn_done(being)
            return True
        else:
            logger.msg_impossible("{You} cannot close a {}.".format(name, **being.words_dict))
            return False

    #######################
    #spell handlers
    #######################

    def get_spell_handler(self, spell):
        return getattr(self, 'on_spell_' + spell.name)

    def handle_spell(self, spell, tile, being, attacker=None):
        self.get_spell_handler(spell)(spell, tile, being, attacker)

    def on_spell_teleportation(self, spell, tile, being, attacker):

        logger.ddebug('{} teleported to {}'.format(spell.target.being, spell.target))
        if self.player_can_see(tile):
            self.events['being_became_invisible'].emit(spell.target.being.guid)
        if self.player_can_see(spell.target):
            self.events['being_became_visible'].emit(spell.target.idx, spell.target.being.view())

    def on_spell_healing(self, spell, tile, being, attacker):
        verb = 'feel' if being.is_player else 'looks'
        logger.msg_info('{You} {} better'.format(verb, **being.words_dict))

    def on_spell_create_monster(self, spell, tile, being, attacker):
        self.events['being_became_visible'].emit(spell.target.idx, spell.target.being.view())

    def on_spell_death(self, spell, tile, being, attacker):
        self.die(tile.being, attacker)

    def on_spell_digging(self, spell, tile, being, attacker):
        if spell.msg:
            logger.msg_info(spell.msg)
        self.events['tile_changed'].emit(tile.view(self.game.player))

    def on_spell_confusor(self, spell, tile, being, attacker):
        logger.msg_info('{Your} hands begin to glow red.'.format(**being.words_dict))

    def on_spell_confusion(self, spell, tile, being, attacker):
        if being.is_player:
            logger.msg_info("Huh, what? Where am I?")
        else:
            logger.msg_info("{You} {look} confused.".format(**being.words_dict))
        
    def on_spell_opening(self, spell, tile, being, attacker):
        logger.msg_info(spell.msg)
        self.events['tile_changed'].emit(tile.view(self.game.player))

    def on_spell_locking(self, spell, tile, being, attacker):
        logger.msg_info(spell.msg)
        self.events['tile_changed'].emit(tile.view(self.game.player))

    def on_spell_lightning_blind(self, spell, tile, being, attacker):pass
    def on_spell_sleep(self, spell, tile, being, attacker):pass
    def on_spell_striking(self, spell, tile, being, attacker): pass
    def on_spell_fire(self, spell, tile, being, attacker): pass
    def on_spell_magic_missile(self, spell, tile, being, attacker): pass
    def on_spell_lightning(self, spell, tile, being, attacker): pass
    def on_spell_cold(self, spell, tile, being, attacker): pass

