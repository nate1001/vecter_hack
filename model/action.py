

from messenger import Messenger, Signal, register_command
from attack import CombatArena
from attr_reader import AttrReaderError



class Action(Messenger):

    __signals__ = [
        Signal('action_happened_to_player', ('log level', 'msg',)),
    ]

    def __init__(self, being):
        
        super(Action, self).__init__()
        self._being = being

    @classmethod
    def from_being(cls, being, wizard=True):
        '''Create an action that has only the methods allowed by the genus of the species.'''
        
        bases = []
        keys = {}
        for role in being.species.genus.actions:
            cls = globals()[role.capitalize()]
            bases.append(cls)

        if wizard:
            bases.append(Wizard)
                
        cls = type('Action', tuple(bases), {})
        return cls(being)

    def _send_msg(self, loglevel, msg):
        signal = self.events.get('action_happened_to_player')
        if signal:
            signal.emit(loglevel, msg)


    @register_command('move', 'do nothing', '.')
    def do_nothing(self):
        self._being.controller.turn_done(self._being)
        return True

        
#------------------------------------------------------------------------------
### Game Controller
#------------------------------------------------------------------------------
        

class Controller(Messenger):
    
    __signals__ = [
            Signal('action_happened_in_dungeon', ('log level', 'is_player', 'msg')),
            Signal('level_changed', ('level',), 'The current level has changed.'),
            Signal('map_changed', ('level',), 'The map has changed it visual representation.'),

            Signal('being_moved', ('old_idx', 'new_idx', 'guid', 'direction'), 'A Monster has moved to a different tile.'),
            Signal('being_meleed', ('source_idx', 'target_idx', 'guid', 'direction'), 'A Monster has attacked another tile.'),
            Signal('being_died', ('source_idx', 'guid'), 'A Monster has died.'),
            Signal('being_became_visible', ('tile',), 'A Monster just became visible to the player.'),

            Signal('tile_inventory_changed', ('source_idx', 'inventory'), ''),
            Signal('tiles_changed_state', ('changed_tiles',), ''),
    ]



    def __init__(self, dungeon):
        super(Controller, self).__init__()

        self.dungeon = dungeon
        self.combat_arena = CombatArena(self)

    def _send_msg(self, loglevel, being, msg, third_person=None):

        is_player = being is self.dungeon.player

        if is_player:
            self.events['action_happened_in_dungeon'].emit(loglevel, is_player, msg)
        else:
            if third_person is None:
                raise ValueError
            self.events['action_happened_in_dungeon'].emit(loglevel, is_player, third_person)


    def has_monster(self, being, offset):
        new_tile = self.dungeon.get_adjacent_for(being, offset)
        if new_tile and new_tile.being:
            return True
        return False

    def turn_done(self, being):
        player = self.dungeon.player
        if being.is_dead:
            return False

        if being is player:
            self.dungeon.turn_done()
            changed = [t.view(player) for t in self.dungeon._current_level.values() if player.vision.has_changed(t)]
            if changed:
                self.events['tiles_changed_state'].emit(changed)

        return True

    def die(self, being):
        t = self.dungeon.tile_for(being)
        self.dungeon._current_level.kill_being(being)
        if self.dungeon.player is being:
            self.dungeon.die()
        self.events['being_died'].emit(t.idx, being.guid)
        self._send_msg(10, being, "You died!", 'The {} dies.'.format(being.name))
        return True
    
    def melee(self, being, offset):

        if not self.has_monster(being, offset):
            self._send_msg(5, being, 
                "There is no monster to fight there.", 
                "The {} tries to attack nothing.".format(being.name))
            return False

        t = self.dungeon.tile_for(being)
        new_tile = self.dungeon._current_level.get_adjacent(t, offset)
        if not new_tile:
            self._send_msg(5, being, "There is no tile to fight there.")
            return False

        monster = new_tile.being
        self.combat_arena.melee(being, monster)

        # make sure we fire melee before maybe killing the oponent
        t = self.dungeon.tile_for(being)
        direc = self.dungeon._current_level.direction_from(being, new_tile)
        self.events['being_meleed'].emit(t.idx, new_tile.idx, being.guid, direc)

        if monster.is_dead:
            self.die(monster)
            being.stats.experience += int(monster.value)

        self.turn_done(being)
        return True

    def move(self, being, offset):

        old_tile = self.dungeon.tile_for(being)
        new_tile = self.dungeon.get_adjacent_for(being, offset)

        if self.has_monster(being, offset):
            self._send_msg(5, being, "There is a monster on that square.")
            return False

        if not new_tile:
            self._send_msg(5, being, "There is no tile to move there.")
            return False

        if not new_tile.tiletype.is_open:
            self._send_msg(5, being, "You cannot move through {}.".format(new_tile.tiletype))
            return False

        self.dungeon.move_being(new_tile, being)

        player = self.dungeon.player
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
        tile = self.dungeon.tile_for(being)
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
        tile = self.dungeon.tile_for(being)
        item = being.inventory.pop()
        tile.inventory.append(item)
        self.events['tile_inventory_changed'].emit(tile.idx, tile.inventory.view())
        self._send_msg(5, being,
            "You drop the {}.".format(item), 
            "The {} drops the {}.".format(being.name, item))
        self.turn_done(being)
        return True



#------------------------------------------------------------------------------
### Actions
#------------------------------------------------------------------------------
 



class Move(Action):

    __directions = {
        'north':  ( 0,  1),    
        'south':  ( 0, -1),    
        'west':   (-1,  0),    
        'east':   ( 1,  0),    
        'northwest':  (-1, -1),    
        'northeast':  ( 1, -1),    
        'southwest':  (-1,  1),    
        'southeast':  ( 1,  1),    
    }

    def move(self, offset):
        return self._being.controller.move(self._being, offset)

    def __move(self, being, direction):

        offset = self.__directions[direction]
        controller = self._being.controller

        # FIXME
        # if we cannot move
        #if not self._being.can_move():
        if False:
            self._send_msg(5, self._being, "You cannot move!")
            return False

        # if there is a monster and we can fight
        elif controller.has_monster(being, offset) and being.can_melee():
            return controller.melee(being, offset)

        # else try to move to the square
        else:
            ok = controller.move(being, offset)
            if ok:
                #self.examine_tile()
                pass
            return ok

    @register_command('move', 'move west', 'h')
    def move_west(self): return self.__move(self._being, 'west')
    @register_command('move', 'move east', 'l')
    def move_east(self): return self.__move(self._being, 'east')
    @register_command('move', 'move south', 'k')
    def move_south(self): return self.__move(self._being, 'south')
    @register_command('move', 'move north', 'j')
    def move_north(self): return self.__move(self._being, 'north')
    @register_command('move', 'move northwest', 'y')
    def move_northwest(self): return self.__move(self._being, 'northwest')
    @register_command('move', 'move northeast', 'u')
    def move_northeast(self): return self.__move(self._being, 'northeast')
    @register_command('move', 'move southwest', 'b')
    def move_southwest(self): return self.__move(self._being, 'southwest')
    @register_command('move', 'move southeast', 'n')
    def move_southeast(self): return self.__move(self._being, 'southeast')

    @register_command('move', 'move up', '<')
    def move_up(self):
        if not self._being.can_move():
            self._send_msg(5, self._being, "You cannot move!")
            return False
        return self._being.controller.move_up(self._being)

    @register_command('move', 'move down', '>')
    def move_down(self):
        if not self._being.can_move():
            self._send_msg(5, self._being, "You cannot move!")
            return False
        return self._being.controller.move_down(self._being)


class Melee(Action):
    def melee(self, offset):
        return self._being.controller.melee(self._being, offset)


            
class Acquire(Action):

    __signals__ = [
        Signal('inventory_requested', ('inventory',)),
    ]
    
    @register_command('action', 'pickup item', 'g')
    def pickup_item(self):
        ok = self._being.controller.pickup_item(self._being)
        return ok

    @register_command('action', 'drop item', 'd')
    def drop_item(self):
        if not self._being.inventory:
            self._send_msg(5, self._being, "You have no items in your inventory.")
            return False
        ok = self._being.controller.drop_item(self._being)
        return ok

    @register_command('action', 'view inventory', 'i')
    def view_inventory(self):
        self.events['inventory_requested'].emit(self._being.inventory.view())
        return True


class Examine(Action):

    __signals__ = [
        Signal('tile_requested', ('tile',)),
    ]

    @register_command('info', 'examine tile', 'x')
    def examine_tile(self):
        #FIXME
        tile = self._being.tile
        thing = tile.ontop(nobeing=True)
        self.events['tile_requested'].emit(tile)
        self._send_msg(5, self._being, "You are standing on {}.".format(thing.description))
        return False

class Wizard(Action):

    __signals__ = [
        Signal('answer_requested', ('question', 'callback',)),
    ]
    @register_command('wizard', 'create monster', 'ctrl+m')
    def create_monster(self):
        self.events['answer_requested'].emit('Create what species?', self._on_create_monster)
        return False

    def _on_create_monster(self, species):
        game = self._being.controller.dungeon
        try:
            being = game.create_being_by(self._being, species.strip())
        except AttrReaderError:
            self._send_msg(7, "No such spieces {} exists.".format(repr(species)))
            return False
        if not being:
            self._send_msg(7, "Could not create spieces {}.".format(species))
        else:
            self._send_msg(5, "Created spieces {}.".format(species))
            tile = game.tile_for(being)
            self._being.controller.events['being_became_visible'].emit(tile.view(game.player))
        return being is not None
    

class Use(Action):

    __signals__ = [
        Signal('add_usable_requested', ('usables', 'callback')),
        Signal('remove_usable_requested', ('using', 'callback')),
        Signal('using_requested', ('using',)),
    ]

    @register_command('info', 'view equipment', 'e')
    def view_using(self):

        items = self._being.using.items
        self.events['using_requested'].emit(items)
        return True

    @register_command('action', 'wear/wield/use item', 'w')
    def use_item(self):

        items = self._being.using.could_use(self._being.inventory)
        if not items:
            self._send_msg(5, self._being, "You have nothing you can wear or use.")
            return False

        self.events['add_usable_requested'].emit([(i.view()) for i in items], self._use_item)
        return False

    #XXX index may not be stable if inventory is changable across calls
    def _use_item(self, index):

        item = self._being.using.could_use(self._being.inventory)[index]

        ok = self._being.using._add_item(item)
        if not ok:
            self._send_msg(5, self._being, "You cannot wear or use {}.".format(item))
            return False

        self._being.controller.turn_done(self._being)
        self._send_msg(5, self._being, "You are now wearing {}.".format(item))
        return True

    @register_command('action', 'stop using item', 't')
    def remove_using(self):

        using = self._being.using.in_use
        if not using:
            self._send_msg(5, self._being, "You have nothing you can take off or stop using.")
            return False
        self.events['remove_usable_requested'].emit(using, self._remove_using)
        return False

    #XXX index may not be stable if inventory is changable across calls
    def _remove_using(self, index):

        item = self._being.using._get_item(index)
        ok = self._being.using._remove_item(item)
        if not ok:
            self._send_msg(5, self._being, "You cannot stop using {}.".format(item))
            return False
        self._being.controller.turn_done(self._being)
        self._send_msg(5, self._being, "You took off {}.".format(item))
        return True

registered_actions_types = [Move, Acquire, Use, Examine, Melee, Wizard]


