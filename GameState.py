# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, Tuple, Type
# if TYPE_CHECKING:
#     from Abilities import ActivatedAbility

from Cardboard import Cardboard  # actually needs
import Getters as Get  # actually needs
import Zone
from ManaHandler import ManaPool
from Stack import StackCardboard, StackTrigger, StackObject
from Verbs import MoveToZone, DrawCard, Untap
import Choices

import tkinter as tk


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
    of the game and provides tools for other_input to progress the game.
    """

    PHASES = ["untap", "upkeep", "draw", "main1", "combat", "main2",
              "endstep", "cleanup"]

    def __init__(self, num_players: int = 1):
        # super_stack is a list of StackTrigger waiting to be put onto
        # the real stack. NOTHING CAN BE EXECUTED WHILE STUFF IS ON
        # THE SUPERSTACK (incl state-based)
        self.stack: List[StackObject] = []
        self.super_stack: List[StackTrigger] = []
        self.player_list: List[Player] = []
        for _ in range(num_players):
            Player(self)  # adds single new asking_player to the player_list
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
    def total_turns(self) -> int:
        return sum([p.turn_count for p in self.player_list])

    @property
    def game_over(self) -> bool:
        return not any([pl.victory_status == "" for pl in self.player_list])

    def copy_and_track(self, track_list: list | tuple
                       ) -> Tuple[GameState, list | tuple]:
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
        for obj in self.stack:
            state.stack.append(obj.copy(self, state))
        for obj in self.super_stack:
            state.super_stack.append(obj.copy(self, state))
        # finally, copy the track_list, which can contain any types
        new_track_list = GameState.copy_arbitrary_list(self, state, track_list)
        # return!
        return state, new_track_list

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
                new_list.append(item.copy_as_pointer(state_new))
            elif isinstance(item, StackObject):
                new_list.append(item.copy(state_orig, state_new))
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

    def add_to_stack(self, obj: StackObject):
        if hasattr(obj.obj, "zone"):
            obj.obj.zone = Zone.Stack()
        self.stack.append(obj)

    def get_all_public_cards(self):
        faceup = []
        for player in self.player_list:
            faceup += player.field + player.grave
        return faceup

    def give_to(self, cardboard,
                destination: Type[Zone.DeckTop | Zone.DeckBottom | Zone.Hand
                                  | Zone.Field],
                player_index=0):
        """Move the specified piece of cardboard from the zone
        it is currently in to the specified destination zone.
        Raises IndexError if the cardboard is not in the zone
        it claims to be in.
        Adds any triggered StackEffects to the super_stack.
        MUTATES.
        """
        if cardboard.owner_index < 0:
            cardboard.owner_index = player_index
        mover = MoveToZone(destination(player_index))
        mover.add_self_to_state_history = lambda *args: None  # silent
        mover.do_it(self, player_index, cardboard)

    # -------------------------------------------------------------------------

    def state_based_actions(self):
        """MUTATES. Performs any state-based actions like killing creatures if
        toughness is less than 0.
        Adds any triggered StackAbilities to the super_stack.
        """
        for player in self.player_list:
            i = 0
            while i < len(player.field):
                card = player.field[i]
                toughness = Get.Toughness().get(self, player.player_index,
                                                card)
                if toughness is not None and toughness <= 0:
                    mover = MoveToZone(Zone.Grave(player.player_index))
                    mover.do_it(self, player.player_index, card)
                    continue  # don't increment counter
                i += 1
            # legend rule   # TODO
            # Sacrifice().do_it(self, player.player_index, card)

    def pass_turn(self):
        self.phase = 0
        self.active_player_index = ((self.active_player_index + 1)
                                    % len(self.player_list))
        self.priority_player_index: int = self.active_player_index
        # make sure that the stack is empty
        self.stack = []
        self.super_stack = []

    def step_untap(self):
        """MUTATES. Adds any triggered StackAbilities to the
        super_stack. This function is where things reset for
        the turn."""
        was_tracking = self.is_tracking_history
        if self.is_tracking_history:
            turn = self.active.turn_count
            ii = self.active_player_index
            text = "\nUntap step: Player%i Turn%i" % (turn, ii)
            self.events_since_previous += text
        self.phase = GameState.PHASES.index("untap")
        # resets that happen for all players
        for player in self.player_list:
            player.pool = ManaPool("")
            player.num_spells_cast = 0
            player.num_lands_played = 0
            for card in player.field:
                # erase the invisible counters
                card.counters = [c for c in card.counters if c[0] not in "@$"]
        # things which happen only for the newly active asking_player
        self.active.turn_count += 1
        # temporarily turn off tracking for these Untaps
        self.is_tracking_history = False
        for card in self.active.field:
            Untap().do_it(self, self.active_player_index, card, [])
            card.summon_sick = False
        self.is_tracking_history = was_tracking  # reset tracking to how it was

    def step_upkeep(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack."""
        if self.is_tracking_history:
            self.events_since_previous += "\nUpkeep step"
        self.phase = GameState.PHASES.index("upkeep")
        for card in self.get_all_public_cards():
            for ability in card.rules_text.trig_upkeep:
                # adds any triggering abilities to self.super_stack
                ability.add_any_to_super(self, self, card, None)

    def step_draw(self):
        """MUTATES. Adds any triggered StackAbilities to the super_stack.
           Draws from player_index 0 of deck."""
        was_tracking = self.is_tracking_history
        if self.is_tracking_history:
            self.events_since_previous += "\nDraw step"
        self.phase = GameState.PHASES.index("draw")
        # temporarily turn off tracking for this Draw
        self.is_tracking_history = False
        DrawCard().do_it(self, self.active_player_index, None, [])
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
        obj = new_state.stack.pop(-1)
        if obj.effect is None:
            tuple_list = [(new_state, obj.player_index, obj.source_card, [])]
        else:
            # perform the effect (resolve ability, perform spell, etc)
            tuple_list = obj.effect.do_it(new_state, obj.player_index,
                                          obj.source_card, obj.choices)
        # if card is on stack (not just a pointer), move it to destination zone
        if isinstance(obj.obj, Cardboard):
            dest = obj.obj.rules_text.cast_destination.copy()
            dest.player = obj.player_index  # update to give to correct player
            for gm, pl, cd, ins in tuple_list:
                MoveToZone(dest).do_it(gm, pl, cd, [])
        # clear the superstack and return!
        results = []
        for tup in tuple_list:
            results += tup[0].clear_super_stack()
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
        # active player puts their triggers onto the stack first. So, find the
        # first player in player-order who has a trigger on the super_stack.
        player = self.active_player_index
        theirs = [(ii, trig) for (ii, trig) in enumerate(self.super_stack)
                  if trig.player_index == player]
        while len(theirs) == 0:
            player = player + 1 % len(self.player_list)
            theirs = [(ii, trig) for (ii, trig) in enumerate(self.super_stack)
                      if trig.player_index == player]
            # only back to active player if super_stack==[]. breaks base case.
            assert player != self.active_player_index
        # pick a super_stack StackTrigger to move to the stack
        maker = self.player_list[player].decision_maker
        for item in Choices.choose_exactly_one(theirs, "Add to stack", maker):
            ii = item[0]  # index first, then object second
            state2 = self.copy()
            obj = state2.super_stack.pop(ii)
            if not obj.caster_verb.can_be_done(state2, obj.player_index,
                                               obj.source_card, [obj]):
                # If can't resolve ability, still use the GameState where it
                # was removed from the stack. e.g. invalid targets still
                # removes the trigger from the super_stack.
                results += [state2]
            else:
                results += [tup[0] for tup in
                            obj.caster_verb.do_it(state2, obj.player_index,
                                                  obj.source_card, [obj])]
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
    #             MoveToZone(ZONE.GRAVE).do_it(self, self.active_player_index,
    #                                          card,)
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

    def build_tk_display(self, parentframe):
        # button to do the next thing
        if len(self.game.stack) == 0:
            b = tk.Button(self.status, text="Pass\nturn", bg="yellow",
                          width=7,
                          command=self.PassTurn)
            b.grid(row=1, column=5, padx=5, pady=5)
        else:
            b = tk.Button(self.status, text="Resolve\nnext", bg="yellow",
                          width=7,
                          command=self.ResolveTopOfStack)
            b.grid(row=1, column=5, padx=5, pady=2)
        # undo button
        b2 = tk.Button(self.status, text="undo", bg="yellow",
                       command=self.Undo)
        b2.grid(row=1, column=6, padx=5, pady=2)
        # auto-resolve button
        b3 = tk.Checkbutton(self.status, text="Auto-resolve all",
                            variable=self.var_resolveall,
                            indicatoron=True)
        # onvalue=1,background='grey')#,selectcolor='green')
        b3.grid(row=2, column=5, columnspan=2, padx=5, pady=5)


# ---------------------------------------------------------------------------


class Player:
    def __init__(self, state: GameState, decision_maker: str = "try_all"):
        """Initializer also adds the new Player to the
        GameState's list of players"""
        self.gamestate: GameState = state
        # duck-type to Cardboard.player_index
        self.player_index: int = len(state.player_list)
        state.player_list.append(self)
        self.turn_count: int = 0
        self.life: int = 20
        self.num_lands_played: int = 0
        self.num_spells_cast: int = 0  # number of spells you cast this turn
        self.pool: ManaPool = ManaPool("")
        self.victory_status: str = ""  # "Playing". can also be "W" or "L".
        # game zones
        self.deck: List[Cardboard] = []  # list of Cardboard objects
        self.hand: List[Cardboard] = []  # list of Cardboard objects
        self.field: List[Cardboard] = []  # list of Cardboard objects
        self.grave: List[Cardboard] = []  # list of Cardboard objects
        # how the player makes decisions. ["try_all", "try_one", or "manual"]
        self.decision_maker: str = decision_maker

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
        txt += "(WON)" if self.victory_status == "W" else ""
        txt += "(LOST)" if self.victory_status == "L" else ""
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
        index += "" if self.victory_status == "" else self.victory_status
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

    # def get_zone(self, zone_name) -> List[Cardboard] | List[StackObject]:
    #     if zone_name == ZONE.DECK or zone_name == ZONE.DECK_BOTTOM:
    #         zone = self.deck
    #     elif zone_name == ZONE.HAND:
    #         zone = self.hand
    #     elif zone_name == ZONE.FIELD:
    #         zone = self.field
    #     elif zone_name == ZONE.GRAVE:
    #         zone = self.grave
    #     else:
    #         raise IndexError
    #     return zone

    def has_type(self, some_type):
        """duck-typed with Cardboard so SOURCE is valid type hint"""
        return isinstance(self, some_type)

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

    def get_valid_activations(self) -> List[StackObject]:
        """
        Return a list of all abilities that can be put on the
        stack right now. The form of the return is a tuple of
        the inputs that Verb.PlayAbility needs in order
        to put a newly activated ability onto the stack.
        """
        activatables: List[StackObject] = []
        active_objects = []  # objects I've already checked through
        game = self.gamestate
        for source in self.hand + self.field + self.grave:
            if any([source.is_equiv_to(ob) for ob in active_objects]):
                continue  # skip cards equivalent to those already searched
            add_object = False
            for ability in source.get_activated():
                can_do = ability.valid_stack_objects(game, self.player_index,
                                                     source)
                if len(can_do) > 0:
                    add_object = True
                activatables += can_do
            if add_object:  # track object to not look at any similar again.
                active_objects.append(source)
        return activatables

    def get_valid_castables(self) -> List[StackObject]:
        """Return a list of all cast-able cards that can be put
        on the stack right now, as a list of Cardboard's which
        have not yet been paid for or moved from their current
        zones. Think of these like pointers."""
        castables: List[StackCardboard] = []
        active_objects = []
        game = self.gamestate
        for card in self.hand:
            if any([card.is_equiv_to(ob) for ob in active_objects]):
                continue  # skip cards equivalent to those already searched
            can_do = card.valid_stack_objects(game)
            if len(can_do) > 0:
                active_objects.append(card)
                castables += can_do
        return castables

    def add_to_hand(self, card: Cardboard):
        """Hand is sorted and tracks Zone.location."""
        card.zone = Zone.Hand(self.player_index)
        self.hand.append(card)
        self.hand.sort(key=Cardboard.get_id)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(len(self.hand)):
            self.hand[ii].zone.location = ii

    def remove_from_hand(self, card: Cardboard):
        """Field is sorted and tracks Zone.location."""
        index = card.zone.location
        self.hand.pop(index)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(index, len(self.hand)):
            self.hand[ii].zone.location = ii

    def add_to_field(self, card: Cardboard):
        """Field is sorted and tracks Zone.location."""
        card.zone = Zone.Field(self.player_index)
        self.field.append(card)
        self.field.sort(key=Cardboard.get_id)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(len(self.field)):
            self.field[ii].zone.location = ii

    def remove_from_field(self, card: Cardboard):
        """Field is sorted and tracks Zone.location."""
        index = card.zone.location
        self.field.pop(index)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(index, len(self.field)):
            self.field[ii].zone.location = ii

    def add_to_grave(self, card: Cardboard):
        """Grave is sorted and tracks Zone.location."""
        card.zone = Zone.Grave(self.player_index)
        self.grave.append(card)
        self.grave.sort(key=Cardboard.get_id)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(len(self.grave)):
            self.grave[ii].zone.location = ii

    def remove_from_grave(self, card: Cardboard):
        """Grave is sorted and tracks Zone.location."""
        index = card.zone.location
        self.grave.pop(index)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(index, len(self.grave)):
            self.grave[ii].zone.location = ii

    def add_to_deck(self, card: Cardboard, dist_from_bottom: int):
        """Deck is not sorted but DOES track Zone.location."""
        # deck[0] is bottom, deck[-1] is top
        if dist_from_bottom < 0:
            # insert has strange negative indexing. otherwise 0 and -1 would
            # do the same thing. insert at len(list), not len-1, to be at end.
            dist_from_bottom += len(self.deck) + 1
        card.zone = Zone.Deck(self.player_index, dist_from_bottom)
        self.deck.insert(dist_from_bottom, card)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(dist_from_bottom, len(self.deck)):
            self.deck[ii].zone.location = ii

    def remove_from_deck(self, card: Cardboard):
        """Deck is not sorted but DOES track Zone.location."""
        index = card.zone.location
        self.deck.pop(index)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(index, len(self.deck)):
            self.deck[ii].zone.location = ii







    def RebuildHand(self):
        for widgets in self.hand.winfo_children():
            widgets.destroy()
        for ii, card in enumerate(self.game.hand):
            butt = card.build_tk_display(self.hand)
            abils = [a for a in card.get_activated()
                     if a.CanAfford(self.game, card)]
            # activated abilities in hand are not yet implemented
            assert (len(abils) == 0)
            if card.rules_text.CanAfford(self.game, card):
                butt.config(state="normal",
                            command=lambda c=card: self.CastSpell(c))
            else:
                butt.config(state="disabled")
            butt.grid(row=1, column=ii, padx=5, pady=3)