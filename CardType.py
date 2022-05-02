# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


from ManaHandler import ManaCost,ManaPool

import copy





##---------------------------------------------------------------------------##

class CardType():
    def __init__(self,name,cost,typelist):
        self.name = name
        self.cost = ManaCost(cost)
        self.typelist = [s.lower() for s in typelist]
        self.activated = []
        self.triggered = []
        self.upkeep = []
        
    #abilities and triggers within a card are always called by the gamestate
    #by passing the source Cardboard into the function. Thus, the ability
    #doesn't need to know parent Cardboard ahead of time.  This allows me to
    #make CardTypes that are generic and never mutated and maintain the
    #distinction between Cardboard and CardType. This distinction makes it much
    #easier to copy and iterate Gamestates.
        
    
    
    

# class Spell(CardType):
#     def __init__(self,name,cost,typelist,effect,targetlist,otherchoices):
#         super().__init__(name,cost,typelist)
#         self.effect = effect
#         self.targetlist = targetlist
#         self.otherchoices = otherchoices
    

class Creature(CardType):
    def __init__(self,name,cost,typelist,power,toughness):
        super().__init__(name,cost,typelist)
        self.basepower = power
        self.basetoughness = toughness
        if "creature" not in self.typelist:
            self.typelist = ["creature"] + self.typelist
        

        

        
class ActivatedAbility():
    def __init__(self,name,afford_fn,pay_fn,execute_fn):
        self.name = name
        self.afford_fn = afford_fn
        self.pay_fn = pay_fn
        self.execute_fn = execute_fn
        
    def PayAndExecute(self,source,gamestate):
        """Returns a copy of the gamestate but with the costs paid and the
        ability performed. DOES NOT MUTATE. Returns False if ability cannot
        be activated (due to cost, lack of targets, etc.)"""
        #check to make sure the execution is legal
        if not self.CanAfford(source,gamestate):
            return False
        newstate = gamestate.copy(omit=[source])
        #copy the source separately to keep track of it in the new universe
        newsource = source.copy()
        newstate.GetZone(newsource.zone).append(newsource)        
        #it is safe to mutate the copies
        if not self.Pay(newsource,newstate):
            return False
        self.Execute(newsource,newstate)
        return newstate
        
    def CanAfford(self,source,gamestate):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        if self.afford_fn is not None:
            return self.afford_fn(source,gamestate)
        else:
            #don't have an "afford" function, so just try it and see!
            return True
                
    def Pay(self,source,gamestate):
        """MUTATES the gamestate to pay for the ability's cost.
        Returns True if the cost has been paid, False if it cannot be paid.
        Note that the gamestate may have been mutated even if False is returned!"""
        try:
            self.pay_fn(source,gamestate)
            return True
        except:
            return False
    
    def Execute(self,source,gamestate):
        """MUTATES the gamestate to perform the ability."""
        self.execute_fn(source,gamestate)
        if gamestate.verbose:
            print("Activating: %s" %self.name)
        
    def __str__(self):
        return self.name



# ##---------------------------------------------------------------------------##

# class ManaSource():
#     def __init__(self): pass
#     @property
#     def unavailable(self): return False
#     @property
#     def tapsfor(self):
#         """returns a list of ManaPool objects that the ManaSource COULD generate"""
#         return []
#     def MakeMana(self,color):
#         """Adds the given ManaPool (or mana string) to the gamestate's floating
#         pool, if the ManaSource can generate it. Mutates self's gamestate!"""
#         if isinstance(color,str):
#             color = ManaPool(color)
#         if self.unavailable or color not in self.tapsfor:
#             return False #do nothing and SAY it did nothing
#         else:
#             self.gamestate.pool.AddMana( color ) #add mana and SAY it added mana
#             return True
    
# ##---------------------------------------------------------------------------##

# class Land(Permanent,ManaSource):
#     def __init__(self,name,typelist):
#         super().__init__(name,"",typelist)
#         self.cost = None
#     @property
#     def unavailable(self):
#         return self.tapped
#     def MakeMana(self,color):
#         if super().MakeMana(color):  #added mana, so tap or the like
#             self.tapped = True
            
# ##---------------------------------------------------------------------------##


        
        
        
        
        
        
        
        
        

    
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
        





