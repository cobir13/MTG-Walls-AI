# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING, Tuple
import random

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard
    from Abilities import ActivatedAbility

import ZONE
import MatchCardPatterns as Match
import Getters as Get
import ManaHandler
import Stack


class WinTheGameError(Exception):
    pass


class LoseTheGameError(Exception):
    pass


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

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
        # this parent function doesn't DO anything itself. That is for children
        # to overwrite, and then to call this parent function. The parent
        # function handles two things:
        #    1) Adding to the super_stack any triggers triggered by the
        #       execution of tthis Verb
        #    2) "Using up" any choices that this Verb needed, so that the list
        #       of choices returned (for later use) is appropriately shortened.
        # add a note to the GameState's history that this Verb has occurred,
        # assuming that the GameState is tracking such things.
        self.add_self_to_state_history(state, subject, choices)
        # `trigger_source` is source of the trigger. Not to be confused
        # with `source`, which is the source of the Verb which is
        # potentially CAUSING the trigger.
        for trigger_source in state.field + state.grave + state.hand:
            for ability in trigger_source.rules_text.trig_verb:
                if ability.is_triggered(self, state, trigger_source, subject):
                    effect = Stack.StackAbility(ability, trigger_source,
                                                [subject])
                    state.super_stack.append(effect)
        # return the expected triplet of GameState, source Cardboard,
        # and list of choices. But strip out any choices that this
        # Verb already 'used up'.
        return [(state, subject, choices[len(self.getter_list):])]

    def __str__(self):
        text = type(self).__name__
        if len(self.sub_verbs) > 0 or len(self.getter_list) > 0:
            text += "("
            if len(self.sub_verbs) > 0:
                text += ",".join([v.__str__() for v in self.sub_verbs])
            if len(self.sub_verbs) > 0 and len(self.getter_list) > 0:
                text += "|"
            if len(self.getter_list) > 0:
                text += ",".join([g.__str__() for g in self.getter_list])
            text += ")"
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
        # If all getters have single output, then this Verb doesn't need
        # to return multiple GameStates and is allowed to just mutate
        # its input. Note: all([])==True
        getters_can_mutate = all([g.single_output for g in self.getter_list])
        subs_can_mutate = any([v.mutates for v in self.sub_verbs])
        return getters_can_mutate or subs_can_mutate

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

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        """If the GameState is tracking history, adds a note
        to that history describing this Verb. Mutates state,
        technically, in that note is added rather than added
        to a copy."""
        if state.is_tracking_history:
            record = "\n%s %s" % (str(self), subject.name)
            # if len(choices) > 0:
            #     record += " {%s}" % ", ".join([str(c) for c in choices])
            state.events_since_previous += record


# ----------

class ManyVerbs(Verb):
    def __init__(self, list_of_verbs: List[Verb]):
        super().__init__()
        assert (len(list_of_verbs) > 1)
        self.sub_verbs = list_of_verbs
        self.getter_list = []

    def __str__(self):
        return " & ".join([v.__str__() for v in self.sub_verbs])

    def do_it(self, state: GameState, subject: Cardboard,
              choices: list) -> List[Tuple[GameState, Cardboard, list]]:
        tuple_list = [(state, subject, choices)]
        for v in self.sub_verbs:
            # if verb allowed to mutate, mutate gamestates in place
            if v.mutates:
                for g, c, ch in tuple_list:
                    v.do_it(g, c, ch)
            # if verb returns new list, use that to overwrite tuple_list
            else:
                new_tuple_list = []
                for g, c, ch in tuple_list:
                    new_tuple_list += v.do_it(g, c, ch)
                tuple_list = new_tuple_list
        # The do_it functions of each Verb will handle triggers for those
        # sub-verbs. no need to call super().do_it because nothing triggers.
        # Similarly, ManyVerbs itself has no getters, so there is no need to
        # reduce the length of the choice_list on behalf of the ManyVerb
        # itself, and each Verb's do_it will have reduced the list according
        # to that particular Verb's getter_list.  So omit the call to super
        return tuple_list


# ----------
class ChooseAVerb(Verb):
    def __init__(self, list_of_verbs: List[Verb]):
        super().__init__()
        assert (len(list_of_verbs) > 1)
        self.sub_verbs = list_of_verbs
        self.getter_list = [Get.Chooser(Get.Const(self.sub_verbs), 1, False)]

    def __str__(self):
        return " or ".join([v.__str__() for v in self.sub_verbs])

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        """first element of choices is the choice of which verb to use"""
        chosen_verb: Verb = choices[0]
        return chosen_verb.can_be_done(state, subject, choices[1:])

    def do_it(self, state: GameState, subject: Cardboard,
              choices: list) -> List[Tuple[GameState, Cardboard, list]]:
        """first element of choices is the choice of which verb to use"""
        chosen_verb: Verb = choices[0]
        return chosen_verb.do_it(state, subject, choices[1:])

    @property
    def mutates(self):
        return any([v.mutates for v in self.sub_verbs])

    def choose_choices(self, state: GameState, subject: Cardboard):
        # choices are: the verb I choose, together with IT'S choices
        possible_verbs = self.getter_list[0].get(state, subject)
        final = []
        for (verb) in possible_verbs:
            choices_for_this_verb = verb.choose_choices(state, subject)
            final += [[verb] + sublist for sublist in choices_for_this_verb]
        return final


# ----------
class VerbManyTimes(Verb):
    def __init__(self, verb: Verb, getter: Get.Integer | int):
        super().__init__()
        self.sub_verbs = [verb]
        if isinstance(getter, int):
            getter = Get.ConstInteger(getter)
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
        return [[sub[0]] + (sub[1:] * sub[0]) for sub in raw_choices]

    def __str__(self):
        return str(self.sub_verbs[0]) + "(" + str(self.getter_list[0]) + ")"


# ----------
class VerbOnSplitList(Verb):
    def __init__(self, act_on_chosen: VerbOnSubjectCard,
                 act_on_non_chosen: VerbOnSubjectCard | None,
                 chooser: Get.Chooser):
        super().__init__()
        assert act_on_non_chosen.num_inputs == 0
        assert act_on_chosen.num_inputs == 0
        self.sub_verbs = [act_on_chosen, act_on_non_chosen]
        # chooser isn't in getter_list because ALL the options are being used
        # up one way or another, so it's not working like a normal getter.
        self.chooser = chooser

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        # Note that NO CHOICES ARE BEING PASSED TO THE SUB_VERBS. This is
        # because they are assumed to take no inputs and act only on their
        # subjects.
        all_options = self.chooser.getter.get(state, subject)
        act_on_chosen, act_on_non_chosen = self.sub_verbs
        for card in all_options:
            if card in choices:
                if not act_on_chosen.can_be_done(state, card, []):
                    return False
            else:
                if not act_on_non_chosen.can_be_done(state, card, []):
                    return False
        return True

    def do_it(self, state: GameState, subject: Cardboard,
              choices: list) -> List[Tuple[GameState, Cardboard, list]]:
        """
        This function will appy the act_on_chosen Verb to each card in
        choices, and will apply the act_on_non_chosen to each other card
        in the list of options (which is found from the getter within
        the chooser, to find the list the chooser is choosing from).
        """
        all_options = self.chooser.getter.get(state, subject)
        act_on_chosen, act_on_non_chosen = self.sub_verbs
        # put all_options and also choices into tuple_list to track them
        tuple_list = [(state, subject, all_options + choices)]
        for ii in range(len(all_options)):
            new_tuples = []
            for g, s, concat in tuple_list:
                chosen_copied = concat[len(all_options):]
                option = concat[ii]
                # check if this option has been chosen or not
                if option in chosen_copied:
                    new_tuples += act_on_chosen.do_it(g, option, concat)
                    # Note: act_on_chosen has num_inputs == 0 so it will
                    # return (copies of) the contatenated list, without
                    # eating through any. Same with act_on_non_chosen below.
                else:
                    new_tuples += act_on_non_chosen.do_it(g, option, concat)
            tuple_list = new_tuples  # overwrite
        return [(g, s, []) for g, s, _ in tuple_list]

    def __str__(self):
        act_on_chosen, act_on_non_chosen = self.sub_verbs
        act_yes = str(act_on_chosen)
        comp = "<=" if self.chooser.can_be_less else ""
        num = self.chooser.num_to_choose
        get_str = str(self.chooser.getter)
        act_no = str(act_on_non_chosen)
        s = "%s on %s%i of %s else %s" % (act_yes, comp, num, get_str, act_no)
        return s

    def choose_choices(self, state: GameState, subject: Cardboard):
        return self.chooser.get(state, subject)


# ----------

class VerbAtomic(Verb):
    pass


# ----------

class VerbOnSubjectCard(Verb):
    """acts on the source passed into the `do_it` method"""
    pass


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class NullVerb(Verb):
    """This Verb does literally nothing, ever."""

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject: Cardboard | None, choices):
        # add triggers to super_stack, reduce length of choices list
        """Mutates. Reorder deck randomly."""
        return [(state, subject, choices)]

    @property
    def mutates(self):
        return False

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        return


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

    def __str__(self):
        return "PayMana{%s}" % str(self.mana_cost)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            text = "\nPay %s" % str(self.mana_cost)
            state.events_since_previous += text


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

    def __str__(self):
        return "AddMana{%s}" % str(self.mana_pool_to_add)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            text = "\nAdd %s" % str(self.mana_pool_to_add)
            state.events_since_previous += text


# =============================================================================

class LoseOwnLife(VerbAtomic):
    def __init__(self, damage_getter: Get.Integer | int):
        super().__init__()
        if isinstance(damage_getter, int):
            damage_getter = Get.ConstInteger(damage_getter)
        self.getter_list = [damage_getter]

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject, choices):
        damage = choices[0]
        state.life -= damage
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            text = "\nLose %i life" % self.getter_list[0].get(state, subject)
            state.events_since_previous += text


# ----------

class DealDamageToOpponent(VerbAtomic):
    def __init__(self, damage_getter: Get.Integer | int):
        super().__init__()
        if isinstance(damage_getter, int):
            damage_getter = Get.ConstInteger(damage_getter)
        self.getter_list = [damage_getter]

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject, choices):
        damage = choices[0]
        state.opponent_life -= damage
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            text = "\nDeal %i damage" % self.getter_list[0].get(state, subject)
            state.events_since_previous += text


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
    """Adds the given counter string to the subject card"""

    def __init__(self, counter_text: str):
        super().__init__()
        self.counter_text = counter_text

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return subject.zone == ZONE.FIELD

    def do_it(self, state, subject, choices):
        subject.add_counter(self.counter_text)
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            text = "\nPut %s counter on %s" % (self.counter_text, subject.name)
            state.events_since_previous += text


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

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        return  # doesn't mark itself as having done anything


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

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        return  # doesn't mark itself as having done anything


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
        return super().do_it(state, subject, choices)

    @property
    def mutates(self):
        return True

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            state.events_since_previous += "\nShuffle"


# ----------

class MoveToZone(VerbOnSubjectCard):
    """Moves the subject card to the given zone
    NOTE: cannot actually remove the subject card from the
    stack (because it's wrapped in a StackObject).
    NOTE: cannot actually add the subject card to the stack
    (because it's wrapped in a StackObject) or to the deck
    (because it's unclear if it should be added to the top
    or to the bottom).
    In both of these cases, the function does as much of the
    move as it can (sets Cardboard.zone, removes even if it
    can't add, etc.) and hopes that the calling function will
    know to do the rest.
    """

    def __init__(self, destination_zone):
        super().__init__()
        self.destination = destination_zone
        self.origin = None  # to let triggers check where card moved from

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        if subject.zone in [ZONE.DECK, ZONE.DECK_BOTTOM, ZONE.HAND,
                            ZONE.FIELD, ZONE.GRAVE]:
            return subject in state.get_zone(subject.zone)

    def do_it(self, state, subject, choices=()):
        # NOTE: Cardboard can't live on the stack. only StackObjects do. So
        # reassign card zone and remove/add to zones as appropriate, but never
        # directly add or remove from the stack. StackCardboard does the rest.
        self.origin = subject.zone  # so trigger knows where card moved from
        # remove from origin
        if self.origin in [ZONE.DECK, ZONE.DECK_BOTTOM, ZONE.HAND,
                           ZONE.FIELD, ZONE.GRAVE]:
            state.get_zone(self.origin).remove(subject)
        # add to destination
        subject.zone = self.destination
        if self.destination in [ZONE.HAND, ZONE.FIELD, ZONE.GRAVE]:
            # these three zones must remain sorted at all times
            zone_list = state.get_zone(self.destination)
            zone_list.append(subject)  # can add to any index b/c about to sort
            state.re_sort(self.destination)
        elif self.destination == ZONE.DECK:
            state.deck.insert(0, subject)  # add to top (index 0) of deck
        elif self.destination == ZONE.DECK_BOTTOM:
            state.deck.append(subject)  # add to bottom (index -1) of deck
        # any time you change zones, reset the cardboard parameters
        subject.reset_to_default_cardboard()
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def __str__(self):
        if self.destination == ZONE.DECK:
            text = "Deck"
        elif self.destination == ZONE.DECK_BOTTOM:
            text = "BottomOfDeck"
        elif self.destination == ZONE.HAND:
            text = "Hand"
        elif self.destination == ZONE.FIELD:
            text = "Field"
        elif self.destination == ZONE.GRAVE:
            text = "Grave"
        elif self.destination == ZONE.STACK:
            text = "Stack"
        else:
            raise IndexError
        return "MoveTo" + text


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

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        return


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class PlayVerb(VerbAtomic):
    pass


# ----------
class PlayAbility(PlayVerb):
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
        return (self.ability.cost.can_be_done(state, subject, pay_choices)
                and self.ability.effect.can_be_done(state, subject, targets))

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
        for g1, s1, targets in list_of_tuples:
            g1.stack.append(Stack.StackAbility(self.ability, s1, targets))
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

    def __str__(self):
        return "Activate " + str(self.ability)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            record = "\n*** Activate %s ***" % self.ability.name
            # if len(choices) > 0:
            #     record += " {%s}" % ", ".join([str(c) for c in choices])
            state.events_since_previous += record


# ----------
class PlayManaAbility(PlayAbility):
    def do_it(self, state: GameState, subject: Cardboard, choices: list):
        """Activate the ability. The source of the ability is
        assumed to be the `subject` Cardboard. `choices` describe
        the choices for paying for the ability, followed by choices
        for using the ability. Note that super_stack is NOT
        guaranteed to be clear!
        """
        # Near-copy of PlayCardboard.do_it. For Cobi's sanity, many of
        # the comments there have been deleted here.
        if not self.can_be_done(state, subject, choices):
            return []
        # 601.2h: pay costs
        copy_of_game, things = state.copy_and_track([subject] + choices)
        copy_of_spell = things[0]
        copy_of_choices = things[1:]
        # The casting will chew through all the payment choices
        list_of_tuples = self.ability.cost.do_it(copy_of_game, copy_of_spell,
                                                 copy_of_choices)
        # Mana Abilities which don't use the stack
        new_tuple_list = []
        for g1, s1, targets in list_of_tuples:
            new_tuple_list += self.ability.effect.do_it(g1, s1, targets)
        # 601.2i: add any trigger that trigger off of this activation itself.
        final_results = []
        for g2, s2, targets2 in new_tuple_list:
            final_results += super().do_it(g2, s2, targets2)
        return final_results


# ----------
class PlayTriggeredAbility(PlayAbility):
    pass


# ----------
class PlayActivatedAbility(PlayAbility):
    pass


# ----------
class PlayCardboard(PlayVerb):
    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        """Returns whether the `source` card can currently be
         cast. Can all its cost be paid and all targets satisfied
         for the given set of choices?"""
        cost = subject.rules_text.cost
        pay_choices = choices[:cost.num_inputs]
        return cost.can_be_done(state, subject, pay_choices)

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
        list_of_tuples = subject.cost.do_it(copy_of_game, copy_of_spell,
                                            copy_of_choices)
        # Build a StackCardboard and add it to the stack
        for g1, s1, targets in list_of_tuples:
            # MoveToZone doesn't actually PUT the Cardboard anywhere. It
            # knows the stack is for StackObjects only. Just removes from
            # hand and marks it's zone as being the stack. Mutates in-place.
            MoveToZone(ZONE.STACK).do_it(g1, s1, targets)
            g1.stack.append(Stack.StackCardboard(s1, targets))
            g1.num_spells_cast += 1
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
        # 601.2c: choose targets and modes. only relevant for effects, I think
        return subject.cost.choose_choices(state, subject)

    def mutates(self):
        return False

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            record = "\n*** Cast %s ***" % subject.name
            # if len(choices) > 0:
            #     record += " {%s}" % ", ".join([str(c) for c in choices])
            state.events_since_previous += record


# ----------
class PlayLand(PlayCardboard):
    def do_it(self, state, subject, choices):
        """Puts the `source` card on the stack, including making any
        choices necessary to do that. Returns (GameState,Cardboard)
        copies but does not mutate. Note that super_stack is NOT
        guaranteed to be clear!"""
        # Near-copy of PlayCardboard.do_it. For Cobi's sanity, many of
        # the comments there have been deleted here.
        # check to make sure the execution is legal
        if not self.can_be_done(state, subject, choices):
            return []
        # 601.2h: pay costs
        copy_of_game, things = state.copy_and_track([subject] + choices)
        copy_of_spell = things[0]
        copy_of_choices = things[1:]
        # The casting will chew through all the payment choices
        list_of_tuples = subject.cost.do_it(copy_of_game, copy_of_spell,
                                            copy_of_choices)
        for g1, s1, targets in list_of_tuples:
            # Lands go directly to play
            MoveToZone(ZONE.FIELD).do_it(g1, s1, targets)
        # 601.2i: add any trigger that trigger off of this casting itself.
        final_results = []
        for g2, s2, targets2 in list_of_tuples:
            final_results += super().do_it(g2, s2, targets2)
        return final_results


# ----------
class PlaySpell(PlayCardboard):

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        if not super().can_be_done(state, subject, choices):
            return False  # handles cost stuff
        assert subject.effect is not None
        target_choices = choices[subject.cost.num_inputs:]
        if not subject.effect.can_afford(state, subject, target_choices):
            return False
        return True

    def choose_choices(self, state: GameState, subject: Cardboard):
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payment_choices = super().choose_choices(state, subject)
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


# ----------
class PlayInstant(PlayCardboard):
    pass


# ----------
class PlaySorcery(PlayCardboard):
    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        doable = super().can_be_done(state, subject, choices)
        stack_empty = len(state.stack) == 0
        has_flash = Match.Keyword("flash").match(subject, state, subject)
        return doable and (stack_empty or has_flash)


# ----------
class PlayPermanent(PlayCardboard):
    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        doable = super().can_be_done(state, subject, choices)
        stack_empty = len(state.stack) == 0
        has_flash = Match.Keyword("flash").match(subject, state, subject)
        return doable and (stack_empty or has_flash)
