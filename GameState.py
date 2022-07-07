# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, Tuple
# if TYPE_CHECKING:
#     import RulesText

# import tkinter as tk
from Abilities import ActivatedAbility
import Stack
from Cardboard import Cardboard  # actually needs
import Getters as Get
import ZONE
from ManaHandler import ManaPool
import Choices
import Verbs


class GameState:
    """The current state of the game.
    
    For anything relating to a decision (paying a cost, activating
    an ability, casting a spell), do not mutate this state.  Rather,
    always create a new state representing the new situation.
    
    A GameState holds all the Cardboard pieces representing the MtG
    cards. It keeps track of which zones they are in, but THEY keep
    track of which cards they represent.
    
    The GameState has functions for gameplay actions which come
    from base MtG rules, for example emptying mana at the end of
    phases or untapping at the untap step. All of these actions
    should be called by an outside function of some sort. The
    GameState does not progress the game, it merely tracks the state
    of the game and provides tools for others to progress the game.
    """

    def __init__(self):
        self.deck: List[Cardboard] = []  # list of Cardboard objects
        self.hand: List[Cardboard] = []  # list of Cardboard objects
        self.field: List[Cardboard] = []  # list of Cardboard objects
        self.grave: List[Cardboard] = []  # list of Cardboard objects
        self.pool: ManaPool = ManaPool("")

        self.stack = []  # list of Cardboards and StackEffects
        self.super_stack = []  # list of StackEffects waiting to be
        # put on the stack. NOTHING CAN BE EXECUTED WHILE
        # STUFF IS ON THE SUPERSTACK (incl state-based)

        self.turn_count = 1
        self.is_my_turn = True

        self.life = 20
        self.opponent_life = 20
        self.has_played_land = False

        # self.num_lands_played
        # self.num_lands_permitted
        # self.opponent_list = [] ???
        # self.num_spells_cast

        self.verbose = False

    def __str__(self):
        txt = "HAND:    " + ",".join([str(card) for card in self.hand])
        if len(self.field) > 0:
            txt += "\nFIELD:   " + ",".join([str(card) for card in self.field])
        if len(self.grave) > 0:
            txt += "\nGRAVE:   " + ",".join([str(card) for card in self.grave])
        if len(self.stack) > 0:
            txt += "\nSTACK:   " + ",".join([str(obj) for obj in self.stack])
        txt += "\nLife: %2i vs %2i" % (self.life, self.opponent_life)
        txt += "    Deck: %2i" % len(self.deck)
        txt += "    Mana: (%s)" % str(self.pool)
        return txt

    def __eq__(self, other):
        # easy disqualifications first
        if not (len(self.deck) == len(other.deck)
                and len(self.hand) == len(other.hand)
                and len(self.field) == len(other.field)
                and len(self.grave) == len(other.grave)
                and len(self.stack) == len(other.stack)
                and len(self.super_stack) == len(other.super_stack)
                and self.turn_count == other.turn_count
                and self.is_my_turn == other.is_my_turn
                and self.life == other.life
                and self.opponent_life == other.opponent_life
                and self.has_played_land == other.has_played_land
                and self.pool == other.pool):
            return False
        # also need to compare hands, fields, etc. We know they are sorted
        # and have the same length, so just step through them
        for ii in range(len(self.hand)):
            if not self.hand[ii].is_equiv_to(other.hand[ii]):
                return False
        for ii in range(len(self.grave)):
            if not self.grave[ii].is_equiv_to(other.grave[ii]):
                return False
        for ii in range(len(self.field)):
            if not self.field[ii].is_equiv_to(other.field[ii]):
                return False
        # stack isn't SORTED but it's ORDERED so can treat it the same
        for ii in range(len(self.stack)):
            if not self.stack[ii].is_equiv_to(other.stack[ii]):
                return False
        # if got to here, we're good!
        return True

    def get_id(self):
        my_turn = "MY" if self.is_my_turn else "OP"
        played_land = "_PL" if self.is_my_turn else ""
        s = "%s%i_%02ivs%02i%s" % (my_turn, self.turn_count,
                                   self.life, self.opponent_life, played_land)
        s += "_" + ",".join([c.get_id() for c in self.hand])
        s += "_" + ",".join([c.get_id() for c in self.field])
        s += "_" + ",".join([c.get_id() for c in self.grave])
        s += "_" + ",".join([c.get_id() for c in self.stack])
        s += "(%s)" % str(self.pool)
        return s

    def __hash__(self):
        return self.get_id().__hash__()  # hash the string of the get_id

    def copy_and_track(self, track_list) -> Tuple[GameState, List[Cardboard]]:
        """Returns a disconnected copy of the gamestate and also
        a list of Cardboard's in the new gamestate corresponding
        to the list of Cardboard's we were asked to track. This
        allows tracking "between split universes."
        If track_list has non-Cardboard objects, they're also
        returned"""
        # make new Gamestate and start copying attributes by value
        state = GameState()
        # copy mana pool
        state.pool = self.pool.copy()
        # these are all ints or bools, so safe to copy directly
        state.turn_count = self.turn_count
        state.is_my_turn = self.is_my_turn
        state.life = self.life
        state.opponent_life = self.opponent_life
        state.has_played_land = self.has_played_land
        state.verbose = self.verbose
        # need to track any pointers in StackObjects
        stack_index = len(track_list)  # index for where stack portion begins
        for obj in self.stack + self.super_stack:
            track_list += [obj.card] + obj.choices
        # blank list to fill with corresponding copies of cards in track_list
        new_track_list = track_list[:]  # a copy of track_list

        def copy_list_and_update_pointers_to_it(original_list):
            """Goes through a list and returns a list of
            copies of each element in the original list. Also
            checks against track_list to make sure that any pointers
            to the original elements now points at the new copies of
            the elements. Maintains order so that the new list
            does not need to be re-sorted."""
            new_list = []
            for obj2 in original_list:
                if isinstance(obj2, list) or isinstance(obj2, tuple):
                    # recurse. I THINK this never happens but just in case
                    new_object = copy_list_and_update_pointers_to_it(obj2)
                elif hasattr(obj2, "copy"):
                    new_object = obj2.copy()
                else:
                    # not copiable, probably int or similar
                    new_object = obj2
                new_list.append(new_object)
                # now spin through track_list. if we just copied a
                # Cardboard that we are tracking, replace the old
                # pointer in newtracklist with a pointer to the new
                # copy.
                # (For things like ints, we don't care if it's
                # technically the old object or a new copy.)
                if isinstance(new_object, Cardboard):
                    for index, tracked_object in enumerate(track_list):
                        # try to iterate through tracked_object just in case
                        try:
                            new_track_list[index] = [
                                new_object if obj2 is c else c
                                for c in tracked_object]
                        except TypeError:
                            if obj2 is tracked_object:
                                new_track_list[index] = new_object
            return new_list

        state.deck = copy_list_and_update_pointers_to_it(self.deck)
        state.hand = copy_list_and_update_pointers_to_it(self.hand)
        state.field = copy_list_and_update_pointers_to_it(self.field)
        state.grave = copy_list_and_update_pointers_to_it(self.grave)

        def copy_stack_objects(original_list):
            """Goes through a list of StackObjects and rebuilds
            copies of them. StackObjects contain pointers to
            Cardboard's, so we get the new pointers to the newly
            copied Cardboard's by looking in the new_track_list.
            This assumes that the StackObjects are checked in the
            same order that they were placed into new_track_list.
            Returns a list of new StackObjects and the new version
            of new_track_list."""
            new_list = []
            for obj2 in original_list:
                new_card = new_track_list[stack_index]
                i_end = stack_index + 1 + len(obj2.choices)
                new_choices = new_track_list[stack_index + 1:i_end]
                # build the new StackObject
                if isinstance(obj2, Stack.StackCardboard):
                    new_stack_obj = Stack.StackCardboard(new_card, new_choices)
                elif isinstance(obj2, Stack.StackAbility):
                    ability = obj2.ability  # does this need a copy?
                    new_stack_obj = Stack.StackAbility(ability, new_card,
                                                       new_choices)
                else:
                    raise TypeError("Unknown type of StackObject!")
                new_list.append(new_stack_obj)
                # get rid of the references I just used. done with them now.
                result = new_track_list[:stack_index] + new_track_list[i_end:]
                return new_list, result

        # copy stack and superstack, replacing pointers in StackObjects as I go
        state.stack, new_track_list = copy_stack_objects(self.stack)
        state.super_stack, new_track_list = copy_stack_objects(
            self.super_stack)
        # return
        return state, new_track_list

    def copy(self):
        return self.copy_and_track([])[0]

    # -----MUTATING FUNCTIONS. They all return a list of StackEffects

    def get_zone(self, zone_name):
        if zone_name == ZONE.DECK:
            zone = self.deck
        elif zone_name == ZONE.HAND:
            zone = self.hand
        elif zone_name == ZONE.FIELD:
            zone = self.field
        elif zone_name == ZONE.GRAVE:
            zone = self.grave
        elif zone_name == ZONE.STACK:
            zone = self.stack
        else:
            raise IndexError
        return zone

    def re_sort(self, zone_name):
        """sort the specified zone, if it is a zone that is supposed
        to be sorted"""
        if zone_name == ZONE.HAND:
            self.hand.sort(key=Cardboard.get_id)
        elif zone_name == ZONE.FIELD:
            self.field.sort(key=Cardboard.get_id)
        elif zone_name == ZONE.GRAVE:
            self.grave.sort(key=Cardboard.get_id)

    def _move_zone(self, cardboard, destination):
        """Move the specified piece of cardboard from the zone
        it is currently in to the specified destination zone.
        Raises IndexError if the cardboard is not in the zone
        it claims to be in.
        Adds any triggered StackEffects to the super_stack.
        MUTATES.
        """
        Verbs.MoveToZone(destination).do_it(self, cardboard, [])

    # -------------------------------------------------------------------------

    def state_based_actions(self):
        """MUTATES. Performs any state-based actions like killing creatures if
        toughness is less than 0.
        Adds any triggered StackAbilities to the super_stack.
        """
        i = 0
        while i < len(self.field):
            cardboard = self.field[i]
            toughness = Get.Toughness().get(self, cardboard)
            if toughness is not None and toughness <= 0:
                Verbs.MoveToZone(ZONE.GRAVE).do_it(self, cardboard, [])
                continue  # don't increment counter
            i += 1
        # legend rule   # TODO

    def untap_step(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack."""
        # newstate,_ = self.copy_and_track([])  #copy, but nothing to track
        self.pool = ManaPool("")
        self.stack = []
        self.turn_count += 1
        self.has_played_land = False
        for card in self.field:
            Verbs.UntapSelf().do_it(self, card, [])
            card.summon_sick = False
            # erase the invisible counters
            card.counters = [c for c in card.counters if
                             c[0] not in ("@", "$")]

    def upkeep_step(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack."""
        for cardboard in self.hand + self.field + self.grave:
            for ability in cardboard.rules_text.trig_upkeep:
                new_effect = Stack.StackAbility(ability, cardboard, [])
                self.super_stack.append(new_effect)

    def draw_card(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack.
           Draws from index 0 of deck."""
        Verbs.DrawCard().do_it(self, None, [])

    def resolve_top_of_stack(self):
        """
        DOES NOT MUTATE. Instead, returns a list of GameStates in
            which the top item of the stack has been resolved.
        If it was a StackCardboard, the card has been moved to the
            appropriate zone. If it was a Spell specifically, the
            effect has been resolved. Any enter-the-battlefield
            effects or similar effects that trigger based on motion
            have been placed on the stack.
        If it was a StackAbility then the ability has been resolved
            and any new abilities that triggered as a result have
            been placed on the stack."""
        if len(self.stack) == 0:
            return []
        assert (isinstance(self.stack[-1], Stack.StackObject))
        return self.stack[-1].resolve(self)

    def clear_super_stack(self):
        """Returns a list of GameStates where the objects on the super_stack
        have been placed onto the stack in all possible orders or otherwise
        dealt with. If super_stack is empty, returns [self].
        DOES NOT MUTATE."""
        # base case: no items on super_stack
        if len(self.super_stack) == 0:
            return [self]
        results = []
        # pick a super_stack effect to move to the stack
        for item in Choices.choose_exactly_one(
                        list(enumerate(self.super_stack)),
                        "Add to stack"):
            ii = item[0]  # index first, then object second
            new_state = self.copy()
            stack_ability = new_state.super_stack.pop(ii)
            if stack_ability.ability.is_type(Verbs.AsEnterEffect):
                # if the ability contains an AsEntersEffect, then enact
                # it immediately rather than putting it on the stack.
                results += stack_ability.resolve(self)
            else:
                new_state.stack.append(stack_ability)
                results.append(new_state)
        # recurse
        final_results = []
        for state in results:
            final_results += state.clear_super_stack()
        return final_results

    # -------------------------------------------------------------------------

    def get_valid_activations(self) -> List[
        Tuple[ActivatedAbility, GameState, Cardboard, list]]:
        """
        Return a list of all abilities that can be put on the
        stack right now. The form of the return is a tuple of
        the inputs that Verb.ActivateAbility needs in order
        to put a newly activated ability onto the stack.
        """
        effects = []
        active_objects = []  # objects I've already checked through
        for source in self.hand + self.field + self.grave:
            if any([source.is_equiv_to(ob) for ob in active_objects]):
                continue  # skip cards equivalent to those already searched
            add_object = False
            for ability in source.get_activated():
                # check whether price can be paid
                for choices in ability.get_choice_options(self, source):
                    if ability.can_afford(self, source, choices):
                        # this ability with this set of choices is castable!
                        effects.append((ability, self, source, choices))
                        add_object = True
            if add_object:  # track any object whose ability we looked at
                active_objects.append(source)
        return effects

    def get_valid_castables(self):
        """Return a list of all cast-able cards that can be put
        on the stack right now, as a list of Cardboard's which
        have not yet been paid for or moved from their current
        zones. Think of these like pointers."""
        cards = []
        # look for all cards that can be cast
        active_objects = []
        for card in self.hand:
            if any([card.is_equiv_to(ob) for ob in active_objects]):
                continue  # skip cards equivalent to those already searched
            if (len(self.stack) > 0
                    and "instant" not in card.rules_text.keywords):  # TODO
                continue  # if stack is full, can only cast instants
            if card.rules_text.can_afford(self, card):
                cards.append(card)
                active_objects.append(card)
        return cards

    # -------------------------------------------------------------------------

    # def Attack(self):
    #     """Attack with anything that can"""
    #     attackerlist = [] #keep track of what attacked, to print if verbose
    #     oldlife = self.opponent_life
    #     haveArcades = any( [isinstance(c,Decklist.Arcades) for c in self.field])
    #     #attack with everything that can
    #     for critter in self.field:
    #         if not isinstance(critter,RulesText.Creature): #only attack with creatures
    #             continue
    #         if critter.summon_sick or critter.tapped: #creature needs to be able to attack
    #             continue
    #         if "defender" in critter.keywords:
    #             if haveArcades: #have an Arcades, so can attack with the defenders!
    #                 self.opponent_life -= critter.toughness
    #                 attackerlist.append(critter)
    #         else: #non-defenders
    #             self.opponent_life -= critter.power
    #             attackerlist.append(critter)
    #     #attacking taps the attacker 
    #     for critter in attackerlist:
    #         if not "vigilance" in critter.keywords:
    #                 critter.tapped = True  
    #         if "lifelink" in critter.keywords:
    #             self.life += critter.power
    #     if self.verbose and len(attackerlist)>0: #print what just happened
    #         print("COMBAT  ",",".join([att.name for att in attackerlist]),"for %i damage" %(oldlife-self.opponent_life))
    #     if self.opponent_life <= 0:
    #         raise IOError("COMBAT DAMAGE WINS THE GAME!")

    # def PassTurn(self):
    #     #discard down to 7 cards
    #     if len(self.hand)>7:
    #         discardlist = AI.ChooseCardstoDiscard(self)
    #         if self.verbose:
    #             print("discard:",[str(c) for c in discardlist])
    #         for card in discardlist:
    #             self.hand.remove(card)
    #     #clear any floating mana
    #     if self.verbose and self.pool.mana_value()>0:
    #         print("end with %s" %(str(self.pool)))
    #     for color in self.pool.data.keys():
    #         self.pool.data[color] = 0 
    #     #pass the turn
    #     if not self.is_my_turn:
    #         self.turn_count += 1
    #         self.has_played_land = False
    #     self.is_my_turn = not self.is_my_turn

#     def TakeDamage(self,damage):
#         self.life -= damage
#         if self.life <= 0:
#             raise IOError("LOSE DUE TO DAMAGE!")


# -----------------------------------------------------------------------------


# =============================================================================
# class ManualGame(tk.Tk):
# 
#     def __init__(self, startstate):
#         super().__init__()
#         self.history = [startstate]
#         # if you win or lose, game raises an error
#         self.report_callback_exception = self.HandleError
#         # how to pass and allow stack to resolve. sort of like F2 on MagicOnline
#         self.var_resolveall = tk.IntVar(self, 1)
#         # stack
#         tk.Label(self, text="STACK", wraplength=1).grid(row=0, column=0)
#         self.stack = tk.Frame(self, borderwidth=1, relief="solid")
#         self.stack.grid(row=0, column=1, padx=5, pady=5, sticky="W")
#         # current situation
#         tk.Label(self, text="STATE", wraplength=1).grid(row=1, column=0)
#         self.status = tk.Frame(self, borderwidth=1, relief="solid")
#         self.status.grid(row=1, column=1, padx=5, pady=5, sticky="W")
#         # battlefield
#         tk.Label(self, text="FIELD", wraplength=1).grid(row=2, column=0)
#         self.field = tk.Frame(self, bg="lightgray", borderwidth=1, relief="solid")
#         self.field.grid(row=2, column=1, padx=5, pady=15, sticky="W")
#         # hand
#         tk.Label(self, text="HAND", wraplength=1).grid(row=3, column=0)
#         self.hand = tk.Frame(self, borderwidth=1, relief="solid")
#         self.hand.grid(row=3, column=1, padx=5, pady=5, sticky="W")
#         # populate the display and start the game
#         self.RebuildDisplay()
#         self.mainloop()
# 
#     @property
#     def game(self):
#         assert (not isinstance(self.history[-1], str))
#         return self.history[-1]
# 
#     def RebuildStack(self):
#         for widgets in self.stack.winfo_children():
#             widgets.destroy()
#         for ii, obj in enumerate(self.game.stack):
#             # obj is either Cardboard or StackEffect. both have TkDisplay method
#             butt = obj.build_tk_display(self.stack)
#             butt.config(command=self.ResolveTopOfStack)
#             butt.grid(row=1, column=ii, padx=5, pady=3)
# 
#     def RebuildStatus(self):
#         for widgets in self.status.winfo_children():
#             widgets.destroy()
#         # turn count
#         tk.Label(self.status, text="Turn:\n%i" % self.game.turn_count,
#                  ).grid(row=1, column=1, rowspan=2, padx=5, pady=5)
#         # life totals
#         tk.Label(self.status, text="Life total: %i" % self.game.life
#                  ).grid(row=1, column=2, padx=5, pady=2)
#         tk.Label(self.status, text="Opponent: %i" % self.game.opponent_life
#                  ).grid(row=2, column=2, padx=5, pady=2)
#         # cards remaining
#         tk.Label(self.status, text="Cards in deck: %i" % len(self.game.deck)
#                  ).grid(row=1, column=3, padx=5, pady=2)
#         tk.Label(self.status, text="Cards in grave: %i" % len(self.game.grave)
#                  ).grid(row=2, column=3, padx=5, pady=2)
#         # mana and land-drops
#         if str(self.game.pool) != "":
#             manastr = "Mana floating: (%s)" % str(self.game.pool)
#         else:
#             manastr = "Mana floating: None"
#         landstr = "Played land: %s" % ("yes" if self.game.has_played_land else "no")
#         tk.Label(self.status, text=manastr
#                  ).grid(row=1, column=4, padx=5, pady=2)
#         tk.Label(self.status, text=landstr
#                  ).grid(row=2, column=4, padx=5, pady=2)
#         # button to do the next thing
#         if len(self.game.stack) == 0:
#             b = tk.Button(self.status, text="Pass\nturn", bg="yellow", width=7,
#                           command=self.PassTurn)
#             b.grid(row=1, column=5, padx=5, pady=5)
#         else:
#             b = tk.Button(self.status, text="Resolve\nnext", bg="yellow", width=7,
#                           command=self.ResolveTopOfStack)
#             b.grid(row=1, column=5, padx=5, pady=2)
#         # undo button
#         b2 = tk.Button(self.status, text="undo", bg="yellow", command=self.Undo)
#         b2.grid(row=1, column=6, padx=5, pady=2)
#         # auto-resolve button
#         b3 = tk.Checkbutton(self.status, text="Auto-resolve all",
#                             variable=self.var_resolveall,
#                             indicatoron=True)  # ,onvalue=1,background='grey')#,selectcolor='green')
#         b3.grid(row=2, column=5, columnspan=2, padx=5, pady=5)
# 
#     def RebuildHand(self):
#         for widgets in self.hand.winfo_children():
#             widgets.destroy()
#         for ii, card in enumerate(self.game.hand):
#             butt = card.build_tk_display(self.hand)
#             abils = [a for a in card.get_activated() if a.CanAfford(self.game, card)]
#             assert (len(abils) == 0)  # activated abilities in hand not yet implemented
#             if card.rules_text.CanAfford(self.game, card):
#                 butt.config(state="normal",
#                             command=lambda c=card: self.CastSpell(c))
#             else:
#                 butt.config(state="disabled")
#             butt.grid(row=1, column=ii, padx=5, pady=3)
# 
#     def RebuildField(self):
#         for widgets in self.field.winfo_children():
#             widgets.destroy()
#         toprow = 0  # number in bottom row
#         botrow = 0  # number in top row
#         for card in self.game.field:
#             butt = card.build_tk_display(self.field)
#             # make the button activate this card's abilities
#             abils = [a for a in card.get_activated() if a.CanAfford(self.game, card)]
#             if len(abils) == 0:
#                 butt.config(state="disabled")  # nothing to activate
#             elif len(abils) == 1:
#                 command = lambda c=card, a=abils[0]: self.ActivateAbility(c, a)
#                 butt.config(state="normal", command=command)
#             else:  # len(abils)>1:
#                 # ask the user which one to use
#                 print("ask the user which ability to use, I guess")
#             # add card-button to the GUI. Lands on bottom, cards on top
#             if card.has_type(RulesText.Creature):
#                 butt.grid(row=1, column=toprow, padx=5, pady=3)
#                 toprow += 1
#             else:
#                 butt.grid(row=2, column=botrow, padx=5, pady=3)
#                 botrow += 1
# 
#     def RebuildDisplay(self):
#         self.RebuildStack()
#         self.RebuildStatus()
#         self.RebuildField()
#         self.RebuildHand()
# 
#     def Undo(self):
#         if len(self.history) > 1:
#             self.history.pop(-1)  # delete last gamestate from history list
#             self.RebuildDisplay()
# 
#     def CastSpell(self, spell):
#         universes = self.game.CastSpell(spell)
#         if len(universes) == 0:
#             return  # casting failed, nothing changed so do nothing
#         assert (len(universes) == 1)
#         self.history.append(universes[0])
#         if self.var_resolveall.get():
#             self.EmptyEntireStack()
#         else:
#             self.RebuildDisplay()
# 
#     def ActivateAbility(self, source, ability):
#         universes = self.game.ActivateAbilities(source, ability)
#         if len(universes) == 0:
#             return  # activation failed, nothing changed so do nothing
#         assert (len(universes) == 1)
#         self.history.append(universes[0])
#         if self.var_resolveall.get():
#             self.EmptyEntireStack()
#         else:
#             self.RebuildDisplay()
# 
#     def ResolveTopOfStack(self):
#         if len(self.game.stack) == 0:
#             return  # nothing to resolve, so don't change anything
#         universes = self.game.ResolveTopOfStack()
#         # if len(universes)==0:
#         #     return #nothing changed so do nothing
#         assert (len(universes) == 1)
#         self.history.append(universes[0])
#         if self.var_resolveall.get():
#             self.EmptyEntireStack()
#         else:
#             self.RebuildDisplay()
# 
#     def EmptyEntireStack(self):
#         while len(self.game.stack) > 0:
#             universes = self.game.ResolveTopOfStack()
#             # if len(universes)==0:
#             #     return #nothing changed so do nothing
#             assert (len(universes) == 1)
#             self.history.append(universes[0])
#         self.RebuildDisplay()
# 
#     def PassTurn(self):
#         newstate = self.game.copy()
#         newstate.UntapStep()
#         newstate.UpkeepStep()
#         newstate.draw_card()  # technically should clear super_stack FIRST but whatever
#         # clear the super stack, then clear the normal stack
#         activelist = newstate.ClearSuperStack()
#         finalstates = set()
#         while len(activelist) > 0:
#             state = activelist.pop(0)
#             if len(state.stack) == 0:
#                 finalstates.add(state)
#             else:
#                 activelist += state.ResolveTopOfStack()
#         # all untap/upkeep/draw abilities are done
#         assert (len(finalstates) == 1)
#         self.history.append(finalstates.pop())
#         self.RebuildDisplay()
# 
#     def HandleError(self, exc, val, tb, *args):
#         """overwrite tkinter's usual error-handling routine if it's something
#         I care about (like winning or losing the game)
#         exc is the error type (it is of class 'type')
#         val is the error itself (it is some subclass of Exception)
#         tb is the traceback object (it is of class 'traceback')
#         See https://stackoverflow.com/questions/4770993/how-can-i-make-silent-exceptions-louder-in-tkinter
#         """
#         if isinstance(val, WinTheGameError):
#             tk.Label(self.status, text="CONGRATS! YOU WON THE GAME!", bg="red",
#                      ).grid(row=0, column=0, columnspan=10, padx=5, pady=5)
#             for frame in [self.field, self.hand, self.stack, self.status]:
#                 for widget in frame.winfo_children():
#                     if isinstance(widget, tk.Button):
#                         widget.config(state="disabled")
#         elif isinstance(val, LoseTheGameError):
#             tk.Label(self.status, text="SORRY, YOU LOST THE GAME", bg="red",
#                      ).grid(row=0, column=0, columnspan=10, padx=5, pady=5)
#             for frame in [self.field, self.hand, self.stack, self.status]:
#                 for widget in frame.winfo_children():
#                     if isinstance(widget, tk.Button):
#                         widget.config(state="disabled")
#         elif isinstance(val, Choices.AbortChoiceError):
#             return  # just don't panic. gamestate is unchanged.
#         else:
#             super().report_callback_exception(exc, val, tb, *args)
# 
# 
# 
# =============================================================================


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# =============================================================================
# if __name__ == "__main__":
#     print("testing ManualGame...")
#     import Decklist
#     import Choices
# 
#     Choices.AUTOMATION = False
# 
#     game = GameState()
#     game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.FIELD)
#     game.MoveZone(Cardboard.Cardboard(Decklist.Caretaker), ZONE.FIELD)
# 
#     game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.HAND)
#     game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.HAND)
#     game.MoveZone(Cardboard.Cardboard(Decklist.Roots), ZONE.HAND)
#     game.MoveZone(Cardboard.Cardboard(Decklist.Battlement), ZONE.HAND)
#     game.MoveZone(Cardboard.Cardboard(Decklist.Company), ZONE.HAND)
# 
#     for _ in range(5):
#         game.MoveZone(Cardboard.Cardboard(Decklist.Blossoms), ZONE.DECK)
#     for _ in range(5):
#         game.MoveZone(Cardboard.Cardboard(Decklist.Omens), ZONE.DECK)
#         game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.DECK)
#         game.MoveZone(Cardboard.Cardboard(Decklist.Battlement), ZONE.DECK)
# 
#     # window = tk.Tk()
# 
#     # Choices.SelecterGUI(game.hand,"test chooser GUI",1,False)
# 
#     # window.mainloop()
# 
#     game.UntapStep()
#     game.UpkeepStep()
#     gui = ManualGame(game)
# =============================================================================
