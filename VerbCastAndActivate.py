from __future__ import annotations
from typing import TYPE_CHECKING, Tuple, List

if TYPE_CHECKING:
    from Cardboard import Cardboard
    from GameState import GameState
    from Stack import StackObject
    from Verbs import Verb

import ZONE
from RulesText import Creature
from VerbParents import VerbAtomic
from Verbs import MoveToZone, TapSelf, NullVerb
import MatchCardPatterns as Match


class PutStackObjectOnStack(VerbAtomic):
    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        """Assumes `choices` contains a single element, the StackObject to
        pay for and then put onto the stack. `subject` argument is ignored.
        """
        stack_obj: StackObject = choices[0]
        real_subject = stack_obj.card
        cost: Verb = (stack_obj.cost if stack_obj.cost is not None
                      else NullVerb())
        effect: Verb = (stack_obj.effect if stack_obj.effect is not None
                        else NullVerb())
        pay_choices = stack_obj.choices[:cost.num_inputs]
        targets = stack_obj.choices[cost.num_inputs:]
        return (cost.can_be_done(state, real_subject, pay_choices) and
                effect.can_be_done(state, real_subject, targets))

    def do_it(self, state: GameState, subject: Cardboard, choices: list):
        """Assumes `choices` contains a single element, the StackObject to
        pay for and then put onto the stack. `subject` argument is ignored.
        DOES NOT MUTATE.
        """
        # check to make sure the execution is legal
        if not self.can_be_done(state, subject, choices):
            return []

        # 601.2b: choose costs (additional costs, choose X, choose hybrid).
        # this has already been done by choices.
        # 601.2c: choose targets and modes -- already done by choices.
        # 601.2f: determine total cost -- part of payment for me, I think?
        # 601.2g: activate mana abilities -- I don't actually permit this.
        # 601.2h: pay costs
        stack_obj: StackObject = choices[0]
        cost: Verb = (stack_obj.cost if stack_obj.cost is not None
                      else NullVerb())
        originals_to_track = [stack_obj.card] + stack_obj.choices
        copy_of_game, things = state.copy_and_track(originals_to_track)
        copy_of_spell = things[0]
        copy_of_choices = things[1:]

        need to remove card from previous location if it's a card!'


        # The casting will chew through all the payment choices, leaving only
        # the target choices in the resulting tuples. Then those tuples are
        # returned as a list of (GameState, Cardboard, choices) tuples.
        list_of_tuples = cost.do_it(copy_of_game, copy_of_spell,
                                    copy_of_choices)
        # Build an updated copy of the StackObject and add it to the stack.
        # OR do something stranger, like for lands and mana abilities. It
        # might mutate and that's ok (here, at least).
        list_of_tuples = self._put_on_stack(list_of_tuples, stack_obj)
        # 601.2i: ability has now "been activated".  Any abilities which
        # trigger from some aspect of paying the costs have already
        # been added to the superstack during ability.cost.pay. Now add
        # any trigger that trigger off of this activation itself.
        final_results = []
        for g2, s2, targets2 in list_of_tuples:
            final_results += super().do_it(g2, s2, targets2)
        return final_results

    def choose_choices(self, state: GameState, subject: Cardboard):
        return []  # all choices have already been made by the StackObject

    def mutates(self):
        return False

    def num_inputs(self):
        return 0

    def _put_on_stack(self,
                      list_of_tuples: List[Tuple[GameState, Cardboard, list]],
                      stack_obj: StackObject
                      ) -> List[Tuple[GameState, Cardboard, list]]:
        for g1, s1, targets in list_of_tuples:
            new_obj = stack_obj.copy(new_card=s1, new_choices=targets)
            g1.stack.append(new_obj)
        return list_of_tuples


class PlayAbility(PutStackObjectOnStack):
    def __init__(self):
        super().__init__()

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            record = "\n*** Activate %s ***" % choices[0].ability.name
            state.events_since_previous += record


class PlayManaAbility(PlayAbility):
    def __init__(self):
        super().__init__()

    def _put_on_stack(self,
                      list_of_tuples: List[Tuple[GameState, Cardboard, list]],
                      stack_obj: StackObject
                      ) -> List[Tuple[GameState, Cardboard, list]]:
        """mana abilities don't use stack. just execute it."""
        new_tuple_list = []
        for g1, s1, targets in list_of_tuples:
            new_tuple_list += stack_obj.ability.effect.do_it(g1, s1, targets)
        return new_tuple_list


class AddTriggeredAbility(PutStackObjectOnStack):
    pass




class PlayCard(PutStackObjectOnStack):
    def __init__(self):
        super().__init__()


class PlayLand(PlayCard):
    def __init__(self):
        super().__init__()

    def _put_on_stack(self,
                      list_of_tuples: List[Tuple[GameState, Cardboard, list]],
                      stack_obj: StackObject
                      ) -> List[Tuple[GameState, Cardboard, list]]:
        """Lands don't go to stack. Just move it directly to play"""
        new_tuple_list = []
        mover = MoveToZone(ZONE.FIELD)
        for g1, s1, targets in list_of_tuples:
            new_tuple_list += mover.do_it(g1, s1, targets)
        return new_tuple_list

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            record = "\n*** Play land %s ***" % subject.name
            # if len(choices) > 0:
            #     record += " {%s}" % ", ".join([str(c) for c in choices])
            state.events_since_previous += record





















# ----------

class TapSymbol(TapSelf):
    """{T}. `subject` gets tapped if it's not a summoning-sick creature"""

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return (super().can_be_done(state, subject, choices)
                and not (Match.CardType(Creature).match(subject, state,
                                                        subject)
                         and subject.summon_sick))

    def __str__(self):
        return "{T}"
