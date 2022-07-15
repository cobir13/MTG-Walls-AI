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
        #       active_states: states which have options (moves to explore)
        #       loss_states: states where the game has ended in a loss
        #       win_states: states where the game has ended in a win
        # The i-th index within the list gives the set of states for the i-th
        # turn of the game.
        # NOTE: for all of these sets of GameStates, the super_stack is
        # guaranteed to be empty. But the normal stack may have things!
        self.turn_limit = turn_limit  # max number of turns this will test
        self.traverse_counter: int = 0  # num states every visited. for debug.
        self.intermediate_states: List[Set[GameState]] = []
        self.active_states: List[Set[GameState]] = []
        self.loss_states: List[Set[GameState]] = []
        self.win_states: List[Set[GameState]] = []
        for state in start_states:
            self._add_state_to_active(state)

    def _add_state_to_tracker(self, tracker: List[Set[GameState]],
                              state: GameState):
        while len(tracker) <= state.turn_count:
            tracker.append(set())
        tracker[state.turn_count].add(state)

    def _add_state_to_active(self, state: GameState):
        # only add if NEW state we haven't seen this turn yet
        if (len(self.intermediate_states) <= state.turn_count
                or state not in self.intermediate_states[state.turn_count]):
            if state.has_options:
                self._add_state_to_tracker(self.active_states, state)
            # also add to intermediate, which tracks ALL states
            self._add_state_to_tracker(self.intermediate_states, state)
        self.traverse_counter += 1  # counter doesn't care if repeats

    def _add_state_to_win(self, state: GameState):
        # only add if NEW state we haven't seen this turn yet
        if (len(self.intermediate_states) < state.turn_count
                or state not in self.intermediate_states[state.turn_count]):
            self._add_state_to_tracker(self.win_states, state)
            # also add to intermediate, which tracks ALL states
            self._add_state_to_tracker(self.intermediate_states, state)
        self.traverse_counter += 1  # counter doesn't care if repeats

    def _add_state_to_loss(self, state: GameState):
        # only add if NEW state we haven't seen this turn yet
        if (len(self.intermediate_states) < state.turn_count
                or state not in self.intermediate_states[state.turn_count]):
            self._add_state_to_tracker(self.loss_states, state)
            # also add to intermediate, which tracks ALL states
            self._add_state_to_tracker(self.intermediate_states, state)
        self.traverse_counter += 1  # counter doesn't care if repeats

    def main_phase_for_all_active_states(self, turn=-1):
        """DOES NOT MUTATE"""
        while len(self.get_active(turn)) > 0:
            # remove a random GameState from the active list and explore it
            state: GameState = self.get_active(turn).pop()
            # options are: cast spell, activate ability, let stack resolve
            activables = state.get_valid_activations()
            castables = state.get_valid_castables()
            # if there are valid actions, make new nodes by taking them
            # TODO: win and loss conditions here?
            new_nodes = []
            for ability, source, choice_list in activables:
                for game in ability.activate(state, source, choice_list):
                    new_nodes += game.clear_super_stack()
            for card, choice_list in castables:
                for game in card.cast(state, choice_list):
                    new_nodes += game.clear_super_stack()
            if len(state.stack) > 0:
                # list of GameStates with the top effect on the stack resolved
                for game in state.resolve_top_of_stack():
                    new_nodes += game.clear_super_stack()
            # add these new nodes to the trackers
            for new_state in new_nodes:
                self._add_state_to_active(new_state)  # only adds if truly new

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
            self._add_state_to_active(new_state)  # only adds if truly new

    def get_states_no_stack(self, turn: int = -1) -> List[GameState]:
        return [gs for gs in self.get_intermediate(turn) if len(gs.stack) == 0]

    def get_states_no_options(self, turn: int = -1) -> List[GameState]:
        return [gs for gs in self.get_intermediate(turn) if not gs.has_options]

    def get_intermediate(self, turn: int = -1) -> Set[GameState]:
        """Returns the set of intermediate states for the
        specified turn. If turn is -1, gets the states from
        the latest turn instead."""
        return self.intermediate_states[turn]

    def get_active(self, turn: int = -1) -> Set[GameState]:
        """Returns the set of active states for the
        specified turn. If turn is -1, gets the states from
        the latest turn instead."""
        return self.active_states[turn]

    # def PrintLatest(self):
    #     finalnodes = self.LatestNodes()
    #     if len(finalnodes) == 0:
    #         print("\n-------start of upkeep of turn %i----------" % (
    #             len(self.trackerlist)))
    #         for node in self.LatestTracker().activenodes:
    #             print(node)
    #             print("-----------------")
    #     else:
    #         print(
    #             "\n-------end of turn %i----------" % (len(self.tracklist)))
    #         for node in finalnodes:
    #             print(node)
    #             print("-----------------")

    # def GetFinal(self):
    #     """Return a list of final nodes. Uses a fancier version
    #     of equivalency, where nodes are equal if their states
    #     would be equal IF THEY WERE UNTAPPED. They aren't
    #     actually untapped yet, this just checks ahead."""
    #
    #     class FancyNode():
    #         def __init__(self, node):
    #             self.node = node
    #
    #         def __eq__(self, other):
    #             untapped = self.node.state.copy()
    #             untapped.step_untap()
    #             untapped_other = other.node.state.copy()
    #             untapped_other.step_untap()
    #             return untapped == untapped_other  # usual GameState _eq_
    #
    #         def __hash__(self):
    #             untapped = self.node.state.copy()
    #             untapped.step_untap()
    #             return untapped.__hash__()
    #
    #     fancyset = set()
    #     for node in self.finalnodes:
    #         fancyset.add(FancyNode(node))
    #     return [fn.node for fn in fancyset]
    #
    # def GetAll(self):
    #     """Return a list of all nodes. Uses a fancier version of equivalency,
    #     where nodes are equal if their states would be equal WHEN WE UNTAP
    #     NEXT TURN. They aren't actually untapped yet, this just checks ahead.
    #     I can use this if I want to permit the AI to "stop early" before
    #     exhausting all possible moves."""
    #
    #     class FancyNode():
    #         def __init__(self, node):
    #             self.node = node
    #
    #         def __eq__(self, other):
    #             untapped = self.node.state.copy()
    #             untapped.step_untap()
    #             untapped_other = other.node.state.copy()
    #             untapped_other.step_untap()
    #             return untapped == untapped_other  # usual GameState _eq_
    #
    #         def __hash__(self):
    #             untapped = self.node.state.copy()
    #             untapped.step_untap()
    #             return untapped.__hash__()
    #
    #     fancyset = set()
    #     for node in self.allnodes:
    #         fancyset.add(FancyNode(node))
    #     # return the not-yet-untapped nodes, but only those with empty stacks
    #     return [fn.node for fn in fancyset if len(fn.node.state.stack) == 0]
