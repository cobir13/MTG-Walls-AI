# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


import ZONE


##---------------------------------------------------------------------------##

class Cardboard():
    """Represents the physical piece of cardboard that is a Magic card.
    """
    
    
    
    def __init__(self,cardtype,zone):
        """cardtype: a Cardtype instance."""
        self.cardtype = cardtype
        self.tapped = False
        self.summonsick = True
        self.counters = []  #holds counters and also internal effects for tracking once-per-turn abilities
        self.zone = zone
    


    def __str__(self):
        s = self.cardtype.name
        if self.zone == ZONE.FIELD and self.tapped:
            s += "(T)"
        if len(self.counters)>0:
            s += "[%s]" %",".join(self.counters)
        return s
    
    def copy(self):
        newcard = Cardboard(self.cardtype,self.zone)
        #safe to copy by reference since they're all ints, str, etc
        newcard.tapped    = self.tapped
        newcard.summonsick= self.summonsick
        newcard.zone      = self.zone
        #counters is a LIST so it needs to be copied carefully, without reference
        newcard.counters = self.counters.copy()
        #cardtype never mutates so it's ok that they're both pointing at the
        #same instance of a CardType
        newcard.cardtype  = self.cardtype
        return newcard
    

    # def GetAbilities(self):
    #     ability_list = []
    #     for ability in self.cardtype.activated:
    #         # name = ability.name
    #         func = lambda game,s=self: ability.PayAndExecute(s,game)
    #         ability_list.append( func )
    #     return ability_list
        
    @property
    def name(self):
        return self.cardtype.name
    @property
    def activated(self):
        return self.cardtype.activated
        
    
    
    