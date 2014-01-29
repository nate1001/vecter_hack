
from random import choice

from messenger import Messenger, Signal, register_command
from model.attr_reader import AttrReaderError

from config import logger, direction_by_name

class Action(Messenger):

    __signals__ = [
        Signal('action_happened_to_player', ('log level', 'msg',)),
        Signal('direction_requested', ('question', 'callback')),
        Signal('item_direction_requested', ('question', 'index', 'callback')),
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

    def dispatch_command(self, name):
        
        ok = getattr(self, name)()
        if ok:
            self.being.move_made()
        return ok


    @register_command('move', 'do nothing', '.')
    def do_nothing(self):

        logger.debug('{} do nothing for a turn.'.format(self.being.words.You))
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

        #FIXME this should go to controller
        if being.has_condition('confused'):
            tiles = [t for t in controller.game.level.adjacent_tiles(subject) if t.tiletype.is_open]
            if not tiles:
                return False
            target = choice(tiles)
        else:
            target = controller.game.level.adjacent_tile(subject, direc)

        # FIXME
        # if we cannot move
        #if not self.being.can_move():
        if False:
            logger.msg_impossible('{You} cannot move!'.format(**subject.being.words_dict))
            return False

        # if there is a monster and we can fight
        elif target.being and being.species.attacks:
            return controller.attack(subject, target, direc)

        # else try to move to the square
        else:
            ok = controller.move(subject, target)
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
        if not self.being.can_move:
            logger.msg_impossible('{You} cannot move!'.format(**self.being.words_dict))
            return False
        return self.controller.move_up(self.being)

    @register_command('move', 'move down', '>')
    def move_down(self):
        if not self.being.can_move:
            logger.msg_impossible('{You} cannot move!'.format(**self.being.words_dict))
            return False
        return self.controller.move_down(self.being)

class Melee(Action):
    def melee(self, target):
        being = self.being
        subject = self.controller.game.level.tile_for(being)
        direc = subject.direction(target)
        return self.controller.attack(subject, target, direc)
            
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
            logger.msg_impossible('{You} have no items in your inventory!'.format(**self.being.words_dict))
            return False
        ok = self.controller.drop_item(self.being)
        return ok

    @register_command('action', 'view inventory', 'i')
    def view_inventory(self):
        self.events['inventory_requested'].emit(self.being.inventory.view())
        return True

class Examine(Action):
    __signals__ = [
    ]
    @register_command('info', 'examine tile', ':')
    def examine_tile(self):
        tile = self.controller.game.level.tile_for(self.being)
        thing = tile.ontop(nobeing=True)
        logger.msg_info("{You} are standing on {}.".format(thing.description, **self.being.words_dict))
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
            logger.msg_impossible("No such spieces {} exists.".format(repr(species)))
            return False
        if not being:
            logger.msg_impossible("Could not create spieces {}.".format(species))
        else:
            logger.msg_info("Created spieces {}.".format(species))
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
            logger.msg_impossible("No such item {} exists.".format(repr(item_name)))
            return False
        if not item:
            logger.msg_impossible("Could not create item {}.".format(item_name))
        else:
            logger.msg_info("Created item {}.".format(item))
            tile = game.level.tile_for(self.being)
            self.controller.events['tile_inventory_changed'].emit(tile.idx, tile.inventory.view())
        return item is not None
    

class Grab(Action):

    __signals__ = (
    )

    @register_command('action', 'open something', 'o')
    def open(self):
        question = 'Open in what direction?'
        self.events['direction_requested'].emit(question, self._open)
        return False

    def _open(self, direction):
        subject = self.controller.game.level.tile_for(self.being)
        target = self.controller.game.level.adjacent_tile(subject, direction)
        return self.controller.open(self.being, target)

    @register_command('action', 'close something', 'c')
    def close(self):
        question = 'Close in what direction?'
        self.events['direction_requested'].emit(question, self._close)
        return False

    def _close(self, direction):
        subject = self.controller.game.level.tile_for(self.being)
        target = self.controller.game.level.adjacent_tile(subject, direction)
        return self.controller.close(self.being, target)


class Kick(Action):
    __signals__ = (
    )
    @register_command('action', 'kick something', 'alt+d')
    def kick(self):
        question = 'Kick in what direction?'
        self.events['direction_requested'].emit(question, self._kick)
        return False

    def _kick(self, direction):
        subject = self.controller.game.level.tile_for(self.being)
        target = self.controller.game.level.adjacent_tile(subject, direction)
        return self.controller.kick(subject, target, direction)


class Use(Action):

    __signals__ = [
        Signal('usable_requested', ('question', 'usables', 'callback')),
        Signal('remove_usable_requested', ('using', 'callback')),
        Signal('using_requested', ('using',)),
    ]

    @register_command('info', 'view equipment', 'e')
    def view_using(self):
        self.events['using_requested'].emit(self.being.inventory.wearing_view())
        return True

    @register_command('action', 'quaff a potion', 'q')
    def quaff_potion(self):
        items = self.being.inventory.by_klass_name('potion')
        if not items:
            logger.msg_impossible("{You} have nothing you can quaff.".format(**self.being.words_dict))
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
            logger.msg_impossible("{You} have nothing you can read.".format(**self.being.words_dict))
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
            logger.msg_impossible("{You} have nothing to zap.".format(**self.being.words_dict))
            return False

        question = 'Zap what wand?'
        self.events['usable_requested'].emit(question, [(i.view()) for i in items], self._zap)
        return False

    def _zap(self, index):
        wand = self.being.inventory.by_klass_name('wand')[index]
        if wand.charges < 1:
            logger.msg_impossible("The wand has no charges.")
            return False

        if wand.kind.directional:
            question = 'What direction?'
            self.events['item_direction_requested'].emit(question, index, self._zap_direction)
            return False
        else:
            return self.controller.zap(self.being, wand, None)

    def _zap_direction(self, index, direction):
        wand = self.being.inventory.by_klass_name('wand')[index]
        return self.controller.zap(self.being, wand, direction)


    @register_command('action', 'wear/wield item', 'w')
    def wear_item(self):

        items = self.being.inventory.could_wear()
        if not items:
            logger.msg_impossible("{You} have nothing you can wear or use.".format(**self.being.words_dict))
            return False
        question = 'Wear or wield what item?'
        self.events['usable_requested'].emit(question, [(i.view()) for i in items], self._wear)
        return False


    #XXX index may not be stable if inventory is changable across calls
    def _wear(self, index):

        item = self.being.inventory.could_wear()[index]
        self.being.inventory.wear(item)
        self.controller.turn_done(self.being)
        logger.msg_info("{You} are now wearing {}.".format(item, **self.being.words_dict))
        return True

    @register_command('action', 'stop using item', 't')
    def remove_using(self):

        wearing = self.being.inventory.wearing
        if not wearing:
            logger.msg_impossible("You have nothing you can take off or stop using.")
            return False
        self.events['remove_usable_requested'].emit([i.view() for i in wearing], self._remove_using)
        return False

    #XXX index may not be stable if inventory is changable across calls
    def _remove_using(self, index):

        item = self.being.inventory.wearing[index]
        self.being.inventory.take_off(item)
        self.controller.turn_done(self.being)
        logger.msg_info("{You} took off {}.".format(item, **self.being.words_dict))
        return True


registered_actions_types = [Move, Acquire, Use, Examine, Melee, Wizard]


