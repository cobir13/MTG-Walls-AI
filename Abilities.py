# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, Type, Tuple, TYPE_CHECKING, TypeVar

import Verbs
import Costs
# import Zone
import Match2
from Match2 import VerbPattern, SelfAsEnter
import Getters as Get
import Stack
import Phases

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
    def __init__(self, name, trigger: VerbPattern, effect: Verbs.Verb):
        self.name: str = name
        self.condition: VerbPattern = trigger
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
        if self.condition.match(verb, state, source_of_ability.player_index,
                                source_of_ability):
            player = source_of_ability.player_index
            stack_obj = Stack.StackTrigger(player, obj=self,
                                           pay_cost=None, do_effect=None)
            # Note: pay, effect verbs not yet populated. AddTriggeredAbility
            # does that later.
            caster = Verbs.AddTriggeredAbility()
            if isinstance(self.condition, SelfAsEnter):
                caster = Verbs.AddAsEntersAbility()
            [caster] = caster.populate_options(state, player,
                                               source=source_of_ability,
                                               cause=verb.subject,
                                               stack_object=stack_obj)
            if caster.can_be_done(state):
                state.super_stack.append(caster)

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.condition), str(self.effect))

    def get_id(self):
        return str(self)

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)

    def copy(self, new_state: GameState | None = None):
        abil = TriggeredAbility(self.name, self.condition,
                                self.effect.copy(new_state))
        abil.__class__ = self.__class__
        return abil

    def add_to_tracker(self, state: GameState, owner: Cardboard):
        state.trig_event.append(TriggeredAbilityHolder(owner, self))


# # -----------------------------------------------------------------------

class TimedAbility:
    def __init__(self, name, phase: Phases.Phases,
                 if_condition: Get.GetBool, effect: Verbs.Verb):
        self.name: str = name
        self.timing: Phases.Phases = phase
        self.condition: Get.GetBool = if_condition
        self.effect: Verbs.Verb = effect
        self.num_inputs = effect.num_inputs

    def add_any_to_super(self, state: GameState,
                         source_of_ability: Cardboard):
        """
        MUTATES.
        Checks if it is the right phase for this ability to occur,
        and also if the GameState meets the necessary conditions
        (if any) for it to occur.
        If the ability IS triggered, MUTATES the GameState to add
        a populated AddTriggeredAbility Verb to the super_stack.
        The controller of the card controls the ability.
        """
        if state.phase != self.timing:
            return  # wrong timing, so do nothing. doesn't fire.
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
        abil = TimedAbility(self.name, self.timing, self.condition,
                            self.effect.copy(new_state))
        abil.__class__ = self.__class__
        return abil

    def add_to_tracker(self, state: GameState, owner: Cardboard):
        state.trig_timed.append(TimedAbilityHolder(owner, self))


# # -----------------------------------------------------------------------

class ModificationEffect:
    """
    Broadly speaking, Effects change the values returned by Getters.
    For example, a card that gave all merfolk you control +1/+1
    and islandwalk would be two ModificationEffects: one to make
    Get.PowerAndTough return a value 1 larger than before, and one
    to add "islandwalk" to the return list of Get.Keywords.
    """

    def __init__(self, name: str, getter_to_affect: Type[Get.Getter], params):
        """params are parameters used by apply_modifier, in subclasses"""
        self.name: str = name
        self.getter_to_affect: Type[Get.Getter] = getter_to_affect
        self.params = params  # parameters used by apply_modifier

    def right_type_to_affect(self, getter) -> bool:
        return isinstance(getter, self.getter_to_affect)

    def apply_modifier(self, orig: T, state: GameState, player: int,
                       source: Cardboard, owner: Cardboard) -> T:
        """
        `orig` is the value that the Getter is currently
        reporting. This function applies the effect of the
        static ability by instead returning a DIFFERENT
        value -- usually an incremental chang from the
        given, previous value.
        `player` and `source` are the Player (index) and source
        Cardboard causing the Getter to be asked, respectively.
        This function assumes that the modification SHOULD
        be applied. It does not recheck whether the
        Effect is applicable. That is the job of
        whoever calls this function.
        """
        raise NotImplementedError


class BuffStats(ModificationEffect):
    def __init__(self, name: str,
                 params: Tuple[int | Get.GetInteger, int | Get.GetInteger]):
        """
        Params is a pair of integers representing power and toughness
        modifications to the creature's base power and toughness.
        """
        p_mod, t_mod = params  # modifiers to power and toughness
        if isinstance(p_mod, int):
            p_mod = Get.ConstInteger(p_mod)
        if isinstance(t_mod, int):
            t_mod = Get.ConstInteger(t_mod)
        super().__init__(name, Get.PowerAndTough, (p_mod, t_mod))
        self.params: Tuple[Get.GetInteger, Get.GetInteger]

    def apply_modifier(self, orig: Tuple[int, int], state: GameState,
                       player: int, source: Cardboard, owner: Cardboard
                       ) -> Tuple[int, int]:
        p_mod = self.params[0].get(state, player, source)
        t_mod = self.params[1].get(state, player, source)
        return orig[0] + p_mod, orig[1] + t_mod


class GrantKeyword(ModificationEffect):
    def __init__(self, name: str, params: List[str] | Get.GetStringList):
        """Params are a list of keywords to grant."""
        if isinstance(params, list):
            params = Get.ConstStringList(params)
        super().__init__(name, Get.Keywords, params)
        self.params: Get.GetStringList

    def apply_modifier(self, orig: List[str], state: GameState, player: int,
                       source: Cardboard, owner: Cardboard) -> List[str]:
        to_add = self.params.get(state, player, source)
        return orig + [kw for kw in to_add if kw not in orig]


# ----------


class ReplacementEffect:
    """
    In general, this effect prevents a Verb from occuring and
    instead replaces it with a different, modified version of
    the same Verb.
    """

    def __init__(self, name: str, verb_to_affect: Type[Verbs.Verb], params):
        """params are parameters used by apply_modifier, in subclasses"""
        self.name: str = name
        self.verb_to_affect: Type[Verbs.Verb] = verb_to_affect
        self.params = params  # parameters used by apply_modifier

    def right_type_to_affect(self, getter) -> bool:
        return (isinstance(getter, Verbs.Verb)
                and getter.is_type(self.verb_to_affect))

    def apply_modifier(self, orig: Verbs.Verb, state: GameState, player: int,
                       source: Cardboard, owner: Cardboard) -> Verbs.Verb:
        """
        `orig` is the original Verb which is now being replaced.
        This function applies the ReplacementEffect by returning
        a new, different Verb which should be run instead of the
        original Verb.
        `player` and `source` are the Player (index) and source
        Cardboard of the Verb, respectively.
        This function assumes that the modification SHOULD
        be applied. It does not recheck whether the
        Effect is applicable. That is the job of
        whoever calls this function.
        """
        raise NotImplementedError


# ----------


class StaticAbility:
    """
    Static abilities appear on permanents and apply for as long as
    the permanent remains in play. The given effect will be applied
    to all cards or verbs which meet the given criteria.
    Note: This class works for BOTH ModificationEffects AND
    ReplacementEffects.
    """

    def __init__(self,
                 effect: ModificationEffect | ReplacementEffect,
                 applies_to: Match2.CardPattern | Match2.VerbPattern):

        self.name: str = effect.name
        self.effect: ModificationEffect | ReplacementEffect = effect
        self.applies_to: Match2.CardPattern | Match2.VerbPattern = applies_to

    def is_applicable(self, target: Get.Getter | Verbs.Verb,
                      state: GameState, player: int, source: Cardboard,
                      owner: Cardboard) -> bool:
        """
        The card `owner` is creating this static ability. Now a
        Verb or a Getter has occurred, and we need to see if this
        Effect applies to it or not.
        `player` and `source` are the Player and Cardboard causing
        the Verb to be performed or the Getter to be asked (the
        `player` and `source` arguments to Getter.get or fields of
        the Verb).
        This function returns whether this static ability affects
        the given Getter or Verb, as a boolean.
        """
        # ModificationEffects are paired with CardPatterns looking at `source`
        if isinstance(self.effect, ModificationEffect):
            return (self.effect.right_type_to_affect(target)
                    and self.applies_to.match(source, state, player, owner))
        # ReplacementEffect are paired with VerbPatterns looking at `target`
        elif isinstance(self.effect, ReplacementEffect):
            return (self.effect.right_type_to_affect(target)
                    and self.applies_to.match(target, state, player, owner))
        else:
            raise TypeError  # should only ever be one of these two types!
        # note: you CAN pass a Cardboard into a VerbPattern. It'll
        # return False but it won't crash. Same with passing a Verb
        # into a CardPattern

    def apply_modifier(self, value: T, state: GameState, player: int,
                       source: Cardboard, owner: Cardboard) -> T:
        """
        Modify the Verb or the Getter output as dictated by the
        Effect. This function assumes that the modification
        SHOULD be applied. It does not recheck whether the
        StaticAbility is applicable. That is the job of whoever
        calls this function.
        """
        return self.effect.apply_modifier(value, state, player, source, owner)

    def copy(self, new_state: GameState | None = None):
        abil = StaticAbility(self.name, self.effect,
                             self.applies_to)
        abil.__class__ = self.__class__
        return abil

    def add_to_tracker(self, state: GameState, owner: Cardboard):
        state.statics.append(StaticAbilityHolder(owner, self))


# # -----------------------------------------------------------------------

# # duration: Phases.Phases | Get.GetBool):
#
#
# class OngoingEffect:
#     """
#     This class is for ongoing effects that are created by another
#     spell or ability. In practice, it is much like a Static
#     Ability in that it holds a ModificationEffect (which modifies
#     Getters) or a ReplacementEffect (which modifies Verbs).
#     Unlike a StaticAbility, it has an independent existence from
#     the card or ability which created it. It typically lasts until
#     end of turn or until some other condition is met, rather than
#     until the card generating the static effect leaves play. It is
#     often targetted rather than affecting an entire category of
#     cards, but either is possible.
#     """
#
#     def __init__(self, name: str,
#                  effect: ModificationEffect | ReplacementEffect,
#                  applies_to: Match2.CardPattern | Match2.VerbPattern | None,
#                  duration: Phases.Phases | Get.GetBool):
#         """
#         duration: the effect ends at the given Phase; or the effect
#                 ends when the GetBool becomes False
#
#         """
#
#
#         self.name: str = name
#         self.getter_to_affect: Type[Get.Getter] = getter_to_affect
#         self.pattern_for_card: Match2.CardPattern = pattern_for_card
#         self.duration = duration  # phase or GetBool==True
#         self.params = params  # parameters used by apply_modifier
#
#     def is_applicable(self, getter: Get.Getter, subject: Match.SUBJECT,
#                       state: GameState, player: int, owner: Cardboard,
#                       ) -> bool:
#         """
#         The card `owner` is creating this static ability. Now
#         `player` is calling the Getter `getter` to find out info
#         about `subject` (a Cardboard or Player, usually). This
#         function returns whether this static ability affects the
#         value returned by the Getter?
#         """
#         return (isinstance(getter, self.getter_to_affect)
#                 and self.pattern_for_card.match(subject, state,
#                                                 player, owner))
#
#     def apply_modifier(self, value: T, state: GameState, player: int,
#                        source: Cardboard, owner: Cardboard) -> T:
#         """
#         `value` is the value that the Getter is currently
#         reporting. This function applies the effect of the
#         static ability by instead returning a DIFFERENT
#         value -- usually an incremental chang from the
#         given, previous value.
#         This function assumes that the modification SHOULD
#         be applied. It does not recheck whether the
#         StaticAbility is applicable. That is the job of
#         whoever calls this function.
#         """
#         raise NotImplementedError
#
#     def copy(self, new_state: GameState | None = None):
#         abil = StaticAbility(self.name, self.getter_to_affect,
#                              self.pattern_for_card, self.params)
#         abil.__class__ = self.__class__
#         return abil
#
#     def add_to_tracker(self, state: GameState, owner: Cardboard):
#         state.statics.append(TimedAbilityHolder(owner, self))


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
        self.static_ability: StaticAbility = effect
        self.lasts_until: Phases.Phases | None = lasts_until

    def copy(self, state: GameState):
        return StaticAbilityHolder(self.card.copy(state),
                                   self.static_ability.copy(state),
                                   self.lasts_until)


# class OngoingEffectHolder:
#     """
#     Holds an ongoing effect as well as the target (NOT the source!)
#     of the effect. One-shot effects no longer need to track their
#     source.
#     """
#
#     def __init__(self, referred_card: Cardboard, effect: StaticAbility,
#                  lasts_until: Phases.Phases | None = None):
#         self.card: Cardboard = referred_card
#         self.effect: StaticAbility = effect
#         self.lasts_until: Phases.Phases | None = lasts_until
#
#     def copy(self, state: GameState):
#         return StaticAbilityHolder(self.card.copy(state),
#                                    self.effect.copy(state),
#                                    self.lasts_until)
