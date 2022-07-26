# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from Cardboard import Cardboard
    # from RulesText import RulesText
    from state import state
    from Verbs import SUBJECT, INPUT
import Getters as Get


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------

class Pattern:
    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        """Does the subject match this pattern, as measured
        in the given state and asked by the given asker?"""
        raise Exception
    
    def __str__(self):
        return type(self).__name__

    def __and__(self, other):
        return _AllOf([self, other])

    def __or__(self, other):
        return _AnyOf([self, other])

    def __invert__(self):
        return _Negated(self)


class _AnyOf(Pattern):
    """A pattern which returns true if the card matches ANY
        (rather than all) of the given pattern."""
    def __init__(self, patterns: List[Pattern]):
        self.patterns = patterns

    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return any([p.match(subject, state, asker) for p in self.patterns])

    def __str__(self):
        return " or ".join([str(p) for p in self.patterns])


class _AllOf(Pattern):
    """A pattern which returns true if the card matches ALL
        the given pattern."""
    def __init__(self, patterns: List[Pattern]):
        self.patterns = patterns

    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return all([p.match(subject, state, asker) for p in self.patterns])

    def __str__(self):
        return " and ".join([str(p) for p in self.patterns])


class _Negated(Pattern):
    def __init__(self, pattern: Pattern):
        self.pattern = pattern

    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return not self.pattern.match(subject, state, asker)

    def __str__(self):
        return "not " + str(self.pattern)


class Anything(Pattern):
    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return True

    def __str__(self):
        return ""


class Nothing(Pattern):
    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return False

    def __str__(self):
        return ""


# ----------

class YouControl(Pattern):
    def match(self, subject: Cardboard, state, asker: INPUT) -> bool:
        return subject.player_index == asker.player_index


class CardType(Pattern):
    def __init__(self, card_type: type):
        self.type_to_match: type = card_type

    def match(self, subject: SUBJECT, state, asker: INPUT) -> bool:
        return subject.has_type(self.type_to_match)

    def __str__(self):
        return super().__str__() + "(" + self.type_to_match.__name__ + ")"


class Keyword(Pattern):
    def __init__(self, keyword: str):
        self.keyword_to_match = keyword

    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return self.keyword_to_match in Get.Keywords().get(state, subject)

    def __str__(self):
        return super().__str__() + "(" + self.keyword_to_match + ")"


class Name(Pattern):
    def __init__(self, name: str):
        self.name_to_match = name

    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return self.name_to_match == Get.CardName().get(state, subject)

    def __str__(self):
        return super().__str__() + "(" + self.name_to_match + ")"


# class Zone(Pattern):
#     def __init__(self, zone):
#         self.zone = zone
#     def match(self, card):
#         self.zone == card.zone

class Counter(Pattern):
    def __init__(self, counter_to_match: str):
        self.counter_to_match = counter_to_match

    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return self.counter_to_match in Get.Counters().get(state, subject)

    def __str__(self):
        return super().__str__() + "(" + self.counter_to_match + ")"


class Tapped(Pattern):
    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return Get.IsTapped().get(state, subject)


class Untapped(Pattern):
    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return Get.IsUntapped().get(state, subject)


class Another(Pattern):
    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return not (subject is asker)


class IsSelf(Pattern):
    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        return subject is asker


class NumericPattern(Pattern):
    """ 'card comparator value' """

    def __init__(self, comparator: str, value: int, getter: Get.Integer):
        assert (comparator in [">", "<", "=", "==", "<=", ">=", "!=", ])
        self.comparator = comparator
        self.value = value
        self.getter = getter

    def match(self, subject: SUBJECT, state: state, asker: INPUT) -> bool:
        card_value = self.getter.get(state, subject)
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

