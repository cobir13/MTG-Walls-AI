# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from typing import List
from GameState import GameState
from Cardboard import Cardboard
import Choices
import MatchCardPatterns as Match


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------

class Getter:
    def get(self, state:GameState, subject:Cardboard):
        raise Exception

# ----------

class Integer(Getter):
    def get(self, state:GameState, subject:Cardboard) -> int:
        return super().get(state,subject)

# ----------

class NumberInZone(Integer):
    """Get the number of Cardboards which match the wildcard patterns"""
    def __init__(self, patterns:List[Match.CardPattern],zone):
        super().__init__()
        self.patterns = patterns
        self.zone = zone
    def get(self, state:GameState, subject:Cardboard):
        zone = state.get_zone(self.zone)
        return len( [c for c in zone
                                 if all([p.match(c,state,subject) for p in self.patterns])] )

# ----------

class ConstInteger(Integer):
    def __init__(self, constant_value:int):
        super().__init__()
        self.constant_value = constant_value
    def get(self, state:GameState, subject:Cardboard):
        return self.constant_value

# ----------

class CardboardList(Getter):
    def get(self, state:GameState, subject:Cardboard) -> List[Cardboard]:
        raise Exception

# ----------

class Const(Getter):
    def __init__(self, constant_value):
        super().__init__()
        self.constant_value = constant_value
    def get(self, state:GameState, subject:Cardboard):
        return self.constant_value

# ----------

class ConstCardboard(CardboardList):
    def __init__(self, cardboard):
        super().__init__()
        self.constant_value = cardboard
    def get(self, state:GameState, subject:Cardboard):
        return [self.constant_value]

# ----------

class ListFromZone(CardboardList):
    def __init__(self, patterns:List[Match.CardPattern], zone):
        super().__init__()
        self.patterns = patterns
        self.zone = zone
    def get(self, state:GameState, subject:Cardboard) -> List[Cardboard]:
        zone = state.get_zone(self.zone)
        return [c for c in zone if all([p.match(c,state,subject) for p in self.patterns])]

# ----------

class TopOfDeck(CardboardList):
    def __init__(self, patterns:List[Match.CardPattern], get_depth:ConstInteger):
        super().__init__()
        self.patterns = patterns
        self.get_depth = get_depth
    def get(self, state:GameState, subject:Cardboard) -> List[Cardboard]:
        num_of_cards_deep = self.get_depth.get(state,subject)
        top_of_deck = state.deck[:num_of_cards_deep]
        return [c for c in top_of_deck
                            if all([p.match(c,state,subject) for p in self.patterns])]

# =============================================================================
# class GetSelf(CardboardList):
#     
#     def __init__(self):
#         super().__init__()
#         
#     def get(self, state:GameState, subject:Cardboard):
#         return [subject]
# =============================================================================


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


# =============================================================================
# class Chooser:
#     
#     def __init__(self, getter:Getter, num_to_choose:int, can_be_less:bool ):
#         self.getter = getter
#         self.num_to_choose = num_to_choose
#         self.can_be_less = can_be_less
#     def choose(self,  state:GameState, subject:Cardboard) -> List[tuple]:
#         """returns a list of all choices that have been selected. Each element
#         of the list is a tuple of length N, where N is the number of items
#         requested."""
#         options = self.getter.get(state,subject) #list of tuples of items
#         if self.must_be_exact:
#             if self.num_to_choose == 1:
#                 return [(c,) for c in Choices.ChooseExactlyOne(options)]
#             else:
#                 return Choices.ChooseExactlyN(options, self.num_to_choose)
#         else:
#             return Choices.ChooseNOrFewer(options, self.num_to_choose)
# 
# # ----------
# 
# class ChooseOneCardboard(Chooser):
#     def __init__(self, getter:CardboardList):
#         super().__init__()
#         self.getter = getter
#         self.num_to_choose = 1
#         self.can_be_less = False
# =============================================================================

    
        
