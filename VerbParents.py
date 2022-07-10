from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import Getters as Get
    from Cardboard import Cardboard
    from GameState import GameState

from Stack import StackAbility


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
        # TODO: move to PlayTree or ActivateAbility & CastAbility?
        if state.verbose:
            state.history.append(str(self))
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
        return [(state, subject, choices[len(self.getter_list):])]

    # def __str__(self):
    #     text = type(self).__name__
    #     if len(self.sub_verbs) > 0:
    #         text += "(" + ",".join([str(v) for v in self.sub_verbs]) + ")"
    #     return text

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


# ----------
class VerbAtomic(Verb):
    pass


# ----------

class VerbOnSubjectCard(Verb):
    """acts on the source passed into the `do_it` method"""
    pass


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


# ----------
class ManyVerbs(Verb):
    def __init__(self, list_of_verbs: List[Verb]):
        super().__init__()
        assert(len(list_of_verbs) > 1)
        self.sub_verbs = list_of_verbs
        self.getter_list = []

    def __str__(self):
        return "&".join([v.__str__() for v in self.sub_verbs])

    def do_it(self, state: GameState, subject: Cardboard,
              choices: list) -> List[Tuple[GameState, Cardboard, list]]:
        tuple_list = [(state, subject, choices)]
        for v in self.sub_verbs:
            # if verb allowed to mutate, mutate gamestates in place
            if v.mutates:
                for g,c,ch in tuple_list:
                    v.do_it(g,c,ch)
            # if verb returns new list, use that to overwrite tuple_list
            else:
                new_tuple_list = []
                for g,c,ch in tuple_list:
                    new_tuple_list += v.do_it(g,c,ch)
                tuple_list = new_tuple_list
        # The do_it functions of each Verb will handle triggers for those
        # sub-verbs. no need to call super().do_it because nothing triggers.
        # Similarly, ManyVerbs itself has no getters, so there is no need to
        # reduce the length of the choice_list on behalf of the ManyVerb
        # itself, and each Verb's do_it will have reduced the list according
        # to that particular Verb's getter_list.  So omit the call to super
        return tuple_list


# ----------

class ChooseVerb(Verb):
    def __init__(self, list_of_verbs: List[Verb], chooser: Get.Chooser):
        super().__init__()
        assert (len(list_of_verbs) > 1)
        self.sub_verbs = list_of_verbs
        self.getter_list = [chooser]
        # TODO I still need chooser to have correct type. return index or verb?

    def __str__(self):
        return " or ".join([v.__str__() for v in self.sub_verbs])

    def do_it(self, state: GameState, subject: Cardboard,
              choices: list) -> List[Tuple[GameState, Cardboard, list]]:
        # first element of choices is the index of which verb to use
        return self.sub_verbs[choices[0]].do_it(state, subject, choices[1:])

    @property
    def mutates(self):
        return any([v.mutates for v in self.sub_verbs])


# ----------

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
        return [[sub[0]] + (sub[1:] * sub[0]) for sub in raw_choices]

    def __str__(self):
        return str(self.sub_verbs[0]) + "(" + str(self.getter_list[0]) + ")"

# ----------


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
