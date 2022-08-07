# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set
if TYPE_CHECKING:
    import GameState


class PlayTree:
    """
    Holds all gamestates that occur over the course of a game.
    Stores the initial states, the final states, and all intermediate states.
    """

    def __init__(self, start_states: List[GameState], turn_limit: int):
        # Internal structure: indexed lists of sets. Each set represents
        # GameStates from the same turn of the game (so identical turnclocks).
        # There are four lists:
        #       intermediate_states: every state reached during the turn
        #       _active_states: states which have _options (moves to explore)
        #       game_over_states: states where the game has ended in a loss
        #       _out_of_option_states: states where the game has ended in a win
        # The i-th index within the list gives the set of states for the i-th
        # total turn of the game (sum of turns that any player has taken).
        # NOTE: for all of these sets of GameStates, the super_stack is
        # guaranteed to be empty. But the normal stack may have things!
        self.turn_limit = turn_limit  # max number of turns this will test
        self.traverse_counter: int = 0  # num states every visited. for debug.
        self._intermediate_states: List[Set[GameState]] = []
        self._active_states: List[Set[GameState]] = []
        self._out_of_option_states: List[Set[GameState]] = []
        self._game_over_states: List[Set[GameState]] = []
        for state in start_states:
            self._add_state_to_trackers(state)

    def _add_state_to_trackers(self, state: GameState):
        # only add if NEW state. If we've seen it this turn, don't track.
        if (len(self._intermediate_states) <= state.total_turns
                or state not in self._intermediate_states[state.total_turns]):
            # make sure trackers have enough slots. all are same length.
            while len(self._intermediate_states) <= state.total_turns:
                self._intermediate_states.append(set())
                self._active_states.append(set())
                self._out_of_option_states.append(set())
                self._game_over_states.append(set())
            if state.game_over:
                self._game_over_states[state.total_turns].add(state)
            elif state.has_options:
                self._active_states[state.total_turns].add(state)
            else:
                self._out_of_option_states[state.total_turns].add(state)
            # always add to intermediate, which tracks ALL states
            self._intermediate_states[state.total_turns].add(state)
        self.traverse_counter += 1  # counter doesn't care if repeats

    def main_phase_for_all_active_states(self, turn=-1):
        """DOES NOT MUTATE"""
        while len(self._active_states[turn]) > 0:
            # remove a random GameState from the active list and explore it
            state: GameState = self._active_states[turn].pop()
            # _options are: cast spell, activate ability, let stack resolve
            activables = state.priority.get_valid_activations()
            castables = state.priority.get_valid_castables()
            # if there are valid actions, make new nodes by taking them
            # TODO: win and loss conditions here?
            new_nodes = []
            for stack_object in activables + castables:
                for state2 in stack_object.put_on_stack(state):
                    new_nodes += state2.clear_super_stack()
            if len(state.stack) > 0:
                # list of GameStates with the top effect on the stack resolved
                for state2 in state.resolve_top_of_stack():
                    new_nodes += state2.clear_super_stack()
            # add these new nodes to the trackers
            for new_state in new_nodes:
                self._add_state_to_trackers(new_state)

    def beginning_phase_for_all_valid_states(self, turn=-1):
        """Apply untap, upkeep, draw to all intermediate states
        which are legal stopping points -- have empty stacks.
        This will result in new states being added to the active
        states list for the next turn, since untap step
        increments the turn counter.
        DOES NOT MUTATE EXISTING STATES"""
        new_nodes = []
        for state in self.get_states_no_stack(turn):
            state2 = state.copy()
            state2.step_untap()
            state2.step_upkeep()
            state2.step_draw()
            new_nodes += state2.clear_super_stack()
        # The states in new_node may have things on the stack! That's ok.
        # They are the new active_states.
        for new_state in new_nodes:
            self._add_state_to_trackers(new_state)

    def get_states_no_stack(self, turn: int = -1) -> List[GameState]:
        return [gs for gs in self.get_intermediate(turn) if len(gs.stack) == 0]

    def get_states_no_options(self, turn: int = -1) -> List[GameState]:
        return list(self._out_of_option_states[turn])

    def get_intermediate(self, turn: int = -1) -> List[GameState]:
        """Returns the set of intermediate states for the
        specified turn. If turn is -1, gets the states from
        the latest turn instead."""
        return list(self._intermediate_states[turn])

    def get_active(self, turn: int = -1) -> List[GameState]:
        """Returns the set of active states for the
        specified turn. If turn is -1, gets the states from
        the latest turn instead."""
        return list(self._active_states[turn])

    def get_finished(self, turn: int = -1) -> List[GameState]:
        """Returns the set of active states for the
        specified turn. If turn is -1, gets the states from
        the latest turn instead."""
        return list(self._game_over_states[turn])
