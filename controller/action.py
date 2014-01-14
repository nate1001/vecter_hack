

from messenger import Messenger, Signal, register_command
from model.attr_reader import AttrReaderError

from config import game_logger, direction_by_name

class Action(Messenger):

    __signals__ = [
        Signal('action_happened_to_player', ('log level', 'msg',)),
    ]

    def __init__(self, controller, being):
        
        super(Action, self).__init__()
        self.being = being
        self.controller = controller

    @classmethod
    def from_being(cls, controller, being, wizard=True):
        '''Create an action that has only the methods allowed by the genus of the species.'''
        
        bases = []
        keys = {}
        for role in being.species.genus.actions:
            cls = globals()[role.capitalize()]
            bases.append(cls)

        if wizard:
            bases.append(Wizard)
                
        cls = type('Action', tuple(bases), {})
        return cls(controller, being)

    def _send_msg(self, loglevel, msg):
        signal = self.events.get('action_happened_to_player')
        if signal:
            signal.emit(loglevel, msg)
            game_logger.info(msg)


    @register_command('move', 'do nothing', '.')
    def do_nothing(self):
        self.controller.turn_done(self.being)
        return True


class Move(Action):

    def move(self, target):
        subject = self.controller.game.level.tile_for(self.being)
        return self.controller.move(subject, target)

    def __move(self, being, name):

        direc = direction_by_name[name]
        controller = self.controller
        subject = controller.game.level.tile_for(being)
        target = controller.game.level.adjacent_tile(subject, direc)

        # FIXME
        # if we cannot move
        #if not self.being.can_move():
        if False:
            self._send_msg(5, "You cannot move!")
            return False

        # if there is a monster and we can fight
        elif target.being and being.can_melee():
            return controller.melee(subject, target, direc)

        # else try to move to the square
        else:
            ok = controller.move(subject, target)
            if ok:
                #self.examine_tile()
                pass
            return ok

    @register_command('move', 'move west', 'h')
    def move_west(self): return self.__move(self.being, 'west')
    @register_command('move', 'move east', 'l')
    def move_east(self): return self.__move(self.being, 'east')
    @register_command('move', 'move south', 'j')
    def move_south(self): return self.__move(self.being, 'south')
    @register_command('move', 'move north', 'k')
    def move_north(self): return self.__move(self.being, 'north')
    @register_command('move', 'move northwest', 'y')
    def move_northwest(self): return self.__move(self.being, 'northwest')
    @register_command('move', 'move northeast', 'u')
    def move_northeast(self): return self.__move(self.being, 'northeast')
    @register_command('move', 'move southwest', 'b')
    def move_southwest(self): return self.__move(self.being, 'southwest')
    @register_command('move', 'move southeast', 'n')
    def move_southeast(self): return self.__move(self.being, 'southeast')

    @register_command('move', 'move up', '<')
    def move_up(self):
        if not self.being.can_move():
            self._send_msg(5, "You cannot move!")
            return False
        return self.controller.move_up(self.being)

    @register_command('move', 'move down', '>')
    def move_down(self):
        if not self.being.can_move():
            self._send_msg(5, "You cannot move!")
            return False
        return self.controller.move_down(self.being)

class Melee(Action):
    def melee(self, target):
        being = self.being
        subject = self.controller.game.level.tile_for(being)
        direc = subject.direction(target)
        return self.controller.melee(subject, target, direc)
            
class Acquire(Action):

    __signals__ = [
        Signal('inventory_requested', ('inventory',)),
    ]
    
    @register_command('action', 'pickup item', 'g')
    def pickup_item(self):
        ok = self.controller.pickup_item(self.being)
        return ok

    @register_command('action', 'drop item', 'd')
    def drop_item(self):
        if not self.being.inventory:
            self._send_msg(5, "You have no items in your inventory.")
            return False
        ok = self.controller.drop_item(self.being)
        return ok

    @register_command('action', 'view inventory', 'i')
    def view_inventory(self):
        self.events['inventory_requested'].emit(self.being.inventory.view())
        return True


class Examine(Action):

    __signals__ = [
        Signal('tile_requested', ('tile',)),
    ]

    @register_command('info', 'examine tile', 'x')
    def examine_tile(self):
        #FIXME
        tile = self.being.tile
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
        game = self.controller.game
        try:
            being = game.create_being_by(self.being, species.strip())
        except AttrReaderError:
            self._send_msg(7, "No such spieces {} exists.".format(repr(species)))
            return False
        if not being:
            self._send_msg(7, "Could not create spieces {}.".format(species))
        else:
            self._send_msg(5, "Created spieces {}.".format(species))
            tile = game.level.tile_for(being)
            self.controller.events['being_became_visible'].emit(tile.view(game.player))
        return being is not None


    @register_command('wizard', 'create item', 'ctrl+i')
    def create_item(self):
        self.events['answer_requested'].emit('Create what item?', self._on_create_item)
        return False

    def _on_create_item(self, item_name):
        game = self.controller.game
        try:
            item = game.create_item_by(self.being, item_name.strip())
        except AttrReaderError:
            self._send_msg(7, "No such item {} exists.".format(repr(item_name)))
            return False
        if not item:
            self._send_msg(7, "Could not create item {}.".format(item_name))
        else:
            self._send_msg(5, "Created item {}.".format(item))
            tile = game.level.tile_for(self.being)
            self.controller.events['tile_inventory_changed'].emit(tile.idx, tile.inventory.view())
        return item is not None
    


class Use(Action):

    __signals__ = [
        Signal('usable_requested', ('question', 'usables', 'callback')),
        Signal('item_direction_requested', ('question', 'index', 'callback')),
        Signal('usable_direction_requested', ('question', 'usables', 'callback')),
        Signal('remove_usable_requested', ('using', 'callback')),
        Signal('using_requested', ('using',)),
    ]

    @register_command('info', 'view equipment', 'e')
    def view_using(self):

        items = self.being.using.items
        self.events['using_requested'].emit(items)
        return True

    @register_command('action', 'wear/wield item', 'w')
    def wear_item(self):

        items = self.being.using.could_use(self.being.inventory)
        if not items:
            self._send_msg(5, "You have nothing you can wear or use.")
            return False

        question = 'Wear or wield what item?'
        self.events['usable_requested'].emit(question, [(i.view()) for i in items], self._use_item)
        return False

    @register_command('action', 'quaff a potion', 'q')
    def quaff_potion(self):
        items = self.being.inventory.by_klass_name('potion')
        if not items:
            self._send_msg(5, "You have nothing you can quaff.")
            return False

        question = 'Quaff what potion?'
        self.events['usable_requested'].emit(question, [(i.view()) for i in items], self._quaff)
        return False

    def _quaff(self, index):
        potion = self.being.inventory.by_klass_name('potion')[index]
        return self.controller.quaff(self.being, potion)

    @register_command('action', 'read a scroll', 'r')
    def read_scroll(self):
        items = self.being.inventory.by_klass_name('scroll')
        if not items:
            self._send_msg(5, "You have nothing you can read.")
            return False

        question = 'Read what scroll?'
        self.events['usable_requested'].emit(question, [(i.view()) for i in items], self._read)
        return False

    def _read(self, index):
        scroll = self.being.inventory.by_klass_name('scroll')[index]
        return self.controller.read(self.being, scroll)

    @register_command('action', 'zap a wand', 'z')
    def zap_wand(self):
        items = self.being.inventory.by_klass_name('wand')
        if not items:
            self._send_msg(5, "You have nothing you can zap.")
            return False

        question = 'Zap what wand?'
        self.events['usable_requested'].emit(question, [(i.view()) for i in items], self._zap)
        return False

    def _zap(self, index):
        wand = self.being.inventory.by_klass_name('wand')[index]
        if wand.charges < 1:
            self._send_msg(5, "The wand has no charges.")
            return False

        question = 'Zap {} what direction?'.format(wand)
        self.events['item_direction_requested'].emit(question, index, self._zap_direction)
        return False

    def _zap_direction(self, index, direction):
        wand = self.being.inventory.by_klass_name('wand')[index]
        return self.controller.zap(self.being, wand, direction)

    #XXX index may not be stable if inventory is changable across calls
    def _use_item(self, index):

        item = self.being.using.could_use(self._being.inventory)[index]

        ok = self.being.using._add_item(item)
        if not ok:
            self._send_msg(5, self.being, "You cannot wear or use {}.".format(item))
            return False

        self.controller.turn_done(self.being)
        self._send_msg(5, "You are now wearing {}.".format(item))
        return True

    @register_command('action', 'stop using item', 't')
    def remove_using(self):

        using = self.being.using.in_use
        if not using:
            self._send_msg(5, "You have nothing you can take off or stop using.")
            return False
        self.events['remove_usable_requested'].emit(using, self._remove_using)
        return False

    #XXX index may not be stable if inventory is changable across calls
    def _remove_using(self, index):

        item = self.being.using._get_item(index)
        ok = self.being.using._remove_item(item)
        if not ok:
            self._send_msg(5, "You cannot stop using {}.".format(item))
            return False
        self.controller.turn_done(self.being)
        self._send_msg(5, "You took off {}.".format(item))
        return True


registered_actions_types = [Move, Acquire, Use, Examine, Melee, Wizard]


