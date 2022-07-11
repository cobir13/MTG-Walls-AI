from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Cardboard import Cardboard
    from Abilities import GenericAbility
    from VerbParents import Verb, ManyVerbs
from Verbs import MoveToZone
from Stack import StackObject


class StackCardboard(StackObject):

    def __init__(self, card: Cardboard, choices: list):
        super().__init__()
        self.ability: GenericAbility | None = None
        self.card: Cardboard = card
        self.choices: list = choices

    @property
    def effect(self) -> Verb:
        # Cards always need to be moved to their destination zone as part
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
        return "Spell: " + self.card.name

    def __repr__(self):
        return "Spell: " + self.card.name

    # def build_tk_display(self, parentframe, ):
    #     return tk.Button(parentframe,
    #                      text="Effect: %s" % self.name,
    #                      anchor="w",
    #                      height=7, width=10, wraplength=80,
    #                      padx=3, pady=3,
    #                      relief="solid", bg="lightblue")


