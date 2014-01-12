
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
    @classmethod
    def apply(cls, being, tiles):
        raise NotImplementedError

class AttackSpell(Spell):
    @classmethod
    def apply(cls, being, tiles, arena):
        for tile in tiles:
            if tile.being:
                arena.spell_attack(tile.being, cls.name, cls.dice)

class FireSpell(AttackSpell):
    name = 'fire'
    dice = SumOfDiceDist(4, 8)
    
registered_spells = {
    'fire': FireSpell
}

