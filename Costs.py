from __future__ import annotations
from typing import TYPE_CHECKING, List

from ManaHandler import ManaCost
from Verbs import Verb, PayMana, ManyVerbs, NullVerb

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

    def _get_multi_verb(self) -> Verb:
        if self.mana_cost is None:
            if len(self.additional) == 0:
                return NullVerb()
            elif len(self.additional) == 1:
                return self.additional[0]
            else:  # longer than 1
                return ManyVerbs(self.additional)
        else:
            mana_verb = PayMana(str(self.mana_cost))
            if len(self.additional) > 0:
                return ManyVerbs([mana_verb] + self.additional)
            else:
                return mana_verb

    @property
    def mana_value(self) -> int:
        if self.mana_cost is not None:
            return self.mana_cost.cmc()
        else:
            return 0

    @property
    def num_inputs(self) -> int:
        return sum([v.num_inputs for v in self.additional])

    def can_afford(self, state: GameState, subject: Cardboard, choices: list):
        if self.mana_cost is None:
            afford_mana = True
        else:
            afford_mana = state.pool.can_afford_mana_cost(self.mana_cost)
        afford_other = all([v.can_be_done(state, subject, choices)
                            for v in self.additional])
        return afford_mana and afford_other

    def pay_cost(self, state: GameState, subject: Cardboard, choices: list):
        return self._get_multi_verb().do_it(state, subject, choices)

    def get_options(self, state: GameState, source: Cardboard | None,
                    cause: Cardboard | None):
        return self._get_multi_verb().choose_choices(state, source, cause)

    def __str__(self):
        return str(self.mana_cost) + "+" + str(self._get_multi_verb())


