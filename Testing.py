# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 22:15:57 2020

@author: Cobi
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Tuple, List

import Verbs

if TYPE_CHECKING:
    from Abilities import ActivatedAbility

import ZONE
from GameState import GameState
import ManaHandler
import Decklist
from Cardboard import Cardboard, CardNull
from Verbs import PlayAbility, PlayCardboard
from PlayTree import PlayTree
import time

if __name__ == "__main__":

    def cast_thing(state,
                   th: Tuple[ActivatedAbility, Cardboard, list] | Cardboard
                   ) -> List[GameState]:
        if isinstance(th, tuple):
            ability, source, choice_list = th
            g_list = PlayAbility(ability).do_it(state, source, choice_list)
        else:
            card = th
            choice_list = card.cost.choose_choices(state, card)
            g_list = PlayCardboard().do_it(state, card, choice_list)
        return [g for g, _, _ in g_list]


    # -----------------------------------------------------------------------

    print("Testing Wall of Roots...")
    start_clock = time.perf_counter()

    game_orig = GameState()
    game_orig.is_tracking_history = False  # True
    assert len(game_orig.get_valid_activations()) == 0
    assert len(game_orig.get_valid_castables()) == 0

    # four copies of Wall of Roots in hand
    for i in range(4):
        game_orig.MoveZone(Cardboard(Decklist.Roots()), ZONE.HAND)
    assert (len(game_orig.hand) == 4)
    assert (len(game_orig.field) == 0)

    # make sure the AddMana Verb works properly
    tuple_list = Decklist.Verbs.AddMana("U").do_it(game_orig, CardNull(), [])
    assert len(tuple_list) == 1
    mana_game, _, choices = tuple_list[0]
    assert len(choices) == 0
    assert mana_game.pool == ManaHandler.ManaPool("U")
    # because AddMana mutates, returned game IS original game
    assert game_orig.pool == ManaHandler.ManaPool("U")
    assert mana_game is game_orig

    # check the abilities of Wall of Roots in hand. it has 1 but can't be used.
    roots = game_orig.hand[0]
    assert len(roots.get_activated()) == 1
    roots_abil = roots.get_activated()[0]
    choices = roots_abil.get_choice_options(game_orig, roots)
    assert choices == [[]]  # list of empty list
    assert not PlayAbility(roots_abil).can_be_done(game_orig, roots, [])

    # move a Wall of Roots to field and try again
    game_orig.MoveZone(game_orig.hand[0], ZONE.FIELD)
    assert len(game_orig.hand) == 3
    assert len(game_orig.field) == 1
    roots = game_orig.field[0]
    assert len(roots.get_activated()) == 1
    assert len(roots.counters) == 0  # no counters on it yet
    roots_abil = roots.get_activated()[0]
    choices = roots_abil.get_choice_options(game_orig, roots)
    assert choices == [[]]  # list of empty list
    assert PlayAbility(roots_abil).can_be_done(game_orig, roots, [])

    # make sure the cost can actually be paid
    cost_game = game_orig.copy()
    cost_roots = cost_game.field[0]
    assert roots_abil.cost.can_be_done(cost_game, cost_roots, [])
    tuple_list = roots_abil.cost.do_it(cost_game, cost_roots, [])
    assert len(tuple_list) == 1
    assert roots_abil.cost.mutates  # this particular cost mutates
    assert cost_game is tuple_list[0][0]  # so output is same as original
    assert len(cost_roots.counters) == 2
    for value in cost_roots.counters:
        assert "-0/-1" == value or "@" in value
    # should no longer be possible to do
    assert not roots_abil.cost.can_be_done(cost_game, cost_roots, [])
    assert len(cost_game.get_valid_activations()) == 0

    # untap to reset things, then try to activate the ability "properly"
    game_orig.step_untap()
    assert len(game_orig.get_valid_activations()) == 1
    game_list = cast_thing(game_orig, game_orig.get_valid_activations()[0])
    assert len(game_list) == 1
    activ_game = game_list[0]
    assert activ_game is not game_orig
    new_roots = activ_game.field[0]
    assert roots is not new_roots
    assert new_roots.has_type(Decklist.Roots)
    assert len(roots.counters) == 0  # no counters on original
    assert len(new_roots.counters) == 2  # -0/-1 and @used
    assert activ_game.pool == ManaHandler.ManaPool("G")
    assert game_orig.pool == ManaHandler.ManaPool("")  # original unchanged
    assert len(new_roots.get_activated()) == 1  # still has one ability
    assert len(activ_game.get_valid_activations()) == 0

    # try to cast something
    assert len(activ_game.get_valid_castables()) == 0  # not enough mana yet
    assert activ_game.pool == ManaHandler.ManaPool("G")
    copygame = activ_game.copy()
    copygame.pool.add_mana("G")  # add mana directly
    # all 3 roots in hand only generate 1 option--to cast Roots
    assert (len(copygame.get_valid_castables()) == 1)
    # cast the newly castable spell
    cardboard = copygame.get_valid_castables()[0]
    assert [o is cardboard for o in copygame.hand] == [True, False, False]
    [copygame3] = cast_thing(copygame, cardboard)  # puts it on the stack
    assert (copygame3.pool == ManaHandler.ManaPool(""))  # no mana anymore
    assert (len(copygame3.stack) == 1)  # one spell on the stack
    assert (len(copygame3.hand) == 2)  # two cards in hand
    assert (len(copygame3.field) == 1)  # one card in play
    [copygame4] = copygame3.resolve_top_of_stack()
    assert (copygame4.pool == ManaHandler.ManaPool(""))  # still no mana
    assert (len(copygame4.stack) == 0)  # nothing on the stack
    assert (len(copygame4.hand) == 2)  # two cards in hand
    assert (len(copygame4.field) == 2)  # two cards in play
    # should be one ability (new Roots) & no castable spells (not enough mana)
    assert (len(copygame4.get_valid_activations()) == 1)
    assert (len(copygame4.get_valid_castables()) == 0)
    # Stack should be empty, so resolving the stack should be impossible
    assert ([] == copygame4.resolve_top_of_stack())
    # Just to check, original game is still unchanged:
    assert (len(activ_game.field) == 1)
    assert (str(activ_game.pool) == "G")

    # check that game history is NOT tracking (since tracking is off)
    assert not game_orig.is_tracking_history
    assert game_orig.previous_state is None
    assert game_orig.events_since_previous == ""
    assert not activ_game.is_tracking_history
    assert activ_game.previous_state is None
    assert activ_game.events_since_previous == ""

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing Sylvan Caryatid, Untap & Upkeep, GameState history...")
    start_clock = time.perf_counter()

    # add a caryatid to the all-roots game
    carygame1, _ = game_orig.copy_and_track([])
    carygame1.is_tracking_history = True  # start tracking
    carygame1.MoveZone(Cardboard(Decklist.Caryatid()), ZONE.FIELD)
    # should only see one valid ability to activate, since Caryatid not hasty
    assert (len(carygame1.get_valid_activations()) == 1)
    assert (len(carygame1.get_valid_castables()) == 0)  # no castable cards

    # try to untap and upkeep to get rid of summonning sickness
    carygame1.step_untap()
    carygame1.step_upkeep()
    assert len(carygame1.get_valid_castables()) == 0  # no castable cards
    gameN = carygame1
    options = gameN.get_valid_activations() + gameN.get_valid_castables()
    assert len(options) == 2
    # as long as there are things to do, do them! auto-choose 1st option
    while len(options) > 0:
        gameN = cast_thing(gameN, options[0])[0]
        while len(gameN.stack) > 0:
            gameN = gameN.resolve_top_of_stack()[0]
        options = gameN.get_valid_activations() + gameN.get_valid_castables()
    # result should be Caryatid and two Roots in play
    assert len(gameN.hand) == 2
    assert len(gameN.field) == 3
    assert gameN.pool == ManaHandler.ManaPool("G")

    # check if the history tracker worked
    historyN = gameN.get_all_history()
    # print(historyN)
    assert historyN.count("*** Activate Roots add G ***") == 2
    assert historyN.count("*** Activate Caryatid add Au ***") == 1
    assert historyN.count("*** Cast Roots ***") == 1
    assert game_orig.get_all_history() == ""

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    # build a PlayTree
    tree1 = PlayTree([carygame1], 5)
    # try untap and upkeep
    try:
        tree1.beginning_phase_for_all_active_states()
        assert False  # SHOULD throw error, because drawing from empty library
    except Verbs.LoseTheGameError:
        assert True











    # # basic game-loop
    # def BasicLoop(gamestate):
    #     gameN = gamestate
    #     options = gameN.get_valid_activations() + gameN.get_valid_castables()
    #     while len(options) > 0:
    #         if gameN.is_tracking_history:
    #             print("\n")
    #             print(gameN)
    #         if len(options) > 1 and gameN.is_tracking_history:
    #             print("\nSplit! options are:", options)
    #             print("Taking last option in list")
    #         if isinstance(options[-1], Abilities.StackEffect):
    #             universes = options[-1].PutOnStack(gameN)
    #         elif isinstance(options[-1], Cardboard):
    #             universes = gameN.CastSpell(
    #                 options[-1])  # puts it on the stack
    #         else:
    #             raise ValueError("incorrect type of object on stack!")
    #         # universes is a list of GameStates
    #         if len(universes) > 1 and gameN.is_tracking_history:
    #             print("\nSplit! universes are:")
    #             for u in universes:
    #                 print("     ---\n", u, "\n     ---")
    #             print("Taking last option in list")
    #         gameN = universes[-1]
    #         while len(gameN.stack) > 0:
    #             universes = gameN.resolve_top_of_stack()
    #             if len(universes) > 1 and gameN.is_tracking_history:
    #                 print("Split! universes are:")
    #                 for u, _ in universes:
    #                     print("     ---\n", u, "\n     ---")
    #                 print("Taking last option in list")
    #             gameN = universes[-1]
    #         options = gameN.get_valid_activations() +
    #                                      gameN.get_valid_castables()
    #     return gameN
    #
    #
    # ###--------------------------------------------------------------------
    # print("Testing basic lands and BasicLoop...")
    # start_clock = time.perf_counter()
    #
    # game = GameState()
    # game.is_tracking_history = False
    # # field
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.FIELD)
    # game.MoveZone(Cardboard(Decklist2.Plains), ZONE.FIELD)
    # # hand
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Roots), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Caryatid), ZONE.HAND)
    #
    # gameN = BasicLoop(game)
    # assert (len(gameN.hand) == 1)
    # assert (len(gameN.field) == 5)
    # assert (gameN.pool == ManaHandler.ManaPool(""))
    # assert (len(game.field) == 2)  # orig game is untouched
    #
    # print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))
    #
    # ###--------------------------------------------------------------------
    # print("Testing shock-lands...")
    # start_clock = time.perf_counter()
    #
    # game = GameState()
    # game.is_tracking_history = False
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.FIELD)
    # # hand
    # game.MoveZone(Cardboard(Decklist2.BreedingPool), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Caryatid), ZONE.HAND)
    #
    # # run all the way through, with the settings I've chosen, should end with
    # # shocking in the Breeding Pool and using it to cast the Caryatid
    # gameN = BasicLoop(game)
    # assert (len(gameN.hand) == 0)
    # assert (len(gameN.field) == 3)
    # assert (gameN.pool == ManaHandler.ManaPool(""))
    # assert (gameN.life == 18)
    #
    # # make sure we have shock and tapped options available
    # options = game.get_valid_castables()
    # assert (len(options) == 1)
    # assert (options[0] is game.hand[1])  # only castable is shockland
    # universes = game.CastSpell(
    #     options[-1])  # puts it into play, b/c lands not on stack
    # assert (len(universes) == 2)  # shock or tapped
    #
    # # shock-universe
    # assert (not [u for u in universes if u.life == 18][0].field[0].tapped)
    # # tapped-universe
    # assert ([u for u in universes if u.life == 20][0].field[0].tapped)
    #
    # print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))
    #
    # ###--------------------------------------------------------------------
    # print("""Testing equality of gamestates...""")
    # start_clock = time.perf_counter()
    #
    # game = GameState()
    # game.is_tracking_history = False
    # # field
    # game.MoveZone(Cardboard(Decklist2.Plains), ZONE.FIELD)
    # # hand
    # game.MoveZone(Cardboard(Decklist2.HallowedFountain), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Roots), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Caryatid), ZONE.HAND)
    #
    # # try to copy, make sure equality holds
    # cp = game.copy()
    # assert (cp == game)
    # assert (cp is not game)
    #
    # # add this forest to one but not the other
    # forest = Cardboard(Decklist2.Forest)
    # game.MoveZone(forest, ZONE.FIELD)
    # assert (game != cp)
    # # add a copy of the forst to the other
    # forest2 = forest.copy()
    # forest2.zone = ZONE.NEW
    # cp.MoveZone(forest2, ZONE.FIELD)
    # Cardboard uses "is" for eq  (or else "in list" breaks)
    # assert forest != forest2
    # assert forest is not forest2
    # assert (game == cp)
    # # tap both of these forests for mana
    # cp3 = game.ActivateAbilities(forest, forest.get_activated()[0])[0]
    # assert (game != cp3)
    # assert (cp != cp3)
    # cp4 = cp.ActivateAbilities(forest2, forest2.get_activated()[0])[0]
    # assert (game != cp4)
    # assert (cp3 == cp4)
    # assert (not (cp3 is cp4))
    #
    # # can I put these in a set?
    # # noinspection PySetFunctionToLiteral
    # testset = set([game, cp, cp3])
    # assert (len(testset) == 2)
    # assert (cp4 in testset)
    #
    # # two lands. put into play in opposite order. Should be equivalent.
    # game1 = GameState()
    # game1.is_tracking_history = False
    # game1.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game1.MoveZone(Cardboard(Decklist2.Plains), ZONE.HAND)
    # game2 = game1.copy()
    # # game 1: [0] into play, then the other
    # game1.MoveZone(game1.hand[0], ZONE.FIELD)
    # game1.untap_step()
    # game1.MoveZone(game1.hand[0], ZONE.FIELD)
    # # game 2: [1] into play, then the other
    # game2.MoveZone(game2.hand[1], ZONE.FIELD)
    # game2.untap_step()
    # game2.MoveZone(game2.hand[0], ZONE.FIELD)
    # assert (game1 == game2)
    #
    # # two creatures. put into play in opposite order. Should be NOT
    # # equivalent, because of summoning sickness
    # game1 = GameState()
    # game1.is_tracking_history = False
    # game1.MoveZone(Cardboard(Decklist2.Caryatid), ZONE.HAND)
    # game1.MoveZone(Cardboard(Decklist2.Roots), ZONE.HAND)
    # game2 = game1.copy()
    # # game 1: [0] into play, then the other
    # game1.MoveZone(game1.hand[0], ZONE.FIELD)
    # game1.untap_step()
    # game1.MoveZone(game1.hand[0], ZONE.FIELD)
    # # game 2: [1] into play, then the other
    # game2.MoveZone(game2.hand[1], ZONE.FIELD)
    # game2.untap_step()
    # game2.MoveZone(game2.hand[0], ZONE.FIELD)
    # assert (game1 != game2)  # creatures DO get summoning-sick.
    #
    # print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))
    #
    # ###--------------------------------------------------------------------
    # print("Testing TurnTracker...")
    # start_clock = time.perf_counter()
    #
    # game = GameState()
    # game.is_tracking_history = False
    # # field
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.FIELD)
    # game.MoveZone(Cardboard(Decklist2.Plains), ZONE.FIELD)
    # # hand
    # game.MoveZone(Cardboard(Decklist2.HallowedFountain), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Roots), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist.Caryatid), ZONE.HAND)
    #
    # tracker = PlayTree.TurnTracker.InitFromGameState(game)
    # tracker.PlayTurn()
    # assert (len(tracker.finalnodes) == 8)
    # assert (len(tracker.allnodes) == 84)
    # assert (tracker.traverse_counter == 146)
    # assert (len(tracker.GetFinal()) == 6)
    # assert (len(tracker.GetAll()) == 18)
    # # for node in tracker.finalnodes:
    # #     print("-----------")
    # #     print(node)
    # # print("\n\n")
    #
    # # fixing TurnTracker history duplication: second minor test
    # game2 = GameState()
    # game2.is_tracking_history = True
    # game2.MoveZone(Cardboard(Decklist2.HallowedFountain),
    #                  ZONE.HAND)
    # game2.MoveZone(Cardboard(Decklist.Forest), ZONE.HAND)
    #
    # tracker2 = PlayTree.TurnTracker.InitFromGameState(game2)
    # tracker2.PlayTurn()
    # assert (len(tracker2.finalnodes) == 4)
    # assert (len(tracker2.allnodes) == 7)
    # assert (tracker2.traverse_counter == 6)
    # assert (len(tracker2.GetFinal()) == 3)
    # assert (len(tracker2.GetAll()) == 4)
    # histlength = [0, 0, 0, 0]
    # for n in tracker2.allnodes:
    #     histlength[len(n.history)] += 1
    # assert (histlength == [1, 3, 3, 0])  # 1 with zero action, 3 with one...
    #
    # print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))
    #
    # ###--------------------------------------------------------------------
    # print("Testing PlayTree...")
    # start_clock = time.perf_counter()
    #
    # game = GameState()
    # game.is_tracking_history = False
    # game.MoveZone(Cardboard(Decklist2.Plains), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Roots), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Caryatid), ZONE.HAND)
    # for x in range(10):
    #     game.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    #
    # tree = PlayTree.PlayTree(game, 5)
    # # tree.PrintLatest()
    # assert (len(tree.LatestNodes()) == 2)
    #
    # tree.PlayNextTurn()
    # # tree.PrintLatest()
    #
    # tree.PlayNextTurn()
    # # tree.PrintLatest()
    # assert (len(tree.LatestNodes()) == 4)
    # assert (all([len(n.state.hand) == 2 for n in tree.LatestNodes()]))
    # assert (all([len(n.state.field) == 5 for n in tree.LatestNodes()]))
    #
    # assert (
    #     all([n.state.turn_count == 1 for n in tree.trackerlist[0].allnodes]))
    # assert (
    #     all([n.state.turn_count == 2 for n in tree.trackerlist[1].allnodes]))
    # assert (
    #     all([n.state.turn_count == 3 for n in tree.trackerlist[2].allnodes]))
    #
    # print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))
    #
    # ###--------------------------------------------------------------------
    # print("Testing Caretakers, Axebane, Battlement...")
    # start_clock = time.perf_counter()
    #
    # game = GameState()
    # game.is_tracking_history = False
    # game.MoveZone(Cardboard(Decklist2.Caretaker), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Caretaker), ZONE.HAND)
    # game.MoveZone(game.hand[0], ZONE.FIELD)
    # assert (len(game.super_stack) == 0)  # nothing triggers off of this move
    #
    # assert (game.field[0].summon_sick)
    # assert (len(game.get_valid_activations()) == 0)
    # # what if I give the caretaker something to tap?
    # caryatid = Cardboard(Decklist2.Caryatid)
    # game.MoveZone(caryatid, ZONE.FIELD)
    # no, caretaker still summon_sick. good.
    # assert len(game.get_valid_activations()) == 0
    # game.field.remove(caryatid)
    #
    # game.untap_step()
    # assert (len(game.get_valid_activations()) == 0)  # nothing to tap
    #
    # # give it something to tap
    # caryatid.zone = ZONE.NEW
    # game.MoveZone(caryatid, ZONE.FIELD)
    # assert (len(game.get_valid_activations()) == 1)
    #
    # [univ1] = game.get_valid_activations()[0].PutOnStack(
    #     game)  # mana so just happens
    # assert (univ1.pool == ManaHandler.ManaPool("A"))
    # assert (all([c.tapped for c in univ1.field]))
    #
    # # give it TWO things to tap
    # game.MoveZone(game.hand[0], ZONE.FIELD)
    # still only 1 ability even if 2 "targets"
    # assert len(game.get_valid_activations()) == 1
    # universes = game.get_valid_activations()[0].PutOnStack(
    #     game)  # mana so just happens
    # assert (len(universes) == 2)  # two possible things to tap
    # [univ2, univ3] = universes
    # assert (univ2.pool == ManaHandler.ManaPool("A"))
    # assert (univ3.pool == ManaHandler.ManaPool("A"))
    # assert (len(univ2.field) == len(univ3.field))
    # # check that they are really tapped differently
    # assert [c.tapped for c in univ2.field] != [c.tapped for c in univ3.field]
    #
    # # see what happens with two active caretakers
    # game3 = univ3
    # game3.untap_step()
    # 2 Caretakers combined, plus Caryatid
    # assert len(game3.get_valid_activations()) == 2
    # care3 = [c for c in game3.field
    #          if c.rules_text == Decklist2.Caretaker][0]
    # universes = game3.ActivateAbilities(care3, care3.get_activated()[0])
    # assert (len(universes) == 2)
    # [univ4, univ5] = universes
    # assert (univ4.pool == ManaHandler.ManaPool("A"))
    # assert (univ5.pool == ManaHandler.ManaPool("A"))
    # assert (len(univ4.field) == len(univ5.field))
    # assert [c.tapped for c in univ4.field] != [c.tapped for c in univ5.field]
    # # One universe has action left (caryatid), other doesn't (lone caretaker)
    # assert ({len(univ4.get_valid_activations()),
    #          len(univ5.get_valid_activations())} == {0, 1})
    #
    # # may as well use this setup to test Axebane and Battlement as well
    # axe = Cardboard(Decklist2.Axebane)
    # battle = Cardboard(Decklist2.Battlement)
    # game6 = univ2.copy()
    # game6.MoveZone(axe, ZONE.FIELD)
    # game6.MoveZone(battle, ZONE.FIELD)
    # assert len(game6.get_valid_activations()) == 0  # still summon_sick
    # game6.untap_step()
    # [u_axe] = game6.ActivateAbilities(axe, axe.get_activated()[0])
    # assert (u_axe.pool == ManaHandler.ManaPool("AAAAA"))
    # [u_bat] = game6.ActivateAbilities(battle, battle.get_activated()[0])
    # assert (u_bat.pool == ManaHandler.ManaPool("GGGGG"))
    #
    # print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))
    #
    # ###--------------------------------------------------------------------
    # print("Can PlayTree find 8 mana on turn 3...")
    # start_clock = time.perf_counter()
    #
    # game = GameState()
    # game.is_tracking_history = True
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Roots), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Caretaker), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Battlement), ZONE.HAND)
    # # deck
    # for x in range(10):
    #     game.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    #
    # tree = PlayTree.PlayTree(game, 5)
    # assert (len(tree.trackerlist[-1].finalnodes) == 1)
    # assert (len(tree.LatestNodes()) == 1)
    #
    # tree.PlayNextTurn()
    # assert (len(tree.trackerlist[-1].finalnodes) == 2)
    # assert (len(tree.LatestNodes()) == 2)
    #
    # tree.PlayNextTurn()
    # assert (len(tree.trackerlist[-1].finalnodes) == 6)
    # # if I untap, only difference is counters on Roots. I lose track of mana
    # assert (len(tree.LatestNodes()) == 2)
    # # mana not visible in LatestNodes but IS visible in finalnodes
    # assert (any([n.state.pool.can_afford_mana_cost(ManaHandler.ManaCost("8"))
    #              for n in tree.trackerlist[-1].finalnodes]))
    #
    # # for n in tree.trackerlist[-1].finalnodes:
    # #     print(n)
    # #     print("")
    # # print("-----------\n")
    #
    # print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))
    #
    # ###--------------------------------------------------------------------
    # print("Testing Wall of Blossoms, Arcades, and ETBs")
    # start_clock = time.perf_counter()
    #
    # game = GameState()
    # game.is_tracking_history = True
    # # field
    # game.MoveZone(Cardboard(Decklist2.Plains), ZONE.FIELD)
    # # hand
    # game.MoveZone(Cardboard(Decklist2.Blossoms), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Blossoms), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # # deck
    # for x in range(10):
    #     game.MoveZone(Cardboard(Decklist2.Island), ZONE.DECK)
    #
    # tree = PlayTree.PlayTree(game, 5)
    #
    # # only option is play Forest, play Blossoms, draw Island
    # assert (len(tree.LatestNodes()) == 1)
    # assert (len(tree.trackerlist[-1].finalnodes) == 1)
    # [node] = tree.trackerlist[-1].finalnodes
    # final = node.state
    # assert (len(final.hand) == 2)
    # assert (len(final.field) == 3)
    # assert (len(final.deck) == 9)
    # assert (any([c.rules_text == Decklist2.Island for c in final.hand]))
    # assert (not any([c.rules_text == Decklist2.Island for c in final.field]))
    #
    # # play next turn: draw Island, play Island, play Blossoms, draw Island
    # tree.PlayNextTurn()
    # assert (len(tree.LatestNodes()) == 1)
    # assert (len(tree.trackerlist[-1].finalnodes) == 2)  # floating W or U
    # [node, _] = tree.trackerlist[-1].finalnodes
    # final = node.state
    # assert (len(final.hand) == 2)
    # assert (len(final.field) == 5)
    # assert (len(final.deck) == 7)
    #
    # assert (any([c.rules_text == Decklist2.Island for c in final.hand]))
    # assert (any([c.rules_text == Decklist2.Island for c in final.field]))
    #
    # # cast a Caryatid to be sure I didn't make ALL defenders draw on etb
    # final.MoveZone(Cardboard(Decklist2.Caryatid), ZONE.HAND)
    # final.untap_step()
    # tree2 = PlayTree.PlayTree(final, 5)
    # tree2.PlayNextTurn()
    # assert (len(tree2.LatestNodes()) == 1)
    # final2 = tree2.LatestNodes()[0].state
    # assert (len(final2.hand) == 1)
    # assert (len(final2.field) == 8)
    # assert (len(final2.deck) == 6)
    #
    # # but what if there was an Arcades in play?
    # gameA = GameState()
    # # deck
    # for x in range(10):
    #     gameA.MoveZone(Cardboard(Decklist2.Island), ZONE.DECK)
    # gameA.MoveZone(Cardboard(Decklist2.Arcades), ZONE.FIELD)
    # assert (len(gameA.super_stack) == 0)  # Arcades doesn't trigger itself
    # # add Blossoms to field and hopefully draw 2
    # gameA.MoveZone(Cardboard(Decklist2.Blossoms), ZONE.FIELD)
    # assert (len(gameA.super_stack) == 2)
    # assert (len(gameA.stack) == 0)
    # assert (len(gameA.hand) == 0)  # haven't draw or put triggers on stack
    # assert (len(gameA.deck) == 10)  # haven't draw or put triggers on stack
    # # clear the super_stack and then stack. should come to the same thing.
    # gameA, gameA1 = gameA.clear_super_stack()
    # assert (gameA != gameA1)  # different order of triggers
    # while len(gameA.stack) > 0:
    #     universes = gameA.resolve_top_of_stack()
    #     assert (len(universes) == 1)
    #     gameA = universes[0]
    # while len(gameA1.stack) > 0:
    #     universes = gameA1.resolve_top_of_stack()
    #     assert (len(universes) == 1)
    #     gameA1 = universes[0]
    # assert (gameA == gameA1)
    # assert (len(gameA.super_stack) == 0)
    # # should have drawn 2 cards
    # assert (len(gameA.hand) == 2)
    # assert (len(gameA.deck) == 8)
    # # now let's try to add a Caryatid to field and hopefully draw 1
    # gameA.MoveZone(Cardboard(Decklist2.Caryatid), ZONE.FIELD)
    # assert (len(gameA.super_stack) == 1)
    # assert (len(gameA.hand) == 2)  # haven't draw or put triggers on stack
    # assert (len(gameA.deck) == 8)  # haven't draw or put triggers on stack
    # [gameA] = gameA.clear_super_stack()
    # while len(gameA.stack) > 0:
    #     universes = gameA.resolve_top_of_stack()
    #     assert (len(universes) == 1)
    #     gameA = universes[0]
    # # should have drawn 2 cards
    # assert (len(gameA.hand) == 3)
    # assert (len(gameA.deck) == 7)
    #
    # # set up a sample game and play the first few turns. Should be able to
    # # cast Arcades on turn 3 and then draw a lot of cards
    #
    # game = GameState()
    # game.is_tracking_history = False
    # # hand
    # game.MoveZone(Cardboard(Decklist2.Plains), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Island), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Caryatid), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Blossoms), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.Arcades), ZONE.HAND)
    # # deck
    # for x in range(4):
    #     game.MoveZone(Cardboard(Decklist2.Roots), ZONE.DECK)
    # for x in range(4):
    #     game.MoveZone(Cardboard(Decklist2.Island), ZONE.DECK)
    #
    # tree = PlayTree.PlayTree(game, 5)
    # tree.PlayNextTurn()  # turn 2
    # tree.PlayNextTurn()  # turn 3
    # waystohaveArcades = 0
    # for n in tree.LatestNodes():
    #     if any([c.rules_text == Decklist2.Arcades for c in n.state.field]):
    #         # print(n.state,"\n")
    #         waystohaveArcades += 1
    # assert (waystohaveArcades == 2)  # use Roots OR Caryatid to cast on T3
    #
    # tree.PlayNextTurn()  # turn 4
    # assert (min([len(n.state.deck) for n in tree.LatestNodes()]) == 0)
    # for n in tree.LatestNodes():
    #     if len(n.state.deck) == 0:
    #         assert (len(n.state.hand) == 4)
    #         assert (n.state.pool == ManaHandler.ManaPool(""))
    #
    # print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))
    #
    # ###--------------------------------------------------------------------
    # print("Testing fetchlands")
    # start_clock = time.perf_counter()
    #
    # # make a game with some fetchable lands in deck and fetchlands in hand
    # game = GameState()
    # game.is_tracking_history = False
    # # deck
    # game.MoveZone(Cardboard(Decklist2.Plains), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Island), ZONE.DECK)
    # # hand
    # game.MoveZone(Cardboard(Decklist2.WindsweptHeath), ZONE.HAND)
    # game.MoveZone(Cardboard(Decklist2.WindsweptHeath), ZONE.HAND)
    #
    # # pre-shuffle check
    # assert (game.deck[0].rules_text == Decklist2.Plains)
    # assert (game.deck[-1].rules_text == Decklist2.Island)
    #
    # # play the fetch
    # universes = game.CastSpell(game.hand[0])
    # for g in universes:
    #     assert (len(g.deck) == 5)
    #     assert (len(g.hand) == 1)
    #     assert (len(g.grave) == 1)
    #     assert (g.life == 19)
    #     # print([str(c) for c in g.deck])
    # assert (len(universes) == 2)
    # assert (not universes[0].field[0].is_equiv_to(universes[1].field[0]))
    #
    # # MOVE the fetch into play instead. should put onto super_stack first
    # game2 = game.copy()
    # game2.MoveZone(game2.hand[0], ZONE.FIELD)
    # assert (game2.stack == [])
    # assert (len(game2.super_stack) == 1)
    # assert (len(game2.clear_super_stack()) == 2)  # same 2 as before
    #
    # # add two shocks to the deck.  should both be fetchable. I expect four
    # # fetchable targets and six total gamestates (due to shocked vs tapped)
    # game.MoveZone(Cardboard(Decklist2.HallowedFountain), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.TempleGarden), ZONE.DECK)
    #
    # # play the fetch
    # universes = game.CastSpell(game.hand[0])
    # landstrings = []
    # totallife = 0
    # for g in universes:
    #     assert (len(g.deck) == 7)
    #     assert (len(g.hand) == 1)
    #     assert (len(g.grave) == 1)
    #     assert (len(g.super_stack) == 0)
    #     assert (len(g.stack) == 0)
    #     landstrings.append(g.field[0].get_id())
    #     totallife += g.life
    # assert (len(universes) == 6)
    # assert (landstrings == ["LandPlains_2", "LandForest_2",
    #                         "LandHallowedFountain_T2",
    #                         "LandHallowedFountain_2",
    #                         "LandTempleGarden_T2", "LandTempleGarden_2"])
    # assert (totallife == (19 * 4) + (17 * 2))
    #
    # # what if deck has no valid targets?
    # gameE = GameState()
    # # deck
    # for i in range(10):
    #     gameE.MoveZone(Cardboard(Decklist2.Island), ZONE.DECK)
    # # hand
    # gameE.MoveZone(Cardboard(Decklist2.WindsweptHeath), ZONE.HAND)
    # universes = gameE.CastSpell(gameE.hand[0])
    # assert (len(universes) == 1)
    # assert (len(universes[0].deck) == 10)
    # assert (len(universes[0].hand) == 0)
    # assert (len(universes[0].grave) == 1)
    #
    # print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))
    #
    # ###--------------------------------------------------------------------
    # print("Testing Collected Company and simultaneous ETBs")
    # start_clock = time.perf_counter()
    #
    # game = GameState()
    # # deck of 6 cards
    # game.MoveZone(Cardboard(Decklist2.Caretaker), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Caretaker), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Axebane), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Battlement), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    # # put Collected Company directly onto the stack
    # game.MoveZone(Cardboard(Decklist2.Company), ZONE.STACK)
    # assert (len(game.super_stack) == 0)
    #
    # # resolve Collected Company
    # universes = game.resolve_top_of_stack()
    # assert (len(universes) == 4)
    # for u in universes:
    #     assert (len(u.deck) == 4)
    #     assert (len(u.field) == 2)
    #     assert (len(u.grave) == 1)
    #     if any([c.rules_text == Decklist2.Axebane for c in u.field]):
    #         assert (
    #             not any([c.rules_text == Decklist2.Axebane for c in u.deck]))
    #     if any([c.rules_text == Decklist2.Battlement for c in u.field]):
    #         assert (not any(
    #             [c.rules_text == Decklist2.Battlement for c in u.deck]))
    #     assert (not any(["land" in c.rules_text.keywords for c in u.field]))
    #
    # # deck of 6 forests on top, then 10 islands
    # gameF = GameState()
    # for _ in range(6):
    #     gameF.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    # for _ in range(10):
    #     gameF.MoveZone(Cardboard(Decklist2.Island), ZONE.DECK)
    # # should be forests on top
    # assert (all([c.rules_text == Decklist2.Forest for c in gameF.deck[:6]]))
    # gameF.MoveZone(Cardboard(Decklist2.Company), ZONE.STACK)
    # universes = gameF.resolve_top_of_stack()
    # assert (len(universes) == 1)
    # u = universes[0]
    # # now should be islands on top, forests on bottom
    # assert (all([c.rules_text == Decklist2.Island for c in u.deck[:10]]))
    # assert (all([c.rules_text == Decklist2.Forest for c in u.deck[-6:]]))
    # assert (len(u.field) == 0)
    # assert (len(u.grave) == 1)
    #
    # # deck of 5 forests on top, one Caretaker, then 10 islands
    # game1 = GameState()
    # for _ in range(5):
    #     game1.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    # game1.MoveZone(Cardboard(Decklist2.Caretaker), ZONE.DECK)
    # for _ in range(10):
    #     game1.MoveZone(Cardboard(Decklist2.Island), ZONE.DECK)
    # assert (len(game1.deck) == 16)
    # game1.MoveZone(Cardboard(Decklist2.Company), ZONE.STACK)
    # universes = game1.resolve_top_of_stack()
    # assert (len(universes) == 1)
    # u = universes[0]
    # # now should be islands on top, forests on bottom
    # assert (all([c.rules_text == Decklist2.Island for c in u.deck[:10]]))
    # assert (all([c.rules_text == Decklist2.Forest for c in u.deck[-5:]]))
    # assert (u.deck[-6].rules_text == Decklist2.Island)
    # assert (len(u.field) == 1)
    # assert (len(u.grave) == 1)
    #
    # # deck of only 4 cards total, all Caretakers
    # game4 = GameState()
    # for _ in range(4):
    #     game4.MoveZone(Cardboard(Decklist2.Caretaker), ZONE.DECK)
    # # should be forests on top
    # assert (len(game4.deck) == 4)
    # game4.MoveZone(Cardboard(Decklist2.Company), ZONE.STACK)
    # universes = game4.resolve_top_of_stack()
    # assert (len(universes) == 1)
    # u = universes[0]
    # assert (len(u.deck) == 2)
    # assert (len(u.field) == 2)
    # assert (len(u.grave) == 1)
    #
    # # Does Blossoms trigger correctly? start with 12 cards in deck
    # game = GameState()
    # game.MoveZone(Cardboard(Decklist2.Blossoms), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Omens), ZONE.DECK)
    # for _ in range(10):
    #     game.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    # # put Collected Company directly onto the stack
    # game.MoveZone(Cardboard(Decklist2.Company), ZONE.STACK)
    # universes = game.resolve_top_of_stack()
    # assert len(universes) == 2  # two draws could be on stack in either order
    # u0, u1 = universes
    # assert (u0 != u1)
    # while len(u0.stack) > 0:
    #     [u0] = u0.resolve_top_of_stack()
    # while len(u1.stack) > 0:
    #     [u1] = u1.resolve_top_of_stack()
    # assert (u0 == u1)
    # assert (len(u0.hand) == 2 and len(u0.deck) == 8)
    #
    # # Note: if I put two identical Blossoms into play simultaneously, I STILL
    # # will get two GameStates even though they are identical! And that's ok.
    # # it's not worth the effort to optimize this out, right now.
    # game = GameState()
    # game.MoveZone(Cardboard(Decklist2.Blossoms), ZONE.DECK)
    # game.MoveZone(Cardboard(Decklist2.Blossoms), ZONE.DECK)
    # for _ in range(10):
    #     game.MoveZone(Cardboard(Decklist2.Forest), ZONE.DECK)
    # # put Collected Company directly onto the stack
    # game.MoveZone(Cardboard(Decklist2.Company), ZONE.STACK)
    # universes = game.resolve_top_of_stack()
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
    #
    # ###--------------------------------------------------------------------
    #
    # print("\n\npasses all tests!")
