
from util import get_article
from attr_reader import AttrConfig
from equipment import Inventory, Light

class TileTypeCategory(AttrConfig):

    attrs = (
        ('is_open', 'boolean'),
        ('color', 'qtcolor'),
        ('background', 'qtcolor'),
        ('zval', 'int'),
        ('parts', 'textlist'),
    )

class TileType(AttrConfig):
    '''The type of a tile such as a floor or a wall.'''

    attrs = (
        ('ascii', 'text'),
        ('category', 'text'),
        ('desc', 'text'),
    )

    def __init__(self, name):
        super(TileType, self).__init__(name)

        category = TileTypeCategory(self.category)
        self.is_open = category.is_open
        self.color = category.color
        self.background = category.background
        self.zval = category.zval
        self.parts = category.parts
        self.kind = category.name

    @property
    def char(self):
        #FIXME: nasty hack. Does config parser truley not have a an escape character?!
        if self.ascii == '<space>':
           return ' '
        return self.ascii

    def __repr__(self):
        return "<TileType {}>".format(self.ascii)

    def __str__(self):
        return "{} {}".format(get_article(self.name), self.name)



class Tile(object):
    '''A container of Beings and Equipment.'''

    class View(object):
        
        def __init__(self, tile, player):

            self.x = tile.x
            self.y = tile.y
            self.idx = tile.idx
            self.neighbors = {}
            self.direction = None

            tiletype = player.vision.get_tiletype(tile)
            inventory = player.vision.get_inventory(tile)
            being = player.vision.get_being(tile)
            self.state = player.vision.get_state(tile)

            self.category = 'dungeon'

            self.parts = tiletype.parts
            self.name = tiletype.name
            self.char = tiletype.char
            self.color = tiletype.color
            self.background = tiletype.background
            self.zval = tiletype.zval
            self.is_open = tiletype.is_open
            self.kind = tiletype.kind

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
        return "<Tile {},{} {} {} >".format(self.x, self.y, 
            self.being and repr(self.being.char) or '', 
            self.inventory and repr(self.inventory.char) or '')

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

    def view(self, player):
        return self.__class__.View(self, player)

    def get_offset(self, other):
        '''Return the offset from another tile.'''
        return (other.x - self.x, other.y - self.y)

    def ontop(self, nobeing=False):
        '''Return the object that can be seen from a birds eye view.'''
        if self.being and nobeing == False:
            return self.being
        elif self.inventory:
            return self.inventory
        else:
            return self

