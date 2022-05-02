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
        """
        name (str)  : name of this card.
        cost (Cost) : mana and additional cost to cast this card.
        typelist (list(str)):
                      List of lowercase tags describing this card. Includes
                      MtG types as well as relevant keywords.
        activated (list(Abilities)):
                      List of Ability objects representing activated abilities.
        upkeep (list(fn)):
                      List of functions that should be run on the gamestate and
                      card every upkeep. For effects that trigger on upkeep.
        
        pay_fn: function that takes in a GameState and a source Cardboard.
            Returns a list of (gamestate,source) pairs giving all possible
            ways the ability could be executed, accounting for all player
            choices and options.  Empty list if impossible to execute.
            DOES NOT MUTATE the original gamestate.
        
        
        
        """

        
        self.name = name
        self.cost = cost
        self.typelist = [s.lower() for s in typelist]
        #abilities
        self.activated = []  #make separate for mana abilities?
        #effects
        #FORMAT IS: lambda source_cardboard,gamestate : mutated gamestate
        self.upkeep = []
        self.cast_effect = []  #also where enter-the-battlefield effects live

        
    CAST_DESTINATION = ZONE.UNKNOWN  #children should overwrite

    #abilities and triggers within a card are always called by the gamestate
    #by passing the source Cardboard into the function. Thus, the ability
    #doesn't need to know parent Cardboard ahead of time.  This allows me to
    #make CardTypes that are generic and never mutated and maintain the
    #distinction between Cardboard and CardType. This distinction makes it much
    #easier to copy and iterate Gamestates.


    def CanAfford(self,gamestate,source):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return self.cost.CanAfford(gamestate,source)  
    
    def Cast(self,gamestate,source):
        """Returns a copy of the gamestate but with the costs paid and the
        card cast. DOES NOT MUTATE. Returns False if card cannot be cast
        (due to cost, lack of targets, etc.)"""
        
        """
        Takes in the GameState in which the spell is supposed to be cast
            and also the source Cardboard that is being cast.
        Returns a list of (GameState,Cardboard) pairs in which the spell
            has been cast. The list is:
            - length 1 if there is exactly one way to do this
            - length 0 if this cannot be done (costs, lack of targets, etc)
            - length >1 if there are options that can be decided differently.
        The original GameState and source Cardboard are NOT mutated.
        """
        
        
        
        #check to make sure the execution is legal
        if not self.cost.CanAfford(gamestate,source):
            return False
        #split off universes where costs have been paid
        paid_list = self.cost.Pay(gamestate,source)
        if gamestate.verbose and len(paid_list)>0:
            print("Casting: %s" %self.name)
        #for each of these universes, cast the spell
        executed_list = []
        for state,card in paid_list:
            #these are copies so it is safe to mutate them during casting
            state.MoveZone(card,self.CAST_DESTINATION)
            #trigger enter-the-battlefield effects or cast effects
            if len(self.cast_effect)>0:
                for effect in self.cast_effect:
                    executed_list += effect(state,card)
            else:
                executed_list += [(state,card)]
        return executed_list
        
    

        

    

    

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




