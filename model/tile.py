
from equipment import Inventory, Light
from config import direction_by_abr


class Tile(object):
    '''A container of Beings and Equipment.'''

    class View(object):
        
        def __init__(self, tile, player):

            self.x = tile.x
            self.y = tile.y
            self.idx = tile.idx
            self.neighbors = {}

            tiletype = player.vision.get_tiletype(tile)
            inventory = player.vision.get_inventory(tile)
            being = player.vision.get_being(tile)
            self.state = player.vision.get_state(tile)

            self.category = 'dungeon'

            self.features = tiletype.features
            self.name = tiletype.name
            self.char = tiletype.char
            self.color = tiletype.color
            self.background = tiletype.background
            self.zval = tiletype.zval
            self.is_open = tiletype.is_open
            self.kind = tiletype.kind
            self.direction = tiletype.direction

            self.inventory = inventory.view() if inventory is not None else Inventory().view()
            self.being = being.view() if being else None

        def __repr__(self):
            return '<Tile.View ({},{})>'.format(self.x, self.y)


    def distance(self, other):
        x1, y1 = self.x, self.y
        x2, y2 = other.x, other.y
        return ((x2 - x1)**2 + (y2 - y1)**2)**.5

    def __init__(self, tiletype, x, y):

        self.tiletype = tiletype
        self.x = x 
        self.y = y
        self.inventory = Inventory()
        self.being = None
        self.portal = None

        self._permalit = False
        self._lit = False

    def __repr__(self):
        return "<Tile {},{} {} {}>".format(self.x, self.y, 
            self.being and repr(self.being.char) or '', 
            self.inventory and repr(self.inventory.char) or '')

    def __str__(self):
        return '({},{})'.format(self.x, self.y)

    @property
    def description(self):
        return self.tiletype.desc

    @property
    def idx(self): return (self.x, self.y)

    @property
    def char(self): return self.tiletype.char

    @property
    def color(self):
        return self.tiletype.color

    @property
    def lit(self):
        return self._permalit or self._lit

    @property
    def light(self):

        lights = []
        if self.being:
            lights.extend(self.being.inventory.get_by_class(Light))
        lights.extend(self.inventory.get_by_class(Light))

        lights = sorted([(es.item.radius, es.item) for es in lights])
        if lights:
            return lights[-1][1]
        return None

    @property
    def openable(self): 
        return (
            self.tiletype.is_door 
            and not self.tiletype.is_open 
            and not self.tiletype.is_locked
        )
    @property
    def closable(self): 
        return (
            self.tiletype.is_door 
            and self.tiletype.is_open
            and not self.tiletype.is_broken
        )
    @property
    def lockable(self): 
        return (
            self.tiletype.is_door 
            and not self.tiletype.is_open 
            and not self.tiletype.is_locked
        )
    @property
    def unlockable(self): return (
        self.tiletype.is_door 
        and self.tiletype.is_locked 
    )
    @property
    def breakable(self): return (
        self.tiletype.is_door 
        and not self.tiletype.is_open 
        and not self.tiletype.is_broken
    )
    @property
    def fixable(self): return (
        self.tiletype.is_door 
        and self.tiletype.is_broken
    )

    def view(self, player):
        return self.__class__.View(self, player)


    def direction(self, other):
        offset = (other.x - self.x, other.y - self.y)
        for d in direction_by_abr.values():
            if d.offset == offset:
                return d
        raise ValueError(other)

    def ontop(self, nobeing=False):
        '''Return the object that can be seen from a birds eye view.'''
        if self.being and nobeing == False:
            return self.being
        elif self.inventory:
            return self.inventory
        else:
            return self

