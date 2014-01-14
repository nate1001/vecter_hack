
from random import choice

from model.util import SumOfDiceDist
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
        m = 'apply_' + (self.method or '')
        if self.method and not getattr(self, m):
            raise ValueError("{} requires method {}.".format(self, m))

    def view(self):
        return Spell.View(self)

    def apply(self, controller, tile):
        method = getattr(self, 'apply_' + self.method)
        return method(controller, tile)

    def set_condition(self, tile, name):
        time = self.dice.roll()
        tile.being.condition.set_timed_condition(name, time)
        return True

    def apply_healing(self, controller, tile):

        being = tile.being
        if not being:
            return False

        add = self.dice.roll()
        if being.stats.hit_points + add > being.stats.max_hit_points:
            being.stats.max_hit_points += 1
        being.stats.hit_points += add
        being.condition.clear_condition('blind')

        controller._send_msg(5, being, 
            "You feel better.", 
            "{} looks better.".format(being.name))
        return True

    def apply_sleep(self, controller, tile):
        if not tile.being:
            return False
        return self.set_condition(tile, 'asleep')

    def apply_lightning_blind(self, controller, tile):
        if tile.being:
            return self.set_condition(tile, 'blind')
        return False

    def apply_teleportation(self, controller, tile):
        
        if not tile.being:
            return False

        tiles = [t for t in controller.game.level.values() if not t.being and t.tiletype.is_open]
        if not tiles:
            return False
        target = choice(tiles)
        subject = controller.game.level.tile_for(tile.being)
        controller.game.level.move_being(subject, target)
        controller.events['being_teleported'].emit(subject.idx, target.idx, target.being.guid)
        controller.events['being_became_visible'].emit(target.view(controller.game.player))
        return True


registered_spells = {}
for item in  AttrReader.items_from_klass(Spell):
    registered_spells[item.name] = item

