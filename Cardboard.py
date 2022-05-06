# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


import ZONE
import CardType


##---------------------------------------------------------------------------##

class Cardboard():
    """Represents the physical piece of cardboard that is a Magic card.
    """
    
    
    
    def __init__(self,cardtype,zone):
        """cardtype: a Cardtype instance."""
        self.cardtype = cardtype
        self.tapped = False
        self.summonsick = True
        self.counters = []  #sorted list of counters. Also other trackers
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
    
    def AddCounter(self,addition):
        self.counters = sorted(self.counters + [addition])
        
    @property
    def name(self):
        return self.cardtype.name

    # def GetAbilities(self):
    #     return self.cardtype.activated
    
    

    
    def ID(self):
        s = type(self.cardtype).__name__ #MtG card type (creature, land, etc)
        s += self.cardtype.name + "_"
        if self.tapped:
            s += "T"
        if self.summonsick and isinstance(self.cardtype,CardType.Creature):
            s += "S"
        s += str(self.zone)
        s += "_"+"_".join(self.counters)
        return s
        
    def EquivTo(self,other):
        return self.ID() == other.ID()
    
    