# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""
from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard
    from Stack import StackObject

    TARGET = int | Cardboard | StackObject

import Choices
import Match as Match
import ZONE


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------

class GetTrait:
    def __init__(self):
        self.single_output: bool = True

    def get(self, state: GameState, player: int, source: Cardboard):
        raise Exception

    def __str__(self):
        return type(self).__name__


# class GlobalGetter(GetTrait):
#     """Doesn't need a asking_card card, just a GameState"""
#     def get(self, state: GameState):
#         raise Exception
#
#
# class PlayerGetter(GetTrait):
#     """Needs a asking_player and a GameState"""
#     def get(self, state: GameState):
#         raise Exception
#
#
# class SpecificGetter(GetTrait):
#     """Needs a specific comparator card and a GameState"""
#     def get(self, state: GameState):
#         raise Exception


class Const(GetTrait):
    def __init__(self, value):
        super().__init__()
        self.value = value

    def get(self, state: GameState, player: int, source: Cardboard):
        return self.value

    def __str__(self):
        return str(self.value)


class Integer(GetTrait):
    pass


class ConstInteger(Const, Integer):
    pass


class StringList(GetTrait):
    pass


class Bool(GetTrait):
    pass


class String(GetTrait):
    pass


class ConstString(Const, String):
    pass


# ----------

# class GetManaCost(GetTrait):
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

    def get(self, state: GameState, player: int, source: Cardboard):
        return self.string_to_copy * self.num_to_copy.get(state, player,
                                                          source)


# ----------


class Count(Integer):
    """Get the number of Cardboards which match all given pattern.
    NOTE: checks all Players' zones, so be sure to include the
    pattern for "YouControl" or similar."""

    def __init__(self, pattern: Match.Pattern, zone):
        super().__init__()
        self.pattern = pattern
        self.zone = zone

    def get(self, state: GameState, player: int, source: Cardboard):
        zone = state.get_zone(self.zone, None)
        return len([c for c in zone if
                    self.pattern.match(c, state, player, source)])

    def __str__(self):
        return super().__str__() + "(" + str(self.pattern) + ")"


# ----------

class Keywords(StringList):
    def get(self, state: GameState, player: int, source: Cardboard
            ) -> List[str]:
        try:
            return source.rules_text.keywords
        except AttributeError:
            return []


class CardName(String):
    def get(self, state: GameState, player: int, source: Cardboard) -> str:
        try:
            return source.rules_text.name
        except AttributeError:
            return ""


class Counters(StringList):
    def get(self, state: GameState, player: int, source: Cardboard
            ) -> List[str]:
        try:
            return source.counters
        except AttributeError:
            return []


class IsTapped(Bool):
    def get(self, state: GameState, player: int, source: Cardboard) -> bool:
        try:
            return source.tapped
        except AttributeError:
            return False


class IsUntapped(Bool):
    def get(self, state: GameState, player: int, source: Cardboard) -> bool:
        try:
            return not source.tapped
        except AttributeError:
            return False


class Power(Integer):
    def get(self, state: GameState, player: int, source: Cardboard) -> int:
        try:
            modifier = sum([int(v[:v.index("/")])
                            for v in Counters().get(state, player, source)
                            if "/" in v])
            return source.rules_text.power + modifier
        except AttributeError:
            return 0


class Toughness(Integer):
    def get(self, state: GameState, player: int, source: Cardboard) -> int:
        try:
            modifier = sum([int(v[v.index("/") + 1:])
                            for v in source.counters if "/" in v])
            return source.rules_text.toughness + modifier
        except AttributeError:
            return 0


class ManaValue(Integer):
    """ 'card comparator value' """

    def get(self, state: GameState, player: int, source: Cardboard) -> int:
        try:
            return source.rules_text.mana_value
        except AttributeError:
            return 0


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


class GetMatches:
    """Parent function, for getting every Player (well, asking_player
    index really) or Cardboard which matches the given Pattern.
    Not super efficient, necessarily, and may be cumbersome.
    Subclasses are generally more efficient."""

    def __init__(self, pattern: Match.Pattern):
        self.pattern: Match.Pattern = pattern

    def get_options(self, state: GameState, asking_player: int,
                    asking_card: Cardboard | None) -> List[TARGET]:
        # get all players and cards which might possibly match
        options: List[TARGET] = []
        if self.pattern.has_type(Match.PlayerPattern):
            for ii, player in enumerate(state.player_list):
                if self.pattern.match(player, state, asking_player,
                                      asking_card):
                    options.append(ii)
        if self.pattern.has_type(Match.CardPattern):
            # check the relevant zones
            for zone_pattern in self.pattern.get_type(Match.Zone):
                # check ALL players' zones
                for card in state.get_zone(zone_pattern.zone, None):
                    if self.pattern.match(card, state, asking_player,
                                          asking_card):
                        options.append(card)
        return options


class FromZones(GetMatches):
    def __init__(self, zone_list: list, pattern: Match.Pattern,
                 yours: bool = False, opponents: bool = False):
        super().__init__(pattern)
        self.you_control = yours
        self.opponent_controls = opponents
        assert yours or opponents
        self.zones = zone_list

    def get_options(self, state: GameState, asking_player: int,
                    asking_card: Cardboard | None) -> List[Cardboard]:
        options = []
        for player in range(len(state.player_list)):
            is_you = player == asking_player
            if (self.you_control and is_you) or (self.opponent_controls
                                                 and not is_you):
                for zone in self.zones:
                    for card in state.get_zone(zone, player):
                        if self.pattern.match(card, state, asking_player,
                                              asking_card):
                            options.append(card)
        return options

    def __str__(self):
        return type(self).__name__


class FromPlay(FromZones):
    def __init__(self, pattern: Match.Pattern):
        yours = pattern.has_type(Match.YouControl)
        opps = pattern.has_type(Match.OppControls)
        super().__init__([ZONE.FIELD], pattern, yours, opps)


class TopOfDeck(FromZones):
    """Get all cards from top of deck which match all given pattern"""

    def __init__(self, get_depth: Integer | int, pattern: Match.Pattern):
        yours = pattern.has_type(Match.YouControl)
        opps = pattern.has_type(Match.OppControls)
        super().__init__([ZONE.DECK], pattern, yours, opps)
        if isinstance(get_depth, int):
            get_depth = ConstInteger(get_depth)
        self.depth = get_depth

    def get_options(self, state: GameState, asking_player: int,
                    asking_card: Cardboard | None) -> List[Cardboard]:
        num_deep = self.depth.get(state, asking_player, asking_card)
        options = []
        for ii, player in enumerate(state.player_list):
            is_you = ii == asking_player
            if (self.you_control and is_you) or (self.opponent_controls
                                                 and not is_you):
                for card in player.deck[:num_deep]:
                    if self.pattern.match(card, state, asking_player,
                                          asking_card):
                        options.append(card)
        return options

    def __str__(self):
        return "Top%ofDeck" % str(self.depth)


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class Chooser:

    def __init__(self, options: GetMatches | list,
                 num_to_choose: Integer | int, can_be_fewer: bool):
        self.options: list | GetMatches = options
        if isinstance(num_to_choose, int):
            num_to_choose = ConstInteger(num_to_choose)
        self.num_to_choose = num_to_choose
        self.can_be_less = can_be_fewer

    def get(self, state: GameState, asking_player: int,
            asking_card: Cardboard) -> List[tuple]:
        """returns a list of all choices that have been selected. Each element
        of the list is a tuple of length N, where N is the number of items
        requested."""
        options = self.options
        if isinstance(self.options, GetMatches):
            options = self.options.get_options(state, asking_player,
                                               asking_card)
        num = self.num_to_choose.get(state, asking_player, asking_card)
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
        return "Choose(%s%s from %s)" % (less_ok, n, str(self.options))


class Target(Chooser):
    pass


class Choose(Chooser):
    pass


class You(Chooser):
    def __init__(self):
        super().__init__([], 1, False)

    def get(self, state: GameState, asking_player: int,
            asking_card: Cardboard) -> List[tuple]:
        return [(asking_player,)]

    def __str__(self):
        return "You"


class Itself(Chooser):
    def __init__(self):
        super().__init__([], 1, False)

    def get(self, state: GameState, asking_player: int,
            asking_card: Cardboard) -> List[tuple]:
        return [(asking_card,)]

    def __str__(self):
        return "Self"
