# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 12:41:07 2020

@author: Cobi
"""


class ManaPool():
    colorlist = ["W", "U", "B", "R", "G", "C", "A"]

    def __init__(self, cost_str: str):
        """Takes in a string in the usual mtg color syntax. This is a mana POOL,
        so there's no such thing as generic mana here. Everything must be specified.
        'C' is colorless, 'A' is gold (can be used for any color)."""
        cost_str = cost_str.upper()
        self.data = {}  # dictionary of {color:amount}
        for s in ManaPool.colorlist:
            self.data[s] = cost_str.count(s)

    def cmc(self):
        """ "converted mana cost". An int, ignoring color"""
        return sum(self.data.values())

    def AddMana(self, mana):
        if isinstance(mana, str):
            mana = ManaPool(mana)
        for s in ManaPool.colorlist:
            self.data[s] += mana.data[s]

    def CanAffordCost(self, cost):
        if self.cmc() < cost.cmc():
            return False
        gold = self.data["A"]
        for c in ["W", "U", "B", "R", "G", "C"]:
            if self.data[c] < cost.data[c]:
                # pool doesn't haven enough mana of this color! dip into gold
                gold -= (cost.data[c] - self.data[c])
                if gold < 0:  # don't have enough gold to cover the cost either!
                    return False
                    # if reached here, we have enough colored mana of each color
        return True

    def PayCost(self, cost):
        assert (self.CanAffordCost(cost))
        # pay the colored costs first
        for c in ManaCost.colorlist:  # yes, Cost not Pool
            if self.data[c] >= cost.data[c]:  # can pay without gold
                self.data[c] -= cost.data[c]
            else:
                self.data[c] = 0
                self.data["A"] -= (cost.data[c] - self.data[c])
        # still need to pay generic part of the cost
        k = 0;
        paid = 0
        while paid < cost.data["gen"] and k <= 5:
            color = ManaPool.colorlist[k]
            if self.data[color] > 1:  # try to save at least 1 of each color, if possible
                self.data[color] -= 1
                paid += 1
            else:
                k += 1
        # if reached here, I DO need to start emptying out some colors entirely. Do that.
        k = 0
        while paid < cost.data["gen"]:
            color = ManaPool.colorlist[k]
            if self.data[color] > 0:
                self.data[color] -= 1
                paid += 1
            else:
                k += 1

    def __str__(self):
        manastring = ""
        for s in ManaPool.colorlist:
            manastring += s * self.data[s]
        return manastring

    def copy(self):
        return ManaPool(str(self))

    def __eq__(self, other):
        # two pools are equal if they have the same in each entry
        for color, amount in self.data.items():
            if amount != other.data[color]:
                return False
        return True


##---------------------------------------------------------------------------##

class ManaCost:
    colorlist = ["W", "U", "B", "R", "G", "C"]

    def __init__(self, cost_str: str):
        """Takes in a string in the usual mtg color syntax. Numbers represent
        "generic" mana, which can be paid later with any color of mana"""
        cost_str = cost_str.upper()
        self.data = {}
        for s in ManaCost.colorlist:
            self.data[s] = cost_str.count(s)
        numstr = ''.join(i for i in cost_str if i.isdigit())
        self.data["gen"] = int(numstr) if numstr else 0

    def cmc(self):
        return sum(self.data.values())

    def __str__(self):
        manastring = str(self.data["gen"]) if self.data["gen"] > 0 else ""
        for s in ManaCost.colorlist:
            manastring += s * self.data[s]
        return manastring

    def copy(self):
        return ManaCost(str(self))
