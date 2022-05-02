# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


from ManaHandler import ManaCost


class Cost():
    def __init__(self,manacost=None,afford_fn=None,pay_fn=None):
        """
        afford_fn: function that takes in a GameState and a source Cardboard.
            Returns a boolean: "can this GameState and this Card afford the
            cost?"  DOES NOT MUTATE. Can include other, non-mana costs.
        pay_fn: function that takes in a GameState and a source Cardboard.
            Returns a list of (gamestate,source) pairs giving all possible
            ways the (non-mana) costs could be paid. Empty list if impossible
            to pay. DOES NOT MUTATE the original gamestate.
        """
        if manacost is None:
            self.manacost = ManaCost("")
        else:
            self.manacost = ManaCost(manacost)
        self.afford_fn = afford_fn
        self.pay_fn = pay_fn   
    
    def CanAfford(self,gamestate,source):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        #if can't afford mana portion, then can't afford cost
        if not gamestate.pool.CanAffordCost(self.manacost):
            return False
        #if we have an afford_fn, use it. If it says True, we say true
        if self.afford_fn is not None:
            return self.afford_fn(gamestate,source)
        else:
            #don't have an "afford" function, so mana is all there is!
            return True
                
    def Pay(self,gamestate,source):
        """Returns list of GameStates where the cost has been paid.
        Takes in the GameState in which the cost is supposed to be paid and
            the source Cardboard that is generating the cost.
        Returns a list of (GameState,Cardboard) pairs in which the cost has
            been paid. The list is length 1 if there is exactly one way to pay
            the cost, and the list is length 0 if the cost cannot be paid.
        The original GameState and Source are NOT mutated.
        """       
        #copy the source separately to keep track of it in the new universe
        newstate,[newsource] = gamestate.CopyAndTrack([source])
        try:
            #pay the mana portion. this never splits into new gamestates
            newstate.pool.PayCost(self.manacost)  #mutates
            if self.pay_fn is None:
                return [(newstate,newsource)]
            else:
                result_list = self.pay_fn(newstate,newsource)
            return result_list
        except:
            return []

    def __str__(self):
        s = str(self.manacost)
        if self.pay_fn is not None:
            s += " %s" %self.pay_fn.__name__
        return s






# class Action():
#     """nicer wrapper for actions which affect a gamestate"""
#     def __init__(self,name,func):
#         """
#         name: name of the action.
#         func: function that takes in a source Cardboard and a GameState, and
#             returns a list of (gamestate,source) pairs giving all possible
#             results of the Action. DOES NOT MUTATE the original gamestate.
#         """
#         self.name = name
#         self.func = func
#     def Act(self,gamestate,cardboard):
#         return self.func(gamestate,cardboard)
#     def __str__(self):
#         return self.name
#     def __repr__(self):
#         return("Action(%s)" %self.name)
    