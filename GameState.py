# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Tuple
# if TYPE_CHECKING:
#     from Abilities import ActivatedAbility

from Cardboard import Cardboard  # actually needs
import Getters as Get  # actually needs
import ZONE
from ManaHandler import ManaPool
from Stack import StackAbility, StackObject, StackCardboard
from Verbs import MoveToZone, DrawCard, UntapSelf
import Choices
from Abilities import AsEnterEffect, ActivatedAbility


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
        self.stack: List[StackObject] = []
        self.pool: ManaPool = ManaPool("")
        # super_stack is a list of StackObject waiting to be put onto
        # the real stack. NOTHING CAN BE EXECUTED WHILE STUFF IS ON
        # THE SUPERSTACK (incl state-based)
        self.super_stack: List[StackObject] = []
        self.turn_count: int = 1
        self.is_my_turn: bool = True
        self.life: int = 20
        self.opponent_life: int = 20
        self.has_played_land: int = False
        self.num_spells_cast: int = 0  # number of spells you cast this turn
        # self.num_lands_played
        # self.num_lands_permitted
        # self.opponent_list = [] ???
        # If we are tracking history, then we write down the previous distinct
        # GameState and a string describing how we got from there to here.
        # Things that mutate will add to the string, and things that copy
        # will write down the original state and clear the string.
        self.is_tracking_history: bool = False
        self.previous_state: GameState | None = None
        self.events_since_previous: str = ""

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

    def __hash__(self):
        # self.get_id()
        return self.get_id().__hash__()  # hash the string of the get_id

    def __neg__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        return isinstance(other, GameState) and self.get_id() == other.get_id()
        # # easy disqualifications first
        # if not (len(self.deck) == len(other.deck)
        #         and len(self.hand) == len(other.hand)
        #         and len(self.field) == len(other.field)
        #         and len(self.grave) == len(other.grave)
        #         and len(self.stack) == len(other.stack)
        #         and len(self.super_stack) == len(other.super_stack)
        #         and self.turn_count == other.turn_count
        #         and self.is_my_turn == other.is_my_turn
        #         and self.life == other.life
        #         and self.opponent_life == other.opponent_life
        #         and self.has_played_land == other.has_played_land
        #         and self.num_spells_cast == other.num_spells_cast
        #         and self.pool == other.pool):
        #     return False
        # # also need to compare hands, fields, etc. We know they are sorted
        # # and have the same length, so just step through them
        # for ii in range(len(self.hand)):
        #     if not self.hand[ii].is_equiv_to(other.hand[ii]):
        #         return False
        # for ii in range(len(self.grave)):
        #     if not self.grave[ii].is_equiv_to(other.grave[ii]):
        #         return False
        # for ii in range(len(self.field)):
        #     if not self.field[ii].is_equiv_to(other.field[ii]):
        #         return False
        # # stack isn't SORTED but it's ORDERED so can treat it the same
        # for ii in range(len(self.stack)):
        #     if not self.stack[ii].is_equiv_to(other.stack[ii]):
        #         return False
        # # if got to here, we're good!
        # return True

    def get_id(self):
        turn = "%s%i" % ("MY" if self.is_my_turn else "OP", self.turn_count)
        life = "%ivs%i" % (self.life, self.opponent_life)
        land = "Land1" if self.has_played_land else "Land0"
        storm = "storm%i" % self.num_spells_cast
        pool = "(%s)" % str(self.pool)
        deck = "deck%i" % len(self.deck)
        hand = ",".join([c.get_id() for c in self.hand])
        field = ",".join([c.get_id() for c in self.field])
        grave = ",".join([c.get_id() for c in self.grave])
        stack = ",".join([c.get_id() for c in self.stack])
        return "|".join([turn, life, land, storm, pool,
                         deck, hand, field, grave, stack])

    # @staticmethod
    # def construct_from_string(id_string: str):
    #     game = GameState()
    #     parts = id_string.split("|")
    #     game.is_my_turn = parts[0][:2] == "MY"  # turn
    #     game.turn_count = int(parts[0][2:])
    #     my_life, op_life = parts[1].split("vs")  # life
    #     game.life = int(my_life)
    #     game.opponent_life = int(op_life)
    #     game.has_played_land = parts[2][4:] == "1"  # land
    #     game.num_spells_cast = int(parts[3][5:])  # storm
    #     game.hand = [Cardboard.construct_from_string(s)
    #                  for s in parts[4].split(",") if s != ""]
    #     game.field = [Cardboard.construct_from_string(s)
    #                   for s in parts[5].split(",") if s != ""]
    #     game.grave = [Cardboard.construct_from_string(s)
    #                   for s in parts[6].split(",") if s != ""]
    #     game.stack = [StackObject.construct_from_string(s)
    #                   for s in parts[7].split(",") if s != ""]
    #     return game

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
        state.num_spells_cast = self.num_spells_cast
        state.is_tracking_history = self.is_tracking_history
        state.previous_state = self if state.is_tracking_history else None
        state.events_since_previous = ""
        # for the lists of Cardboards (hand, deck, field, grave), spin
        # through making copies as I go. The ordering will be maintained
        state.hand = [c.copy() for c in self.hand]
        state.deck = [c.copy() for c in self.deck]
        state.field = [c.copy() for c in self.field]
        state.grave = [c.copy() for c in self.grave]
        # now copy the stack and superstack, which are made of StackObjects.
        # Need to append as I go, in case of pointers to StackObjects, so
        # I can't use list comprehensions. Must use a loop. I tried. --Cobi.
        for s in self.stack:
            state.stack.append(GameState.copy_stack_object(self, state, s))
        for s in self.super_stack:
            state.super_stack.append(GameState.copy_stack_object(self,
                                                                 state, s))
        # finally, copy the track_list, which can contain any types
        new_track_list = GameState.copy_arbitrary_list(self, state, track_list)
        # return!
        return state, new_track_list

    @staticmethod
    def copy_stack_object(state_orig: GameState, state_new: GameState,
                          obj: StackObject) -> StackObject:
        """This function assumes that everything except the
        stack and superstack have already been copied
        correctly. In other words, all Cardboards have
        already been copied. It is only StackObjects which
        remain to be copied."""
        # if this StackObject is a pointer to a DIFFERENT StackObject on the
        # stack which already has a copy, then just return a pointer to that
        # copy. (Relevant for e.g. counterspell, which targets a StackObject)
        if isinstance(obj, StackObject) and obj in state_orig.stack:
            index = state_orig.stack.index(obj)
            if len(state_new.stack) > index:
                return state_new.stack[index]
        # If card is ACTUALLY on the stack, then just make new copy of it. But
        # if it's in a non-stack zone, this is a pointer, and we need to find
        # the copied version of whatever it's pointing to.
        if obj.card.zone == ZONE.STACK:
            new_card = obj.card.copy()
        else:
            zone_orig = state_orig.get_zone(obj.card.zone)
            zone_new = state_new.get_zone(obj.card.zone)
            # look for true equality (not just equivalence) in old cards
            jj = [ii for ii, c in enumerate(zone_orig) if c is obj.card][0]
            new_card = zone_new[jj]
        # the StackObject's list of choices is copied by another function
        new_choices = GameState.copy_arbitrary_list(state_orig, state_new,
                                                    obj.choices)
        return obj.__class__(ability=obj.ability, card=new_card,
                             choices=new_choices)

    @staticmethod
    def copy_arbitrary_list(state_orig: GameState, state_new: GameState,
                            list_to_copy: list | tuple) -> list:
        """This function assumes that everything except the
        stack and superstack have already been copied
        correctly. In other words, all Cardboards have
        already been copied. This function returns a copy of
        the given list, with all Cardboards and StackObjects
        replaced by their appropriate copies. List is allowed
        to contain other types of objects too."""
        # objects in this list can be several types: Cardboard, StackObject,
        # lists / tuples / iterables, and immutable types
        new_list = []
        for item in list_to_copy:
            if isinstance(item, Cardboard):
                if item.zone == ZONE.STACK:
                    new_card = item.copy()  # truly on stack, so isn't ref
                else:
                    zone_orig = state_orig.get_zone(item.zone)
                    zone_new = state_new.get_zone(item.zone)
                    jj = [ii for ii, c in enumerate(zone_orig) if c is item][0]
                    new_card = zone_new[jj]
                new_list.append(new_card)
            elif isinstance(item, StackObject):
                new_obj = GameState.copy_stack_object(state_orig, state_new,
                                                      item)
                new_list.append(new_obj)
            elif isinstance(item, list) or isinstance(item, tuple):
                new_iterable = GameState.copy_arbitrary_list(state_orig,
                                                             state_new, item)
                new_list.append(new_iterable)  # recurse!
            elif isinstance(item, int) or isinstance(item, str):
                new_list.append(item)  # immutable and passed by value
            else:
                raise ValueError("unknown type in choices list!")
        return list_to_copy.__class__(new_list)

    def copy(self) -> GameState:
        return self.copy_and_track([])[0]

    def get_zone(self, zone_name) -> List[Cardboard] | List[StackObject]:
        if zone_name == ZONE.DECK or zone_name == ZONE.DECK_BOTTOM:
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

    def get_all_history(self):
        text = ""
        if self.previous_state is not None:
            text += self.previous_state.get_all_history()
            text += "\n-----"
        text += self.events_since_previous
        return text

    @property
    def has_options(self) -> bool:
        """Either has items on the stack to resolve, or has
        activated abilities that can be activated (including
        mana abilities), or has cards that can be cast."""
        return (len(self.stack) + len(self.get_valid_activations())
                + len(self.get_valid_castables())) > 0

    # -----MUTATING FUNCTIONS

    def re_sort(self, zone_name):
        """sort the specified zone, if it is a zone that is supposed
        to be sorted"""
        if zone_name == ZONE.HAND:
            self.hand.sort(key=Cardboard.get_id)
        elif zone_name == ZONE.FIELD:
            self.field.sort(key=Cardboard.get_id)
        elif zone_name == ZONE.GRAVE:
            self.grave.sort(key=Cardboard.get_id)
        # no other zones are sorted, so we're done.

    def MoveZone(self, cardboard, destination):
        """Move the specified piece of cardboard from the zone
        it is currently in to the specified destination zone.
        Raises IndexError if the cardboard is not in the zone
        it claims to be in.
        Adds any triggered StackEffects to the super_stack.
        MUTATES.
        """
        mover = MoveToZone(destination)
        mover.add_self_to_state_history = lambda g, c, ch: None  # silent
        mover.do_it(self, cardboard, [])

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
                MoveToZone(ZONE.GRAVE).do_it(self, cardboard, [])
                continue  # don't increment counter
            i += 1
        # legend rule   # TODO

    def step_untap(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack."""
        was_tracking = self.is_tracking_history
        if self.is_tracking_history:
            turn = self.turn_count
            self.events_since_previous += "\nUntap step: now turn %i" % turn
        self.pool = ManaPool("")
        self.stack = []
        self.turn_count += 1
        self.has_played_land = False
        self.num_spells_cast = 0  # reset this counter
        # temporarily turn off tracking for these Untaps
        self.is_tracking_history = False
        for card in self.field:
            UntapSelf().do_it(self, card, [])
            card.summon_sick = False
            # erase the invisible counters
            card.counters = [c for c in card.counters if
                             c[0] not in ("@", "$")]
        self.is_tracking_history = was_tracking  # reset tracking to how it was

    def step_upkeep(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack."""
        if self.is_tracking_history:
            self.events_since_previous += "\nUpkeep step"
        for cardboard in self.hand + self.field + self.grave:
            for ability in cardboard.rules_text.trig_upkeep:
                new_effect = StackAbility(ability, cardboard, [])
                self.super_stack.append(new_effect)

    def step_draw(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack.
           Draws from index 0 of deck."""
        was_tracking = self.is_tracking_history
        if self.is_tracking_history:
            self.events_since_previous += "\nDraw step"
        # temporarily turn off tracking for this Draw
        self.is_tracking_history = False
        DrawCard().do_it(self, None, [])
        self.is_tracking_history = was_tracking  # reset tracking to how it was

    def resolve_top_of_stack(self) -> List[GameState]:
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
        assert (isinstance(self.stack[-1], StackObject))
        new_state = self.copy()
        # remove StackObject from the stack
        stack_obj = new_state.stack.pop(-1)
        tuple_list = [(new_state, stack_obj.card, [])]
        # perform the effect (resolve ability, perform spell, etc)
        if stack_obj.effect is not None:
            tuple_list = stack_obj.effect.do_it(new_state, stack_obj.card,
                                                stack_obj.choices)
        # if card is on stack (not just a pointer), move it to destination zone
        if stack_obj.card.zone == ZONE.STACK:
            mover = MoveToZone(stack_obj.card.rules_text.cast_destination)
            for g, s, ch in tuple_list:
                mover.do_it(g, s, ch)  # mutates in-place
        # clear the superstack and return!
        results = []
        for state2, _, _ in tuple_list:
            results += state2.clear_super_stack()
        return results

    def clear_super_stack(self) -> List[GameState]:
        """Returns a list of GameStates where the objects on the super_stack
        have been placed onto the stack in all possible orders or otherwise
        dealt with. If super_stack is empty, returns [self].
        DOES NOT MUTATE."""
        # base case: no items on super_stack
        if len(self.super_stack) == 0:
            return [self]
        results: List[GameState] = []
        # pick a super_stack effect to move to the stack
        for item in Choices.choose_exactly_one(
                list(enumerate(self.super_stack)),
                "Add to stack"):
            ii = item[0]  # index first, then object second
            new_state = self.copy()
            stack_ability = new_state.super_stack.pop(ii)
            if isinstance(stack_ability.ability.trigger, AsEnterEffect):
                # if the ability contains an AsEntersEffect, then enact
                # it immediately rather than putting it on the stack.
                tuple_list = stack_ability.effect.do_it(new_state,
                                                        stack_ability.card,
                                                        stack_ability.choices)
                results += [g for g, _, _, in tuple_list]
            else:
                new_state.stack.append(stack_ability)
                results.append(new_state)
        # recurse
        final_results = []
        for state in results:
            final_results += state.clear_super_stack()
        return final_results

    # def step_cleanup(self):
    #     if self.is_tracking_history:
    #         self.events_since_previous += "\nCleanup"
    #     # discard down to 7 cards
    #     if len(self.hand) > 7:
    #         discard_list = Choices.choose_exactly_n(self.hand,
    #                                                 len(self.hand) - 7,
    #                                                 "discard to hand size")
    #         if self.is_tracking_history:
    #             print("discard:", [str(c) for c in discard_list])
    #         for card in discard_list:
    #             MoveToZone(ZONE.GRAVE).do_it(self, card, [])
    #     # clear any floating mana
    #     if self.is_tracking_history and self.pool.cmc() > 0:
    #         print("end with %s" % (str(self.pool)))
    #     for color in self.pool.data.keys():
    #         self.pool.data[color] = 0
    #     # pass the turn
    #     if not self.is_my_turn:
    #         self.turn_count += 1
    #         self.has_played_land = False
    #     self.is_my_turn = not self.is_my_turn

    def step_attack(self):
        if self.is_tracking_history:
            self.events_since_previous += "\nGo to combat"
        print("not yet implemented")
        return

    # -------------------------------------------------------------------------

    def get_valid_activations(self) -> List[
        Tuple[ActivatedAbility, Cardboard, list]]:
        """
        Return a list of all abilities that can be put on the
        stack right now. The form of the return is a tuple of
        the inputs that Verb.PlayAbility needs in order
        to put a newly activated ability onto the stack.
        """
        activatables = []
        active_objects = []  # objects I've already checked through
        for source in self.hand + self.field + self.grave:
            if any([source.is_equiv_to(ob) for ob in active_objects]):
                continue  # skip cards equivalent to those already searched
            add_object = False
            for ability in source.get_activated():
                # find available choice options, see if any let me activate
                for choices in ability.get_cast_options(self, source):
                    if ability.can_be_cast(self, source, choices):
                        # this ability with this set of choices is castable!
                        activatables.append((ability, source, choices))
                        add_object = True
            if add_object:  # track any object whose ability we looked at
                active_objects.append(source)
        return activatables

    def get_valid_castables(self) -> List[Tuple[Cardboard, list]]:
        """Return a list of all cast-able cards that can be put
        on the stack right now, as a list of Cardboard's which
        have not yet been paid for or moved from their current
        zones. Think of these like pointers."""
        castables = []
        # look for all cards that can be cast
        active_objects = []
        for card in self.hand:
            if any([card.is_equiv_to(ob) for ob in active_objects]):
                continue  # skip cards equivalent to those already searched
            add_object = False
            # find available choice options, see if any let me cast the card
            for choices in card.get_cast_options(self):
                if card.can_be_cast(self, choices):
                    castables.append((card, choices))
                    add_object = True
            if add_object:  # track any card that can be cast at least one way
                active_objects.append(card)
        return castables
