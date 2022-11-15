# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING, TypeVar

import Verbs
import Costs
import Getters as Get
import Stack
import Times
import Zone
import Match2

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard
    from Match2 import VerbPattern

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
    """
    A TriggeredAbility says that when a triggering Verb is
    performed, do a specific Verb in response.
    For example, Wall of Blossoms says "when this card enters the
    battlefield, draw a card." In this case, the trigger condition
    is that a MoveToZone Verb with the Wall of Blossoms as the
    subject and with Zone.Field as its destination was just
    performed.  The effect Verb is to make the Wall of Blossom's
    controller draw a card.
    """

    def __init__(self, name, triggers_from: VerbPattern, effect: Verbs.Verb,
                 duration: (Times.RelativeTime | Get.GetBool | None) = None):
        """
        `duration` describes the times when the TriggeredAbility
        will listen for a triggering Verb to occur.  There are
        three possible ways of describing this:
        - Times.RelativeTime
                The TriggeredAbility will listen from now until the
                given phase, when the ability will vanish forever.
        - Get.GetBool
                The TriggeredAbility will listen from now until the
                Getter evaluates to False, whereupon it will vanish.
        - None
                The TriggeredAbility will listen so long as the
                source Cardboard creating it remains on the
                battlefield.
        """
        self.name: str = name
        self.triggers_from: VerbPattern = triggers_from
        self.effect: Verbs.Verb = effect
        self.duration: Times.RelativeTime = duration

    def add_effect_to_super(self, state: GameState,
                            source_of_ability: Cardboard,
                            causing_verb: Verbs.Verb):
        """
        Adds a populated AddTriggeredAbility Verb for the effect
        to the state's super_stack, assuming that the effect can
        legally be done. MUTATES THE GAMESTATE.
        Note: does NOT check whether the causing_verb meets the
        trigger condition or not. That should be done manually
        by whoever calls this function.
        """
        # if self.triggers_from.match(verb, state,
        #                             source_of_ability.player_index,
        #                             source_of_ability):
        player = source_of_ability.player_index
        stack_obj = Stack.StackTrigger(player, obj=self,
                                       pay_cost=None, do_effect=None)
        # Note: pay, effect verbs not yet populated. AddTriggeredAbility
        # does that later.
        caster = Verbs.AddTriggeredAbility()
        # I can't use isinstance without causing circular imports
        if type(self.triggers_from).__name__ == "SelfAsEnter":
            caster = Verbs.AddAsEntersAbility()
        [caster] = caster.populate_options(state, player,
                                           source=source_of_ability,
                                           cause=causing_verb.subject,
                                           stack_object=stack_obj)
        if caster.can_be_done(state):
            state.super_stack.append(caster)

    def __str__(self):
        return "TrigAbility(%s -> %s)" % (
            str(self.triggers_from), str(self.effect))

    def get_id(self):
        return str(self)

    def is_type(self, verb_type):
        return self.effect.is_type(verb_type)

    def copy(self, new_state: GameState | None = None):
        abil = TriggeredAbility(self.name, self.triggers_from,
                                self.effect.copy(new_state))
        abil.__class__ = self.__class__
        return abil

    def add_to_tracker(self, state: GameState, owner: Cardboard):
        """Add a Holder for this ability to the GameState's
        trigger-tracker list. `owner` is the card that owns
        this triggered ability."""
        duration = Holder.calcuate_duration(self.duration, state, owner)
        holder = TriggeredAbilityHolder(owner, owner.player_index,
                                        self, duration)
        state.trig_event.append(holder)


# # -----------------------------------------------------------------------

class TimedAbility:
    """
    A TimedAbility describes an ability which causes a Verb to
    occur at a specified moment in time.
    For example, Nyx-Fleece Ram says "at the beginning of your
    upkeep, you gain 1 life." This is a TimedAbility. The
    timing is "your upkeep" and the Verb is "you can 1 life."
    """

    def __init__(self, name, timing: Times.RelativeTime,
                 effect: Verbs.Verb,
                 duration: Times.RelativeTime | Get.GetBool | None = None):
        """
        `duration` describes the times when the TimedAbility is
        permitted to activate. Outside these times, the ability
        will not occur even if the timing is right. (For example,
        if Nyx-Fleece Ram leaves the battlefield, the ability
        will not occur even though your upkeep is beginning).
        There are three possible ways of describing these times:
        - Times.RelativeTime
                The TimedAbility will occur if the inciting phase
                happens between now and the given RelativeTime.
        - Get.GetBool
                The TimedAbility will occur if the inciting phase
                happens between now and when the Getter first
                evaluates to False. After it evaluates to False,
                the TImedAbility can never occur.
        - None
                The TimedAbility will occur if the inciting phase
                happens while the source Cardboard creating it
                remains on the battlefield.
        """

        self.name: str = name
        self.timing: Times.RelativeTime = timing
        self.effect: Verbs.Verb = effect
        self.duration: Times.RelativeTime | Get.GetBool | None = duration

    def add_effect_to_super(self, state: GameState,
                            source_of_ability: Cardboard):
        """
        Adds a populated AddTriggeredAbility Verb for the effect
        to the state's super_stack, assuming that the effect can
        legally be done. MUTATES THE GAMESTATE.
        Note: does NOT check whether the GameState meets the timing
        condition not. That should be done manually by whoever
        calls this function.
        """
        player = source_of_ability.player_index
        obj = Stack.StackTrigger(controller=player,
                                 obj=self,
                                 pay_cost=None,
                                 do_effect=None)  # not yet populated
        caster = Verbs.AddTriggeredAbility()
        [caster] = caster.populate_options(state, player,
                                           source=source_of_ability,
                                           cause=None,
                                           stack_object=obj)
        if caster.can_be_done(state):
            state.super_stack.append(caster)

    def __str__(self):
        return "Ability(%s -> %s)" % (str(self.timing), str(self.effect))

    def copy(self, new_state: GameState | None = None):
        abil = TimedAbility(self.name, self.timing,
                            self.effect.copy(new_state), self.duration)
        abil.__class__ = self.__class__
        return abil

    def timing_matches(self, state: GameState, owner_player: int) -> bool:
        if state.phase != self.timing.phase:
            return False
        if isinstance(self.timing.player, int):
            assert owner_player == self.timing.player
            return state.active_player_index == self.timing.player
        else:
            if self.timing.player == "mine":
                return state.active_player_index == owner_player
            elif self.timing.player == "your":
                return state.active_player_index != owner_player
            else:
                return True  # right phase, "any" player

    def add_to_tracker(self, state: GameState, owner: Cardboard):
        duration = Holder.calcuate_duration(self.duration, state, owner)
        state.trig_timed.append(TimedAbilityHolder(owner, owner.player_index,
                                                   self, duration))


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
                 duration: Times.RelativeTime | Get.GetBool | None):
        """
        `duration` describes how long the ContinuousEffect applies
        for. There are three possible ways of describing this:
        - Times.RelativeTime
                The effect lasts from now until the given phase.
        - Get.GetBool
                The effect lasts until the Getter evaluates to
                False, whereupon it will vanish.
        - None
                The effect lasts so long as the source Cardboard
                creating it remains on the battlefield.
        """
        self.name: str = name
        self.condition: Match2.QueryPattern | Match2.VerbPattern = \
            thing_to_affect
        self.duration: Times.RelativeTime | Get.GetBool | None = duration
        self.params = None  # parameters used by apply_modifier, in subclasses
        # to avoid infinite loop, this allows Getters to temporarily disable
        # this effect which checking to see if it is applicable or not. It is
        # re-enabled afterwards.
        self.temporarily_ignore = False

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
        if self.duration is None:
            timesup = "leaves"
        else:  # Times.RelativeTime and Get.Bool both have nice string methods
            timesup = str(self.duration)
        return "%s modified by %s until %s" % (str(self.condition),
                                               self._string_params(), timesup)

    def add_to_tracker(self, state: GameState, owner: Cardboard):
        """For static abilities which add themselves directly
        to the GameState when the creature is in play. Other
        ways of applying the effect should use the appropriate
        Verb instead of using this function."""
        duration = Holder.calcuate_duration(self.duration, state, owner)
        h = ActiveAbilityHolder(source=owner,
                                controller=owner.player_index,
                                effect=self,
                                duration=duration,
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
        card_pattern = (pattern_for_source & Match2.CardType("creature")
                        & Match2.IsInZone(Zone.Field))
        pattern = Match2.QueryPattern(Get.PowerAndTough, card_pattern,
                                      pattern_for_player)
        super().__init__(name, pattern, duration)
        p_mod, t_mod = params  # modifiers to power and toughness
        if isinstance(p_mod, int):
            p_mod = Get.ConstInteger(p_mod)
        if isinstance(t_mod, int):
            t_mod = Get.ConstInteger(t_mod)
        self.params: Tuple[Get.GetInteger, Get.GetInteger] = (p_mod, t_mod)

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

        pattern = Match2.QueryPattern(Get.Keywords, pattern_for_source,
                                      pattern_for_player)
        super().__init__(name, pattern, duration)
        if isinstance(params, list):
            params = Get.ConstStringList(params)
        self.params: Get.GetStringList = params

    def apply_modifier(self, orig: List[str], state: GameState, player: int,
                       source: Cardboard, owner: Cardboard) -> List[str]:
        to_add = self.params.get(state, player, source)
        return orig + [kw for kw in to_add if kw not in orig]

    def _string_params(self) -> str:
        """Format the params nicely to be printed for debug, tracking."""
        return "+" + str(self.params)


# # -----------------------------------------------------------------------

class Holder:
    def __init__(self, source: Cardboard, controller: int,
                 effect: ContinousEffect | TriggeredAbility | TimedAbility,
                 duration: Tuple[int, Times.Phase] | Get.GetBool | None,
                 target: VerbPattern | Match2.QueryPattern | None):
        """
        duration: - turn and phase. if later than that, remove this holder.
                  - bool or GetBool. if False, remove this holder
                  - None. Holder endures until permanent leaves play
        target: - VerbPattern (for replacement effects and triggered abilities)
                - QueryPattern (for modification effects)
                - None (for timed abilities)
        """

        self.source: Cardboard = source  # card creating the ability
        self.controller: int = controller  # player controlling the ability
        self.effect: ContinousEffect | TriggeredAbility | TimedAbility = effect
        self.duration: Tuple[
                           int, Times.Phase] | Get.GetBool | None = duration
        self.target: VerbPattern | Match2.QueryPattern | None = target

    def copy(self, state: GameState):
        raise NotImplementedError

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

    @staticmethod
    def calcuate_duration(duration: Times.RelativeTime | Get.GetBool | None,
                          state, owner
                          ) -> Tuple[int, Times.Phase] | Get.GetBool | None:
        """turn relative time ("my next end step") into absolute"""
        if isinstance(duration, Times.RelativeTime):
            turn = state.total_turns
            # if already passed the phase this turn, soonest is next turn
            if duration.phase >= state.phase:
                turn += 1
            # now increment until we find the right player
            if duration.player == "mine":
                while turn % len(state.player_list) != owner.player_index:
                    turn += 1
            elif duration.player == "your":
                while turn % len(state.player_list) == owner.player_index:
                    turn += 1
            elif isinstance(duration.player, int):
                assert duration.player < len(state.player_list)
                while turn % len(state.player_list) != duration.player:
                    turn += 1
            return turn, duration.phase
        else:
            return duration


class ActiveAbilityHolder(Holder):
    """Holds active abilities (static, triggered, timed) in the
    GameState tracking lists"""

    def copy(self, state: GameState):
        return ActiveAbilityHolder(self.source.copy(state), self.controller,
                                   self.effect, self.duration,
                                   self.target)

    def is_applicable(self, subject: Verbs.Verb | Get.GetterQuery,
                      state: GameState):
        """This active ability cares about the given Verb or Getter"""
        if self.effect.temporarily_ignore:
            return False
        else:
            self.effect.temporarily_ignore = True
            # the call to `match` may recursively call `is_applicable` on this
            # (or other) effects. however, the call to THIS effect will be
            # caught by the base case above, so there will not be an infinite
            # loop
            r = self.target.match(subject, state, self.controller, self.source)
            self.effect.temporarily_ignore = False  # reset to active status
            return r

    def __str__(self):
        return "{%s, %s}" % (str(self.source), str(self.effect))

    def get_new_value(self, orig_value, state, player, source):
        return self.effect.apply_modifier(orig_value, state, player, source,
                                          self.source)


class TriggeredAbilityHolder(Holder):
    """Holds triggered abilities in the GameState tracking lists"""

    def __init__(self, source: Cardboard, controller: int,
                 effect: TriggeredAbility,
                 duration: Tuple[int, Times.Phase] | Get.GetBool | None):
        super().__init__(source, controller, effect, duration,
                         target=effect.triggers_from)
        self.effect: TriggeredAbility

    def copy(self, state: GameState):
        return TriggeredAbilityHolder(self.source.copy(state), self.controller,
                                      self.effect, self.duration)

    def apply_if_applicable(self, subject: Verbs.Verb, state: GameState):
        if self.target.match(subject, state, self.controller, self.source):
            self.effect.add_effect_to_super(state, self.source, subject)

    def __str__(self):
        return "{%s, %s}" % (str(self.source), str(self.effect))


class TimedAbilityHolder(Holder):
    """Holds timed abilities in the GameState tracking lists"""

    def __init__(self, source: Cardboard, controller: int,
                 effect: TimedAbility,
                 duration: Tuple[int, Times.Phase] | Get.GetBool | None):
        super().__init__(source, controller, effect, duration, target=None)
        self.effect: TimedAbility

    def copy(self, state: GameState):
        return TimedAbilityHolder(self.source.copy(state), self.controller,
                                  self.effect, self.duration)

    def __str__(self):
        return "{%s, %s}" % (str(self.source), str(self.effect))

    def apply_if_applicable(self, state: GameState):
        if self.effect.timing_matches(state, self.controller):
            self.effect.add_effect_to_super(state, self.source)
