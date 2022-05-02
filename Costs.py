# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


from ManaHandler import ManaCost,ManaPool


class Cost():
    def __init__(self,manacost=None,afford_fn=None,pay_fn=None):
        """
        afford_fn: function that takes in a source Card and a GameState.
            Returns a boolean: "can this GameState and this Card afford the
            cost?"  DOES NOT MUTATE. Can include other, non-mana costs.
        pay_fn: function that takes in a source Card and a GameState. MUTATES
            THE GAMESTATE to pay the cost.  Returns True if the cost has been
            paid, False if it could not be paid.
            NOTE: GameState may have been mutated even if False isreturned!
        """
        if manacost is None:
            self.manacost = ManaCost("")
        else:
            self.manacost = ManaCost(manacost)
        self.afford_fn = afford_fn
        self.pay_fn = pay_fn   
    
    def CanAfford(self,source,gamestate):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        #if can't afford mana portion, then can't afford cost
        if not gamestate.pool.CanAffordCost(self.manacost):
            return False
        #if we have an afford_fn, use it. If it says True, we say true
        if self.afford_fn is not None:
            return self.afford_fn(source,gamestate)
        else:
            #don't have an "afford" function, so mana is all there is!
            return True
                
    def Pay(self,source,gamestate):
        """MUTATES the gamestate to pay for the ability's cost.
        Returns True if the cost has been paid, False if it cannot be paid.
        Note that the gamestate may have been mutated even if False is returned!"""       
        try:
            gamestate.pool.PayCost(self.manacost)
            if self.pay_fn is not None:
                self.pay_fn(source,gamestate)
            return True
        except:
            return False

    def __str__(self):
        s = str(self.manacost)
        if self.pay_fn is not None:
            s += " %s" %self.pay_fn.__name__
        return s

