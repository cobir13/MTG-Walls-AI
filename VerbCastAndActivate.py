from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Abilities import ActivatedAbility
    from Cardboard import Cardboard
    from GameState import GameState

import ZONE
from StackCardboard import StackCardboard
from Stack import StackAbility
from RulesText import Land, Creature
from VerbParents import VerbAtomic, VerbOnSubjectCard
from Verbs import AddMana, MoveToZone, TapSelf
import MatchCardPatterns as Match


class ActivateAbility(VerbAtomic):
    def __init__(self, ability: ActivatedAbility):
        super().__init__()
        self.ability = ability

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        """Activate the ability. The source of the ability is
        assumed to be the `subject` Cardboard.
        """
        pay_choices = choices[:self.ability.cost.num_inputs]
        targets = choices[self.ability.cost.num_inputs:]
        return (self.ability.cost.can_be_done(state, subject, pay_choices) and
                self.ability.effect.can_be_done(state, subject, targets))

    def do_it(self, state: GameState, subject: Cardboard, choices: list):
        """Activate the ability. The source of the ability is
        assumed to be the `subject` Cardboard. `choices` describe
        the choices for paying for the ability, followed by choices
        for using the ability. Note that super_stack is NOT
        guaranteed to be clear!
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
        copy_of_game, things = state.copy_and_track([subject] + choices)
        copy_of_spell = things[0]
        copy_of_choices = things[1:]
        # The casting will chew through all the payment choices, leaving only
        # the target choices in the resulting tuples. Then those tuples are
        # returned as a list of (GameState, Cardboard, choices) tuples.
        list_of_tuples = self.ability.cost.do_it(copy_of_game, copy_of_spell,
                                                 copy_of_choices)
        # Build a StackAbility and add it to the stack
        if not self.ability.is_type(AddMana):
            for g1, s1, targets in list_of_tuples:
                g1.stack.append(StackAbility(self.ability, s1, targets))
        # ...except for Mana Abilities which don't use the stack
        else:
            new_tuple_list = []
            for g1, s1, targets in list_of_tuples:
                new_tuple_list += self.ability.effect.do_it(g1, s1, targets)
            list_of_tuples = new_tuple_list
        # 601.2i: ability has now "been activated".  Any abilities which
        # trigger from some aspect of paying the costs have already
        # been added to the superstack during ability.cost.pay. Now add
        # any trigger that trigger off of this activation itself.
        final_results = []
        for g2, s2, targets2 in list_of_tuples:
            final_results += super().do_it(g2, s2, targets2)
        return final_results

    def choose_choices(self, state: GameState, subject: Cardboard):
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payment_choices = self.ability.cost.choose_choices(state, subject)
        # 601.2c: choose targets and modes
        target_choices = self.ability.effect.choose_choices(state, subject)
        # combine all combinations of these
        new_choices = []
        for sub_pay in payment_choices:
            for sub_target in target_choices:
                new_choices.append(
                    sub_pay + sub_target)  # concatenate sub-lists
        return new_choices

    def mutates(self):
        return False

    def num_inputs(self):
        return self.ability.cost.num_inputs + self.ability.effect.num_inputs

    def __str__(self):
        return "Activate " + str(self.ability)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            record = "\n*** Activate %s ***" % self.ability.name
            # if len(choices) > 0:
            #     record += " {%s}" % ", ".join([str(c) for c in choices])
            state.events_since_previous += record


class CastCard(VerbOnSubjectCard):
    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        """Cast the `source` card"""
        cost = subject.rules_text.cost
        pay_choices = choices[:cost.num_inputs]
        if not cost.can_be_done(state, subject, pay_choices):
            return False
        if subject.effect is not None:
            target_choices = choices[cost.num_inputs:]
            if not subject.effect.can_afford(state, subject, target_choices):
                return False
        return True

    def do_it(self, state, subject, choices):
        """Puts the `source` card on the stack, including making any
        choices necessary to do that. Returns (GameState,Cardboard)
        copies but does not mutate. Note that super_stack is NOT
        guaranteed to be clear!"""
        # check to make sure the execution is legal
        if not self.can_be_done(state, subject, choices):
            return []
        # 601.2b: choose costs (additional costs, choose X, choose hybrid).
        # this has already been done by choices.
        # 601.2c: choose targets and modes -- already done by choices.
        # 601.2f: determine total cost -- part of payment for me, I think?
        # 601.2g: activate mana abilities -- I don't actually permit this.
        # 601.2h: pay costs
        copy_of_game, things = state.copy_and_track([subject] + choices)
        copy_of_spell = things[0]
        copy_of_choices = things[1:]
        # The casting will chew through all the payment choices, leaving only
        # the target choices in the resulting tuples. Then those tuples are
        # returned as a list of (GameState, Cardboard, choices) tuples.
        # Make the do_it "silent" by temporarily wiping the recorder function
        list_of_tuples = subject.cost.do_it(copy_of_game, copy_of_spell,
                                            copy_of_choices)
        # Build a StackCardboard and add it to the stack
        for g1, s1, targets in list_of_tuples:
            # Special exception for lands, which go directly to play
            if subject.has_type(Land):
                # mutate in-place
                MoveToZone(ZONE.FIELD).do_it(g1, s1, targets)
            else:
                # MoveToZone doesn't actually PUT the Cardboard anywhere. It
                # knows the stack is for StackObjects only. Just removes from
                # hand. Mutates in-place.
                MoveToZone(ZONE.STACK).do_it(g1, s1, targets)
                g1.stack.append(StackCardboard(s1, targets))
                g1.num_spells_cast += 1
        # 601.2i: ability has now "been activated".  Any abilities which
        # trigger from some aspect of paying the costs have already
        # been added to the superstack during ability.cost.pay. Now add
        # any trigger that trigger off of this casting itself.
        final_results = []
        for g2, s2, targets2 in list_of_tuples:
            final_results += super().do_it(g2, s2, targets2)
        return final_results

    def choose_choices(self, state: GameState, subject: Cardboard):
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payment_choices = subject.cost.choose_choices(state, subject)
        # 601.2c: choose targets and modes
        if subject.effect is not None:
            target_choices = subject.effect.choose_choices(state, subject)
            # combine all combinations of these
            new_choices = []
            for sub_pay in payment_choices:
                for sub_target in target_choices:
                    # concatenate sub-lists
                    new_choices.append(sub_pay + sub_target)
            return new_choices
        else:
            return payment_choices

    def mutates(self):
        return False

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            record = "\n*** Cast %s ***" % subject.name
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
