
from random import choice
from model.attr_reader import AttrConfig, AttrReader


class Spell(AttrConfig):
    
    attrs = (
        ('color', 'qtcolor', True),
        ('damage', 'dice', True),
        ('method', 'text', True),
        ('dice', 'dice', True),
    )
    
    class View(object):
        def __init__(self, spell):
            self.category = 'spell'
            self.name = spell.name
            self.color = spell.color

        def __repr__(self):
            return '<Spell.View {}>'.format(self.name)

    def __init__(self, name):
        super(Spell, self).__init__(name)
        m = 'on_' + (self.method or '')
        if self.method and not getattr(self, m):
            raise ValueError("{} requires method {}.".format(self, m))

    def view(self):
        return Spell.View(self)

    def handle(self, game, tile):
        method = getattr(self, 'on_' + self.method)
        return method(game, tile)

    def set_condition(self, tile, name):
        time = self.dice.roll()
        tile.being.condition.set_timed_condition(name, time)
        return True

    def on_healing(self, game, tile):

        being = tile.being
        if not being:
            return False

        add = self.dice.roll()
        if being.stats.hit_points + add > being.stats.max_hit_points:
            being.stats.max_hit_points += 1
        being.stats.hit_points += add
        being.condition.clear_condition('blind')
        return True

    def on_sleep(self, game, tile):
        if not tile.being:
            return False
        return self.set_condition(tile, 'asleep')

    def on_lightning_blind(self, game, tile):
        if tile.being:
            return self.set_condition(tile, 'blind')
        return False

    def on_teleportation(self, game, tile):
        
        if not tile.being:
            return False

        tiles = [t for t in game.level.values() if not t.being and t.tiletype.is_open]
        if not tiles:
            return False
        target = choice(tiles)
        subject = game.level.tile_for(tile.being)
        game.level.move_being(subject, target)
        return True

    def on_create_monster(self, game, tile):
        return False


registered_spells = {}
for item in  AttrReader.items_from_klass(Spell):
    registered_spells[item.name] = item

