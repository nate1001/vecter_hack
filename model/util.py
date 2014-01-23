
from collections import OrderedDict
from random import normalvariate, random

def get_article(name):
    if name[0] in 'aeiou':
        return 'an'
    else:
        return 'a'


class Verb(object):
    
    @classmethod
    def from_text(cls, text):
        if text.find('|') > -1:
            a, b = text.split('|')
            me = a
            she = a+b
        else:
            me = text
            she = text
        return cls(me, she)
    
    def __init__(self, me, she):
        
        self.me = me
        self.she = she

    def __str__(self):
        return self.me
        

def normal(mean, std_dev, minimum=None, maximum=None):
    value = int(round(normalvariate(mean, std_dev)))
    if minimum is not None:
        value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


class SumOfDiceDist(object):
    
    # The joy of this will be that mean and std_dev make for a normal distribution.
    
    # constraints: Die must start with one and be fair.
    # (not as much info as you would think for such a applied distribution)

    # best reference I found below: hopefully you remember your sumations and polynomial expansions into 
    # polynomials from enginering calc :)

    # http://www.madandmoonly.com/doctormatt/mathematics/dice1.pdf
    # In general, a fair n-sided die can be represented by the polynomial:
    # 1/n( x + x**2 + x**3 + ... + x**n)

    @classmethod
    def from_text(cls, text):
        modifier = 0
        rolls, sides = text.split('d')
        rolls = int(rolls)
        if sides.find('+') > -1:
            sides, modifier = sides.split('+')
            modifier = int(modifier)
        elif sides.find('-') > -1:
            sides, modifier = sides.split('-')
            modifier = - int(modifier)
        sides = int(sides)
        return cls(rolls, sides, modifier=modifier)
    
    def __init__(self, rolls, sides, minimum=1, maximum=None, modifier=0):
        self._rolls = rolls
        self._sides = sides
        self._minimum = minimum
        self._maximum = maximum
        self._modifier = modifier

        self._stats = {
            'mean': self._mean(),
            'expectation': self._expectation(),
            'variance': self._variance(),
            'std_dev': self._std_dev(),
        }

    @property
    def mean(self): return self._stats['mean']
    @property
    def expectation(self): return self._stats['expectation']
    @property
    def variance(self): return self._stats['variance']
    @property
    def std_dev(self): return self._stats['std_dev']
    @property
    def rolls(self): return self._rolls
    @property
    def sides(self): return self._sides
    @property
    def minimum(self): return self._minimum
    @property
    def maximum(self): return self._maximum
    @property
    def modifier(self): return self._modifier


    def __str__(self):
        return "{}d{}".format(self._rolls, self._sides)

    def __repr__(self):
        return str(self)
        
    def roll(self):
        i = int(round(normalvariate(self.mean, self.std_dev)))
        if self._minimum is not None:
            i = max(i, self._minimum)
        if self._maximum is not None:
            i = min(i, self._maximum)
        return i + self._modifier

    def _mean(self):
        return self._expectation() * self._rolls

    def _expectation(self, squared=False):
        # per die!

        #http://www.futureaccountant.com/theory-of-expectation-random-variable/problems-solutions/throwing-rolling-dice-02.php

        s = self.sides
        total = 0
        for n in range(1, s+1):
            if squared:
                total += float(n**2)/s
            else:
                total += float(n)/s
        return total

    def _variance(self):
        return (self._expectation(squared=True) - self._expectation()**2) * self._rolls

    def _std_dev(self):
        return (self._variance())**.5

class Chance(object):
    
    def __init__(self, chance):
        
        chance = float(chance)
        if chance < 0 or chance > 1:
            raise ValueError(chance)
        self.chance = float(chance)

    def roll(self):
        return random() < self.chance
            
    

if __name__ == '__main__':

    dice = SumOfDiceDist(15,15)
    d = SumOfDiceDist(7,30)

    for d in sorted([d, dice], lambda a,b: cmp(getattr(a, 'sides'), getattr(b, 'sides'))):
        pass


