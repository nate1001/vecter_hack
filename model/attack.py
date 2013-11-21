
import random


class CombatArena(object):
    
    def __init__(self, controller):
        self.controller = controller
    
    def _attack(self, attacker, attackee, item):
        

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

            damage = attacker.stats.melee.roll()
            print 'attackee {} damage: {}'.format(attackee, damage)

            self.controller._send_msg(
                7, 
                attacker, 
                "You hit the {} for {} hp".format(attackee.name, damage),
                "The {} hits you for {} hp.".format(attacker.name, damage))
            self._take_damage(attackee, damage)
        else:
            self.controller._send_msg(
                7, 
                attacker, 
                "You missed the {}".format(attackee.name),
                "the {} missed you.".format(attacker.name))

    def _test_hit(self, chance, ac, invisible):
        #from angband

        k = random.randint(0, 100)

        #There is an automatic 12% chance to hit, and 5% chance to miss.
        if (k < 17):
            return k < 12

	    #Penalize invisible targets
        if invisible:
            chance /= 2

	    # Starting a bit higher up on the scale
        if (chance < 9):
            chance = 9

        return random.randint(0, chance) >= (ac * 2 / 3)

    def _take_damage(self, being, damage):
        being.stats._change_stat('hit_points', -damage)
        if being.stats.hit_points < 0:
            self.controller.die(being)

    def melee(self, attacker, attackee):
        self._attack(attacker, attackee, None)
