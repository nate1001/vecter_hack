
from random import choice

from attack import CombatArena
from model.util import SumOfDiceDist

'''
ATTACKS
=======
magic missile         :  150   7    50  :  8   RAY
cold                  :  175   7    40  :  8   RAY
fire                  :  175   7    40  :  8   RAY
lightning             :  175   7    40  :  8   RAY

death                 :  500   7     5  :  8   RAY
striking              :  150   7    75  :  8   BEAM

CONDITIONS
==========
sleep                 :  175   7    50  :  8   RAY
slow monster          :  150   7    50  :  8   BEAM
speed monster         :  150   7    50  :  8   BEAM
make invisible        :  150   7    45  :  8   BEAM

TILE
====
light                 : $100   7    95  : 15   NODIR
digging               :  150   7    55  :  8   RAY
locking               :  150   7    25  :  8   BEAM
opening               :  150   7    25  :  8   BEAM
secret door detection :  150   7    50  : 15   NODIR

DUNGEON
=======
create monster        :  200   7    45  : 15   NODIR
wishing               :  500   7     5  :  3!  NODIR
enlightenment         :  150   7    15  : 15   NODIR
nothing               :  100   7    25  : 15   BEAM
probing               :  150   7    30  :  8   BEAM
undead turning        :  150   7    50  :  8   BEAM
cancellation          :  200   7    45  :  8   BEAM
polymorph             :  200   7    45  :  8   BEAM
teleportation         :  200   7    45  :  8   BEAM
'''

class Spell(object):
    
    kind = None

    class View(object):
        def __init__(self, spell):
            self.name = spell.name
            self.category = 'spell'

        def __repr__(self):
            return '<Spell.View {}>'.format(self.name)

    def view(self):
        return Spell.View(self)


class AttackSpell(Spell):
    
    kind = 'attack'
    
    def __init__(self, name, damage, conditions):
        self.name = name
        self.damage = damage
        self.conditions = conditions


class HealingSpell(Spell):
    
    def __init__(self, name, dice):
        self.name = name
        self.dice = dice
    
    def apply(self, controller, being):
        add = self.dice.roll()
        if being.stats.hit_points + add > being.stats.max_hit_points:
            being.stats.max_hit_points += 1
        being.stats.hit_points += add
        being.condition.clearCondition('blind')

        controller._send_msg(5, being, 
            "You feel better.", 
            "{} looks better.".format(being.name))
        return True


class ConditionSpell(Spell):
    def __init__(self, name, dice):
        self.name = name
        self.dice = dice

    def apply(self, controller, tile):
        time = self.dice.roll()
        tile.being.condition.setTimedCondition(self.name, time)
        return True


class TeleportSpell(Spell):
    
    def __init__(self, name):
        self.name = name
    
    def apply(self, controller, tile):
        
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

registered_spells = {
    'fire': AttackSpell('fire', SumOfDiceDist(6,6), []),
    'cold': AttackSpell('cold', SumOfDiceDist(6,6), []),
    'magic_missile': AttackSpell('magic missile', SumOfDiceDist(6,2), []),
    'lightning': AttackSpell('lightning', SumOfDiceDist(6,6), ['blind']),
    'striking': AttackSpell('striking', SumOfDiceDist(2,12), []),

    'sleep': ConditionSpell('asleep', SumOfDiceDist(6,21)),

    'healing': HealingSpell('healing', SumOfDiceDist(8,4)),
    'teleportation': TeleportSpell('teleportation'),
}

