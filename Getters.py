# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""
from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from GameState import GameState, Player
    from Cardboard import Cardboard
    from Stack import StackObject

    TARGET = int | Cardboard | StackObject
    TRAIT = int | Tuple[int, int] | str | List[str] | bool

import Match2
import Zone


# #--------------------------------------------------------------------------
# #--------------------------------------------------------------------------

class GetterQuery:
    """A convenient way to bundle a Getter along with the arguments
    being passed into it at the moment."""
    def __init__(self, getter, state, player, source):
        self.getter = getter
        self.state = state
        self.player = player
        self.source = source


class Getter:
    def get(self, state: GameState, player: int, source: Cardboard):
        """
        Return the value of the parameter or concept we are
        interested in. `state` is the GameState to look in,
        and `player` and `source` are the player and card
        which are causing us to look.
        For example, the card may have an ability which
        requires knowing the number of creatures in play. In
        that case, `source` is that card and `player` is the
        index of that card's controlling Player.
        The returned value takes into account any static
        effects which may change the result.
        """
        iterate_value = self._get(state, player, source)
        query = GetterQuery(self, state, player, source)
        for holder in state.statics + state.statics_to_remove:
            if holder.is_applicable(query, state):
                iterate_value = holder.get_new_value(iterate_value, state,
                                                     player, source)
        return iterate_value

    def _get(self, state: GameState, player: int, source: Cardboard):
        """The function which actually knows how to extract
        the desired value from the GameState."""
        raise NotImplementedError

    def __str__(self):
        return type(self).__name__


class GetInteger(Getter):
    """Return type of the Getter is an integer"""
    pass


class GetIntPair(Getter):
    """Return type of the Getter is a pair (tuple) of integers"""
    pass


class GetBool(Getter):
    """Return type of the Getter is a bool"""
    pass


class GetString(Getter):
    """Return type of the Getter is a single string"""
    pass


class GetStringList(Getter):
    """Return type of the Getter is a list of strings"""
    pass


class Const(Getter):
    """Returns a constant value, defined at initialization"""

    def __init__(self, value):
        self.value = value

    def _get(self, state: GameState, player: int, source: Cardboard):
        return self.value

    def __str__(self):
        return str(self.value)


class ConstString(Const, GetString):
    pass


class ConstStringList(Const, GetStringList):
    pass


class ConstBool(Const, GetBool):
    pass


class ConstInteger(Const, GetInteger):
    pass


class CardListFrom(Getter):
    """Returns a list of cards (Cardboards) from the
    given zone. Handes the zone being relative rather
    than absolute, if needed."""

    def __init__(self, zone_or_zones: Zone.Zone | List[Zone.Zone]):
        if not isinstance(zone_or_zones, list):
            zone_or_zones = [zone_or_zones]
        self.zones: List[Zone.Zone] = zone_or_zones

    def _get(self, state: GameState, player: int, source: Cardboard
             ) -> List[Cardboard]:
        cards: List[Cardboard] = []
        for z in self.zones:
            for z2 in z.get_absolute_zones(state, player, source):
                cards += z2.get(state)
        return cards

    def __str__(self):
        return "+".join([str(z) for z in self.zones])


class PlayerList(Getter):
    def _get(self, state: GameState, player: int, source: Cardboard
             ) -> List[Player]:
        return state.player_list


class StackList(Getter):
    def _get(self, state: GameState, player: int, source: Cardboard
             ) -> List[StackObject]:
        return state.stack


# ---------------------------------------------------------------------------

class You(PlayerList):
    """Returns list of the player matching the pattern
    Match2.You (which is, the player calling `get`)."""

    def _get(self, state: GameState, player: int, source: Cardboard
             ) -> List[Player]:
        return [pl for pl in super()._get(state, player, source)
                if Match2.You().match(pl, state, player, source)]


class Opponents(PlayerList):
    """Returns list of the player matching the pattern
    Match2.Opponent (which is, all opponents of the player
    calling `get`)."""

    def _get(self, state: GameState, player: int, source: Cardboard
             ) -> List[Player]:
        return [pl for pl in super()._get(state, player, source)
                if Match2.Opponent().match(pl, state, player, source)]


class Owners(PlayerList):
    """Returns list of the player matching the pattern
    Match2.Owner (which is, the player who owns the
    asking Cardboard)."""

    def _get(self, state: GameState, player: int, source: Cardboard
             ) -> List[Player]:
        return [pl for pl in super()._get(state, player, source)
                if Match2.Owner().match(pl, state, player, source)]


class Controllers(PlayerList):
    """Returns list of the player matching the pattern
    Match2.Owner (which is, the player who controlls the
    asking Cardboard)."""

    def _get(self, state: GameState, player: int, source: Cardboard
             ) -> List[Player]:
        return [pl for pl in super()._get(state, player, source)
                if Match2.Controller().match(pl, state, player, source)]


# ---------------------------------------------------------------------------


# ----------

# class GetManaCost(GetTrait):
#     def _get(self, state: GameState, asker: INPUT) -> ManaCost:
#         raise Exception
#

# ----------

class Count(GetInteger):
    """Get the number of Cardboards which match all given pattern."""

    def __init__(self, pattern: Match2.CardPattern, zone: Zone.Zone):
        super().__init__()
        self.pattern: Match2.CardPattern = pattern
        self.zone: Zone.Zone = zone

    def _get(self, state: GameState, player: int, source: Cardboard) -> int:
        to_check = self.zone.get_absolute_zones(state, player, source)
        return sum([len([c for c in zone.get(state)
                         if self.pattern.match(c, state, player, source)])
                    for zone in to_check])

    def __str__(self):
        return super().__str__() + "(" + str(self.pattern) + ")"


# ----------

class Keywords(GetStringList):
    def _get(self, state: GameState, player: int, source: Cardboard
             ) -> List[str]:
        try:
            return source.rules_text.keywords
        except AttributeError:
            return []


class CardTypes(GetStringList):
    def _get(self, state, player, source) -> List[str]:
        try:
            return source.rules_text.cardtypes
        except AttributeError:
            return []


class CardName(GetString):
    def _get(self, state: GameState, player: int, source: Cardboard) -> str:
        try:
            return source.rules_text.name
        except AttributeError:
            return ""


class Counters(GetStringList):
    def _get(self, state: GameState, player: int, source: Cardboard
             ) -> List[str]:
        try:
            return source.counters
        except AttributeError:
            return []


class IsTapped(GetBool):
    def _get(self, state: GameState, player: int, source: Cardboard) -> bool:
        try:
            return source.tapped
        except AttributeError:
            return False


class CanTapSymbol(GetBool):
    def _get(self, state: GameState, player: int, source: Cardboard) -> bool:
        is_creature = "creature" in CardTypes().get(state, player, source)
        is_hasty = "haste" in Keywords().get(state, player, source)
        try:
            is_sick = source.summon_sick
        except AttributeError:
            is_sick = False
        is_tapped = IsTapped().get(state, player, source)
        return (not is_creature or is_hasty or not is_sick) and not is_tapped


class PowerAndTough(GetIntPair):
    def _get(self, state: GameState, player: int, source: Cardboard
             ) -> Tuple[int, int]:
        try:
            power_mod = sum([int(v[:v.index("/")])
                             for v in Counters().get(state, player, source)
                             if "/" in v])
            tough_mod = sum([int(v[v.index("/") + 1:])
                             for v in Counters().get(state, player, source)
                             if "/" in v])
            power = source.rules_text.power + power_mod
            toughness = source.rules_text.toughness + tough_mod
            return power, toughness
        except AttributeError:
            return 0, 0


class Power(GetInteger):
    # Overrides get (not _get), because uses PowerAndTough rather than own _get
    def get(self, state: GameState, player: int, source: Cardboard):
        return PowerAndTough().get(state, player, source)[0]


class Toughness(GetInteger):
    # Overrides get (not _get), because uses PowerAndTough rather than own _get
    def get(self, state: GameState, player: int, source: Cardboard):
        return PowerAndTough().get(state, player, source)[1]


class ManaValue(GetInteger):
    def _get(self, state: GameState, player: int, source: Cardboard) -> int:
        try:
            return source.rules_text.mana_value
        except AttributeError:
            return 0


# class CanAttack(GetBool):
#     """Whether the source card, controlled by the given player, can attack
#     right now."""
#     def _get(self, state: GameState, player: int, source: Cardboard):
#         is_critter = Match2.CardType(Creature).match(self.subject, state,
#                                                     self.player, self.source)
#         is_sick = self.subject.summon_sick
#         has_haste = Match2.Keyword("haste").match(self.subject, state,
#                                                  self.player, self.source)
#
#
#         to_check = self.zone.get_absolute_zones(state, player, source)
#         return sum([len([c for c in zone.get(state)
#                          if self.pattern.match(c, state, player, source)])
#                     for zone in to_check])



# ---------------------------------------------------------------------------


class Repeat(Getter):
    """Basically a wrapper for `thing_to_repeat` * `num`.
    Useful for repeating a string, list, etc. Or
    multiplying a number, I guess."""

    def __init__(self, thing_to_repeat, num: GetInteger | int):
        self.thing_to_repeat = thing_to_repeat
        if isinstance(num, int):
            num = ConstInteger(num)
        self.num: GetInteger = num

    def _get(self, state: GameState, player: int, source: Cardboard):
        return self.thing_to_repeat * self.num.get(state, player, source)


class RepeatString(Repeat, GetString):
    def __init__(self, thing_to_repeat: str, num: GetInteger | int):
        super().__init__(thing_to_repeat, num)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class AllWhich:
    """return subsets of the given list, of all objects
     which match the specified pattern."""

    def __init__(self, pattern_for_valid: Match2.Pattern):
        self.pattern = pattern_for_valid

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
        a set of mutually valid options.
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
        super().__init__(Match2.Anything())

    def __str__(self):
        return "all of "


class Chooser(AllWhich):

    def __init__(self, pattern_for_valid: Match2.Pattern,
                 num_to_choose: GetInteger | int, can_be_fewer: bool):
        super().__init__(pattern_for_valid)
        if isinstance(num_to_choose, int):
            num_to_choose = ConstInteger(num_to_choose)
        self.num_to_choose: GetInteger = num_to_choose
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

    def __init__(self, pattern_for_valid: Match2.Pattern | None):
        if pattern_for_valid is None:
            pattern_for_valid = Match2.Anything()
        super().__init__(pattern_for_valid, 1, False)
