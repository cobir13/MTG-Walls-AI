from __future__ import annotations
from typing import TYPE_CHECKING, List

from ManaHandler import ManaCost
from Verbs import Verb, PayMana, MultiVerb, NullVerb

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard


class Cost:
    def __init__(self, *args: str | ManaCost | Verb):
        """If cost includes paying mana, that should be the
        first argument. Otherwise, proceed directly to Verb
        arguments."""
        self.base_mana_cost: ManaCost | None = None  # to overwrite later
        if len(args) > 0:
            if isinstance(args[0], str):
                self.base_mana_cost = ManaCost(args[0])
                args = args[1:]
            elif isinstance(args[0], ManaCost):
                self.base_mana_cost = args[0]
                args = args[1:]
        self.additional: List[Verb] = list(args)
        # pre-calculate mana_value integer because it never changes
        if self.base_mana_cost is None:
            self.mana_value = 0
        else:
            self.mana_value = self.base_mana_cost.cmc()

    def _get_multi_verb(self) -> Verb:
        if self.base_mana_cost is None:
            if len(self.additional) == 0:
                return NullVerb()
            elif len(self.additional) == 1:
                return self.additional[0]
            else:  # longer than 1
                return MultiVerb(self.additional)
        else:
            mana_verb = PayMana(str(self.base_mana_cost))
            if len(self.additional) > 0:
                # noinspection PyTypeChecker
                return MultiVerb([mana_verb] + self.additional[:])
            else:
                return mana_verb

    def get_payment_plans(self, state: GameState, controller: int,
                          source: Cardboard | None, cause: Cardboard | None
                          ) -> List[Verb] | [None]:
        """Return list of Verbs giving valid ways to pay the cost.
        If there is no cost to pay, return [None] to mean that
        nothing needs to be done. If the cost cannot be paid,
        return [] to mean that there is no valid way in which to
        pay the cost."""
        if self.base_mana_cost is None and len(self.additional) == 0:
            return [None]
        else:
            opts = self._get_multi_verb().populate_options(state, controller,
                                                           source, cause)
            return [v for v in opts if v.can_be_done(state)]

    def __str__(self):
        if self.base_mana_cost is not None and len(self.additional) > 0:
            return str(self.base_mana_cost) + "+" + str(self._get_multi_verb())
        elif self.base_mana_cost is not None:
            return str(self.base_mana_cost)
        elif len(self.additional) > 0:
            return str(self._get_multi_verb())
        else:  # both are None, essentially
            return "0"
