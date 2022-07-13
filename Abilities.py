# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

import Verbs

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard
    import MatchCardPatterns as Match


class Trigger:

    def __init__(self, verb_type: type,
                 patterns_for_subject: List[Match.CardPattern]):
        self.verb_type = verb_type
        self.patterns = patterns_for_subject

    def is_triggered(self, verb: Verbs.Verb, state: GameState,
                     source: Cardboard, trigger_card: Cardboard):
        """`source` is source of possible trigger. `trigger_card` is the
        thing which caused the trigger to be checked for viability."""
        return (isinstance(verb, self.verb_type)
                and all([p.match(trigger_card, state, source) for p in
                         self.patterns]))

    def __str__(self):
        return "Trigger(%s,%s)" % (self.verb_type.__name__,
                                   str(self.patterns))

# ----------


class TriggerOnMove(Trigger):

    def __init__(self, patterns_for_subject: List[Match.CardPattern], origin,
                 destination):
        super().__init__(Verbs.MoveToZone, patterns_for_subject)
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
        super().__init__(Verbs.NullVerb, [])

    def is_triggered(self, verb: Verbs.Verb, state: GameState,
                     source: Cardboard, trigger_card: Cardboard):
        return False

    def __str__(self):
        return ""


# ----------
class AsEnterEffect(TriggerOnMove):
    """A specific subcategory of TriggerOnMove.  This is an
    enters-the-battlefield effect except more so: triggered abilities of this
    type bypass the stack and are handled IMMEDIATELY when the super_stack is
    cleared. This can be seen in `GameState.clear_super_stack`.
    """
    pass


# ----------

class GenericAbility:

    def __init__(self, name, effect: Verbs.Verb):
        self.name: str = name
        self.cost: Verbs.Verb = Verbs.NullVerb()
        self.trigger: Trigger = NullTrigger()
        self.effect: Verbs.Verb = effect
        if effect.is_type(Verbs.AddMana):
            self.caster_verb: Verbs.PlayVerb = Verbs.PlayManaAbility(self)
        else:
            self.caster_verb: Verbs.PlayVerb = Verbs.PlayAbility(self)

    def get_cast_options(self, state: GameState, source: Cardboard):
        return self.caster_verb.choose_choices(state, source)

    def can_be_cast(self, state: GameState, source: Cardboard, choices: list):
        return self.caster_verb.can_be_done(state, source, choices)

    def activate(self, state: GameState, source: Cardboard, choices: list
                 ) -> List[GameState]:
        """Returns a list of GameStates where this spell has
        been cast (put onto the stack) and all costs paid."""
        return [g for g, _, _ in self.caster_verb.do_it(state, source,
                                                        choices)]

    def is_triggered(self, verb: Verbs.Verb, state: GameState,
                     source: Cardboard, trigger_card: Cardboard):
        """
        Returns boolean "the given Verb `verb` being performed on
        the card `trigger_card` meets self's trigger condition."
        `source` is assumed to be the source of this triggered
        ability.
        """
        return self.trigger.is_triggered(verb, state, source, trigger_card)

    def __str__(self):
        txt_cost = str(self.cost)
        txt_trig = str(self.trigger)
        txt_efct = str(self.effect)
        return "Ability(%s,%s -> %s)" % (txt_cost, txt_trig, txt_efct)

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)

    def get_choice_options(self, state: GameState, source: Cardboard):
        if self.cost is not Verbs.NullVerb:
            overall_verb = Verbs.ManyVerbs([self.cost, self.effect])
            return overall_verb.choose_choices(state, source)
        else:
            return self.effect.choose_choices(state, source)


class ActivatedAbility(GenericAbility):
    def __init__(self, name, cost: Verbs.Verb, effect: Verbs.Verb):
        super().__init__(name, effect)
        self.cost: Verbs.Verb = cost


class TriggeredAbility(GenericAbility):
    def __init__(self, name, trigger: Trigger, effect: Verbs.Verb):
        super().__init__(name, effect)
        self.trigger: Trigger = trigger


class TimedAbility(GenericAbility):
    pass
