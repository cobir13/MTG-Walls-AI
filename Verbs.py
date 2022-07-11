# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING
import random

from VerbParents import Verb, VerbAtomic, VerbOnSubjectCard, VerbOnTarget

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard

import ZONE
import MatchCardPatterns as Match
import Getters as Get
import ManaHandler


class WinTheGameError(Exception):
    pass


class LoseTheGameError(Exception):
    pass


# ------------------------------------------------------------------------------

class PayMana(VerbAtomic):
    """deducts the given amount of mana from the GameState's mana pool"""

    def __init__(self, mana_string: str):
        super().__init__()
        self.mana_cost = ManaHandler.ManaCost(mana_string)

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return state.pool.can_afford_mana_cost(self.mana_cost)

    def do_it(self, state, subject, choices):
        state.pool.pay_mana_cost(self.mana_cost)
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def __str__(self):
        return "PayMana{%s}" % str(self.mana_cost)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            text = "\nPay %s" % str(self.mana_cost)
            state.events_since_previous += text


# ----------

class AddMana(VerbAtomic):
    """adds the given amount of mana to the GameState's mana pool"""

    def __init__(self, mana_string: str):
        super().__init__()
        self.mana_pool_to_add = ManaHandler.ManaPool(mana_string)

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject, choices):
        state.pool.add_mana(self.mana_pool_to_add)
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def __str__(self):
        return "AddMana{%s}" % str(self.mana_pool_to_add)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            text = "\nAdd %s" % str(self.mana_pool_to_add)
            state.events_since_previous += text


# =============================================================================

class LoseOwnLife(VerbAtomic):
    def __init__(self, damage_getter: Get.Integer | int):
        super().__init__()
        if isinstance(damage_getter, int):
            damage_getter = Get.ConstInteger(damage_getter)
        self.getter_list = [damage_getter]

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject, choices):
        damage = choices[0]
        state.life -= damage
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            text = "\nLose %i life" % self.getter_list[0].get(state, subject)
            state.events_since_previous += text


# ----------

class DealDamageToOpponent(VerbAtomic):
    def __init__(self, damage_getter: Get.Integer | int):
        super().__init__()
        if isinstance(damage_getter, int):
            damage_getter = Get.ConstInteger(damage_getter)
        self.getter_list = [damage_getter]

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject, choices):
        damage = choices[0]
        state.opponent_life -= damage
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            text = "\nDeal %i damage" % self.getter_list[0].get(state, subject)
            state.events_since_previous += text


# ----------

class TapSelf(VerbOnSubjectCard):
    """taps `subject` if it was not already tapped."""

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return subject.zone == ZONE.FIELD and not subject.tapped

    def do_it(self, state, subject, choices):
        subject.tapped = True
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class TapAny(VerbOnTarget):

    def __init__(self, patterns: List[Match.CardPattern]):
        getter = Get.Chooser(Get.ListFromZone(patterns, ZONE.FIELD), 1, False)
        super().__init__(getter, TapSelf())


# ----------

class UntapSelf(VerbOnSubjectCard):

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return subject.tapped and subject.zone == ZONE.FIELD

    def do_it(self, state, subject, choices):
        subject.tapped = False
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)


# ----------

class AddCounterToSelf(VerbOnSubjectCard):
    """Adds the given counter string to the subject card"""

    def __init__(self, counter_text: str):
        super().__init__()
        self.counter_text = counter_text

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return subject.zone == ZONE.FIELD

    def do_it(self, state, subject, choices):
        subject.add_counter(self.counter_text)
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            text = "\nPut %s counter on %s" % (self.counter_text, subject.name)
            state.events_since_previous += text


# ----------

class ActivateOncePerTurn(VerbOnSubjectCard):
    """Marks the given `subject` as only able to activate this ability once
    per turn"""

    def __init__(self, ability_name: str):
        super().__init__()
        self.counter_text = "@" + ability_name  # "@" is invisible counter

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return (subject.zone == ZONE.FIELD
                and self.counter_text not in subject.counters)

    def do_it(self, state, subject, choices):
        subject.add_counter(self.counter_text)
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        return  # doesn't mark itself as having done anything


# ----------

class ActivateOnlyAsSorcery(VerbAtomic):
    """Checks that the stack is empty and cannot be done otherwise"""

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return len(state.stack) == 0

    def do_it(self, state, subject, choices):
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        return  # doesn't mark itself as having done anything


# ----------

class Shuffle(VerbAtomic):
    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject: Cardboard | None, choices):
        # add triggers to super_stack, reduce length of choices list
        """Mutates. Reorder deck randomly."""
        random.shuffle(state.deck)
        return super().do_it(state, subject, choices)

    @property
    def mutates(self):
        return True

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        if state.is_tracking_history:
            state.events_since_previous += "\nShuffle"


# ----------

class MoveToZone(VerbOnSubjectCard):
    """Moves the subject card to the given zone
    NOTE: cannot actually remove the subject card from the
    stack (because it's wrapped in a StackObject).
    NOTE: cannot actually add the subject card to the stack
    (because it's wrapped in a StackObject) or to the deck
    (because it's unclear if it should be added to the top
    or to the bottom).
    In both of these cases, the function does as much of the
    move as it can (sets Cardboard.zone, removes even if it
    can't add, etc.) and hopes that the calling function will
    know to do the rest.
    """

    def __init__(self, destination_zone):
        super().__init__()
        self.destination = destination_zone
        self.origin = None  # to let triggers check where card moved from

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        if subject.zone in [ZONE.DECK, ZONE.DECK_BOTTOM, ZONE.HAND,
                            ZONE.FIELD, ZONE.GRAVE]:
            return subject in state.get_zone(subject.zone)

    def do_it(self, state, subject, choices=()):
        # NOTE: Cardboard can't live on the stack. only StackObjects do. So
        # reassign card zone and remove/add to zones as appropriate, but never
        # directly add or remove from the stack. StackCardboard does the rest.
        self.origin = subject.zone  # so trigger knows where card moved from
        # remove from origin
        if self.origin in [ZONE.DECK, ZONE.DECK_BOTTOM, ZONE.HAND,
                           ZONE.FIELD, ZONE.GRAVE]:
            state.get_zone(self.origin).remove(subject)
        # add to destination
        subject.zone = self.destination
        if self.destination in [ZONE.HAND, ZONE.FIELD, ZONE.GRAVE]:
            # these three zones must remain sorted at all times
            zone_list = state.get_zone(self.destination)
            zone_list.append(subject)  # can add to any index b/c about to sort
            state.re_sort(self.destination)
        elif self.destination == ZONE.DECK:
            state.deck.insert(0, subject)  # add to top (index 0) of deck
        elif self.destination == ZONE.DECK_BOTTOM:
            state.deck.append(subject)  # add to bottom (index -1) of deck
        # any time you change zones, reset the cardboard parameters
        subject.reset_to_default_cardboard()
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def __str__(self):
        if self.destination == ZONE.DECK:
            text = "Deck"
        elif self.destination == ZONE.DECK_BOTTOM:
            text = "BottomOfDeck"
        elif self.destination == ZONE.HAND:
            text = "Hand"
        elif self.destination == ZONE.FIELD:
            text = "Field"
        elif self.destination == ZONE.GRAVE:
            text = "Grave"
        elif self.destination == ZONE.STACK:
            text = "Stack"
        else:
            raise IndexError
        return "MoveTo" + text


# ----------

class NullVerb(Verb):
    """This Verb does literally nothing, ever. It is always
    do-able, has 0 inputs, does not mutate, and is silent.
    It's a Null Verb. Exactly what it says on the tin."""

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return True

    def do_it(self, state, subject: Cardboard | None, choices):
        return [(state, subject, choices)]

    @property
    def mutates(self):
        return False

    @property
    def num_inputs(self):
        return 0

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        return


# ----------

class DrawCard(VerbAtomic):
    """draw from index 0 of deck"""

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard | None,
                    choices: list) -> bool:
        return True  # Even if the deck is 0, you CAN draw. you'll just lose

    def do_it(self, state, subject: Cardboard | None, choices: list | None):
        if len(state.deck) > 0:
            mover = MoveToZone(ZONE.HAND)
            mover.do_it(state,
                        state.deck[0], )  # adds move triggers to super_stack
            # add triggers to super_stack, reduce length of choices list
            return super().do_it(state, subject, choices)
        else:
            raise LoseTheGameError


# ----------

class PlayLandForTurn(VerbAtomic):
    """Doesn't actually move any cards, just toggles the gamestate to say
    that we have played a land this turn"""

    def __init__(self):
        super().__init__()

    def can_be_done(self, state: GameState, subject: Cardboard,
                    choices: list) -> bool:
        return not state.has_played_land

    def do_it(self, state, subject, choices):
        state.has_played_land = True
        # add triggers to super_stack, reduce length of choices list
        return super().do_it(state, subject, choices)

    def add_self_to_state_history(self, state: GameState,
                                  subject: Cardboard, choices: list):
        return
