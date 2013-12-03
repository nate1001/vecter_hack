

from messenger import Messenger, Signal, register_command
from attack import CombatArena



class Action(Messenger):

    __signals__ = [
        Signal('action_happened_to_player', ('log level', 'is_player', 'msg',)),
    ]

    def __init__(self, being):
        
        super(Action, self).__init__()
        self._being = being

    @classmethod
    def from_being(cls, being):
        '''Create an action that has only the methods allowed by the genus of the species.'''
        
        bases = []
        keys = {}
        for role in being.species.genus.actions:
            cls = globals()[role.capitalize()]
            bases.append(cls)
                
        cls = type('Action', tuple(bases), {})
        return cls(being)

    def _send_msg(self, loglevel, being, msg, third_person=None):

        is_player = being is being.controller.dungeon.player

        if is_player:
            self.events['action_happened_to_player'].emit(loglevel, is_player, msg)
        else:
            if third_person is None:
                raise ValueError()
            self.events['action_happened_to_player'].emit(loglevel, is_player, third_person)

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

            Signal('being_moved', ('old_idx', 'new_idx', 'guid'), 'A Monster has moved to a different tile.'),
            Signal('being_meleed', ('source_idx', 'target_idx', 'guid'), 'A Monster has attacked another tile.'),
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
        new_tile = self.dungeon._current_level.get_adjacent(being.tile, offset)
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
        self.dungeon._current_level.kill_being(being)
        if self.dungeon.player is being:
            self.dungeon.game.die()
        self.events['being_died'].emit(being.tile.idx, being.guid)
        self._send_msg(10, being, "You died!", 'The {} dies.'.format(being.name))
        return True
    
    def melee(self, being, offset):

        if not self.has_monster(being, offset):
            self._send_msg(5, being, 
                "There is no monster to fight there.", 
                "The {} tries to attack nothing.".format(being.name))
            return False

        new_tile = self.dungeon._current_level.get_adjacent(being.tile, offset)
        if not new_tile:
            self._send_msg(5, being, "There is no tile to fight there.")
            return False

        monster = new_tile.being
        self.combat_arena.melee(being, monster)

        # make sure we fire melee before maybe killing the oponent
        self.events['being_meleed'].emit(being.tile.idx, new_tile.idx, being.guid)

        if monster.is_dead:
            self.die(monster)

        self.turn_done(being)
        return True

    def move(self, being, offset):
        old_tile = being.tile

        if self.has_monster(being, offset):
            self._send_msg(5, being, "There is a monster on that square.")
            return False

        new_tile = self.dungeon._current_level.get_adjacent(old_tile, offset)
        if not new_tile:
            self._send_msg(5, being, "There is no tile to move there.")
            return False

        if not new_tile.tiletype.is_open:
            self._send_msg(5, being, "You cannot move through {}.".format(new_tile.tiletype))
            return False

        new_tile.move_to(being)
        
        player = self.dungeon.player
        vision = player.vision
        # if a monster just walked out of the dark
        if not being is player and (vision.can_see(new_tile) and not vision.can_see(old_tile)):
                self.events['being_became_visible'].emit(new_tile.view(player))
        else:
            self.events['being_moved'].emit(old_tile.idx, new_tile.idx, being.guid)

        thing = new_tile.ontop(nobeing=True)
        self._send_msg(2, being,
            "You are standing on {}.".format(thing.description),
            "The {} is standing on {}.".format(being.name, thing.description))

        self.turn_done(being)
        return True

    def _move_staircase(self, being, staircase):
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
        try:
            item = being.tile.inventory.pop()
        except IndexError:
            self._send_msg(5, being, "There is nothing to pickup")
            return False

        being.inventory.append(item)
        self.events['tile_inventory_changed'].emit(being.tile.idx, being.tile.inventory.view())
        self._send_msg(5, being,
            "You pick up the {}.".format(item), 
            "The {} picks up the {}.".format(being.name, item))
        self.turn_done(being)
        return True

    def drop_item(self, being):

        if not being.inventory:
            return False

        item = being.inventory.pop()
        being.tile.inventory.append(item)
        self.events['tile_inventory_changed'].emit(being.tile.idx, being.tile.inventory.view())
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
        tile = self._being.tile
        thing = tile.ontop(nobeing=True)
        self.events['tile_requested'].emit(tile)
        self._send_msg(5, self._being, "You are standing on {}.".format(thing.description))
        return False
    

class Wear(Action):

    __signals__ = [
        Signal('add_wielding_requested', ('wearables', 'callback')),
        Signal('take_off_item_requested', ('wearing', 'callback')),
        Signal('remove_wielding_requested', ('worn', 'callback')),
        Signal('equipment_requested', ('wearing',)),
    ]

    @register_command('info', 'view equipment', 'e')
    def view_equipment(self):

        items = self._being.wearing._get_items()
        self.events['equipment_requested'].emit(items)
        return True

    @register_command('info', 'wield/wear item', 'w')
    def wield_item(self):

        items = self._being.wearing._possible(self._being.inventory)
        if not items:
            self._send_msg(5, self._being, "You have nothing you can wear.")
            return False

        self.events['add_wielding_requested'].emit([str(i) for i in items], self._wield_item)
        return False

    @register_command('action', 'take off item', 't')
    def takoff_item(self):

        items = self._being.wearing._get_items(show_blank=False)
        if not items:
            self._send_msg(5, self._being, "You have nothing you can take off.")
            return False

        self.events['take_off_item_requested'].emit(items, self._take_off_item)
        return False


    #XXX index may not be stable if inventory is changable across calls
    def _wield_item(self, index):

        item = self._being.wearing._possible(self._being.inventory)[index]

        ok = self._being.wearing.set_item(item)
        if not ok:
            self._send_msg(5, self._being, "You cannot wield or wear {}.".format(item))
            return False

        self._being.controller.turn_done(self._being)
        self._send_msg(5, self._being, "You are now wearing {}.".format(item))
        return True

    #XXX index may not be stable if inventory is changable across calls
    def _take_off_item(self, index):

        item = self._being.wearing._get_items(show_blank=False)[index]

        ok = self._being.wearing.remove_item(item)
        if not ok:
            self._send_msg(5, self._being, "You cannot take off {}.".format(item[1]))
            return False

        self._being.controller.turn_done(self._being)
        self._send_msg(5, self._being, "You took off {}.".format(item[1]))
        return True

registered_actions_types = [Move, Acquire, Wear, Examine]


