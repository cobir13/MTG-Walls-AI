# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""
from typing import List

import ZONE
import RulesText
import tkinter as tk


##---------------------------------------------------------------------------##

class Cardboard:
    """Represents the physical piece of cardboard that is a Magic card.
    """

    # needs to not overwrite equality, because I often check if a card is in
    # a list and I need the `in` functionality to use `is` rather than `==`.
    # Unfortunately, this also means I can't drop Cardboard's into sets to sort.

    def __init__(self, rules_text: RulesText):
        self.rules_text: RulesText = rules_text
        self.tapped: bool = False
        self.summon_sick: bool = True
        self.counters: List[str] = []  # sorted list of counters. Also other trackers
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
        # safe to copy by reference since they're all ints, str, etc
        new_card.tapped = self.tapped
        new_card.summon_sick = self.summon_sick
        new_card.zone = self.zone
        # counters is a LIST so it needs to be copied carefully, without reference
        new_card.counters = self.counters.copy()
        # cardtype never mutates so it's ok that they're both pointing at the
        # same instance of a RulesText
        new_card.rules_text = self.rules_text
        return new_card

    def add_counter(self, addition):
        self.counters = sorted(self.counters + [addition])

    @property
    def name(self):
        return self.rules_text.name

    def get_activated(self):
        return self.rules_text.activated

    def get_id(self):
        s = type(self.rules_text).__name__  # MtG card type (creature, land, etc)
        s += self.rules_text.name + "_"
        if self.tapped:
            s += "T"
        if self.summon_sick and self.has_type(RulesText.Creature):
            s += "S"
        s += str(self.zone)
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

    def has_type(self, cardtype):
        """Returns bool: "this Cardboard refers to a card which is the given
        RulesText type (in addition to possibly other types as well)" """
        return isinstance(self.rules_text, cardtype)

    def cmc(self):
        return self.rules_text.cost.manacost.cmc()

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
        if self.cmc() > 0:
            cost_string = "(" + str(self.rules_text.cost.manacost) + ")"
        # string for name
        # text += "".join([l if l.islower() else " "+l for l in self.name])[1:]
        name_string = self.name
        # string for power and toughness, if any
        ptstr = ""
        if self.has_type(RulesText.Creature):
            ptstr = "%i/%i" % (self.rules_text.basepower, self.rules_text.basetoughness)
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
            text += ptstr
            text += " " * (30 - len(ptstr) - len(cost_string))
            text += cost_string
        else:
            text = " " * (20 - len(cost_string)) + cost_string + "\n"
            text += name_string + "\n"
            text += counter_string
            while text.count("\n") < 6:
                text += "\n"
            text += " " * (20 - len(ptstr)) + ptstr
        # build the button and return it
        button = tk.Button(parent_frame,
                           text=text, anchor="w",
                           height=4 if self.tapped else 7,
                           width=15 if self.tapped else 10,
                           wraplength=110 if self.tapped else 80,
                           padx=3, pady=3,
                           relief="raised", bg="lightgreen")
        return button


if __name__ == "__main__":
    import Decklist

    window = tk.Tk()
    frame = tk.Frame(window)
    frame.grid(padx=5, pady=5)

    c1 = Cardboard(Decklist.Roots)
    c1.build_tk_display(frame).grid(row=0, column=0, padx=5)
    c2 = Cardboard(Decklist.Caretaker)
    c2.build_tk_display(frame).grid(row=0, column=1, padx=5)

    c4 = Cardboard(Decklist.Caretaker)
    c4.tapped = True
    c4.build_tk_display(frame).grid(row=0, column=2, padx=5)

    c3 = Cardboard(Decklist.WindsweptHeath)
    c3.tapped = True
    c3.build_tk_display(frame).grid(row=0, column=3, padx=5)

    window.mainloop()
