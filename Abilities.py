# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

import Verbs
import Costs
import ZONE
import MatchCardPatterns as Match

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard

# ---------------------------------------------------------------------------


class Trigger:

    def __init__(self, verb_type: type,
                 pattern_for_subject: Match.CardPattern):
        self.verb_type = verb_type
        self.pattern = pattern_for_subject

    def is_triggered(self, verb: Verbs.Verb, state: GameState,
                     source: Cardboard, trigger_card: Cardboard):
        """`source` is source of possible trigger. `trigger_card` is the
        thing which caused the trigger to be checked for viability."""
        return (isinstance(verb, self.verb_type)
                and self.pattern.match(trigger_card, state, source))

    def __str__(self):
        return "Trigger(%s,%s)" % (self.verb_type.__name__, str(self.pattern))

# ----------


class TriggerOnMove(Trigger):

    def __init__(self, pattern_for_subject: Match.CardPattern, origin,
                 destination):
        super().__init__(Verbs.MoveToZone, pattern_for_subject)
        self.origin = origin
        self.destination = destination

    def is_triggered(self, verb: Verbs.Verb, state: GameState,
                     source: Cardboard, trigger_card: Cardboard):
        return (super().is_triggered(verb, state, source, trigger_card)
                and isinstance(verb, Verbs.MoveToZone)
                and (self.origin == verb.origin or self.origin is None)
                and (self.destination == trigger_card.zone
                     or self.destination is None)
                )


class NullTrigger(Trigger):
    def __init__(self):
        super().__init__(Verbs.NullVerb, Match.Nothing())

    def __str__(self):
        return ""


class TriggerOnSelfEnter(TriggerOnMove):
    def __init__(self):
        super().__init__(Match.IsSelf(), None, ZONE.FIELD)

    def __str__(self):
        return "Self ETB"


# ----------

class AsEnterEffect(TriggerOnMove):
    """A specific subcategory of TriggerOnMove.  This is an
    enters-the-battlefield effect except more so: triggered abilities of this
    type bypass the stack and are handled IMMEDIATELY when the super_stack is
    cleared. This can be seen in `GameState.clear_super_stack`.
    """
    pass


# ----------

class ActivatedAbility:
    def __init__(self, name, cost: Costs.Cost, effect: Verbs.Verb):
        self.name: str = name
        self.cost: Costs.Cost = cost
        self.effect: Verbs.Verb = effect
        self.caster_verb: Verbs.PlayAbility = Verbs.PlayAbility(self)
        if effect.is_type(Verbs.AddMana):
            self.caster_verb = Verbs.PlayManaAbility(self)

    def get_activation_options(self, state: GameState, source: Cardboard
                               ) -> List[list]:
        return self.caster_verb.choose_choices(state, source, source)

    def can_be_activated(self, state: GameState, source: Cardboard,
                         choices: list):
        return self.caster_verb.can_be_done(state, source, choices)

    def activate(self, state: GameState, source: Cardboard, choices: list
                 ) -> List[GameState]:
        """Returns a list of GameStates where this spell has
        been cast (put onto the stack) and all costs paid.
        GUARANTEED NOT TO MUTATE THE ORIGINAL STATE"""
        # PlayAbility.do_it does not mutate
        return [g for g, _, _ in self.caster_verb.do_it(state, source,
                                                        choices)]

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.cost), str(self.effect))

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)


class TriggeredAbility:
    def __init__(self, name, trigger: Trigger, effect: Verbs.Verb):
        self.name: str = name
        self.trigger: Trigger = trigger
        self.effect: Verbs.Verb = effect
        add_triggered_ability = Verbs.AddTriggeredAbility(self)
        self.caster_verb: Verbs.AddTriggeredAbility = add_triggered_ability
        if isinstance(self.trigger, AsEnterEffect):
            self.caster_verb = Verbs.AddAsEntersAbility(self)

    def is_triggered(self, verb: Verbs.Verb, state: GameState,
                     source: Cardboard, trigger_card: Cardboard):
        """
        Returns boolean "the given Verb `verb` being performed on
        the card `trigger_card` meets self's trigger condition."
        `source` is assumed to be the source of this triggered
        ability.
        """
        return self.trigger.is_triggered(verb, state, source, trigger_card)

    def get_target_options(self, state: GameState, source: Cardboard,
                           cause: Cardboard) -> List[list]:
        return self.caster_verb.choose_choices(state, source, cause)

    def can_be_added(self, state: GameState, source: Cardboard, choices: list):
        """First element of `choices` must be the thing which
        caused this ability to trigger."""
        return self.caster_verb.can_be_done(state, source, choices)

    def add_to_stack(self, state: GameState, source: Cardboard, choices: list
                     ) -> List[GameState]:
        """Returns a list of GameStates where a StackObject
        for this ability has been added to the stack.
        First element of `choices` must be the thing which
        caused this ability to trigger.
        Returns a list of new GameStates, DOES NOT MUTATE."""
        return [g for g, _, _ in self.caster_verb.do_it(state, source,
                                                        choices)]

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.trigger), str(self.effect))

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)
