# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from VerbParents import Verb
    from GameState import GameState
    from Cardboard import Cardboard
    import MatchCardPatterns as Match
from Verbs import MoveToZone
from VerbParents import ManyVerbs


class Trigger:

    def __init__(self, verb_type: type,
                 patterns_for_subject: List[Match.CardPattern]):
        self.verb_type = verb_type
        self.patterns = patterns_for_subject

    def is_triggered(self, verb: Verb, state: GameState, source: Cardboard,
                     trigger_card: Cardboard):
        """`source` is source of possible trigger. `trigger_card` is the
        thing which caused the trigger to be checked for viability."""
        return (isinstance(verb, self.verb_type)
                and all([p.match(trigger_card, state, source) for p in
                         self.patterns]))


# ----------

class TriggerOnMove(Trigger):

    def __init__(self, patterns_for_subject: List[Match.CardPattern], origin,
                 destination):
        super().__init__(MoveToZone, patterns_for_subject)
        self.origin = origin
        self.destination = destination

    def is_triggered(self, verb: Verb, state: GameState, source: Cardboard,
                     trigger_card: Cardboard):
        return (super().is_triggered(verb, state, source, trigger_card)
                and isinstance(verb, MoveToZone)
                and (self.origin == verb.origin or self.origin is None)
                and (self.destination == trigger_card.zone
                     or self.destination is None)
                )


# ----------

class GenericAbility:
    def __init__(self, name, effect: Verb):
        self.name: str = name
        self.cost: Verb | None = None
        self.trigger: Trigger | None = None
        self.effect: Verb = effect

    def can_afford(self, state: GameState, source: Cardboard, choices: list):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        if self.cost is None:
            return False
        else:
            return self.cost.can_be_done(state, source, choices)

    def pay(self, state: GameState, source: Cardboard, choices):
        """
        Returns a list of (GameState,Cardboard) pairs in which the
        cost has been paid. The list is length 1 if there is exactly
        one way to pay the cost, and the list is length 0 if the cost
        cannot be paid.
        The original GameState and Source are NOT mutated.
        """
        if not self.can_afford(state, source, choices):
            return []
        else:
            return self.cost.do_it(state, source, choices)

    def is_triggered(self, verb: Verb, state: GameState, source: Cardboard,
                     trigger_card: Cardboard):
        """
        Returns boolean "the given Verb `verb` being performed on
        the card `trigger_card` meets self's trigger condition."
        `source` is assumed to be the source of this triggered
        ability.
        """
        if self.trigger is None:
            return False
        else:
            return self.trigger.is_triggered(verb, state, source, trigger_card)

    def __str__(self):
        return self.name

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)

    def get_choice_options(self, state: GameState, source: Cardboard):
        if self.cost is not None:
            overall_verb = ManyVerbs([self.cost, self.effect])
            return overall_verb.choose_choices(state, source)
        else:
            return self.effect.choose_choices(state, source)


class ActivatedAbility(GenericAbility):
    def __init__(self, name, cost: Verb, effect: Verb):
        super().__init__(name, effect)
        self.cost: Verb | None = cost


class TriggeredAbility(GenericAbility):
    def __init__(self, name, trigger: Trigger, effect: Verb):
        super().__init__(name, effect)
        self.trigger: Trigger | None = trigger


class TimedAbility(GenericAbility):
    pass
