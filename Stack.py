from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from Abilities import GenericAbility
    from Cardboard import Cardboard
    from GameState import GameState
    from VerbParents import Verb
    from VerbCastAndActivate import (PutStackObjectOnStack, PlayAbility,
                                     PlayCard)


class StackObject:
    def __init__(self):
        # The Ability that is being activated, if any
        self.ability: GenericAbility | None = None
        # The Cardboard being cast, or the source of the ability, if any
        self.card: Cardboard | None = None
        # list of any modes or targets or other choices made during casting
        # or activation.  If targets are Cardboards, they are pointers.
        self.choices: list = []
        # the Verb used to actually put this StackObject onto the stack (which
        # triggers things which trigger off of casting spells, playing lands,
        # activating abilities, triggering abilities, etc.
        self.verb_to_put_it_onto_stack: PutStackObjectOnStack | None = None

    def copy(self, new_card: Cardboard, new_choices: list) -> StackObject:
        new_obj = StackObject()
        new_obj.ability = self.ability
        new_obj.choices = new_choices
        new_obj.verb_to_put_it_onto_stack = self.verb_to_put_it_onto_stack
        return new_obj

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

    def is_valid_to_play(self, state: GameState) -> bool:
        return self.verb_to_put_it_onto_stack.can_be_done(state, self.card,
                                                          [self])

    def play_onto_stack(self, state: GameState):
        """Use the `putter` Verb to put itself onto the stack
         of the given GameState. DOES NOT MUTATE."""
        return self.verb_to_put_it_onto_stack.do_it(state, self.card, [self])


class StackAbility(StackObject):

    def __init__(self, ability: GenericAbility, source: Cardboard,
                 choices: list, putter: PlayAbility):
        super().__init__()
        self.ability: GenericAbility = ability
        self.card: Cardboard = source
        self.choices: list = choices
        self.verb_to_put_it_onto_stack = putter

    def __str__(self):
        return self.ability.name

    def __repr__(self):
        return "Effect: " + self.ability.name

    @property
    def name(self):
        return self.ability.name

    def copy(self, new_card: Cardboard, new_choices: list) -> StackAbility:
        return StackAbility(self.ability, new_card, new_choices,
                            self.verb_to_put_it_onto_stack)

    # def build_tk_display(self, parentframe, ):
    #     return tk.Button(parentframe,
    #                      text="Effect: %s" % self.name,
    #                      anchor="w",
    #                      height=7, width=10, wraplength=80,
    #                      padx=3, pady=3,
    #                      relief="solid", bg="lightblue")


class StackCardboard(StackObject):

    def __init__(self, card: Cardboard, choices: list, putter: PlayCard):
        super().__init__()
        self.ability: None = None
        self.card: Cardboard = card
        self.choices: list = choices
        self.verb_to_put_it_onto_stack = putter

    def __str__(self):
        return "Spell: " + self.card.name

    def __repr__(self):
        return "Spell: " + self.card.name

    def copy(self, new_card: Cardboard, new_choices: list) -> StackCardboard:
        new_obj = StackCardboard(new_card, new_choices,
                                 self.verb_to_put_it_onto_stack)
        new_obj.ability = self.ability
        return new_obj

    # def build_tk_display(self, parentframe, ):
    #     return tk.Button(parentframe,
    #                      text="Effect: %s" % self.name,
    #                      anchor="w",
    #                      height=7, width=10, wraplength=80,
    #                      padx=3, pady=3,
    #                      relief="solid", bg="lightblue")
