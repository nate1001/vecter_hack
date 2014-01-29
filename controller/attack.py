
from random import random, randint
from model.util import SumOfDiceDist as Dice
from model.condition import TimedCondition

from config import logger

class CombatArena(object):
    
    hit_dice = Dice(1,20)
    to_hit_base = 10

    def __init__(self, controller):
        self.controller = controller

    def _send_msg(self, msg):
        self.controller.events['action_happened_in_game'].emit(7, False, msg)

    def _take_damage(self, attackee, attacker, damage):

        if attacker:
            logger.ddebug('{ar.You} {ar.inflict} {hp} hit points of damage on {ae.your_self}.'.format(
                ar=attacker.words, ae=attackee.words, hp=damage))
        else:
            logger.ddebug('{hp} hit points of damage is inflected on {ae.your_self}.'.format(ae=attackee.words, hp=damage))
        attackee.hit_points -= damage
        if attackee.is_dead:
            self.controller.die(attackee, attacker)

    def attack(self, attacker, attackee):

        # confusor
        #if attacker.has_condition('confusor'):
        #    attackee.condition.set_condition('confused', Dice(1, 7, modifier=15).roll())

        for attack in attacker.attacks:
            self._attack(attack, attacker, attackee)
        # attacker might have triggered passive attacks  and the tables turn.
        #FIXME some passive attacks like acid trigger even if that attackee died
        if [a for a in attacker.attacks if a.means.triggers_passive and not attackee.is_dead]:
            for attack in attackee.passive:
                self._attack(attack, attackee, attacker)

    def _attack(self, attack, attacker, attackee):
        if attack.means.condition:
            success, msg = self.on_set_condition(attack, attacker, attackee)
        else:
            method = getattr(self, 'on_' + attack.means.name)
            success, msg = method(attack, attacker, attackee)

        if success:
            logger.msg_warn(msg.strip())
        else:
            logger.msg_info(msg.strip())

    def on_set_condition(self, attack, attacker, attackee):
        c = attack.means.condition
        r = c.resisted_by
        if r and attackee.has_condition(r):
            fmt = attack.way.miss
            logger.msg_debug('{You} {} {}, but it failed'.format(attack, attackee, **attacker.words_dict))
            time = 0
        else:
            fmt = attack.way.hit
            time = attack.dice.roll()
            ct = TimedCondition(c.name, time)
            attackee.set_condition(ct)
            logger.msg_debug('{You} {} {} for {} turns'.format(attack, attackee, time, **attacker.words_dict))

        msgd = {
            'ar': attacker.words, 
            'ae': attackee.words,
            'a': attack,
            'time': time,
            'resisted': c.resisted.me if attackee.is_player else c.resisted.she,
            'gained': c.gained,
        }
        return time != 0, fmt.format(**msgd)



    def on_melee(self, attack, attacker, attackee): 

        #XXX  I'm guessing dice dice is set in mons.c on weapon attacks
        #   if the monster had no weapon and then we use the 
        # the weapon dice if we have a weapon. But I have not checked.

        # chance is 1d20
        # if chance is less than hittable then attack works
        # we start in the middle at to_hit_base 
        # then high armor makes the attackee more hittable
        # then the attacker monster level adds to hittableness

        weapon = attack.way.name == 'wields' and attacker.inventory.melee
        hittable = max(1, self.to_hit_base + attackee.ac + attacker.species.level)
        roll = self.hit_dice.roll()
        msgd = {'ar': attacker.words, 'ae': attackee.words, 'melee':weapon}
        msg = attack.way.try_.format(**msgd)
        # if its a hit
        if hittable > roll:

            damage = weapon.dice.roll() if weapon else attack.dice.roll() 

            self._take_damage(attackee, attacker, damage)
            if not attackee.is_dead:
                msg += ' ' + attack.way.hit.format(**msgd)
            else:
                msg = attack.way.kill.format(**msgd)
        else:
            msg += ' ' + attack.way.miss.format(**msgd)
            damage = 0

        logger.msg_debug('{} {} with {} (h:{} r:{} d:{} new hp:{})'.format(
            attacker.words.You, attack, attackee, hittable, roll, damage, attackee.hit_points))
        return damage != 0, msg


    def spell_attack(self, subject, target, spell):

        attackee = target.being
        attacker = subject.being

        if attacker:
            logger.ddebug('{} casting {} on {}.'.format(attacker.words.You_are, spell, attackee.words.your_self))
        else:
            logger.ddebug('{} is cast upon {}.'.format(str(spell).capitalize(), attackee.words.your_self))

        if [c for c in attackee.conditions if c.spell_resistance == spell.name]:
            logger.msg_info('{} resits the {} spell.'.format(attackee.words.You, spell.name))
            self.controller.events['being_spell_resistance'].emit(target.idx, attackee.guid, spell.view())
        else:
            damage = spell.damage.roll()
            logger.msg_debug("The {} spell does {} damage on {}".format(spell.name, damage, attackee))
            self.controller.events['being_spell_damage'].emit(target.idx, attackee.guid, spell.view())
            self._take_damage(attackee, attacker, damage)

        return True

