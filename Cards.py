# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


from ManaHandler import ManaCost
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

class ManaSource():
    def __init__(self):
        self.tapsfor = []
    @property
    def unavailable(self): return False
    def MakeMana(self,gamestate): pass

##---------------------------------------------------------------------------##

class Ability():
    def __init__(self,card,cost,func):
        """func is the function of the ability. It takes in a gamestate and does whatever it does"""
        self.card = card
        if isinstance(cost,ManaCost):
            self.cost = cost
        else:
            self.cost = ManaCost(cost)
        self.func = func
    def Activate(self,gamestate):
        """Deducts payment for the ability and then performs the ability"""
        gamestate.pool.PayCost(self.cost)
        self.func(gamestate)
        


##===========================================================================##

class Spell(Card):
    def __init__(self,name,cost,typelist):
        super().__init__(name,cost,typelist)
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
    
##---------------------------------------------------------------------------##

class Land(Permanent,ManaSource):
    def __init__(self,name,typelist):
        super().__init__(name,"",typelist)
        self.cost = None
    @property
    def unavailable(self):
        return self.tapped or len(self.tapsfor)==0 
    def MakeMana(self,gamestate,color):
        """mutates the pool of the given gamestate to addd a mana of the given
        color (if possible, otherwise this function just does nothing)."""
        if self.unavailable or color not in self.tapsfor:
            return
        else:
            gamestate.pool.AddMana(color)
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






