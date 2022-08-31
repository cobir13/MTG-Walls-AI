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
    import Zone

    # SOURCE = Cardboard | Player
    CAUSE = Cardboard | Player | None
    INPUTS = List[int | Cardboard | StackObject | None | Zone.Zone |
                  Tuple[int | Cardboard | StackObject | None]]
    RESULT = Tuple[GameState, int, Cardboard | None, INPUTS]  # or CONTEXT?

import Zone
import Match as Match
import Getters as Get
import ManaHandler
import Stack
import Choices


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class Verb:
    """Describes an action that a human player can take.
    NOTE: VERBS ARE NOT ALLOWED TO MUTATE AFTER CREATION."""

    def __init__(self, num_inputs: int, copies: bool):
        self.num_inputs: int = num_inputs
        self.copies: bool = copies  # returns copies of GameStates, not mutate.

    def get_input_options(self, state: GameState, player: int,
                          source: Cardboard | None, cause: Cardboard | None
                          ) -> List[INPUTS]:
        """A list of possible input lists that are meant to
        be plugged into can_be_done and do_it"""
        return []  # this means "cannot be done". "No inputs" would be [[]].

    def can_be_done(self, state: GameState, player: int,
                    source: Cardboard | None, other_inputs: INPUTS) -> bool:
        """
        Returns whether this Verb can be done, given
        the current gamestate and list of inputs.
        Arguments are:
            - GameState
            - controlling player (or at least their player_index)
            - card that is causing this Verb to be done, if any
            - list of any additional inputs needed to perform the
                verb. The number of other inputs is specified by
                the verb's field `num_inputs`
        """
        return len(other_inputs) >= self.num_inputs

    def do_it(self, state: GameState, player: int, source: Cardboard | None,
              other_inputs: INPUTS, check_triggers=True) -> List[RESULT]:
        """Carries out the Verb.
         If `copies`, returns fresh Results to avoid mutating
         the input GameState. If `copies` is False, then just
         mutates it.
         If `check_triggers`, calls check_triggers to add any
         new triggers to the super_stack of the result states.
         If the caller wants to call cause_triggers manually,
         such as for a MultiVerb of some sort, they can call
         it themselves later.
         Note that the returned input_list

         """
        self.add_self_to_state_history(state, player, source, other_inputs)
        if check_triggers:
            return [self.check_triggers(state, player, source, other_inputs)]
        else:
            return [(state, player, source, other_inputs)]

    def check_triggers(self, state: GameState, player: int,
                       source: Cardboard | None, other_inputs: INPUTS
                       ) -> RESULT:
        """Adds any new triggers to the super_stack. Also, shortens
        input argument list to "use up" this Verb's subject and any
        other inputs.
        THIS FUNCTION ALWAYS MUTATES."""
        # `trigger_source` is the card which owns the triggered ability which
        # might be triggering. Not to be confused with `subject`, which is the
        # cause of the Verb which is potentially CAUSING the trigger.
        for trigger_source, ability in state.trig_event + state.trig_to_remove:
            # add any abilities that trigger to the super_stack
            ability.add_any_to_super(state, trigger_source.player_index,
                                     trigger_source, self, source)
        return state, player, source, other_inputs[self.num_inputs:]

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
                         any([v.copies for v in self.sub_verbs]), )

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

    def do_it(self, state, player, source, other_inputs,
              check_triggers=True) -> List[RESULT]:
        tuple_list = [(state, player, source, other_inputs)]
        for v in self.sub_verbs:
            new_tuple_list = []
            for st, pl, srce, ins in tuple_list:
                for result in v.do_it(st, pl, srce, ins, check_triggers=False):
                    # normally, do_it would check if verb caused any triggered
                    # abilities to trigger. That check also trims the verb's
                    # inputs from the input list. BUT here, I need to wait
                    # until after ALL verbs are finished before checking about
                    # triggers. So, I need to trim them. But also need to keep
                    # all inputs for later, for the checking. So instead,
                    # CYCLE the inputs. Add to end of list, retrieve later.
                    st2, pl2, srce2, ins2 = result
                    ins2 = ins2[v.num_inputs:] + ins2[:v.num_inputs]
                    new_tuple_list.append((st2, pl2, srce2, ins2))
            tuple_list = new_tuple_list
        # pull inputs to front of list for removal
        n = self.num_inputs
        tuple_list = [(st3, pl3, srce3, ins3[n:] + ins3[:n])
                      for st3, pl3, srce3, ins3 in tuple_list]
        if check_triggers:
            return [self.check_triggers(*res) for res in tuple_list]
        else:
            return tuple_list

    def check_triggers(self, state: GameState, player: int,
                       source: Cardboard | None, other_inputs: INPUTS
                       ) -> RESULT:
        """Adds any new triggers to the super_stack. Also, shortens
        input argument list to "use up" this Verb's subject and any
        other inputs.
        THIS FUNCTION ALWAYS MUTATES."""
        # check if THIS verb causes any triggers. mutates state. returns
        # a trimmed input list. Don't want trimmed yet, so don't store output.
        Verb.check_triggers(self, state, player, source, other_inputs)
        result = (state, player, source, other_inputs)
        for v in self.sub_verbs:
            # each check_triggers trims the input list of that verb's inputs
            result = v.check_triggers(*result)  # mutates
        return result

    def is_type(self, verb_type: type):
        return any([v.is_type(verb_type) for v in self.sub_verbs])

    def __str__(self):
        return " & ".join([v.__str__() for v in self.sub_verbs])


class AffectPlayer(Verb):
    def __init__(self, num_inputs=0):
        """Subject is the asking_player of the Verb"""
        super().__init__(num_inputs, False, )  # mutates, doesn't copy

    def get_input_options(self, state: GameState, player: int,
                          source, cause) -> List[INPUTS]:
        """A list of possibly input lists that are meant to
        be plugged into can_be_done and do_it"""
        return [[]]  # means "no other inputs". "Cannot be done" would be [].

    def do_it(self, state: GameState, player: int, source: Cardboard | None,
              other_inputs: INPUTS, check_triggers=True) -> List[RESULT]:
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def on(self, subject_chooser: Get.AllWhich,
           option_getter: Get.PlayerList, allowed_to_fail: bool = True
           ) -> ApplyToPlayer:
        return ApplyToPlayer(subject_chooser, option_getter, self,
                             allowed_to_fail)


class AffectSourceCard(Verb):
    def __init__(self, num_inputs=0):
        """Subject is the source card of the Verb"""
        super().__init__(num_inputs, False, )  # mutates, doesn't copy

    def get_input_options(self, state: GameState, player: int,
                          source: Cardboard | None, cause) -> List[INPUTS]:
        """A list of possibly input lists that are meant to
        be plugged into can_be_done and do_it"""
        return [[]]  # means "no other inputs". "Cannot be done" would be [].

    def do_it(self, state: GameState, player: int, source: Cardboard,
              other_inputs: INPUTS, check_triggers=True) -> List[RESULT]:
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def on(self, subject_chooser: Get.AllWhich,
           option_getter: Get.CardsFrom, allowed_to_fail: bool = True
           ) -> ApplyToCard:
        return ApplyToCard(subject_chooser, option_getter, self,
                           allowed_to_fail)


class ApplyToCard(Verb):
    """Chooses targets and then passes those targets along
    to the sub-verb AS THOUGH THEY WERE THE `SOURCE` FOR THE
    SUB-VERB.
    If the chooser returns a list longer than length 1, then
    the sub-verb is applied to all the targets in turn.
    """

    def __init__(self, subject_chooser: Get.AllWhich,
                 option_getter: Get.CardsFrom, verb: Verb,
                 allowed_to_fail: bool = True):
        super().__init__(1, copies=True)
        self.chooser: Get.AllWhich = subject_chooser
        self.option_getter: Get.CardsFrom = option_getter
        self.verb = verb
        assert verb.num_inputs == 0
        self.allowed_to_fail = allowed_to_fail

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
        In this particular case, the sublists are length 1 and
        contain a tuple of possible targets to apply the subverb
        to.
        Note that these choices are made at CAST-TIME. If you want
        them to run at RESOLVE-TIME instead, wrap this in `Defer`.
        """
        options = self.option_getter.get(state, player, source)
        choices = self.chooser.pick(options, state, player, source)
        # chooser returns a list of tuples of Cardboards. An input is a
        # LIST of tuples of Cardboards, so wrap each tuple in a list
        assert self.verb.num_inputs == 0
        return [[x] for x in choices]

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        """
        The first element of `other_inputs` is a tuple containing
        targets to use as the single target of the given Verb. If
        # the tuple is empty, the chooser "failed to find" a target.
        # The Verb will not be applied to anything. Still may be ok.
        # If the tuple has many elements, the Verb must be able to
        # be performed on ALL of them.
        """
        if not super().can_be_done(state, player, source, other_inputs):
            return False  # confirms other_inputs is long enough
        targets: Tuple[int | Cardboard | StackObject | None] = other_inputs[0]
        if len(targets) == 0:
            # chooser failed to find a target. ok only if "allowed" to fail.
            return self.allowed_to_fail
        # must be able to perform the verb on ALL given targets
        return all([self.verb.can_be_done(state, player, t, other_inputs[1:])
                    for t in targets])

    def do_it(self, state: GameState, player, source, other_inputs,
              check_triggers=True):
        """
        The first element of `other_inputs` is a tuple containing
        targets to use as the single target of the given Verb. If
        the tuple is empty, the chooser "failed to find" a target.
        The Verb will not be applied to anything. If the tuple has
        any elements, the Verb will attempt to perform itself on
        ALL of them.
        """
        targets = other_inputs[0]
        if len(targets) == 0:
            # Failed to find target. If got this far, presumably failing is ok.
            # So do nothing. Call check_triggers if asked.
            if not self.copies:
                state2, things = state.copy_and_track([source] + other_inputs)
                res = (state2, player, things[0], things[1:])
            else:
                res = (state, player, source, other_inputs)
            return [self.check_triggers(*res)] if check_triggers else [res]
        else:
            if self.copies:
                concat_list = other_inputs + [source]  # track source
                state2, things = state.copy_and_track(concat_list)
                tuple_list = [(state2, player, None, things)]
                for ii in range(len(targets)):
                    new_tuples = []
                    for st, pl, _, ins in tuple_list:
                        targ = ins[0][ii]
                        new_tuples += self.verb.do_it(st, pl, targ, ins[1:],
                                                      check_triggers=False)
                    tuple_list = new_tuples
                # "source" in tuple_list is wrong. retrieve true source
                result_list = [(st2, pl2, ins2[-1], ins2[:-1])
                               for st2, pl2, targ2, ins2 in tuple_list]
            else:
                for target in targets:
                    self.verb.do_it(state, player, target, other_inputs[1:],
                                    check_triggers=False)
                result_list = [(state, player, source, other_inputs)]
            if check_triggers:
                return [self.check_triggers(*res) for res in result_list]
            else:
                return result_list

    def check_triggers(self, state: GameState, player: int,
                       source: Cardboard | None, other_inputs: INPUTS
                       ) -> RESULT:
        """Adds any new triggers to the super_stack. Also, shortens
        input argument list to "use up" this Verb's target(s).
        The first element of `other_inputs` is a tuple containing
        targets to use as the single target of the given Verb. If
        the tuple is empty, the chooser "failed to find" a target.
        The Verb will not be applied to anything. If the tuple has
        any elements, the Verb will attempt to perform itself on
        ALL of them.
        THIS FUNCTION ALWAYS MUTATES."""
        for t in other_inputs[0]:
            # check_triggers mutates state. no trim since verb takes 0 inputs.
            self.verb.check_triggers(state, player, t, other_inputs[1:])
        # check if THIS verb causes any triggers. returns with targets trimmed
        return Verb.check_triggers(self, state, player, source, other_inputs)

    def is_type(self, verb_type: type):
        return self.verb.is_type(verb_type)

    def __str__(self):
        return "%s(%s%s)" % (str(self.verb), str(self.chooser),
                             str(self.option_getter))


class ApplyToPlayer(Verb):
    """Chooses targets and then passes those targets along
    to the player AS THOUGH IT WAS THE `PLAYER` FOR THE
    SUB-VERB.
    If the chooser returns a list longer than length 1, then
    the sub-verb is applied to all the players in turn.
    """

    def __init__(self, subject_chooser: Get.AllWhich,
                 option_getter: Get.PlayerList, verb: Verb,
                 allowed_to_fail: bool = True):
        super().__init__(1, copies=True)
        self.chooser: Get.AllWhich = subject_chooser
        self.option_getter: Get.PlayerList = option_getter
        self.verb = verb
        assert verb.num_inputs == 0
        self.allowed_to_fail = allowed_to_fail

    def get_input_options(self, state, player, source, cause
                          ) -> List[List[Tuple[int]]]:
        """
        In this particular case, the sublists are length 1 and
        contain a tuple of possible players to apply the subverb
        to.
        """
        options: List[Player] = self.option_getter.get(state, player, source)
        results: List[List[Tuple[int]]] = []
        for tup in self.chooser.pick(options, state, player, source):
            tup: Tuple[Player]
            new_tup: Tuple[int] = tuple([p.player_index for p in tup])
            results.append([new_tup])
        return results

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        """
        The first element of `other_inputs` is a tuple containing
        targets to use as the `player` of the given Verb. If
        # the tuple is empty, the chooser "failed to find" a target.
        # The Verb will not be applied to anything. Still may be ok.
        # If the tuple has many elements, the Verb must be able to
        # be performed on ALL of those players.
        """
        if not super().can_be_done(state, player, source, other_inputs):
            return False  # confirms other_inputs is long enough
        targets: Tuple[int] = other_inputs[0]
        if len(targets) == 0:
            # chooser failed to find a target. ok only if "allowed" to fail.
            return self.allowed_to_fail
        # must be able to perform the verb on ALL given targets
        return all([self.verb.can_be_done(state, t, source, other_inputs[1:])
                    for t in targets])

    def do_it(self, state: GameState, player, source, other_inputs,
              check_triggers=True):
        """
        The first element of `other_inputs` is a tuple containing
        targets to use as the `player` of the given Verb. If
        the tuple is empty, the chooser "failed to find" a target.
        The Verb will not be applied to anything. If the tuple has
        any elements, the Verb will attempt to perform itself on
        ALL of those players.
        """
        targets = other_inputs[0]
        if len(targets) == 0:
            # Failed to find target. If got this far, presumably failing is ok.
            # So do nothing. Call check_triggers if asked.
            if not self.copies:
                state2, things = state.copy_and_track([source] + other_inputs)
                res = (state2, player, things[0], things[1:])
            else:
                res = (state, player, source, other_inputs)
            return [self.check_triggers(*res)] if check_triggers else [res]
        else:
            if self.copies:
                state2, things = state.copy_and_track([source] + other_inputs)
                tuple_list = [(state2, player, things[0], things[1:])]
                for ii in range(len(targets)):
                    new_tuples = []
                    for st, _, srce, ins in tuple_list:
                        targ = ins[0][ii]
                        new_tuples += self.verb.do_it(st, targ, srce, ins[1:],
                                                      check_triggers=False)
                    tuple_list = new_tuples
                # "player" in tuple_list is wrong. retrieve true player
                result_list = [(st2, player, srce2, ins2)
                               for st2, pl2, srce2, ins2 in tuple_list]
            else:
                for target in targets:
                    self.verb.do_it(state, target, source, other_inputs[1:],
                                    check_triggers=False)
                result_list = [(state, player, source, other_inputs)]
            if check_triggers:
                return [self.check_triggers(*res) for res in result_list]
            else:
                return result_list

    def check_triggers(self, state: GameState, player: int,
                       source: Cardboard | None, other_inputs: INPUTS
                       ) -> RESULT:
        """Adds any new triggers to the super_stack. Also, shortens
        input argument list to "use up" this Verb's target(s).
        The first element of `other_inputs` is a tuple containing
        targets to use as the `player` of the given Verb. If
        the tuple is empty, the chooser "failed to find" a target.
        The Verb will not be applied to anything. If the tuple has
        any elements, the Verb will attempt to perform itself on
        ALL of those players.
        THIS FUNCTION ALWAYS MUTATES."""
        for t in other_inputs[0]:
            # check_triggers mutates state. no trim since verb takes 0 inputs.
            self.verb.check_triggers(state, t, source, other_inputs[1:])
        # check if THIS verb causes any triggers. returns with targets trimmed
        return Verb.check_triggers(self, state, player, source, other_inputs)

    def is_type(self, verb_type: type):
        return self.verb.is_type(verb_type)

    def __str__(self):
        return "%s(%s%s)" % (str(self.verb), str(self.chooser),
                             str(self.option_getter))


class Modal(Verb):
    """Choose between various Verbs. All _options should require
    the same number of inputs. Mode is chosen at cast-time,
    not on resolution."""

    def __init__(self, list_of_verbs: List[Verb],
                 num_to_choose: Get.Integer | int = 1, can_be_less=False):
        super().__init__(1 + num_to_choose * list_of_verbs[0].num_inputs,
                         any([v.copies for v in list_of_verbs]))
        assert (len(list_of_verbs) > 1)
        assert all([v.num_inputs == list_of_verbs[0].num_inputs
                    for v in list_of_verbs])
        self.sub_verbs = list_of_verbs
        if isinstance(num_to_choose, int):
            num_to_choose = Get.ConstInteger(num_to_choose)
        self.num_to_choose: Get.Integer = num_to_choose
        self.can_be_less: bool = can_be_less

    def get_input_options(self, state, player, source, cause
                          ) -> List[INPUTS]:
        # step 1: choose a verb or set of verbs
        possible = [(ii, str(v)) for ii, v in enumerate(self.sub_verbs)]
        num: int = self.num_to_choose.get(state, player, source)
        decider = state.player_list[player].decision_maker
        modes: List[Tuple[Tuple[int, str]]]
        if self.can_be_less:
            modes = Choices.choose_n_or_fewer(possible, num, setting=decider)
        else:
            if num == 1:
                modes = [(c,) for c in
                         Choices.choose_exactly_one(possible, setting=decider)]
            else:
                modes = Choices.choose_exactly_n(possible, num,
                                                 setting=decider)
        # step 2: for each chosen verb, return verb plus ITS required inputs
        choices: List[INPUTS] = []
        for set_of_verbs in modes:  # Tuple[Tuple[int, str]]
            verb_indices: Tuple[int] = tuple([ii for ii, ss in set_of_verbs])
            # use MultiVerb to figure out the actual inputs
            multi = MultiVerb([self.sub_verbs[ii] for ii in verb_indices])
            for sub_choice in multi.get_input_options(state, player,
                                                      source, cause):
                choices.append([tuple(verb_indices)] + sub_choice)
        return choices

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        """first element of other_inputs is the choice of which verbs to use"""
        multi = MultiVerb([self.sub_verbs[ii] for ii in other_inputs[0]])
        return multi.can_be_done(state, player, source, other_inputs)

    def do_it(self, state: GameState, player, source, other_inputs,
              check_triggers=True):
        """first element of other_inputs is the choice of which verb to use"""
        multi = MultiVerb([self.sub_verbs[ii] for ii in other_inputs[0]])
        res_list = multi.do_it(state, player, source, other_inputs[1:], False)
        if check_triggers:
            return [self.check_triggers(*res) for res in res_list]
        else:
            return res_list

    def check_triggers(self, state: GameState, player: int,
                       source: Cardboard | None, other_inputs: INPUTS
                       ) -> RESULT:
        """Adds any new triggers to the super_stack. Also, shortens
        input argument list to "use up" this Verb's selection of
        verb.  The 1st element of other_inputs is the choice of
        which verbs to perform.
        THIS FUNCTION ALWAYS MUTATES."""
        multi = MultiVerb([self.sub_verbs[ii] for ii in other_inputs[0]])
        multi.check_triggers(state, player, source, other_inputs[1:])
        # check if THIS verb causes any triggers. Trims.
        return Verb.check_triggers(self, state, player, source, other_inputs)

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
        """Returns EITHER a single element (the "cause" argument
        to this function, so that the sub-verb can run its own
        get_input_options function later on) OR a tuple of
        choices (as figured out during do_it)
        Saves the cause so that the sub-verb can run
        its own get_input_options function later on."""
        assert False  # deliberate error so that I remember this is broken
        return [[cause]]


    def do_it(self, state: GameState, player, source, other_inputs,
              check_triggers=True):
        cause = other_inputs[0]
        results = []
        if self.verb.copies:
            choices = self.verb.get_input_options(state, player, source, cause)
            for choice in choices:
                results += self.verb.do_it(state, player, source, choice,
                                           check_triggers=False)
        else:
            choices = self.verb.get_input_options(state, player, source, cause)
            for choice in choices:
                state2, things = state.copy_and_track([source] + choice)
                source2 = things[0]
                ch2 = things[1:]
                results += self.verb.do_it(state2, player, source2, ch2,
                                           check_triggers=False)
        if check_triggers:
            return [self.check_triggers(*res) for res in results]
        else:
            return results

    def check_triggers(self, state: GameState, player: int,
                       source: Cardboard | None, other_inputs: INPUTS
                       ) -> RESULT:
        """Adds any new triggers to the super_stack. Also, shortens
        input argument list to "use up" this Verb's selection of
        verb.  The 1st element of other_inputs is the choice of
        which verbs to perform.
        THIS FUNCTION ALWAYS MUTATES."""
        return self.verb.check_triggers(state, player, source, other_inputs)

    def is_type(self, verb_type: type):
        return self.verb.is_type(verb_type)

    def __str__(self):
        return str(self.verb)


# ----------

class VerbManyTimes(Verb):
    def __init__(self, verb: Verb, num_to_repeat: Get.Integer | int):
        """The number of times to repeat the verb is chosen on casting"""
        super().__init__(1 + verb.num_inputs, verb.copies)
        self.verb = verb
        if isinstance(num_to_repeat, int):
            num_to_repeat = Get.ConstInteger(num_to_repeat)
        self.num_to_repeat = num_to_repeat

    def get_input_options(self, state: GameState, player: int,
                          source: Cardboard | None, cause: Cardboard | None
                          ) -> List[INPUTS]:
        # number of times to repeat plus sub-verb's inputs
        n = self.num_to_repeat.get(state, player, source)
        return [n] + self.verb.get_input_options(state, player, source, cause)

    def can_be_done(self, state: GameState, player: int,
                    source: Cardboard | None, other_inputs: INPUTS) -> bool:
        """first element of input is number of times to repeat (int)."""
        return self.verb.can_be_done(state, player, source, other_inputs[1:])

    def do_it(self, state: GameState, player: int, source: Cardboard | None,
              other_inputs: INPUTS, check_triggers=True) -> List[RESULT]:
        """first element of input is number of times to repeat (int)."""
        num_to_repeat = other_inputs[0]
        if num_to_repeat == 0:
            if self.copies:
                game2, things = state.copy_and_track([source] + other_inputs)
                results = [(game2, player, things[0], things[2:])]  # trim num
            else:
                results = [(state, player, source, other_inputs[1:])]
        elif num_to_repeat == 1:
            results = self.verb.do_it(state, player, source, other_inputs[1:],
                                      check_triggers=False)
        else:
            # do a MultiVerb containing this verb repeated a bunch of times
            multi_verb = MultiVerb([self.verb] * num_to_repeat)
            new_inputs = other_inputs[1:self.num_inputs] * num_to_repeat
            new_inputs += other_inputs[self.num_inputs:]
            results = multi_verb.do_it(state, player, source, new_inputs,
                                       check_triggers=False)
        # add the num_to_repeat back in
        results = [(st3, pl3, srce3, [num_to_repeat] + ins3)
                   for st3, pl3, srce3, ins3 in results]
        if check_triggers:
            return [self.check_triggers(*res) for res in results]
        else:
            return results

    def check_triggers(self, state: GameState, player: int,
                       source: Cardboard | None, other_inputs: INPUTS
                       ) -> RESULT:
        """Adds any new triggers to the super_stack. Also, shortens
        input argument list to "use up" this Verb's selection of
        verb.  The 1st element of other_inputs is the choice of
        which verbs to perform.
        THIS FUNCTION ALWAYS MUTATES."""
        num_to_repeat = other_inputs[0]
        for _ in range(num_to_repeat):
            self.verb.check_triggers(state, player, source, other_inputs[1:])
        return Verb.check_triggers(self, state, player, source, other_inputs)

    def __str__(self):
        return str(self.verb) + " x " + str(self.num_to_repeat)


class LookDoThenDo(Verb):
    def __init__(self, look_at: Get.CardsFrom, choose: Get.AllWhich,
                 do_to_chosen: AffectSourceCard,
                 do_to_others: AffectSourceCard):
        super().__init__(2, ((not choose.single_output)
                             or do_to_chosen.copies or do_to_others.copies))
        self.option_getter: Get.CardsFrom = look_at
        self.chooser: Get.AllWhich = choose
        assert do_to_chosen.num_inputs == 0
        assert do_to_others.num_inputs == 0
        self.do_to_chosen: AffectSourceCard = do_to_chosen
        self.do_to_others: AffectSourceCard = do_to_others

    # noinspection PyTypeChecker
    def get_input_options(self, state: GameState, player: int,
                          source: Cardboard | None, cause: Cardboard | None
                          ) -> List[INPUTS]:
        """Two inputs: a tuple of chosen, and a tuple of non-chosen."""

        options = self.option_getter.get(state, player, source)
        choices = self.chooser.pick(options, state, player, source)
        # chooser gives list of tuples of cards.  Output should be a list of
        # lists of tuples, as [tup_chosen, tup_non_chosen]
        return [[chosen, tuple([c for c in options if c not in chosen])]
                for chosen in choices]

    def can_be_done(self, state: GameState, player: int,
                    source: Cardboard | None, other_inputs: INPUTS) -> bool:
        """First 2 inputs: a tuple of chosen, and a tuple of non-chosen."""
        if not super().can_be_done(state, player, source, other_inputs):
            return False
        chosen = other_inputs[0]
        unchosen = other_inputs[1]
        return (all([self.do_to_chosen.can_be_done(state, player, c)
                     for c in chosen])
                and all([self.do_to_others.can_be_done(state, player, c)
                         for c in unchosen]))

    def do_it(self, state: GameState, player: int, source: Cardboard | None,
              other_inputs: INPUTS, check_triggers=True) -> List[RESULT]:
        """First 2 inputs: a tuple of chosen, and a tuple of non-chosen."""
        chosen = other_inputs[0]
        unchosen = other_inputs[1]
        if self.copies:
            state2, concat2 = state.copy_and_track([source] + other_inputs)
            tuple_list = [(state2, player, concat2[0], concat2)]
        else:
            tuple_list = [(state, player, source, [source] + other_inputs)]
        # do the chosen ones first. keep all inputs. By assumption none are
        # used anyway, since AffectSourceCard, but inputs used for tracking.
        for ii in range(len(chosen)):
            new_list = []
            for st, pl, srce, ins in tuple_list:
                new_list += self.do_to_chosen.do_it(st, pl, ins[1][ii], ins,
                                                    check_triggers=False)
            tuple_list = new_list
        # now the non-chosen ones
        for jj in range(len(unchosen)):
            new_list = []
            for st, pl, srce, ins in tuple_list:
                new_list += self.do_to_others.do_it(st, pl, ins[2][jj], ins,
                                                    check_triggers=False)
            tuple_list = new_list
        # reset the source to be the original source
        tuple_list = [(st2, pl2, ins2[0], ins2[1:])
                      for st2, pl2, srce2, ins2 in tuple_list]
        # check triggers, or just return
        if check_triggers:
            return [self.check_triggers(*res) for res in tuple_list]
        else:
            return tuple_list

    def check_triggers(self, state: GameState, player: int,
                       source: Cardboard | None, other_inputs: INPUTS
                       ) -> RESULT:
        """Adds any new triggers to the super_stack. Also, shortens
        input argument list to "use up" this Verb's subject and any
        other inputs.
        First 2 inputs: a tuple of chosen, and a tuple of non-chosen.
        THIS FUNCTION ALWAYS MUTATES."""
        for chosen_card in other_inputs[0]:
            self.do_to_chosen.check_triggers(state, player, chosen_card, [])
        for unchosen_card in other_inputs[1]:
            self.do_to_others.check_triggers(state, player, unchosen_card, [])
        # check if THIS verb causes any triggers. strip off inputs and return
        return Verb.check_triggers(self, state, player, source, other_inputs)

    def __str__(self):
        act_yes = str(self.do_to_chosen)
        choose = str(self.chooser)
        options = str(self.option_getter)
        act_no = str(self.do_to_others)
        s = "%s on %s%s else %s" % (act_yes, choose, options, act_no)
        return s


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
        return [[]]

    def do_it(self, state: GameState, player, source, other_inputs,
              check_triggers=True):
        return [(state, player, source, other_inputs)]

    def check_triggers(self, state: GameState, player: int,
                       source: Cardboard | None, other_inputs: INPUTS
                       ) -> RESULT:
        return state, player, source, other_inputs

    def add_self_to_state_history(self, state, player, source,
                                  other_inputs):
        return

    def __str__(self):
        return ""


class PayMana(AffectPlayer):
    """deducts the given amount of mana from the Player's
    mana pool."""

    def __init__(self, mana_string: Get.String | str):
        super().__init__()
        if isinstance(mana_string, str):
            mana_string = Get.ConstString(mana_string)
        self.string_getter: Get.String = mana_string

    def can_be_done(self, state, player, source, other_inputs=[]) -> bool:
        if not super().can_be_done(state, player, source, other_inputs):
            return False
        mana_str = self.string_getter.get(state, player, source)
        pool = state.player_list[player].pool
        return pool.can_afford_mana_cost(ManaHandler.ManaCost(mana_str))

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        mana_str = self.string_getter.get(state, player, source)
        pool = state.player_list[player].pool
        pool.pay_mana_cost(ManaHandler.ManaCost(mana_str))
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def __str__(self):
        return "PayMana{%s}" % str(self.string_getter)

    def add_self_to_state_history(self, state: GameState, player,
                                  source, other_inputs: Player):
        if state.is_tracking_history:
            cost = ManaHandler.ManaCost(
                self.string_getter.get(state, player, source))
            text = "\nPay %s" % str(cost)
            state.events_since_previous += text


class AddMana(AffectPlayer):
    """adds the given amount of mana to the player's mana pool"""

    def __init__(self, mana_string: Get.String | str):
        super().__init__()
        if isinstance(mana_string, str):
            mana_string = Get.ConstString(mana_string)
        self.string_getter: Get.String = mana_string

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        mana_str = self.string_getter.get(state, player, source)
        pool = state.player_list[player].pool
        pool.add_mana(ManaHandler.ManaPool(mana_str))
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        if state.is_tracking_history:
            pool = ManaHandler.ManaPool(
                self.string_getter.get(state, player, source))
            text = "\nAdd %s" % str(pool)
            state.events_since_previous += text


class LoseLife(AffectPlayer):
    def __init__(self, damage_getter: Get.Integer | int):
        """The subject player loses the given amount of life"""
        super().__init__()
        if isinstance(damage_getter, int):
            damage_getter = Get.ConstInteger(damage_getter)
        self.damage_getter: Get.Integer = damage_getter

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        pl = state.player_list[player]
        pl.life -= self.damage_getter.get(state, player, source)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        if state.is_tracking_history:
            text = "\nLose %i life" % self.damage_getter.get(state, player,
                                                             source)
            state.events_since_previous += text


class GainLife(AffectPlayer):
    def __init__(self, amount_getter: Get.Integer | int):
        """The subject player gains the given amount of life"""
        super().__init__()
        if isinstance(amount_getter, int):
            amount_getter = Get.ConstInteger(amount_getter)
        self.amount_getter: Get.Integer = amount_getter

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        pl = state.player_list[player]
        pl.life += self.amount_getter.get(state, player, source)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        if state.is_tracking_history:
            text = "\nLose %i life" % self.amount_getter.get(state, player,
                                                             source)
            state.events_since_previous += text


class DamageToPlayer(AffectPlayer):
    def __init__(self, damage: Get.Integer | int):
        """The subject asking_player gains the given amount of life"""
        super().__init__(1)
        # if isinstance(amount_getter, int):
        #     amount_getter = Get.ConstInteger(amount_getter)
        self.damage: Get.Integer | int = damage

    def get_input_options(self, state: GameState, player: int,
                          source: Cardboard | None, cause: Cardboard | None
                          ) -> List[INPUTS]:
        """Input is amount of damage to deal. It is an int if the
        damage is known for sure, otherwise it is None (to calculate
        at resolution)."""
        if isinstance(self.damage, int):
            return [[self.damage]]
        else:
            return [[None]]  # placeholder 

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        damage = other_inputs[0]
        if other_inputs[0] is None:
            damage = self.damage.get(state, player, source)  # use getter
            other_inputs = [damage] + other_inputs[1:]
        LoseLife(damage).do_it(state, player, source, [], False)
        index = source.player_index
        if "lifelink" in Get.Keywords().get(state, index, source):
            GainLife(damage).do_it(state, index, source, [], False)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def check_triggers(self, state: GameState, player: int,
                       source: Cardboard | None, other_inputs: INPUTS
                       ) -> RESULT:
        damage = other_inputs[0]
        assert damage is not None  # debug. value should be locked in by here.
        LoseLife(damage).check_triggers(state, player, source, [])
        index = source.player_index
        if "lifelink" in Get.Keywords().get(state, index, source):
            GainLife(damage).check_triggers(state, index, source, [])
        # trim and return the trimmed version
        return Verb.check_triggers(self, state, player, source, other_inputs)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        if state.is_tracking_history:
            value = other_inputs[0]
            if other_inputs[0] is None:
                value = self.damage.get(state, player, source)  # use getter
            text = "\n%s dealt %i damage to player%i" % (str(source), value,
                                                         player)
            state.events_since_previous += text


class LoseTheGame(AffectPlayer):

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        state.player_list[player].victory_status = "L"
        # if everyone else has lost, the last player standing wins!
        still_playing = [pl for pl in state.player_list
                         if pl.victory_status == ""]
        if len(still_playing) == 1:
            # I'm gonna cheat and always check triggers for winning, losing.
            WinTheGame().do_it(state, still_playing[0].player_index, None, [],
                               True)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        if state.is_tracking_history:
            text = "\nPlayer %i loses the game!" % player
            state.events_since_previous += text


class WinTheGame(AffectPlayer):

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        state.player_list[player].victory_status = "W"
        # all other players automatically lose
        for pl in state.player_list:
            # I'm gonna cheat and always check triggers for winning, losing.
            if pl.victory_status == "":
                LoseTheGame().do_it(state, pl.player_index, None, [], True)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        if state.is_tracking_history:
            text = "\nPlayer %i wins the game!" % player
            state.events_since_previous += text


# ----------

class Tap(AffectSourceCard):
    """taps the source card if it was not already tapped."""

    def can_be_done(self, state, player, source, other_inputs=[]):
        return (super().can_be_done(state, player, source, other_inputs)
                and source.is_in(Zone.Field) and not source.tapped)

    def do_it(self, state: GameState, player, source, other_inputs,
              check_triggers=True):
        source.tapped = True
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)


class Untap(AffectSourceCard):
    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, player, source,
                    other_inputs=[]) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and source.tapped and source.is_in(Zone.Field))

    def do_it(self, state: GameState, player, source, other_inputs,
              check_triggers=True):
        source.tapped = False
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)


class AddCounter(AffectSourceCard):
    """Adds the given counter string to the subject card"""

    def __init__(self, counter_text: str):
        super().__init__()
        self.counter_text = counter_text

    def can_be_done(self, state: GameState, player, source,
                    other_inputs=[]) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and source.is_in(Zone.Field))

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        source.add_counter(self.counter_text)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

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

    def can_be_done(self, state, player, source, other_inputs=[]) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and source.is_in(Zone.Field)
                and self.counter_text not in source.counters)

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        source.add_counter(self.counter_text)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        return  # doesn't mark itself as having done anything


class ActivateOnlyAsSorcery(Verb):
    """Checks that the stack is empty and the asking_player has
     priority. Otherwise, can_be_done will return False."""

    def can_be_done(self, state, player, source, other_inputs) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and len(state.stack) == 0 and len(state.super_stack) == 0
                and state.active_player_index == player)

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        return  # doesn't mark itself as having done anything


class Shuffle(AffectPlayer):
    """Shuffles the deck of given player."""

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        """Mutates. Reorder deck randomly."""
        random.shuffle(state.player_list[player].deck)
        for ii in range(len(state.player_list[player].deck)):
            state.player_list[player].deck[ii].zone.location = ii
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        if state.is_tracking_history:
            state.events_since_previous += "\nShuffle"


class MoveToZone(AffectSourceCard):
    """Moves the subject card to the given zone.
    NOTE: cannot actually remove the subject card from the
    stack (because it's wrapped in a StackObject).
    NOTE: cannot actually add the subject card to the stack
    (because it's wrapped in a StackObject).
    In both of these cases, the function does as much of the
    move as it can (sets Cardboard.zone, removes even if it
    can't add, etc.) and hopes that the calling function will
    know to do the rest.
    """

    def __init__(self, destination_zone: Zone.Zone):
        super().__init__(2)
        self._destination: Zone.Zone = destination_zone

    def get_input_options(self, state: GameState, player: int,
                          source, cause) -> List[INPUTS]:
        """Two inputs: origin and destination. Both are None
        initially, since origin isn't known until do_it and
        destination might still be a relative location instead
        of an absolute location. They will be filled in as
        absolute locations during do_it and used for checking
        if the movement triggered anything."""
        return [[None, None]]

    def can_be_done(self, state, player, source, other_inputs=[None, None]):
        if not super().can_be_done(state, player, source, other_inputs):
            return False
        if not source.zone.is_fixed or self._destination.is_single:
            # origin zone and destination zone must be clear locations
            print("dest zone not specified!", state, player, source)  # debug
            return False
        if not source.is_in(Zone.Stack) and not source.is_in(Zone.Unknown):
            return source in source.zone.get(state)  # is where supposed to be
        else:
            return True

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        # figure out absolute origin and destination zone
        dest = self._destination
        if not dest.is_single:
            zone_list = dest.get_absolute_zones(state, player, source)
            if len(zone_list) != 1:
                raise Zone.Zone.NotSpecificPlayerError
            dest = zone_list[0]
        origin = source.zone.copy()
        other_inputs = [origin, dest] + other_inputs[2:]
        # NOTE: Zone handles whether the Cardboard is actually added or pulled
        # from the zone (e.g. for the Stack). Don't worry about that here.
        origin.remove_from_zone(state, source)
        # add to destination. (also resets source's zone to be destination.)
        dest.add_to_zone(state, source)
        source.reset_to_default_cardboard()
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    @property
    def destination(self) -> Zone.Zone:
        return self._destination

    def __str__(self):
        return "MoveTo" + str(self._destination)


class DrawCard(AffectPlayer):
    """The player draws from the top (index -1) of the deck"""

    def can_be_done(self, state, player, source, other_inputs=[]) -> bool:
        # Even if the deck is empty, you CAN draw. you'll just lose.
        return super().can_be_done(state, player, source, other_inputs)

    def do_it(self, state, player: int, source, other_inputs,
              check_triggers=True):
        top_card_list = Zone.DeckTop(player).get(state)
        if len(top_card_list) > 0:
            mover = MoveToZone(Zone.Hand(player))
            # move the card using MoveToZone.
            # I'm going to cheat and never proc move-from-deck-to-hand triggers
            mover.do_it(state, player, top_card_list[0], [], False)
        else:
            state.player_list[player].victory_status = "L"
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)


class MarkAsPlayedLand(AffectPlayer):
    """Doesn't actually move any cards, just toggles the
    gamestate to say that the asking_player of `subject` has
    played a land this turn"""

    def can_be_done(self, state, player, source, other_inputs=[]) -> bool:
        return state.player_list[player].land_drops_left > 0

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        state.player_list[player].num_lands_played += 1
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, player, source, other_inputs,
                          check_triggers)

    def add_self_to_state_history(self, state, player, source, other_inputs):
        return

# old version. subclass of AffectSourceCard, not of MoveToZone
# class Sacrifice(AffectSourceCard):
#     def can_be_done(self, state, player, source: Cardboard,
#                     other_inputs=[]) -> bool:
#         return (super().can_be_done(state, player, source, other_inputs)
#                 and source.is_in(Zone.Field))
#
#     def do_it(self, state, player, source, other_inputs, check_triggers=True):
#         mover = MoveToZone(Zone.Grave(source.owner_index))
#         mover.do_it(state, player, source, [None, None], False)
#         # add history. maybe check_triggers (add to super_stack, trim inputs)
#         return Verb.do_it(self, state, player, source, other_inputs,
#                           check_triggers)
#
#     def check_triggers(self, state: GameState, player: int,
#                        source: Cardboard | None, other_inputs: INPUTS
#                        ) -> RESULT:
#         # sacrifice is always from field to grave
#         origin = Zone.Field(source.player_index)
#         destination = Zone.Grave(source.owner_index)
#         assert source.player_index == source.owner_index  # bug w/ stealing
#         mover = MoveToZone(destination)
#         mover.check_triggers(state, player, source, [origin, destination])
#         return super().check_triggers(state, player, source, other_inputs)


class Sacrifice(MoveToZone):
    def __init__(self):
        super().__init__(Zone.Grave(Get.Owners()))

    def can_be_done(self, state, player, source: Cardboard,
                    other_inputs=[]) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and source.is_in(Zone.Field)
                and player == source.player_index )

    def __str__(self):
        return "Sacrifice"

# old version. subclass of AffectSourceCard, not of MoveToZone
# class Destroy(AffectSourceCard):
#     def can_be_done(self, state, player, source: Cardboard,
#                     other_inputs=[]) -> bool:
#         # allowed to attempt even if indestructible
#         return (super().can_be_done(state, player, source, other_inputs)
#                 and source.is_in(Zone.Field))
#
#     def do_it(self, state, player, source, other_inputs, check_triggers=True):
#         if not Match.Keyword("indestructible").match(source, state, player,
#                                                      source):
#             mover = MoveToZone(Zone.Grave(source.owner_index))
#             mover.do_it(state, player, source, [None, None], False)
#         # add history. maybe check_triggers (add to super_stack, trim inputs)
#         return Verb.do_it(self, state, player, source, other_inputs,
#                           check_triggers)
#
#     def check_triggers(self, state: GameState, player: int,
#                        source: Cardboard | None, other_inputs: INPUTS
#                        ) -> RESULT:
#         # destroy is always from field to grave
#         origin = Zone.Field(source.player_index)
#         destination = Zone.Grave(source.owner_index)
#         assert source.player_index == source.owner_index  # bug w/ stealing
#         mover = MoveToZone(destination)
#         mover.check_triggers(state, player, source, [origin, destination])
#         return super().check_triggers(state, player, source, other_inputs)


class Destroy(MoveToZone):
    def __init__(self):
        super().__init__(Zone.Grave(Get.Owners()))

    def can_be_done(self, state, player, source: Cardboard,
                    other_inputs=[]) -> bool:
        return (super().can_be_done(state, player, source, other_inputs)
                and source.is_in(Zone.Field)
                and player == source.player_index )

    def do_it(self, state, player, source, other_inputs, check_triggers=True):
        if Match.Keyword("indestructible").match(source, state,
                                                 player, source):
            if check_triggers:
                return [(state, player, source, other_inputs[2:])]
            else:
                return [(state, player, source, other_inputs)]
        else:
            return super().do_it(state, player, source, other_inputs,
                                 check_triggers)

    def check_triggers(self, state, player, source, other_inputs) -> RESULT:
        if Match.Keyword("indestructible").match(source, state,
                                                 player, source):
            return state, player, source, other_inputs[2:]
        else:
            return super().check_triggers(state, player, source, other_inputs)

    def __str__(self):
        return "Destroy"

# ----------


class SearchDeck(AffectPlayer):
    def __init__(self, zone_to_move_to: Zone.Zone, num_to_find: int,
                 pattern: Match.Pattern):
        super().__init__()
        self.chooser = Get.Chooser(pattern, num_to_find, can_be_fewer=True)
        self.destination: Zone.Zone = zone_to_move_to

    def do_it(self, state: GameState, player: int, source: Cardboard | None,
              other_inputs: INPUTS, check_triggers=True) -> List[RESULT]:
        decklist = Get.CardsFrom(Zone.Deck(player, None))
        mover_list = [MoveToZone(z) for z in
                      self.destination.get_absolute_zones(state, player,
                                                          source)]
        assert len(mover_list) == 1  # debug
        mover: MoveToZone = mover_list[0]
        # noinspection PyTypeChecker
        do_er = LookDoThenDo(decklist, self.chooser, mover, NullVerb)
        return do_er.do_it(state, player, source, other_inputs, check_triggers)


class SearchDeck(AffectPlayer):
    def __init__(self, zone_to_move_to: Zone.Zone, num_to_find: int,
                 pattern: Match.Pattern):
        self.chooser = Get.Chooser(pattern, num_to_find, can_be_fewer=True)
        self.destination: Zone.Zone = zone_to_move_to
        super().__init__()
        self.copies = True

    def do_it(self, state: GameState, player: int, source: Cardboard | None,
              other_inputs: INPUTS, check_triggers=True) -> List[RESULT]:
        mover_list = [MoveToZone(z) for z in
                      self.destination.get_absolute_zones(state,
                                                          player, source)]
        assert len(mover_list) == 1  # debug
        mover: MoveToZone = mover_list[0]
        # search the deck
        decklist = Get.CardsFrom(Zone.Deck(player, None))
        # find cards and move them to proper zone!
        res_list = []
        for choice in self.chooser.pick(decklist, state, player, source):
            things = [source] + list(choice) + other_inputs
            state2, things2 = state.copy_and_track(things)
            source2 = things2[0]
            choice2 = things2[1:len(choice) + 1]
            inputs2 = things2[len(choice) + 1:]
            for card in choice2:
                mover.do_it(state2, player, card, [])
            res_list += super().do_it(state2, player, source2, inputs2)
        return res_list


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
        obj: StackObject = other_inputs[0]  # other_inputs should be len 1
        num_payments = 0
        if obj.cost is not None:
            num_payments = obj.cost.num_inputs
        # pay_choices = obj.choices[1:num_payments + 1]
        # target_choices = obj.choices[1 + num_payments:]
        pay_choices = obj.choices[:num_payments]
        target_choices = obj.choices[num_payments:]
        return ((obj.cost is None
                 or obj.cost.can_afford(state, player, source, pay_choices))
                and (source.effect is None
                     or source.effect.can_be_done(state, player, source,
                                                  target_choices)))

    def do_it(self, state: GameState, player, source, other_inputs,
              check_triggers=True):
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
            num_payments = obj2.cost.num_inputs
            pay_choices = obj2.choices[:num_payments] + [obj2]
            # keep only the targets.
            obj2.choices = obj2.choices[num_payments:]
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
            record = "\n*** %s %s ***" % (str(self), other_inputs[0].name)
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
              other_inputs: List[StackTrigger], check_triggers=True):
        """Put the StackObject onto the stack, paying any
        necessary costs. Bypass the stack if necessary.
        Assumes that the triggered ability has already
        been removed from the super_stack by others."""
        # check to make sure the execution is legal
        if not self.can_be_done(state, player, source, other_inputs):
            return []
        # 601.2a: add the spell to the stack
        trig: StackTrigger = other_inputs[0]
        targets = [[]]
        if trig.effect is not None:
            targets = trig.effect.get_input_options(state, player,
                                                    trig.source_card,
                                                    trig.cause)
        # now have targets for the trigger, so can make StackAbility for it
        final_results = []
        for choices in targets:
            abil = Stack.StackAbility(trig.player_index, trig.source_card,
                                      trig.obj, choices, NullVerb())
            state2, [abil2] = state.copy_and_track([abil])
            state2.stack.append(abil2)
            # if necessary, the object will now instantly resolve. We are
            # guaranteed that the object is be the latest item on the stack
            # since triggers go to SUPER-stack.
            new_tuple_list = self._remove_if_needed(state2, player,
                                                    abil2.source_card, [abil2])
            # 601.2i: ability has now "been activated".  Add any triggers
            # that trigger off of this trigger itself.
            for st, pl, srce, ins in new_tuple_list:
                final_results += Verb.do_it(self, st, pl, srce, ins,
                                            check_triggers)
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
            inputs = stack_obj.choices + obj_as_input
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
        MoveToZone(Zone.Stack()).do_it(game, obj.player_index, obj.obj, )
        # for a StackCardboard, obj.source_card and obj.obj are pointers to
        # the same thing. Thus, moving either of them is sufficient.
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
        assert stack_obj.obj.is_in(Zone.Stack)
        # move the land to the `player`'s field instantly
        mover = MoveToZone(Zone.Field(player))
        mover.do_it(game, stack_obj.player_index, stack_obj.obj, [])
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
        has_flash = Match.Keyword("flash").match(card, state, player, card)
        return doable and (stack_empty or has_flash)


# ----------
class PlayPermanent(PlayCardboard):
    def can_be_done(self, state, player, source, other_inputs) -> bool:
        doable = super().can_be_done(state, player, source, other_inputs)
        stack_empty = len(state.stack) == 0
        card = other_inputs[0].obj
        has_flash = Match.Keyword("flash").match(card, state, player, card)
        return doable and (stack_empty or has_flash)
