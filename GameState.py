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
from Stack import StackAbility, StackObject
from StackCardboard import StackCardboard
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
        self.verbose: bool = False
        self.history: List[str] = []

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
        s = "%s%i_%02ivs%02i%s_C%i" % (my_turn, self.turn_count,
                                       self.life, self.opponent_life,
                                       played_land, self.num_spells_cast)
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
        state.num_spells_cast = self.num_spells_cast
        state.verbose = self.verbose
        state.history = self.history.copy()
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
            i_end = stack_index
            for stack_obj in original_list:
                new_card = new_track_list[stack_index]
                i_end = stack_index + 1 + len(stack_obj.choices)
                new_choices = new_track_list[stack_index + 1:i_end]
                # build the new StackObject
                if isinstance(stack_obj, StackCardboard):
                    new_stack_obj = StackCardboard(new_card, new_choices)
                elif isinstance(stack_obj, StackAbility):
                    ability = stack_obj.ability  # does this need a copy?
                    new_stack_obj = StackAbility(ability, new_card,
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

    def copy(self) -> GameState:
        return self.copy_and_track([])[0]

    # -----MUTATING FUNCTIONS. They all return a list of StackEffects

    def get_zone(self, zone_name) -> List[Cardboard] | List[StackObject]:
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

    def MoveZone(self, cardboard, destination):
        """Move the specified piece of cardboard from the zone
        it is currently in to the specified destination zone.
        Raises IndexError if the cardboard is not in the zone
        it claims to be in.
        Adds any triggered StackEffects to the super_stack.
        MUTATES.
        """
        MoveToZone(destination).do_it(self, cardboard, [])

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
        self.pool = ManaPool("")
        self.stack = []
        self.turn_count += 1
        self.has_played_land = False
        self.num_spells_cast = 0  # reset this counter
        for card in self.field:
            UntapSelf().do_it(self, card, [])
            card.summon_sick = False
            # erase the invisible counters
            card.counters = [c for c in card.counters if
                             c[0] not in ("@", "$")]

    def step_upkeep(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack."""
        for cardboard in self.hand + self.field + self.grave:
            for ability in cardboard.rules_text.trig_upkeep:
                new_effect = StackAbility(ability, cardboard, [])
                self.super_stack.append(new_effect)

    def step_draw(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack.
           Draws from index 0 of deck."""
        DrawCard().do_it(self, None, [])

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
            if isinstance(stack_ability.ability.trigger, AsEnterEffect):
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

    def step_cleanup(self):
        # discard down to 7 cards
        if len(self.hand) > 7:
            discard_list = Choices.choose_exactly_n(self.hand,
                                                    len(self.hand) - 7,
                                                    "discard to hand size")
            if self.verbose:
                print("discard:", [str(c) for c in discard_list])
            for card in discard_list:
                MoveToZone(ZONE.GRAVE).do_it(self, card, [])
        # clear any floating mana
        if self.verbose and self.pool.cmc() > 0:
            print("end with %s" % (str(self.pool)))
        for color in self.pool.data.keys():
            self.pool.data[color] = 0
        # pass the turn
        if not self.is_my_turn:
            self.turn_count += 1
            self.has_played_land = False
        self.is_my_turn = not self.is_my_turn

    def step_attack(self):
        print("not yet implemented")
        return

    # -------------------------------------------------------------------------

    def get_valid_activations(self) -> List[
        Tuple[ActivatedAbility, Cardboard, list]]:
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
                        effects.append((ability, source, choices))
                        add_object = True
            if add_object:  # track any object whose ability we looked at
                active_objects.append(source)
        return effects

    def get_valid_castables(self) -> List[Cardboard]:
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
