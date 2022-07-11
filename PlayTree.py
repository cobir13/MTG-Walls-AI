# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:
    import GameState
    from Stack import StackObject


class PlayTree:
    """
    Holds all gamestates that occur over the course of a turn.

    Stores the initial states, the final states, and all intermediate states.
    """

    def __init__(self, start_states: List[GameState], turn_limit: int):
        # NOTE: for all of these sets of GameStates, the super_stack is
        # guaranteed to be empty but the normal stack may have things!

        # Every intermediate GameState that has been reached so far this turn.
        self.all_intermediate: Set[GameState] = set(start_states)
        # set of GameStates that have no more options for the player to take.
        self.final_states: Set[GameState] = set()
        # set of GameStates which have options left to explore to see what
        # new GameStates they will create.
        self.active_states: Set[GameState] = set(start_states)
        # for debugging, track total number of states visited. (This is more
        # than total intermediate states, since some intermediate states are
        # reached multiple times through different sequences of actions
        self.traverse_counter: int = 0
        # hold the tree for the next turn of the game
        self.next_turn: PlayTree | None = None

    def get_turn_n(self):
        return []

    def do_main_phase_for_active(self):
        while len(self.active_states) > 0:
            # remove a random GameState from the active list and explore it
            state = self.active_states.pop()
            # options are: cast spell, activate ability, let stack resolve
            activables: List[StackObject] = state.get_valid_activations()
            castables: List[StackObject] = state.get_valid_castables()
            # if no valid actions, this is a final state
            if len(activables) + len(castables) + len(state.stack) == 0:
                self.final_states.add(state)
                # It is already in allnodes so don't need to add it to there.
                # Just move on to the next GameState in active_states
                continue
            # if there ARE valid actions, make new nodes by taking them
            new_nodes = []
            for stack_obj in activables + castables:
                game_tuple_list = stack_obj.play_onto_stack(state)
                # list of (GameState, source Cardboard, list) tuples.
                for g, _, _ in game_tuple_list:
                    new_nodes += g.clear_super_stack()
            # if there are things on stack, can let them resolve
            if len(state.stack) > 0:
                # list of GameStates with the top effect on the stack resolved
                for g in state.resolve_top_of_stack():
                    new_nodes += g.clear_super_stack()
            # add these new nodes to the PlayTree's tracker
            for new_state in new_nodes:
                self.traverse_counter += 1
                # if state already exists, then we're done with this state
                if new_state not in self.all_intermediate:
                    self.active_states.add(new_state)
                    self.all_intermediate.add(new_state)

    def do_beginning_phase_for_active(self):
        """Apply untap, upkeep, draw to all currently-active
        states, updating the active and intermediate state
        sets as appropriate. This should end with active
        states having empty superstacks but possibly still
        having triggers on the stack. Who knows, maybe the
        player wants a chance to respond to those
        triggers!
        """
        new_nodes = []
        for state in self.active_states:
            state2 = state.copy()
            state2.step_untap()
            state2.step_upkeep()
            state2.step_draw()
            new_nodes += state2.clear_super_stack()
        # The states in new_node may have things on the stack! That's ok.
        # They are the new active_states.
        self.active_states = set(new_nodes)
        self.all_intermediate.update(new_nodes)
        self.traverse_counter += len(new_nodes)

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
