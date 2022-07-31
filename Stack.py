from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from Abilities import ActivatedAbility, TriggeredAbility
    from Cardboard import Cardboard
    from Verbs import Verb, INPUTS
    from Costs import Cost
    from GameState import GameState


class StackObject:

    def __init__(self, controller: int, source_card: Cardboard | None,
                 obj: ActivatedAbility | TriggeredAbility | Cardboard,
                 chosen_options: INPUTS,
                 caster_verb: Verb):
        self.player_index: int = controller
        self.source_card: Cardboard | None = source_card
        # the THING which is on the stack.
        self.obj: ActivatedAbility | TriggeredAbility | Cardboard = obj
        # list of any modes or targets or other choices made during casting
        # or activation.  If targets are Cardboards, they are pointers.
        self.choices: INPUTS = chosen_options
        self.caster_verb = caster_verb

    @property
    def cost(self) -> Cost | None:
        if hasattr(self.obj, "cost"):
            return self.obj.cost

    @property
    def effect(self) -> Verb | None:
        if hasattr(self.obj, "effect"):
            return self.obj.effect

    def get_id(self):
        s_text = "" if self.source_card is None else self.source_card.get_id()
        obj_text = self.obj.get_id()
        list_text = ",".join([c.get_id() if hasattr(c, "get_id") else str(c)
                              for c in self.choices])
        return "Ob%i(%s-%s,%s)" % (self.player_index, s_text, obj_text,
                                   list_text)

    def is_equiv_to(self, other: StackObject):
        return self.get_id() == other.get_id()

    @property
    def name(self):
        return self.obj.name

    def __str__(self):
        return "Ob(%s)" % self.name

    def __repr__(self):
        return self.get_id()

    def put_on_stack(self, state: GameState) -> List[GameState]:
        """Returns a list of GameStates where this spell has
        been cast (put onto the stack) and all costs paid.
        GUARANTEED NOT TO MUTATE THE ORIGINAL STATE"""
        # PlayAbility.do_it does not mutate
        return [t[0] for t in self.caster_verb.do_it(state, self.player_index,
                                                     self.source_card, [self])]

    def copy(self, state_orig: GameState, state_new: GameState):
        """This function assumes that everything except the
        stack and superstack have already been copied
        correctly. In other words, all Cardboards have
        already been copied. It is only StackObjects which
        remain to be copied."""
        # if this StackObject is a pointer to a DIFFERENT StackObject on the
        # stack which already has a copy, then just return that new copied
        # object. (Relevant for e.g. counterspell, which targets a StackObject)
        if self in state_orig.stack:
            index = state_orig.stack.index(self)
            if len(state_new.stack) > index:  # check if new copy exists yet
                return state_new.stack[index]
        # If reached here, we need to make a new StackObject ourselves
        controller: int = self.player_index  # copy int directly
        # asking_card card
        if self.source_card is None:
            source = None
        else:
            source = self.source_card.copy_as_pointer(state_orig, state_new)
        # object card or object ability
        if hasattr(self.obj, "copy_as_pointer"):  # it's a Cardboard
            obj = self.obj.copy_as_pointer(state_orig, state_new)
        else:
            obj = self.obj.copy()
        # copy options
        options = state_orig.copy_arbitrary_list(state_orig, state_new,
                                                 self.choices)
        verb = self.caster_verb
        # initialize into a StackObject, then cast it to the correct subclass
        new_obj = StackObject(controller, source, obj, options, verb)
        new_obj.__class__ = self.__class__  # set the class type directly
        return new_obj


class StackAbility(StackObject):

    def __str__(self):
        return "Effect(%s)" % self.name

    # def build_tk_display(self, parentframe, ):
    #     return tk.Button(parentframe,
    #                      text="Effect: %s" % self.name,
    #                      anchor="w",
    #                      height=7, width=10, wraplength=80,
    #                      padx=3, pady=3,
    #                      relief="solid", bg="lightblue")


class StackTrigger(StackAbility):

    def __init__(self, controller: int, source_card: Cardboard,
                 obj: TriggeredAbility, cause_card: Cardboard,
                 chosen_options: INPUTS, caster_verb: Verb):
        """First entry in `choices` should be the Cardboard that
        caused the ability to trigger."""

        super().__init__(controller, source_card, obj,
                         [cause_card] + chosen_options, caster_verb)

    @property
    def cause(self):
        return self.choices[0]


class StackCardboard(StackObject):

    def __init__(self, controller: int, source_card: None,
                 obj: Cardboard, chosen_options: INPUTS, caster_verb: Verb):
        super().__init__(controller, obj, obj, chosen_options, caster_verb)

    def __str__(self):
        return "Spell: " + self.name

    # def build_tk_display(self, parentframe, ):
    #     return tk.Button(parentframe,
    #                      text="Effect: %s" % self.name,
    #                      anchor="w",
    #                      height=7, width=10, wraplength=80,
    #                      padx=3, pady=3,
    #                      relief="solid", bg="lightblue")
