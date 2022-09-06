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


class TriggerWhenVerb:

    # pattern_for_verb, pattern_for_subject_, pattern_for_subject, etc...

    def __init__(self,
                 verb_type: Type[Verbs.Verb],
                 pattern_for_subject: Match.Pattern
                 ):
        self.verb_type = verb_type
        self.pattern_for_subject = pattern_for_subject

    def is_triggered(self,
                     state: GameState,
                     source_of_ability: Cardboard,
                     verb: Verbs.Verb):
        ability_owner = source_of_ability.player_index
        return (verb.is_type(self.verb_type)  # isinstance can't see sub-verbs
                and self.pattern_for_subject.match(verb.subject, state,
                                                   ability_owner,
                                                   source_of_ability))

    def __str__(self):
        return "Trigger(%s,%s)" % (self.verb_type.__name__,
                                   str(self.pattern_for_subject))


# ----------

class TriggerWhenMove(TriggerWhenVerb):

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
                     or any([verb.destination.is_contained_in(z)
                             for z in dests]))
                )


class NeverTrigger(TriggerWhenVerb):
    def __init__(self):
        super().__init__(Verbs.NullVerb, Match.Nothing())

    def __str__(self):
        return ""


class AlwaysTrigger(TriggerWhenVerb):
    def __init__(self):
        super().__init__(Verbs.NullVerb, Match.Nothing())

    def __str__(self):
        return ""

    def is_triggered(self, *args, **kwargs):
        return True


class TriggerOnSelfEnter(TriggerWhenMove):
    def __init__(self):
        super().__init__(Match.IsSelf(), None, Zone.Field(Get.Controllers()))

    def __str__(self):
        return "Self ETB"


# ----------

class AsEnterEffect(TriggerWhenMove):
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

    def valid_casters(self, state: GameState, player: int,
                      source: Cardboard) -> List[Verbs.PlayAbility]:
        """Create as many valid PlayAbility Verbs as possible,
        one for each valid way to activate this ability. This
        function doesn't ACTUALLY run those verbs to activate
        the ability and add a StackAbility to the stack and
        pay its posts, but it fully populates the PlayAbility
        verbs and the pay_cost and do_effect verbs of the
        ability so that they will do those things when they
        are run.
        If the ability cannot be activated, the empty list is
        returned."""
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        # Note: if cost is free, payments is [None]. If cost cannot be paid,
        # payments is [] so loops won't loop and no caster is returned.
        payments = self.cost.get_payment_plans(state, player, source, None)
        # 601.2c: choose targets and modes. Note: if there are no effects,
        # then loops won't loop and no caster is returned.
        effects = self.effect.populate_options(state, player, source, None)
        effects = [eff for eff in effects if eff.can_be_done(state)]
        # build casters and stack objects for all combinations of these
        caster_list = []
        for pay_verb in payments:  # pay_verb already populated
            for effect_verb in effects:
                stack_obj = Stack.StackAbility(controller=player,
                                               obj=self,
                                               pay_cost=pay_verb,
                                               do_effect=effect_verb)
                # figure out which verb can be used to cast this object
                caster: Verbs.PlayAbility = Verbs.PlayAbility()
                if self.effect.is_type(Verbs.AddMana):
                    caster = Verbs.PlayManaAbility()
                [caster] = caster.populate_options(state=state,
                                                   player=player,
                                                   source=source,
                                                   cause=None,
                                                   stack_object=stack_obj)
                if caster.can_be_done(state):
                    caster_list.append(caster)
        return caster_list

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.cost), str(self.effect))

    def get_id(self):
        return str(self)

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)

    def copy(self, new_state: GameState | None = None):
        abil = ActivatedAbility(self.name, self.cost,
                                self.effect.copy(new_state))
        abil.__class__ = self.__class__
        return abil


class TriggeredAbility:
    def __init__(self, name, trigger: TriggerWhenVerb, effect: Verbs.Verb):
        self.name: str = name
        self.trigger: TriggerWhenVerb = trigger
        self.effect: Verbs.Verb = effect
        self.num_inputs = effect.num_inputs

    def add_any_to_super(self, state: GameState,
                         source_of_ability: Cardboard,
                         verb: Verbs.Verb):
        """
        MUTATES.
        Checks if the given Verb meets this ability's trigger
        condition. If the ability IS triggered, MUTATES
        the GameState `state` to add a populated
        AddTriggeredAbility Verb to the super_stack.
        """
        if self.trigger.is_triggered(state, source_of_ability, verb):
            player = source_of_ability.player_index
            stack_obj = Stack.StackTrigger(player, obj=self,
                                           pay_cost=None, do_effect=None)
            # Note: pay, effect verbs not yet populated. AddTriggeredAbility
            # does that later.
            caster = Verbs.AddTriggeredAbility()
            if isinstance(self.trigger, AsEnterEffect):
                caster = Verbs.AddAsEntersAbility()
            [caster] = caster.populate_options(state, player,
                                               source=source_of_ability,
                                               cause=verb.subject,
                                               stack_object=stack_obj)
            if caster.can_be_done(state):
                state.super_stack.append(caster)

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.trigger), str(self.effect))

    def get_id(self):
        return str(self)

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)

    def copy(self, new_state: GameState | None = None):
        abil = TriggeredAbility(self.name, self.trigger,
                                self.effect.copy(new_state))
        abil.__class__ = self.__class__
        return abil


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
        the GameState `state` to add a populated
        AddTriggeredAbility Verb to the super_stack. The
        controller of the card controls the ability.
        """
        player = source_of_ability.player_index
        # if meets condition:
        if self.condition.get(state, player, source_of_ability):
            obj = Stack.StackTrigger(controller=player,
                                     obj=self,
                                     pay_cost=None,
                                     do_effect=None)  # not yet populated
            caster = Verbs.AddTriggeredAbility()
            [caster] = caster.populate_options(state, player,
                                               source=source_of_ability,
                                               cause=None,
                                               stack_object=obj)
            state.super_stack.append(caster)

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.condition), str(self.effect))

    def copy(self, new_state: GameState | None = None):
        abil = TimedAbility(self.name, self.condition,
                            self.effect.copy(new_state))
        abil.__class__ = self.__class__
        return abil
