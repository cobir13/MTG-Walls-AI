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
        self.pattern = pattern_for_subject

    def is_triggered(self, verb: Verbs.Verb, state: GameState,
                     source: Cardboard, trigger_card: Cardboard):
        """`asking_card` is asking_card of possible trigger.
        `trigger_card` is the thing which caused the trigger
        to be checked for viability."""
        return (isinstance(verb, self.verb_type)
                and self.pattern.match(trigger_card, state,
                                       trigger_card.player_index, source))

    def __str__(self):
        return "Trigger(%s,%s)" % (self.verb_type.__name__, str(self.pattern))


# ----------

class TriggerOnMove(Trigger):

    def __init__(self, pattern_for_subject: Match.Pattern,
                 origin: Zone.Zone | None,
                 destination: Zone.Zone | None):
        super().__init__(Verbs.MoveToZone, pattern_for_subject)
        self.origin: Zone.Zone | None = origin
        self.destination: Zone.Zone | None = destination

    def is_triggered(self, verb: Verbs.Verb, state: GameState,
                     source: Cardboard, trigger_card: Cardboard):
        pl = source.player_index
        origins: List[Zone] = [self.origin]
        if self.origin is not None and not self.origin.is_fixed:
            origins = self.origin.get_absolute_zones(state, pl, source)
        dests: List[Zone] = [self.destination]
        if self.destination is not None and not self.destination.is_fixed:
            dests = self.destination.get_absolute_zones(state, pl, source)
        return (super().is_triggered(verb, state, source, trigger_card)
                and isinstance(verb, Verbs.MoveToZone)
                and (self.origin is None
                     or any([verb.origin.is_contained_in(z) for z in origins]))
                and (self.destination is None
                     or any([verb.destination.is_contained_in(z)
                             for z in dests]))
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

    def is_triggered(self, verb: Verbs.Verb, state: GameState,
                     source: Cardboard, trigger_card: Cardboard):
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
        options and target options and makes usable
        StackObjects accordingly. If the ability cannot
        be activated, the empty list is returned."""
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payments = self.cost.get_options(state, player, source, None)
        # keep only the valid ones
        payments = [ch for ch in payments
                    if self.cost.can_afford(state, player, source, ch)]
        # 601.2c: choose targets and modes
        targets = self.effect.get_input_options(state, player, source, None)
        targets = [ch for ch in targets if
                   self.effect.can_be_done(state, player, source, ch)]
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

    def add_any_to_super(self, verb: Verbs.Verb, state: GameState,
                         player: int, source: Cardboard,
                         trigger_card: Cardboard | None):
        """
        MUTATES.
        Checks if the given Verb `verb` being performed on the
        card `trigger_card` meets this ability's trigger
        condition. `asking_card` is assumed to be the source of this
        triggered ability. If the ability IS triggered, MUTATES
        the GameState `state` to add a StackTrigger object to
        the super_stack.  Control of the ability is `player`.
        """
        if self.trigger.is_triggered(verb, state, source, trigger_card):
            caster = Verbs.AddTriggeredAbility()
            if isinstance(self.trigger, AsEnterEffect):
                caster = Verbs.AddAsEntersAbility()
            stack_obj = Stack.StackTrigger(player, source, self, trigger_card,
                                           [], caster)
            state.super_stack.append(stack_obj)

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.trigger), str(self.effect))

    def get_id(self):
        return str(self)

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)

    def copy(self):
        return self
