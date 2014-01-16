
from attr_reader import AttrConfig, AttrReader
from util import get_article

class TileTypeCategory(AttrConfig):

    attrs = (
        ('is_open', 'boolean'),
        ('color', 'qtcolor'),
        ('background', 'qtcolor'),
        ('zval', 'int'),
        ('features', 'textlist'),
        ('desc', 'text', True),
        ('ascii', 'text', True),
        ('is_door', 'boolean', True),
        ('is_open', 'boolean', True),
        ('is_locked', 'boolean', True),
        ('is_broken', 'boolean', True),
    )

    def __repr__(self):
        return '<TileTypeCategory {}>'.format(repr(self.name))

    @classmethod
    def get_door_type(cls, is_broken, is_open, is_locked):
        kinds = [
            d for d in AttrReader.items_from_klass(cls) 
            if d.is_door
            and bool(d.is_broken) == is_broken
            and bool(d.is_open) == is_open
            and bool(d.is_locked) == is_locked
        ]
        if len(kinds) != 1:
            raise ValueError(kinds)
        return kinds[0]


class TileType(AttrConfig):
    '''The type of a tile such as a floor or a wall.'''

    attrs = (
        ('category', 'text'),
        ('ascii', 'text', True),
        ('desc', 'text', True),
        ('bounce', 'text', True),
        ('direction', 'text', True),
    )
    @classmethod
    def get_door_type(cls, direction, is_broken, is_open, is_locked):

        kind = TileTypeCategory.get_door_type(is_broken, is_open, is_locked)
        types = [
            d for d in AttrReader.items_from_klass(cls) 
            if d.category == kind.name
            and d.direction == direction
        ]
        if len(types) != 1:
            raise ValueError(types)
        return types[0]
        
    def __init__(self, name):
        super(TileType, self).__init__(name)

        category = TileTypeCategory(self.category)
        self.is_open = category.is_open
        self.color = category.color
        self.background = category.background
        self.zval = category.zval
        self.features = category.features
        self.kind = category.name

        self.is_door = category.is_door
        self.is_locked = category.is_locked
        self.is_open = category.is_open
        self.is_broken = category.is_broken

        self.ascii = category.ascii or self.ascii
        if not self.ascii:
            raise ValueError('ascii not set for {}'.format(self))
        self.desc = category.desc or self.desc
        if not self.desc:
            raise ValueError('desc not set for {}'.format(self))

    @property
    def char(self):
        #FIXME: nasty hack. Does config parser truley not have a an escape character?!
        if self.ascii == '<space>':
           return ' '
        return self.ascii

    def __repr__(self):
        return "<TileType {}>".format(repr(self.name))

    def __str__(self):
        return "{} {}".format(get_article(self.name), self.name)

