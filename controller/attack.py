
from random import random, randint
from model.util import SumOfDiceDist as Dice

from config import logger


class CombatArena(object):
    
    def __init__(self, controller):
        self.controller = controller
    

    def melee(self, attacker, attackee):

        game = self.controller.game
        t = self.controller.game.level.tile_for(attacker)
        self._attack(attacker, attackee, None)

    def spell_attack(self, subject, target, spell):

        attackee = target.being
        attacker = subject.being

        if attackee.has_resitance(spell.name):
            logger.debug('The {} resits the {} spell.'.format(attackee, spell.name))
            self.controller.events['being_spell_resistance'].emit(target.idx, attackee.guid, spell.view())
            if self.game.player is attackee:
                self.controller._send_msg(7, attackee, "You aren't hurt!", None)
        else:
            damage = spell.damage.roll()
            logger.debug("The {} spell does {} damage on {}".format(spell.name, damage, attackee))
            self.controller.events['being_spell_damage'].emit(target.idx, attackee.guid, spell.view())
            self._take_damage(attackee, attacker, damage)
        return True

    def _take_damage(self, attackee, attacker, damage):
        attackee.stats.hit_points -= damage
        if attackee.is_dead:
            self.controller.die(attackee)
            if attacker:
                attacker.stats.experience += int(attackee.value)
                self.controller._send_msg(7, attacker, 
                    "You kill the {}.".format(attackee.name),
                    "")
            else:
                self.controller._send_msg(7, attacker, 
                    "The {} dies.".format(attackee.name),
                    "")

    def _attack(self, attacker, attackee, item):
        # make sure we fire melee before maybe killing the oponent

        
        # from angband
	    #int bonus = p_ptr->state.to_h + o_ptr->to_h;
	    #int chance = p_ptr->state.skills[SKILL_TO_HIT_MELEE] + bonus * BTH_PLUS_ADJ;

        # player to_h bonus is based on strength (see player/calc.c) which ranges from (-3 to +15).
        # object to_h bonus is based on enchantment ... maybe around (0 - 25)
        # bonus is      player.to_hit + obect.to_hit
        # to_hit_melee is based off player race and class
        #   where race seems to be number between 0 - 100 with most values somewere in the middle (mage 20, warrior 80)
        #   where class is modifer mabybe -10 or +10 depending

        # so an average fighter might have 50 + ((0 + 3) * 3)

        # chance is     player.melee_skill + (the bonus * 3)
        chance = 50
        hit = self._test_hit(chance, attackee.stats.ac, False)

        if hit:
            # confusor
            if attacker.condition.confusor:
                attackee.condition.set_timed_condition('confused', Dice(1, 7, modifier=15).roll())
                attacker.condition.set_untimed_condition('confusor', -1)
                if not attacker.condition.confusor:
                    self.controller._send_msg(5, attacker, "Your hands stop glowing red.", None)
                self.controller._send_msg(5, attackee, 
                    "You are confused.",
                    "The {} appears confused".format(attackee.name))
                    
            # intrinsic attack
            for intrinsic in attackee.species.i_attacks:
                # if the attack works
                r = random()
                logger.debug("chance %s for intrinsic %s", round(r, 2), intrinsic)
                if r > intrinsic.chance:
                    damage = intrinsic.damage.roll()
                    attacker.condition.set_timed_condition(intrinsic.condition, damage)
                    logger.debug('The {} {} the {} for {} damage'.format(attackee, intrinsic.verb, attacker, damage))
                    self.controller._send_msg(7, attacker, 
                        "The {} {} you!".format(attacker.name, intrinsic.verb),
                        "The {} {} the {}".format(attackee.name, intrinsic.verb, attacker))
                    return
                    

            damage = attacker.stats.melee.roll()
            logger.debug('The #{} {} hits the #{} {} for {} hp'.format(
                attacker.guid, attacker.name, attackee.guid, attackee.name, damage))
            self._take_damage(attackee, attacker, damage)
            if not attackee.is_dead:
                self.controller._send_msg(7, attacker, 
                    "You hit the {}".format(attackee.name),
                    "The {} hits you.".format(attacker.name))
        else:
            logger.debug('The #{} {} misses the #{} {}'.format(attacker.guid, attacker.name, attackee.guid, attackee.name))
            self.controller._send_msg( 7, attacker, 
                "You missed the {}".format(attackee.name),
                "The {} missed you.".format(attacker.name))

    def _test_hit(self, chance, ac, invisible):
        #from angband

        k = randint(0, 100)

        #There is an automatic 12% chance to hit, and 5% chance to miss.
        if (k < 17):
            return k < 12

	    #Penalize invisible targets
        if invisible:
            chance /= 2

	    # Starting a bit higher up on the scale
        if (chance < 9):
            chance = 9

        return randint(0, chance) >= (ac * 2 / 3)
        

