# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, Type, Tuple, TYPE_CHECKING, TypeVar

import Verbs
import Costs
import Zone
import Match
import Getters as Get
import Stack
import Phases
from Match import DetectVerbDone, DetectAsEnter

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard

T = TypeVar('T')


# # -----------------------------------------------------------------------

class ActivatedAbility:
    def __init__(self, name, cost: Costs.Cost, effect: Verbs.Verb):
        self.name: str = name
        self.cost: Costs.Cost = cost
        self.effect: Verbs.Verb = effect

    def valid_caster(self, state: GameState, player: int,
                     source: Cardboard) -> Verbs.PlayAbility | None:
        """
        If this ability can be activated right now (there are
        valid ways to pay its costs and choose its targets),
        return a PlayAbility Verb. That Verb, when run, will
        ask its controller to choose those payment options and
        targets and will put a StackAbility for this ability
        on the stack.
        If the ability cannot be activated, None is returned.
        Note: the PlayAbility's StackObject has no populated
        pay_cost or do_effect yet.
        """
        payments = self.cost.get_payment_plans(state, player, source, None)
        if len(payments) == 0:
            return None  # no valid way to pay costs
        effects = self.effect.populate_options(state, player, source, None)
        if len([eff for eff in effects if eff.can_be_done(state)]) == 0:
            return None  # no valid way to choose effects
        # if reached here, ability can be done!  build a caster for it
        stack_obj = Stack.StackAbility(controller=player, obj=self,
                                       pay_cost=None, do_effect=None)
        # figure out which verb can be used to cast this object
        caster: Verbs.PlayAbility = Verbs.PlayAbility()
        if self.effect.is_type(Verbs.AddMana):
            caster = Verbs.PlayManaAbility()
        [caster] = caster.populate_options(state=state, player=player,
                                           source=source, cause=None,
                                           stack_object=stack_obj)
        return caster

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


# # -----------------------------------------------------------------------

class TriggeredAbility:
    def __init__(self, name, trigger: DetectVerbDone, effect: Verbs.Verb):
        self.name: str = name
        self.trigger: DetectVerbDone = trigger
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
            if isinstance(self.trigger, DetectAsEnter):
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


# # -----------------------------------------------------------------------

class TimedAbility:
    def __init__(self, name, if_condition: Get.GetBool, effect: Verbs.Verb):
        self.name: str = name
        self.condition: Get.GetBool = if_condition
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


# # -----------------------------------------------------------------------

class StaticAbility:
    """Broadly speaking, Static Abilities affect the values returned
    by Getters. For example, a card that gave all merfolk you control
    +1/+1 and islandwalk would be three StaticAbilities: one to make
    Get.Power return a value 1 larger than before when called on
    merfolk you control; one doing the same thing to Get.Toughness;
    and one to add "islandwalk" to the return list of Get.Keywords.
    """

    def __init__(self, name: str, getter_to_affect: Type[Get.Getter],
                 pattern_for_card: Match.CardPattern, params):
        self.name: str = name
        self.getter_to_affect: Type[Get.Getter] = getter_to_affect
        self.pattern_for_card: Match.CardPattern = pattern_for_card
        self.params = params  # parameters used by apply_modifier

    def is_applicable(self, getter: Get.Getter, subject: Match.SUBJECT,
                      state: GameState, player: int, owner: Cardboard,
                      ) -> bool:
        """
        The card `owner` is creating this static ability. Now
        `player` is calling the Getter `getter` to find out info
        about `subject` (a Cardboard or Player, usually). This
        function returns whether this static ability affects the
        value returned by the Getter?
        """
        return (isinstance(getter, self.getter_to_affect)
                and self.pattern_for_card.match(subject, state, player, owner))

    def apply_modifier(self, value: T, state: GameState, player: int,
                       source: Cardboard, owner: Cardboard) -> T:
        """
        `value` is the value that the Getter is currently
        reporting. This function applies the effect of the
        static ability by instead returning a DIFFERENT
        value -- usually an incremental chang from the
        given, previous value.
        This function assumes that the modification SHOULD
        be applied. It does not recheck whether the
        StaticAbility is applicable. That is the job of
        whoever calls this function.
        """
        raise NotImplementedError

    def copy(self, new_state: GameState | None = None):
        abil = StaticAbility(self.name, self.getter_to_affect,
                             self.pattern_for_card, self.params)
        abil.__class__ = self.__class__
        return abil


class BuffStats(StaticAbility):
    def __init__(self, name: str, pattern_for_card: Match.CardPattern,
                 params: Tuple[int | Get.GetInteger, int | Get.GetInteger],
                 only_in_play=True):
        """Buffs usually only affect creatures on the battlefield
        ("in play"), so this condition can be added automatically.
        No need to spell it out in pattern_for_card.
        Params is a pair of integers representing power and toughness
        modifications to the creature's base power and toughness.
        """
        full_pattern = pattern_for_card  # TODO: & Match.IsType(Creature)
        if only_in_play:
            full_pattern = full_pattern & Match.IsInZone(Zone.Field)
        p_mod, t_mod = params  # modifiers to power and toughness
        if isinstance(p_mod, int):
            p_mod = Get.ConstInteger(p_mod)
        if isinstance(t_mod, int):
            t_mod = Get.ConstInteger(t_mod)
        super().__init__(name, Get.PowerAndTough, full_pattern, (p_mod, t_mod))
        self.params: Tuple[Get.GetInteger, Get.GetInteger]

    def apply_modifier(self, value: Tuple[int, int], state: GameState,
                       player: int, source: Cardboard, owner: Cardboard
                       ) -> Tuple[int, int]:
        p_mod = self.params[0].get(state, player, source)
        t_mod = self.params[1].get(state, player, source)
        return value[0] + p_mod, value[1] + t_mod


class GrantKeyword(StaticAbility):
    def __init__(self, name: str, pattern_for_card: Match.CardPattern,
                 params: List[str] | Get.GetStringList,
                 only_in_play=True):
        """Keywords usually only aply to creatures on the battlefield
        ("in play"), so this condition can be added automatically.
        No need to spell it out in pattern_for_card.
        Params are the list of keywords to grant."""
        full_pattern = pattern_for_card
        if only_in_play:
            full_pattern = full_pattern & Match.IsInZone(Zone.Field)
        if isinstance(params, list):
            params = Get.ConstStringList(params)
        super().__init__(name, Get.Keywords, full_pattern, params)
        self.params: Get.GetStringList

    def apply_modifier(self, value: List[str], state: GameState, player: int,
                       source: Cardboard, owner: Cardboard) -> List[str]:
        to_add = self.params.get(state, player, source)
        return value + [kw for kw in to_add if kw not in value]


# # -----------------------------------------------------------------------



# # -----------------------------------------------------------------------

class TriggeredAbilityHolder:
    """Holds triggered abilities in the GameState tracking lists"""
    def __init__(self, referred_card: Cardboard, effect: TriggeredAbility):
        self.card: Cardboard = referred_card
        self.effect: TriggeredAbility = effect

    def copy(self, state: GameState):
        return TriggeredAbilityHolder(self.card.copy(state),
                                      self.effect.copy(state))


class TimedAbilityHolder:
    """Holds timed abilities in the GameState tracking lists"""
    def __init__(self, referred_card: Cardboard, effect: TimedAbility):
        self.card: Cardboard = referred_card
        self.effect: TimedAbility = effect

    def copy(self, state: GameState):
        return TimedAbilityHolder(self.card.copy(state),
                                  self.effect.copy(state))


class StaticAbilityHolder:
    """Holds static abilities in the GameState tracking lists"""
    def __init__(self, referred_card: Cardboard, effect: StaticAbility,
                 lasts_until: Phases.Phases | None = None):
        self.card: Cardboard = referred_card
        self.effect: StaticAbility = effect
        self.lasts_until: Phases.Phases | None = lasts_until

    def copy(self, state: GameState):
        return StaticAbilityHolder(self.card.copy(state),
                                   self.effect.copy(state),
                                   self.lasts_until)

class OngoingEffectHolder:
    """Holds an ongoing effect as well as the target
    (NOT the source!) of the effect"""



