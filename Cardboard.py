# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""

from __future__ import annotations

import Stack
import ZONE
import tkinter as tk
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from GameState import GameState
    from Verbs import Verb
    from Stack import StackCardboard

from RulesText import RulesText
import Costs


# -----------------------------------------------------------------------------

class Cardboard:
    """Represents the physical piece of cardboard that is a Magic card.
    """

    # needs to not overwrite equality, because I often check if a card is in
    # a list and I need the `in` functionality to use `is` rather than `==`.
    # Unfortunately, this also means I can't drop Cardboards into sets to sort.

    def __init__(self, rules_text: RulesText):
        self.rules_text: RulesText = rules_text
        self.tapped: bool = False
        self.summon_sick: bool = True  # Has been in play since upkeep? No.
        self.counters: List[
            str] = []  # sorted list of counters. Also other trackers
        # track where the card is: index (within a gamestate) of the player
        # who controls it, index of the player who ownes it, and its zone.
        self.player_index = -1  # controller. duck-type to Player.index
        self.owner_index = -1
        self.zone = ZONE.NEW

    def __str__(self):
        s = self.rules_text.name
        if self.zone == ZONE.FIELD and self.tapped:
            s += "(T)"
        if len(self.counters) > 0:
            s += "[%s]" % ",".join(self.counters)
        return s

    def __repr__(self):
        return "Card " + self.get_id()

    def copy(self):
        new_card = Cardboard(self.rules_text)
        # RulesText never mutates so it's ok that they're both pointing at the
        # same instance of a RulesText
        new_card.rules_text = self.rules_text
        # safe to copy by reference since they're all ints, str, etc
        new_card.tapped = self.tapped
        new_card.summon_sick = self.summon_sick
        new_card.player_index = self.player_index
        new_card.owner_index = self.owner_index
        new_card.zone = self.zone
        # counters is a LIST so it needs to be copied without reference
        new_card.counters = self.counters.copy()
        return new_card

    def copy_as_pointer(self, state_orig: GameState, state_new: GameState):
        """A more careful version of copy. This one first
        checks to see if the card is secretly a "pointer"
        to a card which already exists in the new GameState.
        If it is, returns the card in the new GameState. If
        it is not, returns a fresh copy of the card.
        Useful when copying spells on the stack."""
        if self.zone == ZONE.STACK:
            # TODO: on-cast trigger would have a source pointing to stack
            return self.copy()  # if on stack, can't be a pointer.
        try:
            zone_orig = self.get_home_zone_list(state_orig)
            zone_new = self.get_home_zone_list(state_new)
            # look for true equality (not just equivalence) in old cards
            indices = [ii for ii, c in enumerate(zone_orig) if c is self]
            if len(indices) > 0:
                return zone_new[indices[0]]
            else:
                return self.copy()  # couldn't find, so copy.
        except ValueError:
            # no zone. Maybe is new? Anyway, just make a fresh copy.
            return self.copy()

    def add_counter(self, addition):
        self.counters = sorted(self.counters + [addition])

    @property
    def name(self) -> str:
        return self.rules_text.name

    @property
    def cost(self) -> Costs.Cost:
        return self.rules_text.cost

    @property
    def effect(self) -> Verb:
        return self.rules_text.effect

    def get_home_zone_list(self, state: GameState):
        if self.zone in [ZONE.NEW, ZONE.UNKNOWN]:
            raise ValueError("Can't be in Zone because has no owner!")
        elif self.zone == ZONE.STACK:
            return state.stack
        else:
            return state.player_list[self.player_index].get_zone(self.zone)

    def get_activated(self):
        return self.rules_text.activated

    def get_id(self):
        s = type(
            self.rules_text).__name__  # MtG card type (creature, land, etc)
        # s += self.rules_text.name + "_"
        if self.tapped:
            s += "T"
        if self.summon_sick:
            s += "S"
        s += "_P%iz%s" % (self.player_index, str(self.zone))
        if len(self.counters) > 0:
            s += "[" + ",".join(self.counters) + "]"
        return s

    def is_equiv_to(self, other):
        if not isinstance(other, Cardboard):
            return False
        else:
            return self.get_id() == other.get_id()

    def __eq__(self, other):
        return self is other  # pointer equality.
        # I need "is" equality for "is Cardboard in GameState list". That needs
        # to care about same-object not just whether two Cardboards are
        # equivalent or not. I defined EquivTo as a more intuitive, descriptive
        # definition of equality that I use for comparing two GameStates.

    def has_type(self, card_type: type) -> bool:
        """Returns bool: "this Cardboard refers to a card which is the given
        RulesText type (in addition to possibly other types as well)" """
        return isinstance(self.rules_text, card_type)

    # def has_keyword(self, keyword:str):
    #     return keyword in self.rules_text.keywords

    def mana_value(self) -> int:
        return self.rules_text.mana_value

    def reset_to_default_cardboard(self):
        self.tapped = False
        self.summon_sick = True
        self.counters = [c for c in self.counters if
                         c[0] == "$"]  # sticky counters stay

    def valid_stack_objects(self, state: GameState) -> List[StackCardboard]:
        """Create as many valid StackCardboards as possible,
        one for each valid way to cast this Cardboard.
        This function doesn't ACTUALLY add them to stack
        or pay their costs, it just works out the payment
        options and target options and makes usable
        StackObjects accordingly. If the card cannot be
        cast, the empty list is returned."""
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        player = state.player_list[self.player_index]
        payments = self.cost.get_options(state, player, self, None)
        # keep only the valid ones
        payments = [ch for ch in payments if self.cost.can_afford(state, *ch)]
        # 601.2c: choose targets and modes
        targets = self.effect.get_input_options(state, player, self, None)
        targets = [ch for ch in targets if
                   self.effect.can_be_done(state, INT,, *ch]
        # combine all combinations of these
        obj_list = []
        for sub_pay in payments:
            for sub_target in targets:
                # concatenate sub-lists
                inputs = sub_pay + sub_target
                # figure out which verb can be used to cast this object
                caster_verb = self.rules_text.caster_verb
                obj = Stack.StackCardboard(None, self, inputs, caster_verb)
                obj_list.append(obj)
        return obj_list

    def build_tk_display(self, parent_frame):
        """Returns a tkinter button representing the Cardboard.
        Note: clicking the button won't do anything yet. Setting up the button
        so that clicking it will cast the card or activate its abilities is
        the responsibility of whatever is building the GUI.
        Similarly, whatever calls this function is responsible for adding the
        button to the tkinter frame so that it actually appears on screen.
        """
        # string for mana cost (if any)
        cost_string = ""
        if self.mana_value() > 0:
            cost_string = "(" + str(self.rules_text.mana_cost) + ")"
        # string for name
        # text += "".join([l if l.islower() else " "+l for l in self.name])[1:]
        name_string = self.name
        # string for power and toughness, if any
        power_toughness_string = ""
        if hasattr(self.rules_text, "power") and hasattr(self.rules_text,
                                                         "toughness"):
            power_toughness_string = "%i/%i" % (self.rules_text.power,
                                                self.rules_text.toughness)
            # string for counters, if any
        counter_string = ""
        for c in set(self.counters):
            if c[0] != "@":
                counter_string += "[%s]" % c
                if self.counters.count(c) > 1:
                    counter_string += "x%i" % self.counters.count(c)
                counter_string += "\n"
        # configure text. tapped and untapped display differently
        if self.tapped:
            text = " " * (27 - len(name_string)) + name_string + "\n"
            text += counter_string
            while text.count("\n") < 3:
                text += "\n"
            text += power_toughness_string
            text += " " * (30 - len(power_toughness_string) - len(cost_string))
            text += cost_string
        else:
            text = " " * (20 - len(cost_string)) + cost_string + "\n"
            text += name_string + "\n"
            text += counter_string
            while text.count("\n") < 6:
                text += "\n"
            text += " " * (20 - len(power_toughness_string))
            text += power_toughness_string
        # build the button and return it
        # noinspection SpellCheckingInspection
        button = tk.Button(parent_frame,
                           text=text, anchor="w",
                           height=4 if self.tapped else 7,
                           width=15 if self.tapped else 10,
                           wraplength=110 if self.tapped else 80,
                           padx=3, pady=3,
                           relief="raised", bg='lightgreen')
        return button


class CardNull(Cardboard):

    def __init__(self):
        super().__init__(RulesText())
        self.rules_text: None
        self.tapped: bool = False
        self.summon_sick: bool = True
        self.counters = []
        self.zone = ZONE.NEW

    def __str__(self):
        return "Null"

    def __repr__(self):
        return "NullCard"

    def copy(self):
        return CardNull()

    def add_counter(self, addition):
        return

    @property
    def name(self):
        return "Null"

    @property
    def cost(self):
        return None

    @property
    def effect(self):
        return None

    def get_activated(self):
        return []

    def get_id(self):
        return ""

    def is_equiv_to(self, other):
        return False

    def __eq__(self, other):
        return False

    def has_type(self, card_type: type) -> bool:
        return False

    def mana_value(self):
        return None

# if __name__ == "__main__":
#     import Decklist
#
#     window = tk.Tk()
#     frame = tk.Frame(window)
#     frame.grid(padx=5, pady=5)
#
#     c1 = Cardboard(Decklist.Roots)
#     c1.build_tk_display(frame).grid(row=0, column=0, padx=5)
#     c2 = Cardboard(Decklist.Caretaker)
#     c2.build_tk_display(frame).grid(row=0, column=1, padx=5)
#
#     c4 = Cardboard(Decklist.Caretaker)
#     c4.tapped = True
#     c4.build_tk_display(frame).grid(row=0, column=2, padx=5)
#
#     # c3 = Cardboard(Decklist.WindsweptHeath)
#     # c3.tapped = True
#     # c3.build_tk_display(frame).grid(row=0, column=3, padx=5)
#
#     window.mainloop()
