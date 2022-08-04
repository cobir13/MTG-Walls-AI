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
import Match
import Zone


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------

class Getter:
    def __init__(self, gives_single_output: bool):
        self.single_output: bool = gives_single_output

    def get(self, state: GameState, player: int, source: Cardboard):
        raise Exception

    def __str__(self):
        return type(self).__name__


class Const(Getter):
    """Returns a constant value, defined at initialization"""
    def __init__(self, value):
        Getter.__init__(self, gives_single_output=True)
        self.value = value

    def get(self, state: GameState, player: int, source: Cardboard):
        return self.value

    def __str__(self):
        return str(self.value)


class GetTrait(Getter):
    """Return the value of a specified trait, usually
    of the given source Cardboard but potentially of
    the given Player or GameState. Intended to check
    values which might be affected by static abilities
    etc.
    """
    def __init__(self):
        Getter.__init__(self, gives_single_output=True)


class GetCards(Getter):
    """Returns a list of cards (Cardboards) who match the given
    criteria. (Possibly empty, if no matches)."""

    def __init__(self, pattern_to_satisfy: Match.Pattern,
                 zone_or_zones: Zone.Zone | List[Zone.Zone]):
        super().__init__(True)
        if not isinstance(zone_or_zones, list):
            zone_or_zones = [zone_or_zones]
        self.zones: List[Zone.Zone] = zone_or_zones
        self.pattern: Match.Pattern = pattern_to_satisfy

    def get(self, state: GameState, player: int, source: Cardboard
            ) -> List[Cardboard]:
        zones_to_check = []
        for z in self.zones:
            zones_to_check += z.get_absolute_zones(state, player, source)
        cards: List[Cardboard] = []
        for z in zones_to_check:
            cards += [c for c in z.get(state)
                      if self.pattern.match(c, state, player, source)]
        return cards

    def __str__(self):
        return str(self.pattern) + " in " + ",".join([str(z)
                                                      for z in self.zones])


class GetPlayers(Getter):
    """Returns a list of players (ints) who match the given
    criteria. (Possibly empty, if no matches)."""
    def __init__(self, player_pattern: Match.PlayerPattern):
        super().__init__(gives_single_output=False)
        self.pattern = player_pattern

    def get(self, state: GameState, player, source) -> List[int]:
        return [p.player_index for p in state.player_list
                if self.pattern.match(p, state, player, source)]


# ---------------------------------------------------------------------------

class You(GetPlayers):
    """Returns list of the player matching the pattern
    Match.You (which is, the player calling `get`)."""
    def __init__(self):
        super().__init__(Match.You())


class Opponents(GetPlayers):
    """Returns list of the player matching the pattern
    Match.Opponent (which is, all opponents of the player
    calling `get`)."""
    def __init__(self):
        super().__init__(Match.Opponent())


class Owners(GetPlayers):
    """Returns list of the player matching the pattern
    Match.Owner (which is, the player who owns the
    asking Cardboard)."""
    def __init__(self):
        super().__init__(Match.Owner())


class Controllers(GetPlayers):
    """Returns list of the player matching the pattern
    Match.Owner (which is, the player who controlls the
    asking Cardboard)."""
    def __init__(self):
        super().__init__(Match.Controller())


# ---------------------------------------------------------------------------

class Integer(GetTrait):
    """Return type of the trait is an integer"""
    pass


class ConstInteger(Const, Integer):
    pass


class StringList(GetTrait):
    """Return type of the trait is a list of strings"""
    pass


class Bool(GetTrait):
    """Return type of the trait is a bool"""
    pass


class String(GetTrait):
    """Return type of the trait is a single string"""
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

class Repeat(Getter):
    """Basically a wrapper for `thing_to_repeat` * `num`.
    Useful for repeating a string, list, etc. Or
    multiplying a number, I guess."""
    def __init__(self, thing_to_repeat, num: Integer | int):
        Getter.__init__(self, gives_single_output=num.single_output)
        self.thing_to_repeat = thing_to_repeat
        if isinstance(num, int):
            num = ConstInteger(num)
        self.num: Integer = num

    def get(self, state: GameState, player: int, source: Cardboard):
        return self.thing_to_repeat * self.num.get(state, player, source)


class RepeatString(Repeat, String):
    def __init__(self, thing_to_repeat: str, num: Integer | int):
        super().__init__(thing_to_repeat, num)


# ----------

class Count(Integer):
    """Get the number of Cardboards which match all given pattern."""

    def __init__(self, pattern: Match.Pattern, zone: Zone.Zone):
        super().__init__()
        self.pattern: Match.Pattern = pattern
        self.zone: Zone.Zone = zone

    def get(self, state: GameState, player: int, source: Cardboard):
        to_check = self.zone.get_absolute_zones(state, player, source)
        return sum([len([c for c in zone.get(state)
                         if self.pattern.match(c, state, player, source)])
                    for zone in to_check])

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


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class Chooser(Getter):

    def __init__(self,
                 options: GetCards | GetPlayers | List[TARGET],
                 num_to_choose: Integer | int, can_be_fewer: bool):
        super().__init__(False)
        self.options: GetCards | GetPlayers | List[TARGET] = options
        if isinstance(num_to_choose, int):
            num_to_choose = ConstInteger(num_to_choose)
        self.num_to_choose: Integer = num_to_choose
        self.can_be_less = can_be_fewer

    def get(self, state: GameState, asking_player: int, asking_card: Cardboard
            ) -> List[Tuple[TARGET]]:
        """returns a list of all choices that have been selected. Each element
        of the list is a tuple of length N, where N is the number of items
        requested."""
        if isinstance(self.options, (GetCards, GetPlayers)):
            options: List[TARGET] = self.options.get(state, asking_player,
                                                     asking_card)
        else:
            options: List[TARGET] = self.options
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


class Any(Chooser):
    """choose any one single option. Exactly one."""
    def __init__(self, options: GetCards | GetPlayers | List[TARGET]):
        super().__init__(options, num_to_choose=1, can_be_fewer=False)


class Each(Chooser):
    def __init__(self, options: GetCards | GetPlayers):
        super().__init__(options, -1, False)

    def get(self, state: GameState, asking_player: int, asking_card: Cardboard
            ) -> List[Tuple[TARGET]]:
        """returns a list of all choices that have been selected. Each element
        of the list is a tuple of length N, where N is the number of items
        requested."""
        if isinstance(self.options, (GetCards, GetPlayers)):
            options: List[TARGET] = self.options.get(state, asking_player,
                                                     asking_card)
        else:
            options: List[TARGET] = self.options
        return [tuple(options)]

    def __str__(self):
        return "All %s" % str(self.options)
