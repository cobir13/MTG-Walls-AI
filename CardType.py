# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


from ManaHandler import ManaCost,ManaPool
import ZONE
import Abilities






##---------------------------------------------------------------------------##

class CardType():
    def __init__(self,name,cost,typelist):
        self.name = name
        self.cost = cost
        self.typelist = [s.lower() for s in typelist]
        #abilities
        self.activated = []  #make separate for mana abilities?
        #effects
        #FORMAT IS: lambda source_cardboard,gamestate : mutated gamestate
        self.upkeep = []
        self.cast_effect = []  #also where enter-the-battlefield effects live
        
        # #build the ability to cast the spell?
        # def casting(source,gamestate):
        #     gamestate.MoveZone(source,ZONE.FIELD)
        #     for effect in self.cast_effect:
        #          effect(source,gamestate)
        # Abilities.ActivatedAbility("cast "+name,cost,
        
    CAST_DESTINATION = ZONE.UNKNOWN  #children should overwrite

    #abilities and triggers within a card are always called by the gamestate
    #by passing the source Cardboard into the function. Thus, the ability
    #doesn't need to know parent Cardboard ahead of time.  This allows me to
    #make CardTypes that are generic and never mutated and maintain the
    #distinction between Cardboard and CardType. This distinction makes it much
    #easier to copy and iterate Gamestates.


    def CanAfford(self,source,gamestate):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return self.cost.CanAfford(source,gamestate)  
    
    def Cast(self,source,gamestate):
        """Returns a copy of the gamestate but with the costs paid and the
        card cast. DOES NOT MUTATE. Returns False if card cannot be cast
        (due to cost, lack of targets, etc.)"""
        #check to make sure the execution is legal
        if not self.cost.CanAfford(source,gamestate):
            return False
        #Make the new gamestate (and source for the new gamestate) to mutate
        newstate = gamestate.copy(omit=[source])
        newsource = source.copy()
        newstate.GetZone(newsource.zone).append(newsource)    
        #we can safely try to mutate the copies. Pay costs:
        if not self.cost.Pay(newsource,newstate):
            return False
        if newstate.verbose:
            print("Casting: %s" %self.name)
        newstate.MoveZone(newsource,self.CAST_DESTINATION)
        for effect in self.cast_effect:
            effect(newsource,newstate)
        return newstate

    

    

class Permanent(CardType):
    
    CAST_DESTINATION = ZONE.FIELD



class Creature(Permanent):
    def __init__(self,name,cost,typelist,power,toughness):
        super().__init__(name,cost,typelist)
        self.basepower = power
        self.basetoughness = toughness
        if "creature" not in self.typelist:
            self.typelist = ["creature"] + self.typelist
        



class Spell(CardType):
    
    CAST_DESTINATION = ZONE.GRAVE




