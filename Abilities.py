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

class TargetBundle():
    def __init__(self,source,othertargets=[]):
        """Convenient way to pass around a gamestate being affected,
        the source (Cardboard) of the effect, and any other targets
        (Cardboards) that might need to be tracked as well.
        """
        self.source = source
        self.targets = othertargets

    @property
    def gamestate(self):
        if self.source is not None:
            return self.source.owngame
        elif len(self.targets)>0:
            return self.targets[0].owngame
        else:
            raise ValueError("no Cardboards in TargetBundle!")

    def SplitUniverses(self):
        """Return a copy of this bundle: a copied gamestate inhabited by
        copied Cardboards. The source and othertargets list are the
        equivalent objects as the ones from the source bundle, just in
        a new gamestate."""
        
        
        newstate = self.gamestate.copy(omit=[self.source]+self.targets)
        newsource = self.source.copy(newstate)
        newstate.AddToZone( newsource, newsource.zone)
        newtargets = []
        for c in self.targets:
            new_c = c.copy(newstate)
            newstate.AddToZone( new_c, new_c.zone )
            newtargets.append(new_c)
        return TargetBundle(newsource,newtargets)
        
        






class ActivatedAbility():
    def __init__(self,name,cost,execute_fn):
        """
        pay_fn: function that takes in a TargetBundle.
            Returns a list of TargetBundle pairs giving all possible
            ways the ability could be executed, accounting for all player
            choices and options.  Empty list if impossible to execute.
            DOES NOT MUTATE the original gamestate.
        """
        self.name = name
        self.cost = cost
        self.execute_fn = execute_fn
        
    def PayAndExecute(self,sourcebundle):
        """Returns list of TargetBundles where the cost has been paid and the 
            abilities have been performed.
        Takes in a TargetBundle describing the source Cardboard that is
            generating the cost.
        Returns a list of TargetBundles in which the cost has
            been paid and the abilities have been performed. The list is:
            - length 1 if there is exactly one way to do this
            - length 0 if this cannot be done (costs, lack of targets, etc)
            - length >1 if there are options that can be decided differently.
        The original states in the sourcebundle are not mutated.
        """   
        #check to make sure the execution is legal
        if not self.cost.CanAfford(sourcebundle):
            return False
        # if sourcebundle.gamestate.verbose:
        #     print("Activating: %s" %self.name)
        #split off universes where costs have been paid
        paid_list = self.cost.Pay(sourcebundle)
        #for each of these universes, complete the effect
        executed_list = []
        for bundle in paid_list:
            executed_list += self.Execute(bundle)
        return executed_list
        
    def CanAfford(self,sourcebundle):
        """Returns boolean: can this TargetBundle afford the cost?
        DOES NOT MUTATE."""
        return self.cost.CanAfford(sourcebundle)   
    
    def Execute(self,sourcebundle):
        """Returns list of TargetBundles where the ability has been performed.
        Takes in a TargetBundle describing the source Cardboard that is
            generating the cost.
        Returns a list of TargetBundles in which the cost has
            been paid and the abilities have been performed. The list is:
            - length 1 if there is exactly one way to do this
            - length 0 if this cannot be done (costs, lack of targets, etc)
            - length >1 if there are options that can be decided differently.
        The original states in the sourcebundle are not mutated.
        """   
        executed_list = self.execute_fn(sourcebundle)
        #Check state-based actions, to ensure that returned GameStates are legal
        for bundle in executed_list:
            bundle.gamestate.StateBasedActions()
        return executed_list
        
        
    def __str__(self):
        return self.name





class ManaAbility(ActivatedAbility):
    """No functional difference to ActivatedAbility, just for tracking and
    as a place to collect some useful functions."""
    
    def DorkAvailable(bundle):
        return (not bundle.source.tapped
                and not bundle.source.summonsick
                and bundle.source.zone == ZONE.FIELD)
    
    def TapToPay(bundle):
        newbundle = bundle.gamestate.CopyAndTrack(bundle)
        newbundle.source.tapped = True
        return [newbundle]

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