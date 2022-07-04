# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from typing import List
from Cardboard import Cardboard
from RulesText import RulesText
import Getters as Get


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


class CardPattern:
    def match(self, card:Cardboard, gamestate, source) -> bool:
        raise Exception

class CardType(CardPattern):
    def __init__(self, card_type:RulesText):
        self.type_to_match = card_type
    def match(self, card, gamestate, source):
        return isinstance(card,self.type_to_match)
    
class Keyword(CardPattern):
    def __init__(self, keyword:str):
        self.keyword_to_match = keyword
    def match(self, card, gamestate, source):
        return self.keyword_to_match in Get.Keywords(gamestate,card)

class Name(CardPattern):
    def __init__(self, name:str):
        self.name_to_match = name
    def match(self, card, gamestate, source):
        return self.name_to_match == Get.Name(gamestate,card)

# class Zone(CardPattern):
#     def __init__(self, zone):
#         self.zone = zone
#     def match(self, card):
#         self.zone == card.zone

class Counter(CardPattern):
    def __init__(self, counter_to_match:str):
        self.counter_to_match = counter_to_match
    def match(self, card, gamestate, source=None):
        return self.counter_to_match in Get.Counters(gamestate,card)

class Tapped(CardPattern):
    def match(self, card, gamestate, source=None):
        return Get.IsTapped(gamestate,card)

class Untapped(CardPattern):
    def match(self, card, gamestate, source=None):
        return Get.IsUntapped(gamestate,card)

class NotSelf(CardPattern):
    def match(self, card, gamestate, source):
        return not (card is source)

class IsSelf(CardPattern):
    def match(self, card, gamestate, source):
        return card is source

class NumericPattern(CardPattern):
    """ 'card comparator value' """
    def __init__(self, comparator:str, value:int, getter:Get.Integer):
        assert(comparator in [">","<","=","==","<=",">=","!=",])
        self.comparator = comparator
        self.value = value
        self.getter = getter
    def match(self, card, gamestate, source):
        card_value = self.getter.get(gamestate,card)
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
    def __init__(self, comparator:str, value:int):
        super().__init__(comparator, value, Get.Power())
        
class Toughness(NumericPattern):
    """ 'card comparator value' """
    def __init__(self, comparator:str, value:int):
        super().__init__(comparator, value, Get.Toughness())

class ManaValue(NumericPattern):
    """ 'card comparator value' """
    def __init__(self, comparator:str, value:int):
        super().__init__(comparator, value, Get.ManaValue())



