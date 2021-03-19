# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


from ManaHandler import ManaCost,ManaPool
import copy


##---------------------------------------------------------------------------##

class Card():
    def __init__(self,name,cost,typelist):
        self.name = name
        self.cost = ManaCost(cost)
        self.typelist = typelist
        self.gamestate = None
    def __str__(self):
        return self.name + ("(T)" if hasattr(self,"tapped") and self.tapped else "")
    def copy(self):
        newcopy = copy.copy(self)
        newcopy.gamestate = None
        return newcopy
    
##---------------------------------------------------------------------------##

class ManaSource():
    def __init__(self): pass
    @property
    def unavailable(self): return False
    @property
    def tapsfor(self):
        """returns a list of ManaPool objects that the ManaSource COULD generate"""
        return []
    def MakeMana(self,color):
        """Adds the given ManaPool (or mana string) to the gamestate's floating
        pool, if the ManaSource can generate it. Mutates self's gamestate!"""
        if isinstance(color,str):
            color = ManaPool(color)
        if self.unavailable or color not in self.tapsfor:
            return False #do nothing and SAY it did nothing
        else:
            self.gamestate.pool.AddMana( color ) #add mana and SAY it added mana
            return True

##---------------------------------------------------------------------------##

class Ability():
    def __init__(self,name,card,cost,func):
        """func is the function of the ability. It takes in a gamestate and does whatever it does"""
        self.card = card
        self.name = name
        if isinstance(cost,ManaCost):
            self.cost = cost
        else:
            self.cost = ManaCost(cost)
        self.func = func
    def Activate(self):
        """Deducts payment for the ability and then performs the ability"""
        self.gamestate.pool.PayCost(self.cost)
        self.func(self.gamestate)
    @property
    def gamestate(self):
        return self.card.gamestate
        


##===========================================================================##

class Spell(Card):
    def __init__(self,name,cost,typelist):
        super().__init__(name,cost,typelist)
    def Effect(self):
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
    
##---------------------------------------------------------------------------##

class Land(Permanent,ManaSource):
    def __init__(self,name,typelist):
        super().__init__(name,"",typelist)
        self.cost = None
    @property
    def unavailable(self):
        return self.tapped
    def MakeMana(self,color):
        if super().MakeMana(color):  #added mana, so tap or the like
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






