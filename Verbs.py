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
    from Abilities import TriggeredAbility, ActivatedAbility
    from Stack import StackObject

    # SOURCE = Cardboard | Player
    SUBJECT = Cardboard | Player | StackObject
    CAUSE = Cardboard | Player | None
    INPUT = Cardboard | Player | StackObject | int | list | None
    RESULT = Tuple[GameState, Player, SUBJECT, Tuple[INPUT]]

import ZONE
import Match as Match
import Getters as Get
import ManaHandler
import Stack


class WinTheGameError(Exception):
    pass


class LoseTheGameError(Exception):
    pass


# def join(list_of_lists: List[list]):
#     accumulator = []
#     for sub_list in list_of_lists:
#         accumulator += sub_list
#     return accumulator
# 
# class Action:
#     def __init__(self):
#         self.controller_index: int  # or possibly Player
#         # any action in the game is either because a card said to do (add mana,
#         # tap a creature) so because the game rules said to do so (declare as
#         # attacker
#         self.source: Cardboard | None
#         self.subject: Cardboard | Player | StackObject  # what is it affecting


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class Verb:
    def __init__(self, num_inputs: int, mutates: bool):
        self.num_inputs: int = num_inputs  # includes usual "subject" at [0].
        self.mutates: bool = mutates

    def get_input_options(self, state: GameState, controller: Player,
                          source: Cardboard | None, cause: Cardboard | None
                          ) -> List[Tuple[INPUT]]:
        """A list of possibly input tuples, the first
         `num_inputs` of which match `input_signature`
         for their types."""
        return []

    def can_be_done(self, state: GameState, controller: Player,
                    source: Cardboard | None, subject: INPUT,
                    *others: INPUT) -> bool:
        """GameState; subject to apply the Verb to; any
        additional inputs needed. The specific type of
        `subject` and of the other inputs is specified
        by `input_signature`"""
        # noinspection PyTypeHints
        return 1 + len(others) >= self.num_inputs

    def do_it(self, state: GameState, controller: Player,
              source: Cardboard | None, subject: INPUT, *others: INPUT
              ) -> List[RESULT]:
        """Mutates state to add triggers to super_stack.
                Returns state, source, choices -- except choices
                have been shortened to "use up" this Verb's inputs."""
        self.add_self_to_state_history(state, subject, *others)
        # `trigger_source` is source of the trigger. Not to be confused
        # with `subject`, which is the cause of the Verb which is
        # potentially CAUSING the trigger.
        for trigger_source in state.get_all_public_cards():
            for ability in trigger_source.rules_text.trig_verb:
                if ability.is_triggered(self, state, trigger_source, source):
                    stack_obj = Stack.StackTrigger(ability, trigger_source,
                                                   [source])
                    state.super_stack.append(stack_obj)
        return [(state, controller, source, others[self.num_inputs:])]

    def is_type(self, verb_type: type) -> bool:
        return isinstance(self, verb_type)

    def __add__(self, other):
        return MultiVerb([self, other])

    # def __or__

    def __str__(self):
        return type(self).__name__

    def add_self_to_state_history(self, state: GameState, subject: INPUT,
                                  *others: INPUT) -> None:
        """If the GameState is tracking history, adds a note
        to that history describing this Verb. Mutates state,
        technically, in that note is added rather than added
        to a copy."""
        if state.is_tracking_history:
            record = "\n%s %s" % (str(self), subject.name)
            state.events_since_previous += record

    # def on(self, subject_getter: Get.Getter) -> ApplyTo:
    #     return ApplyTo(subject_getter, self)


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
        # if any don't mutate, then whole verb must copy instead of mutating.
        super().__init__(sum([v.num_inputs for v in self.sub_verbs]),
                         all([v.mutates for v in self.sub_verbs]))

    def get_input_options(self, state, controller, source, cause):
        # list of sublists. start with 1 sublist, which is empty
        choices = [()]
        # get any choices from any sub-verbs
        for v in self.sub_verbs:
            if v.num_inputs >= 0:
                verb_choices = v.get_input_options(state, controller,
                                                   source, cause)
                new_list = []
                for sublist in choices:
                    new_list += [sublist + ch for ch in verb_choices]
                choices = new_list
        return choices

    def can_be_done(self, state, controller, source, *inputs) -> bool:
        if not super().can_be_done(state, controller, source, *inputs):
            return False
        i_start = 0
        for v in self.sub_verbs:
            i_end = i_start + v.num_inputs
            if not v.can_be_done(state, controller, source,
                                 *inputs[i_start:i_end]):
                # if any verb cannot be done, the whole list cannot be done
                return False
            i_start = i_end  # increment to use the next choices for next verb
        return True  # if reached here, all verbs are doable!

    def do_it(self, state, controller, source, *inputs) -> List[RESULT]:
        """Mutates state to add triggers to super_stack.
        Returns state, source, choices -- except choices
        have been shortened to "use up" this Verb's inputs."""
        tuple_list = [(state, inputs)]
        for v in self.sub_verbs:
            new_tuple_list = []
            for st, cn, sr, ip in tuple_list:
                # uses up inputs as it goes, dumps shorter inputs into list. 
                new_tuple_list += v.do_it(st, cn, sr, *ip)
            tuple_list = new_tuple_list
        # The do_it functions of each Verb will handle triggers for those
        # sub-verbs. The Multi-Verb itself can't cause any triggers.
        return tuple_list

    def is_type(self, verb_type: type):
        return any([v.is_type(verb_type) for v in self.sub_verbs])

    def __str__(self):
        return " & ".join([v.__str__() for v in self.sub_verbs])


class AffectsController(Verb):
    def get_input_options(self, state: GameState, controller: Player,
                          source: Cardboard | None, cause: Cardboard | None
                          ) -> List[Tuple[INPUT]]:
        """Subject is the controller of the Verb"""
        return [(controller,)]


class AffectsSource(Verb):
    def get_input_options(self, state: GameState, controller: Player,
                          source: Cardboard | None, cause: Cardboard | None
                          ) -> List[Tuple[INPUT]]:
        """Subject is the source of the Verb"""
        return [(source,)]


# class ApplyTo(Verb):
#     """Chooses a subject and then applies the given Verb to
#     that subject.
#     The first element of `choices` is a list giving the
#     targets of the given Verb. If there is more than one
#     target given, the Verb is applied to each target in
#     sequence.
#     """
# 
#     def __init__(self, subject_getter: Get.Getter, verb: Verb):
#         self.getter = subject_getter
#         self.verb = verb
#         assert self.verb.num_inputs == 0
#         self.allowed_to_fail = (hasattr(self.getter, "can_be_less")
#                                 and self.getter.can_be_less)
# 
#     @property
#     def num_inputs(self) -> int:
#         return 1 + self.verb.num_inputs
# 
#     @property
#     def mutates(self):
#         return self.verb.mutates
# 
#     def get_input_options(self, state: GameState, source: SOURCE,
#                           cause: CAUSE) -> List[INPUT]:
#         """
#         Returns a list of sub-lists. Each sub-list represents
#         one possible way to choose modes and/or targets for this
#         Verb.  The sublists are intended to be passed into calls
#         to `can_be_done` and `do_it` as the `choices` argument.
#         The `source` is the thing which is performing the verb,
#         and the `cause` is the reason why the verb is being
#         performed (often identical to the source).
#         """
#         # list of sublists. start with 1 sublist, which is empty
#         choices = [[x] for x in self.getter.get(state, source)]
#         assert self.verb.num_inputs == 0
#         # verb_choices = self.verb.get_input_options(state, source, cause)
#         # new_list = []
#         # for sublist in choices:
#         #     new_list += [sublist + ch for ch in verb_choices]
#         # choices = new_list
#         return choices
# 
#     def can_be_done(self, state: GameState, *inputs: SUBJECT) -> bool:
#         """
#         The first element of `choices` is a list of length 0
#         or 1 containing the single target of the given Verb.
#         If empty, the chooser "failed to find" a target. The
#         Verb will not be applied to anything. Still may be ok.
#         """
#         if len(choices) == 0:  # has no first element
#             return False
#         if len(choices[0]) == 0:
#             # chooser failed to find a target. ok only if "allowed" to fail.
#             return self.allowed_to_fail
#         return any([self.verb.can_be_done(state, target, choices[1:])
#                     for target in choices[0]])
# 
#     def do_it(self, state: GameState, *inputs):
#         """Expects the first element of `choices` to be a list
#         of subjects that the Verb should be applied to.
#         The first element of `choices` is also allowed to be
#         empty. This is the "fail to find" mode. The Verb
#         will not be applied to anything, but this is ok."""
#         if len(choices[0]) == 0:
#             # Failed to find target. If got this far, presumably failing is ok.
#             # So do nothing and trigger.
#             if self.mutates:
#                 return [(state, source, choices[1:])]
#             else:
#                 state2, things = state.copy_and_track([subject] + choices[1:])
#                 return [(state2, things[0], things[1:])]
#         else:
#             if self.mutates:
#                 for target in choices[0]:
#                     self.verb.do_it(state, )
#                 return [(state, source, choices[self.num_inputs:])]
#             else:
#                 # make some extra choices to chew through. Should look like:
#                 # target1, choiceA, ... choiceN, target2, choiceA, ... choiceN,
#                 # final_choicesX, ... final_choicesZ
#                 concat_choices = [subject]
#                 for target in choices[0]:
#                     concat_choices.append(target)
#                     concat_choices += choices[1:self.num_inputs]
#                 concat_choices += choices[self.num_inputs:]
#                 # copy gamestate (and these choices) and then start do_it loop
#                 state2, concat2 = state.copy_and_track(concat_choices)
#                 # standard "state, source, choices" format
#                 tuple_list: List[RESULT] = [(state2, concat2[0], concat2[1:])]
#                 for _ in range(len(choices[0])):
#                     new_list = []
#                     for g, s, ch in tuple_list:
#                         new_list += self.verb.do_it(g, )
#                     tuple_list = new_list
#                 return tuple_list
# 
#     def is_type(self, verb_type: type):
#         return self.verb.is_type(verb_type)
# 
#     def __str__(self):
#         return "%s(%s)" % (str(self.verb), str(self.getter))
# 
# 
# class Modal(Verb):
#     """Mode is chosen at cast-time"""
# 
#     def __init__(self, list_of_verbs: List[Verb], num_to_choose: int = 1):
#         super().__init__()
#         assert (len(list_of_verbs) > 1)
#         assert all([v.num_inputs == list_of_verbs[0].num_inputs
#                     for v in list_of_verbs])
#         self.sub_verbs = list_of_verbs
#         options = [(ii, str(v)) for ii, v in enumerate(self.sub_verbs)]
#         self.chooser = Get.Chooser(Get.Const(options), num_to_choose, False)
# 
#     @property
#     def num_inputs(self) -> int:
#         return 1 + self.sub_verbs[0].num_inputs  # choice of verbs is [0]
# 
#     @property
#     def mutates(self):
#         return any([v.mutates for v in self.sub_verbs])
# 
#     def get_input_options(self, state: GameState, source: SOURCE,
#                           cause: CAUSE) -> List[INPUT]:
#         # choices are: the verb I choose, together with IT'S choices
#         modes: List[Tuple[Tuple[int, str]]] = self.chooser.get(state, source)
#         choices: List[INPUT] = []
#         for set_of_verbs in modes:
#             verb_indices = [index for index, name in set_of_verbs]
#             multi = MultiVerb([self.sub_verbs[ii] for ii in verb_indices])
#             for sub_choice in multi.get_input_options(state, source, cause):
#                 # noinspection PyTypeChecker
#                 choices += [verb_indices] + sub_choice
#         return choices
# 
#     def can_be_done(self, state: GameState, *inputs: SUBJECT) -> bool:
#         """first element of choices is the choice of which verbs to use"""
#         multi = MultiVerb([self.sub_verbs[ii] for ii in choices[0]])
#         return multi.can_be_done(state, inputs, choices[1:])
# 
#     def do_it(self, state: GameState, *inputs) -> List[RESULT]:
#         """first element of choices is the choice of which verb to use"""
#         multi = MultiVerb([self.sub_verbs[ii] for ii in choices[0]])
#         return multi.do_it(state, )
# 
#     def __str__(self):
#         return " or ".join([v.__str__() for v in self.sub_verbs])
# 
#     def is_type(self, verb_type: type) -> bool:
#         return all([v.is_type(verb_type) for v in self.sub_verbs])
# 
# 
# class Defer(Verb):
#     """
#     Defers any cast-time choices of the given verb to instead
#     be chosen only on resolution.
#     """
#     def __init__(self, verb: Verb):
#         self.verb = verb
# 
#     @property
#     def mutates(self):
#         return False
# 
#     def do_it(self, state: GameState, *inputs):
#         # choices should be []
#         results = []
#         if self.verb.mutates:
#             choices = self.verb.get_input_options(state, source, choices)
#             for choice in choices:
#                 state2, things = state.copy_and_track([subject]+choice)
#                 results += self.verb.do_it(state2, )
#         else:
#             choices = self.verb.get_input_options(state, source, subject)
#             for choice in choices:
#                 results += self.verb.do_it(state, )
#         return results
# 
#     def is_type(self, verb_type: type):
#         return self.verb.is_type(verb_type)
# 
#     def __str__(self):
#         return str(self.verb)


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
#         # Note that NO INPUT ARE BEING PASSED TO THE SUB_VERBS. This is
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
#         s = "%s on %s%i of %s else %s" % (act_yes, comp, num, get_str, act_no)
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
# class VerbOnCause(ApplyTo):
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
#                           cause: CAUSE) -> List[INPUT]:
#         return [[[cause]]]


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class NullVerb(Verb):
    """This Verb does literally nothing, ever."""

    def __init__(self):
        super().__init__(0, False)

    def get_input_options(self, state, controller, source, cause):
        return [(None,)]

    def do_it(self, state: GameState, controller, source, *inputs):
        return [(state, controller, source, inputs)]

    def add_self_to_state_history(self, state, *inputs):
        return

    def __str__(self):
        return ""


class PayMana(AffectsController):
    """deducts the given amount of mana from the Player's
    mana pool."""

    def __init__(self, mana_string: Get.String | str):
        super().__init__(0, True)
        if isinstance(mana_string, str):
            mana_string = Get.ConstString(mana_string)
        self.string_getter: Get.String = mana_string

    def can_be_done(self, state, controller, source, 
                    subject: INPUT, *inputs: INPUT) -> bool:
        if not super().can_be_done(state, controller, source, subject, *inputs):
            return False
        cost = ManaHandler.ManaCost(self.string_getter.get(state, subject))
        return subject.pool.can_afford_mana_cost(cost)

    def do_it(self, state, controller, source, subject, *inputs):
        cost = ManaHandler.ManaCost(self.string_getter.get(state, subject))
        subject.pool.pay_mana_cost(cost)
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)

    def __str__(self):
        return "PayMana{%s}" % str(self.string_getter)

    def add_self_to_state_history(self, state: GameState, subject: INPUT,
                                  *inputs: Player):
        if state.is_tracking_history:
            cost = ManaHandler.ManaCost(self.string_getter.get(state, subject))
            text = "\nPay %s" % str(cost)
            state.events_since_previous += text


class AddMana(AffectsController):
    """adds the given amount of mana to the GameState's mana pool"""

    def __init__(self, mana_string: Get.String | str):
        super().__init__(0, True)
        if isinstance(mana_string, str):
            mana_string = Get.ConstString(mana_string)
        self.string_getter: Get.String = mana_string

    def do_it(self, state, controller, source, subject, *inputs):
        pool = ManaHandler.ManaPool(self.string_getter.get(state, subject))
        subject.pool.add_mana(pool)
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)

    def add_self_to_state_history(self, state, subject, *inputs):
        if state.is_tracking_history:
            pool = ManaHandler.ManaPool(self.string_getter.get(state, subject))
            text = "\nAdd %s" % str(pool)
            state.events_since_previous += text


class LoseLife(AffectsController):
    def __init__(self, damage_getter: Get.Integer | int):
        """The subject player loses the given amount of life"""
        super().__init__(0, True)
        if isinstance(damage_getter, int):
            damage_getter = Get.ConstInteger(damage_getter)
        self.damage_getter: Get.Integer = damage_getter

    def do_it(self, state, controller, source, subject, *inputs):
        subject.life -= self.damage_getter.get(state, subject)
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)

    def add_self_to_state_history(self, state, subject, *inputs):
        if state.is_tracking_history:
            text = "\nLose %i life" % self.damage_getter.get(state, subject)
            state.events_since_previous += text


class Tap(AffectsSource):
    """taps `source` if it was not already tapped."""
    def __init__(self):
        super().__init__(1, True)

    def can_be_done(self, state: GameState, controller, source, subject,
                    *inputs: Cardboard) -> bool:
        return (super().can_be_done(state, controller, subject, source, *inputs)
                and subject.zone == ZONE.FIELD and not subject.tapped)

    def do_it(self, state: GameState, controller, source, subject, *inputs):
        subject.tapped = True
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)


class Untap(AffectsSource):

    def can_be_done(self, state: GameState, controller, source, subject,
                    *inputs: Cardboard) -> bool:
        return (super().can_be_done(state, controller, source, subject, *inputs)
                and subject.tapped and subject.zone == ZONE.FIELD)

    def do_it(self, state: GameState, controller, source, subject, *inputs):
        subject.tapped = False
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)


class AddCounter(AffectsSource):
    """Adds the given counter string to the subject card"""

    def __init__(self, counter_text: str):
        super().__init__()
        self.counter_text = counter_text

    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        return inputs.zone == ZONE.FIELD

    def do_it(self, state, controller, source, *inputs):
        subject.add_counter(self.counter_text)
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)

    def add_self_to_state_history(self, state: GameState, controller, source,
                                  *inputs: Cardboard):
        if state.is_tracking_history:
            text = "\nPut %s counter on %s" % (self.counter_text, subject.name)
            state.events_since_previous += text


class ActivateOncePerTurn(Verb):
    """Marks the given `subject` as only able to activate this ability once
    per turn"""

    def __init__(self, ability_name: str):
        super().__init__()
        self.counter_text = "@" + ability_name  # "@" is invisible counter

    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        return (inputs.zone == ZONE.FIELD
                and self.counter_text not in inputs.counters)

    def do_it(self, state, controller, source, *inputs):
        subject.add_counter(self.counter_text)
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)

    def add_self_to_state_history(self, state: GameState, controller, source,
                                  *inputs: Cardboard):
        return  # doesn't mark itself as having done anything


class ActivateOnlyAsSorcery(Verb):
    """Checks that the stack is empty and cannot be done otherwise"""

    def can_be_done(self, state: GameState, controller, source,
                    *inputs: SUBJECT) -> bool:
        return len(state.stack) == 0

    def do_it(self, state, controller, source, *inputs):
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)

    def add_self_to_state_history(self, state: GameState, controller, source,
                                  *inputs: Cardboard):
        return  # doesn't mark itself as having done anything


class Shuffle(Verb):
    """Shuffles the deck of the controller of `subject`"""

    def do_it(self, state, controller, source, *inputs):
        # add triggers to super_stack, reduce length of input list
        """Mutates. Reorder deck randomly."""
        random.shuffle(subject.deck)
        return super().do_it(state, controller, source, subject, *inputs)

    def add_self_to_state_history(self, state, controller, source, *inputs):
        if state.is_tracking_history:
            state.events_since_previous += "\nShuffle"


class MoveToZone(Verb):
    """Moves the subject card to its controller's given zone.
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

    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        if not super().can_be_done(state, PLAYER, SUBJECT, inputs, choices):
            return False
        elif inputs.zone in [ZONE.DECK, ZONE.DECK_BOTTOM, ZONE.HAND,
                             ZONE.FIELD, ZONE.GRAVE]:
            return inputs in state.get_zone(inputs.zone,
                                            inputs.controller_index)
        else:
            return True

    def do_it(self, state, controller, source, *inputs):
        # NOTE: Cardboard can't live on the stack. only StackObjects do. So
        # reassign card zone and remove/add to zones as appropriate, but never
        # directly add or remove from the stack. StackCardboard does the rest.
        self.origin = subject.zone  # so trigger knows where card moved from
        # remove from origin
        if self.origin in [ZONE.DECK, ZONE.DECK_BOTTOM, ZONE.HAND,
                           ZONE.FIELD, ZONE.GRAVE]:
            zone = state.get_zone(subject.zone, subject.player_index)
            zone.remove(subject)
        # add to destination
        subject.zone = self.destination
        if self.destination in [ZONE.HAND, ZONE.FIELD, ZONE.GRAVE]:
            # these three zones must remain sorted at all times
            zone_list = state.get_zone(self.destination,
                                       subject.player_index)
            zone_list.append(subject)  # can add to any index b/c about to sort
            player = state.player_list[subject.player_index]
            player.re_sort(self.destination)
        elif self.destination == ZONE.DECK:
            deck = state.get_zone(ZONE.DECK, subject.player_index)
            deck.insert(0, subject)  # add to top (index 0) of deck
        elif self.destination == ZONE.DECK_BOTTOM:
            deck = state.get_zone(ZONE.DECK, subject.player_index)
            deck.append(subject)  # add to bottom (index -1) of deck
        # any time you change zones, reset the cardboard parameters
        subject.reset_to_default_cardboard()
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)

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


class DrawCard(Verb):
    """The controller of `subject` draws from index 0 of deck"""

    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Player) -> bool:
        return True  # Even if the deck is 0, you CAN draw. you'll just lose

    def do_it(self, state, controller, source, *inputs):
        if len(subject.deck) > 0:
            mover = MoveToZone(ZONE.HAND)
            # Adds move triggers to super_stack
            mover.do_it(state, PLAYER, SUBJECT)
            # add triggers to super_stack, reduce length of input list
            return super().do_it(state, controller, source, subject, *inputs)
        else:
            raise LoseTheGameError


class MarkAsPlayedLand(Verb):
    """Doesn't actually move any cards, just toggles the
    gamestate to say that the controller of `subject` has
    played a land this turn"""

    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Player) -> bool:
        return inputs.land_drops_left > 0

    def do_it(self, state, controller, source, *inputs):
        subject.num_lands_played += 1
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)

    def add_self_to_state_history(self, state: GameState, controller, source,
                                  *inputs: Player):
        return


class Sacrifice(Verb):
    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        return (super().can_be_done(state, PLAYER, SUBJECT, inputs, choices)
                and inputs.zone == ZONE.FIELD)

    def do_it(self, state, controller, source, *inputs):
        MoveToZone(ZONE.GRAVE).do_it(state, PLAYER, SUBJECT)
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)


class Destroy(Verb):
    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        return inputs.zone == ZONE.FIELD  # can attempt even if indestructible

    def do_it(self, state, controller, source, *inputs):
        if not Match.Keyword("indestructible").match(
                Player | Cardboard | StackObject, GameState, SOURCE):
            MoveToZone(ZONE.GRAVE).do_it(state, PLAYER, SUBJECT)
        # add triggers to super_stack, reduce length of input list
        return super().do_it(state, controller, source, subject, *inputs)


# ----------

class Tutor(ApplyTo):
    def __init__(self, zone_to_move_to, num_to_find: int,
                 pattern: Match.CardPattern):
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

class PlayAbility(Verb):
    def __init__(self, ability: ActivatedAbility):
        super().__init__()
        self.ability = ability

    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        """Can the ability be activated? The source of the
         ability is assumed to be the `subject` Cardboard.
        """
        pay_choices = choices[:self.ability.cost.num_inputs]
        targets = choices[self.ability.cost.num_inputs:]
        return (self.ability.cost.can_afford(state, inputs, pay_choices)
                and self.ability.effect.can_be_done(state, PLAYER, SUBJECT,
                                                    inputs, targets))

    def do_it(self, state: GameState, controller, source, *inputs):
        """Activate the ability. The source of the ability is
        assumed to be the `subject` Cardboard. `choices` describe
        the choices for paying for the ability, followed by choices
        for using the ability. Note that super_stack is NOT
        guaranteed to be clear!
        DOES NOT MUTATE THE GIVEN STATE.
        """
        # check to make sure the execution is legal
        if not self.can_be_done(state, PLAYER, SUBJECT, source, choices):
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
        list_of_tuples = self.ability.cost.pay_cost(copy_of_game,
                                                    copy_of_spell,
                                                    copy_of_choices)
        # Build a StackAbility and add it to the stack
        new_tuple_list = []
        for g1, s1, targets in list_of_tuples:
            new_tuple_list += self._add_to_stack(g1, s1, targets)
        # 601.2i: ability has now "been activated".  Any abilities which
        # trigger from some aspect of paying the costs have already
        # been added to the superstack during ability.cost.pay. Now add
        # any trigger that trigger off of this activation itself.
        final_results = []
        for g2, s2, targets2 in new_tuple_list:
            final_results += super().do_it(g2, PLAYER, SUBJECT)
        return final_results

    def _add_to_stack(self, game: GameState, source: Cardboard,
                      targets: INPUT) -> List[RESULT]:
        """Mutates the given gamestate by creating a StackAbility
        and adding it to the stack."""
        game.stack.append(Stack.StackAbility(self.ability, source, targets))
        return [(game, source, targets)]

    def get_input_options(self, state: GameState, source: SOURCE,
                          cause: CAUSE) -> List[INPUT]:
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payments = self.ability.cost.get_options(state, source, cause)
        # 601.2c: choose targets and modes
        targets = self.ability.effect.get_input_options(state, source, cause)
        # combine all combinations of these
        new_choices = []
        for sub_pay in payments:
            for sub_target in targets:
                new_choices.append(
                    sub_pay + sub_target)  # concatenate sub-lists
        return new_choices

    def mutates(self):
        return False

    def num_inputs(self):
        return self.ability.cost.num_inputs + self.ability.effect.num_inputs

    def __str__(self):
        return "Activate " + str(self.ability)

    def add_self_to_state_history(self, state: GameState, controller, source,
                                  *inputs: Cardboard):
        if state.is_tracking_history:
            record = "\n*** Activate %s ***" % self.ability.name
            # if len(choices) > 0:
            #     record += " {%s}" % ", ".join([str(c) for c in choices])
            state.events_since_previous += record


# ----------

class PlayManaAbility(PlayAbility):
    def _add_to_stack(self, game: GameState, source: SOURCE,
                      targets: INPUT) -> List[RESULT]:
        """Mana abilities don't use the stack. So, instead of
        creating a StackAbility and adding it to the stack,
        simply mutate the gamestate to add the mana directly."""
        return self.ability.effect.do_it(game, PLAYER, SUBJECT)


# ----------
class AddTriggeredAbility(Verb):
    """Adds a triggered ability StackObject to the stack
    for the given ability. It does NOT handle putting the
    StackTrigger onto the super_stack in the first place
    or checking if the ability really triggered (both of
    which happen in super().do_it, the Verb function). It
    also does NOT handle resolving the ability (which is
    in GameState.resolve_top_of_stack)."""

    def __init__(self, ability: TriggeredAbility):
        super().__init__()
        self.ability = ability

    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        """Can this triggered_ability be put onto the stack?
        The ability itself has already decided whether it has
        been triggered. This function only checks that the
        choices for targets are valid. `choices` must be at
        least length 1, because choices[0] is the thing
        that caused the ability to trigger
        """
        return (len(choices) >= 1 and
                self.ability.effect.can_be_done(state, PLAYER, SUBJECT, inputs,
                                                choices[1:]))

    def do_it(self, state: GameState, controller, source, *inputs):
        """Activate the ability. The source of the ability is
        assumed to be the `subject` Cardboard. The first item
        in `choices` must be the thing which triggered the
        ability in the first place, and the rest is targets
        for the ability's effect.
        DOES NOT MUTATE THE GIVEN GAMESTATE.
        """
        # check to make sure the execution is legal
        if not self.can_be_done(state, PLAYER, SUBJECT, source, choices):
            return []
        # new copy of the game
        game2, things = state.copy_and_track([subject] + choices)
        spell2 = things[0]
        # things is [cause: Cardboard] + choices: list. but no longer need
        # the cause anymore!
        choices2 = things[2:]
        # Build a StackTrigger and add to stack. Subclasses may execute instead
        tuple_list = self._add_to_stack(game2, spell2, choices2)
        # trigger abilities that trigger off of this trigger itself
        final_results = []
        for g2, s2, targets2 in tuple_list:
            # strip the 'cause` cardboard off the choice_list manually
            final_results += super().do_it(g2, PLAYER, SUBJECT)
        return final_results

    def _add_to_stack(self, game: GameState, source: Cardboard,
                      choices: INPUT) -> List[RESULT]:
        """Mutates the given gamestate by creating a StackAbility
        and adding it to the stack. First element of choices is
        NO LONGER the `cause` that triggered the ability, that
        has already been stripped out. The choices list here
        should just be the choices needed to execute the effect."""
        game.stack.append(Stack.StackAbility(self.ability, source, choices))
        return [(game, source, choices)]

    def get_input_options(self, state: GameState, source: SOURCE, cause: CAUSE
                          ) -> List[INPUT]:
        """The cardboard that caused the ability to trigger
        is guaranteed to be the first element of each returned
        choice sublist."""
        targets = self.ability.effect.get_input_options(state, source, cause)
        return [[cause] + sub for sub in targets]

    def mutates(self):
        return False

    def __str__(self):
        return "AddTrigger " + str(self.ability)

    def add_self_to_state_history(self, state: GameState, controller, source,
                                  *inputs: Cardboard):
        if state.is_tracking_history:
            record = "\n*** AddTrigger %s ***" % self.ability.name
            # if len(choices) > 0:
            #     record += " {%s}" % ", ".join([str(c) for c in choices])
            state.events_since_previous += record


class AddAsEntersAbility(AddTriggeredAbility):
    def _add_to_stack(self, game: GameState, source: Cardboard, targets: list
                      ) -> List[Tuple[GameState, Cardboard, list]]:
        """As-enter effects don't use the stack. So, instead of
        creating a StackTrigger and adding it to the stack,
        simply MUTATE the gamestate to carry out the effect.
        First element of choices is NO LONGER the `cause` that
        triggered the ability, that has already been stripped
        out. The choices list here should just be the choices
        needed to execute the effect."""
        return self.ability.effect.do_it(game, PLAYER, SUBJECT)


# ----------

class PlayCardboard(Verb):

    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        """Returns whether the `source` card can currently be
         cast. Can all its cost be paid and all targets satisfied
         for the given set of choices?"""
        cost = inputs.rules_text.cost
        pay_choices = choices[:cost.num_inputs]
        return cost.can_afford(state, inputs, pay_choices)

    def do_it(self, state, controller, source, *inputs):
        """Puts the `source` card on the stack, including making any
        choices necessary to do that. Returns (GameState,Cardboard)
        copies but does not mutate. Note that super_stack is NOT
        guaranteed to be clear!"""
        # check to make sure the execution is legal
        if not self.can_be_done(state, PLAYER, SUBJECT, source, choices):
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
        list_of_tuples = subject.cost.pay_cost(copy_of_game, copy_of_spell,
                                               copy_of_choices)
        # Build a StackCardboard and add it to the stack
        new_tuple_list = []
        for g1, s1, targets in list_of_tuples:
            # MoveToZone doesn't actually PUT the Cardboard anywhere. It
            # knows the stack is for StackObjects only. Just removes from
            # hand and marks it's zone as being the stack. Mutates in-place.
            new_tuple_list += self._add_to_stack(g1, s1, targets)
        # 601.2i: ability has now "been activated".  Any abilities which
        # trigger from some aspect of paying the costs have already
        # been added to the superstack during ability.cost.pay. Now add
        # any trigger that trigger off of this casting itself.
        final_results = []
        for g2, s2, targets2 in list_of_tuples:
            final_results += super().do_it(g2, PLAYER, SUBJECT)
        return final_results

    @staticmethod
    def _add_to_stack(game: GameState, source: Cardboard, targets: list
                      ) -> List[Tuple[GameState, Cardboard, list]]:
        """Mutates the given gamestate by moving the card to
        the stack and creating a StackCardboard for it there."""
        MoveToZone(ZONE.STACK).do_it(game, PLAYER, SUBJECT)
        game.stack.append(Stack.StackCardboard(None, source, targets))
        game.player_list[source.player_index].num_spells_cast += 1
        return [(game, source, targets)]

    def get_input_options(self, state, source=None, cause=None):
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        # 601.2c: choose targets and modes. only relevant for effects, I think
        return source.cost.get_options(state, source, cause)

    def mutates(self):
        return False

    def add_self_to_state_history(self, state: GameState, controller, source,
                                  *inputs: Cardboard):
        if state.is_tracking_history:
            record = "\n*** Cast %s ***" % subject.name
            # if len(choices) > 0:
            #     record += " {%s}" % ", ".join([str(c) for c in choices])
            state.events_since_previous += record


# ----------
class PlayLand(PlayCardboard):
    @staticmethod
    def _add_to_stack(game: GameState, source: Cardboard, targets: list
                      ) -> List[Tuple[GameState, Cardboard, list]]:
        """Lands skip the stack. So simply move the card directly
         into play"""
        MoveToZone(ZONE.FIELD).do_it(game, PLAYER, SUBJECT)
        return [(game, source, targets)]


# ----------
class PlaySpellWithEffect(PlayCardboard):

    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        if not super().can_be_done(state, PLAYER, SUBJECT, inputs, choices):
            return False  # handles cost stuff
        assert inputs.effect is not None
        target_choices = choices[inputs.cost.num_inputs:]
        if not inputs.effect.can_be_done(state, PLAYER, SUBJECT, inputs,
                                         target_choices):
            return False
        return True

    def get_input_options(self, state, source=None, cause=None):
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payment_choices = super().get_input_options(state, source, cause)
        # 601.2c: choose targets and modes
        if source.effect is not None:
            target_choices = source.effect.get_input_options(state, source,
                                                             cause)
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
class PlayInstant(PlaySpellWithEffect):
    pass


# ----------
class PlaySorcery(PlayCardboard):
    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        doable = super().can_be_done(state, PLAYER, SUBJECT, inputs, choices)
        stack_empty = len(state.stack) == 0
        has_flash = Match.Keyword("flash").match(
            Player | Cardboard | StackObject, GameState, SOURCE)
        return doable and (stack_empty or has_flash)


# ----------
class PlayPermanent(PlayCardboard):
    def can_be_done(self, state: GameState, controller, source,
                    *inputs: Cardboard) -> bool:
        doable = super().can_be_done(state, PLAYER, SUBJECT, inputs, choices)
        stack_empty = len(state.stack) == 0
        has_flash = Match.Keyword("flash").match(
            Player | Cardboard | StackObject, GameState, SOURCE)
        return doable and (stack_empty or has_flash)
