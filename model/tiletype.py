
from attr_reader import AttrConfig
from util import get_article

class TileTypeCategory(AttrConfig):

    attrs = (
        ('is_open', 'boolean'),
        ('color', 'qtcolor'),
        ('background', 'qtcolor'),
        ('zval', 'int'),
        ('features', 'textlist'),
    )

class TileType(AttrConfig):
    '''The type of a tile such as a floor or a wall.'''

    attrs = (
        ('ascii', 'text'),
        ('category', 'text'),
        ('desc', 'text'),
        ('bounce', 'text', True),
    )

    def __init__(self, name):
        super(TileType, self).__init__(name)

        category = TileTypeCategory(self.category)
        self.is_open = category.is_open
        self.color = category.color
        self.background = category.background
        self.zval = category.zval
        self.features = category.features
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

