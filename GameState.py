# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, Tuple
# if TYPE_CHECKING:
#     from Abilities import ActivatedAbility

from Cardboard import Cardboard, CardNull  # actually needs
import Getters as Get  # actually needs
import ZONE
from ManaHandler import ManaPool
from Stack import StackAbility, StackCardboard, StackTrigger, StackObject
from Verbs import MoveToZone, DrawCard, Untap
import Choices
from Abilities import ActivatedAbility


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

    PHASES = ["untap", "upkeep", "draw", "main1", "combat", "main2",
              "endstep", "cleanup"]

    def __init__(self, num_players: int = 1):
        # super_stack is a list of StackTrigger waiting to be put onto
        # the real stack. NOTHING CAN BE EXECUTED WHILE STUFF IS ON
        # THE SUPERSTACK (incl state-based)
        self.stack: List[StackCardboard | StackAbility] = []
        self.super_stack: List[StackTrigger] = []
        self.player_list: List[Player] = []
        for _ in range(num_players):
            Player(self)  # adds single new player to the player_list
        self.active_player_index: int = 0
        self.priority_player_index: int = 0
        self.phase = 0
        # If we are tracking history, then we write down the previous distinct
        # GameState and a string describing how we got from there to here.
        # Things that mutate will add to the string, and things that copy
        # will write down the original state and clear the string.
        self.is_tracking_history: bool = False
        self.previous_state: GameState | None = None
        self.events_since_previous: str = ""

    def __hash__(self):
        return self.get_id().__hash__()  # hash the string of the get_id

    def __neg__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        return isinstance(other, GameState) and self.get_id() == other.get_id()

    def __str__(self):
        txt = "\n".join([str(p) for p in self.player_list])
        txt += "\nPhase %i" % self.phase
        if len(self.stack) > 0:
            txt += "\nSTACK:  " + ",".join([str(s) for s in self.stack])
        if len(self.super_stack) > 0:
            txt += "\nSUPER:  " + ",".join([str(s) for s in self.super_stack])
        return txt

    def get_id(self):
        players = [p.get_id() for p in self.player_list]
        phase = "\nPhase %i" % self.phase
        stack = ",".join([c.get_id() for c in self.stack])
        super_stack = ",".join([c.get_id() for c in self.super_stack])
        return "\n".join(players + [phase, stack, super_stack])

    @property
    def active(self) -> Player:
        return self.player_list[self.active_player_index]

    @property
    def priority(self) -> Player:
        return self.player_list[self.priority_player_index]

    @property
    def total_turns(self):
        return sum([p.turn_count for p in self.player_list])

    def copy_and_track(self, track_list) -> Tuple[GameState, list]:
        """Returns a disconnected copy of the gamestate and also
        a list of Cardboards in the new gamestate corresponding
        to the list of Cardboards we were asked to track. This
        allows tracking "between split universes."
        If track_list has non-Cardboard objects, they're also
        returned"""
        # make new Gamestate and start copying attributes by value
        state = GameState(0)
        # copy the player list. new players automatically added to state.
        [p.copy(state) for p in self.player_list]
        # copy history stuff
        state.is_tracking_history = self.is_tracking_history
        state.previous_state = self if state.is_tracking_history else None
        state.events_since_previous = ""
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
    def copy_stack_object(state_orig: GameState, state_new: GameState, obj):
        """This function assumes that everything except the
        stack and superstack have already been copied
        correctly. In other words, all Cardboards have
        already been copied. It is only StackObjects which
        remain to be copied."""
        # if this StackObject is a pointer to a DIFFERENT StackObject on the
        # stack which already has a copy, then just return a pointer to that
        # copy. (Relevant for e.g. counterspell, which targets a StackObject)
        if obj in state_orig.stack:
            index = state_orig.stack.index(obj)
            if len(state_new.stack) > state_orig.stack.index(obj):
                return state_new.stack[index]
        # If card is ACTUALLY on the stack, then just make new copy of it. But
        # if it's in a non-stack zone, this is a pointer, and we need to find
        # the copied version of whatever it's pointing to.
        if obj.card.zone == ZONE.STACK:
            new_card = obj.card.copy()
        else:
            zone_orig = obj.card.get_home_zone_list(state_orig)
            zone_new = obj.card.get_home_zone_list(state_new)
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
                    zone_orig = item.get_home_zone_list(state_orig)
                    zone_new = item.get_home_zone_list(state_new)
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
            else:
                new_list.append(item)  # immutable and passed by value, I hope
        return list_to_copy.__class__(new_list)

    def copy(self) -> GameState:
        return self.copy_and_track([])[0]

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
        opts = sum(
            [len(p.get_valid_activations()) + len(p.get_valid_castables())
             for p in self.player_list])
        return opts + len(self.stack) > 0

    def get_zone(self, zone, player_index: int | None):
        """Returns the zone belonging to the specified player.
        If `player_index` is None and the zone is a private zone
        that ought to belong to only a single player (HAND, DECk,
        FIELD, GRAVE), then returns a concatenated list of ALL
        of those zones. This latter functionality is useful for
        stuff like "find every creature in play, no matter who
        controls it." """
        if zone in [ZONE.NEW, ZONE.UNKNOWN]:
            raise ValueError("These zones don't actually exist!")
        elif zone == ZONE.STACK:
            return self.stack
        elif player_index is not None:
            return self.player_list[player_index].get_zone(zone)
        else:
            new_list = []
            for player in self.player_list:
                new_list += player.get_zone(zone)
            return new_list

    def get_all_public_cards(self):
        faceup = []
        for player in self.player_list:
            faceup += player.field + player.grave
        return faceup

    def give_to(self, cardboard, destination, player_index=0):
        """Move the specified piece of cardboard from the zone
        it is currently in to the specified destination zone.
        Raises IndexError if the cardboard is not in the zone
        it claims to be in.
        Adds any triggered StackEffects to the super_stack.
        MUTATES.
        """
        if cardboard.controller_index < 0:
            cardboard.controller_index = player_index
        if cardboard.owner_index < 0:
            cardboard.owner_index = player_index
        mover = MoveToZone(destination)
        mover.add_self_to_state_history = lambda g, c, ch: None  # silent
        mover.do_it(self, cardboard, [])

    # -------------------------------------------------------------------------

    def state_based_actions(self):
        """MUTATES. Performs any state-based actions like killing creatures if
        toughness is less than 0.
        Adds any triggered StackAbilities to the super_stack.
        """
        for player in self.player_list:
            i = 0
            while i < len(player.field):
                cardboard = player.field[i]
                toughness = Get.Toughness().get(self, cardboard)
                if toughness is not None and toughness <= 0:
                    MoveToZone(ZONE.GRAVE).do_it(self, cardboard, [])
                    continue  # don't increment counter
                i += 1
            # legend rule   # TODO

    def step_untap(self):
        """MUTATES. Adds any triggered StackAbilities to the
        super_stack. This function is where things reset for
        the turn."""
        was_tracking = self.is_tracking_history
        if self.is_tracking_history:
            turn = self.active.turn_count
            ii = self.active_player_index
            self.events_since_previous += "\nUntap step: P%i T%i" % (turn, ii)
        self.phase = GameState.PHASES.index("untap")
        # make sure that the stack is empty
        self.stack = []
        self.super_stack = []
        # resets that happen for all players
        for player in self.player_list:
            player.pool = ManaPool("")
            player.num_spells_cast = 0
            player.num_lands_played = 0
            for card in player.field:
                # erase the invisible counters
                card.counters = [c for c in card.counters if c[0] not in "@$"]
        # things which happen only for the newly active player
        self.active.turn_count += 1
        # temporarily turn off tracking for these Untaps
        self.is_tracking_history = False
        for card in self.active.field:
            Untap().do_it(self, card, [])
            card.summon_sick = False
        self.is_tracking_history = was_tracking  # reset tracking to how it was

    def step_upkeep(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack."""
        if self.is_tracking_history:
            self.events_since_previous += "\nUpkeep step"
        self.phase = GameState.PHASES.index("upkeep")
        for card in self.get_all_public_cards():
            for ability in card.rules_text.trig_upkeep:
                new_effect = StackTrigger(ability, card, [])
                self.super_stack.append(new_effect)

    def step_draw(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack.
           Draws from index 0 of deck."""
        was_tracking = self.is_tracking_history
        if self.is_tracking_history:
            self.events_since_previous += "\nDraw step"
        self.phase = GameState.PHASES.index("draw")
        # temporarily turn off tracking for this Draw
        self.is_tracking_history = False
        DrawCard().do_it(self, CardNull(), [])
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
        # pick a super_stack StackTrigger to move to the stack
        for item in Choices.choose_exactly_one(
                list(enumerate(self.super_stack)),
                "Add to stack"):
            ii = item[0]  # index first, then object second
            new_state = self.copy()
            trigger = new_state.super_stack.pop(ii)
            ability = trigger.ability
            card = trigger.card
            cause = trigger.choices[0]
            # get_target_options adds `cause` to `choices` for creating the
            # new StackTrigger
            for choices in ability.get_target_options(new_state, card, cause):
                if ability.can_be_added(new_state, card, choices):
                    results += ability.add_to_stack(new_state, card, choices)
                else:
                    # If can't resolve ability, still remove it from the stack.
                    # For example, invalid target still removes the trigger
                    # from the super_stack.
                    results += [new_state.copy()]
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
        self.phase = GameState.PHASES.index("combat")
        print("not yet implemented")
        return


# ---------------------------------------------------------------------------


class Player:
    def __init__(self, state: GameState):
        """Initializer also adds the new Player to the
        GameState's list of players"""
        self.gamestate: GameState = state
        self.player_index: int = len(state.player_list)
        state.player_list.append(self)
        self.turn_count: int = 0
        self.life: int = 20
        self.num_lands_played: int = 0
        self.num_spells_cast: int = 0  # number of spells you cast this turn
        self.pool: ManaPool = ManaPool("")
        # game zones
        self.deck: List[Cardboard] = []  # list of Cardboard objects
        self.hand: List[Cardboard] = []  # list of Cardboard objects
        self.field: List[Cardboard] = []  # list of Cardboard objects
        self.grave: List[Cardboard] = []  # list of Cardboard objects

    @property
    def is_my_turn(self):
        return self.player_index == self.gamestate.active_player_index

    @property
    def is_my_priority(self):
        return self.player_index == self.gamestate.priority_player_index

    @property
    def land_drops_left(self):
        return 1 - self.num_lands_played

    def __str__(self):
        txt = "Player%i" % self.player_index
        txt += "(ACTIVE)" if self.is_my_turn else ""
        txt += "(PRIORITY)" if self.is_my_priority else ""
        txt += "  T:%2i" % self.turn_count
        txt += "  HP:%2i" % self.life
        txt += "  Deck:%2i" % len(self.deck)
        txt += "  Mana:(%6s)" % str(self.pool)
        if len(self.hand) > 0:
            txt += "\nHAND:   " + ",".join([str(card) for card in self.hand])
        if len(self.field) > 0:
            txt += "\nFIELD:  " + ",".join([str(card) for card in self.field])
        if len(self.grave) > 0:
            txt += "\nGRAVE:  " + ",".join([str(card) for card in self.grave])
        return txt

    def get_id(self):
        index = "P%i" % self.player_index
        index += "A" if self.is_my_turn else ""
        index += "P" if self.is_my_priority else ""
        turn = "t%i" % self.turn_count
        life = "life%i" % self.life
        land = "land%i" % self.num_lands_played
        storm = "storm%i" % self.num_spells_cast
        pool = "(%s)" % str(self.pool)
        deck = "deck%i" % len(self.deck)
        hand = ",".join([c.get_id() for c in self.hand])
        field = ",".join([c.get_id() for c in self.field])
        grave = ",".join([c.get_id() for c in self.grave])
        return "|".join([index, turn, life, land, storm, pool,
                         deck, hand, field, grave])

    def get_zone(self, zone_name) -> List[Cardboard] | List[StackObject]:
        if zone_name == ZONE.DECK or zone_name == ZONE.DECK_BOTTOM:
            zone = self.deck
        elif zone_name == ZONE.HAND:
            zone = self.hand
        elif zone_name == ZONE.FIELD:
            zone = self.field
        elif zone_name == ZONE.GRAVE:
            zone = self.grave
        else:
            raise IndexError
        return zone

    def copy(self, new_state: GameState) -> Player:
        """Returns a disconnected copy of the Player and also
        a list of Cardboards in the new Player corresponding
        to the list of Cardboards we were asked to track. This
        allows tracking "between split universes."
        If track_list has non-Cardboard objects, they're also
        returned"""
        new_player = Player(new_state)
        # copy the ints by value
        new_player.turn_count = self.turn_count
        new_player.life = self.life
        new_player.num_lands_played = self.num_lands_played
        new_player.num_spells_cast = self.num_spells_cast
        # copy mana pool
        new_player.pool = self.pool.copy()
        # for the lists of Cardboards (hand, deck, field, grave), spin
        # through making copies as I go. The ordering will be maintained
        new_player.hand = [c.copy() for c in self.hand]
        new_player.deck = [c.copy() for c in self.deck]
        new_player.field = [c.copy() for c in self.field]
        new_player.grave = [c.copy() for c in self.grave]
        return new_player

    def get_valid_activations(self) -> List[Tuple[
        ActivatedAbility, Cardboard, list]]:
        """
        Return a list of all abilities that can be put on the
        stack right now. The form of the return is a tuple of
        the inputs that Verb.PlayAbility needs in order
        to put a newly activated ability onto the stack.
        """
        activatables = []
        active_objects = []  # objects I've already checked through
        game = self.gamestate
        for source in self.hand + self.field + self.grave:
            if any([source.is_equiv_to(ob) for ob in active_objects]):
                continue  # skip cards equivalent to those already searched
            add_object = False
            for ability in source.get_activated():
                # find available choice options, see if any let me activate
                for choices in ability.get_activation_options(game, source):
                    if ability.can_be_activated(game, source, choices):
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
        active_objects = []
        game = self.gamestate
        for card in self.hand:
            if any([card.is_equiv_to(ob) for ob in active_objects]):
                continue  # skip cards equivalent to those already searched
            add_object = False
            # find available choice options, see if any let me cast the card
            for choices in card.get_cast_options(game):
                if card.can_be_cast(game, choices):
                    castables.append((card, choices))
                    add_object = True
            if add_object:  # track any card that can be cast at least one way
                active_objects.append(card)
        return castables

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
