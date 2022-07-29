# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING, Tuple
import random

if TYPE_CHECKING:
    from GameState import GameState, Player
    from Cardboard import Cardboard
    from Stack import StackObject, StackTrigger, StackCardboard

    # SOURCE = Cardboard | Player
    SUBJECT = Cardboard | Player | StackObject
    CAUSE = Cardboard | Player | None
    INPUTS = List[Cardboard | Player | StackObject | int | list | None]
    RESULT = Tuple[GameState, int, Cardboard | None, INPUTS]

import ZONE
import Match as Match
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
    def __init__(self, num_inputs: int, copies: bool):
        self.num_inputs: int = num_inputs  # includes usual "subject" at [0].
        self.copies: bool = copies  # returns copies of GameStates, not mutate.

    def get_input_options(self, state: GameState, player: int,
                          source: Cardboard | None, cause: Cardboard | None
                          ) -> List[INPUTS]:
        """A list of possibly input lists that are meant to
        be plugged into can_be_done and do_it"""
        return []

    def can_be_done(self, state: GameState, player: int,
                    source: Cardboard | None, other_inputs: INPUTS) -> bool:
        """GameState; subject to apply the Verb to; any
        additional inputs needed. The specific type of
        `subject` and of the other inputs is specified
        by `input_signature`"""
        return 1 + len(other_inputs) >= self.num_inputs

    def do_it(self, state: GameState, player: int,
              source: Cardboard | None, other_inputs: INPUTS
              ) -> List[RESULT]:
        """Carries out the Verb. Adds any new triggers to the
         super_stack and shortens input argument list to "use
         up" this Verb's subject and any other inputs.
         If `copies`, returns fresh Results to avoid mutating
         the input GameState. If `copies` is False, then just
         mutates it.
         """
        self.add_self_to_state_history(state, player, source, other_inputs)
        # `trigger_source` is source of the trigger. Not to be confused
        # with `subject`, which is the cause of the Verb which is
        # potentially CAUSING the trigger.
        for trigger_source in state.get_all_public_cards():
            for ability in trigger_source.rules_text.trig_verb:
                # add any abilities that trigger to the super_stack
                ability.add_any_to_super(self, state, trigger_source, source)
        return [(state, player, source, other_inputs[self.num_inputs:])]

    def is_type(self, verb_type: type) -> bool:
        return isinstance(self, verb_type)

    def __add__(self, other):
        return MultiVerb([self, other])

    # def __or__

    def __str__(self):
        return type(self).__name__

    def add_self_to_state_history(self, state: GameState, player,
                                  source: Cardboard | None,
                                  other_inputs: INPUTS) -> None:
        """If the GameState is tracking history, adds a note
        to that history describing this Verb. Mutates state,
        technically, in that note is added rather than added
        to a copy."""
        if state.is_tracking_history:
            record = "\n%s %s" % (str(self), source.name)
            state.events_since_previous += record

    def on(self, subject_getter: Get.Getter) -> ApplyToCard:
        return ApplyToCard(subject_getter, self)


class MultiVerb(Verb):

    def __init__(self, list_of_verbs: List[Verb]):
        self.sub_verbs = list_of_verbs
        # unpack any nested MultiVerbs and combine them into this one.
        ii = 0
        while ii < len(self.sub_verbs):
            if isinstance(self.sub_verbs[ii], MultiVerb):
                before = self.sub_verbs[:ii]
                middle = self.sub_verbs[ii].sub_verbs
                after = self.sub_verbs[ii + 1:]
                self.sub_verbs = before + middle + after
            else:
                ii += 1
        # figure out number of inputs, etc, based on sub_verbs.
        super().__init__(sum([v.num_inputs for v in self.sub_verbs]),
                         any([v.copies for v in self.sub_verbs]))

    def get_input_options(self, state, player, source, cause
                          ) -> List[INPUTS]:
        # list of sublists. start with 1 sublist, which is empty
        choices = [[]]
        # get any choices from any sub-verbs
        for v in self.sub_verbs:
            if v.num_inputs >= 0:
                verb_choices = v.get_input_options(state, player,
                                                   source, cause)
                new_list = []
                for sublist in choices:
                    new_list += [sublist + ch for ch in verb_choices]
                choices = new_list
        return choices

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        if not super().can_be_done(state, player, source, other_inputs):
            return False
        i_start = 0
        for v in self.sub_verbs:
            i_end = i_start + v.num_inputs
            if not v.can_be_done(state, player, source,
                                 other_inputs[i_start:i_end]):
                # if any verb cannot be done, the whole list cannot be done
                return False
            i_start = i_end  # increment to use the next choices for next verb
        return True  # if reached here, all verbs are doable!

    def do_it(self, state, player, source, other_inputs) -> List[RESULT]:
        tuple_list = [(state, source)]
        for v in self.sub_verbs:
            new_tuple_list = []
            for st, pl, srce, ins in tuple_list:
                # uses up inputs as it goes, dumps shorter inputs into list. 
                new_tuple_list += v.do_it(st, pl, srce, ins)
            tuple_list = new_tuple_list
        # The do_it functions of each Verb will handle triggers for those
        # sub-verbs. The Multi-Verb itself can't cause any triggers.
        return tuple_list

    def is_type(self, verb_type: type):
        return any([v.is_type(verb_type) for v in self.sub_verbs])

    def __str__(self):
        return " & ".join([v.__str__() for v in self.sub_verbs])


class AffectController(Verb):
    def __init__(self):
        """Subject is the player of the Verb"""
        super().__init__(0, True)

    # def get_input_options(self, state: GameState, player: Player,
    #                       source: Cardboard | None, cause: Cardboard | None
    #                       ) -> List[Tuple[INPUTS]]:
    #     """Subject is the player of the Verb"""
    #     return [(player,)]


class AffectSourceCard(Verb):
    def __init__(self):
        """Subject is the source card of the Verb"""
        super().__init__(0, True)

    # def get_input_options(self, state: GameState, player: Player,
    #                       source: Cardboard | None, cause: Cardboard | None
    #                       ) -> List[Tuple[INPUTS]]:
    #     """Subject is the source of the Verb"""
    #     return [(source,)]


class ApplyToCard(Verb):
    """Chooses targets and then passes those targets along
    to the sub-verb AS THOUGH THEY WERE THE SOURCE OF THE
    SUB-VERB.
    If the chooser returns a list longer than length 1, then
    the sub-verb is applied to all the targets in turn.
    """

    def __init__(self, subject_getter: Get.Getter, verb: Verb):
        super().__init__(verb.num_inputs,
                         not subject_getter.single_output or verb.copies)
        self.getter = subject_getter
        self.verb = verb
        assert verb.num_inputs == 0
        self.allowed_to_fail = (hasattr(self.getter, "can_be_less")
                                and self.getter.can_be_less)

    def get_input_options(self, state, player, source, cause
                          ) -> List[INPUTS]:
        """
        Returns a list of sub-lists. Each sub-list represents
        one possible way to choose modes and/or targets for this
        Verb.  The sublists are intended to be passed into calls
        to `can_be_done` and `do_it` as the `choices` argument.
        The `source` is the thing which is performing the verb,
        and the `cause` is the reason why the verb is being
        performed (often identical to the source).
        """
        # list of sublists. start with 1 sublist, which is empty
        choices = [[x] for x in self.getter.get(state, player, source)]
        assert self.verb.num_inputs == 0
        # verb_choices = self.verb.get_input_options(state, player,
        #                                            source, cause)
        # new_list = []
        # for sublist in choices:
        #     new_list += [sublist + ch for ch in verb_choices]
        # choices = new_list
        return choices

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        """
        The first element of `other_inputs` is a list of length 0
        or 1 containing the single target of the given Verb.
        If empty, the chooser "failed to find" a target. The
        Verb will not be applied to anything. Still may be ok.
        """
        if not super().can_be_done(state, player, source, other_inputs):
            return False  # confirms other_inputs is long enough
        targets = other_inputs[0]
        if len(targets) == 0:
            # chooser failed to find a target. ok only if "allowed" to fail.
            return self.allowed_to_fail
        return any([self.verb.can_be_done(state, player, t, other_inputs[1:])
                    for t in targets])

    def do_it(self, state: GameState, player, source, other_inputs):
        """Expects the first element of `other_inputs` to be a
        list of subjects that the Verb should be applied to.
        The first element of `other_inputs` is also allowed to
        be empty. This is the "fail to find" mode. The Verb
        will not be applied to anything, but this is ok."""
        targets = other_inputs[0]
        if len(targets) == 0:
            # Failed to find target. If got this far, presumably failing is ok.
            # So do nothing and trigger nothing. Do snip the inputs though.
            if not self.copies:
                state2, things = state.copy_and_track(
                    [source] + other_inputs[1:])
                source2 = things[0]
                inputs2 = things[1:]
                return [(state2, player, source2, inputs2)]
            else:
                return [(state, player, source, other_inputs[1:])]
        else:
            if self.copies:
                # make some extra choices to chew through. Should look like:
                # [target1, ... targetN, otherX, ... otherZ, source].
                concat_choices = targets + other_inputs[1:] + [source]
                # concat_choices = []
                # for target in targets:
                #     concat_choices.append(target)
                #     concat_choices += other_inputs[1:self.verb.num_inputs+1]
                # concat_choices += [source]
                # concat_choices += other_inputs[self.verb.num_inputs + 1:]
                # copy gamestate (and these choices) and then start do_it loop
                state2, concat2 = state.copy_and_track(concat_choices)
                # standard "state, player, source, choices" format
                tuple_list = [(state2, player, concat2[0], concat2)]
                for _ in range(len(targets)):
                    new_list = []
                    for g, plr, _, ins in tuple_list:
                        new_list += self.verb.do_it(g, plr, ins[0], ins[1:])
                    tuple_list = new_list
                # at this point we've done all the work, but still need to
                # extract the source to return!
                return [(g, plr, ins[-1], ins[:-1])
                        for g, plr, trg, ins in tuple_list]
            else:
                for target in targets:
                    self.verb.do_it(state, player, target, other_inputs[1:])
                return [(state, player, source, other_inputs[1:])]

    def is_type(self, verb_type: type):
        return self.verb.is_type(verb_type)

    def __str__(self):
        return "%s(%s)" % (str(self.verb), str(self.getter))


#
# 
class Modal(Verb):
    """Choose between various Verbs. All options should require
    the same number of inputs. Mode is chosen at cast-time,
    not on resolution."""

    def __init__(self, list_of_verbs: List[Verb], num_to_choose: int = 1):
        super().__init__(1 + num_to_choose * list_of_verbs[0].num_inputs,
                         any([v.copies for v in list_of_verbs]))
        assert (len(list_of_verbs) > 1)
        assert all([v.num_inputs == list_of_verbs[0].num_inputs
                    for v in list_of_verbs])
        self.sub_verbs = list_of_verbs
        options = [(ii, str(v)) for ii, v in enumerate(self.sub_verbs)]
        self.chooser = Get.Chooser(Get.Const(options), num_to_choose, False)

    def get_input_options(self, state, player, source, cause
                          ) -> List[INPUTS]:
        # choices are: the verbs I choose, together with THEIR choices
        modes: List[Tuple[Tuple[int, str]]] = self.chooser.get(state, player,
                                                               source)
        choices: List[INPUTS] = []
        for set_of_verbs in modes:
            verb_indices = [index for index, name in set_of_verbs]
            multi = MultiVerb([self.sub_verbs[ii] for ii in verb_indices])
            for sub_choice in multi.get_input_options(state, player,
                                                      source, cause):
                # noinspection PyTypeChecker
                choices.append([verb_indices] + sub_choice)
        return choices

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        """first element of choices is the choice of which verbs to use"""
        multi = MultiVerb([self.sub_verbs[ii] for ii in other_inputs[0]])
        return multi.can_be_done(state, player, source, other_inputs)

    def do_it(self, state: GameState, player, source, other_inputs):
        """first element of choices is the choice of which verb to use"""
        multi = MultiVerb([self.sub_verbs[ii] for ii in other_inputs[0]])
        return multi.do_it(state, player, source, other_inputs)

    def __str__(self):
        return " or ".join([v.__str__() for v in self.sub_verbs])

    def is_type(self, verb_type: type) -> bool:
        return all([v.is_type(verb_type) for v in self.sub_verbs])


class Defer(Verb):
    """
    Defers any cast-time choices of the given verb to instead
    be chosen only on resolution.
    """

    def __init__(self, verb: Verb):
        super().__init__(1, copies=True)
        self.verb = verb

    def get_input_options(self, state, player, source, cause
                          ) -> List[INPUTS]:
        """Saves the cause so that the sub-verb can run
        its own get_input_options function later on."""
        return [[cause]]

    def do_it(self, state: GameState, player, source, other_inputs):
        cause = other_inputs[0]
        results = []
        if self.verb.copies:
            choices = self.verb.get_input_options(state, player,
                                                  source, cause)
            for choice in choices:
                results += self.verb.do_it(state, player, source, choice)
        else:
            choices = self.verb.get_input_options(state, player,
                                                  source, cause)
            for choice in choices:
                state2, things = state.copy_and_track([source] + choice)
                source2 = things[0]
                ch2 = things[1:]
                results += self.verb.do_it(state2, player, source2, ch2)
        return results

    def is_type(self, verb_type: type):
        return self.verb.is_type(verb_type)

    def __str__(self):
        return str(self.verb)


# ----------


# ----------
# class VerbManyTimes(Verb):
#     def __init__(self, verb: Verb, getter: Get.Integer | int):
#         super().__init__()
#         self.sub_verbs = [verb]
#         if isinstance(getter, int):
#             getter = Get.ConstInteger(getter)
#         self.getter_list = [getter]
#
#     def can_be_done(self, state: GameState, subject: Cardboard,
#                     choices: list) -> bool:
#         return (len(choices) >= 1
#                 and self.sub_verbs[0].can_be_done(state, source,
#                                                   choices[1:]))
#
#     def do_it(self, state: GameState, subject: Cardboard, choices):
#         """mutates!"""
#         num_to_repeat = choices[0]
#         if num_to_repeat == 0:
#             game2, things = state.copy_and_track([subject] + choices[1:])
#             return [(game2, things[0], things[1:])]
#         elif num_to_repeat == 1:
#             return self.sub_verbs[0].do_it(state, source, choices[1:])
#         else:
#             # do a MultiVerb containing this verb repeated a bunch of times
#             multi_verb = MultiVerb([self.sub_verbs[0]] * num_to_repeat)
#             return multi_verb.do_it(state, source, choices[1:])
#
#     def get_input_options(self, state: GameState, source: Cardboard = None,
#                        cause=None):
#         raw_choices = super().get_input_options(state, source, cause)
#         # In each sublist in raw_choices, the first is the number of times to
#         # repeat the Verb and the rest is one copy of the choices for that
#         # Verb. I need to duplicate those other choices according to the
#         # number of times we'll be repeating it.
#         return [[sub[0]] + (sub[1:] * sub[0]) for sub in raw_choices]
#
#     def __str__(self):
#         return str(self.sub_verbs[0]) + "(" + str(self.getter_list[0]) + ")"


# # ----------
# class VerbOnSplitList(Verb):
#     def __init__(self, act_on_chosen: VerbOnSubjectCard,
#                  act_on_non_chosen: VerbOnSubjectCard | None,
#                  chooser: Get.Chooser):
#         super().__init__()
#         assert act_on_non_chosen.num_inputs == 0
#         assert act_on_chosen.num_inputs == 0
#         self.sub_verbs = [act_on_chosen, act_on_non_chosen]
#         # chooser isn't in getter_list because ALL the options are being used
#         # up one way or another, so it's not working like a normal getter.
#         self.chooser = chooser
#
#     def can_be_done(self, state: GameState, subject: Cardboard,
#                     choices: list) -> bool:
#         # Note that NO INPUTS ARE BEING PASSED TO THE SUB_VERBS. This is
#         # because they are assumed to take no inputs and act only on their
#         # subjects.
#         all_options = self.chooser.getter.get(state, subject)
#         act_on_chosen, act_on_non_chosen = self.sub_verbs
#         for card in all_options:
#             if card in choices:
#                 if not act_on_chosen.can_be_done(state, card, []):
#                     return False
#             else:
#                 if not act_on_non_chosen.can_be_done(state, card, []):
#                     return False
#         return True
#
#     def do_it(self, state: GameState, subject: Cardboard,
#               choices: list) -> List[Tuple[GameState, Cardboard, list]]:
#         """
#         This function will appy the act_on_chosen Verb to each card in
#         choices, and will apply the act_on_non_chosen to each other card
#         in the list of options (which is found from the getter within
#         the chooser, to find the list the chooser is choosing from).
#         """
#         all_options = self.chooser.getter.get(state, subject)
#         act_on_chosen, act_on_non_chosen = self.sub_verbs
#         # put all_options and also choices into tuple_list to track them
#         tuple_list = [(state, source, all_options + choices)]
#         for ii in range(len(all_options)):
#             new_tuples = []
#             for g, s, concat in tuple_list:
#                 chosen_copied = concat[len(all_options):]
#                 option = concat[ii]
#                 # check if this option has been chosen or not
#                 if option in chosen_copied:
#                     new_tuples += act_on_chosen.do_it(g, option, concat)
#                     # Note: act_on_chosen has num_inputs == 0 so it will
#                     # return (copies of) the contatenated list, without
#                     # eating through any. Same with act_on_non_chosen below.
#                 else:
#                     new_tuples += act_on_non_chosen.do_it(g, option, concat)
#             tuple_list = new_tuples  # overwrite
#         return [(g, s, []) for g, s, _ in tuple_list]
#
#     def __str__(self):
#         act_on_chosen, act_on_non_chosen = self.sub_verbs
#         act_yes = str(act_on_chosen)
#         comp = "<=" if self.chooser.can_be_less else ""
#         num = self.chooser.num_to_choose
#         get_str = str(self.chooser.getter)
#         act_no = str(act_on_non_chosen)
#         s = "%s on %s%i of %s else %s" % (act_yes, comp, num, get_str,act_no)
#         return s
#
#     def get_input_options(self, state: GameState, source: Cardboard = None,
#                        cause=None):
#         list_of_chosen_tuples = self.chooser.get(state, source)
#         # I need to return a list of lists. Each sublist has one element: a
#         # tuple of the chosen cards. Right now I have a list of tuples, not
#         # a list of lists of tuples.
#         return [[tup] for tup in list_of_chosen_tuples]


# # noinspection PyMissingConstructor
# class VerbOnCause(ApplyToCard):
#     """Applies the given VerbOnSubjectCard to the `cause`
#     argument of get_input_options. Which is to say, ensures
#     that the `cause` argument is returned as the first
#     element of the choices list, and then applies the
#     verb's do_it to that first element.
#     """
# 
#     def __init__(self, verb: Verb):
#         self.verb = verb
# 
#     def get_input_options(self, state: GameState, source: SOURCE,
#                           cause: CAUSE) -> List[INPUTS]:
#         return [[[cause]]]


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class NullVerb(Verb):
    """This Verb does literally nothing, ever."""

    def __init__(self):
        super().__init__(0, True)

    def get_input_options(self, state, player, source, cause):
        return [()]

    def do_it(self, state: GameState, player, source, other_inputs):
        return [(state, player, source, other_inputs)]

    def add_self_to_state_history(self, state, player, source,
                                  other_inputs):
        return

    def __str__(self):
        return ""


class PayMana(AffectController):
    """deducts the given amount of mana from the Player's
    mana pool."""

    def __init__(self, mana_string: Get.String | str):
        super().__init__()
        if isinstance(mana_string, str):
            mana_string = Get.ConstString(mana_string)
        self.string_getter: Get.String = mana_string

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        if not super().can_be_done(state, player, source, other_inputs):
            return False
        mana_str = self.string_getter.get(state, player, source)
        pool = state.player_list[player].pool
        return pool.can_afford_mana_cost(ManaHandler.ManaCost(mana_str))

    def do_it(self, state, player, source, other_inputs):
        mana_str = self.string_getter.get(state, player, source)
        pool = state.player_list[player].pool
        pool.pay_mana_cost(ManaHandler.ManaCost(mana_str))
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)

    def __str__(self):
        return "PayMana{%s}" % str(self.string_getter)

    def add_self_to_state_history(self, state: GameState, player,
                                  source, other_inputs: Player):
        if state.is_tracking_history:
            cost = ManaHandler.ManaCost(
                self.string_getter.get(state, player, source))
            text = "\nPay %s" % str(cost)
            state.events_since_previous += text


class AddMana(AffectController):
    """adds the given amount of mana to the GameState's mana pool"""

    def __init__(self, mana_string: Get.String | str):
        super().__init__()
        if isinstance(mana_string, str):
            mana_string = Get.ConstString(mana_string)
        self.string_getter: Get.String = mana_string

    def do_it(self, state, player, source, other_inputs):
        mana_str = self.string_getter.get(state, player, source)
        pool = state.player_list[player].pool
        pool.add_mana(ManaHandler.ManaPool(mana_str))
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        if state.is_tracking_history:
            pool = ManaHandler.ManaPool(
                self.string_getter.get(state, player, source))
            text = "\nAdd %s" % str(pool)
            state.events_since_previous += text


class LoseLife(AffectController):
    def __init__(self, damage_getter: Get.Integer | int):
        """The subject player loses the given amount of life"""
        super().__init__()
        if isinstance(damage_getter, int):
            damage_getter = Get.ConstInteger(damage_getter)
        self.damage_getter: Get.Integer = damage_getter

    def do_it(self, state, player, source, other_inputs):
        pl = state.player_list[player]
        pl.life -= self.damage_getter.get(state, player, source)
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        if state.is_tracking_history:
            text = "\nLose %i life" % self.damage_getter.get(state, player,
                                                             source)
            state.events_since_previous += text


class Tap(AffectSourceCard):
    """taps `source` if it was not already tapped."""

    def can_be_done(self, state, player, source, other_inputs):
        return (super().can_be_done(state, player, source, other_inputs)
                and source.zone == ZONE.FIELD and not source.tapped)

    def do_it(self, state: GameState, player, source, other_inputs):
        source.tapped = True
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)


class Untap(AffectSourceCard):
    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, player, source,
                    other_inputs) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and source.tapped and source.zone == ZONE.FIELD)

    def do_it(self, state: GameState, player, source, other_inputs):
        source.tapped = False
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)


class AddCounter(AffectSourceCard):
    """Adds the given counter string to the subject card"""

    def __init__(self, counter_text: str):
        super().__init__()
        self.counter_text = counter_text

    def can_be_done(self, state: GameState, player, source,
                    other_inputs) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and source.zone == ZONE.FIELD)

    def do_it(self, state, player, source, other_inputs):
        source.add_counter(self.counter_text)
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)

    def add_self_to_state_history(self, state: GameState, player, source,
                                  other_inputs):
        if state.is_tracking_history:
            text = "\nPut %s counter on %s" % (self.counter_text, source.name)
            state.events_since_previous += text


class ActivateOncePerTurn(AffectSourceCard):
    """Marks the given `subject` as only able to activate this ability once
    per turn"""

    def __init__(self, ability_name: str):
        super().__init__()
        self.counter_text = "@" + ability_name  # "@" is invisible counter

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and source.zone == ZONE.FIELD
                and self.counter_text not in source.counters)

    def do_it(self, state, player, source, other_inputs):
        source.add_counter(self.counter_text)
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        return  # doesn't mark itself as having done anything


class ActivateOnlyAsSorcery(Verb):
    """Checks that the stack is empty and the player has
     priority. Otherwise, can_be_done will return False."""

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and len(state.stack) == 0 and len(state.super_stack) == 0
                and state.active_player_index == player)

    def do_it(self, state, player, source, other_inputs):
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        return  # doesn't mark itself as having done anything


class Shuffle(AffectController):
    """Shuffles the deck of the player of `subject`"""

    def do_it(self, state, player, source, other_inputs):
        # add triggers to super_stack, reduce length of input list
        """Mutates. Reorder deck randomly."""
        random.shuffle(state.player_list[player].deck)
        return super().do_it(state, player, source, other_inputs)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        if state.is_tracking_history:
            state.events_since_previous += "\nShuffle"


class MoveToZone(AffectSourceCard):
    """Moves the subject card to its player's given zone.
    NOTE: cannot actually remove the subject card from the
    stack (because it's wrapped in a StackObject).
    NOTE: cannot actually add the subject card to the stack
    (because it's wrapped in a StackObject).
    In both of these cases, the function does as much of the
    move as it can (sets Cardboard.zone, removes even if it
    can't add, etc.) and hopes that the calling function will
    know to do the rest.
    """

    def __init__(self, destination_zone):
        super().__init__()
        self.destination = destination_zone
        self.origin = None  # to let triggers check where card moved from

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        if not super().can_be_done(state, player, source, other_inputs):
            return False
        elif source.zone in [ZONE.DECK, ZONE.DECK_BOTTOM, ZONE.HAND,
                             ZONE.FIELD, ZONE.GRAVE]:
            return source in state.get_zone(source.zone,
                                            source.player_index)
        else:
            return True

    def do_it(self, state, player, source, other_inputs):
        # NOTE: Cardboard can't live on the stack. only StackObjects do. So
        # reassign card zone and remove/add to zones as appropriate, but never
        # directly add or remove from the stack. StackCardboard does the rest.
        self.origin = source.zone  # so trigger knows where card moved from
        # remove from origin
        if self.origin in [ZONE.DECK, ZONE.DECK_BOTTOM, ZONE.HAND,
                           ZONE.FIELD, ZONE.GRAVE]:
            zone = state.get_zone(source.zone, source.player_index)
            zone.remove(source)
        # add to destination
        source.zone = self.destination
        if self.destination in [ZONE.HAND, ZONE.FIELD, ZONE.GRAVE]:
            # these three zones must remain sorted at all times
            zone_list = state.get_zone(self.destination,
                                       source.player_index)
            zone_list.append(source)  # can add to any index b/c about to sort
            player = state.player_list[source.player_index]
            player.re_sort(self.destination)
        elif self.destination == ZONE.DECK:
            deck = state.get_zone(ZONE.DECK, source.player_index)
            deck.insert(0, source)  # add to top (index 0) of deck
        elif self.destination == ZONE.DECK_BOTTOM:
            deck = state.get_zone(ZONE.DECK, source.player_index)
            deck.append(source)  # add to bottom (index -1) of deck
        # any time you change zones, reset the cardboard parameters
        source.reset_to_default_cardboard()
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)

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


class DrawCard(AffectController):
    """The player of `subject` draws from index 0 of deck"""

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        # Even if the deck is 0, you CAN draw. you'll just lose
        return super().can_be_done(state, player, source, other_inputs)

    def do_it(self, state, player: int, source, other_inputs: INPUTS):
        if len(state.player_list[player].deck) > 0:
            mover = MoveToZone(ZONE.HAND)
            # Adds move triggers to super_stack
            mover.do_it(state, player, state.player_list[player].deck[0], [])
            # add triggers to super_stack, reduce length of input list
            return super().do_it(state, player, source, other_inputs)
        else:
            raise LoseTheGameError


class MarkAsPlayedLand(AffectController):
    """Doesn't actually move any cards, just toggles the
    gamestate to say that the player of `subject` has
    played a land this turn"""

    def can_be_done(self, state, player, source, other_inputs: INPUTS) -> bool:
        return state.player_list[player].land_drops_left > 0

    def do_it(self, state, player, source, other_inputs: INPUTS):
        state.player_list[player].num_lands_played += 1
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        return


class Sacrifice(AffectSourceCard):
    def can_be_done(self, state, player, source: Cardboard,
                    other_inputs) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and source.zone == ZONE.FIELD)

    def do_it(self, state, player, source, other_inputs):
        MoveToZone(ZONE.GRAVE).do_it(state, player, source, [])
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)


class Destroy(AffectSourceCard):
    def can_be_done(self, state, player, source: Cardboard,
                    other_inputs) -> bool:
        # allowed to attempt even if indestructible
        return (super().can_be_done(state, player, source, other_inputs)
                and source.zone == ZONE.FIELD)

    def do_it(self, state, player, source, other_inputs):
        if not Match.Keyword("indestructible").match(source, state, source):
            MoveToZone(ZONE.GRAVE).do_it(state, player, source, [])
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, player, source, other_inputs)


# ----------

class Tutor(ApplyToCard):
    def __init__(self, zone_to_move_to, num_to_find: int,
                 pattern: Match.Pattern):
        getter = Get.Chooser(Get.ListFromZone(pattern, ZONE.DECK),
                             num_to_find, can_be_fewer=True)
        verb = MultiVerb([MoveToZone(zone_to_move_to), Shuffle()])
        super().__init__(getter, verb)


# ----------

# class TapAny(VerbOnTarget):
#
#     def __init__(self, pattern: Match.CardPattern):
#         getter = Get.Chooser(Get.ListFromZone(pattern, ZONE.FIELD), 1, False)
#         super().__init__(getter, Tap())


# ----------


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class UniversalCaster(Verb):
    def __init__(self):
        super().__init__(1, copies=True)

    def get_input_options(self, state: GameState, player: Player,
                          source: Cardboard | None, cause: Cardboard | None
                          ):
        """This should never be called. Inputs will be a single
        element, a StackObject to cast (to pay its costs and move
        it to the stack)."""
        raise Exception

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        """Can the given Cardboard or StackObject be put onto
        the stack?
        """
        if not super().can_be_done(state, player, source, other_inputs):
            return False
        obj: StackObject = other_inputs[0]
        num_payments = 0
        if source.cost is not None:
            num_payments = obj.cost.num_inputs
        pay_choices = obj.choices[1:num_payments + 1]
        target_choices = obj.choices[1 + num_payments:]
        return ((obj.cost is None
                 or obj.cost.can_afford(state, player, source, pay_choices))
                and (source.effect is None
                     or source.effect.can_be_done(state, player, source,
                                                  target_choices)))

    def do_it(self, state: GameState, player, source, other_inputs):
        """Put the StackObject onto the stack, paying any
        necessary costs. Bypass the stack if necessary."""
        # check to make sure the execution is legal
        if not self.can_be_done(state, player, source, other_inputs):
            return []
        # 601.2a: add the spell to the stack
        obj: StackObject = other_inputs[0]
        state2, [source2, obj2] = state.copy_and_track([source, obj])
        self._add_to_stack(state2, obj2)
        # 601.2b: choose costs (additional costs, choose X, choose hybrid. For
        #   me this has already been done by choices.)
        # 601.2c: choose targets and modes -- already done by choices.
        # 601.2f: determine total cost -- part of payment for me, I think?
        # 601.2g: activate mana abilities -- I don't actually permit this.
        # 601.2h: pay costs
        if source.cost is not None:
            num_payments = source.cost.num_inputs
            pay_choices = obj2.choices[:num_payments] + [obj2]
            # keep only the targets.
            obj2.choices = obj2.choices[pay_choices:]
            tuple_list: List[RESULT] = obj2.cost.pay_cost(state2, player,
                                                          source2, pay_choices)
        else:
            tuple_list: List[RESULT] = [(state2, player, source, [obj2])]
        # if necessary, the object will now instantly resolve. We are
        # guaranteed that the object is be the latest item on the stack, as
        # triggers go to SUPER-stack. obj was put on stack so early because
        # then it can be automatically copied by GameState, for ease.
        new_tuple_list = []
        for result in tuple_list:
            # only item remaining in input is the copy_of_obj we added
            new_tuple_list += self._remove_if_needed(*result)
        # 601.2i: ability has now "been activated".  Any abilities which
        # trigger from some aspect of paying the costs have already
        # been added to the superstack during ability.cost.pay. Now add
        # any trigger that trigger off of this activation/casting itself.
        final_results = []
        for g2, p2, s2, input2 in new_tuple_list:
            final_results += super().do_it(g2, p2, s2, input2)
        return final_results

    @staticmethod
    def _add_to_stack(game: GameState, obj: StackObject) -> None:
        """Mutate the GameState to put the given StackObject
        onto the stack. This includes removing it from other
        zones if necessary."""
        game.stack.append(obj)

    @staticmethod
    def _remove_if_needed(game: GameState, player: int, source: Cardboard,
                          obj_as_input: List[StackObject]) -> List[RESULT]:
        """If the thing we just put on the stack is supposed to
        resolve instantly, do that. MUTATES."""
        return [(game, player, source, obj_as_input)]

    def add_self_to_state_history(self, state: GameState, player,
                                  source: StackObject, other_inputs: INPUTS):
        if state.is_tracking_history:
            record = "\n*** %s %s ***" % (str(self), str(source))
            state.events_since_previous += record


class PlayAbility(UniversalCaster):
    def __str__(self):
        return "Activate"


class PlayManaAbility(PlayAbility):
    @staticmethod
    def _remove_if_needed(game: GameState, player: int, source: Cardboard,
                          obj_as_input: List[StackObject]) -> List[RESULT]:
        """If the thing we just put on the stack is supposed to
        resolve instantly, do that."""
        stack_obj = game.stack.pop(-1)
        assert stack_obj is obj_as_input[0]
        # perform the effect (resolve ability, perform spell, etc)
        if stack_obj.effect is None:
            return [(game, player, source, obj_as_input)]
        else:
            # add stack_obj to the list of choices needed to perform the
            # `effect`, so stack_obj will remain once choices are used up.
            inputs = stack_obj.choices + [stack_obj]
            return stack_obj.effect.do_it(game, player, source, inputs)


class AddTriggeredAbility(UniversalCaster):
    def __str__(self):
        return "Trigger"

    def do_it(self, state: GameState, player, source,
              other_inputs: List[StackTrigger]):
        """Put the StackObject onto the stack, paying any
        necessary costs. Bypass the stack if necessary."""
        # check to make sure the execution is legal
        if not self.can_be_done(state, player, source, other_inputs):
            return []
        # 601.2a: add the spell to the stack
        trig: StackTrigger = other_inputs[0]
        targets = [()]
        if trig.effect is not None:
            targets = trig.effect.get_input_options(state, player,
                                                    trig.source_card,
                                                    trig.cause)
        # now have targets for the trigger, so can make StackAbility for it
        final_results = []
        for choices in targets:
            abil = Stack.StackAbility(trig.player_index, trig.source_card,
                                      trig.obj, choices, NullVerb())
            state2, [abil2, trig2] = state.copy_and_track([abil, trig])
            state2.super_stack.remove(trig2)
            state2.stack.append(abil)
            # if necessary, the object will now instantly resolve. We are
            # guaranteed that the object is be the latest item on the stack
            # since triggers go to SUPER-stack.
            new_tuple_list = self._remove_if_needed(state2, player,
                                                    abil.source_card, [abil2])
            # 601.2i: ability has now "been activated".  Any abilities which
            # trigger from some aspect of paying the costs have already
            # been added to the superstack during ability.cost.pay. Now add
            # any trigger that trigger off of this activation/casting itself.
            for results in new_tuple_list:
                final_results += super().do_it(*results)
        return final_results


class AddAsEntersAbility(AddTriggeredAbility):
    @staticmethod
    def _remove_if_needed(game: GameState, player: int, source: Cardboard,
                          obj_as_input: List[StackObject]) -> List[RESULT]:
        """If the thing we just put on the stack is supposed to
        resolve instantly, do that."""
        stack_obj = game.stack.pop(-1)
        assert stack_obj is obj_as_input[0]
        # perform the effect (resolve ability, perform spell, etc)
        if stack_obj.effect is None:
            return [(game, player, source, obj_as_input)]
        else:
            # add stack_obj to the list of choices needed to perform the
            # `effect`, so stack_obj will remain once choices are used up.
            inputs = stack_obj.choices + [stack_obj]
            return stack_obj.effect.do_it(game, player, source, inputs)


# ----------

class PlayCardboard(UniversalCaster):

    def __str__(self):
        return "Cast"

    @staticmethod
    def _add_to_stack(game: GameState, obj: StackCardboard) -> None:
        """Mutate the GameState to put the given StackObject
        onto the stack. This includes removing it from other
        zones if necessary."""
        zone = game.get_zone(obj.source_card.zone, obj.player_index)
        zone.remove(obj.source_card)
        game.stack.append(obj)


# ----------
class PlayLand(PlayCardboard):

    def __str__(self):
        return "Play"

    @staticmethod
    def _remove_if_needed(game: GameState, player: int, source: Cardboard,
                          obj_as_input: List[StackObject]) -> List[RESULT]:
        """If the thing we just put on the stack is supposed to
        resolve instantly, do that."""
        stack_obj = game.stack.pop(-1)
        assert stack_obj is obj_as_input[0]
        assert stack_obj.obj.zone == ZONE.STACK
        # move the land to the field instantly
        MoveToZone(ZONE.FIELD).do_it(game, stack_obj.player_index,
                                     stack_obj.obj, [])
        # add stack_obj so that it will remain once choices are used up.
        inputs = stack_obj.choices + [stack_obj]
        return stack_obj.effect.do_it(game, stack_obj.player_index,
                                      stack_obj.obj, inputs)


# ----------
class PlaySorcery(PlayCardboard):
    def can_be_done(self, state, player, source, other_inputs) -> bool:
        doable = super().can_be_done(state, player, source, other_inputs)
        stack_empty = len(state.stack) == 0
        card = other_inputs[0].obj
        has_flash = Match.Keyword("flash").match(card, state, card)
        return doable and (stack_empty or has_flash)


# ----------
class PlayPermanent(PlayCardboard):
    def can_be_done(self, state, player, source, other_inputs) -> bool:
        doable = super().can_be_done(state, player, source, other_inputs)
        stack_empty = len(state.stack) == 0
        card = other_inputs[0].obj
        has_flash = Match.Keyword("flash").match(card, state, card)
        return doable and (stack_empty or has_flash)
