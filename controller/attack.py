
from random import random, randint

from config import logger


class CombatArena(object):
    
    def __init__(self, controller):
        self.controller = controller
    

    def melee(self, attacker, attackee):

        game = self.controller.game
        t = self.controller.game.level.tile_for(attacker)
        self._attack(attacker, attackee, None)

    def spell_attack(self, target, spell):

        attackee = target.being
        damage = spell.damage.roll()
        self.controller._send_msg(
            7, 
            attackee, 
            "You take {} damage form the {} spell.".format(damage, spell.name),
            "The {} spell does {} damage on {}".format(spell.name, damage, attackee.name),
        )
        self.controller.events['being_spell_damage'].emit(target.idx, attackee.guid, spell.view())
        for condition in spell.conditions:
            #FIXME set time with dice
            attackee.condition.setTimedCondition(condition, 5)
        self._take_damage(attackee, damage)

    def _take_damage(self, being, damage):
        being.stats.hit_points -= damage
        if being.is_dead:
            self.controller.die(being)
            being.stats.experience += int(being.value)

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

            for intrinsic in attackee.species.i_attacks:
                # if the attack works
                r = random()
                logger.debug("chance %s for intrinsic %s", round(r, 2), intrinsic)
                if r > intrinsic.chance:
                    damage = intrinsic.damage.roll()
                    attacker.condition.setTimedCondition(intrinsic.condition, damage)
                    msg = 'The {} {} the {} for {} damage'.format(
                        attackee, intrinsic.verb, attacker, damage)
                    logger.info(msg)

                    self.controller._send_msg(
                        7, 
                        attacker, 
                        "The {} {} you!".format(attacker.name, intrinsic.verb),
                        "The {} {} the {}".format(attackee.name, intrinsic.verb, attacker),
                    )
                    return
                    

            damage = attacker.stats.melee.roll()
            msg = 'The #{} {} hits the #{} {} for {} hp'.format(
                attacker.guid, attacker.name, attackee.guid, attackee.name, damage)
            logger.info(msg)
            self.controller._send_msg(
                7, 
                attacker, 
                "You hit the {} for {} hp".format(attackee.name, damage),
                "The {} hits you for {} hp.".format(attacker.name, damage))
            self._take_damage(attackee, damage)
        else:
            msg = 'The #{} {} misses the #{} {}'.format(
                attacker.guid, attacker.name, attackee.guid, attackee.name)
            logger.info(msg)
            self.controller._send_msg(
                7, 
                attacker, 
                "You missed the {}".format(attackee.name),
                "the {} missed you.".format(attacker.name))

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
        

