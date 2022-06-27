# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from typing import List
from GameState import GameState
from Cardboard import Cardboard
from RulesText import Creature
import ZONE












class Action:
    @staticmethod
    def can_be_done(state: GameState, subject: Cardboard, targets: List[Cardboard]) -> bool:
        raise Exception
    @staticmethod
    def do_it(state: GameState, subject: Cardboard, targets: List[Cardboard]) -> List[GameState]:
        raise Exception    



#------------------------------------------------------------------------------

class TapSymbol(Action):
    
    def can_be_done(state, subject, targets):
        return (not subject.tapped and subject.zone == ZONE.FIELD
                and (not subject.has_type(Creature) and subject.summon_sick))
    
    def do_it(state, subject, targets): 
        subject.tapped = True

#------------------------------------------------------------------------------

class Add01Counter(Action):
    
    def can_be_done(state, subject, targets):
        return subject.zone == ZONE.FIELD
    
    def do_it(state, subject, targets): 
        subject.add_counter("-0/-1")

#------------------------------------------------------------------------------

class OncePerTurn(Action):
    
    def can_be_done(state, subject, targets):
        return "@used" not in subject.counters and subject.zone == ZONE.FIELD
    
    def do_it(state, subject, targets): 
        subject.add_counter("@used")  # "@" counters are cleared by untap step

#------------------------------------------------------------------------------

class AddGreen(Action):
    
    def can_be_done(state, subject, targets):
        return True
    
    def do_it(state, subject, targets): 
        state.AddToPool("G")

#------------------------------------------------------------------------------







class TapAnother(Action):

    @staticmethod
    def can_be_done(state, subject, targets):
        return (not subject.tapped and subject.zone == ZONE.FIELD
                and (not subject.has_type(Creature) and subject.summon_sick))
    
    @staticmethod
    def do_it(state, subject, targets): 
        subject.tapped = True
        
        
        
        
        
        
class Condition:
    def __init__(self, param_name:str, comparator:str, value):
        self.param_name = param_name
        assert(comparator in ["is", "=", "==", "<", ">", "!"])
        self.comparator = comparator
        self.value = value
    def compare(self, cardboard: Cardboard):
        #get value from the cardboard to compare to
        if hasattr(cardboard, self.param_name):
            other_value = getattr(cardboard,self.param_name)
        elif hasattr(cardboard.rules_text, self.param_name):
            other_value = getattr(cardboard.rules_text,self.param_name)
        else:
            return False
        if callable(other_value):
            other_value = other_value()
        #compare
        if self.comparator in ["is", "=", "=="]:
            return other_value == self.value
        if self.comparator == "<":
            return other_value < self.value
        if self.comparator == ">":
            return other_value > self.value
        if self.comparator == "!=":
            return other_value != self.value
        else:
            raise ValueError("Invalid comparator!")


class WildCard:
    def __init__(self, conditions: List[Condition]):
        self.conditions = conditions
    def compare(self, cardboard: Cardboard):
        return all([cond.compare(cardboard) for cond in self.conditions])



        
        
        
def count_matches(gamestate, zone, wildcard):
    return len([c.is_equiv_to(wildcard) for c in gamestate._GetZone(zone)])

def look(gamestate, top_n):
    return gamestate.deck[:top_n]