# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, Type, TYPE_CHECKING

import Verbs
import Costs
import Zone
import Match
import Getters as Get
import Stack

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard

# ---------------------------------------------------------------------------


class Trigger:

    def __init__(self, verb_type: Type[Verbs.Verb],
                 pattern_for_subject: Match.Pattern):
        self.verb_type = verb_type
        self.pattern_for_subject = pattern_for_subject

    def is_triggered(self,
                     state: GameState,
                     source_of_ability: Cardboard,
                     verb: Verbs.Verb):
        ability_owner = source_of_ability.player_index
        return (isinstance(verb, self.verb_type)
                and self.pattern_for_subject.match(verb.subject, state,
                                                   ability_owner,
                                                   source_of_ability))

    def __str__(self):
        return "Trigger(%s,%s)" % (self.verb_type.__name__,
                                   str(self.pattern_for_subject))


# ----------

class TriggerOnMove(Trigger):

    def __init__(self, pattern_for_subject: Match.Pattern,
                 origin: Zone.Zone | None,
                 destination: Zone.Zone | None):
        super().__init__(Verbs.MoveToZone, pattern_for_subject)
        self.origin: Zone.Zone | None = origin
        self.destination: Zone.Zone | None = destination

    def is_triggered(self,
                     state: GameState,
                     source_of_ability: Cardboard,
                     verb: Verbs.Verb):
        pl = source_of_ability.player_index
        origins: List[Zone] = [self.origin]
        if self.origin is not None and not self.origin.is_fixed:
            origins = self.origin.get_absolute_zones(state, pl,
                                                     source_of_ability)
        dests: List[Zone] = [self.destination]
        if self.destination is not None and not self.destination.is_fixed:
            dests = self.destination.get_absolute_zones(state, pl,
                                                        source_of_ability)
        return (super().is_triggered(state, source_of_ability, verb)
                and isinstance(verb, Verbs.MoveToZone)
                and (self.origin is None
                     or any([verb.origin.is_contained_in(z) for z in origins]))
                and (self.destination is None
                     or any([verb.dest.is_contained_in(z) for z in dests]))
                )


class NeverTrigger(Trigger):
    def __init__(self):
        super().__init__(Verbs.NullVerb, Match.Nothing())

    def __str__(self):
        return ""


class AlwaysTrigger(Trigger):
    def __init__(self):
        super().__init__(Verbs.NullVerb, Match.Nothing())

    def __str__(self):
        return ""

    def is_triggered(self, *args, **kwargs):
        return True


class TriggerOnSelfEnter(TriggerOnMove):
    def __init__(self):
        super().__init__(Match.IsSelf(), None, Zone.Field(Get.Controllers()))

    def __str__(self):
        return "Self ETB"


# ----------

class AsEnterEffect(TriggerOnMove):
    """A specific subcategory of TriggerOnMove.  This is an
    enters-the-battlefield effect except more so: triggered abilities of this
    type bypass the stack and are handled IMMEDIATELY when the super_stack is
    cleared. This can be seen in `GameState.clear_super_stack`.
    """
    def __init__(self):
        super().__init__(Match.IsSelf(), None, Zone.Field(Get.Controllers()))


# ----------

class ActivatedAbility:
    def __init__(self, name, cost: Costs.Cost, effect: Verbs.Verb):
        self.name: str = name
        self.cost: Costs.Cost = cost
        self.effect: Verbs.Verb = effect

    def valid_stack_objects(self, state: GameState, player: int,
                            source: Cardboard) -> List[Stack.StackAbility]:
        """Create as many valid StackAbilities as possible,
        one for each valid way to activate this ability.
        This function doesn't ACTUALLY add them to stack
        or pay their costs, it just works out the payment
        _options and target _options and makes usable
        StackObjects accordingly. If the ability cannot
        be activated, the empty list is returned."""
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payments = self.cost.get_options(state, player, source, None)
        # keep only the valid ones
        payments = [ch for ch in payments
                    if self.cost.can_afford(state, player, source, ch)]
        # 601.2c: choose targets and modes
        targets = self.effect.populate_options(state, player, source, None)
        targets = [ch for ch in targets if
                   self.effect.can_be_done(state)]
        # combine all combinations of these
        obj_list = []
        for sub_pay in payments:
            for sub_target in targets:
                # concatenate sub-lists
                inputs = sub_pay + sub_target
                # figure out which verb can be used to cast this object
                caster: Verbs.UniversalCaster = Verbs.PlayAbility()
                if self.effect.is_type(Verbs.AddMana):
                    caster = Verbs.PlayManaAbility()
                obj = Stack.StackAbility(player, source, self, inputs, caster)
                obj_list.append(obj)
        return obj_list

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.cost), str(self.effect))

    def get_id(self):
        return str(self)

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)

    def copy(self):
        return self


class TriggeredAbility:
    def __init__(self, name, trigger: Trigger, effect: Verbs.Verb):
        self.name: str = name
        self.trigger: Trigger = trigger
        self.effect: Verbs.Verb = effect
        self.num_inputs = effect.num_inputs

    def add_any_to_super(self, state: GameState,
                         source_of_ability: Cardboard,
                         verb: Verbs.Verb):
        """
        MUTATES.
        Checks if the given Verb meets this ability's trigger
        condition. If the ability IS triggered, MUTATES
        the GameState `state` to add a StackTrigger object to
        the super_stack.
        """
        if self.trigger.is_triggered(state, source_of_ability, verb):
            caster = Verbs.AddTriggeredAbility()
            if isinstance(self.trigger, AsEnterEffect):
                caster = Verbs.AddAsEntersAbility()
            stack_obj = Stack.StackTrigger(source_of_ability.player_index,
                                           source_of_ability, self,
                                           source_of_verb, [], caster)
            state.super_stack.append(stack_obj)

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.trigger), str(self.effect))

    def get_id(self):
        return str(self)

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)

    def copy(self):
        return self


class TimedAbility:
    def __init__(self, name, if_condition: Get.Bool, effect: Verbs.Verb):
        self.name: str = name
        self.condition: Get.Bool = if_condition
        self.effect: Verbs.Verb = effect
        self.num_inputs = effect.num_inputs

    def add_any_to_super(self, state: GameState,
                         source_of_ability: Cardboard):
        """
        MUTATES.
        Checks if the given gamestate meets the condition to
        trigger. If the ability IS triggered, MUTATES
        the GameState `state` to add a StackTrigger object to
        the super_stack. The controller of the card controls
        the ability.
        """
        player = source_of_ability.player_index
        # if meets condition:
        if self.condition.get(state, player, source_of_ability):
            caster = Verbs.AddTriggeredAbility()
            stack_obj = Stack.StackTrigger(player, source_of_ability, self,
                                           None, [], caster)
            state.super_stack.append(stack_obj)

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.condition), str(self.effect))
