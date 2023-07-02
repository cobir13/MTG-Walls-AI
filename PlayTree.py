# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, Set

import Times
from GameState import GameState
from Times import Phase


class PlayTree:
    """
    Holds all gamestates that occur over the course of a game.
    Stores the initial states, the final states, and all intermediate states.
    """

    def __init__(self, start_states: List[GameState], turn_limit: int):
        """
        The structures to hold historical GameStates are:
              _active_states:
                  list (turn of game) of list (phase of game) of list of
                  states which still need to be processed for that phase.
                  By "processed" I mean that THE STATE IS IN THE BEGINNING
                  OF THE GIVEN PHASE AND THE PHASE STILL NEEDS TO BE
                  PERFORMED ON IT. Note that PlayTree does not clear these
                  states, but rather leaves them as a history marker. Thus,
                  these states should be copied rather than mutated.
                  Indexed as _active_states[turn][phase][index].
                  Superstack and normal stack must both be empty.
              _out_of_option_states:
                  list (turn of game) of list of states where the game has
                  no more valid option this turn. Indexed as
                  _out_of_option_states[turn][index].
                  Superstack and normal stack must both be empty.
              _game_over_states:
                  list (turn of game) of list of states where the game has
                  ended. Indexed as _game_over_states[turn][index].
                  Superstack and normal stack may not be empty.
        """
        self.turn_limit = turn_limit  # max number of turns this will test
        self._active_states: List[List[List[GameState]]] = []
        # self._out_of_option_states: List[List[GameState]] = []
        self._game_over_states: List[List[GameState]] = []
        # prep the start states. if turn 0, advance to turn 1 as untap
        for state in start_states:
            if state.total_turns == 0:
                state = state.copy()
                state.active_player_index -= 1  # so pass_turn won't change it.
                state.pass_turn()
            self.track_this_state(state)

    def track_this_state(self, state: GameState):
        if len(self._active_states) <= state.total_turns:
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

    def process_states_in_phase(self, phase: Phase, turn: int = -1):
        """
        Copies all states from the given turn and phase and plays them
        out until the players pass to the next phase.
        """
        # all intermediate states, to avoid repeating work
        intermeds: Set[GameState] = set()
        # all states still in this phase that still need to be processed.
        in_progress: List[GameState] = []
        for s in self._active_states[turn][phase]:
            # instantiate by doing any automatic phase actions
            in_progress += Times.do_special_phase_thing(s)
        while len(in_progress) > 0:
            # remove a GameState from the in-progress list and explore it
            state4: GameState = in_progress.pop()
            if state4.phase != phase or state4.game_over:
                # new phase and/or game is over, so done processing this state
                self.track_this_state(state4)
            else:
                # give priority player a chance to act, then process again
                new_sts = state4.do_priority_action()
                in_progress.extend([s for s in new_sts if s not in intermeds])
                intermeds.update(new_sts)

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
            self.track_this_state(state2)
        # run endstep phase
        self.phase_cleanup()

    def beginning_phases(self):
        """Untap, upkeep, draw, and move to main phase.
        DOES NOT MUTATE EXISTING STATES"""
        self.phase_untap()
        self.phase_upkeep()
        self.phase_draw()

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
