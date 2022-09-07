# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""

from __future__ import annotations

import Stack
import Zone
import tkinter as tk
from typing import List, TYPE_CHECKING, Type

if TYPE_CHECKING:
    from GameState import GameState
    from Verbs import Verb, PlayCardboard

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
        self.owner_index = -1  # None?
        self.zone = Zone.Unknown()

    def __str__(self):
        s = self.rules_text.name
        if self.is_in(Zone.Field) and self.tapped:
            s += "(T)"
        if len(self.counters) > 0:
            s += "[%s]" % ",".join(self.counters)
        return s

    def __repr__(self):
        s = "Card_"
        s += type(self.rules_text).__name__  # MtG type (creature, land, etc)
        if self.tapped or self.summon_sick:
            s += "_"
        if self.tapped:
            s += "T"
        if self.summon_sick:
            s += "S"
        s += "_%s" % str(self.zone)
        if self.zone.location is not None:
            s += "[%s]" % str(self.zone.location)
        if len(self.counters) > 0:
            s += "_[" + ",".join(self.counters) + "]"
        return s

    def copy(self, state_new: GameState | None = None):
        """A more careful version of copy. This one first
        checks to see if the card is secretly a "pointer"
        to a card which already exists in the new GameState.
        If it is, returns the card in the new GameState. If
        it is not, returns a fresh copy of the card.
        Useful when copying spells on the stack."""
        if state_new is None:
            new_card = Cardboard(self.rules_text)
            # RulesText never mutates so it's ok that they're both pointing
            # at the same instance of a RulesText
            new_card.rules_text = self.rules_text
            # safe to copy by reference since they're all ints, str, etc
            new_card.tapped = self.tapped
            new_card.summon_sick = self.summon_sick
            new_card.owner_index = self.owner_index
            # counters is a LIST so it needs to be copied without reference
            new_card.counters = self.counters.copy()
            # zone can mutate, I think?  safer to copy not refer
            new_card.zone = self.zone.copy()
            return new_card
        else:
            assert self.zone.location is not None  # for debug
            new_home = self.zone.get(state_new)
            if len(new_home) == 1 and new_home[0].is_equiv_to(self):
                # there is an identical card in the new game at the location
                # where this card expects to be. Return the new card
                return new_home[0]
            else:  # empty list, or card doesn't match...
                return self.copy(state_new=None)  # couldn't find. new copy.

    def add_counter(self, addition):
        self.counters = sorted(self.counters + [addition])

    @property
    def player_index(self) -> int | None:
        """controller. duck-type to Player.player_index"""
        return self.zone.player

    @property
    def name(self) -> str:
        return self.rules_text.name

    @property
    def cost(self) -> Costs.Cost:
        return self.rules_text.cost

    @property
    def effect(self) -> Verb | None:
        return self.rules_text.effect

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
        s += "_" + str(self.zone)
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

    def has_type(self, card_type: Type[RulesText]) -> bool:
        """Returns bool: "this Cardboard refers to a card which is the given
        RulesText type (in addition to possibly other types as well)" """
        return isinstance(self.rules_text, card_type)

    def is_in(self, zone: Type[Zone]):
        return isinstance(self.zone, zone)

    # def has_keyword(self, keyword:str):
    #     return keyword in self.rules_text.keywords

    def mana_value(self) -> int:
        return self.rules_text.mana_value

    def reset_to_default_cardboard(self):
        self.tapped = False
        self.summon_sick = True
        self.counters = [c for c in self.counters if
                         c[0] == "$"]  # sticky counters stay

    # def valid_stack_objects(self, state: GameState) -> List[StackCardboard]:
    #     """Create as many valid StackCardboards as possible,
    #     one for each valid way to cast this Cardboard.
    #     This function doesn't ACTUALLY add them to stack
    #     or pay their costs, it just works out the payment
    #     verbs and target verbs and makes usable
    #     StackObjects accordingly. If the card cannot be
    #     cast, the empty list is returned."""
    #     # 601.2b: choose costs (additional costs, choose X, choose hybrid)
    #     player = self.player_index
    #     payments = self.cost.get_payment_plans(state, player, self, None)
    #     if len(payments) == 0:
    #         payments = [None]
    #     # 601.2c: choose targets and modes
    #     effects = self.effect.populate_options(state, player, self, None)
    #     effects = [eff for eff in effects if eff.can_be_done(state)]
    #     if len(effects) == 0:
    #         effects = [None]
    #     # build stack objects for all combinations of these
    #     obj_list = []
    #     for pay_verb in payments:
    #         for effect_verb in effects:
    #             caster = self.rules_text.caster_verb
    #             obj_list.append(Stack.StackCardboard(controller=player,
    #                                                  obj=self,
    #                                                  pay_cost=pay_verb,
    #                                                  do_effect=effect_verb,
    #                                                  caster_type=caster))
    #     return obj_list

    def valid_casters(self, state: GameState) -> List[PlayCardboard]:
        """Create as many valid PlayCardboard as possible,
        one for each valid way to cast this Cardboard. This
        function doesn't ACTUALLY run those verbs to cast the
        cardboard and add it to stack and pay its cost, but
        it fully populates the PlayCardboard verbs and the
        pay_cost and do_effect verbs of the card so that
        they will do those things when they are run.
        If the card cannot be cast, the empty list is returned."""
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        # Note: if cost is free, payments is [None]. If cost cannot be paid,
        # payments is [] so loops won't loop and no caster is returned.
        player = self.player_index
        payments = self.cost.get_payment_plans(state, player, self, None)
        # 601.2c: choose targets and modes
        if self.effect is None:
            effects = [None]  # no effects so no targets to choose, etc
        else:
            # Note: if no effects can legally be done, then `effects` is
            # empty list and loops won't loop and no caster is returned.
            effects = self.effect.populate_options(state, player, self, None)
            effects = [eff for eff in effects if eff.can_be_done(state)]
        # build casters and stack objects for all combinations of these
        caster_list = []
        for pay_verb in payments:
            for effect_verb in effects:
                stack_obj = Stack.StackCardboard(controller=player,
                                                 obj=self,
                                                 pay_cost=pay_verb,
                                                 do_effect=effect_verb)
                caster: PlayCardboard = self.rules_text.caster_verb()
                [caster] = caster.populate_options(state=state,
                                                   player=player,
                                                   source=self,
                                                   cause=None,
                                                   stack_object=stack_obj)
                if caster.can_be_done(state):
                    caster_list.append(caster)
        return caster_list

    def build_tk_display(self, parent_frame):
        """Returns a tkinter button representing the Cardboard.
        Note: clicking the button won't do anything yet. Setting up the button
        so that clicking it will cast the card or activate its abilities is
        the responsibility of whatever is building the GUI.
        Similarly, whatever calls this function is responsible for adding the
        button to the tkinter frame so that it actually appears on screen.
        """
        # button = tk.Button(parent_frame,
        #                    height=4 if self.tapped else 7,
        #                    width=15 if self.tapped else 10,
        #                    wraplength=110 if self.tapped else 80,
        #                    padx=3, pady=3,
        #                    relief="raised", bg='lightgreen',
        #                    anchor="center"
        #                    )
        # button.grid_propagate(False)  # don't resize
        # # mana cost (if any)
        # cost_string = ""
        # if self.mana_value() > 0:
        #     cost_string = "(" + str(self.rules_text.mana_cost) + ")"
        # cost_label = tk.Label(button, text=cost_string, bg="red", anchor="ne")
        # cost_label.grid(row=0, column=0, sticky="ewn")
        # # name
        # name_label = tk.Label(button, text=self.name, bg="red",
        #                       anchor="center", wraplength=70)
        # name_label.grid(row=1, column=0, sticky="ns")
        # # counters, if any
        # counter_string = ""
        # for c in set(self.counters):
        #     if c[0] != "@":
        #         counter_string += "[%s]" % c
        #         if self.counters.count(c) > 1:
        #             counter_string += "x%i" % self.counters.count(c)
        #         counter_string += "\n"
        # counter_label = tk.Label(button, text=counter_string, bg="red",
        #                          anchor="center", borderwidth=1)
        # counter_label.grid(row=2, column=0, sticky="ns")
        # # power and toughness, if any
        # pt_string = ""
        # if hasattr(self.rules_text, "power") and hasattr(self.rules_text,
        #                                                  "toughness"):
        #     pt_string = "%i/%i" % (self.rules_text.power,
        #                            self.rules_text.toughness)
        # pt_label = tk.Label(button, text=pt_string, bg="red", anchor="e")
        # pt_label.grid(row=3, column=0, sticky="ews")
        # # let subcomponents resize
        # button.rowconfigure("all", weight=1)
        # button.columnconfigure("all", weight=1)
        # # let clicks pass through the labels onto the button???
        # return button

        # string for mana cost (if any)
        cost_string = ""
        if self.mana_value() > 0:
            cost_string = "(" + str(self.rules_text.mana_cost) + ")"
        # string for name
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
            text += " " * (30 - len(power_toughness_string)-len(cost_string))
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
                           text=text, anchor="w", justify="left",
                           height=4 if self.tapped else 7,
                           width=15 if self.tapped else 10,
                           wraplength=110 if self.tapped else 80,
                           padx=3, pady=3,
                           relief="raised", bg='lightgreen')
        return button


class CardNull(Cardboard):

    def __init__(self):
        super().__init__(RulesText())
        self.tapped: bool = False
        self.summon_sick: bool = True
        self.counters = []
        self.zone = Zone.Unknown()

    def __str__(self):
        return "Null"

    def __repr__(self):
        return "NullCard"

    def copy(self, *args):
        return CardNull()

    def add_counter(self, addition):
        return

    def valid_casters(self, state: GameState) -> List[PlayCardboard]:
        return []

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
