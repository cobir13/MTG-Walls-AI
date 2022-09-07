from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Abilities import ActivatedAbility, TriggeredAbility, TimedAbility
    from Cardboard import Cardboard
    from Verbs import Verb
    from Costs import Cost
    from GameState import GameState

import Zone
import tkinter as tk


class StackObject:

    def __init__(self, controller: int,
                 obj: (Cardboard | ActivatedAbility | TriggeredAbility
                       | TimedAbility),
                 pay_cost: Verb | None, do_effect: Verb | None):
        """
        controller: the player controlling this stack object
        obj:        the card being cast or ability being activated
                    or triggered. Note that any effect Verbs within
                    the card or ability are NOT populated with
                    inputs. That is what `effect` is for.
        pay_cost:   The Verb that pays the cost for putting this
                    StackObjectthat onto the stack.
        do_effect:  The effect Verb that will be executed when this
                    StackObject comes off the stack.
        """
        self.player_index: int = controller
        # obj is the card on the stack or the ability causing the effect
        self.obj: Cardboard | ActivatedAbility | TriggeredAbility = obj
        self.pay_cost: Verb | None = pay_cost
        self.do_effect: Verb | None = do_effect
        self.zone = Zone.Stack(None)

    @property
    def cost(self) -> Cost | None:
        if hasattr(self.obj, "cost"):
            return self.obj.cost

    def get_id(self):
        type_text = "%s%i" % (type(self).__name__, self.player_index)
        assert self.zone.is_contained_in(Zone.Stack())
        if self.zone.location is not None:
            type_text += str(self.zone.location)
        obj_text = self.obj.get_id()
        pay = "" if self.pay_cost is None else "+" + self.pay_cost.get_id()
        eff = "" if self.do_effect is None else " ->" + self.do_effect.get_id()
        return "%s(%s%s%s)" % (type_text, obj_text, pay, eff)

    def is_equiv_to(self, other: StackObject):
        return self.get_id() == other.get_id()

    @property
    def name(self):
        return self.obj.name

    def __str__(self):
        return "%s \"%s\"" % (type(self).__name__, self.name)

    def __repr__(self):
        return self.get_id()

    def copy(self, state_new: GameState | None = None):
        """This function assumes that everything except maybe
        the stack and superstack have already been copied
        correctly. In other words, all Cardboards have already
        been copied. It is only StackObjects which remain to
        be copied."""
        # if this StackObject is a pointer to a DIFFERENT StackObject on the
        # stack which already has a copy, then just return that new copied
        # object. (Relevant for e.g. counterspell, which targets a StackObject)
        if state_new is not None:
            new_home = self.zone.get(state_new)
            if len(new_home) == 1 and new_home[0].is_equiv_to(self):
                # An identical StackObject is in the new game at the location
                # self expects to live. Return pointer to this StackObject.
                return new_home[0]
        # If reached here, we need to make a new StackObject ourselves
        controller: int = self.player_index  # copy int directly
        if hasattr(self.obj, "copy"):  # it's a Cardboard
            obj = self.obj.copy(state_new)
        else:
            obj = self.obj.copy()
        cst = None if self.pay_cost is None else self.pay_cost.copy(state_new)
        ef = None if self.do_effect is None else self.do_effect.copy(state_new)
        # initialize into a StackObject, then cast it to the correct subclass
        new_obj = StackObject(controller, obj, cst, ef)
        new_obj.zone = self.zone.copy(None)
        new_obj.__class__ = self.__class__  # set the class type directly
        return new_obj

    def build_tk_display(self, parentframe, ):
        text = self.name
        # if self.effect.source is not None:
        #     text += "\nFrom: %s" % self.effect.source.name
        # list_chosen = ",".join([c.name if hasattr(c, "name") else str(c)
        #                         for c in self.choices])
        # if len(list_chosen) > 0:
        #     text += "\n" + list_chosen
        text += "\n" + str(self.obj) + "\n" + str(self.do_effect)
        return tk.Button(parentframe,
                         text=text,
                         anchor="w",
                         height=7, width=10, wraplength=80,
                         padx=3, pady=3,
                         relief="solid", bg="lightblue")


class StackAbility(StackObject):
    pass


class StackTrigger(StackAbility):
    """
    Holds a triggered ability on the super_stack.
    NOTE: effect is None at this point, since the effect Verb
        is only populated when it is put onto the stack not
        when it is put onto the superstack. This is because
        populating a verb can split the GameState into many
        copies, but putting things onto the superstack should
        mutate rather than copy.
    """
    pass


class StackCardboard(StackObject):

    def build_tk_display(self, parentframe, ):
        return tk.Button(parentframe,
                         text=str(self),
                         anchor="w",
                         height=7, width=10, wraplength=80,
                         padx=3, pady=3,
                         relief="solid", bg="lightgreen")
