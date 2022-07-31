# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List

import ZONE

if TYPE_CHECKING:
    from Cardboard import Cardboard
    from GameState import GameState, Player
    SUBJECT = Cardboard | Player  # | StackObject
import Getters as Get


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------

class Pattern:
    def match(self, subject: SUBJECT, state: GameState, player: int,
              source: Cardboard) -> bool:
        """Does the subject match this pattern, as measured
        in the given state and compared to the given asking_card
        Cardboard and given Player (player_index)?"""
        raise Exception

    def has_type(self, pattern_type: type) -> bool:
        return isinstance(self, pattern_type)

    def get_type(self, pattern_type: type) -> List[Pattern]:
        if isinstance(self, pattern_type):
            return [self]
        else:
            return []
    
    def __str__(self):
        return type(self).__name__

    def __and__(self, other_pattern):
        return _AllOf([self, other_pattern])

    def __or__(self, other_pattern):
        return _AnyOf([self, other_pattern])

    def __invert__(self):
        return _Negated(self)


class _AnyOf(Pattern):
    """A pattern which returns true if the card matches ANY
        (rather than all) of the given pattern."""
    def __init__(self, patterns: List[Pattern]):
        self.patterns: List[Pattern] = patterns

    def match(self, subject, state, player, source) -> bool:
        return any([p.match(subject, state, player, source)
                    for p in self.patterns])

    def has_type(self, pattern_type: type):
        return any([p.has_type(pattern_type) for p in self.patterns])

    def get_type(self, pattern_type: type):
        sub_patterns = []
        for p in self.patterns:
            sub_patterns += p.get_type(pattern_type)
        return sub_patterns

    def __str__(self):
        return " or ".join([str(p) for p in self.patterns])


class _AllOf(Pattern):
    """A pattern which returns true if the card matches ALL
        the given pattern."""
    def __init__(self, patterns: List[Pattern]):
        self.patterns = patterns

    def match(self, subject, state, player, source) -> bool:
        return all([p.match(subject, state, player, source)
                    for p in self.patterns])

    def has_type(self, pattern_type: type):
        return any([p.has_type(pattern_type) for p in self.patterns])

    def get_type(self, pattern_type: type):
        sub_patterns = []
        for p in self.patterns:
            sub_patterns += p.get_type(pattern_type)
        return sub_patterns

    def __str__(self):
        return " and ".join([str(p) for p in self.patterns])


class _Negated(Pattern):
    def __init__(self, pattern: Pattern):
        self.pattern = pattern

    def match(self, subject, state, player, source) -> bool:
        return not self.pattern.match(subject, state, player, source)

    def has_type(self, pattern_type: type):
        return self.pattern.has_type(pattern_type)

    def get_type(self, pattern_type: type):
        return self.pattern.get_type(pattern_type)

    def __str__(self):
        return "not " + str(self.pattern)


class Anything(Pattern):
    def match(self, subject, state, player, source) -> bool:
        return True

    def __str__(self):
        return ""


class Nothing(Pattern):
    def match(self, subject, state, player, source) -> bool:
        return False

    def __str__(self):
        return ""


# ----------

class CardPattern(Pattern):
    def match(self, subject: Cardboard, state: GameState, player: int,
              source: Cardboard) -> bool:
        """Subclasses should use try-except to catch
        AttributeErrors, in case of wrong `subject` type."""
        raise Exception


class PlayerPattern(Pattern):
    def match(self, subject: Player, state: GameState, player: int,
              source: Cardboard) -> bool:
        """Subclasses should use try-except to catch
        AttributeErrors, in case of wrong `subject` type."""
        raise Exception


# ----------

class CardType(CardPattern):
    def __init__(self, card_type: type):
        self.type_to_match: type = card_type

    def match(self, subject: Cardboard, state, player, source):
        try:
            return subject.has_type(self.type_to_match)
        except AttributeError:
            return False

    def __str__(self):
        return super().__str__() + "(" + self.type_to_match.__name__ + ")"


class Keyword(CardPattern):
    def __init__(self, keyword: str):
        self.keyword_to_match = keyword

    def match(self, subject: Cardboard, state, player, source):
        try:
            return self.keyword_to_match in Get.Keywords().get(state, player,
                                                               subject)
        except AttributeError:
            return False

    def __str__(self):
        return super().__str__() + "(" + self.keyword_to_match + ")"


class Name(CardPattern):
    def __init__(self, name: str):
        self.name_to_match = name

    def match(self, subject: Cardboard, state, player, source):
        try:
            return self.name_to_match == Get.CardName().get(state, player,
                                                            subject)
        except AttributeError:
            return False

    def __str__(self):
        return super().__str__() + "(" + self.name_to_match + ")"


class Counter(CardPattern):
    def __init__(self, counter_to_match: str):
        self.counter_to_match = counter_to_match

    def match(self, subject: Cardboard, state, player, source):
        try:
            return self.counter_to_match in subject.counters
        except AttributeError:
            return False

    def __str__(self):
        return super().__str__() + "(" + self.counter_to_match + ")"


class Tapped(CardPattern):
    def match(self, subject: Cardboard, state, player, source) -> bool:
        try:
            return subject.tapped
        except AttributeError:
            return False


class Untapped(CardPattern):
    def match(self, subject: Cardboard, state, player, source) -> bool:
        try:
            return not subject.tapped
        except AttributeError:
            return False


class Zone(CardPattern):
    def __init__(self, zone: int):
        self.zone = zone

    def match(self, subject: Cardboard, state, player, source):
        try:
            return subject.zone == self.zone
        except AttributeError:
            return False

    def __str__(self):
        if self.zone == ZONE.DECK or self.zone == ZONE.DECK_BOTTOM:
            return "InDeck"
        elif self.zone == ZONE.HAND:
            return "InHand"
        elif self.zone == ZONE.FIELD:
            return "OnField"
        elif self.zone == ZONE.GRAVE:
            return "InGrave"
        else:
            return "InZone%i" % self.zone


# ----------

class IsSelf(CardPattern):
    def match(self, subject: Cardboard, state, player, source) -> bool:
        return subject is source


class Another(CardPattern):
    def match(self, subject: Cardboard, state, player, source) -> bool:
        return subject is not source


class YouControl(CardPattern):
    def match(self, subject: Cardboard, state, player, source):
        if player is not None:
            return subject.player_index == player
        elif source is not None:
            return subject.player_index == source.player_index
        else:
            return False


class OppControls(CardPattern):
    def match(self, subject: Cardboard, state, player, source):
        if player is not None:
            return subject.player_index != player
        elif source is not None:
            return subject.player_index != source.player_index
        else:
            return False


class You(PlayerPattern):
    def match(self, subject: Player, state, player, source) -> bool:
        return subject.player_index == player


class Opponent(PlayerPattern):
    def match(self, subject: Player, state, player, source) -> bool:
        return subject.player_index != player


# ----------

class NumericPattern(Pattern):
    """ 'card comparator value' """

    def __init__(self, comparator: str, value: int, getter: Get.Integer):
        assert (comparator in [">", "<", "=", "==", "<=", ">=", "!=", ])
        self.comparator = comparator
        self.value = value
        self.getter = getter

    def match(self, subject: SUBJECT, state: GameState, player: int,
              source: Cardboard) -> bool:
        try:
            card_value = self.getter.get(state, player, subject)
        except AttributeError:
            return False
        else:
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
