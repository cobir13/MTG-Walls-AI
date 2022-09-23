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
    from Stack import StackObject

    TARGET = int | Cardboard | StackObject

import Pilots
import Match
import Zone


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------

class Getter:
    def __init__(self, gives_single_output: bool):
        self.single_output: bool = gives_single_output  # TODO: obsolete?

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


class CardsFrom(Getter):
    """Returns a list of cards (Cardboards) from the
    given zone. Handes the zone being relative rather
    than absolute, if needed."""

    def __init__(self, zone_or_zones: Zone.Zone | List[Zone.Zone]):
        super().__init__(True)
        if not isinstance(zone_or_zones, list):
            zone_or_zones = [zone_or_zones]
        self.zones: List[Zone.Zone] = zone_or_zones

    def get(self, state: GameState, player: int, source: Cardboard
            ) -> List[Cardboard]:
        cards: List[Cardboard] = []
        for z in self.zones:
            for z2 in z.get_absolute_zones(state, player, source):
                cards += z2.get(state)
        return cards

    def __str__(self):
        return "+".join([str(z) for z in self.zones])


class PlayerList(Getter):
    def __init__(self):
        super().__init__(True)

    def get(self, state: GameState, player: int, source: Cardboard
            ) -> List[Player]:
        return state.player_list


class StackList(Getter):
    def __init__(self):
        super().__init__(True)

    def get(self, state: GameState, player: int, source: Cardboard
            ) -> List[StackObject]:
        return state.stack


# ---------------------------------------------------------------------------

class You(PlayerList):
    """Returns list of the player matching the pattern
    Match.You (which is, the player calling `get`)."""

    def get(self, state: GameState, player: int, source: Cardboard
            ) -> List[Player]:
        return [pl for pl in super().get(state, player, source)
                if Match.You().match(pl, state, player, source)]


class Opponents(PlayerList):
    """Returns list of the player matching the pattern
    Match.Opponent (which is, all opponents of the player
    calling `get`)."""

    def get(self, state: GameState, player: int, source: Cardboard
            ) -> List[Player]:
        return [pl for pl in super().get(state, player, source)
                if Match.Opponent().match(pl, state, player, source)]


class Owners(PlayerList):
    """Returns list of the player matching the pattern
    Match.Owner (which is, the player who owns the
    asking Cardboard)."""

    def get(self, state: GameState, player: int, source: Cardboard
            ) -> List[Player]:
        return [pl for pl in super().get(state, player, source)
                if Match.Owner().match(pl, state, player, source)]


class Controllers(PlayerList):
    """Returns list of the player matching the pattern
    Match.Owner (which is, the player who controlls the
    asking Cardboard)."""

    def get(self, state: GameState, player: int, source: Cardboard
            ) -> List[Player]:
        return [pl for pl in super().get(state, player, source)
                if Match.Controller().match(pl, state, player, source)]


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


class ConstBool(Const, Bool):
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


class CanAttack(Bool):
    """Whether the source card, controlled by the given player, can attack
    right now."""
    def get(self, state: GameState, player: int, source: Cardboard):
        is_critter = Match.CardType(Creature).match(self.subject, state,
                                                    self.player, self.source)
        is_sick = self.subject.summon_sick
        has_haste = Match.Keyword("haste").match(self.subject, state,
                                                 self.player, self.source)


        to_check = self.zone.get_absolute_zones(state, player, source)
        return sum([len([c for c in zone.get(state)
                         if self.pattern.match(c, state, player, source)])
                    for zone in to_check])


# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class AllWhich:
    """return subsets of the given list, of all objects
     which match the specified pattern."""

    def __init__(self, pattern_for_valid: Match.Pattern):
        self.pattern = pattern_for_valid
        self.single_output = True

    def pick(self, options, state: GameState, player: int, card: Cardboard
             ) -> List[tuple]:
        """
        options: list of options. OR, duck-typed object with a
            method get(GameState, int, Cardboard)->list to
            return a list of options. FromZone is an example
            of this sort of object.
        state: GameState for context
        player: player index for context
        card: source Cardboard for context
        Returns all valid selections from among the given options.
        Specifically, returns a list of tuples, each of which are
        a set of mutually valid options. `self.single_output`
        describes whether it returns one tuple or many.
        """
        if not isinstance(options, list):
            options = options.get(state, player, card)
        sub_list = [obj for obj in options
                    if self.pattern.match(obj, state, player, card)]
        return [tuple(sub_list)]  # turn sub-list into tuple, wrap into list

    def __str__(self):
        return "each where " + str(self.pattern)


class All(AllWhich):
    def __init__(self):
        super().__init__(Match.Anything())

    def __str__(self):
        return "all of "


class Chooser(AllWhich):

    def __init__(self, pattern_for_valid: Match.Pattern,
                 num_to_choose: Integer | int, can_be_fewer: bool):
        super().__init__(pattern_for_valid)
        self.single_output = False
        if isinstance(num_to_choose, int):
            num_to_choose = ConstInteger(num_to_choose)
        self.num_to_choose: Integer = num_to_choose
        self.can_be_less = can_be_fewer

    def pick(self, options, state: GameState, player: int, card: Cardboard
             ) -> List[tuple]:
        """returns a list of all choices that have been selected. Each element
        of the list is a tuple of length N, where N is the number of items
        requested."""
        options: tuple = super().pick(options, state, player, card)[0]
        num = self.num_to_choose.get(state, player, card)
        decider = state.player_list[player].pilot
        if self.can_be_less:
            return decider.choose_n_or_fewer(options, num)
        else:
            if num == 1:
                return [(c,) for c in decider.choose_exactly_one(options)]
            else:
                return decider.choose_exactly_n(options, num)
        # TODO: add equivalence screening?

    def __str__(self):
        less_ok = "<=" if self.can_be_less else ""
        n = str(self.num_to_choose)
        return "Choose %s%s of " % (less_ok, n)


class Target(Chooser):
    pass


class Any(Chooser):
    """Choose any one option from the given list of options"""
    def __init__(self, pattern_for_valid: Match.Pattern | None):
        if pattern_for_valid is None:
            pattern_for_valid = Match.Anything()
        super().__init__(pattern_for_valid, 1, False)
