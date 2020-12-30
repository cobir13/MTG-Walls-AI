# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 12:41:07 2020

@author: Cobi
"""


class ManaPool():
    colorlist = ["W","U","B","R","G","C"]
    
    def __init__(self,cost_str):
        """Takes in a string in the usual mtg color syntax. This is a mana POOL,
        so there's no such thing as generic mana here. Everything must be specified."""
        cost_str = cost_str.upper()
        self.data = {}
        for s in ManaPool.colorlist:
            self.data[s] = cost_str.count(s)

    def CMC(self):
        """ "converted mana cost". An int, ignoring color"""
        return sum(self.data.values())
        
    def AddMana(self,cost_str):
        cost_str = cost_str.upper()
        for s in ManaPool.colorlist:
            self.data[s] += cost_str.count(s)
    
    def CanAffordCost(self,cost):
        if self.CMC() < cost.CMC():
            return False
        for c in ["W","U","B","R","G","C"]:
            if self.data[c] < cost.data[c]: 
                return False #pool doesn't haven enough mana of this color!
        #if reached here, we have enough colored mana of each color
        return True
    
    def PayCost(self,cost):
        assert(self.CanAffordCost(cost))
        #pay the colored costs first
        for c in ["W","U","B","R","G","C"]:
            assert(self.data[c]>=cost.data[c])
            self.data[c] -= cost.data[c]
        #still need to pay generic part of the cost
        k = 0; paid=0
        while paid<cost.data["gen"] and k<=5:
            color = ["W","U","B","R","G","C"][k]
            if self.data[color] >1: #try to save at least 1 of each color, if possible
                self.data[color] -= 1
                paid += 1
            else:
                k+=1
        #if reached here, I DO need to start emptying out some colors entirely. Do that.
        k = 0
        while paid<cost.data["gen"]:
            color = ["G","W","U","B","R","C"][k]
            if self.data[color] >0:
                self.data[color] -= 1
                paid += 1
            else:
                k+=1

    def __str__(self):
        manastring = ""
        for s in ManaPool.colorlist:
            manastring += s*self.data[s]
        return manastring

    def copy(self):
        return ManaPool(str(self))

##---------------------------------------------------------------------------##

class ManaCost():
    def __init__(self,cost_str):
        """Takes in a string in the usual mtg color syntax. Numbers represent
        "generic" mana, which can be paid later with any color of mana"""
        cost_str = cost_str.upper()
        self.data = {}
        for s in ["W","U","B","R","G","C"]:
            self.data[s] = cost_str.count(s)
        numstr = ''.join(i for i in cost_str if i.isdigit())
        self.data["gen"] = int(numstr) if numstr else 0

    def CMC(self):
        return sum(self.data.values())

    def __str__(self):
        manastring = str(self.data["gen"]) if self.data["gen"]>0 else ""
        for s in ["W","U","B","R","G","C"]:
            manastring += s*self.data[s]
        return manastring

    def copy(self):
        return ManaCost(str(self))
    
