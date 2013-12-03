
from collections import OrderedDict

from attr_reader import AttrConfig
from action import Action, registered_actions_types
from equipment import Inventory
from messenger import Messenger, Signal, Event, register_command 
from tile import TileType

from pyroguelike.grid import Flags


class Genus(AttrConfig):
    attrs = (
        ('ascii', 'text'),
        ('actions', 'text'),
        ('wearable', 'text'),
        ('intrinsics', 'text'),
        ('infravision', 'int'),
        ('vision', 'int'),
    )
    '''Factory class for grouping common Species attributes.'''

    def __init__(self, name):
        #TODO should make a type for lists in config
        super(Genus, self).__init__(name)
        self.actions = [a.strip() for a in self.actions.split(',')]
        self.instrinsics =[a.strip() for a in self.intrinsics.split(',')]

        for action in self.actions:
            if action.lower() not in [a.__name__.lower() for a in registered_actions_types]:
                raise ValueError("Genus %s does not have a registered action type for %s" %
                     (repr(name), repr(action.lower())) )

class Species(AttrConfig):
    attrs = (
        ('genus', 'text'),
        ('hit points', 'int'),
        ('color', 'qtcolor'),
        ('base ac', 'int'),
        ('base attack', 'dice'),
    )
    ''' Factory class for initializing monsters.'''

    def __init__(self, name):
        super(Species, self).__init__(name)
        self.genus = Genus(self.genus)

    def __repr__(self):
        return "<Species {}>".format(repr(self.name))

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return not self == other

    @property
    def value(self):
        return self.hit_points + self.base_ac + self.base_attack.mean

class Vision(object):
    
    def __init__(self):
        
        self._levels = []
        self._current = None
        self._wizard = False

    def append_level(self, size):
        self._levels.append(_Vision(size, self._wizard))
        self._current = self._levels[-1]

    @property
    def wizard(self):
        return self._wizard

    @wizard.setter
    def wizard(self, is_wizard):
        for vision in self._levels:
            vision._wizard = is_wizard

    def set_see(self, see): self._current.set_see(see)
    def set_infravision(self, infravision): self._current.set_infravision(infravsion)
    def can_see(self, tile): return self._current.can_see(tile)
    def can_see_other(self, other): return self._current.can_see_other(other)
    def can_sense_other(self, other): return self._current.can_sense_other(other)

    def get_being(self, tile): return self._current.get_being(tile)
    def get_tiletype(self, tile): return self._current.get_tiletype(tile)
    def get_inventory(self, tile): return self._current.get_inventory(tile)
    def get_state(self, tile): return self._current.get_state(tile)
    def has_changed(self, tile): return self._current.has_changed(tile)

    
class _Vision(object):
    
    #TODO impliment memorized object on tile in case it moves
    
    states = (
        'see',
        'memorized',
        'unknown',
    )
    unknown = TileType('unknown')
    
    def __init__(self, size, is_wizard):

        self._see = Flags(size)
        self._last_see = Flags(size)
        self._see_changed = Flags(size)
        self._infravision = Flags(size)
        self._memorized = Flags(size)
        self._wizard = is_wizard
        
    def set_see(self, see):
        self._memorized = self._memorized | see
        self._last_see = self._see
        self._see = see
        self._see_changed = see ^ self._last_see

    def set_infravision(self, infravision):
        self._infravision = infravision

    def can_see_other(self, other):
        return self._see[other.tile.idx]

    def can_see(self, tile):
        return self._see[tile.idx]

    def can_sense_other(self, other):
        return self._infravision[other.tile.idx]

    def has_changed(self, tile):
        return self._see_changed[tile.idx]
        
    def get_state(self, tile):
        idx = tile.idx
        if self._see[idx] or self._wizard:
            return 'see'
        if self._memorized[idx]:
            return 'memorized'
        else:
            return 'unknown'

    def get_tiletype(self, tile):

        state = self.get_state(tile)
        if self._wizard or state == 'see':
            return tile.tiletype
        elif state == 'memorized':
            return tile.tiletype
        elif state == 'unknown':
            return self.unknown
        else:
            raise ValueError()

    def get_being(self, tile):

        state = self.get_state(tile)
        infravision = self._infravision[tile.idx]

        if self._wizard or state == 'see':
            return tile.being
        elif infravision:
            return tile.being
        elif state == 'memorized':
            return None
        elif state == 'unknown':
            return None
        else:
            raise ValueError()

    def get_inventory(self, tile):

        state = self.get_state(tile)
        if self._wizard or state == 'see':
            return tile.inventory
        elif state == 'memorized':
            return None
        elif state == 'unknown':
            return None
        else:
            raise ValueError()



class Stats(Messenger):
    '''Holds the value of Being attribues such as hit points.'''

    __signals__ = [
        Signal('stats_updated', ('stats',)),
    ]

    def __init__(self, species):

        super(Stats, self).__init__()

        self._items = OrderedDict()
        self._items['hit_points'] = species.hit_points
        self._items['ac'] = species.base_ac
        self._items['melee'] = species.base_attack
        self._items['infravision'] = species.genus.infravision
        self._items['vision'] = species.genus.vision
        
        self._base = OrderedDict()
        self._base['melee'] = species.base_attack
        self._base['inravision'] = species.genus.infravision
        self._base['vision'] = species.genus.vision
        
    @property
    def items(self):
        return self._items.items()
    
    @property
    def hit_points(self): return self._items['hit_points']
    @property
    def ac(self): return self._items['ac']
    @property
    def melee(self): return self._items['melee']
    @property
    def infravision(self): return self._items['infravision']
    @property
    def vision(self): return self._items['vision']
    
    def _change_stat(self, key, offset):
        self._items[key] += offset
        self.events['stats_updated'].emit(self.items)
    
    def _wear_item(self, item):
        for key in self._items:
            if hasattr(item, key):
                attr = getattr(item, key)
                if type(attr) is int:
                    self._items[key] += attr
                else:
                    self._items[key] = attr
        self.events['stats_updated'].emit(self.items)

    def _remove_item(self, item):
        for key in self._items:
            if hasattr(item, key):
                attr = getattr(item, key)
                if type(attr) is int:
                    self._items[key] -= attr
                else:
                    self._items[key] = self._base[key]
        self.events['stats_updated'].emit(self.items)
        

class Condition(Messenger):
    __signals__ = [
        Signal('condition_updated', ('new condition',)),
    ]

    def __init__(self, being):

        super(Condition,  self).__init__()

        self._can_see = being.species.genus.vision > 0

        self._items = OrderedDict()
        self._items['asleep'] = True
        self._items['blind'] = None

        self.blind = False


    @property
    def asleep(self): return self._items['asleep']
    @asleep.setter
    def asleep(self, is_asleep):
        self._items['asleep'] = is_asleep

    @property
    def blind(self): return self._items['blind']
    @blind.setter
    def blind(self, is_blind):
        self._items['blind'] = is_blind




class Wearing(Messenger):

    __signals__ = [
        Signal('wearing_updated', ('items',)),
    ]
    
    def __init__(self, stats):
        super(Wearing,  self).__init__()
        self._items = OrderedDict()
        self._stats = stats

    @classmethod
    def from_being(cls, being):
        '''Create wearing class that has only has slots allowed by the genus of the species.'''
        
        wearing = Wearing(being.stats)
        for wearable in [a.strip() for a in being.species.genus.wearable.split(',')]:
            wearing._items[wearable] = None
            setattr(wearing, wearable, None)
        return wearing

    @property
    def items(self):
        '''Items that are being worn and slots that could be worn.'''
        return self._get_items()

    def _get_items(self, show_blank=True):
        strings = []
        for key, value in self._items.iteritems():
            if not value:
                if show_blank:
                    strings.append((str(key), ''))
            else:
                strings.append((key, value.string(worninfo=False)))
        return strings

    def set_item(self, stack):
        if stack.item.wearable not in self._items.keys():
            return False
        old = self._items[stack.item.wearable]
        if old:
            old.setWearing(False)
        self._items[stack.item.wearable] = stack
        stack.setWearing(True)
        self._stats._wear_item(stack.item)
        self.events['wearing_updated'].emit(self.items)
        return True

    def remove_item(self, text):

        #XXX make sure text repr is unique or this will fail!
        ok = False
        for idx, label in enumerate(self.items):
            if label == text:
                ok = True
                break
            
        if not ok:
            return False

        i = 0
        for key in self._items:
            if idx == i:
                break
            i += 1

        self._items[key].setWearing(False)
        self._stats._remove_item(self._items[key].item)
        self._items[key] = None
        self.events['wearing_updated'].emit(self.items)
        return True
    
    def _possible(self, inventory):
        '''Items that may be worn (could replace what is already being worn.)'''
        wearables = []
        for stack in inventory:
            if stack.item.wearable in self._items.keys():
                wearables.append(stack)
        return wearables

        

class PlayerView(Messenger):

    def __init__(self, player):

        super(PlayerView, self).__init__()
        
        self.name = player.species.name
        self.color = player.species.color
        self.char = player.species.genus
        self._stats = player.stats
        self._inventory = player.inventory
        self._wearing = player.wearing
        self._player_id = id(player)
        self._actions = player.actions
        self._vision = player.vision

        # expose events to this class
        events = (
            player.actions.events.values()
            + player.stats.events.values()
            + player.inventory.events.values()
            + player.wearing.events.values()
        )
        for event in events:
            self.events[event.name] = event

    @property
    def vision(self):
        return self._vision

    @property
    def stats(self):
        return self._stats

    @property
    def inventory(self):
        return self._inventory

    @property
    def wearing(self):
        return self._wearing

    def dispatch_command(self, name):
        
        method = getattr(self._actions, name)
        status = method()

        # has to return something (False - action failed / True action succeeded)
        if status is None:
            raise ValueError("callback {} returned None.".format(name))

        # else its information
        else:
            return status

    def emit_info(self):
        self.events['inventory_updated'].emit(self.inventory.items)
        self.events['wearing_updated'].emit(self._wearing.items)
        self.events['stats_updated'].emit(self.stats.items)


class Being(object):
    '''The instance of a Species.'''

    guid = 0

    class View(object):
        
        def __init__(self, being):

            self.is_player = being.is_player
            self.color = being.species.color
            self.char = being.species.genus.ascii
            self.category = being.species.genus.name
            self.name = being.species.name
            self.guid = being.guid

        def __str__(self):
            return '<Being.View {}>'.format(self.name)

    def __init__(self, controller, species, is_player=False):
        
        Being.guid += 1 #FIXME
        
        self.guid = Being.guid
        self.species = species
        
        self.controller = controller
        self.is_player = is_player
        self.stats = Stats(species)
        self.inventory = Inventory()
        self.wearing = Wearing.from_being(self)
        self.condition = Condition(self)
        self.vision = Vision()

        self.actions = Action.from_being(self) 
        self.tile = None

    def __repr__(self):
        return "<Being {}{}>".format(self, self.tile and ' on {},{}'.format(self.tile.x, self.tile.y) or '(no tile)')

    def __str__(self):
        return '#{} {}'.format(self.guid, self.species.name)

    @property
    def is_dead(self):
        return self.stats.hit_points < 0

    @property
    def name(self):
        return self.species.name

    @property
    def color(self):
        return self.species.color

    @property
    def char(self):
        return self.species.genus.ascii

    @property
    def can_see(self):
        return not self.condition.blind

    def new_level(self, size):
        self.vision.append_level(size)

    def view(self):
        return self.__class__.View(self)

    #FIXME
    def can_move(self):
        return True

    #FIXME
    def can_melee(self):
        return True

          

if __name__ == '__main__':

     human = Species('orc')
     being = Being(None, human)
     print dir(being.actions)


