from __future__ import annotations
from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard
    from Abilities import GenericAbility
    from Verbs import Verb
from Verbs import MoveToZone, ManyVerbs


class StackObject:
    def __init__(self):
        # The Ability that is being activated, if any
        self.ability: GenericAbility | None = None
        # The Cardboard being cast, or the source of the ability, if any
        self.card: Cardboard | None = None
        # list of any modes or targets or other choices made during casting
        # or activation.  If targets are Cardboards, they are pointers.
        self.choices: list = []

    @property
    def cost(self) -> Verb | None:
        if self.ability is not None:
            return self.ability.cost
        elif self.card is not None:
            return self.card.cost
        else:
            return None

    @property
    def effect(self) -> Verb | None:
        if self.ability is not None:
            return self.ability.effect
        elif self.card is not None and hasattr(self.card, "effect"):
            return self.card.effect
        else:
            return None

    def resolve(self, state: GameState) -> List[GameState]:
        """Returns list of GameStates resulting from performing
        this spell's effect. That might consist of carrying out
        the Verbs of an instant or sorcery, or might consist of
        moving a permanent from the stack to the battlefield and
        putting all resulting triggers onto the stack.
        Does not mutate the original GameState"""
        assert (self is state.stack[-1])  # last item on the stack
        new_state = state.copy()
        # remove StackObject from the stack
        stack_obj = new_state.stack.pop(-1)
        tuple_list = [(new_state, stack_obj.card, [])]
        # perform the effect (resolve ability, move card to zone, etc)
        if stack_obj.effect is not None:
            tuple_list = stack_obj.effect.do_it(new_state, stack_obj.card,
                                                stack_obj.choices)
        # clear the superstack and return!
        results = []
        for state2, _, _ in tuple_list:
            results += state2.clear_super_stack()
        return results

    def get_id(self):
        text = "Ob("
        text += "" if self.ability is None else "%s|" % str(self.ability)
        text += "" if self.card is None else self.card.get_id()
        choices = ",".join([c.get_id() if hasattr(c, "get_id") else str(c)
                            for c in self.choices])
        text += "|"+choices if len(choices) > 0 else ""
        text += ")"
        return text

    def is_equiv_to(self, other: StackObject):
        return self.get_id() == other.get_id()

    @property
    def name(self):
        return self.get_id()


class StackCardboard(StackObject):

    def __init__(self, card: Cardboard, choices: list):
        super().__init__()
        self.ability: GenericAbility | None = None
        self.card: Cardboard = card
        self.choices: list = choices

    @property
    def effect(self) -> Verb:
        # Cards always need to be moved to their destiniation zone as part
        # of their resolution. So, construct a Verb that does this
        mover = MoveToZone(self.card.rules_text.cast_destination)
        # If the card ALSO has an effect, then we'll need to do that effect
        # also. If not, then this mover is it.
        card_effect = super().effect
        if card_effect is not None:
            return ManyVerbs([card_effect, mover])
        else:
            return mover

    def __str__(self):
        return self.card.name

    def __repr__(self):
        return "Spell: " + self.card.name

    # def build_tk_display(self, parentframe, ):
    #     return tk.Button(parentframe,
    #                      text="Effect: %s" % self.name,
    #                      anchor="w",
    #                      height=7, width=10, wraplength=80,
    #                      padx=3, pady=3,
    #                      relief="solid", bg="lightblue")


class StackAbility(StackObject):

    def __init__(self, ability: GenericAbility, source: Cardboard,
                 choices: list):
        super().__init__()
        self.ability: GenericAbility | None = ability
        self.card: Cardboard = source
        self.choices: list = choices

    def __str__(self):
        return self.ability.name

    def __repr__(self):
        return "Effect: " + self.ability.name

    @property
    def name(self):
        return self.ability.name

    # def build_tk_display(self, parentframe, ):
    #     return tk.Button(parentframe,
    #                      text="Effect: %s" % self.name,
    #                      anchor="w",
    #                      height=7, width=10, wraplength=80,
    #                      padx=3, pady=3,
    #                      relief="solid", bg="lightblue")
