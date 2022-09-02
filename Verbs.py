# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING, Tuple, TypeVar
import random

if TYPE_CHECKING:
    from GameState import GameState, Player
    from Cardboard import Cardboard
    from Stack import StackObject, StackCardboard
    import Zone
    from Getters import Getter

    # SOURCE = Cardboard | Player
    CAUSE = Cardboard | Player | None
    INPUTS = List[int | Cardboard | StackObject | None | Zone.Zone | Getter |
                  Tuple[int | Cardboard | StackObject | None]]

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
    NOTE: VERBS ARE NOT ALLOWED TO MUTATE AFTER CREATION.
    If you want to mutate a verb, just return a fresh copy
    with the new info.

    Expected flow for a verb:
      - It will be initiated
      - It will create populated Verb (`populate_options`) with
            filled-in inputs. The new Verbs are used for the next
            steps, the original Verb goes no further.
      - The Verb is checked for legality (`can_be_done`). It will
            only be asked to perform if it can legally do so.
      - The Verb is performed (`do_it`). In the process, it returns
            new Verbs whose inputs describe what ACTUALLY was done.
            These new Verbs are used in the next steps
      - A record of this Verb is added to the game's history
      - Triggered abilities are checked (`check_triggers`) to see
            if the performance of this Verb caused any abilities
            to trigger.
    """

    def __init__(self, num_inputs: int, copies: bool):
        self.num_inputs: int = num_inputs
        self.copies: bool = copies  # returns copies of GameStates, not mutate.

        # self.subject: int | Cardboard | None = None  # thing to apply Verb to
        self._source: Cardboard | None = None  # card saying to do the verb
        self._player: int | None = None  # player doing the Verb
        self._cause: Cardboard | None = None  # reason why doing Verb NOW
        self._subject: Cardboard | int | StackObject | None = None  # apply to.
        self._sub_verbs: List[Verb] = []  # space for subclasses to grow
        self._inputs: list = []  # space for subclasses to grow

    @property
    def source(self):
        return self._source

    @property
    def player(self):
        return self._player

    @property
    def cause(self):
        return self._cause

    @property
    def subject(self):
        return self._subject

    @property
    def sub_verbs(self):
        return self._sub_verbs

    @property
    def inputs(self):
        return self._inputs

    def copy(self: V, state_new: GameState | None = None) -> V:
        """
        Build a copy of this Verb. If the new GameState is not
        None, then any pointers to Cardboards are updated to
        point to the corresponding Cardboard in the new state.
        Otherwise, the new copy will have the same pointers as
        the old copy.
        """
        new_verb = Verb(self.num_inputs, self.copies)
        if state_new is None:
            new_verb._source = self._source
            new_verb._cause = self._cause
            new_verb._subject = self._subject
            # new list, same contents
            new_verb._inputs = self._inputs[:]
        else:
            new_verb._source = (None if self._source is None
                                else self._source.copy_as_pointer(state_new))
            new_verb._cause = (None if self._cause is None
                               else self._cause.copy_as_pointer(state_new))
            ins = state_new.copy_arbitrary_list(state_new, self._inputs)
            new_verb._inputs = ins
            if self.subject is None:
                new_verb._subject = None
            elif isinstance(self._subject, Stack.StackObject):
                new_verb._subject = self._subject.copy(state_new)
            else:  # Cardboard
                new_verb._subject = self._subject.copy_as_pointer(state_new)
        new_verb._sub_verbs = [v.copy(state_new) for v in self._sub_verbs]
        new_verb._player = self._player  # None and int are both atomic
        new_verb.__class__ = self.__class__  # set the sub-class type directly
        return new_verb

    def replace_verb(self: V, index: int, new_verb: Verb) -> V:
        """Returns a copy of self where the sub_verb at index
        `index` has been replaced with the given new verb.
        If `index` equals the list of subverbs, instead appends
        the new verb (so that it will end up at the expected
        index).
        If the item at that index is already new_value, don't
        copy. Just return self."""
        if index < len(self.sub_verbs):  # can index into list
            if self._sub_verbs[index] is new_verb:
                return self
            else:
                cp = self.copy()
                cp._sub_verbs[index] = new_verb
                return cp
        elif index == len(self._sub_verbs):
            cp = self.copy()
            cp._sub_verbs.append(new_verb)
            return cp
        else:
            raise IndexError

    def replace_input(self: V, index: int, new_value) -> V:
        """Returns a copy of self where the input at index `index`
        has been replaced with the given new input value.
        If `index` equals the list of inputs, instead appends
        the new value (so that it will end up at the expected
        index).
        If the item at that index is already new_value, don't
        copy. Just return self."""
        if index < len(self._inputs):  # can index into list
            if self._inputs[index] is new_value:
                return self
            else:
                cp = self.copy()
                cp._inputs[index] = new_value
                return cp
        elif index == len(self._inputs):
            cp = self.copy()
            cp._inputs.append(new_value)
            return cp
        else:
            raise IndexError

    def replace_subject(self: V, new_subject: Cardboard | int | StackObject
                        ) -> V:
        """Returns a copy of the verb but with a new subject."""
        new_verb = self.copy()
        new_verb._subject = new_subject
        return new_verb

    def populate_options(self, state: GameState, player: int,
                         source: Cardboard | None, cause: Cardboard | None
                         ) -> List[Verb]:
        """
        Return copies of this Verb but with filled-in parameters,
        each representing a set of choices for how to carry out
        this Verb.
        Note that the returned Verbs may not actually be possile
        to execute, in practice. Checking validity is what
        `can_be_done` is for.
        The version in Verb doesn't affect inputs, subverbs, or subject.
        """
        new_verb = self.copy()
        new_verb._player = player
        new_verb._source = source
        new_verb._cause = cause
        return [new_verb]

    def can_be_done(self, state: GameState) -> bool:
        """
        Returns whether this Verb can be done, given the current
        GameState and the fields of the Verb that are filled in.
        """
        # note: parent class doesn't care about subject or cause
        return (self.player is not None
                and self.source is not None
                and all([v.can_be_done(state) for v in self.sub_verbs])
                and len(self.inputs) == self.num_inputs
                )

    def do_it(self: V, state: GameState, to_track: list = [],
              check_triggers=True) -> List[RESULT]:
        """
        Carries out the Verb.
        Returns the new GameState where the Verb has been done,
            plus the Verb that was just done. The Verb may have
            been updated to reflect the actual performance, in
            which case it will be a fresh copy instead of the
            same object.
        If `copies`, returns fresh GameState to avoid mutating
            the input GameState. If `copies` is False, then just
            mutates it and returns the mutated object.
        If `check_triggers`, calls check_triggers to add any new
            triggers to the super_stack of the result states. If
            not, the user is responsible for calling it later.
         """
        # the parent class doesn't actually DO anything. that'll be added
        # in subclasses. This only records, possibly tracks triggers, and
        # handles track-list
        # This parent class function always mutates, as though copies=False.
        self.add_self_to_state_history(state)
        if check_triggers:
            return [self.check_triggers(state, to_track)]
        else:
            return [(state, self, to_track)]

    def check_triggers(self: V, state: GameState, to_track: list = []
                       ) -> RESULT:
        """
        Adds any new triggers to the super_stack. THIS ALWAYS
        MUTATES THE GAMESTATE. Also adds any triggers coming
        from the verb's sub_verbs.
        Note: doesn't DO anything with `to_track` argument.
        But passing it in and back out again makes the syntax
        cleaner for using the function in `do_it` and loops.
        """
        # `trigger_source` is the card which owns the triggered ability which
        # might be triggering. Not to be confused with `subject`, which is the
        # cause of the Verb which is potentially CAUSING the trigger.
        for trigger_source, ability in state.trig_event + state.trig_to_remove:
            # add any abilities that trigger to the super_stack
            ability.add_any_to_super(state, trigger_source, self)
        for v in self.sub_verbs:
            v.check_triggers(state, to_track)
        return state, self, to_track

    def is_type(self, verb_type: type) -> bool:
        return isinstance(self, verb_type)

    def __add__(self, other) -> MultiVerb:
        return MultiVerb([self, other])

    # def __or__

    def __str__(self):
        return type(self).__name__

    def get_id(self):
        txt = str(self)
        txt += "(%s, %s, %s)" % (str(self.player), str(self.source),
                                 str(self.cause))
        if len(self.inputs) > 0:
            txt += "(%s)" % (", ".join([str(i) for i in self.inputs]))
        if len(self.sub_verbs) > 0:
            txt += "(%s)" % (", ".join([v.get_id() for v in self.sub_verbs]))
        return txt

    def add_self_to_state_history(self, state: GameState) -> None:
        """If the GameState is tracking history, adds a note
        to that history describing this Verb. Mutates state,
        technically, in that note is added rather than added
        to a copy."""
        if state.is_tracking_history:
            record = "\n%s %s" % (str(self), self.source.name)
            state.events_since_previous += record


if TYPE_CHECKING:
    V = TypeVar("V", bound=Verb)
    RESULT = Tuple[GameState, Verb, list]


class MultiVerb(Verb):

    def __init__(self, list_of_verbs: List[Verb]):
        self._sub_verbs = list_of_verbs
        # unpack any nested MultiVerbs and combine them into this one.
        ii = 0
        while ii < len(self.sub_verbs):
            if isinstance(self.sub_verbs[ii], MultiVerb):
                before = self.sub_verbs[:ii]
                middle = self.sub_verbs[ii].sub_verbs
                after = self.sub_verbs[ii + 1:]
                self._sub_verbs = before + middle + after
            else:
                ii += 1
        # figure out whether it copies or not based on sub_verbs.
        super().__init__(0, any([v.copies for v in self.sub_verbs]))

    def populate_options(self: V, state, player, source, cause
                         ) -> List[V]:
        # fill in basic info for this multi-verb and its sub_verbs
        [base] = Verb.populate_options(self, state, player, source, cause)
        options = [base]
        # still need subjects,
        for ii, v in enumerate(self.sub_verbs):
            new_opts = []
            for populated in v.populate_options(state, player, source, cause):
                new_opts += [b.replace_verb(ii, populated) for b in options]
            options = new_opts
        return options

    def can_be_done(self, state) -> bool:
        return (super().can_be_done(state)
                and all([v.can_be_done(state) for v in self.sub_verbs]))

    def do_it(self, state, to_track=[], check_triggers=True):
        tuple_list = [(state, self, to_track)]  # GameState, MultiVerb, list
        for ii in range(len(self.sub_verbs)):
            new_tuple_list = []
            for st, multi, trk in tuple_list:
                sub = multi.sub_verbs[ii]
                for st2, sub2, things2 in sub.do_it(st, [multi] + trk, False):
                    multi2 = things2[0].replace_verb(ii, sub2)
                    track2 = things2[1:]
                    new_tuple_list.append((st2, multi2, track2))
            tuple_list = new_tuple_list
        if check_triggers:
            return [multi3.check_triggers(st3, trk3)
                    for st3, multi3, trk3 in tuple_list]
        else:
            return tuple_list

    def is_type(self, verb_type: type):
        return any([v.is_type(verb_type) for v in self.sub_verbs])

    def __str__(self):
        return " & ".join([v.__str__() for v in self.sub_verbs])

    def get_id(self):
        return " & ".join([v.get_id() for v in self.sub_verbs])


class VerbFactory(Verb):
    """For verbs that hold a lot of infrastructure for choosing
    which subverbs to use, but which boil down into being a
    MultiVerb once those are chosen. This isn't a subclass of
    MultiVerb, it just returns them during `populate_options`."""

    class ShouldNeverBeRunError(Exception):
        pass

    def populate_options(self, state, player, source, cause
                         ) -> List[MultiVerb]:
        raise NotImplementedError

    def can_be_done(self, state: GameState) -> bool:
        """populating returns MultiVerbs, so this should never be run"""
        raise VerbFactory.ShouldNeverBeRunError

    def do_it(self, state: GameState, to_track=[], check_triggers=True):
        """populating returns MultiVerbs, so this should never be run"""
        raise VerbFactory.ShouldNeverBeRunError

    def check_triggers(self: V, state, to_track: list = []) -> RESULT:
        """populating returns MultiVerbs, so this should never be run"""
        raise VerbFactory.ShouldNeverBeRunError


class AffectPlayer(Verb):
    """An atomic verb which affects a player. By default,
     the affected card is the controller of the Verb, but
     this can be overwritten."""

    def __init__(self, num_inputs=0):
        super().__init__(num_inputs, False)  # mutates, doesn't copy

    def can_be_done(self, state: GameState) -> bool:
        return super().can_be_done(state) and isinstance(self.subject, int)

    def populate_options(self: V, state, player, source, cause) -> List[V]:
        baselist = super().populate_options(state, player, source, cause)
        return [v.replace_subject(player) for v in baselist]

    def on(self,
           subject_chooser: Get.AllWhich,
           option_getter: Get.PlayerList,
           allowed_to_fail: bool = True) -> ApplyToTargets:
        return ApplyToTargets(subject_chooser, option_getter,
                              self, allowed_to_fail)


class AffectCard(Verb):
    """An atomic verb which affects a card. By default,
     the affected card is the source of the Verb, but
     this can be overwritten."""

    def __init__(self, num_inputs=0):
        super().__init__(num_inputs, False)  # mutates, doesn't copy

    def can_be_done(self, state: GameState) -> bool:
        return (super().can_be_done(state)
                and isinstance(self.subject, Cardboard))

    def populate_options(self, state, player, source, cause):
        baselist = super().populate_options(state, player, source, cause)
        return [v.replace_subject(source) for v in baselist]

    def on(self,
           subject_chooser: Get.AllWhich,
           option_getter: Get.CardsFrom,
           allowed_to_fail: bool = True) -> ApplyToTargets:
        return ApplyToTargets(subject_chooser, option_getter,
                              self, allowed_to_fail)


class AffectStack(Verb):
    """An atomic verb which affects a StackObject. The
    StackObject must be passed in as an additional option
    to `populate_options`, or set manually by the user."""

    def __init__(self, num_inputs=0, copies=False):
        super().__init__(num_inputs, copies)  # mutates, doesn't copy

    def can_be_done(self, state: GameState) -> bool:
        return (super().can_be_done(state)
                and isinstance(self.subject, StackObject))

    def populate_options(self, state: GameState, player: int,
                         source: Cardboard | None, cause: Cardboard | None,
                         stack_object: StackObject | None = None
                         ) -> List[Verb]:
        baselist = super().populate_options(state, player, source, cause)
        return [v.replace_subject(stack_object) for v in baselist]

    def on(self,
           subject_chooser: Get.AllWhich,
           option_getter: Get.StackList,
           allowed_to_fail: bool = True) -> ApplyToTargets:
        return ApplyToTargets(subject_chooser, option_getter,
                              self, allowed_to_fail)


class ApplyToTargets(VerbFactory):
    """Chooses targets and then passes those targets along
    to the sub-verb AS THOUGH THEY WERE THE `SUBJECT` FOR
    THE SUB-VERB.
    If the chooser returns a list longer than length 1, then
    the sub-verb is applied to all the targets in turn.
    """

    def __init__(self, subject_chooser: Get.AllWhich,
                 option_getter: Get.CardsFrom | Get.PlayerList | Get.StackList,
                 verb: AffectCard | AffectPlayer | AffectStack,
                 allowed_to_fail: bool = True):
        super().__init__(3, copies=verb.copies)
        self._inputs = [subject_chooser, option_getter, allowed_to_fail]
        self._sub_verbs = [verb]

    @property
    def allowed_to_fail(self) -> bool:
        return self.inputs[2]

    def populate_options(self: V, state, player, source, cause
                         ) -> List[MultiVerb]:
        """
        The first element of inputs needs to be a tuple of target
        players that the sub-verb should be applied to.
        Note that these choices are made at CAST-TIME. If you want
        them to run at RESOLVE-TIME instead, wrap this in `Defer`.
        """
        options = self.inputs[1].get(state, player, source)
        choices = self.inputs[0].pick(options, state, player, source)
        # chooser returns a list of tuples of Cardboards
        if len(choices) == 0:
            return []
        else:
            multi_list = []
            [subverb] = self.sub_verbs[0].populate_options(state, player,
                                                           source, cause)
            # Populated, but its subject is still player. Now fix that:
            for target_list in choices:
                populated = [subverb.replace_subject(t) for t in target_list]
                # each target now has a populated verb trying to affect it.
                # MultiVerb contains those verbs and executes them together
                multi = MultiVerb(populated)
                # populate Multi. Verb not MultiVerb to not overwrite subs
                Verb.populate_options(multi, state, player, source, cause)
                multi_list.append(multi)
            return multi_list


class Modal(VerbFactory):
    """Choose between various Verbs. Mode is chosen at
    cast-time, not on resolution."""

    def __init__(self, list_of_verbs: List[Verb],
                 num_to_choose: Get.Integer | int = 1, can_be_less=False):
        super().__init__(2, any([v.copies for v in list_of_verbs]))
        assert (len(list_of_verbs) > 1)
        self._sub_verbs = list_of_verbs
        self._inputs = [num_to_choose, can_be_less]

    @property
    def num_to_choose(self) -> Get.Integer | int:
        return self.inputs[0]

    @property
    def can_be_less(self) -> bool:
        return self.inputs[1]

    def populate_options(self, state, player, source, cause
                         ) -> List[MultiVerb]:
        # step 1: choose a verb or set of verbs
        possible = [(ii, str(v)) for ii, v in enumerate(self.sub_verbs)]
        if isinstance(self.num_to_choose, Get.Getter):
            num: int = self.num_to_choose.get(state, player, source)
        else:
            num: int = self.num_to_choose
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
        # step 2: for each chosen set of verbs, make a multi to describe that
        multi_verbs: List[MultiVerb] = []
        for set_of_verbs in modes:  # Tuple[Tuple[int, str]]
            verb_indices: Tuple[int] = tuple([ii for ii, ss in set_of_verbs])
            multi = MultiVerb([self.sub_verbs[ii] for ii in verb_indices])
            # populate the MultiVerb. This automatically populates subverbs
            multi_verbs += multi.populate_options(state, player, source, cause)
        return multi_verbs

    def __str__(self):
        return " or ".join([v.__str__() for v in self.sub_verbs])


class Defer(Verb):
    """
    Defers any cast-time choices of the given verb to instead
    be chosen only on resolution.
    """
    # TODO make this a decorator or abstract class to inherit from?

    def __init__(self, verb: Verb):
        super().__init__(0, copies=True)
        self._sub_verbs = [verb]

    def do_it(self, state: GameState, to_track=[], check_triggers=True):
        # list of verbs now WITH their options properly chosen
        populated = self.sub_verbs[0].populate_options(state, self.player,
                                                       self.source, self.cause)
        # apply each populated verb to a different copy of `state`. Safe to
        # check triggers as we go (if we were asked to do that) because each
        # verb is happening in a different gamestate copy.
        things = [self] + to_track
        results = []
        for verb in populated:
            if verb.copies:
                results += [(st, trk[0].replace_verb(0, vb), trk[1:])
                            for st, vb, trk in verb.do_it(state, things,
                                                          check_triggers)]
            else:
                self2 = self.replace_verb(0, verb)
                state2, things2 = state.copy_and_track([self2] + to_track)
                verb2 = things2[0].sub_verbs[0]
                results += [(st, trk[0].replace_verb(0, vb), trk[1:])
                            for st, vb, trk in verb2.do_it(state2, things2,
                                                           check_triggers)]
        return results

    def check_triggers(self, state, to_track=[]) -> RESULT:
        # nothing can trigger off of a "Defer" verb so doesn't bother to check
        return self.sub_verbs[0].check_triggers(state, to_track)

    def is_type(self, verb_type: type):
        return self.sub_verbs[0].is_type(verb_type)

    def __str__(self):
        return "Defer" + str(self.sub_verbs[0])

    def get_id(self):
        return "Defer" + self.sub_verbs[0].get_id()


class VerbManyTimes(VerbFactory):
    def __init__(self, verb: Verb, num_to_repeat: Get.Integer | int):
        """The number of times to repeat the verb is chosen on casting"""
        super().__init__(1, verb.copies)
        self._sub_verbs = [verb]
        self._inputs = [num_to_repeat]

    @property
    def num_to_repeat(self) -> Get.Integer | int:
        return self.inputs[0]

    def populate_options(self, state, player, source, cause
                         ) -> List[MultiVerb]:
        # number of times to repeat plus sub-verb's inputs
        if isinstance(self.num_to_repeat, Get.Getter):
            num: int = self.num_to_repeat.get(state, player, source)
        else:
            num: int = self.num_to_repeat
        multi = MultiVerb(self.sub_verbs[0:1] * num)  # same verb, n times
        # populate the MultiVerb. This automatically populates subverbs
        return multi.populate_options(state, player, source, cause)

    def __str__(self):
        return str(self.sub_verbs[0]) + " x " + str(self.num_to_repeat)


class LookDoThenDo(VerbFactory):
    """Get some cards, choose a subset, perform one verb on all
    the chosen cards and another verb on all non-chosen cards.
    As usual, selection is made at cast-time and should be wrapped
    in a Defer if resolution-time is desired (as it usually is)."""

    def __init__(self, look_at: Get.CardsFrom, choose: Get.AllWhich,
                 do_to_chosen: AffectCard,
                 do_to_others: AffectCard):
        super().__init__(2, ((not choose.single_output)
                             or do_to_chosen.copies or do_to_others.copies))
        self._inputs = [look_at, choose]
        assert do_to_chosen.num_inputs == 0
        assert do_to_others.num_inputs == 0
        self._sub_verbs = [do_to_chosen, do_to_others]

    @property
    def option_getter(self) -> Get.CardsFrom:
        return self.inputs[0]

    @property
    def chooser(self) -> Get.AllWhich:
        return self.inputs[1]

    def populate_options(self: V, state, player, source, cause
                         ) -> List[MultiVerb]:
        do_to_chosen = self.sub_verbs[0].populate_options(state, player,
                                                          source, cause)[0]
        do_to_others = self.sub_verbs[1].populate_options(state, player,
                                                          source, cause)[0]
        # These verbs are populated, but subject is still source. Now fix that
        options = self.option_getter.get(state, player, source)
        choices = self.chooser.pick(options, state, player, source)
        multi_list: List[MultiVerb] = []
        for chosen_list in choices:
            others_list = [c for c in options if c not in chosen_list]
            populated = []
            # Populate the verb which will act on this chosen card
            for chosen in chosen_list:
                populated += [v.replace_subject(chosen) for v in do_to_chosen]

                populated += do_to_chosen.populate_options(state, player,
                                                           source, cause)
            # Populate the verb which will act on this non-chosen card
            for other in others_list:
                populated += do_to_others.populate_options(state, player,
                                                           other, source)
            # each card now has a populated verb trying to affect it.
            # MultiVerb contains all those verbs and executes them together
            multi = MultiVerb(populated)
            # populate Multi. Verb not MultiVerb to not overwrite subverbs
            Verb.populate_options(multi, state, player, source, cause)
            multi_list.append(multi)
        return multi_list

    def __str__(self):
        act_yes = str(self.sub_verbs[0])
        choose = str(self.chooser)
        options = str(self.option_getter)
        act_no = str(self.sub_verbs[1])
        s = "%s on %s%s else %s" % (act_yes, choose, options, act_no)
        return s


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class NullVerb(Verb):
    """This Verb does literally nothing, ever."""

    def __init__(self):
        super().__init__(0, True)

    def populate_options(self, state, player, source, cause) -> List[Verb]:
        return []

    def do_it(self, state, to_track=[], check_triggers=True) -> List[RESULT]:
        return [(state, self, to_track)]

    def check_triggers(self, state: GameState, to_track: list = []) -> RESULT:
        return state, self, to_track

    def add_self_to_state_history(self, state):
        return

    def __str__(self):
        return "Null"

    def get_id(self):
        return "Null"


class SingleGetterInput(Verb):
    def populate_options(self, state, player, source, cause) -> List[Verb]:
        [base] = Verb.populate_options(self, state, player, source, cause)
        if isinstance(base.inputs[0], Get.Getter):
            value = base.inputs[0].get(state, player, source)
            return [base.replace_input(0, value)]
        else:
            return [base]  # already definite value, so no replacement needed


class PayMana(AffectPlayer, SingleGetterInput):
    """deducts the given amount of mana from the
    subject Player's mana pool."""

    def __init__(self, mana_string: Get.String | str):
        """If mana_string is a getter, it is evaluated during populate"""
        super().__init__(1)
        self._inputs = [mana_string]

    def can_be_done(self, state: GameState) -> bool:
        if not super().can_be_done(state):
            return False
        mana_str = self.inputs[0]
        pool = state.player_list[self.subject].pool
        return pool.can_afford_mana_cost(ManaHandler.ManaCost(mana_str))

    def do_it(self, state, to_track=[], check_triggers=True):
        mana_str = self.inputs[0]
        pool = state.player_list[self.subject].pool
        pool.pay_mana_cost(ManaHandler.ManaCost(mana_str))
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)

    def __str__(self):
        return "PayMana{%s}" % str(self.inputs[0])

    def add_self_to_state_history(self, state: GameState):
        if state.is_tracking_history:
            cost = ManaHandler.ManaCost(self.inputs[0])
            text = "\nPlayer%i add %s" % (self.subject, str(cost))
            state.events_since_previous += text


class AddMana(AffectPlayer, SingleGetterInput):
    """adds the given amount of mana to the player's mana pool"""

    def __init__(self, mana_string: Get.String | str):
        """If mana_string is a getter, it is evaluated during populate"""
        super().__init__(1)
        self._inputs = [mana_string]

    def do_it(self, state, to_track=[], check_triggers=True):
        mana_str = self.inputs[0]
        pool = state.player_list[self.subject].pool
        pool.add_mana(ManaHandler.ManaPool(mana_str))
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)

    def add_self_to_state_history(self, state):
        if state.is_tracking_history:
            pool = ManaHandler.ManaPool(self.inputs[0])
            text = "\nPlayer%i add %s" % (self.subject, str(pool))
            state.events_since_previous += text


class LoseLife(AffectPlayer, SingleGetterInput):
    def __init__(self, damage_getter: Get.Integer | int):
        """The subject player loses the given amount of life. If
        damage_getter is a getter, it is evaluated during populate"""
        super().__init__(1)
        self._inputs = [damage_getter]

    def do_it(self, state, to_track=[], check_triggers=True):
        state.player_list[self.player].life -= self.inputs[0]
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)

    def add_self_to_state_history(self, state):
        if state.is_tracking_history:
            text = "\nPlayer%i lose %i life" % (self.subject, self.inputs[0])
            state.events_since_previous += text


class GainLife(AffectPlayer, SingleGetterInput):
    def __init__(self, amount_getter: Get.Integer | int):
        """The subject player gains the given amount of life. If
        amount_getter is a getter, it is evaluated during populate"""
        super().__init__(1)
        self._inputs = [amount_getter]

    def do_it(self, state, to_track=[], check_triggers=True):
        state.player_list[self.subject].life += self.inputs[0]
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)

    def add_self_to_state_history(self, state):
        if state.is_tracking_history:
            text = "\nPlayer%i gain %i life" % (self.subject, self.inputs[0])
            state.events_since_previous += text


class DamageToPlayer(LoseLife):
    """The subject player is dealt the given amount of damage
        by the source."""

    def do_it(self, state, to_track=[], check_triggers=True):
        # make the source's controller gain life if source has lifelink
        if "lifelink" in Get.Keywords().get(state, self.source.player_index,
                                            self.source):
            gainer = GainLife(self.inputs[0])
            gainer = gainer.replace_subject(self.subject)  # just need subject
            gainer.do_it(state, check_triggers=False)  # mutates
            # add gainer to be a subverb of self, so that triggers will be
            # checked automatically later on
            new_self = self.replace_verb(1, gainer)
        else:
            new_self = self
        # super.do_it to make the player actually lose life. Also, as usual,
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return super(LoseLife, new_self).do_it(state, to_track, check_triggers)

    def add_self_to_state_history(self, state):
        if state.is_tracking_history:
            state.events_since_previous += "\n%s dealt " % str(self.source)
            state.events_since_previous += str(self.inputs[0])
            state.events_since_previous += " damage to Player"
            state.events_since_previous += str(self.subject)


class PayLife(LoseLife):
    """The subject player pays the given amount of life.
    Cannot be done if they don't have enough life to pay."""
    def can_be_done(self, state: GameState) -> bool:
        return (super().can_be_done(state) and
                state.player_list[self.player].life >= self.inputs[0])

    def add_self_to_state_history(self, state):
        if state.is_tracking_history:
            text = "\nPlayer%i pays %i life" % (self.subject, self.inputs[0])
            state.events_since_previous += text


class LoseTheGame(AffectPlayer):

    def do_it(self, state, to_track=[], check_triggers=True):
        state.player_list[self.subject].victory_status = "L"
        # if everyone else has lost, the last player standing wins!
        still_playing = [pl for pl in state.player_list
                         if pl.victory_status == ""]
        if len(still_playing) == 1:
            # build a winner. ignore source, player, etc, just need subject
            win = WinTheGame().replace_subject(still_playing[0].player_index)
            win.do_it(state, check_triggers=False)  # mutates
            new_self = self.replace_verb(0, win)  # add win as sub_verb
        else:
            new_self = self
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(new_self, state, to_track, check_triggers)

    def add_self_to_state_history(self, state):
        if state.is_tracking_history:
            text = "\nPlayer %s loses the game!" % str(self.subject)
            state.events_since_previous += text


class WinTheGame(AffectPlayer):

    def do_it(self, state, to_track=[], check_triggers=True):
        state.player_list[self.subject].victory_status = "W"
        # all other players automatically lose
        new_self = self.copy()
        for pl in state.player_list:
            if pl.victory_status == "":
                lose = LoseTheGame().replace_subject(pl.player_index)
                lose.do_it(state, check_triggers=False)  # mutates
                new_self = new_self.replace_verb(len(new_self.sub_verbs), lose)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(new_self, state, to_track, check_triggers)

    def add_self_to_state_history(self, state):
        if state.is_tracking_history:
            text = "\nPlayer %s wins the game!" % str(self.subject)
            state.events_since_previous += text


# ----------

class Tap(AffectCard):
    """taps the source card if it was not already tapped."""

    def can_be_done(self, state: GameState) -> bool:
        return (super().can_be_done(state)
                and self.subject.is_in(Zone.Field)
                and not self.subject.tapped)

    def do_it(self, state, to_track=[], check_triggers=True) -> List[RESULT]:
        self.subject.tapped = True
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)


class Untap(AffectCard):
    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState) -> bool:
        return (super().can_be_done(state)
                and self.subject.is_in(Zone.Field)
                and self.subject.tapped)

    def do_it(self, state: GameState, to_track=[], check_triggers=True):
        self.subject.tapped = False
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)


class AddCounter(AffectCard):
    """Adds the given counter string to the subject card"""

    def __init__(self, counter_text: str):
        super().__init__()
        self._inputs = [counter_text]

    @property
    def counter_text(self):
        return self.inputs[0]

    def can_be_done(self, state: GameState) -> bool:
        return (super().can_be_done(state)
                and self.subject.is_in(Zone.Field))

    def do_it(self, state, to_track=[], check_triggers=True) -> List[RESULT]:
        self.subject.add_counter(self.counter_text)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)

    def add_self_to_state_history(self, state: GameState):
        if state.is_tracking_history:
            text = "\nPut %s counter on %s" % (self.counter_text,
                                               self.subject.name)
            state.events_since_previous += text


class ActivateOncePerTurn(AffectCard):
    """Marks the given `subject` as only able to activate this ability once
    per turn"""

    def __init__(self, ability_name: str):
        super().__init__()
        self._inputs = ["@" + ability_name]  # "@" is invisible counter

    @property
    def counter_text(self):
        return self.inputs[0]

    def can_be_done(self, state: GameState) -> bool:
        return (super().can_be_done(state)
                and self.subject.is_in(Zone.Field)
                and self.counter_text not in self.subject.counters)

    def do_it(self, state, to_track=[], check_triggers=True):
        self.subject.add_counter(self.counter_text)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)

    def add_self_to_state_history(self, state):
        return  # doesn't mark itself as having done anything


class ActivateOnlyAsSorcery(Verb):
    """Checks that the stack is empty and the controller
     of this Verb has priority. Otherwise, `can_be_done`
     will return False."""

    def can_be_done(self, state: GameState) -> bool:
        return (super().can_be_done(state)
                and len(state.stack) == 0 and len(state.super_stack) == 0
                and state.active_player_index == self.player)

    def do_it(self, state, to_track=[], check_triggers=True):
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)

    def add_self_to_state_history(self, state):
        return  # doesn't mark itself as having done anything


class Shuffle(AffectPlayer):
    """Shuffles the deck of given player."""

    def do_it(self, state, to_track=[], check_triggers=True) -> List[RESULT]:
        """Mutates. Reorder deck randomly."""
        random.shuffle(state.player_list[self.subject].deck)
        for ii in range(len(state.player_list[self.subject].deck)):
            state.player_list[self.subject].deck[ii].zone.location = ii
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)

    def add_self_to_state_history(self, state):
        if state.is_tracking_history:
            state.events_since_previous += "\nShuffle"


class MoveToZone(AffectCard):
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
        self._inputs = [destination_zone, None]

    @property
    def dest(self):
        return self.inputs[0]

    @property
    def origin(self):
        return self.inputs[1]

    def can_be_done(self, state: GameState) -> bool:
        if not super().can_be_done(state):
            return False
        if not self.subject.zone.is_fixed or self.dest.is_single:
            # origin zone and destination zone must be clear locations. debug
            print("dest zone not specified!", state, self.player, self.subject)
            return False
        if (not self.subject.is_in(Zone.Stack)
                and not self.subject.is_in(Zone.Unknown)):
            # confirm Cardboard is where it is supposed to be
            return self.subject in self.subject.zone.get(state)
        else:
            return True

    def do_it(self, state, to_track=[], check_triggers=True) -> List[RESULT]:
        # figure out absolute origin and destination zone
        dest = self.dest
        if not dest.is_single:
            zone_list = dest.get_absolute_zones(state, self.player,
                                                self.subject)  # source?
            if len(zone_list) != 1:
                raise Zone.Zone.NotSpecificPlayerError
            dest = zone_list[0]
        origin = self.subject.zone.copy()
        # NOTE: Zone handles whether the Cardboard is actually added or pulled
        # from the zone (e.g. for the Stack). Don't worry about that here.
        origin.remove_from_zone(state, self.subject)
        # add to destination. (also resets subject's zone to be destination.)
        dest.add_to_zone(state, self.subject)
        self.subject.reset_to_default_cardboard()
        # add the origin and destination to inputs. necessary for checking.
        new_self = self.replace_input(0, dest)
        new_self = new_self.replace_input(1, origin)
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(new_self, state, to_track, check_triggers)

    def __str__(self):
        return "MoveTo" + str(self.dest)

    @staticmethod
    def move(state: GameState, card: Cardboard, destination: Zone.Zone,
             check_triggers = False):
        """Moves the card to the destination zone. Mutates
        the GameState. Helper function for when you need
        o move a card quickly and are willing to take
        responsibility for not breaking the rules."""
        assert destination.is_fixed and destination.is_single
        mover = MoveToZone(destination).replace_subject(card)
        mover.do_it(state, check_triggers=check_triggers)


class DrawCard(AffectPlayer):
    """The subject player draws from the top (index -1) of the deck"""

    # Note: even if the deck is empty, you CAN draw. you'll just lose.

    def do_it(self, state, to_track=[], check_triggers=True) -> List[RESULT]:
        top_card_list = Zone.DeckTop(self.subject).get(state)  # 0 or 1 cards
        if len(top_card_list) > 0:
            mover = MoveToZone(Zone.Hand(self.subject))
            [mover] = mover.populate_options(state, self.player, self.source,
                                             self.cause)
            mover = mover.replace_subject(top_card_list[0])  # move this card
            mover.do_it(state, check_triggers=False)
            # add mover to sub_verbs, to be visible to triggers for move also
            new_self = self.replace_verb(0, mover)
            return Verb.do_it(new_self, state, to_track, check_triggers)
        else:
            lose = LoseTheGame().replace_subject(self.subject)
            lose.do_it(state, check_triggers=False)  # mutates
            # didn't actually draw, so check for LoseTheGame not Draw or Move
            return Verb.do_it(lose, state, to_track, check_triggers)


class MarkAsPlayedLand(AffectPlayer):
    """Doesn't actually move any cards, just toggles the
    gamestate to say that the subjectn player has already
    played a land this turn"""

    def can_be_done(self, state: GameState) -> bool:
        return state.player_list[self.subject].land_drops_left > 0

    def do_it(self, state, to_track=[], check_triggers=True) -> List[RESULT]:
        state.player_list[self.subject].num_lands_played += 1
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)

    def add_self_to_state_history(self, state):
        return


class Sacrifice(MoveToZone):
    def __init__(self):
        super().__init__(Zone.Grave(Get.Owners()))

    def can_be_done(self, state: GameState) -> bool:
        return (super().can_be_done(state)
                and self.subject.is_in(Zone.Field))

    def __str__(self):
        return "Sacrifice"


class Destroy(MoveToZone):
    def __init__(self):
        super().__init__(Zone.Grave(Get.Owners()))

    def can_be_done(self, state: GameState) -> bool:
        return (super().can_be_done(state)
                and self.subject.is_in(Zone.Field))

    def do_it(self, state, to_track=[], check_triggers=True):
        if Match.Keyword("indestructible").match(self.subject, state,
                                                 self.player, self.source):
            return [(state, NullVerb(), to_track)]

    def __str__(self):
        return "Destroy"


# ----------


class SearchDeck(VerbFactory):
    """Search deck for N cards which match the pattern, then
    move those cards to the specified zone. Then shuffle.
    As usual, selection is made at cast-time and should be wrapped
    in a Defer if resolution-time is desired (as it usually is).
    """

    def __init__(self, zone_to_move_to: Zone.Zone, num_to_find: int,
                 pattern: Match.Pattern):
        super().__init__(3, True)
        self._inputs = [zone_to_move_to, num_to_find, pattern]

    def populate_options(self: V, state, player, source, cause
                         ) -> List[MultiVerb]:
        # figure out the absolute destination zone
        [dest] = self.inputs[0].get_absolute_zones(state, player, source)
        # set up chooser
        num_to_find = self.inputs[1]
        pattern = self.inputs[2]
        chooser = Get.Chooser(pattern, num_to_find, can_be_fewer=True)
        # build the LookDoThenDo to do all the heavy lifting
        # noinspection PyTypeChecker
        do_er = LookDoThenDo(look_at=Get.CardsFrom(Zone.Deck(player, None)),
                             choose=chooser,
                             do_to_chosen=MoveToZone(dest),
                             do_to_others=NullVerb())  # wrong type. eh.
        # then shuffle
        multi = MultiVerb([do_er, Shuffle()])
        return multi.populate_options(state, player, source, cause)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class UniversalCaster(AffectStack):
    """
    The Verb which adds a StackObject onto the stack. If there
    is a cost associated with casting the spell or activating
    the ability, this pays the cost. If targets need to be
    chosen for the effect, this chooses the targets. If the
    action bypasses the stack (like playing a land or mana
    ability), this executes the card or effect entirely.
    """

    def __init__(self):
        super().__init__(0, copies=True)

    @property
    def subject(self) -> StackObject:
        return self._subject

    def can_be_done(self, state: GameState) -> bool:
        """Can the given StackObject be put onto the stack?
        """
        stackobj: StackObject = self.subject
        return (super().can_be_done(state)
                and (stackobj.pay_cost is None
                     or stackobj.pay_cost.can_be_done(state))
                and (stackobj.do_effect is None
                     or stackobj.do_effect.can_be_done(state)))

    def do_it(self, state: GameState, to_track=[], check_triggers=True):
        """Put the StackObject onto the stack, paying any
        necessary costs. Bypass the stack if necessary."""
        # check to make sure the execution is legal
        if not self.can_be_done(state):
            return []
        # 601.2a: add the spell to the stack
        state2, things = state.copy_and_track([self] + to_track)
        self2: UniversalCaster = things[0]
        to_track2 = things[1:]
        obj2: StackObject = self2.inputs[0]
        self2._add_to_stack(state2, obj2)
        # 601.2b: choose costs (additional costs, choose X, choose hybrid. For
        #   me this has already been done by choices.)
        # 601.2c: choose targets and modes -- already done by choices.
        # 601.2f: determine total cost -- part of payment for me, I think?
        # 601.2g: activate mana abilities -- I don't actually permit this.
        # 601.2h: pay costs
        if obj2.pay_cost is not None:
            tuple_list: List[RESULT] = obj2.pay_cost.do_it(state2,
                                                           [self2] + to_track2,
                                                           check_triggers)
            # verb in result list needs to be self, not the payment verb
            tuple_list: List[Tuple[GameState, UniversalCaster, list]] = [
                (state3, track3[0], track3[1:])
                for state3, verb, track3 in tuple_list]

        else:
            tuple_list: List[Tuple[GameState, UniversalCaster, list]] = [
                (state2, self2, to_track2)]
        # 601.2i: ability has now "been activated".  Any abilities which
        # trigger from some aspect of paying the costs have already
        # been added to the superstack during ability.cost.pay. Now add
        # any trigger that trigger off of this activation/casting itself.
        results: List[RESULT] = []
        for state4, self4, track4 in tuple_list:
            new_tuple_list = Verb.do_it(self4, state4, track4, check_triggers)
            # if necessary, the object will now instantly resolve. We are
            # guaranteed that the object is be the latest item on the stack, as
            # triggers go on SUPER-stack. obj was put on stack even though it
            # might be removed because then it can be automatically copied by
            # GameState and to make subclasses of UniversalCaster nicer.
            for state5, self5, track5 in new_tuple_list:
                self5: UniversalCaster
                results += self5._remove_if_needed(state5, track5)
        return results

    @staticmethod
    def _add_to_stack(game: GameState, obj: StackObject) -> None:
        """Mutate the GameState to put the given StackObject
        onto the stack. This includes removing it from other
        zones if necessary."""
        game.stack.append(obj)

    def _remove_if_needed(self, game: GameState, to_track: list
                          ) -> List[RESULT]:
        """If the thing we just put on the stack is supposed to
        resolve instantly, do that. Otherwise, just give back all
        the arguments unchanged. ALLOWED TO MUTATE INPUT STATE."""
        return [(game, self, to_track)]

    def add_self_to_state_history(self, state: GameState) -> None:
        if state.is_tracking_history:
            record = "\n*** %s %s ***" % (str(self), self.subject.name)
            state.events_since_previous += record


class PlayAbility(UniversalCaster):
    def __str__(self):
        return "Activate"


class PlayManaAbility(PlayAbility):
    def _remove_if_needed(self, game: GameState, to_track: list
                          ) -> List[RESULT]:
        """If the thing we just put on the stack is supposed to
        resolve instantly, do that. Otherwise, just give back all
        the arguments unchanged. ALLOWED TO MUTATE INPUT STATE."""
        stack_obj = game.stack.pop(-1)
        assert stack_obj is self.inputs[0]  # for debug
        if stack_obj.do_effect is None:
            return [(game, self, to_track)]
        else:
            # perform the effect (resolve ability, perform spell, etc)
            tuple_list = stack_obj.do_effect.do_it(game, [self] + to_track)
            # add this effect verb to self as a sub_verb that was executed, so
            # that its triggers are also automatically checked
            results = []
            for state2, effect2, things2 in tuple_list:
                self2: UniversalCaster = things2[0].replace_verb(0, effect2)
                track2 = things2[1:]
                results.append((state2, self2, track2))
            return results


class AddTriggeredAbility(UniversalCaster):
    def __str__(self):
        return "Trigger"

    def do_it(self, state: GameState, to_track=[], check_triggers=True):
        """Put the StackObject onto the stack, paying any
        necessary costs. Bypass the stack if necessary.
        Assumes that the caster has already been removed
        from the super_stack by others."""
        # check to make sure the execution is legal
        if not self.can_be_done(state):
            return []
        trig: StackObject = self.subject  # specifically a stacktrigger
        # 601.2c: choose targets and modes
        effects = trig.do_effect.populate_options(state, trig.player_index,
                                                  self.source, self.cause)
        effects = [eff for eff in effects if eff.can_be_done(state)]
        if len(effects) == 0:
            effects = [None]
        # 601.2a: add the spell to the stack. make StackAbility for each.
        final_results: List[RESULT] = []
        for do_effect in effects:
            abil = Stack.StackAbility(controller=trig.player_index,
                                      obj=trig.obj,
                                      pay_cost=None,
                                      do_effect=do_effect)
            state2, things = state.copy_and_track([abil, self] + to_track)
            state2.stack.append(things[0])  # copy of StackAbility `abil`
            # 601.2i: ability has now "been activated".  Any abilities which
            # trigger from some aspect of paying the costs have already
            # been added to the superstack during ability.cost.pay. Now add
            # any trigger that trigger off of this activation/casting itself.
            self2: AddTriggeredAbility = things[1]
            new_tuple_list = Verb.do_it(self2, state2, things[2:],
                                        check_triggers)
            # if necessary, the object will now instantly resolve. We are
            # guaranteed that the object is be the latest item on the stack, as
            # triggers go on SUPER-stack. obj was put on stack even though it
            # might be removed because then it can be automatically copied by
            # GameState and to make subclasses of UniversalCaster nicer.
            for state3, self3, track3 in new_tuple_list:
                self3: AddTriggeredAbility
                final_results += self3._remove_if_needed(state3, track3)
        return final_results


class AddAsEntersAbility(AddTriggeredAbility):
    def _remove_if_needed(self, game: GameState, to_track: list
                          ) -> List[RESULT]:
        """If the thing we just put on the stack is supposed to
        resolve instantly, do that. Otherwise, just give back all
        the arguments unchanged. ALLOWED TO MUTATE INPUT STATE."""
        stack_obj = game.stack.pop(-1)
        assert stack_obj is self.subject
        # perform the effect (resolve ability, perform spell, etc)
        if stack_obj.do_effect is None:
            return [(game, self, to_track)]
        else:
            # perform the effect (resolve ability, perform spell, etc)
            tuple_list = stack_obj.do_effect.do_it(game, [self] + to_track)
            # add this effect verb to self as a sub_verb that was executed, so
            # that it's triggers are also automatically checked
            results = []
            for state2, effect2, things2 in tuple_list:
                self2: UniversalCaster = things2[0].replace_verb(0, effect2)
                track2 = things2[1:]
                results.append((state2, self2, track2))
            return results


# ----------

class PlayCardboard(UniversalCaster):

    def __str__(self):
        return "Cast"

    @staticmethod
    def _add_to_stack(game: GameState, obj: StackCardboard) -> None:
        """Mutate the GameState to put the given StackObject
        onto the stack. This includes removing it from other
        zones if necessary."""
        MoveToZone.move(game, obj.obj, Zone.Stack(), False)
        # for a StackCardboard, obj.source_card and obj.obj are pointers to
        # the same thing. Thus, moving either of them is sufficient.
        game.stack.append(obj)


# ----------
class PlayLand(PlayCardboard):

    def __str__(self):
        return "Play"

    def _remove_if_needed(self, game: GameState, to_track: list
                          ) -> List[RESULT]:
        """If the thing we just put on the stack is supposed to
        resolve instantly, do that. Otherwise, just give back all
        the arguments unchanged. ALLOWED TO MUTATE INPUT STATE."""
        stack_obj = game.stack.pop(-1)
        assert stack_obj is self.subject
        assert stack_obj.obj.is_in(Zone.Stack)
        # move the land to the `player`'s field instantly
        mover = MoveToZone(Zone.Field(stack_obj.obj.player_index))
        [mover] = mover.populate_options(game, self.player, self.source,
                                         self.cause)
        mover = mover.replace_subject(stack_obj.obj)
        mover.do_it(game)  # mutates, so no need to track or anything
        # add this effect verb to self as a sub_verb that was executed, so
        # that its triggers are also automatically checked
        self2: PlayLand = self.replace_verb(0, mover)
        return [(game, self2, to_track)]


# ----------
class PlaySorcery(PlayCardboard):
    def can_be_done(self, state: GameState) -> bool:
        doable = super().can_be_done(state)
        stack_empty = len(state.stack) == 0
        card = self.subject.obj
        has_flash = Match.Keyword("flash").match(card, state,
                                                 self.player, card)
        return doable and (stack_empty or has_flash)


# ----------
class PlayPermanent(PlayCardboard):
    def can_be_done(self, state: GameState) -> bool:
        doable = super().can_be_done(state)
        stack_empty = len(state.stack) == 0
        card = self.subject.obj
        has_flash = Match.Keyword("flash").match(card, state,
                                                 self.player, card)
        return doable and (stack_empty or has_flash)
