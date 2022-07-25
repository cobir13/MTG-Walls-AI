# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 22:15:57 2020

@author: Cobi
"""
from __future__ import annotations
from typing import Tuple, List

from Abilities import ActivatedAbility
import ZONE
from GameState import GameState
import ManaHandler
import Decklist
from Cardboard import Cardboard
from PlayTree import PlayTree
import Verbs
import Stack
import Costs
import MatchCardPatterns as Match
import time

if __name__ == "__main__":

    def cast_thing(state,
                   tup: Tuple[ActivatedAbility, Cardboard, list] |
                   Tuple[Cardboard, list]
                   ) -> List[GameState]:
        if len(tup) == 3:
            ab, s, ch = tup
            return ab.activate(state, s, ch)
        elif len(tup) == 2:
            c, ch = tup
            return c.cast(state, ch)


    # -----------------------------------------------------------------------

    print("Testing Wall of Roots and basic GameState...")
    start_clock = time.perf_counter()

    game_orig = GameState(1)
    game_orig.is_tracking_history = False  # True
    assert len(game_orig.player_list) == 1
    player = game_orig.player_list[0]
    assert player.gamestate is game_orig
    assert not game_orig.has_options
    assert len(player.get_valid_activations()) == 0
    assert len(player.get_valid_castables()) == 0

    # four copies of Wall of Roots in hand
    for i in range(4):
        game_orig.give_to(Cardboard(Decklist.Roots()), ZONE.HAND)
    assert (len(game_orig.active.hand) == 4)
    assert (len(game_orig.active.field) == 0)

    # make sure the AddMana Verb works properly
    tuple_list = Decklist.Verbs.AddMana("R").do_it(game_orig,
                                                   game_orig.active, [])
    assert len(tuple_list) == 1
    mana_game, _, choices = tuple_list[0]
    assert len(choices) == 0
    assert mana_game.active.pool == ManaHandler.ManaPool("R")
    # because AddMana mutates, returned game IS original game
    assert game_orig.active.pool == ManaHandler.ManaPool("R")
    assert mana_game is game_orig

    # check the abilities of Wall of Roots in hand. it has 1 but can't be used.
    roots = game_orig.active.hand[0]
    assert len(roots.get_activated()) == 1
    roots_abil = roots.get_activated()[0]
    choices = roots_abil.get_activation_options(game_orig, roots)
    assert choices == [[]]  # list of empty list
    assert not roots_abil.can_be_activated(game_orig, roots, [])

    # move a Wall of Roots to field and try again
    game_orig.give_to(game_orig.active.hand[0], ZONE.FIELD)
    assert len(game_orig.active.hand) == 3
    assert len(game_orig.active.field) == 1
    roots = game_orig.active.field[0]
    assert len(roots.get_activated()) == 1
    assert len(roots.counters) == 0  # no counters on it yet
    roots_abil = roots.get_activated()[0]
    choices = roots_abil.get_activation_options(game_orig, roots)
    assert choices == [[]]  # list of empty list
    assert roots_abil.can_be_activated(game_orig, roots, [])

    # make sure the cost can actually be paid
    cost_game = game_orig.copy()
    cost_roots = cost_game.active.field[0]
    assert roots_abil.cost.can_afford(cost_game, cost_roots, [])
    tuple_list = roots_abil.cost.pay_cost(cost_game, cost_roots, [])
    assert len(tuple_list) == 1
    assert cost_game is tuple_list[0][0]  # so output is same as original
    assert len(cost_roots.counters) == 2
    for value in cost_roots.counters:
        assert "-0/-1" == value or "@" in value
    # should no longer be possible to do
    assert not roots_abil.cost.can_afford(cost_game, cost_roots, [])
    assert len(cost_game.active.get_valid_activations()) == 0

    # untap to reset things, then try to activate the ability "properly"
    game_orig.step_untap()
    assert len(game_orig.active.get_valid_activations()) == 1
    game_list = cast_thing(game_orig,
                           game_orig.active.get_valid_activations()[0])
    assert len(game_list) == 1
    activ_game = game_list[0]
    assert activ_game is not game_orig
    new_roots = activ_game.active.field[0]
    assert roots is not new_roots
    assert new_roots.has_type(Decklist.Roots)
    assert len(roots.counters) == 0  # no counters on original
    assert len(new_roots.counters) == 2  # -0/-1 and @used
    assert activ_game.active.pool == ManaHandler.ManaPool("G")
    assert game_orig.active.pool == ManaHandler.ManaPool("")  # orig the same.
    assert len(new_roots.get_activated()) == 1  # still has one ability
    assert len(activ_game.active.get_valid_activations()) == 0

    # try to cast something
    assert len(activ_game.active.get_valid_castables()) == 0  # no mana
    assert activ_game.active.pool == ManaHandler.ManaPool("G")
    copygame = activ_game.copy()
    copygame.active.pool.add_mana("G")  # add mana directly
    # all 3 roots in hand only generate 1 option--to cast Roots
    assert (len(copygame.active.get_valid_castables()) == 1)
    # cast the newly castable spell
    castable = copygame.active.get_valid_castables()[0]
    card = castable[0]
    assert [o is card for o in copygame.active.hand] == [True, False, False]
    [copygame3] = cast_thing(copygame, castable)  # puts it on the stack
    assert (copygame3.active.pool == ManaHandler.ManaPool(""))  # no mana left
    assert (len(copygame3.stack) == 1)  # one spell on the stack
    assert (len(copygame3.active.hand) == 2)  # two cards in hand
    assert (len(copygame3.active.field) == 1)  # one card in play
    # make sure that all the copying worked out correctly
    assert copygame3 is not copygame
    for c in copygame.active.hand:
        assert c is not copygame3.stack[0].card
        for c3 in copygame3.active.hand:
            assert c is not c3
    further_copy = copygame3.copy()
    assert further_copy.stack[0] is not copygame3.stack[0]
    assert further_copy.stack[0].card is not copygame3.stack[0].card

    # resolve the spell from the stack
    [copygame4] = copygame3.resolve_top_of_stack()
    assert (copygame4.active.pool == ManaHandler.ManaPool(""))  # still no mana
    assert (len(copygame4.stack) == 0)  # nothing on the stack
    assert (len(copygame4.active.hand) == 2)  # two cards in hand
    assert (len(copygame4.active.field) == 2)  # two cards in play
    # should be one ability (new Roots) & no castable spells (not enough mana)
    assert (len(copygame4.active.get_valid_activations()) == 1)
    assert (len(copygame4.active.get_valid_castables()) == 0)
    # Stack should be empty, so resolving the stack should be impossible
    assert ([] == copygame4.resolve_top_of_stack())
    # Just to check, original game is still unchanged:
    assert (len(activ_game.active.field) == 1)
    assert (str(activ_game.active.pool) == "G")

    # check that game history is NOT tracking (since tracking is off)
    assert not game_orig.is_tracking_history
    assert game_orig.previous_state is None
    assert game_orig.events_since_previous == ""
    assert not activ_game.is_tracking_history
    assert activ_game.previous_state is None
    assert activ_game.events_since_previous == ""

    # let's do a full copy test, since copying is rather critical
    test_game = GameState()
    caryatid_in_play = Cardboard(Decklist.Caryatid())
    caryatid_in_play.zone = ZONE.FIELD
    test_game.active.field.append(caryatid_in_play)
    roots_on_stack = Cardboard(Decklist.Roots())
    roots_on_stack.zone = ZONE.STACK
    stack_cardboard = Stack.StackCardboard(None, roots_on_stack,
                                           [1, "a", caryatid_in_play])
    test_game.stack.append(stack_cardboard)
    fake_ability = ActivatedAbility("fake", Costs.Cost(), Verbs.NullVerb())
    stack_ability = Stack.StackAbility(fake_ability, caryatid_in_play,
                                       [(stack_cardboard, caryatid_in_play)])
    test_game.stack.append(stack_ability)
    # test game has: caryatid in play, roots on stack pointing at random stuff,
    # and an ability on stack pointing at roots and also random stuff.
    test_copy = test_game.copy()
    assert test_copy == test_game
    assert test_game.stack[0].card.is_equiv_to(test_copy.stack[0].card)
    assert test_game.stack[0].card is not test_copy.stack[0].card
    assert test_game.stack[1].card.is_equiv_to(test_copy.stack[1].card)
    assert test_game.stack[1].card is not test_copy.stack[1].card
    assert test_game.stack[1].card is test_game.active.field[0]
    assert test_copy.stack[1].card is test_copy.active.field[0]
    assert test_copy.stack[1].choices[0][0] is test_copy.stack[0]
    assert test_copy.stack[1].choices[0][1] is test_copy.active.field[0]
    assert test_copy.stack[1].choices[0][1] is not test_game.active.field[0]
    assert test_copy.stack[1].choices[0][1] is test_copy.stack[1].card
    assert test_copy.stack[0].choices[:2] == [1, "a"]

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing Sylvan Caryatid, Untap & Upkeep, GameState history...")
    start_clock = time.perf_counter()

    # add a caryatid to the all-roots game
    carygame1, _ = game_orig.copy_and_track([])
    carygame1.is_tracking_history = True  # start tracking
    carygame1.give_to(Cardboard(Decklist.Caryatid()), ZONE.FIELD)
    # should only see one valid ability to activate, since Caryatid not hasty
    assert (len(carygame1.active.get_valid_activations()) == 1)
    assert (len(carygame1.active.get_valid_castables()) == 0)  # no castables

    # try to untap and upkeep to get rid of summonning sickness
    carygame1.step_untap()
    carygame1.step_upkeep()
    assert len(carygame1.active.get_valid_castables()) == 0  # no castables
    gameN = carygame1
    # noinspection PyTypeChecker
    options: List[tuple] = (gameN.active.get_valid_activations()
                            + gameN.active.get_valid_castables())
    assert len(options) == 2
    # as long as there are things to do, do them! auto-choose 1st option
    while len(options) > 0:
        gameN = cast_thing(gameN, options[0])[0]
        while len(gameN.stack) > 0:
            gameN = gameN.resolve_top_of_stack()[0]
        # noinspection PyTypeChecker
        options = (gameN.active.get_valid_activations()
                   + gameN.active.get_valid_castables())
    # result should be Caryatid and two Roots in play
    assert len(gameN.active.hand) == 2
    assert len(gameN.active.field) == 3
    assert gameN.active.pool == ManaHandler.ManaPool("G")

    # check if the history tracker worked
    historyN = gameN.get_all_history()
    # print(historyN)
    assert historyN.count("*** Activate Roots add G ***") == 2
    assert historyN.count("*** Activate Caryatid add Au ***") == 1
    assert historyN.count("*** Cast Roots ***") == 1
    assert game_orig.get_all_history() == ""

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing PlayTree basic functionality...")
    start_clock = time.perf_counter()

    # build a PlayTree for a game with no deck
    tree1 = PlayTree([carygame1], 5)
    assert carygame1.active.turn_count == 2
    for t in range(2):
        assert len(tree1.get_active(t)) == 0
        assert len(tree1.get_intermediate(t)) == 0
    assert len(tree1.get_active(2)) == 1
    assert len(tree1.get_active()) == 1
    assert len(tree1.get_intermediate(2)) == 1
    assert len(tree1.get_intermediate()) == 1
    # try untap and upkeep
    try:
        tree1.beginning_phase_for_all_valid_states()
        assert False  # SHOULD throw error, because drawing from empty library
    except Verbs.LoseTheGameError:
        assert True

    tree_game = carygame1.copy()
    tree_game.active.turn_count = 1  # to simplify, roll back to earlier turn
    # HAND: Roots, Roots, Roots
    # FIELD: Caryatid, Roots
    # Life: 20 vs 20, Deck: 0, Mana: ()
    tree_game.is_tracking_history = True
    for x in range(5):
        tree_game.give_to(Cardboard(Decklist.Caryatid()), ZONE.DECK)
    tree2 = PlayTree([tree_game], 5)
    assert len(tree2.get_active()) == 1
    assert len(tree2.get_intermediate()) == 1
    # assert len(tree2.final_states) == 0
    assert tree2.traverse_counter == 1
    assert all([len(gs.active.deck) == 5 for gs in tree2.get_active()])
    assert all([len(gs.active.hand) == 3 for gs in tree2.get_active()])

    tree2.beginning_phase_for_all_valid_states()
    assert len(tree2.active_states) == 3  # turns 0, 1, 2
    assert len(tree2.get_active()) == 1
    assert len(tree2.get_active(1)) == 1
    assert len(tree2.get_intermediate()) == 1
    assert len(tree2.get_intermediate(1)) == 1
    # assert len(tree2.final_states) == 0
    assert tree2.traverse_counter == 2
    assert all([len(gs.active.deck) == 4 for gs in tree2.get_active()])
    assert all([len(gs.active.hand) == 4 for gs in tree2.get_active()])
    assert all([len(gs.stack) == 0 for gs in tree2.get_active()])

    # HAND: Roots, Roots, Roots, Caryatid
    # FIELD: Caryatid, Roots
    # Life: 20 vs 20, Deck: [Caryatid]x4, Mana: ()
    tree2.main_phase_for_all_active_states()
    assert len(tree2.get_active()) == 0
    assert len(tree2.get_active(1)) == 1
    # 9 intermediate. They are: after draw. add G 1st. OR add Au 1st. float GA.
    # caryatid on stack. resolve caryatid.
    # OR roots on stack. resolve roots. float G.
    assert len(tree2.get_intermediate()) == 9
    assert len(tree2.get_intermediate(1)) == 1
    assert tree2.traverse_counter == 11  # 9 + 2, no overlaps
    assert (len(tree2.get_states_no_options()) == 2)  # cast roots or caryatid

    # do one more turn
    tree2.beginning_phase_for_all_valid_states()
    # 5 distinct states. 9, minus 2 that had card on stack. Then Cary{T}+G
    # and unused Caryatid are indistinguishable, and same with Roots[-0/-1]+G
    # and Roots[-0/-1]+Cary{T}+GA.  So 9-2-2=5
    assert len(tree2.get_active()) == 5
    tree2.main_phase_for_all_active_states()
    # I never finished turn 1 properly so there are still actives there. sure.
    assert all([len(tree2.get_active(t)) == 0 for t in [0, 2, 3]])
    # These next several are empirical. I didn't theory. Too hard to count.
    assert len(tree2.get_states_no_options()) == 17  # 20
    assert len(tree2.get_states_no_stack()) == 85  # 88
    n = len(tree2.get_intermediate())
    assert n == 123  # empirical. I didn't theory
    id_list = [g.get_id() for g in tree2.get_intermediate()]
    assert n == len(id_list)
    assert n == len(set(id_list))  # making sure set hash is still working

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing basic lands, shock-lands, fetch-lands...")
    start_clock = time.perf_counter()

    # put some basics in hand, make sure they're playable and produce mana
    game = GameState(1)
    game.give_to(Cardboard(Decklist.Forest()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Plains()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Island()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Swamp()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Mountain()), ZONE.HAND)
    assert len(game.active.get_valid_activations()) == 0
    assert len(game.active.get_valid_castables()) == 5
    tree = PlayTree([game], 2)
    tree.main_phase_for_all_active_states()
    assert len(tree.get_states_no_options()) == 5
    collector = set()
    for g in tree.get_states_no_options():
        collector.add((g.active.field[0].name, str(g.active.pool)))
        assert len(g.active.field) == 1
        assert len(g.active.hand) == 4
    assert collector == {("Forest", "G"), ("Plains", "W"), ("Island", "U"),
                         ("Swamp", "B"), ("Mountain", "R")}

    # test a shock land the same way
    game = GameState(1)
    game.give_to(Cardboard(Decklist.Forest()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.HallowedFountain()), ZONE.HAND)
    assert len(game.active.get_valid_activations()) == 0
    assert len(game.active.get_valid_castables()) == 2
    tree = PlayTree([game], 2)
    tree.main_phase_for_all_active_states()
    assert len(tree.get_states_no_options()) == 4
    collector = set()
    for g in tree.get_states_no_options():
        collector.add((g.active.life, str(g.active.pool)))
        assert len(g.active.field) == 1
        assert len(g.active.hand) == 1
        assert g.active.field[0].tapped
    assert collector == {(20, "G"), (20, ""), (18, "U"), (18, "W")}

    # test a fetch land with many valid targets
    game = GameState(1)
    game.give_to(Cardboard(Decklist.Forest()), ZONE.DECK)
    game.give_to(Cardboard(Decklist.Forest()), ZONE.DECK)
    game.give_to(Cardboard(Decklist.Plains()), ZONE.DECK)
    game.give_to(Cardboard(Decklist.Island()), ZONE.DECK)
    game.give_to(Cardboard(Decklist.Swamp()), ZONE.DECK)
    game.give_to(Cardboard(Decklist.HallowedFountain()), ZONE.DECK)
    game.give_to(Cardboard(Decklist.BreedingPool()), ZONE.DECK)
    game.give_to(Cardboard(Decklist.MistyRainforest()), ZONE.HAND)
    assert len(game.active.get_valid_activations()) == 0
    assert len(game.active.get_valid_castables()) == 1  # play fetch
    matcher = Match.CardType(Decklist.Forest) | Match.CardType(Decklist.Island)
    assert len([c for c in game.active.deck if matcher.match(c, game, c)]) == 5

    tree = PlayTree([game], 2)
    tree.main_phase_for_all_active_states()
    # 4 distinct fetchables, but each shock give 3 options (2 colors + tapped).
    # Can also fail to find.
    assert len(tree.get_states_no_options()) == 9
    collector = set()
    ticker = 0
    for g in tree.get_states_no_options():
        collector.add((g.active.life, str(g.active.pool)))
        assert len(g.active.hand) == 0
        assert g.active.grave[0].has_type(Decklist.MistyRainforest)
        assert any([c.name == "Swamp" for c in g.active.deck])  # never swamp
        if len(g.active.field) == 0:
            ticker += 1
            assert len(g.active.deck) == 7
        else:
            assert len(g.active.deck) == 6
            assert g.active.field[0].tapped
    # 2 ways to have (19,"") and (17,"G")
    assert ticker == 1
    assert collector == {(19, "G"), (19, "U"), (19, ""), (17, "U"), (17, "G"),
                         (17, "W")}

    # what about a fetch with no valid targets
    game = GameState(1)
    game.give_to(Cardboard(Decklist.Island()), ZONE.DECK)
    game.give_to(Cardboard(Decklist.Roots()), ZONE.DECK)
    game.give_to(Cardboard(Decklist.Swamp()), ZONE.DECK)
    game.give_to(Cardboard(Decklist.WindsweptHeath()), ZONE.HAND)
    tree = PlayTree([game], 2)
    tree.main_phase_for_all_active_states()
    assert len(tree.get_states_no_options()) == 1
    result = tree.get_states_no_options()[0]
    assert result.active.life == 19
    assert len(result.active.deck) == 3
    assert len(result.active.hand) == 0
    assert len(result.active.grave) == 1

    # what about no deck at all?
    game = GameState(1)
    game.give_to(Cardboard(Decklist.WindsweptHeath()), ZONE.HAND)
    tree = PlayTree([game], 2)
    tree.main_phase_for_all_active_states()
    assert len(tree.get_states_no_options()) == 1
    result = tree.get_states_no_options()[0]
    assert result.active.life == 19
    assert len(result.active.deck) == 0
    assert len(result.active.hand) == 0
    assert len(result.active.grave) == 1
    
    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("""Testing equality of gamestates...""")
    start_clock = time.perf_counter()

    game = GameState(1)
    # field
    game.give_to(Cardboard(Decklist.Plains()), ZONE.FIELD)
    # hand
    game.give_to(Cardboard(Decklist.HallowedFountain()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Forest()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Roots()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Caryatid()), ZONE.HAND)

    # try to copy, make sure equality holds
    cp = game.copy()
    assert cp == game
    assert cp is not game

    # add this forest to one but not the other
    forest = Cardboard(Decklist.Forest())
    game.give_to(forest, ZONE.FIELD)
    assert (game != cp)
    # add a copy of the forst to the other
    forest2 = forest.copy()
    forest2.zone = ZONE.NEW
    cp.give_to(forest2, ZONE.FIELD)
    # Cardboard uses "is" for eq  (or else "in list" breaks)
    assert forest != forest2
    assert forest is not forest2
    assert (game == cp)
    # tap both of these forests for mana
    cp3 = forest.get_activated()[0].activate(game, forest, [])[0]
    assert (game != cp3)
    assert (cp != cp3)
    cp4 = forest2.get_activated()[0].activate(cp, forest2, [])[0]
    assert (game != cp4)
    assert (cp3 == cp4)
    assert (not (cp3 is cp4))

    # can I put these in a set?
    # noinspection PySetFunctionToLiteral
    testset = set([game, cp, cp3])
    assert (len(testset) == 2)
    assert (cp4 in testset)

    # two lands. put into play in opposite order. Should be equivalent.
    game1 = GameState(1)
    game1.give_to(Cardboard(Decklist.Forest()), ZONE.HAND)
    game1.give_to(Cardboard(Decklist.Plains()), ZONE.HAND)
    game2 = game1.copy()
    # game 1: [0] into play, then the other
    mover = Verbs.MoveToZone(ZONE.FIELD)
    game1A = mover.do_it(game1, game1.active.hand[0], [])[0][0]
    game1B = mover.do_it(game1A, game1A.active.hand[0], [])[0][0]
    # game 2: [1] into play, then the other
    game2A = mover.do_it(game2, game2.active.hand[1], [])[0][0]
    game2B = mover.do_it(game2A, game2A.active.hand[0], [])[0][0]
    assert (game1B == game2B)

    # but they would NOT be equivalent if I untapped between plays, since
    # all cards (including lands!) mark summoning sickness
    game1 = GameState(1)
    game1.give_to(Cardboard(Decklist.Forest()), ZONE.HAND)
    game1.give_to(Cardboard(Decklist.Plains()), ZONE.HAND)
    game2 = game1.copy()
    # game 1: [0] into play, then the other
    mover = Verbs.MoveToZone(ZONE.FIELD)
    game1A = mover.do_it(game1, game1.active.hand[0], [])[0][0]
    game1A.step_untap()
    game1B = mover.do_it(game1A, game1A.active.hand[0], [])[0][0]
    # game 2: [1] into play, then the other
    game2A = mover.do_it(game2, game2.active.hand[1], [])[0][0]
    game2A.step_untap()
    game2B = mover.do_it(game2A, game2A.active.hand[0], [])[0][0]
    assert (game1B != game2B)
    # if untap both, then should be equivalent again
    game1B.step_untap()
    game2B.step_untap()
    assert (game1B == game2B)

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing Caretakers, Axebane, Battlement...")
    start_clock = time.perf_counter()

    game = GameState(1)
    game.give_to(Cardboard(Decklist.Caretaker()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Caretaker()), ZONE.HAND)
    game.give_to(game.active.hand[0], ZONE.FIELD)
    assert (len(game.super_stack) == 0)  # nothing triggers off of this move
    assert game.active.field[0].summon_sick
    assert len(game.active.get_valid_activations()) == 0
    # what if I give the caretaker something to tap?
    caryatid = Cardboard(Decklist.Caryatid())
    game.give_to(caryatid, ZONE.FIELD)
    # no, caretaker is still summon_sick. good.
    assert len(game.active.get_valid_activations()) == 0
    game.active.field.remove(caryatid)

    game.step_untap()
    assert not game.active.field[0].summon_sick
    assert (len(game.active.get_valid_activations()) == 0)  # nothing to tap

    # give it something to tap
    caryatid.zone = ZONE.NEW
    game.give_to(caryatid, ZONE.FIELD)
    assert len(game.active.field) == 2
    assert len(game.active.get_valid_activations()) == 1
    tree = PlayTree([game], 2)
    tree.main_phase_for_all_active_states()
    [univ1] = tree.get_states_no_options()
    assert len(univ1.active.hand) == 0  # used mana to cast 2nd Caretaker
    assert len(univ1.active.field) == 3
    assert univ1.active.pool == ManaHandler.ManaPool("")
    assert all([c.tapped or c.summon_sick for c in univ1.active.field])

    # Rewind to before casting 2nd Caretaker. Give 1st TWO things to tap.
    game.give_to(game.active.hand[0], ZONE.FIELD)
    # only one ability, but two options to activate it
    ability_tuples = game.active.get_valid_activations()
    assert len(ability_tuples) == 2
    assert ability_tuples[0][0] == ability_tuples[1][0]
    assert ability_tuples[0][1] == ability_tuples[1][1]
    assert ability_tuples[0][2] != ability_tuples[1][2]
    tree = PlayTree([game], 2)
    tree.main_phase_for_all_active_states()
    [univ2, univ3] = tree.get_states_no_options()
    assert (univ2.active.pool == ManaHandler.ManaPool("A"))
    assert (univ3.active.pool == ManaHandler.ManaPool("A"))
    assert (len(univ2.active.field) == len(univ3.active.field))
    # check that they are really tapped differently
    assert ([c.tapped for c in univ2.active.field]
            != [c.tapped for c in univ3.active.field])
    assert univ2 != univ3

    # see what happens with two active caretakers
    game3 = univ3
    game3.step_untap()
    # 2 Caretakers plus Caryatid in play. 5 possibilities. But Caretakers are
    # equivalent so we only see 3 options. Good.
    game3_abils = game3.active.get_valid_activations()
    assert len(game3_abils) == 3
    care3_abils = [tup for tup in game3_abils if tup[1].name == "Caretaker"]
    universes = []
    for ability, source, choice_list in care3_abils:
        for g in ability.activate(game3, source, choice_list):
            universes += g.clear_super_stack()
    assert (len(universes) == 2)
    [univ4, univ5] = universes
    assert (univ4.active.pool == ManaHandler.ManaPool("A"))
    assert (univ5.active.pool == ManaHandler.ManaPool("A"))
    assert (len(univ4.active.field) == len(univ5.active.field))
    assert ([c.tapped for c in univ4.active.field]
            != [c.tapped for c in univ5.active.field])
    # One universe has action left (caryatid), other doesn't (lone caretaker)
    assert ({len(univ4.active.get_valid_activations()),
             len(univ5.active.get_valid_activations())} == {0, 1})

    # may as well use this setup to test Axebane and Battlement as well
    axe = Cardboard(Decklist.Axebane())
    battle = Cardboard(Decklist.Battlement())
    game6 = univ2.copy()
    game6.give_to(axe, ZONE.FIELD)
    game6.give_to(battle, ZONE.FIELD)
    assert len(game6.active.get_valid_activations()) == 0  # still summon_sick
    game6.step_untap()
    # axebane; battlement; caryatid; caretaker with 4 targets to tap
    assert len(game6.active.get_valid_activations()) == 7
    tree6 = PlayTree([game6], 5)
    tree6.main_phase_for_all_active_states()
    collector = set()
    for g in tree6.get_states_no_options():
        collector.add(str(g.active.pool))
    assert collector == {"GGGGGAAAAAAA", "GGGGGAAAAAA", "AAAAAAA", "GGGGGAA",
                         "AAA"}
    assert len(tree6.get_states_no_options()) == 1+1+2+2+1
    assert len(tree6.get_active()) == 0
    # Math: count based on when the first caretaker is tapped (which action).
    # 5th: impossible
    # 4th: 6 ways to order other 3. Caretaker taps other caretaker. 6*1=6
    # 3rd: 6 ways for which other is left. Caretaker either taps non-caretaker
    #   or remaining caretaker, so 2 ways. 6*2=12.
    # 2nd: 3 choices for what tapped first. Caretaker has 3 targets: if target
    #   is caretaker, other two tap in either order. If not, can tap the other
    #   and strand the caretaker, or tap both with caretaker. 3*(1*2+2*2)=18
    # 1st: Caretaker has 4 targets. If target is caretaker, then 6 ways to
    #   sequence the other 3. 3 ways to not, leaving caretaker and 2 others.
    #   Either tap caretaker + one of 2 and then remainder, or tap one and then
    #   tap either caretaker or remainder. 1*6+3*(2+2*2)=24
    assert tree6.traverse_counter == 72  # 6+12+18+24=60
    assert len(tree6.get_intermediate()) == 34

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Can PlayTree find 8 mana on turn 3...")
    start_clock = time.perf_counter()

    game = GameState(1)
    game.is_tracking_history = True
    game.give_to(Cardboard(Decklist.Forest()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Forest()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Forest()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Roots()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Caretaker()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Battlement()), ZONE.HAND)
    # deck
    for x in range(10):
        game.give_to(Cardboard(Decklist.Forest()), ZONE.DECK)
    # tree. Turn 1.
    tree = PlayTree([game], 5)
    tree.main_phase_for_all_active_states(1)
    # start, Forest, tap, Caretaker, resolve
    assert len(tree.get_intermediate(1)) == 5
    assert len(tree.get_states_no_options(1)) == 1
    assert tree.traverse_counter == 5

    # Turn 2.
    tree.beginning_phase_for_all_valid_states()
    assert len(tree.get_active(2)) == 3  # played nothing, forest, or caretaker
    tree.main_phase_for_all_active_states(2)
    assert len(tree.get_intermediate(2)) == 53
    assert len(tree.get_states_no_options(2)) == 7
    assert tree.traverse_counter == 74

    # Turn 3.
    tree.beginning_phase_for_all_valid_states()
    assert len(tree.get_active(3)) == 12
    tree.main_phase_for_all_active_states(3)
    print("      ...done running, %0.2f sec. (~0.63 2022-07-22)"
          % (time.perf_counter() - start_clock))
    intermed = tree.get_intermediate(3)
    no_opts = tree.get_states_no_options(3)
    assert len(intermed) == 1638
    assert len(intermed) == len(set(intermed))
    assert len(no_opts) == 62
    assert tree.traverse_counter == 3716
    assert max([g.active.pool.cmc() for g in no_opts]) == 8
    print("      ...done checking, %0.2f sec. (~0.70 2022-07-22)"
          % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing Wall of Blossoms, Arcades, and ETBs")
    start_clock = time.perf_counter()

    game = GameState(1)
    game.is_tracking_history = False
    # field
    game.give_to(Cardboard(Decklist.Plains()), ZONE.FIELD)
    # hand
    game.give_to(Cardboard(Decklist.Blossoms()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Blossoms()), ZONE.HAND)
    game.give_to(Cardboard(Decklist.Forest()), ZONE.HAND)
    # deck
    for x in range(10):
        game.give_to(Cardboard(Decklist.Island()), ZONE.DECK)

    tree = PlayTree([game], 5)
    # only option is play Forest, play Blossoms, draw Island
    tree.main_phase_for_all_active_states()
    assert len(tree.get_states_no_options()) == 1
    [final] = tree.get_states_no_options()
    assert len(final.hand) == 2
    assert len(final.field) == 3
    assert len(final.deck) == 9
    assert any([c.has_type(Decklist.Island) for c in final.hand])
    assert not any([c.has_type(Decklist.Island) for c in final.field])

    # play next turn: draw Island, play Island, play Blossoms, draw Island
    tree2 = PlayTree([final], 5)
    tree2.beginning_phase_for_all_valid_states()
    tree2.main_phase_for_all_active_states()
    assert len(tree2.get_states_no_options()) == 2  # floating W or U
    [final2, _] = tree2.get_states_no_options()
    assert len(final2.hand) == 2
    assert len(final2.field) == 5
    assert len(final2.deck) == 7
    assert (any([c.has_type(Decklist.Island) for c in final2.hand]))
    assert (any([c.has_type(Decklist.Island) for c in final2.field]))

    # cast a Caryatid to be sure I didn't make ALL defenders draw on etb
    final2.give_to(Cardboard(Decklist.Caryatid()), ZONE.HAND)
    tree3 = PlayTree([final2], 5)
    tree3.beginning_phase_for_all_valid_states()
    tree3.main_phase_for_all_active_states()
    for g in tree3.get_states_no_options():
        assert len(g.hand) == 2
        assert len(g.field) == 7
        assert len(g.deck) == 6

    # but what if there was an Arcades in play?
    gameA = GameState(1)
    # deck
    for x in range(10):
        gameA.give_to(Cardboard(Decklist.Island()), ZONE.DECK)
    gameA.give_to(Cardboard(Decklist.Arcades()), ZONE.FIELD)
    assert (len(gameA.super_stack) == 0)  # Arcades doesn't trigger itself
    # add Blossoms to field and hopefully draw 2
    gameA.give_to(Cardboard(Decklist.Blossoms()), ZONE.FIELD)
    assert len(gameA.super_stack) == 2
    assert len(gameA.stack) == 0
    assert len(gameA.active.hand) == 0  # haven't draw, put triggers on stack
    assert len(gameA.active.deck) == 10  # haven't draw, put triggers on stack
    # clear the super_stack and then stack. should come to the same thing.
    gameA, gameA1 = gameA.clear_super_stack()
    assert gameA != gameA1  # different order of triggers
    while len(gameA.stack) > 0:
        universes = gameA.resolve_top_of_stack()
        assert len(universes) == 1
        gameA = universes[0]
    while len(gameA1.stack) > 0:
        universes = gameA1.resolve_top_of_stack()
        assert len(universes) == 1
        gameA1 = universes[0]
    assert gameA == gameA1
    assert len(gameA.super_stack) == 0
    # should have drawn 2 cards
    assert len(gameA.hand) == 2
    assert len(gameA.deck) == 8
    # now let's try to add a Caryatid to field and hopefully draw 1
    gameA.give_to(Cardboard(Decklist.Caryatid()), ZONE.FIELD)
    assert len(gameA.super_stack) == 1
    assert len(gameA.hand) == 2  # haven't draw or put triggers on stack
    assert len(gameA.deck) == 8  # haven't draw or put triggers on stack
    [gameA] = gameA.clear_super_stack()
    while len(gameA.stack) > 0:
        universes = gameA.resolve_top_of_stack()
        assert (len(universes) == 1)
        gameA = universes[0]
    # should have drawn 2 cards
    assert (len(gameA.hand) == 3)
    assert (len(gameA.deck) == 7)

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    # print("Testing Collected Company and simultaneous ETBs")
    # start_clock = time.perf_counter()
    #
    # def cast_and_resolve_company(state):
    #     # cast Collected Company
    #     state.pool.add_mana("GGGG")
    #     state.give_to(Cardboard(Decklist.Company()), ZONE.HAND)
    #     castables = state.get_valid_castables()
    #     print(castables)
    #     assert len(castables) == 1
    #     assert castables[0][1] == []  # no choices to be made, yet
    #     [on_stack] = castables[0][0].cast(state, castables[0][1])
    #     print(castables)
    #     print(on_stack)
    #     assert len(on_stack.super_stack) == 0
    #     return on_stack.resolve_top_of_stack()
    #
    # game = GameState()
    # # deck of 6 cards
    # game.give_to(Cardboard(Decklist.Caretaker()), ZONE.DECK)
    # game.give_to(Cardboard(Decklist.Caretaker()), ZONE.DECK)
    # game.give_to(Cardboard(Decklist.Axebane()), ZONE.DECK)
    # game.give_to(Cardboard(Decklist.Battlement()), ZONE.DECK)
    # game.give_to(Cardboard(Decklist.Forest()), ZONE.DECK)
    # game.give_to(Cardboard(Decklist.Forest()), ZONE.DECK)
    # # cast Collected Company
    # universes = cast_and_resolve_company(game)
    # assert (len(universes) == 4)
    # for u in universes:
    #     assert len(u.deck) == 4
    #     assert len(u.field) == 2
    #     assert len(u.grave) == 1
    #     if any([c.has_type(Decklist.Axebane) for c in u.field]):
    #         assert (
    #             not any([c.has_type(Decklist.Axebane) for c in u.deck]))
    #     if any([c.has_type(Decklist.Battlement) for c in u.field]):
    #         assert (not any(
    #             [c.has_type(Decklist.Battlement) for c in u.deck]))
    #     assert (not any([c.has_type(RulesText.Land) for c in u.field]))
    #
    # # deck of 6 forests on top, then 10 islands
    # gameF = GameState()
    # for _ in range(6):
    #     gameF.give_to(Cardboard(Decklist.Forest()), ZONE.DECK)
    # for _ in range(10):
    #     gameF.give_to(Cardboard(Decklist.Island()), ZONE.DECK)
    # # should be forests on top
    # assert all([c.has_type(Decklist.Forest) for c in gameF.deck[:6]])
    # # cast Collected Company
    # universes = cast_and_resolve_company(gameF)
    # assert len(universes) == 1
    # u = universes[0]
    # # now should be islands on top, forests on bottom
    # assert all([c.has_type(Decklist.Island) for c in u.deck[:10]])
    # assert all([c.has_type(Decklist.Forest) for c in u.deck[-6:]])
    # assert len(u.field) == 0
    # assert len(u.grave) == 1
    #
    # # deck of 5 forests on top, one Caretaker, then 10 islands
    # game1 = GameState()
    # for _ in range(5):
    #     game1.give_to(Cardboard(Decklist.Forest()), ZONE.DECK)
    # game1.give_to(Cardboard(Decklist.Caretaker()), ZONE.DECK)
    # for _ in range(10):
    #     game1.give_to(Cardboard(Decklist.Island()), ZONE.DECK)
    # assert (len(game1.deck) == 16)
    # # cast Collected Company
    # universes = cast_and_resolve_company(game1)
    # assert (len(universes) == 1)
    # u = universes[0]
    # # now should be islands on top, forests on bottom
    # assert all([c.has_type(Decklist.Island) for c in u.deck[:10]])
    # assert all([c.has_type(Decklist.Forest) for c in u.deck[-5:]])
    # assert u.deck[-6].has_type(Decklist.Island)
    # assert len(u.field) == 1
    # assert len(u.grave) == 1
    #
    # # deck of only 4 cards total, all Caretakers
    # game4 = GameState()
    # for _ in range(4):
    #     game4.give_to(Cardboard(Decklist.Caretaker()), ZONE.DECK)
    # # should be forests on top
    # assert (len(game4.deck) == 4)
    # # cast Collected Company
    # universes = cast_and_resolve_company(game4)
    # assert (len(universes) == 1)
    # u = universes[0]
    # assert (len(u.deck) == 2)
    # assert (len(u.field) == 2)
    # assert (len(u.grave) == 1)
    #
    # # Does Blossoms trigger correctly? start with 12 cards in deck
    # game = GameState()
    # game.give_to(Cardboard(Decklist.Blossoms()), ZONE.DECK)
    # game.give_to(Cardboard(Decklist.Omens()), ZONE.DECK)
    # for _ in range(10):
    #     game.give_to(Cardboard(Decklist.Forest()), ZONE.DECK)
    # # cast Collected Company
    # universes = cast_and_resolve_company(game)
    # assert len(universes) == 2  # two draws could be on stack in either order
    # u0, u1 = universes
    # assert (u0 != u1)
    # while len(u0.stack) > 0:
    #     [u0] = u0.resolve_top_of_stack()
    # while len(u1.stack) > 0:
    #     [u1] = u1.resolve_top_of_stack()
    # assert u0 == u1
    # assert len(u0.hand) == 2 and len(u0.deck) == 8
    #
    # # Note: if I put two identical Blossoms into play simultaneously, I STILL
    # # will get two GameStates even though they are identical! And that's ok.
    # # it's not worth the effort to optimize this out, right now.
    # game = GameState()
    # game.give_to(Cardboard(Decklist.Blossoms()), ZONE.DECK)
    # game.give_to(Cardboard(Decklist.Blossoms()), ZONE.DECK)
    # for _ in range(10):
    #     game.give_to(Cardboard(Decklist.Forest()), ZONE.DECK)
    # # cast Collected Company
    # universes = cast_and_resolve_company(game)
    # assert len(universes) == 2  # two draws could be on stack in either order
    # u0, u1 = universes
    # assert (u0 == u1)
    # while len(u0.stack) > 0:
    #     [u0] = u0.resolve_top_of_stack()
    # while len(u1.stack) > 0:
    #     [u1] = u1.resolve_top_of_stack()
    # assert (u0 == u1)
    # assert (len(u0.hand) == 2 and len(u0.deck) == 8)
    #
    # print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("\n\npasses all tests!")
