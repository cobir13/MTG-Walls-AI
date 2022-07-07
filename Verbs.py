# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING
import random

from Stack import StackCardboard, StackAbility

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard
    from Abilities import ActivatedAbility

import ZONE
import MatchCardPatterns as Match
import Getters as Get
import ManaHandler
from RulesText import Creature, Land


class WinTheGameError(Exception):
    pass


class LoseTheGameError(Exception):
    pass


# #------------------------------------------------------------------------------

class Verb:
    def __init__(self):
        self.getter_list: List[Get.Getter] = []
        self.sub_verbs: List[Verb] = []

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        # this function assumes that THIS verb can be done, so all that is
        # left to do is to check if all of the sub-verbs can be done.
        # subclasses will implement whether they can be done or not, and
        # then call this to handle the sub-verbs.
        i_start = self.num_inputs
        for v in self.sub_verbs:
            i_end = i_start + v.num_inputs
            if i_end > len(choices):
                return False  # not enough choices specified
            if not v.can_be_done(state, subject, choices[i_start:i_end]):
                # if any verb cannot be done, the whole list cannot be done
                return False
            i_start = i_end  # increment to use the next choices for next verb
        return True  # if reached here, all verbs are doable!

    def do_it(self, state: GameState, subject: Cardboard,
              choices: list) -> List[Tuple[GameState, Cardboard, list]]:
        """if this Verb has `mutates`, then this function
        mutates the original gamestate.
        If it does not have `mutates` (which is to say, if it
        has multiple possible outputs), then it copies the original
        gamestate rather than mutating it.
        
        In either case, the function returns a list of 
        (GameState,Cardboard,List[Cardboard]) tuples, one tuple
        per possible way that this Verb can be executed. The
        elements in the tuple are the new GameState, the new source
        Cardboard, and any (copied) choices which have not yet been
        used up.
        """
        # `trigger_source` is source of the trigger. Not to be confused
        # with `source`, which is the source of the Verb which is
        # potentially CAUSING the trigger.
        for trigger_source in state.field + state.grave + state.hand:
            for ability in trigger_source.rules_text.trig_verb:
                if ability.is_triggered(self, state, trigger_source, subject):
                    effect = StackAbility(ability, trigger_source, [subject])
                    state.super_stack.append(effect)
        # return the expected triplet of GameState, source Cardboard,
        # and list of choices. But strip out any choices that this
        # Verb already 'used up'.
        return [(state, subject, choices[self.num_inputs:])]

    def __str__(self):
        text = type(self).__name__
        if len(self.sub_verbs) > 0:
            text += "(" + ",".join([str(v) for v in self.sub_verbs]) + ")"
        return text

    def choose_choices(self, state: GameState, subject: Cardboard):
        """returns a list of sub-lists. Each sub-list is the length
        of `getter_list` and represents one possible way to choose
        modes and/or targets for this Verb."""
        # list of sublists. start with 1 sublist, which is empty
        choices = [[]]
        for getter in self.getter_list:
            gotten = getter.get(state, subject)
            if getter.single_output:
                # if only one option, add it to each sublist
                choices = [sublist + [gotten] for sublist in choices]
            else:
                # if many options, make more sublists (one with each added)
                new_choices = []
                for x in gotten:
                    new_choices += [sublist + [x] for sublist in choices]
                choices = new_choices
        # now get any choices from any sub-verbs
        for v in self.sub_verbs:
            verb_choices = v.choose_choices(state, subject)
            new_list = []
            for sublist in choices:
                new_list += [sublist + ch for ch in verb_choices]
            choices = new_list
        return choices

    @property
    def num_inputs(self):
        from_getters = len(self.getter_list)
        from_sub = sum([v.num_inputs for v in self.sub_verbs])
        return from_getters + from_sub

    @property
    def mutates(self):
        # note: all([])==True. So Verbs with no options mutate. good.
        getters_mutate = not all([g.single_output for g in self.getter_list])
        subs_mutate = any([v.mutates for v in self.sub_verbs])
        return getters_mutate or subs_mutate

    def is_type(self, verb_type: type):
        self_is = isinstance(self, verb_type)
        sub_is = any([v.is_type(verb_type) for v in self.sub_verbs])
        return self_is or sub_is

    def get_sub_verbs(self, verb_type: type):
        verbs_that_match = [self]
        if self.is_type(verb_type):
            verbs_that_match.append(self)
        for v in self.sub_verbs:
            verbs_that_match += v.get_sub_verbs(verb_type)
        return verbs_that_match


class VerbAtomic(Verb):
    pass


class VerbOnSubjectCard(Verb):
    """acts on the source passed into the `do_it` method"""
    pass


class VerbOnTarget(Verb):
    """Applies the given VerbOnSubjectCard to the first element of the
    `choices` argument passed into the `do_it` method (which should
    be a Cardboard) rather than on the `subject` argument. The
    remaining elements of `choices` are passed along to the Verb.
    """

    def __init__(self, cardboard_getter: Get.Getter, verb: VerbOnSubjectCard):
        super().__init__()
        self.getter_list = [cardboard_getter]
        self.sub_verbs = [verb]

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return (len(choices) >= 1
                and super().can_be_done(state, choices[0], choices))

    def do_it(self, state: GameState, subject: Cardboard, choices: list):
        return self.sub_verbs[0].do_it(state, choices[0], choices[1:])


class ManyVerbs(Verb):
    def __init__(self, list_of_verbs: List[Verb]):
        super().__init__()
        self.sub_verbs = list_of_verbs
        self.getter_list = []


# ------------------------------------------------------------------------------

class VerbManyTimes(Verb):
    def __init__(self, verb: Verb, getter: Get.Integer):
        super().__init__()
        self.sub_verbs = [verb]
        self.getter_list = [getter]

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return (len(choices) >= 1
                and self.sub_verbs[0].can_be_done(state, subject, choices[1:]))

    def do_it(self, state: GameState, subject: Cardboard, choices):
        """mutates!"""
        num_to_repeat = choices[0]
        # build a ManyVerbs containing this verb repeated a bunch, and do that
        multi_verb = ManyVerbs([self.sub_verbs[0]] * num_to_repeat)
        return multi_verb.do_it(state, subject, choices[1:])

    def choose_choices(self, state: GameState, subject: Cardboard):
        raw_choices = super().choose_choices(state, subject)
        # In each sublist in raw_choices, the first is the number of times to
        # repeat the Verb and the rest is one copy of the choices for that
        # Verb. I need to duplicate those other choices according to the
        # number of times we'll be repeating it.
        return [[sub[0]]+(sub[1:]*sub[0]) for sub in raw_choices]


# ------------------------------------------------------------------------------

class PayMana(VerbAtomic):
    """deducts the given amount of mana from the GameState's mana pool"""

    def __init__(self, mana_string: str):
        super().__init__()
        self.mana_cost = ManaHandler.ManaCost(mana_string)

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return state.pool.can_afford_mana_cost(self.mana_cost)

    def do_it(self, state, subject, choices):
        state.pool.pay_mana_cost(self.mana_cost)
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------   

class AddMana(VerbAtomic):
    """adds the given amount of mana to the GameState's mana pool"""

    def __init__(self, mana_string: str):
        super().__init__()
        self.mana_pool_to_add = ManaHandler.ManaPool(mana_string)

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject, choices):
        state.pool.add_mana(self.mana_pool_to_add)
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# =============================================================================

class LoseOwnLife(VerbAtomic):
    def __init__(self, damage_getter: Get.Integer):
        super().__init__()
        self.getter_list = [damage_getter]

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject, choices):
        damage = choices[0]
        state.life -= damage
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class DealDamageToOpponent(VerbAtomic):
    def __init__(self, damage_getter: Get.Integer):
        super().__init__()
        self.getter_list = [damage_getter]

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject, choices):
        damage = choices[0]
        state.opponent_life -= damage
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class TapSelf(VerbOnSubjectCard):
    """taps `subject` if it was not already tapped."""

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return subject.zone == ZONE.FIELD and not subject.tapped

    def do_it(self, state, subject, choices):
        subject.tapped = True
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class TapSymbol(TapSelf):
    """{T}. `subject` gets tapped if it's not a summoning-sick creature"""

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return (super().can_be_done(state, subject, choices)
                and not (Match.CardType(Creature).match(subject, state,
                                                        subject)
                         and subject.summon_sick))

    def __str__(self):
        return "{T}"


# ----------

class TapAny(VerbOnTarget):

    def __init__(self, patterns: List[Match.CardPattern]):
        getter = Get.Chooser(Get.ListFromZone(patterns, ZONE.FIELD), 1, False)
        super().__init__(getter, TapSelf())


# ----------

class UntapSelf(VerbOnSubjectCard):

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return subject.tapped and subject.zone == ZONE.FIELD

    def do_it(self, state, subject, choices):
        subject.tapped = False
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class AddCounterToSelf(VerbOnSubjectCard):
    """Marks the given `subject` as only able to activate this ability once
    per turn"""

    def __init__(self, counter_text: str):
        super().__init__()
        self.counter_text = "@" + counter_text  # "@" is invisible counter

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return subject.zone == ZONE.FIELD

    def do_it(self, state, subject, choices):
        subject.add_counter(self.counter_text)
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class ActivateOncePerTurn(VerbOnSubjectCard):
    """Marks the given `subject` as only able to activate this ability once
    per turn"""

    def __init__(self, ability_name: str):
        super().__init__()
        self.counter_text = "@" + ability_name  # "@" is invisible counter

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return (subject.zone == ZONE.FIELD
                and self.counter_text not in subject.counters)

    def do_it(self, state, subject, choices):
        subject.add_counter(self.counter_text)
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class ActivateOnlyAsSorcery(VerbAtomic):
    """Checks that the stack is empty and cannot be done otherwise"""

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return len(state.stack) == 0

    def do_it(self, state, subject, choices):
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class Shuffle(VerbAtomic):
    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject: Cardboard | None, choices):
        # add triggers to super_stack, reduce length of choices list
        """Mutates. Reorder deck randomly."""
        random.shuffle(state.deck)

    @property
    def mutates(self):
        return True


# ----------

class MoveToZone(VerbOnSubjectCard):
    """Moves the subject card to the given zone"""

    def __init__(self, destination_zone):
        super().__init__()
        self.destination = destination_zone
        self.origin = None  # to let triggers check where card moved from

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        if subject.zone in [ZONE.DECK, ZONE.HAND, ZONE.FIELD, ZONE.GRAVE]:
            return subject in state.get_zone(subject.zone)

    def do_it(self, state, subject, choices=()):
        self.origin = subject.zone  # so trigger knows where card moved from
        # remove from origin
        if self.origin in [ZONE.DECK, ZONE.HAND, ZONE.FIELD, ZONE.GRAVE]:
            state.get_zone(self.origin).remove(subject)
        # add to destination
        subject.zone = self.destination
        zone_list = state.get_zone(self.destination)
        zone_list.append(subject)
        # sort the zones that need to always be sorted
        state.re_sort(self.destination)
        # any time you change zones, reset the cardboard parameters
        subject.tapped = False
        subject.summon_sick = True
        subject.counters = [c for c in subject.counters if
                            c[0] == "$"]  # sticky counters stay
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class DrawCard(VerbAtomic):
    """draw from index 0 of deck"""

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard | None,
                    choices: list) -> bool:
        return True  # Even if the deck is 0, you CAN draw. you'll just lose

    def do_it(self, state, subject: Cardboard | None, choices: list | None):
        if len(state.deck) > 0:
            mover = MoveToZone(ZONE.HAND)
            mover.do_it(state,
                        state.deck[0], )  # adds move triggers to super_stack
            # add triggers to super_stack, reduce length of choices list
            return super().do_it(state, subject, choices)
        else:
            raise LoseTheGameError


# ----------

class PlayLandForTurn(VerbAtomic):
    """Doesn't actually move any cards, just toggles the gamestate to say
    that we have played a land this turn"""

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return not state.has_played_land

    def do_it(self, state, subject, choices):
        state.has_played_land = True
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class AsEnterEffect(Verb):
    pass  # TODO


# ------------------------------------------------------------------------------

# class VerbOnSplitList(Verb):
#     def __init__(self, act_on_chosen:Verb, options:list, chosen:list,
#                  act_on_non_chosen:Verb = None):
#         super().__init__()
#         self.act_on_chosen = act_on_chosen
#         self.act_on_non_chosen = act_on_non_chosen
#         self.options = options
#         self.chosen = chosen
#         #TODO


# ------------------------------------------------------------------------------


class ActivateAbility(VerbAtomic):
    def __init__(self, ability: ActivatedAbility):
        super().__init__()
        self.ability = ability

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        """Activate the ability. The source of the ability is
        assumed to be the `subject` Cardboard.
        """
        pay_choices = choices[:self.ability.cost.num_inputs]
        targets = choices[self.ability.cost.num_inputs:]
        return (self.ability.cost.can_be_done(state, subject, pay_choices) and
                self.ability.effect.can_be_done(state, subject, targets))

    def do_it(self, state: GameState, subject: Cardboard, choices: list):
        """Activate the ability. The source of the ability is
        assumed to be the `subject` Cardboard. `choices` describe
        the choices for paying for the ability, followed by choices
        for using the ability. Note that super_stack is NOT
        guaranteed to be clear!
        """
        # check to make sure the execution is legal
        if not self.can_be_done(state, subject, choices):
            return []
        # 601.2b: choose costs (additional costs, choose X, choose hybrid).
        # this has already been done by choices.
        # 601.2c: choose targets and modes -- already done by choices.
        # 601.2f: determine total cost -- part of payment for me, I think?
        # 601.2g: activate mana abilities -- I don't actually permit this.
        # 601.2h: pay costs
        copy_of_game, things = state.copy_and_track([subject] + choices)
        copy_of_spell = things[0]
        copy_of_choices = things[1:]
        # The casting will chew through all the payment choices, leaving only
        # the target choices in the resulting tuples. Then those tuples are
        # returned as a list of (GameState, Cardboard, choices) tuples.
        list_of_tuples = self.ability.cost.do_it(copy_of_game, copy_of_spell,
                                                 copy_of_choices)
        # Build a StackAbility and add it to the stack
        if not self.ability.is_type(AddMana):
            for g1, s1, targets in list_of_tuples:
                g1.stack.append(StackAbility(self.ability, s1, targets))
        # ...except for Mana Abilities which don't use the stack
        else:
            new_tuple_list = []
            for g1, s1, targets in list_of_tuples:
                new_tuple_list += self.ability.effect.do_it(g1, s1, targets)
            list_of_tuples = new_tuple_list
        # 601.2i: ability has now "been activated".  Any abilities which
        # trigger from some aspect of paying the costs have already
        # been added to the superstack during ability.cost.pay. Now add
        # any trigger that trigger off of this activation itself.
        final_results = []
        for g2, s2, targets2 in list_of_tuples:
            final_results += super().do_it(g2, s2, targets2)
        return final_results

    def choose_choices(self, state: GameState, subject: Cardboard):
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payment_choices = self.ability.cost.choose_choices(state, subject)
        # 601.2c: choose targets and modes
        target_choices = self.ability.effect.choose_choices(state, subject)
        # combine all combinations of these
        new_choices = []
        for sub_pay in payment_choices:
            for sub_target in target_choices:
                new_choices.append(
                    sub_pay + sub_target)  # concatenate sub-lists
        return new_choices

    def mutates(self):
        return False

    def num_inputs(self):
        return self.ability.cost.num_inputs + self.ability.effect.num_inputs


# ------------------------------------------------------------------------------

class CastCard(VerbOnSubjectCard):
    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        """Cast the `source` card"""
        cost = subject.rules_text.cost
        pay_choices = choices[:cost.num_inputs]
        if not cost.can_be_done(state, subject, pay_choices):
            return False
        if subject.effect is not None:
            target_choices = choices[cost.num_inputs:]
            if not subject.effect.can_afford(state, subject, target_choices):
                return False
        return True

    def do_it(self, state, subject, choices):
        """Puts the `source` card on the stack, including making any
        choices necessary to do that. Returns (GameState,Cardboard)
        copies but does not mutate. Note that super_stack is NOT
        guaranteed to be clear!"""
        # check to make sure the execution is legal
        if not self.can_be_done(state, subject, choices):
            return []
        # 601.2b: choose costs (additional costs, choose X, choose hybrid).
        # this has already been done by choices.
        # 601.2c: choose targets and modes -- already done by choices.
        # 601.2f: determine total cost -- part of payment for me, I think?
        # 601.2g: activate mana abilities -- I don't actually permit this.
        # 601.2h: pay costs
        copy_of_game, things = state.copy_and_track([subject] + choices)
        copy_of_spell = things[0]
        copy_of_choices = things[1:]
        # The casting will chew through all the payment choices, leaving only
        # the target choices in the resulting tuples. Then those tuples are
        # returned as a list of (GameState, Cardboard, choices) tuples.
        list_of_tuples = subject.cost.pay(copy_of_game, copy_of_spell,
                                          copy_of_choices)
        # Build a StackCardboard and add it to the stack
        for g1, s1, targets in list_of_tuples:
            # Special exception for lands, which go directly to play
            if subject.has_type(Land):
                mover = MoveToZone(ZONE.FIELD)
                mover.do_it(g1, s1, targets)  # mutate in-place
            else:
                g1.stack.append(StackCardboard(s1, targets))  # mutate in-place
        # 601.2i: ability has now "been activated".  Any abilities which
        # trigger from some aspect of paying the costs have already
        # been added to the superstack during ability.cost.pay. Now add
        # any trigger that trigger off of this casting itself.
        final_results = []
        for g2, s2, targets2 in list_of_tuples:
            final_results += super().do_it(g2, s2, targets2)
        return final_results

    def choose_choices(self, state: GameState, subject: Cardboard):
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payment_choices = subject.cost.choose_choices(state, subject)
        # 601.2c: choose targets and modes
        if subject.effect is not None:
            target_choices = subject.effect.choose_choices(state, subject)
            # combine all combinations of these
            new_choices = []
            for sub_pay in payment_choices:
                for sub_target in target_choices:
                    # concatenate sub-lists
                    new_choices.append(sub_pay + sub_target)
            return new_choices
        else:
            return payment_choices

    def mutates(self):
        return False

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


# ----------


# ----------
