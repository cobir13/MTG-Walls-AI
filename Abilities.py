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
        self.name = name
        self.cost = cost
        self.execute_fn = execute_fn
        
    def PayAndExecute(self,source,gamestate):
        """Returns a copy of the gamestate but with the costs paid and the
        ability performed. DOES NOT MUTATE. Returns False if ability cannot
        be activated (due to cost, lack of targets, etc.)"""
        #check to make sure the execution is legal
        if not self.cost.CanAfford(source,gamestate):
            return False
        newstate = gamestate.copy(omit=[source])
        #copy the source separately to keep track of it in the new universe
        newsource = source.copy()
        newstate.GetZone(newsource.zone).append(newsource)        
        #we can safely try to mutate the copies
        if not self.cost.Pay(newsource,newstate):
            return False
        self.Execute(newsource,newstate)
        return newstate
        
    def CanAfford(self,source,gamestate):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return self.cost.CanAfford(source,gamestate)   
    
    def Execute(self,source,gamestate):
        """MUTATES the gamestate to perform the ability."""
        self.execute_fn(source,gamestate)
        if gamestate.verbose:
            print("Activating: %s" %self.name)
        
    def __str__(self):
        return self.name


