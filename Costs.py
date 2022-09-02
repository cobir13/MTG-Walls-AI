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
        self.mana_cost: ManaCost | None = None  # overwrite later if exists
        if len(args) > 0:
            if isinstance(args[0], str):
                self.mana_cost = ManaCost(args[0])
                args = args[1:]
            elif isinstance(args[0], ManaCost):
                self.mana_cost = args[0]
                args = args[1:]
        self.additional: List[Verb] = list(args)
        self.num_inputs = sum([v.num_inputs for v in self.additional])
        self.mana_value = 0
        if self.mana_cost is not None:
            self.mana_value = self.mana_cost.cmc()

    def _get_multi_verb(self) -> Verb:
        if self.mana_cost is None:
            if len(self.additional) == 0:
                return NullVerb()
            elif len(self.additional) == 1:
                return self.additional[0]
            else:  # longer than 1
                return MultiVerb(self.additional)
        else:
            mana_verb = PayMana(str(self.mana_cost))
            if len(self.additional) > 0:
                # noinspection PyTypeChecker
                return MultiVerb([mana_verb] + self.additional[:])
            else:
                return mana_verb

    def get_payment_plans(self, state: GameState, controller: int,
                          source: Cardboard | None, cause: Cardboard | None
                          ) -> List[Verb]:
        """Return list of Verbs giving valid ways to pay the cost"""
        opts = self._get_multi_verb().populate_options(state, controller,
                                                       source, cause)
        return [v for v in opts if v.can_be_done(state)]

    def __str__(self):
        if self.mana_cost is not None and len(self.additional) > 0:
            return str(self.mana_cost) + "+" + str(self._get_multi_verb())
        elif self.mana_cost is not None:
            return str(self.mana_cost)
        elif len(self.additional) > 0:
            return str(self._get_multi_verb())
        else:  # both are None, essentially
            return "0"
