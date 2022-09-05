# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 22:15:57 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List

import Getters as Get
import Abilities
import Zone
from GameState import GameState
import ManaHandler
import Decklist
from Cardboard import Cardboard
from PlayTree import PlayTree
import Verbs
import Stack
import Match
import time
import RulesText
import Costs

if __name__ == "__main__":

    print("Basic structure: Cardboard, GameState, Getters,")
    print("    Matchers, Verbs, Triggers...")
    start_clock = time.perf_counter()


    class Vanil(RulesText.Creature):
        def __init__(self):
            super().__init__()
            self.name = "Vanilla"
            self.cost = Costs.Cost("1U")
            self.set_power_toughness(1, 2)


    class Choc(RulesText.Creature):
        def __init__(self):
            super().__init__()
            self.name = "Chocolate"
            self.cost = Costs.Cost("B")
            self.set_power_toughness(1, 1)


    vanil0 = Cardboard(Vanil())
    vanil1 = Cardboard(Vanil())
    assert vanil0 is not vanil1
    assert not (vanil0 == vanil1)
    assert not (vanil0.rules_text == vanil1.rules_text)
    assert vanil0.zone == vanil1.zone
    assert vanil0.zone is not vanil1.zone
    # try a basic copy
    vanil1A = vanil0.copy()
    assert vanil1A.rules_text is vanil0.rules_text  # rulestext is pointer
    assert vanil1A.is_equiv_to(vanil0)
    assert vanil1A is not vanil0

    # build boardstate
    choc0 = Cardboard(Choc())
    game1 = GameState(2)
    game1.give_to(vanil0, Zone.Field, 0)  # to player 0
    game1.give_to(choc0, Zone.Field, 0)  # to player 0
    game1.give_to(vanil1, Zone.Field, 1)  # to player 1
    assert game1.active.player_index == 0
    # check player0, confirm it has the correct everything
    assert len(game1.player_list[0].hand) == 0
    assert len(game1.player_list[0].grave) == 0
    assert len(game1.player_list[0].deck) == 0
    assert len(game1.player_list[0].field) == 2
    assert game1.player_list[0].field[0] is choc0
    assert game1.player_list[0].field[1] is vanil0
    assert choc0.zone.player == 0 and choc0.zone.location == 0
    assert vanil0.zone.player == 0 and vanil0.zone.location == 1
    assert choc0.summon_sick and vanil0.summon_sick
    assert not choc0.tapped and not vanil0.tapped
    # check player1, confirm it has the correct everything
    assert len(game1.player_list[1].hand) == 0
    assert len(game1.player_list[1].grave) == 0
    assert len(game1.player_list[1].deck) == 0
    assert len(game1.player_list[1].field) == 1
    assert game1.player_list[1].field[0] is vanil1
    assert vanil1.zone.player == 1 and vanil1.zone.location == 0

    # test that Zone is working the way I expect
    assert len(vanil0.zone.get(game1)) == 1  # because zone has location
    assert vanil0 in vanil0.zone.get(game1)
    assert vanil0 is vanil0.zone.get(game1)[0]
    assert Zone.Field(0).get(game1) is game1.player_list[0].field
    assert Zone.Grave(0).get(game1) is game1.player_list[0].grave
    assert len(Zone.Field(None).get(game1)) == 3
    try:
        Zone.Field(Get.Controllers()).get(game1)
        assert False
    except Zone.Zone.RelativeError:
        assert True

    # test some getters
    assert Match.Power("=", 1).match(vanil0, game1, 0, vanil0)
    assert Match.YouControl().match(vanil0, game1, 0, vanil0)
    assert not Match.YouControl().match(vanil1, game1, 0, vanil0)
    assert Match.OppControls().match(vanil1, game1, 0, vanil0)
    assert Zone.Field(Get.Controllers()
                      ).get_absolute_zones(game1, 1, vanil0)[0].player == 0
    assert Zone.Field(Get.Controllers()
                      ).get_absolute_zones(game1, 1, vanil1)[0].player == 1
    # test matchers and CardsFromZone
    assert Get.Count(Match.Toughness(">", 1), Zone.Field(0)
                     ).get(game1, 0, vanil0) == 1
    assert len(Get.AllWhich(Match.Toughness(">", 1)
                            ).pick(Get.CardsFrom(Zone.Field(0)),
                                   game1, 0, vanil0)[0]) == 1  # you=player1
    assert Get.AllWhich(Match.Toughness(">", 1)
                        ).pick(Get.CardsFrom(Zone.Field(0)),
                               game1, 0, vanil0)[0][0] is vanil0
    assert len(Get.AllWhich(Match.Toughness(">", 1)
                            ).pick(Get.CardsFrom(Zone.Field(0)),
                                   game1, 1, vanil0)) == 1  # still player0
    assert len(Get.AllWhich(Match.Toughness(">", 1)
                            ).pick(Get.CardsFrom(Zone.Field(None)),
                                   game1, 0, choc0)[0]) == 2  # all players
    assert len(Get.AllWhich(Match.Toughness(">", 1)
                            ).pick(Get.CardsFrom(Zone.Field(Get.You())),
                                   game1, 0, vanil0)[0]) == 1  # you=player0
    assert len(Get.AllWhich(Match.Toughness(">", 1)
                            ).pick(Get.CardsFrom(Zone.Field(Get.You())),
                                   game1, 1, choc0)[0]) == 1  # you=player1
    assert len(Get.AllWhich(Match.Toughness(">", 1)
                            ).pick(Get.CardsFrom(Zone.Field(Get.You())),
                                   game1, 0, vanil0)[0]) == 1  # you=player0
    assert len(Get.AllWhich(Match.YouControl()
                            ).pick(Get.CardsFrom(Zone.Field(Get.You())),
                                   game1, 0, vanil0)[0]) == 2  # you=player0
    assert len(Get.AllWhich(Match.YouControl()
                            ).pick(Get.CardsFrom(Zone.Field(Get.You())),
                                   game1, 0, choc0)[0]) == 2  # you=player0
    assert len(Get.AllWhich(Match.YouControl()
                            ).pick(Get.CardsFrom(Zone.Field(Get.You())),
                                   game1, 1, choc0)[0]) == 1  # you=player1
    assert len(
        Get.AllWhich(
            Match.YouControl()
        ).pick(Get.CardsFrom(Zone.Field(Get.Controllers())),
               game1, 0, choc0)[0]) == 2  # controller=0
    assert len(
        Get.AllWhich(
            Match.CardType(RulesText.Creature)
        ).pick(Get.CardsFrom(Zone.Field(None)),
               game1, 1, choc0)[0]) == 3  # all players

    # test copying
    gameB, [chocB] = game1.copy_and_track([choc0])
    assert gameB == game1
    assert gameB is not game1
    assert gameB.active.player_index == 0
    # check player0, confirm it has the correct everything
    assert len(gameB.player_list[0].hand) == 0
    assert len(gameB.player_list[0].grave) == 0
    assert len(gameB.player_list[0].deck) == 0
    assert len(gameB.player_list[0].field) == 2
    assert gameB.player_list[0].field[0] is not choc0
    assert gameB.player_list[0].field[0].is_equiv_to(choc0)
    assert gameB.player_list[0].field[1].is_equiv_to(vanil0)
    assert [c.zone.location for c in gameB.player_list[0].field] == [0, 1]
    assert all([c.summon_sick for c in gameB.player_list[0].field])
    assert not any([c.tapped for c in gameB.player_list[0].field])
    # check player1, confirm it has the correct everything
    assert len(gameB.player_list[1].hand) == 0
    assert len(gameB.player_list[1].grave) == 0
    assert len(gameB.player_list[1].deck) == 0
    assert len(gameB.player_list[1].field) == 1
    assert gameB.player_list[1].field[0] is not vanil1
    assert gameB.player_list[1].field[0].is_equiv_to(vanil1)
    # make sure chocB copied correctly
    assert chocB is not choc0
    assert chocB.is_equiv_to(choc0)
    assert chocB is chocB.zone.get(gameB)[0]
    assert chocB is gameB.player_list[0].field[0]
    assert choc0 is chocB.zone.get(game1)[0]
    assert chocB is choc0.zone.get(gameB)[0]


    # -----------------------------------------------------------------------

    # define two cards which can "listen" for triggers. One cares about
    # tapping creatures, the other about moving them from field


    class WeirdOrb(RulesText.Creature):
        def __init__(self):
            super().__init__()
            self.name = "WeirdOrb"
            self.cost = Costs.Cost("5")
            self.set_power_toughness(8, 8)
            self.add_triggered("Orb see tap adds R",
                               Abilities.TriggerWhenVerb(
                                   Verbs.Tap,
                                   Match.ControllerControls()
                               ),
                               Verbs.AddMana("R")
                               )


    class BloodArtist(RulesText.Creature):
        def __init__(self):
            super().__init__()
            self.name = "BloodArtist"
            self.cost = Costs.Cost("1B")
            self.set_power_toughness(0, 1)
            self.add_triggered("Artist drains when dies",
                               Abilities.TriggerWhenMove(
                                   Match.CardType(RulesText.Creature),
                                   Zone.Field(None),
                                   Zone.Grave(None)
                               ),
                               Verbs.GainLife(1)
                               + Verbs.LoseLife(1).on(Get.All(),
                                                      Get.Opponents())
                               )


    # give both of these creatures to player1
    orb1 = Cardboard(WeirdOrb())
    game1.give_to(orb1, Zone.Field, 1)
    artist1 = Cardboard(BloodArtist())
    assert len(artist1.rules_text.trig_verb[0].effect.sub_verbs) == 2
    game1.give_to(artist1, Zone.Field, 1)
    assert len(game1.player_list[1].field) == 3
    assert artist1.zone.location == 0  # BloodArtist comes 1st alphabetically
    # gamestate right now for game1:
    # Player0: Chocolate, Vanilla.    Player1: BloodArtist, Vanilla, WeirdOrb

    # copy the game and start doing verbs and see what happens!
    gameC = game1.copy()
    chocC = gameC.player_list[0].field[0]
    assert chocC.is_equiv_to(choc0)
    tapper = Verbs.Tap()
    assert not tapper.can_be_done(gameC)  # missing important parameters
    [tapper2] = tapper.populate_options(gameC, 0, chocC, None)
    # check that populate didn't mutate original tapper object
    assert not tapper.can_be_done(gameC)
    assert tapper is not tapper2
    assert tapper2.can_be_done(gameC)
    # now actually run the verb. Tap mutates.
    [(game_tap, verb_tap, list_tap)] = tapper2.do_it(gameC)
    assert list_tap == []
    assert verb_tap is tapper2  # output may be new, or not. but never mutated.
    assert verb_tap is not tapper
    assert game_tap is gameC
    assert chocC.tapped
    assert sum([c.tapped for c in Zone.Field(None).get(gameC)]) == 1
    assert len(gameC.stack) == 0  # no trigger because Orb only sees OWN
    assert len(gameC.super_stack) == 0  # creatures, and this was player0's.
    # even if player1 taps player0's creature, Orb won't see it
    vanil0C = gameC.player_list[0].field[1]
    tapper = Verbs.Tap().populate_options(gameC, 1, vanil0C, None)[0]
    tapper.do_it(gameC)
    assert sum([c.tapped for c in Zone.Field(None).get(gameC)]) == 2
    assert len(gameC.stack) == 0  # no trigger because Orb only sees OWN
    assert len(gameC.super_stack) == 0  # creatures, and this was player0's.
    # now player0 tries to tap one of player1's creatures. should trigger Orb,
    # even though it's player0 doing the action.
    vanil1C = gameC.player_list[1].field[1]
    Verbs.Tap().populate_options(gameC, 0, vanil1C, None)[0].do_it(gameC)
    assert sum([c.tapped for c in Zone.Field(None).get(gameC)]) == 3
    game_list = gameC.clear_super_stack()
    assert len(game_list) == 1  # only one way to clear the superstack
    gameD = game_list[0]
    # note: mana only bypasses the stack if the ability was created using a
    # the appropriate verb. This was just me calling Tap on stuff.
    game_list = gameD.resolve_top_of_stack()
    assert len(game_list) == 1  # only one way to clear the stack here
    gameE = game_list[0]
    assert [len(g.super_stack) for g in [gameC, gameD, gameE]] == [1, 0, 0]
    assert [len(g.stack) for g in [gameC, gameD, gameE]] == [0, 1, 0]
    assert [str(g.player_list[1].pool)
            for g in [gameC, gameD, gameE]] == ["", "", "R"]
    assert all([sum([c.tapped for c in Zone.Field(None).get(g)]) == 3
                for g in [gameC, gameD, gameE]])
    # going to kill player0's chocolate
    chocE = gameE.player_list[0].field[0]
    assert chocE.player_index == 0
    artist = gameE.player_list[1].field[0]
    s = artist.rules_text.trig_verb[0].trigger
    assert s.pattern_for_subject.match(chocE, gameE, 0, artist)
    [destroyer] = Verbs.Destroy().populate_options(gameE, 0, chocE, None)
    assert destroyer.can_be_done(gameE)
    assert destroyer.subject is chocE
    destroyer.do_it(gameE)
    assert not chocE.tapped  # not tapped, because dead and in grave
    assert len(Zone.Field(None).get(gameE)) == 4
    assert len(gameE.super_stack) == 1
    game_list = gameE.clear_super_stack()
    assert len(game_list) == 1
    gameF = game_list[0]
    assert len(gameF.stack) == 1  # blood artist trigger
    game_list = gameF.resolve_top_of_stack()
    assert len(game_list) == 1
    gameG = game_list[0]
    assert [len(g.super_stack) for g in [gameE, gameF, gameG]] == [1, 0, 0]
    assert [len(g.stack) for g in [gameE, gameF, gameG]] == [0, 1, 0]
    assert [g.player_list[0].life
            for g in [gameE, gameF, gameG]] == [20, 20, 19]
    assert [g.player_list[1].life
            for g in [gameE, gameF, gameG]] == [20, 20, 21]
    # try to destroy the world!
    wrath = Verbs.Defer(
        Verbs.Destroy().on(Get.AllWhich(Match.CardType(RulesText.Creature)),
                           Get.CardsFrom(Zone.Field(None))))
    assert wrath.copies
    [wrath] = wrath.populate_options(gameG, 0, None, None)
    gameH = wrath.do_it(gameG)[0][0]
    assert len(gameH.super_stack) == 4
    assert len(Zone.Field(None).get(gameH)) == 0
    assert len(Zone.Grave(None).get(gameH)) == 5
    outcomes = gameH.clear_super_stack()
    assert len(outcomes) == 4 * 3 * 2 * 1  # actually distinct on the stack!
    assert all([len(g.stack) == 4 and len(g.super_stack) == 0
                for g in outcomes])
    # trigger tracks "cause" on stack, so these are distinct!
    assert len(set(outcomes)) == 4 * 3 * 2 * 1
    final_games = set()
    for f_game in outcomes:
        while len(f_game.stack) > 0:
            next_steps = f_game.resolve_top_of_stack()
            assert len(next_steps) == 1
            f_game = next_steps[0]
        assert f_game.player_list[0].life == 19 - 4
        assert f_game.player_list[1].life == 21 + 4
        assert len(f_game.stack) == 0
        assert len(f_game.super_stack) == 0
        assert len(Zone.Field(None).get(f_game)) == 0
        assert len(Zone.Grave(None).get(f_game)) == 5
        final_games.add(f_game)
    assert len(final_games) == 1  # after triggers resolve, all identical

    # try to pass turn
    assert game1.active_player_index == 0
    assert game1.priority_player_index == 0
    assert choc0 in game1.active.field
    assert choc0 in game1.player_list[0].field
    game1.pass_turn()
    assert game1.active_player_index == 1
    assert game1.priority_player_index == 1
    assert choc0 not in game1.active.field  # because active has changed
    assert choc0 in game1.player_list[0].field  # but choc0 hasn't moved


    class Jumper(RulesText.Creature):
        # some additional tests for Verbs.MoveToZone in particular
        def __init__(self):
            super().__init__()
            self.name = "Jumper"
            self.cost = Costs.Cost("BBB")
            self.set_power_toughness(7, 1)
            self.add_activated("Jumper move to hand",
                               Costs.Cost("2"),
                               Verbs.MoveToZone(Zone.Hand(Get.Controllers())))

    gameJ1 = GameState()
    gameJ1.give_to(Cardboard(Jumper()), Zone.Field, 0)
    gameJ1.active.pool.add_mana("WW")  # to pay for ability
    gameJ2 = gameJ1.copy()
    j1 = gameJ1.active.field[0]
    j2 = gameJ2.active.field[0]
    assert j1.is_equiv_to(j2)
    assert j1 is not j2
    # COPYING DOESN'T COPY THE RULESTEXT OR ABILITY. ALL POINTERS TO SAME OBJ.
    assert j1.rules_text is j2.rules_text
    assert j1.get_activated()[0] is j2.get_activated()[0]
    assert (j1.get_activated()[0].effect.destination
            is j2.get_activated()[0].effect.destination)
    assert isinstance(j1.get_activated()[0].effect.destination, Zone.Hand)
    assert j1.get_activated()[0].effect.origin is None
    activs = gameJ1.active.get_valid_activations()
    assert len(activs) == 1
    assert activs[0].can_be_done(gameJ1)
    universes = activs[0].do_it(gameJ1)
    assert len(universes) == 1
    gameJ3 = universes[0][0]
    universes = gameJ3.resolve_top_of_stack()
    assert len(universes) == 1
    gameJ4 = universes[0]
    j4 = gameJ4.active.hand[0]
    assert (j1.get_activated()[0].effect.destination
            is j4.get_activated()[0].effect.destination)
    # WHEN MOVE, ZONE OBJECT IS STILL NOT MUTATED. GOOD.
    assert not isinstance(j1.get_activated()[0].effect.origin, Zone.Field)
    assert j1.get_activated()[0].effect.origin is None
    assert not isinstance(j4.get_activated()[0].effect.origin, Zone.Field)
    assert j4.get_activated()[0].effect.origin is None

    # let's do a full copy test, since copying is rather critical
    game1 = GameState()
    # caryatid in play
    Verbs.MoveToZone.move(game1, Cardboard(Decklist.Caryatid()), Zone.Field(0))
    assert game1.active.field[0].zone.player == 0
    assert game1.active.field[0].zone.location == 0

    # Wall of Roots currently on the stack
    roots_on_stack = Cardboard(Decklist.Roots())
    roots_on_stack.zone = Zone.Stack()
    stack_cardboard = Stack.StackCardboard(0, roots_on_stack, None, None)
    roots_on_stack.zone.location = 0
    [caster] = Verbs.PlayCardboard().populate_options(game1, 0,
                                                      roots_on_stack, None,
                                                      stack_cardboard)
    game1.player_list[0].pool.add_mana("GG")
    assert caster.can_be_done(game1)
    game1 = caster.do_it(game1)[0][0]
    assert len(game1.stack) == 1
    assert game1.stack[0].do_effect is None
    assert game1.stack[0].obj is not roots_on_stack
    assert game1.stack[0].obj.is_equiv_to(roots_on_stack)
    assert game1.stack[0].zone.location == 0
    assert game1.stack[0].zone.player is None  # stack has no player
    assert game1.stack[0].obj.zone.location == 0  # card is on stack too
    assert game1.stack[0].obj.zone.player is None  # stack has no player

    # make ability on stack pointing at Roots on stack. "from" Caryatid.
    affecter = Verbs.AffectStack().on(Get.All(), Get.StackList(), False)
    fake_ability = Abilities.ActivatedAbility("fake", Costs.Cost(),
                                              affecter)
    [caster] = fake_ability.valid_casters(game1, 0, game1.active.field[0])
    assert caster.can_be_done(game1)
    game1 = caster.do_it(game1)[0][0]
    assert len(game1.stack) == 2
    assert game1.stack[1].obj.get_id() == fake_ability.get_id()
    assert game1.stack[1].obj is not fake_ability  # copy happened in between
    assert game1.stack[1].zone.player is None  # stack has no player
    assert game1.stack[1].zone.location == 1
    assert isinstance(game1.stack[1].do_effect, Verbs.MultiVerb)
    assert game1.stack[1].do_effect.player == 0
    assert game1.stack[1].do_effect.source is game1.active.field[0]
    assert game1.stack[1].do_effect.subject is None  # because multi-verb
    subverb = game1.stack[1].do_effect.sub_verbs[0]
    assert isinstance(subverb, Verbs.AffectStack)
    assert subverb.player == 0
    assert subverb.source is game1.active.field[0]
    assert subverb.subject is game1.stack[0]

    # test game has: caryatid in play, roots on stack, and an ability pointing
    # at the roots on the stack coming from the caryatid in play.
    obj1 = game1.stack[-1]
    cary1 = game1.active.field[0]
    # try a copy_and_track
    game2, [cary2, obj2] = game1.copy_and_track([cary1, obj1])
    assert game2 == game1
    assert cary2 is not cary1
    assert cary2.is_equiv_to(cary1)
    assert cary2.copy(game1) is cary1
    assert cary1 in cary1.zone.get(game1)
    assert cary2 in cary2.zone.get(game2)
    assert cary2 not in cary2.zone.get(game1)

    assert obj2 is not obj1
    assert obj2.is_equiv_to(obj1)
    assert obj2.copy(game1) is obj1
    assert obj2 is game2.stack[1]
    assert obj2.do_effect is not obj1.do_effect
    assert obj2.do_effect.source is game2.active.field[0]
    assert obj2.do_effect.source is cary2
    assert obj2.do_effect.source is not obj1.do_effect.source
    assert obj2.do_effect.player == 0
    assert obj2.do_effect.subject is None  # as MultiVerb subject always is
    subverb2 = obj2.do_effect.sub_verbs[0]
    assert isinstance(subverb2, Verbs.AffectStack)
    assert subverb2.player == 0
    assert subverb2.source is game2.active.field[0]
    assert subverb2.subject is game2.stack[0]
    assert game1.stack[1].do_effect.sub_verbs[0].subject is game1.stack[0]
    assert game1.stack[1].do_effect.sub_verbs[0].subject is not game2.stack[0]
    assert game2.stack[1].do_effect.sub_verbs[0].subject is not game1.stack[0]
    assert game2.stack[1].do_effect.sub_verbs[0].subject is game2.stack[0]

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing Wall of Roots and basic GameState...")
    start_clock = time.perf_counter()

    # start new game, try to cast some Walls of Roots
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
        game_orig.give_to(Cardboard(Decklist.Roots()), Zone.Hand)
    assert (len(game_orig.active.hand) == 4)
    assert (len(game_orig.active.field) == 0)

    # check the abilities of Wall of Roots in hand. it has 1 but can't be used.
    roots = game_orig.active.hand[0]
    assert len(roots.get_activated()) == 1
    roots_abil = roots.get_activated()[0]
    assert len(roots_abil.valid_casters(game_orig, 0, roots)) == 0

    # move a Wall of Roots to field and try again
    game_orig.give_to(game_orig.active.hand[0], Zone.Field)
    assert len(game_orig.active.hand) == 3
    assert len(game_orig.active.field) == 1
    roots = game_orig.active.field[0]
    assert len(roots.get_activated()) == 1
    assert len(roots.counters) == 0  # no counters on it yet
    roots_abil = roots.get_activated()[0]
    valid = roots_abil.valid_casters(game_orig, 0, roots)
    assert len(valid) == 1

    # make sure the cost can actually be paid
    cost_game = game_orig.copy()
    cost_roots = cost_game.active.field[0]
    plans = roots_abil.cost.get_payment_plans(cost_game, 0, cost_roots, None)
    assert len(plans) == 1 and plans[0] is not None
    assert plans[0].can_be_done(cost_game)
    assert not plans[0].copies  # will mutate, not copy, when executed
    tuple_list = plans[0].do_it(cost_game)
    assert len(tuple_list) == 1
    assert cost_game is tuple_list[0][0]  # mutated so output is original obj.
    assert len(cost_roots.counters) == 2
    for value in cost_roots.counters:
        assert "-0/-1" == value or "@" in value
    # should no longer be possible to do
    plans = roots_abil.cost.get_payment_plans(cost_game, 0, cost_roots, None)
    assert plans == []
    assert len(cost_game.active.get_valid_activations()) == 0

    # untap to reset things, then try to activate the ability "properly"
    game_orig.pass_turn()  # increments turn
    game_orig.step_untap()
    casters = game_orig.active.get_valid_activations()
    assert len(casters) == 1
    game_list = casters[0].do_it(game_orig)
    assert len(game_list) == 1
    activ_game = game_list[0][0]
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
    assert ([o is castable.subject.obj for o in copygame.active.hand]
            == [True, False, False])
    [(copygame3, _, _)] = castable.do_it(copygame)
    assert (copygame3.active.pool == ManaHandler.ManaPool(""))  # no mana left
    assert (len(copygame3.stack) == 1)  # one spell on the stack
    assert (len(copygame3.active.hand) == 2)  # two cards in hand
    assert (len(copygame3.active.field) == 1)  # one card in play
    # make sure that all the copying worked out correctly
    assert copygame3 is not copygame
    for c in copygame.active.hand:
        assert c is not copygame3.stack[0].obj
        for c3 in copygame3.active.hand:
            assert c is not c3
    further_copy = copygame3.copy()
    assert further_copy.stack[0] is not copygame3.stack[0]
    assert further_copy.stack[0].obj is not copygame3.stack[0].obj

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

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing Sylvan Caryatid, Untap & Upkeep, GameState history...")
    start_clock = time.perf_counter()

    # add a caryatid to the all-roots game
    carygame1, _ = game_orig.copy_and_track([])
    carygame1.is_tracking_history = True  # start tracking
    carygame1.give_to(Cardboard(Decklist.Caryatid()), Zone.Field)
    # should only see one valid ability to activate, since Caryatid not hasty
    assert (len(carygame1.active.get_valid_activations()) == 1)
    assert (len(carygame1.active.get_valid_castables()) == 0)  # no castables

    # try to untap and upkeep to get rid of summonning sickness
    carygame1.pass_turn()  # increments turn
    carygame1.step_untap()
    carygame1.step_upkeep()
    assert len(carygame1.active.get_valid_castables()) == 0  # no castables
    gameN = carygame1
    options: List[Stack.StackObject] = (gameN.active.get_valid_activations()
                                        + gameN.active.get_valid_castables())
    assert len(options) == 2
    # as long as there are things to do, do them! auto-choose 1st option
    while len(options) > 0:
        gameN = options[0].put_on_stack(gameN)[0]
        while len(gameN.stack) > 0:
            gameN = gameN.resolve_top_of_stack()[0]
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
    assert len(tree1.get_finished()) == 0
    # try untap and upkeep. expect game_over because draw from empty deck
    tree1.beginning_phase_for_all_valid_states()
    assert len(tree1.get_active()) == 0
    assert len(tree1.get_intermediate()) == 1  # new turn so only 1 this turn.
    assert len(tree1.get_finished()) == 1
    assert tree1.get_finished()[0].game_over
    assert tree1.get_finished()[0].active.victory_status == "L"

    tree_game = carygame1.copy()
    tree_game.active.turn_count = 1  # to simplify, roll back to earlier turn
    # HAND: Roots, Roots, Roots
    # FIELD: Caryatid, Roots
    # Life: 20 vs 20, Deck: 0, Mana: ()
    tree_game.is_tracking_history = True
    for x in range(5):
        tree_game.give_to(Cardboard(Decklist.Caryatid()), Zone.DeckTop)
    tree2 = PlayTree([tree_game], 5)
    assert len(tree2.get_active()) == 1
    assert len(tree2.get_intermediate()) == 1
    # assert len(tree2.final_states) == 0
    assert tree2.traverse_counter == 1
    assert all([len(gs.active.deck) == 5 for gs in tree2.get_active()])
    assert all([len(gs.active.hand) == 3 for gs in tree2.get_active()])

    tree2.beginning_phase_for_all_valid_states()
    # noinspection PyProtectedMember
    assert len(tree2._active_states) == 3  # turns 0, 1, 2
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
    game.give_to(Cardboard(Decklist.Forest()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Plains()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Island()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Swamp()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Mountain()), Zone.Hand)
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
    game.give_to(Cardboard(Decklist.Forest()), Zone.Hand)
    game.give_to(Cardboard(Decklist.HallowedFountain()), Zone.Hand)
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
    game.give_to(Cardboard(Decklist.Forest()), Zone.DeckTop)
    game.give_to(Cardboard(Decklist.Forest()), Zone.DeckTop)
    game.give_to(Cardboard(Decklist.Plains()), Zone.DeckTop)
    game.give_to(Cardboard(Decklist.Island()), Zone.DeckTop)
    game.give_to(Cardboard(Decklist.Swamp()), Zone.DeckTop)
    game.give_to(Cardboard(Decklist.HallowedFountain()), Zone.DeckTop)
    game.give_to(Cardboard(Decklist.BreedingPool()), Zone.DeckTop)
    game.give_to(Cardboard(Decklist.MistyRainforest()), Zone.Hand)
    assert len(game.active.get_valid_activations()) == 0
    assert len(game.active.get_valid_castables()) == 1  # play fetch
    matcher = Match.CardType(Decklist.Forest) | Match.CardType(Decklist.Island)
    assert len([c for c in game.active.deck if
                matcher.match(c, game, player, game.active.hand[0])]) == 5

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
    game.give_to(Cardboard(Decklist.Island()), Zone.DeckTop)
    game.give_to(Cardboard(Decklist.Roots()), Zone.DeckTop)
    game.give_to(Cardboard(Decklist.Swamp()), Zone.DeckTop)
    game.give_to(Cardboard(Decklist.WindsweptHeath()), Zone.Hand)
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
    game.give_to(Cardboard(Decklist.WindsweptHeath()), Zone.Hand)
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
    game.give_to(Cardboard(Decklist.Plains()), Zone.Field)
    # hand
    game.give_to(Cardboard(Decklist.HallowedFountain()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Forest()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Roots()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Caryatid()), Zone.Hand)

    # try to copy, make sure equality holds
    cp = game.copy()
    assert cp == game
    assert cp is not game

    # add this forest to one but not the other
    forest = Cardboard(Decklist.Forest())
    game.give_to(forest, Zone.Field)
    assert (game != cp)
    # add a copy of the forst to the other
    forest2 = forest.copy()
    forest2.zone = Zone.Unknown()
    cp.give_to(forest2, Zone.Field)
    # Cardboard uses "is" for eq  (or else "in list" breaks)
    assert forest != forest2
    assert forest is not forest2
    assert (game == cp)
    # tap both of these forests for mana
    obj = forest.get_activated()[0].valid_stack_objects(game, 0, forest)[0]
    cp3 = obj.put_on_stack(game)[0]
    assert (game != cp3)
    assert (cp != cp3)
    obj2 = forest2.get_activated()[0].valid_stack_objects(cp, 0, forest2)[0]
    cp4 = obj2.put_on_stack(cp)[0]
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
    game1.give_to(Cardboard(Decklist.Forest()), Zone.Hand)
    game1.give_to(Cardboard(Decklist.Plains()), Zone.Hand)
    game2 = game1.copy()
    # game 1: [0] into play, then the other
    mover = Verbs.MoveToZone(Zone.Field(0))

    game1A = mover.replace_subject(game1.active.field[0]).do_it(game1)[0][0]
    game1B = mover.replace_subject(game1A.active.field[0]).do_it(game1A)[0][0]
    # game 2: [1] into play, then the other
    game2A = mover.replace_subject(game2.active.field[1]).do_it(game2)[0][0]
    game2B = mover.replace_subject(game2A.active.field[0]).do_it(game2A)[0][0]
    assert (game1B == game2B)

    # but they would NOT be equivalent if I untapped between plays, since
    # all cards (including lands!) mark summoning sickness
    game1 = GameState(1)
    game1.give_to(Cardboard(Decklist.Forest()), Zone.Hand)
    game1.give_to(Cardboard(Decklist.Plains()), Zone.Hand)
    game2 = game1.copy()
    # game 1: [0] into play, then the other
    mover = Verbs.MoveToZone(Zone.Field(0))
    game1A = mover.replace_subject(game1.active.field[0]).do_it(game1)[0][0]
    game1A.pass_turn()
    game1A.step_untap()
    game1B = mover.replace_subject(game1A.active.field[0]).do_it(game1A)[0][0]
    # game 2: [1] into play, then the other
    game2A = mover.replace_subject(game2.active.field[1]).do_it(game2)[0][0]
    game2A.pass_turn()
    game2A.step_untap()
    game2B = mover.replace_subject(game2A.active.field[0]).do_it(game2A)[0][0]
    assert (game1B != game2B)
    # if untap both, then should be equivalent again
    game1B.pass_turn()
    game1B.step_untap()
    game2B.pass_turn()
    game2B.step_untap()
    assert (game1B == game2B)

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing Caretakers, Axebane, Battlement...")
    start_clock = time.perf_counter()

    game = GameState(1)
    game.give_to(Cardboard(Decklist.Caretaker()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Caretaker()), Zone.Hand)
    game.give_to(game.active.hand[0], Zone.Field)
    assert (len(game.super_stack) == 0)  # nothing triggers off of this move
    assert game.active.field[0].summon_sick
    assert len(game.active.get_valid_activations()) == 0
    # what if I give the caretaker something to tap?
    caryatid = Cardboard(Decklist.Caryatid())
    game.give_to(caryatid, Zone.Field)
    # no, caretaker is still summon_sick. good.
    assert len(game.active.get_valid_activations()) == 0
    game.active.field.remove(caryatid)

    game.pass_turn()
    game.step_untap()
    assert not game.active.field[0].summon_sick
    assert (len(game.active.get_valid_activations()) == 0)  # nothing to tap

    # give it something to tap
    caryatid.zone = Zone.Unknown()
    game.give_to(caryatid, Zone.Field)
    assert len(game.active.field) == 2
    assert len(game.active.get_valid_activations()) == 1
    activ = game.active.get_valid_activations()[0]  # for debug
    tree = PlayTree([game], 2)
    tree.main_phase_for_all_active_states()
    [univ1] = tree.get_states_no_options()
    assert len(univ1.active.hand) == 0  # used mana to cast 2nd Caretaker
    assert len(univ1.active.field) == 3
    assert univ1.active.pool == ManaHandler.ManaPool("")
    assert all([c.tapped or c.summon_sick for c in univ1.active.field])

    # Rewind to before casting 2nd Caretaker. Give 1st TWO things to tap.
    game.give_to(game.active.hand[0], Zone.Field)
    # only one ability, but two _options to activate it
    stack_abilities = game.active.get_valid_activations()
    assert len(stack_abilities) == 2
    assert stack_abilities[0].player_index == stack_abilities[1].player_index
    assert stack_abilities[0].source_card is stack_abilities[1].source_card
    assert stack_abilities[0].obj is stack_abilities[1].obj
    assert stack_abilities[0].choices != stack_abilities[1].choices
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
    game3.pass_turn()
    game3.step_untap()
    # 2 Caretakers plus Caryatid in play. 5 possibilities. But Caretakers are
    # equivalent so we only see 3 _options. Good.
    game3_abils = game3.active.get_valid_activations()
    assert len(game3_abils) == 3
    care3_abils = [obj for obj in game3_abils
                   if obj.source_card.name == "Caretaker"]
    universes = []
    for stack_ability in care3_abils:
        for g in stack_ability.put_on_stack(game3):
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
    game6.give_to(axe, Zone.Field)
    game6.give_to(battle, Zone.Field)
    assert len(game6.active.get_valid_activations()) == 0  # still summon_sick
    game6.pass_turn()  # increments turn
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
    assert len(tree6.get_states_no_options()) == 1 + 1 + 2 + 2 + 1
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
    game.give_to(Cardboard(Decklist.Forest()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Forest()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Forest()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Roots()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Caretaker()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Battlement()), Zone.Hand)
    # deck
    for x in range(10):
        game.give_to(Cardboard(Decklist.Forest()), Zone.DeckTop)
    # tree. Turn 1.
    tree = PlayTree([game], 5)
    tree.main_phase_for_all_active_states(0)
    # start, Forest, tap, Caretaker, resolve
    assert len(tree.get_intermediate(0)) == 5
    assert len(tree.get_states_no_options(0)) == 1
    assert tree.traverse_counter == 5

    # Turn 2.
    tree.beginning_phase_for_all_valid_states()
    assert len(tree.get_active(1)) == 3  # played nothing, forest, or caretaker
    tree.main_phase_for_all_active_states(1)
    assert len(tree.get_intermediate(1)) == 42  # 53
    assert len(tree.get_states_no_options(1)) == 6  # 7
    assert tree.traverse_counter == 59  # 74

    # Turn 3.
    tree.beginning_phase_for_all_valid_states()
    assert len(tree.get_active(2)) == 12
    tree.main_phase_for_all_active_states(2)
    print("      ...done running, %0.2f sec. (~0.63 2022-07-22)"
          % (time.perf_counter() - start_clock))
    intermed = tree.get_intermediate(2)
    no_opts = tree.get_states_no_options(2)
    assert len(intermed) == 980  # 1638
    assert len(intermed) == len(set(intermed))
    assert len(no_opts) == 30  # 62
    assert tree.traverse_counter == 2338  # 3716
    assert max([g.active.pool.cmc() for g in no_opts]) == 8
    print("      ...done checking, %0.2f sec. (~0.70 2022-07-22)"
          % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing Wall of Blossoms, Arcades, and ETBs")
    start_clock = time.perf_counter()

    game = GameState(1)
    game.is_tracking_history = False
    # field
    game.give_to(Cardboard(Decklist.Plains()), Zone.Field)
    # hand
    game.give_to(Cardboard(Decklist.Blossoms()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Blossoms()), Zone.Hand)
    game.give_to(Cardboard(Decklist.Forest()), Zone.Hand)
    # deck
    for x in range(10):
        game.give_to(Cardboard(Decklist.Island()), Zone.DeckTop)

    tree = PlayTree([game], 5)
    # only option is play Forest, play Blossoms, draw Island
    tree.main_phase_for_all_active_states()
    assert len(tree.get_states_no_options()) == 1
    [final] = tree.get_states_no_options()
    assert len(final.active.hand) == 2
    assert len(final.active.field) == 3
    assert len(final.active.deck) == 9
    assert any([c.has_type(Decklist.Island) for c in final.active.hand])
    assert not any([c.has_type(Decklist.Island) for c in final.active.field])

    # play next turn: draw Island, play Island, play Blossoms, draw Island
    tree2 = PlayTree([final], 5)
    tree2.beginning_phase_for_all_valid_states()
    tree2.main_phase_for_all_active_states()
    assert len(tree2.get_states_no_options()) == 2  # floating W or U
    [final2, _] = tree2.get_states_no_options()
    assert len(final2.active.hand) == 2
    assert len(final2.active.field) == 5
    assert len(final2.active.deck) == 7
    assert (any([c.has_type(Decklist.Island) for c in final2.active.hand]))
    assert (any([c.has_type(Decklist.Island) for c in final2.active.field]))

    # cast a Caryatid to be sure I didn't make ALL defenders draw on etb
    final2.give_to(Cardboard(Decklist.Caryatid()), Zone.Hand)
    tree3 = PlayTree([final2], 5)
    tree3.beginning_phase_for_all_valid_states()
    tree3.main_phase_for_all_active_states()
    for g in tree3.get_states_no_options():
        assert len(g.active.hand) == 2
        assert len(g.active.field) == 7
        assert len(g.active.deck) == 6

    # but what if there was an Arcades in play?
    gameA = GameState(1)
    # deck
    for x in range(10):
        gameA.give_to(Cardboard(Decklist.Island()), Zone.DeckTop)
    gameA.give_to(Cardboard(Decklist.Arcades()), Zone.Field)
    assert (len(gameA.super_stack) == 0)  # Arcades doesn't trigger itself
    # add Blossoms to field and hopefully draw 2
    gameA.give_to(Cardboard(Decklist.Blossoms()), Zone.Field)
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
    assert len(gameA.active.hand) == 2
    assert len(gameA.active.deck) == 8
    # now let's try to add a Caryatid to field and hopefully draw 1
    gameA.give_to(Cardboard(Decklist.Caryatid()), Zone.Field)
    assert len(gameA.super_stack) == 1
    assert len(gameA.active.hand) == 2  # haven't draw or put triggers on stack
    assert len(gameA.active.deck) == 8  # haven't draw or put triggers on stack
    [gameA] = gameA.clear_super_stack()
    while len(gameA.stack) > 0:
        universes = gameA.resolve_top_of_stack()
        assert (len(universes) == 1)
        gameA = universes[0]
    # should have drawn 2 cards
    assert (len(gameA.active.hand) == 3)
    assert (len(gameA.active.deck) == 7)

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("Testing Collected Company and simultaneous ETBs")
    start_clock = time.perf_counter()


    def cast_and_resolve_company(state):
        # cast Collected Company
        state.active.pool.add_mana("GGGG")
        state.give_to(Cardboard(Decklist.Company()), Zone.Hand, 0)
        castables = state.active.get_valid_castables()
        assert len(castables) == 1
        # Defer tracks cause, which is None since this is a card being cast.
        assert castables[0].choices == [None]
        [on_stack] = castables[0].put_on_stack(state)
        assert len(on_stack.super_stack) == 0
        assert len(on_stack.stack) == 1
        return on_stack.resolve_top_of_stack()


    game = GameState()
    # deck of 6 cards
    game.give_to(Cardboard(Decklist.Caretaker()), Zone.DeckTop, 0)
    game.give_to(Cardboard(Decklist.Caretaker()), Zone.DeckTop, 0)
    game.give_to(Cardboard(Decklist.Axebane()), Zone.DeckTop, 0)
    game.give_to(Cardboard(Decklist.Battlement()), Zone.DeckTop, 0)
    game.give_to(Cardboard(Decklist.Forest()), Zone.DeckTop, 0)
    game.give_to(Cardboard(Decklist.Forest()), Zone.DeckTop, 0)
    # cast Collected Company
    universes = cast_and_resolve_company(game)
    assert len(universes) == 11
    # (axe, caretaker)x2. (battle, caretaker)x2. (axe, battle).
    # (double caretaker). (axe). (battle). (caretaker)x2. (none). that's 11!
    assert len(set(universes)) == 8
    num_in_field = [0, 0, 0]
    for u in universes:
        assert len(u.active.deck + u.active.field) == 6
        num_in_field[len(u.active.field)] += 1
        assert len(u.active.grave) == 1
        if any([c.has_type(Decklist.Axebane) for c in u.active.field]):
            assert (
                not any([c.has_type(Decklist.Axebane) for c in u.active.deck]))
        if any([c.has_type(Decklist.Battlement) for c in u.active.field]):
            assert (not any(
                [c.has_type(Decklist.Battlement) for c in u.active.deck]))
        assert (not any([c.has_type(RulesText.Land) for c in u.active.field]))
    assert num_in_field == [1, 4, 6]

    # deck of 5 forests on top, one Caretaker, then 10 islands
    game1 = GameState()
    for _ in range(5):
        game1.give_to(Cardboard(Decklist.Forest()), Zone.DeckBottom, 0)
    game1.give_to(Cardboard(Decklist.Caretaker()), Zone.DeckBottom, 0)
    for _ in range(10):
        game1.give_to(Cardboard(Decklist.Island()), Zone.DeckBottom, 0)
    assert (len(game1.active.deck) == 16)
    # cast Collected Company
    universes = cast_and_resolve_company(game1)
    assert (len(universes) == 2)
    u = [g for g in universes if g.active.field != []][0]
    # now should be islands on top (index -1), forests on bottom (index 0)
    assert all([c.has_type(Decklist.Island) for c in u.active.deck[-10:]])
    assert all([c.has_type(Decklist.Forest) for c in u.active.deck[:5]])
    assert u.active.deck[-6].has_type(Decklist.Island)
    assert len(u.active.field) == 1
    assert len(u.active.grave) == 1

    # deck of only 4 cards total, all Caretakers
    game4 = GameState()
    for _ in range(4):
        game4.give_to(Cardboard(Decklist.Caretaker()), Zone.DeckTop, 0)
    assert (len(game4.active.deck) == 4)
    # cast Collected Company
    universes = cast_and_resolve_company(game4)
    # Choices DOES avoid returning AB and BA. But it returns A+B1 and A+B2
    # even if B1 and B2 are equivalent cards. So (4*3)/2 + 4 + 1
    assert len(universes) == 11
    for u in universes:
        assert len(u.active.deck) + len(u.active.field) == 4
        assert len(u.active.grave) == 1

    # Does Blossoms trigger correctly? start with 12 cards in deck
    game = GameState()
    game.give_to(Cardboard(Decklist.Blossoms()), Zone.DeckTop, 0)
    game.give_to(Cardboard(Decklist.Omens()), Zone.DeckTop, 0)
    for _ in range(10):
        game.give_to(Cardboard(Decklist.Forest()), Zone.DeckBottom, 0)
    assert len(game.active.deck) == 12
    # cast Collected Company
    universes = cast_and_resolve_company(game)
    # (omens, blossons) triggers; reverse order; just one or other; neither.
    assert len(universes) == 5
    lengths = [(len(u.active.field), len(u.active.deck)) for u in universes]
    assert lengths == [(2, 10), (2, 10), (1, 11), (1, 11), (0, 12)]
    u0, u1 = [u for u in universes if len(u.active.field) == 2]
    assert u0 != u1
    while len(u0.stack) > 0:
        [u0] = u0.resolve_top_of_stack()
    while len(u1.stack) > 0:
        [u1] = u1.resolve_top_of_stack()
    assert u0 == u1
    assert len(u0.active.hand) == 2 and len(u0.active.deck) == 8

    # Note: if I put two identical Blossoms into play simultaneously, I STILL
    # will get two GameStates even though they are identical! And that's ok.
    # it's not worth the effort to optimize this out, right now.
    game = GameState()
    game.give_to(Cardboard(Decklist.Blossoms()), Zone.DeckTop, 0)
    game.give_to(Cardboard(Decklist.Blossoms()), Zone.DeckTop, 0)
    for _ in range(10):
        game.give_to(Cardboard(Decklist.Forest()), Zone.DeckBottom, 0)
    # cast Collected Company
    universes = cast_and_resolve_company(game)
    # (blossons, blossons) triggers; reverse order; just one or other; neither.
    assert len(universes) == 5
    lengths = [(len(u.active.field), len(u.active.deck)) for u in universes]
    assert lengths == [(2, 10), (2, 10), (1, 11), (1, 11), (0, 12)]
    u0, u1 = [u for u in universes if len(u.active.field) == 2]
    assert u0 == u1
    while len(u0.stack) > 0:
        [u0] = u0.resolve_top_of_stack()
    assert len(u0.active.hand) == 2 and len(u0.active.deck) == 8

    # deck of 6 forests on top, then 10 islands. remember: -1 is top of deck.
    gameF = GameState()
    for _ in range(6):
        gameF.give_to(Cardboard(Decklist.Forest()), Zone.DeckBottom, 0)
    for _ in range(10):
        gameF.give_to(Cardboard(Decklist.Island()), Zone.DeckBottom, 0)
    # should be forests on top
    assert all([c.has_type(Decklist.Forest) for c in gameF.active.deck[-6:]])
    # cast Collected Company
    universes = cast_and_resolve_company(gameF)
    assert len(universes) == 1
    u = universes[0]
    # now should be islands on top, forests on bottom
    assert all([c.has_type(Decklist.Island) for c in u.active.deck[-10:]])
    assert all([c.has_type(Decklist.Forest) for c in u.active.deck[:6]])
    assert len(u.active.field) == 0
    assert len(u.active.grave) == 1

    print("      ...done, %0.2f sec" % (time.perf_counter() - start_clock))

    # -----------------------------------------------------------------------

    print("\n\npasses all tests!")
