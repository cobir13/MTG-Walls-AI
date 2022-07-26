# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from GameState import GameState, Player
    from Cardboard import Cardboard
    # from ManaHandler import ManaCost
    from Verbs import INPUT, SUBJECT, CAUSE

import Choices
import Match as Match


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------

class Getter:
    def __init__(self):
        self.single_output: bool = True

    def get(self, state: GameState, asker: INPUT):
        raise Exception

    def __str__(self):
        return type(self).__name__


# class GlobalGetter(Getter):
#     """Doesn't need a source card, just a GameState"""
#     def get(self, state: GameState):
#         raise Exception
#
#
# class PlayerGetter(Getter):
#     """Needs a player and a GameState"""
#     def get(self, state: GameState):
#         raise Exception
#
#
# class SpecificGetter(Getter):
#     """Needs a specific comparator card and a GameState"""
#     def get(self, state: GameState):
#         raise Exception


class Const(Getter):
    def __init__(self, value):
        super().__init__()
        self.value = value

    def get(self, state: GameState, asker: INPUT):
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


class ConstString(Const, String):
    pass


# ----------

# class GetManaCost(Getter):
#     def get(self, state: GameState, asker: INPUT) -> ManaCost:
#         raise Exception
#
#     @property
#     def single_output(self):
#         return True

# ----------

class ForEach(String):
    def __init__(self, string_to_copy: str, num: Integer):
        super().__init__()
        self.string_to_copy = string_to_copy
        self.num_to_copy = num
        self.single_output = num.single_output

    def get(self, state: GameState, asker: INPUT):
        return self.string_to_copy * self.num_to_copy.get(state, asker)


# ----------


class Count(Integer):
    """Get the number of Cardboards which match all given pattern.
    NOTE: checks all Players' zones, so be sure to include the
    pattern for "YouControl" or similar."""

    def __init__(self, pattern: Match.Pattern, zone):
        super().__init__()
        self.pattern = pattern
        self.zone = zone

    def get(self, state: GameState, asker: INPUT):
        zone = state.get_zone(self.zone, None)
        return len([c for c in zone if self.pattern.match(c, state, asker)])

    def __str__(self):
        return super().__str__() + "(" + str(self.pattern) + ")"

# ----------


class ListFromZone(CardList):
    """Get all cards from `zone` which match all given pattern.
    NOTE: checks all Players' zones, so be sure to include the
    pattern for "YouControl" or similar."""
    def __init__(self, pattern: Match.Pattern, zone):
        super().__init__()
        self.pattern = pattern
        self.zone = zone

    def get(self, state: GameState, asker: INPUT):
        zone = state.get_zone(self.zone, None)
        return [c for c in zone if self.pattern.match(c, state, asker)]


# ----------


class ListTopOfDeck(CardList):
    """Get all cards from top of deck which match all given pattern"""
    def __init__(self, pattern: Match.Pattern, player_index: int,
                 get_depth: Integer | int):
        if isinstance(get_depth, int):
            get_depth = ConstInteger(get_depth)
        super().__init__()
        self.pattern = pattern
        self.get_depth = get_depth
        self.player_index = player_index
        self.single_output = get_depth.single_output

    def get(self, state: GameState, asker: INPUT) -> List[Cardboard]:
        num_of_cards_deep = self.get_depth.get(state, asker)
        deck = state.player_list[self.player_index].deck
        top_of_deck = deck[:num_of_cards_deep]
        return [c for c in top_of_deck if self.pattern.match(c, state, asker)]

    def __str__(self):
        return super().__str__() + "(%s|%s" % (str(self.get_depth),
                                               str(self.pattern))

# ----------


class Keywords(StringList):
    def get(self, state: GameState, asker: INPUT) -> List[str]:
        try:
            return asker.rules_text.keywords
        except AttributeError:
            return []


class CardName(String):
    def get(self, state: GameState, asker: INPUT) -> str:
        try:
            return asker.rules_text.name
        except AttributeError:
            return ""


class Counters(StringList):
    def get(self, state: GameState, asker: INPUT) -> List[str]:
        try:
            return asker.counters
        except AttributeError:
            return []


class IsTapped(Bool):
    def get(self, state: GameState, asker: INPUT) -> bool:
        try:
            return asker.tapped
        except AttributeError:
            return False


class IsUntapped(Bool):
    def get(self, state: GameState, asker: INPUT) -> bool:
        try:
            return not asker.tapped
        except AttributeError:
            return False


class Power(Integer):
    def get(self, state: GameState, asker: INPUT) -> int:
        try:
            modifier = sum([int(v[:v.index("/")])
                            for v in Counters().get(state, asker) if "/" in v])
            return asker.rules_text.power + modifier
        except AttributeError:
            return 0


class Toughness(Integer):
    def get(self, state: GameState, asker: INPUT) -> int:
        try:
            modifier = sum([int(v[v.index("/") + 1:])
                            for v in asker.counters if "/" in v])
            return asker.rules_text.toughness + modifier
        except AttributeError:
            return 0


class ManaValue(Integer):
    """ 'card comparator value' """
    def get(self, state: GameState, asker: INPUT) -> int:
        try:
            asker.rules_text.mana_value
        except AttributeError:
            return 0


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


class Chooser(Getter):

    def __init__(self, getter: Getter, num_to_choose: Integer | int,
                 can_be_fewer: bool):
        super().__init__()
        self.getter = getter
        if isinstance(num_to_choose, int):
            num_to_choose = ConstInteger(num_to_choose)
        self.num_to_choose = num_to_choose
        self.can_be_less = can_be_fewer
        self.single_output = False

    def get(self, state: GameState, asker: INPUT) -> List[tuple]:
        """returns a list of all choices that have been selected. Each element
        of the list is a tuple of length N, where N is the number of items
        requested."""
        options = self.getter.get(state, asker)  # list of tuples of items
        num = self.num_to_choose.get(state, asker)
        if self.can_be_less:
            return Choices.choose_n_or_fewer(options, num)
        else:
            if num == 1:
                return [(c,) for c in Choices.choose_exactly_one(options)]
            else:
                return Choices.choose_exactly_n(options, num)
        # TODO: add equivalence screening?

    def __str__(self):
        less_ok = "<=" if self.can_be_less else ""
        n = str(self.num_to_choose)
        getter = str(self.getter)
        return "Choose(%s%s from %s)" % (less_ok, n, getter)
