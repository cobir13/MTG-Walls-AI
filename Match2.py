# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, Type

import Getters as Get
import Verbs
from Cardboard import Cardboard
from GameState import GameState, Player
from RulesText import RulesText
import Zone


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------

class Pattern:
    """
    A Pattern stores characteristics that game objects can have.
    The main function is `match`, which allows the user to pass
    in any game object and ask whether that object matches the
    description stored in the Pattern. 
    """

    def match(self, subject, state: GameState, asking_player: int,
              asking_card: Cardboard) -> bool:
        """
        Does the subject match this pattern, as measured in the
        given GameState? The given Player (player index, really)
        and the given Cardboard are the ones asking the question. 
        For example, the pattern "is the subject controlled by
        me" will check if the asking_player controls the subject,
        and the pattern "is the subject a creature with higher
        power than me" will check if the subject is a creature,
        the asking_card is also a creature, and the subject has
        a higher power than the asking_card.
        """
        return self._match(subject, state, asking_player, asking_card)

    def _match(self, subject, state: GameState, asking_player: int,
               asking_card: Cardboard) -> bool:
        """
        This is the private version of the public `match`, where
        the real work gets done. Subclasses should overwrite it
        with their own implementation details.
        Does the subject match this pattern, as measured in the
        given GameState? The given Player (player index, really)
        and the given Cardboard are the ones asking the question.
        For example, the pattern "is the subject controlled by
        me" will check if the asking_player controls the subject,
        and the pattern "is the subject a creature with higher
        power than me" will check if the subject is a creature,
        the asking_card is also a creature, and the subject has
        a higher power than the asking_card.
        """
        raise NotImplementedError

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

    def _match(self, subject, state, asking_player, asking_card) -> bool:
        return any([p.match(subject, state, asking_player, asking_card)
                    for p in self.patterns])

    def __str__(self):
        return " or ".join([str(p) for p in self.patterns])


class _AllOf(Pattern):
    """A pattern which returns true if the card matches ALL
        the given pattern."""

    def __init__(self, patterns: List[Pattern]):
        self.patterns = patterns

    def _match(self, subject, state, asking_player, asking_card) -> bool:
        return all([p.match(subject, state, asking_player, asking_card)
                    for p in self.patterns])

    def __str__(self):
        return " and ".join([str(p) for p in self.patterns])


class _Negated(Pattern):
    def __init__(self, pattern: Pattern):
        self.pattern = pattern

    def _match(self, subject, state, asking_player, asking_card) -> bool:
        return not self.pattern.match(subject, state, asking_player,
                                      asking_card)

    def __str__(self):
        return "not " + str(self.pattern)


class Anything(Pattern):
    def _match(self, subject, state, asking_player, asking_card) -> bool:
        return True

    def __str__(self):
        return ""


class Nothing(Pattern):
    def _match(self, subject, state, asking_player, asking_card) -> bool:
        return False

    def __str__(self):
        return ""


# ----------

class CardPattern(Pattern):
    """Only matches to Cardboard subjects. Subjects of any other
    type do not match this Pattern."""

    def match(self, subject, state: GameState, asking_player: int,
              asking_card: Cardboard) -> bool:
        if isinstance(subject, Cardboard):
            return self._match(subject, state, asking_player, asking_card)
        else:
            return False

    def _match(self, subject: Cardboard, state: GameState, asking_player: int,
               asking_card: Cardboard) -> bool:
        raise NotImplementedError


class PlayerPattern(Pattern):
    """Only matches to Player subjects. Subjects of any other
    type do not match this Pattern."""

    def match(self, subject, state: GameState, asking_player: int,
              asking_card: Cardboard) -> bool:
        if isinstance(subject, Player):
            return self._match(subject, state, asking_player, asking_card)
        else:
            return False

    def _match(self, subject: Player, state: GameState, asking_player: int,
               asking_card: Cardboard) -> bool:
        raise NotImplementedError


# class VerbPattern(Pattern):
#     """Only matches to Verb subjects. Subjects of any other
#     type do not match this Pattern."""
#
#     def match(self, subject, state: GameState, asking_player: int,
#               asking_card: Cardboard) -> bool:
#         if isinstance(subject, Verbs.Verb):
#             return self._match(subject, state, asking_player, asking_card)
#         else:
#             return False
#
#     def _match(self, subject: Verbs.Verb, state: GameState,
#                asking_player: int, asking_card: Cardboard) -> bool:
#         raise NotImplementedError


# # ---------- CARD PATTERNS ----------------------------------------------

class CardType(CardPattern):
    def __init__(self, card_type: str):
        self.type_to_match: str = card_type.lower()

    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        its_types = Get.CardTypes().get(state, asking_player, subject)
        return self.type_to_match in its_types

    def __str__(self):
        return "is-" + self.type_to_match


class Keyword(CardPattern):
    def __init__(self, keyword: str):
        self.keyword_to_match = keyword

    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        its_keywords = Get.Keywords().get(state, asking_player, subject)
        return self.keyword_to_match in its_keywords

    def __str__(self):
        return "has-" + self.keyword_to_match


class Name(CardPattern):
    def __init__(self, name: str):
        self.name_to_match = name

    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        its_name = Get.CardName().get(state, asking_player, subject)
        return self.name_to_match == its_name

    def __str__(self):
        return "named-" + self.name_to_match


class Counter(CardPattern):
    def __init__(self, counter_to_match: str):
        self.counter_to_match = counter_to_match

    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        return self.counter_to_match in subject.counters

    def __str__(self):
        return super().__str__() + "(" + self.counter_to_match + ")"


class Tapped(CardPattern):
    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        return Get.IsTapped().get(state, asking_player, asking_card)


class Untapped(CardPattern):
    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        return not Get.IsTapped().get(state, asking_player, asking_card)


class IsInZone(CardPattern):
    def __init__(self, zone: Type[Zone.Zone]):
        self.zone: Type[Zone.Zone] = zone

    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        return subject.is_in(self.zone)

    def __str__(self):
        return self.zone.__name__


class IsSelf(CardPattern):
    """The subject Cardboard is the asking_card"""
    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        return subject is asking_card


class Another(CardPattern):
    """The subject Cardboard is not the asking_card"""
    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        return subject is not asking_card


class YouControl(CardPattern):
    """The asking asking_player controls the given Cardboard"""
    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        return subject.player_index == asking_player


class OppControls(CardPattern):
    """The asking_player does not control the subject Cardboard"""
    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        return subject.player_index != asking_player


class ControllerControls(CardPattern):
    """The controller of the asking_card also controls the subject Cardboard"""
    def _match(self, subject: Cardboard, state, asking_player, asking_card):
        return subject.player_index == asking_card.player_index


# ----------

class NumericPattern(CardPattern):
    """
    This Pattern holds an inequality description of a Cardboard.
    Instead of asking whether the Cardboard has exact traits, it
    permits descriptions involving inequalities (e.g. "Cards with
    power greater than 3"). When the pattern is created, it is
    passed a Getter to find the value of the subject Cardboard's
    trait, as well as an inequality to compare that value to.
    """

    def __init__(self, comparator: str, value: int, getter: Get.GetInteger):
        """
        The comparator is a string from the following list:
            [">", "<", "=", "==", "<=", ">=", "!="]
        It is interpreted as the mathematical expression:
            card_value comparator reference_value
        For example: a comparator of "<", a reference value of 3,
        and a Getter that retrieves the power of a creature would
        match with creatures of power 0, 1, or 2, but fail to match
        creatures with power 3 or greater.
        If the subject Cardboard does not have the relevant trait
        to be gotten by the Getter, the match automatically fails.
        """
        assert (comparator in [">", "<", "=", "==", "<=", ">=", "!=", ])
        self.comparator = comparator
        self.value = value
        self.getter = getter

    def _match(self, subject: Cardboard, state: GameState, asking_player: int,
               asking_card: Cardboard) -> bool:
        try:
            card_value = self.getter.get(state, asking_player, subject)
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


# # ---------- PLAYER PATTERNS --------------------------------------------

class You(PlayerPattern):
    """The subject Player is the asking_player."""

    def _match(self, subject: Player, state, asking_player, asking_card):
        return subject.player_index == asking_player


class Opponent(PlayerPattern):
    """The subject Player is not the asking_player."""

    def _match(self, subject: Player, state, asking_player, asking_card):
        return subject.player_index != asking_player


class Owner(PlayerPattern):
    """The subject Player owns the asking Cardboard."""

    def _match(self, subject: Player, state, asking_player, asking_card):
        return subject.player_index == asking_card.owner_index


class Controller(PlayerPattern):
    """The subject Player controls the asking Cardboard."""

    def _match(self, subject: Player, state, asking_player, asking_card):
        return subject.player_index == asking_card.player_index


# # ---------- VERB PATTERNS ----------------------------------------------

class VerbPattern(Pattern):
    """Only matches to Verb subjects. Subjects of any other
    type do not match this Pattern."""

    def __init__(self,
                 verb_type: Type[Verbs.Verb],
                 pattern_for_subject: Pattern | None = None,
                 pattern_for_source: CardPattern | None = None,
                 pattern_for_player: PlayerPattern | None = None):
        """
        Matches to Verbs of the given type, whose subject and
        source and player all match the respective Patterns.
        If those Patterns are None, then this VerbPattern
        will accept any value for the Verb's corresponding
        trait.
        """
        self.verb_type: Type[Verbs.Verb] = verb_type
        self.pattern_for_subject: Pattern | None = pattern_for_subject
        self.pattern_for_source: CardPattern | None = pattern_for_source
        self.pattern_for_player: PlayerPattern | None = pattern_for_player


    def match(self, subject, state: GameState, asking_player: int,
              asking_card: Cardboard) -> bool:
        """
        Note: a common usage is for a card with a triggered
        ability to be trying to check if a Verb has triggered
        that ability or not. In such a case, the asking_card
        is the Cardboard containing the triggered ability and
        the asking_player is that card's controller. The Verb's
        subject, source, and player are likely different."""
        if isinstance(subject, Verbs.Verb):
            # isinstance can't see sub-verbs, so use Verb.is_type instead
            good_type = subject.is_type(self.verb_type)
            if isinstance(self.pattern_for_subject, Pattern):
                good_subj = self.pattern_for_subject.match(
                    subject.subject, state, asking_player, asking_card)
            else:
                good_subj = True
            if isinstance(self.pattern_for_source, CardPattern):
                good_srce = self.pattern_for_subject.match(
                    subject.source, state, asking_player, asking_card)
            else:
                good_srce = True
            if isinstance(self.pattern_for_player, PlayerPattern):
                player_obj = state.player_list[subject.player]  # int->Player
                good_plyr = self.pattern_for_player.match(
                    player_obj, state, asking_player, asking_card)
            else:
                good_plyr = True
            return (good_type and good_subj and good_srce and good_plyr and
                    self._match(subject, state, asking_player, asking_card))
        else:
            return False

    def _match(self, subject: Verbs.Verb, state: GameState,
               asking_player: int, asking_card: Cardboard) -> bool:
        return True  # in basic VerbPattern, no additional work to do here

    def __str__(self):
        if self.pattern_for_subject is not None:
            subj = str(self.pattern_for_subject)
        else:
            subj = "any"
        return "(if subject %s becomes %s)" % (subj, self.verb_type.__name__)


class MoveType(VerbPattern):
    """Is the subject a MoveToZone Verb moving a card to or from
    the specified zones?"""
    def __init__(self, pattern_for_subject: CardPattern,
                 origin: Zone.Zone | None, destination: Zone.Zone | None):
        super().__init__(Verbs.MoveToZone, pattern_for_subject,
                         pattern_for_source=None, pattern_for_player=None)
        self.origin: Zone.Zone | None = origin
        self.destination: Zone.Zone | None = destination

    def _match(self, subject: Verbs.Verb, state: GameState,
               asking_player: int, asking_card: Cardboard) -> bool:
        # make sure that self's origin, destination are absolute not relative
        origins: List[Zone] = [self.origin]
        if self.origin is not None and not self.origin.is_fixed:
            origins = self.origin.get_absolute_zones(state, asking_player,
                                                     asking_card)
        dests: List[Zone] = [self.destination]
        if self.destination is not None and not self.destination.is_fixed:
            dests = self.destination.get_absolute_zones(state, asking_player,
                                                        asking_card)
        # check if this verb is going to / coming from the right places
        return (isinstance(subject, Verbs.MoveToZone)
                and (self.origin is None
                     or any([subject.origin.is_contained_in(z)
                             for z in origins]))
                and (self.destination is None
                     or any([subject.destination.is_contained_in(z)
                             for z in dests]))
                )

    def __str__(self):
        if self.pattern_for_subject is not None:
            subj = str(self.pattern_for_subject)
        else:
            subj = "any"
        if self.origin is None:
            orig = ""
        else:
            orig = " from " + str(self.origin)
        if self.destination is None:
            dest = ""
        else:
            dest = " to " + str(self.destination)
        return "(if subject %s moves%s%s)" % (subj, orig, dest)


class SelfEnter(MoveType):
    """A common subcategory of MoveType, that describes a card
    entering the battlefield."""
    def __init__(self):
        super().__init__(IsSelf(), None, Zone.Field(Get.Controllers()))

    def __str__(self):
        return "Self ETB"


class SelfAsEnter(MoveType):
    """A specific subcategory of MoveType, that describes a card
    entering the battlefield. Even more specifically, though, it
    is used to signify an "as-enters" effect. This is like a usual
    enters-the-battlefield effect except more so: triggered
    abilities of this type bypass the stack and are handled
    IMMEDIATELY when the super_stack is cleared. This can be seen
    in `GameState.clear_super_stack`.
    """
    def __init__(self):
        super().__init__(IsSelf(), None, Zone.Field(Get.Controllers()))

    def __str__(self):
        return "Self as-enters"
