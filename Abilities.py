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
import Getters as Get
import Stack
import Phases
import Zone
import Match2

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard
    from Match2 import VerbPattern
    import Match2

T = TypeVar('T')

# Abilities either cause Verbs to occur (activated, triggered, timed) or
# cause Effects to apply (replacement effects, modification effects). Note
# that one possible Verb is the Verb to apply an effect (e.g. "target creature
# gets +1/+1 until end of turn"), but that there are other ways for Effects
# to apply (mainly static abilities)



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
            # if isinstance(self.condition, SelfAsEnter):
            # I can't use isinstance without causing circular imports
            if type(self.condition).__name__ == "SelfAsEnter":
                caster = Verbs.AddAsEntersAbility()
            [caster] = caster.populate_options(state, player,
                                               source=source_of_ability,
                                               cause=verb.subject,
                                               stack_object=stack_obj)
            if caster.can_be_done(state):
                state.super_stack.append(caster)

    def __str__(self):
        return "TrigAbility(%s -> %s)" % (
        str(self.condition), str(self.effect))

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

class ContinousEffect:
    """
    Broadly speaking, Effects change the values returned by Getters
    (modification effect) or the Verbs that actually execute when
    you try to perform a Verb (replacement effects).
    For example, a card that gave all merfolk you control +1/+1
    and islandwalk would be two m odification effects: one to make
    Get.PowerAndTough return a value 1 larger than before, and one
    to add "islandwalk" to the return list of Get.Keywords.
    For example, a card that prevented all damage would be a
    replacement effect: DealDamage is being replaced with NullVerb.
    """

    def __init__(self, name: str,
                 thing_to_affect: Match2.QueryPattern | Match2.VerbPattern,
                 duration: Tuple[str, Phases.Phases] | Get.GetBool | None,
                 params):
        """
        duration: - until ( "mine" | "your" | "next", Phase)
                  - until GetBool becomes False
                  - None. Holder endures until permanent leaves play
        params are parameters used by apply_modifier, in subclasses
        """
        self.name: str = name
        self.condition: Match2.QueryPattern | Match2.VerbPattern = \
            thing_to_affect
        self.duration = duration
        self.params = params  # parameters used by apply_modifier
        if isinstance(self.condition, Match2.VerbPattern):
            self.modifies = "verb"
        else:
            self.modifies = "getter"

    def apply_modifier(self, orig: T, state: GameState, player: int,
                       source: Cardboard, owner: Cardboard) -> T:
        """
        `orig` is the value that the Getter is currently reporting
        or the Verb that is planning to execute. This function
        applies the effect of the static ability by instead
        returning a DIFFERENT value -- usually an incremental
        change from the previous Getter value or a new Verb to
        execute based on the old Verb.
        `player` and `source` are the Player (index) and source
        Cardboard causing the Getter to be asked or the Verb to be
        run, respectively.
        This function assumes that the modification SHOULD be
        applied. It does not recheck whether the Effect is
        applicable. That is the job of whoever calls this function.
        """
        raise NotImplementedError

    def _string_params(self) -> str:
        """Format the params nicely to be printed for debug, tracking."""
        raise NotImplementedError

    def __str__(self):
        if isinstance(self.duration, tuple):
            timesup = "%s %s" % (self.duration[0], str(self.duration[1]))
        elif self.duration is None:
            timesup = "leaves"
        else:
            timesup = str(self.duration)
        return "%s modified by %s until %s" % (str(self.condition),
                                               self._string_params(), timesup)

    def calcuate_duration(self, state, owner
                          ) -> Tuple[int, Phases.Phases] | Get.GetBool | None:
        """turn relative time ("my next end step") into absolute"""
        if isinstance(self.duration, tuple):
            turn = state.total_turns
            # if already passed the phase this turn, soonest is next turn
            if self.duration[1] >= state.phase:
                turn += 1
            # now increment until we find the right player
            if self.duration[0] == "mine":
                while turn % len(state.player_list) != owner.player_index:
                    turn += 1
            elif self.duration[0] == "your":
                while turn % len(state.player_list) == owner.player_index:
                    turn += 1
            return turn, self.duration[1]
        else:
            return self.duration

    def add_to_tracker(self, state: GameState, owner: Cardboard):
        """For static abilities which add themselves directly
        to the GameState when the creature is in play. Other
        ways of applying the effect should use the appropriate
        Verb instead of using this function."""
        h = StaticAbilityHolder(source=owner,
                                controller=owner.player_index,
                                effect=self,
                                duration=self.calcuate_duration(state, owner),
                                target=self.condition
                                )
        state.statics.append(h)


class BuffStats(ContinousEffect):
    def __init__(self, name: str, duration,
                 pattern_for_source: Match2.CardPattern | None,
                 pattern_for_player: Match2.PlayerPattern | None,
                 params: Tuple[int | Get.GetInteger, int | Get.GetInteger]):
        """
        Params is a pair of integers representing power and toughness
        modifications to the creature's base power and toughness.
        This class automatically assumes that you only want to affect
        creatures in play, so no need to specify the card type or the
        zone.
        """
        p_mod, t_mod = params  # modifiers to power and toughness
        if isinstance(p_mod, int):
            p_mod = Get.ConstInteger(p_mod)
        if isinstance(t_mod, int):
            t_mod = Get.ConstInteger(t_mod)
        card_pattern = (pattern_for_source & Match2.CardType("creature")
                        & Match2.IsInZone(Zone.Field))
        pattern = Match2.QueryPattern(Get.PowerAndTough, card_pattern,
                                      pattern_for_player)
        super().__init__(name, pattern, duration, (p_mod, t_mod))
        self.params: Tuple[Get.GetInteger, Get.GetInteger]

    def apply_modifier(self, orig: Tuple[int, int], state: GameState,
                       player: int, source: Cardboard, owner: Cardboard
                       ) -> Tuple[int, int]:
        p_mod = self.params[0].get(state, player, source)
        t_mod = self.params[1].get(state, player, source)
        return orig[0] + p_mod, orig[1] + t_mod

    def _string_params(self) -> str:
        """Format the params nicely to be printed for debug, tracking."""
        return "+%s/+%s" % (str(self.params[0]), str(self.params[1]))


class GrantKeyword(ContinousEffect):
    def __init__(self, name: str, duration,
                 pattern_for_source: Match2.CardPattern | None,
                 pattern_for_player: Match2.PlayerPattern | None,
                 params: List[str] | Get.GetStringList):
        """Params are a list of keywords to grant."""
        if isinstance(params, list):
            params = Get.ConstStringList(params)
        pattern = Match2.QueryPattern(Get.Keywords, pattern_for_source,
                                      pattern_for_player)
        super().__init__(name, pattern, duration, params)
        self.params: Get.GetStringList

    def apply_modifier(self, orig: List[str], state: GameState, player: int,
                       source: Cardboard, owner: Cardboard) -> List[str]:
        to_add = self.params.get(state, player, source)
        return orig + [kw for kw in to_add if kw not in orig]

    def _string_params(self) -> str:
        """Format the params nicely to be printed for debug, tracking."""
        return "+%s" % ",".join(self.params)





# # -----------------------------------------------------------------------


class ActiveAbilityHolder:
    """Holds active abilities (static, triggered, timed) in the
    GameState tracking lists"""

    def __init__(self, source: Cardboard, controller: int,
                 effect: ContinousEffect,
                 duration, target):
        """
        duration: - turn and phase. if later than that, remove this holder.
                  - bool or GetBool. if False, remove this holder
                  - None. Holder endures until permanent leaves play
        target: - VerbPattern (for replacement effects)
                - QueryPattern (for modification effects)
        """

        self.source: Cardboard = source  # card creating the ability
        self.controller: int = controller  # player controlling the ability
        self.effect: ContinousEffect = effect
        self.duration: Tuple[int, Phases.Phases] | Get.GetBool | None = duration
        self.target: VerbPattern | Match2.QueryPattern = target
        self.modifies: str = self.effect.modifies

    def copy(self, state: GameState):
        return ActiveAbilityHolder(self.source.copy(state), self.controller,
                                   self.effect, self.duration,
                                   self.target)

    def is_applicable(self, subject: Verbs.Verb | Get.GetterQuery,
                      state: GameState):
        """This active ability cares about the given Verb or Getter"""
        return self.target.match(subject, state, self.controller, self.source)

    def should_keep(self, state) -> bool:
        """Returns whether this ability still applies (True) or
        whether it is no longer applicable and ought to be removed
        from tracking (False). Note: this function does not itself
        remove or keep the ability, it just says what should be
        done by someone else."""
        if self.duration is None:  # keep as long as source is still in play
            return self.source.is_in(Zone.Field)
        elif isinstance(self.duration, bool):  # keep as long as True
            return self.duration
        elif isinstance(self.duration, Get.GetBool):  # keep as long as True
            return self.duration.get(state, self.controller, self.source)
        elif isinstance(self.duration, tuple):  # keep if not past expiration
            turn = self.duration[0]
            phase = self.duration[1]
            return (state.total_turns < turn
                    or (state.total_turns == turn and state.phase <= phase))
        else:
            return False  # this is impossible, so don't keep it

    def __str__(self):
        return "{%s, %s}" % (str(self.source), str(self.effect))


class StaticAbilityHolder(ActiveAbilityHolder):
    def get_new_value(self, orig_value, state, player, source):
        return self.effect.apply_modifier(orig_value, state, player, source,
                                          self.source)


# ----------


class TriggeredAbilityHolder:
    """Holds triggered abilities in the GameState tracking lists"""

    def __init__(self, referred_card: Cardboard, effect: TriggeredAbility):
        self.card: Cardboard = referred_card
        self.effect: TriggeredAbility = effect

    def copy(self, state: GameState):
        return TriggeredAbilityHolder(self.card.copy(state),
                                      self.effect.copy(state))

    def apply_if_applicable(self, verb: Verbs.Verb, state: GameState):
        """Adds the Triggered Ability to the super_stack, if
        it is triggered by this Verb."""
        self.effect.add_any_to_super(state, self.card, verb)

    def __str__(self):
        return "{%s, %s}" %(str(self.card), str(self.effect))


class TimedAbilityHolder:
    """Holds timed abilities in the GameState tracking lists"""

    def __init__(self, referred_card: Cardboard, effect: TimedAbility):
        self.card: Cardboard = referred_card
        self.effect: TimedAbility = effect

    def copy(self, state: GameState):
        return TimedAbilityHolder(self.card.copy(state),
                                  self.effect.copy(state))

    def __str__(self):
        return "{%s, %s}" % (str(self.card), str(self.effect))
