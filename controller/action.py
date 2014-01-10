

from messenger import Messenger, Signal, register_command
from config import game_logger


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
            game_logger.info(msg)


    @register_command('move', 'do nothing', '.')
    def do_nothing(self):
        self._being.controller.turn_done(self._being)
        return True


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
            self._send_msg(5, "You cannot move!")
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
            self._send_msg(5, "You cannot move!")
            return False
        return self._being.controller.move_up(self._being)

    @register_command('move', 'move down', '>')
    def move_down(self):
        if not self._being.can_move():
            self._send_msg(5, "You cannot move!")
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
            self._send_msg(5, "You have no items in your inventory.")
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
        self._send_msg(5, "You are standing on {}.".format(thing.description))
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
            self._send_msg(5, "You have nothing you can wear or use.")
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
        self._send_msg(5, "You are now wearing {}.".format(item))
        return True

    @register_command('action', 'stop using item', 't')
    def remove_using(self):

        using = self._being.using.in_use
        if not using:
            self._send_msg(5, "You have nothing you can take off or stop using.")
            return False
        self.events['remove_usable_requested'].emit(using, self._remove_using)
        return False

    #XXX index may not be stable if inventory is changable across calls
    def _remove_using(self, index):

        item = self._being.using._get_item(index)
        ok = self._being.using._remove_item(item)
        if not ok:
            self._send_msg(5, "You cannot stop using {}.".format(item))
            return False
        self._being.controller.turn_done(self._being)
        self._send_msg(5, "You took off {}.".format(item))
        return True
registered_actions_types = [Move, Acquire, Use, Examine, Melee, Wizard]


