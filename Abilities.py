# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from Verbs import Verb
    from GameState import GameState
    from Cardboard import Cardboard
    import MatchCardPatterns as Match
from Verbs import MoveToZone



class Trigger:
    
    def __init__(self, verb_type:type, patterns_for_subject:List[Match.CardPattern]):
        self.verb_type = verb_type
        self.patterns = patterns_for_subject

    def is_triggered(self, verb:Verb, state:GameState, source:Cardboard, triggerer:Cardboard):
        """`source` is source of possible trigger. `triggerer` is the
        thing which caused the trigger to be checked for viability."""
        return (isinstance(verb,self.verb_type)
                and all([p.match(triggerer,state,source) for p in self.patterns]) )

# ----------

class TriggerOnMove(Trigger):
    
    def __init__(self, patterns_for_subject:List[Match.CardPattern],origin,destination):
        self.ver_type = MoveToZone
        self.patterns = patterns_for_subject
        self.origin = origin
        self.destination = destination
    
    def is_triggered(self, verb:Verb, state:GameState, source:Cardboard, triggerer:Cardboard):
        return (super().is_triggered(verb,state,source,triggerer)
                and (self.origin == verb.origin or self.origin is None)  #MoveSelfToZone has origin
                and (self.destination == triggerer.zone or self.destination is None)
                )
            
# ----------

class GenericAbility:
    def __init__(self, name, cost:Verb, trigger:Trigger, effect:Verb):
        self.name = name
        self.cost = cost
        self.trigger = trigger
        self.effect = effect

    def can_afford(self, gamestate: GameState, source: Cardboard):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        if self.cost is None:
            return False
        else:
            return self.cost.can_be_done(gamestate, source)

    def pay(self, gamestate: GameState, source: Cardboard, choices):
        """
        Returns a list of (GameState,Cardboard) pairs in which the
        cost has been paid. The list is length 1 if there is exactly
        one way to pay the cost, and the list is length 0 if the cost
        cannot be paid.
        The original GameState and Source are NOT mutated.
        """
        if not self.CanAfford(gamestate, source):
            return []
        else:
            return self.cost.pay(gamestate, source)

    def is_triggered(self, verb: Verb, state: GameState, source: Cardboard,
                     triggerer: Cardboard):
        """
        Returns boolean "the given Verb meets the trigger condition"
        """
        if self.trigger is None:
            return False
        else:
            return self.trigger.is_triggered(verb, state, source, triggerer)

    def apply_effect(self, gamestate: GameState, source: Cardboard, choices):
        """
        Returns a list of GameStates where the effect has been performed:
            - length 1 if there is exactly one way to do this
            - length 0 if this cannot be done (costs, lack of targets, etc)
            - length >1 if there are options that can be decided differently.
        The original GameState and source Cardboard are NOT mutated.
        """
        new_state, copied_things = gamestate.copy_and_track([source] + choices)
        new_source = copied_things[0]
        new_choices = copied_things[1:]
        return self.effect.do_it(new_state, new_source, new_choices)

    def __str__(self):
        return self.name

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)


class ActivatedAbility(GenericAbility):
    def __init__(self, name, cost:Verb, effect:Verb):
        super().__init__(name, cost, None, effect)

class TriggeredAbility(GenericAbility):
    def __init__(self, name, trigger:Trigger, effect:Verb):
        super().__init__(name, None, trigger, effect)

