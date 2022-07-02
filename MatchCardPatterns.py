# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from typing import List
from GameState import GameState
from Cardboard import Cardboard
from RulesText import RulesText,Creature
import ManaHandler
import Choices
import ZONE


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


class CardPattern:
    def match(self, card:Cardboard, gamestate=None, source=None) -> bool:
        raise Exception

class CardType(CardPattern):
    def __init__(self, card_type:RulesText):
        self.type_to_match = card_type
    def match(self, card, gamestate=None, source=None):
        return isinstance(card,self.type_to_match)
    
class Keyword(CardPattern):
    def __init__(self, keyword:str):
        self.keyword_to_match = keyword
    def match(self, card, gamestate=None, source=None):
        return self.keyword_to_match in card.rules_text.keywords

class Name(CardPattern):
    def __init__(self, name:str):
        self.name_to_match = name
    def match(self, card, gamestate=None, source=None):
        return self.name_to_match == card.rules_text.name

# class Zone(CardPattern):
#     def __init__(self, zone):
#         self.zone = zone
#     def match(self, card):
#         self.zone == card.zone

class Counter(CardPattern):
    def __init__(self, counter_to_match:str):
        self.counter_to_match = counter_to_match
    def match(self, card, gamestate=None, source=None):
        return self.counter_to_match in card.counters

class Tapped(CardPattern):
    def match(self, card, gamestate=None, source=None):
        return card.tapped

class Untapped(CardPattern):
    def match(self, card, gamestate=None, source=None):
        return not card.tapped

class NotSelf(CardPattern):
    def match(self, card, gamestate, source):
        return not (card is source)

class IsSelf(CardPattern):
    def match(self, card, gamestate, source):
        return card is source

class NumericPattern(CardPattern):
    """ 'card comparator value' """
    def __init__(self, comparator:str, value:int):
        assert(comparator in [">","<","=","==","<=",">=","!=",])
        self.comparator = comparator
        self.value = value
    def get_card_value(self,card:Cardboard):
        return None
    def match(self, card, gamestate=None, source=None):
        card_value = self.get_card_value(card)
        if card_value is None:
            return False
        if self.comparator == "=" or self.comparator == "==":
            return card_value == self.value 
        elif self.comparator == "<":
            return card_value < self.value
        elif self.comparator == "<=":
            return card_value <= self.value 
        elif self.comparator == ">":
            return card_value > self.value 
        elif self.comparator == ">=":
            return card_value >= self.value 
        elif self.comparator == "!=":
            return card_value != self.value
        else:
            raise ValueError("shouldn't be possible to get here!")
        
class Power(NumericPattern):
    """ 'card comparator value' """
    def get_card_value(self,card:Cardboard):
        if hasattr(card,"power"):
            return card.rules_text.power
        
class Toughness(NumericPattern):
    """ 'card comparator value' """
    def get_card_value(self,card:Cardboard):
        if hasattr(card,"toughness"):
            return card.rules_text.toughness

class ManaValue(NumericPattern):
    """ 'card comparator value' """
    def get_card_value(self,card:Cardboard):
        return card.rules_text.mana_value



