# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Cardboard import Cardboard
    # from RulesText import RulesText
    from GameState import GameState
import Getters as Get


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


class CardPattern:
    def match(self, card: Cardboard, gamestate: GameState, source) -> bool:
        raise Exception

    def __str__(self):
        return type(self).__name__


class CardType(CardPattern):
    def __init__(self, card_type: type):
        self.type_to_match: type = card_type

    def match(self, card, gamestate, source):
        return card.has_type(self.type_to_match)

    def __str__(self):
        return super().__str__() + "(" + self.type_to_match.__name__ + ")"


class Keyword(CardPattern):
    def __init__(self, keyword: str):
        self.keyword_to_match = keyword

    def match(self, card, gamestate, source):
        return self.keyword_to_match in Get.Keywords().get(gamestate, card)

    def __str__(self):
        return super().__str__() + "(" + self.keyword_to_match + ")"


class Name(CardPattern):
    def __init__(self, name: str):
        self.name_to_match = name

    def match(self, card, gamestate, source):
        return self.name_to_match == Get.Name().get(gamestate, card)

    def __str__(self):
        return super().__str__() + "(" + self.name_to_match + ")"


# class Zone(CardPattern):
#     def __init__(self, zone):
#         self.zone = zone
#     def match(self, card):
#         self.zone == card.zone

class Counter(CardPattern):
    def __init__(self, counter_to_match: str):
        self.counter_to_match = counter_to_match

    def match(self, card, gamestate, source=None):
        return self.counter_to_match in Get.Counters().get(gamestate, card)

    def __str__(self):
        return super().__str__() + "(" + self.counter_to_match + ")"


class Tapped(CardPattern):
    def match(self, card, gamestate, source=None):
        return Get.IsTapped().get(gamestate, card)


class Untapped(CardPattern):
    def match(self, card, gamestate, source=None):
        return Get.IsUntapped().get(gamestate, card)


class NotSelf(CardPattern):
    def match(self, card, gamestate, source):
        return not (card is source)


class IsSelf(CardPattern):
    def match(self, card, gamestate, source):
        return card is source


class NumericPattern(CardPattern):
    """ 'card comparator value' """

    def __init__(self, comparator: str, value: int, getter: Get.Integer):
        assert (comparator in [">", "<", "=", "==", "<=", ">=", "!=", ])
        self.comparator = comparator
        self.value = value
        self.getter = getter

    def match(self, card, gamestate, source):
        card_value = self.getter.get(gamestate, card)
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

    def __str__(self):
        txt = "(%s %s %s)" % (str(self.getter), self.comparator, self.value)
        return super().__str__() + txt


class Power(NumericPattern):
    """ 'card comparator value' """

    def __init__(self, comparator: str, value: int):
        super().__init__(comparator, value, Get.Power())


class Toughness(NumericPattern):
    """ 'card comparator value' """

    def __init__(self, comparator: str, value: int):
        super().__init__(comparator, value, Get.Toughness())


class ManaValue(NumericPattern):
    """ 'card comparator value' """

    def __init__(self, comparator: str, value: int):
        super().__init__(comparator, value, Get.ManaValue())
