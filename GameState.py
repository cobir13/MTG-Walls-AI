# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, Tuple, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from Abilities import ActiveAbilityHolder
    from Abilities import TriggeredAbilityHolder, TimedAbilityHolder

from Cardboard import Cardboard, CardNull  # actual need
import Getters as Get  # actually needs
import Zone
import Match2
import Verbs
from ManaHandler import ManaPool
from Stack import StackObject
from Verbs import MoveToZone, DrawCard, Untap, NullVerb
import Pilots
import Times


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

    def __init__(self, num_players: int = 1):
        # super_stack is a list of StackTrigger waiting to be put onto
        # the real stack. NOTHING CAN BE EXECUTED WHILE STUFF IS ON
        # THE SUPERSTACK (incl state-based)
        self.stack: List[StackObject] = []
        self.super_stack: List[Verbs.PlayAbility] = []
        self.player_list: List[Player] = []
        for _ in range(num_players):
            Player(self)  # adds single new asking_player to the player_list
        self.active_player_index: int = 0
        self.priority_player_index: int = 0
        self.phase: Times.Phase = Times.Phase.UNTAP
        # If we are tracking history, then we write down the previous distinct
        # GameState and a string describing how we got from there to here.
        # Things that mutate will add to the string, and things that copy
        # will write down the original state and clear the string.
        self.is_tracking_history: bool = False
        self.previous_state: GameState | None = None
        self.events_since_previous: str = ""
        # track triggers. lists are updated when a card changes zones.
        # Format is tuple of (source-Cardboard, triggered ability).
        # These lists are NOT incorporated into the GameState's ID and hash,
        # since they are derivable from the boardstate if necessary.
        self.trig_timed: List[TimedAbilityHolder] = []
        self.trig_event: List[TriggeredAbilityHolder] = []
        self.trigs_to_remove: List[TriggeredAbilityHolder] = []
        # track static effects the same way we track triggers
        self.statics: List[ActiveAbilityHolder] = []
        self.statics_to_remove: List[ActiveAbilityHolder] = []

    def __hash__(self):
        return self.get_id().__hash__()  # hash the string of the get_id

    def __neg__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        return isinstance(other, GameState) and self.get_id() == other.get_id()

    def __str__(self):
        txt = "\n".join([str(p) for p in self.player_list])
        txt += "\nPhase %s" % self.phase.name
        if len(self.stack) > 0:
            txt += "\nSTACK:  " + ",".join([str(s) for s in self.stack])
        if len(self.super_stack) > 0:
            txt += "\nSUPER:  " + ",".join([str(s) for s in self.super_stack])
        return txt

    def get_id(self):
        players = [p.get_id() for p in self.player_list]
        phase = "\n%s" % self.phase.name
        stack = "[%s]" % ",".join([c.get_id() for c in self.stack])
        super_stack = "[%s]" % ",".join([c.get_id() for c in self.super_stack])
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
        state.active_player_index = self.active_player_index
        state.priority_player_index = self.priority_player_index
        state.phase = self.phase
        # copy history stuff
        state.is_tracking_history = self.is_tracking_history
        state.previous_state = self if state.is_tracking_history else None
        state.events_since_previous = ""
        # now copy the stack and superstack, which are made of StackObjects.
        # Need to append as I go, in case of pointers to StackObjects, so
        # I can't use list comprehensions. Must use a loop. I tried. --Cobi.
        for obj in self.stack:
            state.stack.append(obj.copy(state))
        for obj in self.super_stack:
            state.super_stack.append(obj.copy(state))
        # finally, copy the track_list, which can contain any types
        new_track_list = GameState.copy_arbitrary_list(state, track_list)
        # copy each trigger and static effect in the various tracker lists
        state.trig_event = [h.copy(state) for h in self.trig_event]
        state.trigs_to_remove = [h.copy(state) for h in self.trigs_to_remove]
        state.trig_timed = [h.copy(state) for h in self.trig_timed]
        state.statics = [h.copy(state) for h in self.statics]
        state.statics_to_remove = [h.copy(state)
                                   for h in self.statics_to_remove]
        # return!
        return state, new_track_list

    @staticmethod
    def copy_arbitrary_list(state_new: GameState,
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
            if isinstance(item, list) or isinstance(item, tuple):
                new_iterable = GameState.copy_arbitrary_list(state_new, item)
                new_list.append(new_iterable)  # recurse!
            elif hasattr(item, "copy"):  # Verb, StackObject, Cardboard, Zone
                new_list.append(item.copy(state_new))
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
        mana abilities), or has cards that can be cast, or
        has something else to do in this phase."""
        opts = sum(
            [len(p.get_valid_activations()) + len(p.get_valid_castables())
             for p in self.player_list if p.want_to_act])
        return (opts + len(self.stack)) > 0

    def add_to_stack(self, obj: StackObject):
        if hasattr(obj.obj, "zone"):
            obj.obj.zone = Zone.Stack(len(self.stack))
        obj.zone = Zone.Stack(len(self.stack))
        self.stack.append(obj)

    def pop_from_stack(self, index: int = -1) -> StackObject:
        obj = self.stack.pop(index)
        for ii in range(index, len(self.stack) - 1):
            self.stack[ii].zone.location = ii
        return obj

    def give_to(self, card,
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
        if card.owner_index < 0:
            card.owner_index = player_index
        mover = MoveToZone(destination(player_index)).replace_subject(card)
        # mover doesn't have a player or a source or cause. hopefully ok.
        prev_tracking = self.is_tracking_history
        self.is_tracking_history = False  # don't track this move
        mover.do_it(self, to_track=[], check_triggers=True)
        self.is_tracking_history = prev_tracking  # reset tracking

    # -------------------------------------------------------------------------

    def pass_turn(self) -> GameState:
        self.phase = Times.Phase(0)
        self.active_player_index = ((self.active_player_index + 1)
                                    % len(self.player_list))
        self.priority_player_index: int = self.active_player_index
        self.active.turn_count += 1
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
        # add tracker message, if applicable
        if self.is_tracking_history:
            message = "Pass>>Player%i Turn%i" % (self.active_player_index,
                                                 self.active.turn_count)
            if "\n>>" not in self.events_since_previous:
                message = "\n>>" + message
            self.events_since_previous += message
        return self

    def can_safely_skip_this_phase(self) -> bool:
        """
        If no player wants to take any unilateral actions in this
        phase, and there are no timed abilities to condition, and
        there is nothing currently on the stack, return True. If
        this phase CANNOT safely be skipped, return False.
        Meant to be called at the start of a phase before anything
        else has been done, but has no way to enforce or check
        that this condition is obeyed.
        """
        # cannot skip if there is stuff to resolve on the stack
        if len(self.stack) > 0 or len(self.super_stack) > 0:
            return False
        # cannot skip if there are triggers



        opts = sum(
            [len(p.get_valid_activations()) + len(p.get_valid_castables())
             for p in self.player_list if p.want_to_act])
        return (opts + len(self.stack)) > 0





    def pass_phase(self) -> GameState:
        """
        Increment the phase to the next phase. If that moves
        the game into the next turn, pass the turn.
        MUTATES SELF. also returns self.
        """
        message = "\n>>"
        if not self.has_options:
            message += "Out of options. "
        # resets stack, mana pools
        self.stack = []
        self.super_stack = []
        for player in self.player_list:
            player.pool = ManaPool("")
        # active player has priority
        self.priority_player_index = self.active_player_index
        # increment the phase counter. if at end, pass turn instead
        if self.phase.value == len(Times.Phase):
            if self.is_tracking_history:
                self.events_since_previous += message
            return self.pass_turn()
        else:
            new_phase = Times.Phase(self.phase.value + 1)
            if self.is_tracking_history:
                message += "%s>>%s" % (self.phase.name, new_phase.name)
                self.events_since_previous += message
            self.phase = new_phase
            return self

    def pass_priority(self) -> List[GameState]:
        """
        The current player with priority has passed priority. Give
        priority to the next player who wants it or pass until all
        players have passed. If everyone has passed, resolve top
        of the stack or move to the next phase.
        MUTATES SELF. also returns list of new gamestate(s).
        """
        index = self.priority_player_index + 1
        self.priority_player_index = index % len(self.player_list)
        # if there is a stack, increment the priority counter until either we
        # find a player who wants to respond OR we reach the controller of the
        # top of the stack (in which case we've passed all around the circle).
        if len(self.stack) > 0:
            stack_controller = self.stack[-1].player_index
            # increment until find controller, or player who wants to respond.
            while (self.priority_player_index != stack_controller
                   and not self.priority.want_to_respond):
                index = self.priority_player_index + 1
                self.priority_player_index = index % len(self.player_list)
            if self.priority_player_index == stack_controller:
                # found controller. everyone passed, so resolve stack.
                return self.resolve_top_of_stack()
            else:
                # a player who wants to respond now has priority. return.
                return [self]
        else:
            # stack is empty. increment the priority counter until either all
            # players have passed in a circle back to the active player, or
            # until we find a player who wants to take an action
            while (self.priority_player_index != self.active_player_index
                   and not self.priority.want_to_act):
                index = self.priority_player_index + 1
                self.priority_player_index = index % len(self.player_list)
            if self.priority_player_index == self.active_player_index:
                # found active player. everyone passed, so go to next phase
                return [self.pass_phase()]
            else:
                # a player who wants to do an action now has priority. return.
                return [self]

    def do_priority_action(self) -> List[GameState]:
        """
        The player with priority chooses a single valid action
        to do and does it. This action can be: cast a spell,
        activate an ability, or pass priority. A list of new
        GameStates is returned, one for each chosen action,
        where that action has been performed. The original
        GameState is NOT MUTATED.
        Note that pass_priority may change the phase, if no
        player wants priority within this phase.
        """
        # sometimes the player has already stated that they don't want to act
        # at this point in time. If so, just pass priority immediately
        if len(self.stack) > 0 and not self.priority.want_to_respond:
            return self.copy().pass_priority()
        if len(self.stack) == 0 and not self.priority.want_to_act:
            return self.copy().pass_priority()
        # options are: cast spell; activate ability; pass priority
        activables = self.priority.get_valid_activations()
        castables = self.priority.get_valid_castables()
        opts = activables + castables
        state_list: List[GameState] = []
        for to_do in self.priority.pilot.choose_action_to_take(opts):
            if isinstance(to_do, NullVerb):
                # pass priority
                state_list += self.copy().pass_priority()
            else:
                # player chose an actual action to do. do it!
                if to_do.copies:
                    results = to_do.do_it(self)
                else:
                    new_state, [new_caster] = self.copy_and_track([to_do])
                    results = new_caster.do_it(new_state)
                final_results = []
                for state3, _, _ in results:
                    final_results += state3.clear_super_stack()
                state_list += final_results
        # return final results
        return state_list

    # -------------------------------------------------------------------------

    def step_untap(self):
        """
        Untaps all permaments and adds any triggers to
        the super_stack.  Phase remains UNTAP_UPKEEP.
        MUTATES.
        """
        assert self.phase == Times.Phase.UNTAP_UPKEEP
        self.priority_player_index = self.active_player_index
        was_tracking = self.is_tracking_history
        if self.is_tracking_history:
            turn = self.active.turn_count
            ii = self.active_player_index
            text = "\nUntap step: Player%i Turn%i" % (turn, ii)
            self.events_since_previous += text
        # temporarily turn off tracking for these Untaps
        self.is_tracking_history = False
        for card in self.active.field[:]:  # Untap sorts field, so copy list
            untapper = Untap().populate_options(self, self.active_player_index,
                                                card, None)[0]
            untapper.do_it(self, check_triggers=True)
            card.summon_sick = False
        self.is_tracking_history = was_tracking  # reset tracking to how it was

    def step_upkeep(self):
        """
        Puts any upkeep triggers on the super_stack. The phase
        remains "upkeep".
        MUTATES.
        """
        assert self.phase == Times.Phase.UNTAP_UPKEEP
        self.priority_player_index = self.active_player_index
        if self.is_tracking_history:
            self.events_since_previous += "\nUpkeep step"
        # adds timed abilities to super_stack, if time & conditions are right
        for ab_holder in self.trig_timed:
            ab_holder.apply_if_applicable(self)

    def step_draw(self):
        """
        Draws a card for turn and puts any triggers on the
        super_stack. The phase remains "draw". MUTATES.
        """
        assert self.phase == Times.Phase.DRAW
        self.priority_player_index = self.active_player_index
        was_tracking = self.is_tracking_history
        if self.is_tracking_history:
            self.events_since_previous += "\nDraw step"
        # temporarily turn off tracking for this Draw
        self.is_tracking_history = False
        [drawer] = DrawCard().populate_options(self, self.active_player_index,
                                               CardNull(), None)
        drawer.do_it(self)
        self.is_tracking_history = was_tracking  # reset tracking to how it was
        # adds timed abilities to super_stack, if time & conditions are right
        for ab_holder in self.trig_timed:
            ab_holder.apply_if_applicable(self)

    def step_attack(self):
        """Handles the whole combat phase. Phase remains attack.
        MUTATES."""
        assert self.phase == Times.Phase.COMBAT
        self.priority_player_index = self.active_player_index
        if self.is_tracking_history:
            self.events_since_previous += "\nGo to combat"
        # adds timed abilities to super_stack, if time & conditions are right
        for ab_holder in self.trig_timed:
            ab_holder.apply_if_applicable(self)
        # get a list of all possible attackers
        # player = self.active_player_index
        # field = Zone.Field(player).get(self)
        # for card in field:
        #     RulesText.DeclareAttacker().on()
        print("Combat not yet implemented. instead, skip combat.")

    def step_endstep(self):
        """
        Puts any endstep triggers on the super_stack. The phase
        remains "endstep".
        MUTATES.
        """
        assert self.phase == Times.Phase.ENDSTEP
        self.priority_player_index = self.active_player_index
        if self.is_tracking_history:
            self.events_since_previous += "\nEnd step"
        # adds timed abilities to super_stack, if time & conditions are right
        for ab_holder in self.trig_timed:
            ab_holder.apply_if_applicable(self)

    def step_cleanup(self) -> List[GameState]:
        """
        Does cleanup:
        - if there are items on the stack, players can respond.
        - if active player has too many cards in hand, discard.
        Recurses until the stack is empty and the active player
        has few enough cards in hand. Then passes the turn, so
        the returned states are in the Upkeep phase of the next
        player's next turn.
        DOES NOT MUTATE SELF. Returns new GameStates instead.
        """
        assert self.phase == Times.Phase.CLEANUP
        if len(self.stack) > 0:
            game_list = []
            for g in self.do_priority_action():
                if g.phase == Times.Phase.CLEANUP:
                    game_list += g.step_cleanup()
                else:
                    game_list.append(g)
        elif len(self.active.hand) > 7:
            # discard down to 7 cards
            choose_which = Get.Chooser(Match2.Anything(),
                                       num_to_choose=len(self.active.hand) - 7,
                                       can_be_fewer=False)
            get_from_hand = Get.CardListFrom(Zone.Hand(
                self.active_player_index))
            discarder = Verbs.DiscardCard().on(subject_chooser=choose_which,
                                               option_getter=get_from_hand,
                                               allowed_to_fail=False)
            vlist = discarder.populate_options(self, self.active_player_index,
                                               None, None)
            tuple_list = []
            for verb_to_do in vlist:
                if verb_to_do.copies:
                    tuple_list += verb_to_do.do_it(self, check_triggers=True)
                else:
                    state2, [new_verb] = self.copy_and_track([verb_to_do])
                    tuple_list += new_verb.do_it(state2, check_triggers=True)
            game_list = []
            for state3, _, _ in tuple_list:
                for g in state3.clear_super_stack():
                    game_list += g.step_cleanup()
            return game_list
        else:
            return [self.copy().pass_turn()]

    # -------------------------------------------------------------------------

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
        new_state = self.copy()
        # remove StackObject from the stack
        obj = new_state.pop_from_stack(-1)
        if obj.do_effect is None:
            results = [(new_state, None, [obj])]
        else:
            # perform the effect (resolve ability, perform spell, etc).
            results = obj.do_effect.do_it(new_state, to_track=[obj])
        # if card is on stack (not just a pointer), move it to destination zone
        if (isinstance(obj.obj, Cardboard)
                and isinstance(obj.obj.zone, Zone.Stack)):
            dest = obj.obj.rules_text.cast_destination.copy()
            dest.player = obj.player_index  # update to give to correct player
            for state, verb, track in results:
                MoveToZone.move(state, track[0].obj, dest, check_triggers=True)
        # clear the superstack and return!
        final_results: List[GameState] = []
        for tup in results:
            # active player recieves priority. Rule 117.3b
            tup[0].priority_player_index = tup[0].active_player_index
            final_results += tup[0].clear_super_stack()
        return final_results

    def clear_super_stack(self) -> List[GameState]:
        """Returns a list of GameStates where the caster in the
        super_stack have been run to put their StackObjects on
        the stack. Each GameState describes casting them in a
        different possible order. For all returned GameStates,
        the list of triggers to remove have been removed.
        If super_stack is empty, returns [self].
        DOES NOT MUTATE, unless explicitly told it is allowed to.
        """
        # if there are triggered abilities to remove from the tracking list,
        # remove them. Just clear the "remove" list and recurse.
        if len(self.trigs_to_remove) + len(self.statics_to_remove) > 0:
            new_state = self.copy()
            new_state.trigs_to_remove = []
            new_state.statics_to_remove = []
            return new_state.clear_super_stack()  # recurse
        # base case: no items on super_stack
        if len(self.super_stack) == 0:
            return [self]
        # trivial case: one item on super_stack
        elif len(self.super_stack) == 1:
            state2 = self.copy()
            caster2 = state2.super_stack.pop()  # verb to add it to stack
            # put onto the stack of copies of state2. doesn't mutate state2
            if caster2.can_be_done(state2):
                # just want gamestates, don't care about verb or tracklist
                on_stack = [t[0] for t in caster2.do_it(state2)]
                return [state2] if len(on_stack) == 0 else on_stack
            else:
                # If can't resolve ability, still return a GameState where it
                # was removed from the stack. e.g. invalid targets still
                # removes the trigger from the super_stack.
                return [state2]
        # if reached here, have multiple items on stack. the hard part.
        results: List[GameState] = []
        # active player puts their triggers onto the stack first. So, find the
        # first player in player-order who has a caster on the super_stack.
        player = self.active_player_index
        theirs = [(ii, caster)
                  for (ii, caster) in enumerate(self.super_stack)
                  if caster.player == player]
        while len(theirs) == 0:
            player = player + 1 % len(self.player_list)
            theirs = [(ii, caster)
                      for (ii, caster) in enumerate(self.super_stack)
                      if caster.player == player]
            # only back to active player if super_stack==[]. breaks base case.
            assert player != self.active_player_index
        # pick a super_stack caster to cast first.
        decider = self.player_list[player].pilot
        for ii, v in decider.choose_exactly_one(theirs, "Put on stack"):
            state3 = self.copy()
            caster2 = state3.super_stack.pop(ii)  # verb to add it to stack
            # put onto the stack of copies of state2. doesn't mutate state2
            if caster2.can_be_done(state3):
                # just want gamestates, don't care about verb or tracklist
                on_stack = [t[0] for t in caster2.do_it(state3)]
                if len(on_stack) == 0:  # see note re failing to resolve
                    results.append(state3)
                else:
                    results += on_stack
            else:
                # If can't resolve ability, still return a GameState where it
                # was removed from the stack. e.g. invalid targets still
                # removes the trigger from the super_stack.
                results.append(state3)
        # recurse
        final_results = []
        for state in results:
            final_results += state.clear_super_stack()
        return final_results

    def state_based_actions(self):
        """MUTATES. Performs any state-based actions such as killing
        creatures with toughness less than 0.
        If anything triggers as a result of carrying out these
        state-based actions, this function adds them to the
        super-stack.
        See rule 704.5:
        -   players with 0 or less life lose the game (I check in
            the Verb instead)
        -   players who drew from empty decks lose the game (I check
            in the Verb instead)
        -   poison (poison not implemented)
        -   tokens disappear (tokens not yet implemented)
        -   creatures with toughness less than 0 die
        -   creatures die from lethal damage (damage not yet implemented)
        -   legend rule (not yet implemented)
        -   +1/+1 and -1/-1 counters anihilate (not yet implemented)
        """
        # remove any stale triggers or abilities the GameState is tracking
        self.trig_event = [h for h in self.trig_event if h.should_keep(self)]
        self.trig_timed = [h for h in self.trig_timed if h.should_keep(self)]
        self.statics = [h for h in self.statics if h.should_keep(self)]
        self.trigs_to_remove = []
        self.statics_to_remove = []
        # check all creatures each player controls
        for player in self.player_list:
            i = 0
            while i < len(player.field):
                card = player.field[i]
                toughness = Get.Toughness().get(self, player.player_index,
                                                card)
                if toughness is not None and toughness <= 0:
                    MoveToZone.move(self, card, Zone.Grave(card.player_index),
                                    check_triggers=True)
                    continue  # don't increment counter
                i += 1
            # legend rule   # TODO
            # Sacrifice().do_it(self, player.player_index, card)
        return self


# ---------------------------------------------------------------------------


class Player:
    def __init__(self, state: GameState,
                 pilot: Pilots.Pilot = Pilots.BotTriesAll()):
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
        # The following fields are NOT included in get_id
        # how the player makes decisions. ["try_all", "try_one", or "manual"]
        self.pilot: Pilots.Pilot = pilot

    @property
    def is_my_turn(self):
        return self.player_index == self.gamestate.active_player_index

    @property
    def is_my_priority(self):
        return self.player_index == self.gamestate.priority_player_index

    @property
    def land_drops_left(self):
        return 1 - self.num_lands_played

    @property
    def want_to_respond(self) -> bool:
        """Return whether this player wants to respond to things
        being put onto the stack during this phase and turn, or
        whether this player just wants to auto-pass."""
        assert self.is_my_priority
        if self.is_my_turn:
            return self.pilot.respond_in_my_phase[self.gamestate.phase.value]
        else:
            return self.pilot.respond_in_opp_phase[self.gamestate.phase.value]

    @property
    def want_to_act(self) -> bool:
        """Return whether this player wants to put things onto
        the stack during this phase and turn, or whether this
        player just wants to auto-pass."""
        if self.is_my_turn:
            return self.pilot.act_in_my_phase[self.gamestate.phase]
        else:
            return self.pilot.act_in_opp_phase[self.gamestate.phase]

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
            txt += "\n  HAND:  " + ",".join([str(card) for card in self.hand])
        if len(self.field) > 0:
            txt += "\n  FIELD: " + ",".join([str(card) for card in self.field])
        if len(self.grave) > 0:
            txt += "\n  GRAVE: " + ",".join([str(card) for card in self.grave])
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
        new_player = Player(new_state, self.pilot)
        # copy the ints by value
        new_player.turn_count = self.turn_count
        new_player.life = self.life
        new_player.num_lands_played = self.num_lands_played
        new_player.num_spells_cast = self.num_spells_cast
        # copy mana pool
        new_player.pool = self.pool.copy()
        # for the lists of Cardboards (hand, deck, field, grave), spin
        # through making copies as I go. The ordering will be maintained. Note
        # this doesn't supply a GameState to copy() because there should be
        # no pointers within any of these zones. they're real Cardboards.
        new_player.hand = [c.copy() for c in self.hand]
        new_player.deck = [c.copy() for c in self.deck]
        new_player.field = [c.copy() for c in self.field]
        new_player.grave = [c.copy() for c in self.grave]
        return new_player

    def get_valid_activations(self, hide_equivalent=True
                              ) -> List[Verbs.UniversalCaster]:
        """
        Find all abilities that can be activated and put on the
        stack right now. Return them as a list of PlayAbility
        Verbs, each of which will let the user choose payments
        and targets for that ability and put it onto the stack.
        """
        activatables: List[Verbs.PlayAbility] = []
        active_objects: List[Cardboard] = []  # I already checked these cards
        game = self.gamestate
        # temporarily set decision_maker to be "try_all", to see if ANY method
        # of casting this card will work.
        old_pilot = self.pilot
        self.pilot = Pilots.BotTriesAll()
        for source in self.hand + self.field + self.grave:
            if (any([source.is_equiv_to(ob) for ob in active_objects])
                    and hide_equivalent):
                continue  # skip cards equivalent to those already searched
            add_object = False
            for ability in source.get_activated():
                caster = ability.valid_caster(game, self.player_index, source)
                if caster is not None:
                    add_object = True
                    activatables.append(caster)
            # track object to not look at any similar again.
            if add_object and hide_equivalent:
                active_objects.append(source)
        self.pilot = old_pilot  # reset pilot
        return activatables

    def get_valid_castables(self, hide_equivalent=True
                            ) -> List[Verbs.UniversalCaster]:
        """
        Find all cast-able cards that can be put on the stack
        right now. Return them as a list of PlayCardboard Verbs,
        each of which will let the user choose payments and
        targets for that card and put it onto the stack.
        """
        castables: List[Verbs.PlayCardboard] = []
        active_objects: List[Cardboard] = []
        game = self.gamestate
        # temporarily set pilot to be "try_all", to see if ANY method
        # of casting this card will work.
        old_pilot = self.pilot
        self.pilot = Pilots.BotTriesAll()
        for card in self.hand:
            # skip cards equivalent to those
            # already searched
            if (any([card.is_equiv_to(ob) for ob in active_objects])
                    and hide_equivalent):
                continue
            # check if this card can be cast.
            caster = card.valid_caster(game)
            if caster is not None:
                active_objects.append(card)
                castables.append(caster)
        self.pilot = old_pilot  # reset pilot
        return castables

    # -----------

    def add_to_hand(self, card: Cardboard):
        """Maintains that Hand is sorted and tracks Zone.location."""
        card.zone = Zone.Hand(self.player_index)
        self.hand.append(card)
        self.re_sort_hand()

    def remove_from_hand(self, card: Cardboard):
        """
        Removes card from Hand and adds it to Unknown zone.
        Maintains that Hand is sorted and tracks Zone.location.
        """
        index = card.zone.location
        self.hand.pop(index)
        card.zone = Zone.Unknown()
        # order didn't change, so no need to re-sort. just fix indexing.
        for ii in range(index, len(self.hand)):
            self.hand[ii].zone.location = ii

    def re_sort_hand(self):
        self.hand.sort(key=Cardboard.get_id)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(len(self.hand)):
            self.hand[ii].zone.location = ii

    def add_to_field(self, card: Cardboard):
        """Maintains that Field is sorted and tracks Zone.location."""
        card.zone = Zone.Field(self.player_index)
        self.field.append(card)
        self.re_sort_field()
        # add mechanism to sense triggers from cards in play
        # noinspection PyTypeChecker
        for ability in (card.rules_text.trig_verb + card.rules_text.trig_timed
                        + card.rules_text.static):
            ability.add_to_tracker(self.gamestate, card)


    def remove_from_field(self, card: Cardboard):
        """
        Removes card from field and adds it to Unknown zone.
        Maintains that Field is sorted and tracks Zone.location.
        """
        index = card.zone.location
        self.field.pop(index)
        card.zone = Zone.Unknown()
        # order didn't change, so no need to re-sort. just fix indexing.
        for ii in range(index, len(self.field)):
            self.field[ii].zone.location = ii
        # remove mechanism for sensing triggers from this card
        # TODO: remove as unecessary? state_based_actions already does this
        state = self.gamestate  # for brevity
        state.trigs_to_remove += [h for h in state.trig_event
                                  if not h.should_keep(state)]
        state.trig_event = [h for h in state.trig_event
                            if h.should_keep(state)]
        state.trig_timed = [h for h in state.trig_timed
                            if h.should_keep(state)]
        state.statics_to_remove += [h for h in state.statics
                                    if not h.should_keep(state)]
        state.statics = [h for h in state.statics if h.should_keep(state)]

    def re_sort_field(self):
        self.field.sort(key=Cardboard.get_id)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(len(self.field)):
            self.field[ii].zone.location = ii

    def add_to_grave(self, card: Cardboard):
        """Maintains that Grave is sorted and tracks Zone.location."""
        card.zone = Zone.Grave(self.player_index)
        self.grave.append(card)
        self.re_sort_grave()

    def remove_from_grave(self, card: Cardboard):
        """
        Removes card from Grave and adds it to Unknown zone.
        Maintains that Grave is sorted and tracks Zone.location.
        """
        index = card.zone.location
        self.grave.pop(index)
        card.zone = Zone.Unknown()
        # order didn't change, so no need to re-sort. just fix indexing.
        for ii in range(index, len(self.grave)):
            self.grave[ii].zone.location = ii

    def re_sort_grave(self):
        self.grave.sort(key=Cardboard.get_id)
        # update zone locations. mutates, so will also affect pointers.
        for ii in range(len(self.grave)):
            self.grave[ii].zone.location = ii

    def add_to_deck(self, card: Cardboard, dist_from_bottom: int):
        """
        Adds card to the deck at the given distance from the bottom
        of the deck. The Deck is not maintained as sorted, but it
        IS maintained to track Zone.location.
        """
        # deck[0] is bottom, deck[-1] is top
        if dist_from_bottom < 0:
            # insert has strange negative indexing. otherwise 0 and -1 would
            # do the same thing. insert at len(list), not len-1, to be at end.
            dist_from_bottom += len(self.deck) + 1
        card.zone = Zone.Deck(self.player_index, dist_from_bottom)
        self.deck.insert(dist_from_bottom, card)
        # order didn't change, but need to fix indexing.
        for ii in range(dist_from_bottom, len(self.deck)):
            self.deck[ii].zone.location = ii

    def remove_from_deck(self, card: Cardboard):
        """
        Removes card from the Deck and adds it to Unknown zone.
        The Deck is not maintained as sorted, but it IS maintained
        to track Zone.location.
        """
        index = card.zone.location
        self.deck.pop(index)
        card.zone = Zone.Unknown()
        # order didn't change, but need to fix indexing.
        for ii in range(index, len(self.deck)):
            self.deck[ii].zone.location = ii
