# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, Set

from GameState import GameState
from Times import Phase


class PlayTree:
    """
    Holds all gamestates that occur over the course of a game.
    Stores the initial states, the final states, and all intermediate states.
    """

    def __init__(self, start_states: List[GameState], turn_limit: int):
        # The structures to hold historical GameStates are:
        #       _intermediate_states:
        #           set of all intermediate states that have ever been
        #           reached. Set uses ID to make hash, and ID incorporates
        #           turn and phase, so two identical board situations from
        #           different phases will register as separate. This is used
        #           to confirm whether a GameState has been seen already or
        #           not. If we've already visisted a GameState, then we're
        #           already tracking it SOMEWHERE and don't need to do any
        #           further work with it.
        #           Thus, the other lists can be lists rather than sets, to
        #           save on computation time and memory.
        #       _active_states:
        #           list (turn of game) of list (phase of game) of list of
        #           states which still need to be processed for that phase.
        #           By "processed" I mean that THE STATE IS IN THE BEGINNING
        #           OF THE GIVEN PHASE AND THE PHASE STILL NEEDS TO BE
        #           PERFORMED ON IT. Note that PlayTree does not clear these
        #           states, but rather leaves them as a history marker.
        #           Indexed as _active_states[turn][phase][index].
        #       _out_of_option_states:
        #           list (turn of game) of list of states where the game has
        #           no more valid option this turn. Indexed as
        #           _out_of_option_states[turn][index].
        #       _game_over_states:
        #           list (turn of game) of list of states where the game has
        #           ended. Indexed as _game_over_states[turn][index].
        # NOTE: for all of these lists of GameStates, the super_stack is
        # guaranteed to be empty. But the normal stack may have things.
        self.turn_limit = turn_limit  # max number of turns this will test
        self._intermediate_states: Set[GameState] = set()
        self._active_states: List[List[List[GameState]]] = []
        # self._out_of_option_states: List[List[GameState]] = []
        self._game_over_states: List[List[GameState]] = []
        # prep the start states. if turn 0, advance to turn 1 as untap
        for state in start_states:
            if state.total_turns == 0:
                state = state.copy()
                state.active_player_index -= 1  # so pass_turn won't change it.
                state.pass_turn()
            self._add_state_to_trackers(state)

    def _add_state_to_trackers(self, state: GameState):
        # only add if NEW state. If already in intermediate, don't track.
        if (len(self._intermediate_states) <= state.total_turns
                or state not in self._intermediate_states):
            # make sure trackers have enough slots. all are same length.
            while len(self._active_states) <= state.total_turns:
                # for _active_states, need one sub-list per phase
                self._active_states.append([[] for _ in Phase])
                # self._out_of_option_states.append([])
                self._game_over_states.append([])
            if state.game_over:
                self._game_over_states[state.total_turns].append(state)
            else:
                turn = state.total_turns
                self._active_states[turn][state.phase].append(state)
            # always add to intermediate
            self._intermediate_states.add(state)

    def _whittle_and_respond(self, in_progress: List[GameState],
                             track_set: Set[GameState], phase: Phase):
        """
        Pops GameStates off of the `in_progress` set (mutating
        it). Let the players respond to Triggers or just pass,
        as they choose. Puts the new states into the trackers,
        or back into the set if there is still actions to take.
        Continues until `in_progress` is whittled to nothing.
        """
        while len(in_progress) > 0:
            # remove a GameState from the in-progress list and explore it
            state4: GameState = in_progress.pop()
            if state4.phase != phase or state4.game_over:
                # new phase and/or game is over, so done processing this state
                self._add_state_to_trackers(state4)
            else:
                # give priority player a chance to act, then process again
                to_track = state4.do_priority_action()
                in_progress.extend([s for s in to_track if s not in track_set])
                track_set.update(to_track)


    def phase_untap(self):
        """process the states in the uptap phase of active states
        and moves them to the upkeep phase."""
        for state in self._active_states[-1][Phase.UNTAP]:
            state2 = state.copy()
            state2.step_untap()  # phase becomes upkeep
            for new_state in state2.clear_super_stack():
                self._add_state_to_trackers(new_state)  # adds to upkeep phase

    def phase_upkeep(self):
        """process the states in the uptap phase of active states
        and moves them to the next phase."""
        in_progress: List[GameState] = []
        screener: Set[GameState] = set()
        # add upkeep triggers to stack
        for state in self._active_states[-1][Phase.UPKEEP]:
            state2 = state.copy()
            state2.step_upkeep()  # phase remains upkeep
            to_track = state2.clear_super_stack()
            in_progress.extend([s for s in to_track if s not in screener])
            screener.update(to_track)
        # let the players respond to triggers or just pass, as they choose.
        self._whittle_and_respond(in_progress, screener, Phase.UPKEEP)

    def phase_draw(self):
        """process the states in the draw phase of active states
        and moves them to the next phase."""
        in_progress: List[GameState] = []
        screener: Set[GameState] = set()
        # draw a card and add any triggers to the stack
        for state in self._active_states[-1][Phase.DRAW]:
            state2 = state.copy()
            state2.step_draw()  # phase remains draw step
            to_track = state2.clear_super_stack()
            in_progress.extend([s for s in to_track if s not in screener])
            screener.update(to_track)
        # let the players respond to triggers or just pass, as they choose.
        self._whittle_and_respond(in_progress, screener, Phase.DRAW)

    def phase_main(self, phase=Phase.MAIN1):
        """process the states in the main1 or main2 phase of
        active states and moves them to the next phase."""
        in_progress: List[GameState] = []
        screener: Set[GameState] = set()
        to_track = self._active_states[-1][phase]
        in_progress.extend([s for s in to_track if s not in screener])
        screener.update(to_track)
        # let the players respond to triggers or just pass, as they choose.
        self._whittle_and_respond(in_progress, screener, phase)

    def phase_combat(self):
        # Right now, there's no priority during combat. Players just declare
        # attacks and blocks and then damage happens.
        for state in self._active_states[-1][Phase.COMBAT]:
            state2 = state.copy()
            state2.step_attack()  # phase becomes main2
            for new_state in state2.clear_super_stack():
                self._add_state_to_trackers(new_state)  # add to main2 phase

    def phase_endstep(self):
        """process the states in the endstep phase of active states
        and moves them to the cleanup phase."""
        in_progress: List[GameState] = []
        screener: Set[GameState] = set()
        # add end-step triggers to stack
        for state in self._active_states[-1][Phase.ENDSTEP]:
            state2 = state.copy()
            state2.step_endstep()  # phase remains end step
            to_track = state2.clear_super_stack()
            in_progress.extend([s for s in to_track if s not in screener])
            screener.update(to_track)
        # let the players respond to triggers or just pass, as they choose.
        self._whittle_and_respond(in_progress, screener, Phase.ENDSTEP)

    def phase_cleanup(self, ):
        """process the states in the endstep phase of active states
        and moves them to the cleanup phase."""
        for state in self._active_states[-1][Phase.CLEANUP]:
            for state2 in state.step_cleanup():
                assert state2.phase == 0
                self._add_state_to_trackers(state2)

    def main_phase_then_end(self):
        """Does main phase 1 and then skips directly to do cleanup phase.
        DOES NOT MUTATE EXISTING STATES"""
        self.phase_main()
        # main1 dumps results into combat phase. move to endstep phase instead.
        for state in self._active_states[-1][Phase.COMBAT]:
            state2 = state.copy()
            state2.phase = Phase.CLEANUP
            if state2.is_tracking_history:
                state2.events_since_previous += "\n||skip to cleanup"
            self._add_state_to_trackers(state2)
        # run endstep phase
        self.phase_cleanup()

    def beginning_phases(self):
        """Untap, upkeep, draw, and move to main phase.
        DOES NOT MUTATE EXISTING STATES"""
        self.phase_untap()
        self.phase_upkeep()
        self.phase_draw()

    def get_intermediate(self):
        return list(self._intermediate_states)

    def get_latest_active(self, turn: int | None = None,
                          phase: Phase | int | None = None
                          ) -> List[GameState]:
        """Returns the set of active states for the specified
        turn and phase. If turn is None, gets the states from the
        latest turn instead. If phase is None, gets the states
        from the latest phase with active (not-yet-processed) states.
        """
        if turn is None:
            turn = -1
        turn_list: List[List[GameState]] = self._active_states[turn]
        if phase is None:
            phase_lists = [sub for sub in turn_list if len(sub) > 0]
            if len(phase_lists) == 0:
                return []
            else:
                return phase_lists[-1]
        else:
            return turn_list[phase]

    def get_latest_no_options(self, turn: int | None = None,
                              phase: Phase | int | None = None
                              ) -> List[GameState]:
        """Returns the active states which finished their previous
        phase with the "no more options" flag in their histories.
        If the states are not tracking history, this will always
        return the empty list."""
        # step back through previous gamestates to find the last phase change
        no_options = []
        for g in self.get_latest_active(turn, phase):
            prev = g
            events = prev.events_since_previous
            while prev is not None and ">>" not in events:
                prev = prev.previous_state
                events = prev.events_since_previous
            if prev is not None and ">>Out of options" in events:
                no_options.append(g)
        return no_options


    def get_num_active(self, turn: int):
        turn_list: List[List[GameState]] = self._active_states[turn]
        return [len(sub) for sub in turn_list]


    def get_finished(self, turn: int = -1) -> List[GameState]:
        """Returns the set of active states for the
        specified turn. If turn is -1, gets the states from
        the latest turn instead."""
        return list(self._game_over_states[turn])
