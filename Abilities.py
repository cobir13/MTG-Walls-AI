# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


from ManaHandler import ManaCost,ManaPool
import ZONE
import copy




#abilities and triggers within a card are always called by the gamestate
#by passing the source Cardboard into the function. Thus, the ability
#doesn't need to know parent Cardboard ahead of time.  This allows me to
#make CardTypes that are generic and never mutated and maintain the
#distinction between Cardboard and CardType. This distinction makes it much
#easier to copy and iterate Gamestates.


class ActivatedAbility():
    def __init__(self,name,cost,execute_fn):
        """
        pay_fn: function that takes in a GameState and a source Cardboard.
            Returns a list of (gamestate,source) pairs giving all possible
            ways the ability could be executed, accounting for all player
            choices and options.  Empty list if impossible to execute.
            DOES NOT MUTATE the original gamestate.
        """
        self.name = name
        self.cost = cost
        self.execute_fn = execute_fn
        
    def PayAndExecute(self,gamestate,source):
        """Returns list of GameStates where the cost has been paid and the 
            abilities have been performed.
        Takes in the GameState in which the ability is supposed to be performed
            and also the source Cardboard that is generating the cost.
        Returns a list of (GameState,Cardboard) pairs in which the cost has
            been paid and the abilities have been performed. The list is:
            - length 1 if there is exactly one way to do this
            - length 0 if this cannot be done (costs, lack of targets, etc)
            - length >1 if there are options that can be decided differently.
        The original GameState and source Cardboard are NOT mutated.
        """   
        #check to make sure the execution is legal
        if not self.cost.CanAfford(gamestate,source):
            return False
        if gamestate.verbose:
            print("Activating: %s" %self.name)
        #split off universes where costs have been paid
        paid_list = self.cost.Pay(gamestate,source)
        #for each of these universes, complete the effect
        executed_list = []
        for state,card in paid_list:
            executed_list += self.Execute(state,card)
        return executed_list
        
    def CanAfford(self,gamestate,source):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return self.cost.CanAfford(gamestate,source)   
    
    def Execute(self,gamestate,source):
        """
        Takes in the GameState in which the ability is supposed to be performed
            and also the source Cardboard that is generating the ability.
        Returns a list of (GameState,Cardboard) pairs in which the effect
            has been performed. The list is:
            - length 1 if there is exactly one way to do this
            - length 0 if this cannot be done (costs, lack of targets, etc)
            - length >1 if there are options that can be decided differently.
        The original GameState and source Cardboard are NOT mutated.
        """
        executed_list = self.execute_fn(gamestate,source)
        #Check state-based actions, to ensure that returned GameStates are legal
        for state,card in executed_list:
            state.StateBasedActions()
        return executed_list
        
        
    def __str__(self):
        return self.name





class ManaAbility(ActivatedAbility):
    """No functional difference to ActivatedAbility, just for tracking and
    as a place to collect some useful functions."""
    
    def DorkAvailable(gamestate,source):
        return (not source.tapped and not source.summonsick and 
                source.zone == ZONE.FIELD)
    
    def TapToPay(gamestate,source):
        newstate,[newsource] = gamestate.CopyAndTrack([source])
        newsource.tapped = True
        return [(newstate,newsource)]

    def AddColor(gamestate,source,color):
        newstate,[newsource] = gamestate.CopyAndTrack([source])
        newstate.pool.AddMana(color)  #add mana
        return [(newstate,newsource)]

    def AddDual(gamestate,source,color1,color2):
        state1,[source1] = gamestate.CopyAndTrack([source])
        state2,[source2] = gamestate.CopyAndTrack([source])
        state1.pool.AddMana(color1)  #add mana
        state2.pool.AddMana(color2)  #add mana
        return [(state1,source1),(state2,source2)]