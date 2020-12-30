# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


from ManaHandler import ManaPool,ManaCost
import copy


##---------------------------------------------------------------------------##
class Card():
    def __init__(self,name,cost,typelist):
        self.name = name
        self.cost = ManaCost(cost)
        self.typelist = typelist
    def __str__(self):
        return self.name + ("(T)" if hasattr(self,"tapped") and self.tapped else "")
    def copy(self):
        return copy.copy(self)
##---------------------------------------------------------------------------##
class Spell(Card):
    def __init__(self,name,cost,typelist):
        super().__init__(name,cost,typelist)
    
    def GetAbilities(self,gamestate):
        if self.cost.CanAfford(gamestate.manapool):
            #can afford, so return a lambda which is "pay+do effect"
            return [lambda: self.cost.Pay(gamestate.manapool) and self.Effect(gamestate)]
            return [self.Effect]
            
    def Effect(self,gamestate):
        pass
##---------------------------------------------------------------------------##     
class Permanent(Card):
    def __init__(self,name,cost,typelist):
        super().__init__(name,cost,typelist)
        self.tapped = False  
    def Untap(self):
        self.tapped = False
    def Upkeep(self):
        pass
    def ManaCanMake(self,gamestate):
        """The mana that this permanent can produce at this moment, given the gamestate"""
        return ""
##---------------------------------------------------------------------------##
class Land(Permanent):
    def __init__(self,name,typelist):
        super().__init__(name,"",typelist)
        self.cost = None
        self.tapsfor = []
    @property
    def unavailable(self):
        return self.tapped or len(self.tapsfor)==0 
    def MakeMana(self,gamestate):
        """mutates the pool of the given gamestate"""
        if self.unavailable:
            return
        elif len(self.tapsfor) ==1:
            gamestate.pool.AddMana( self.tapsfor[0] )
        else:
            gamestate.pool.AddMana("L")
        # gamestate.pool.AddMana(self.ManaCanMake(gamestate))
        self.tapped = True
##---------------------------------------------------------------------------##
class Creature(Permanent):
    def __init__(self,name,cost,power,toughness,typelist):
        super().__init__(name,cost,typelist)
        self.summonsick = True
        self.power = power
        self.toughness = toughness 
    def Upkeep(self):
        self.summonsick = False
##---------------------------------------------------------------------------##




if __name__ == "__main__":
    caryatid = Creature("Sylvan Caryatid","1G",0,3,["creature","plant","defender"])

    
    pool = ManaPool("GGGGGGRRWWW")
    print(pool)
    while pool.CanAffordCost(caryatid.cost):
        print("can afford. paying")
        pool.PayCost(caryatid.cost)
        print(pool)