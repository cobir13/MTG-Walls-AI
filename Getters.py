# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard
    # from ManaHandler import ManaCost

import Choices
import MatchCardPatterns as Match


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------

class Getter:
    def get(self, state: GameState, source: Cardboard):
        raise Exception

    @property
    def single_output(self):
        return True

    def __str__(self):
        return type(self).__name__


class Const(Getter):
    def __init__(self, value):
        self.value = value

    def get(self, state: GameState, source: Cardboard):
        return self.value

    def __str__(self):
        return str(self.value)


class CardSingle(Getter):
    pass


class CardList(Getter):
    pass


class Integer(Getter):
    pass


class ConstInteger(Const, Integer):
    pass


class StringList(Getter):
    pass


class Bool(Getter):
    pass


class String(Getter):
    pass


# ----------

# class GetManaCost(Getter):
#     def get(self, state: GameState, source: Cardboard) -> ManaCost:
#         raise Exception
#
#     @property
#     def single_output(self):
#         return True

# ----------


class NumberInZone(Integer):
    """Get the number of Cardboards which match all given patterns"""

    def __init__(self, patterns: List[Match.CardPattern], zone):
        super().__init__()
        self.patterns = patterns
        self.zone = zone

    def get(self, state: GameState, source: Cardboard):
        zone = state.get_zone(self.zone)
        return len([c for c in zone if all([p.match(c, state, source)
                                            for p in self.patterns])])

    def __str__(self):
        patterns = ",".join([str(p) for p in self.patterns])
        return super().__str__() + "(" + patterns + ")"

# ----------


class ListFromZone(CardList):
    """Get all cards from `zone` which match all given patterns"""
    def __init__(self, patterns: List[Match.CardPattern], zone):
        super().__init__()
        self.patterns = patterns
        self.zone = zone

    def get(self, state: GameState, source: Cardboard) -> List[Cardboard]:
        zone = state.get_zone(self.zone)
        return [c for c in zone if all([p.match(c, state, source)
                                        for p in self.patterns])]


# ----------


class ListTopOfDeck(CardList):
    """Get all cards from top of deck which match all given patterns"""
    def __init__(self, patterns: List[Match.CardPattern],
                 get_depth: Integer | int):
        super().__init__()
        self.patterns = patterns
        if isinstance(get_depth, int):
            get_depth = ConstInteger(get_depth)
        self.get_depth = get_depth

    def get(self, state: GameState, source: Cardboard) -> List[Cardboard]:
        num_of_cards_deep = self.get_depth.get(state, source)
        top_of_deck = state.deck[:num_of_cards_deep]
        return [c for c in top_of_deck
                if all([p.match(c, state, source) for p in self.patterns])]

    def __str__(self):
        patterns = ",".join([str(p) for p in self.patterns])
        return super().__str__() + "(%s|%s" % (str(self.get_depth), patterns)

# ----------


class Keywords(StringList):
    def get(self, state: GameState, source: Cardboard) -> List[str]:
        return source.rules_text.keywords


class Name(String):
    def get(self, state: GameState, source: Cardboard) -> str:
        return source.rules_text.name


class Counters(StringList):
    def get(self, state: GameState, source: Cardboard) -> List[str]:
        return source.counters


class IsTapped(Bool):
    def get(self, state: GameState, source: Cardboard) -> bool:
        return source.tapped


class IsUntapped(Bool):
    def get(self, state: GameState, source: Cardboard) -> bool:
        return not source.tapped


class Power(Integer):
    def get(self, state: GameState, source: Cardboard) -> int:
        if hasattr(source.rules_text, "power"):
            modifier = sum([int(v[:v.index("/")])
                            for v in source.counters if "/" in v])
            return source.rules_text.power + modifier
        else:
            return 0


class Toughness(Integer):
    def get(self, state: GameState, source: Cardboard) -> int:
        if hasattr(source.rules_text, "toughness"):
            modifier = sum([int(v[v.index("/") + 1:])
                            for v in source.counters if "/" in v])
            return source.rules_text.toughness + modifier
        else:
            return 0


class ManaValue(Integer):
    """ 'card comparator value' """
    def get(self, state: GameState, source: Cardboard) -> int:
        return source.rules_text.mana_value


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


class Chooser(Getter):

    def __init__(self, getter: Getter, num_to_choose: Integer | int,
                 can_be_fewer: bool):
        self.getter = getter
        if isinstance(num_to_choose, int):
            num_to_choose = ConstInteger(num_to_choose)
        self.num_to_choose = num_to_choose
        self.can_be_less = can_be_fewer

    def get(self, state: GameState, source: Cardboard) -> List[tuple]:
        """returns a list of all choices that have been selected. Each element
        of the list is a tuple of length N, where N is the number of items
        requested."""
        options = self.getter.get(state, source)  # list of tuples of items
        num = self.num_to_choose.get(state, source)
        if self.can_be_less:
            return Choices.choose_n_or_fewer(options, num)
        else:
            if num == 1:
                return [(c,) for c in Choices.choose_exactly_one(options)]
            else:
                return Choices.choose_exactly_n(options, num)
        # TODO: add equivalence screening?

    @property
    def single_output(self):
        return False

    def __str__(self):
        less_ok = "<=" if self.can_be_less else ""
        n = str(self.num_to_choose)
        getter = str(self.getter)
        return "Choose(%s%s from %s)" % (less_ok, n, getter)
