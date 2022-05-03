# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 22:15:57 2020

@author: Cobi
"""

import ZONE
import GameState
import ManaHandler
import CardType
import Decklist
import Cardboard
import PlayTree
# import AI



if __name__ == "__main__":


    game = GameState.GameState()
    game.verbose = False #True
    for i in range(4):
        game.AddToZone(Cardboard.Cardboard(Decklist.Roots,ZONE.HAND) )
    game.MoveZone(game.hand[0],ZONE.FIELD)

    options = game.GetValidActions()
    [(copygame2,_)] = options[0].Run()
    assert(copygame2.GetValidActions() == [] )
    
    #add in an extra mana to see what happens
    copygame2.pool.AddMana("G")
    options = copygame2.GetValidActions()
    assert(len(options)==1) #all 3 roots only generate 1 option--to cast Roots
    [(copygame3,_)] = options[0].Run()
    assert(len(copygame3.field)==2)
    assert(len(copygame3.hand)==2)
    assert(str(copygame3.pool)=="")
    
    #Just to check, game0 is still unchanged:
    assert(len(game.field)==1)
    assert(str(game.pool)=="")
    
    ###---finished testing wall of Roots.  let's try Caryatid
    game.AddToZone( Cardboard.Cardboard(Decklist.Caryatid,ZONE.FIELD) )
    options = game.GetValidActions()
    [(carygame1,_)] = options[0].Run()
    assert(len(options)==1)
    carygame1.Untap()
    carygame1.Upkeep()
    options = carygame1.GetValidActions()
    assert(len(options)==2)
    while len(options)>0:
        (gameN,_) = options[0].Run()[0]
        options = gameN.GetValidActions()
    assert(len(gameN.hand)==2)
    assert(len(gameN.field)==3)
    assert(gameN.pool == ManaHandler.ManaPool("G"))
    
    
    ###--------------------------------------------------------------------

    #basic game-loop
    def BasicLoop(gamestate):
        gameN = gamestate
        options = gameN.GetValidActions()
        while len(options)>0:
            if len(options)>1 and gameN.verbose:
                print("Split! options are:",options)
                print("Taking last option in list")
            universes = options[-1].Run()
            if len(universes)>1 and gameN.verbose:
                print("Split! universes are:")
                for u,_ in universes:
                    print("     ---\n",u,"\n     ---")
                print("Taking last option in list")
            (gameN,_) = universes[-1]
            options = gameN.GetValidActions()
        return gameN

    ###--------------------------------------------------------------------
    
    #testing GetValidActions not double-counting duplicate cards
    game = GameState.GameState()
    game.verbose = False
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD))
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD))
    forest = Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD)
    game.AddToZone( forest )
    game.AddToZone( Cardboard.Cardboard(Decklist.Plains,ZONE.HAND))
    plains = Cardboard.Cardboard(Decklist.Plains,ZONE.HAND)
    game.AddToZone( plains )
    
    assert(len(game.GetValidActions())==2)
    #tap one forest, I'll still have the option to tap more forests
    [(gameF,forestF)] = forest.cardtype.activated[0].PayAndExecute(game,forest)
    assert(len(gameF.GetValidActions())==2)
    assert(gameF.pool == ManaHandler.ManaPool("G"))
    assert(forest.tapped == False)  #original forest untouched
    assert(forestF.tapped == True)  #copy of forest is tapped
    #play one plains, I'll lose option to play plains but get to tap plains now
    [(gameP,plainsP)] = plains.cardtype.Cast(game,plains)
    assert(len(gameP.GetValidActions())==2)
    assert(len(gameP.hand)==1)
    assert(len(gameP.field)==4)
    assert(gameP.pool == ManaHandler.ManaPool(""))
    #untap and go to next turn, should have 3 options again: play, tap W, tap G
    gameP.Untap()
    gameP.Upkeep()
    assert(len(gameP.GetValidActions())==3)
    
    #original game is untouched
    assert(len(game.hand)==2)
    assert(game.pool == ManaHandler.ManaPool(""))
    
    ###--------------------------------------------------------------------
    
    #testing basic lands
    game = GameState.GameState()
    game.verbose = False
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD))
    game.AddToZone( Cardboard.Cardboard(Decklist.Plains,ZONE.FIELD))
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Roots,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Caryatid,ZONE.HAND))
                      
    gameN = BasicLoop(game)
    assert(len(gameN.hand)==1)
    assert(len(gameN.field)==5)
    assert(gameN.pool == ManaHandler.ManaPool(""))
    assert(len(game.field)==2)  #orig game is untouched

    ###--------------------------------------------------------------------
    
    #testing shocklands
    game = GameState.GameState()
    game.verbose = False
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD))
    game.AddToZone( Cardboard.Cardboard(Decklist.BreedingPool,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Caryatid,ZONE.HAND))
                      
    gameN = BasicLoop(game)
    assert(len(gameN.hand)==0)
    assert(len(gameN.field)==3)
    assert(gameN.pool == ManaHandler.ManaPool(""))
    assert(gameN.life == 18)

    ###--------------------------------------------------------------------
    
    #testing equality of gamestates
    game = GameState.GameState()
    game.verbose = False
    forest = Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD)
    game.AddToZone( forest )
    game.AddToZone( Cardboard.Cardboard(Decklist.Plains,ZONE.FIELD))
    game.AddToZone( Cardboard.Cardboard(Decklist.HallowedFountain,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND) )
    game.AddToZone( Cardboard.Cardboard(Decklist.Roots,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Caryatid,ZONE.HAND))
    
    assert( game == game.copy() )
    cp = game.copy([forest])
    assert( game != cp )
    forest2 = forest.copy()
    cp.AddToZone(forest2)
    assert( game == cp )
    [(cp3,forest3)] = forest2.GetAbilities()[0].PayAndExecute(cp,forest2)
    assert( game != cp3)
    assert( cp != cp3)
    [(cp4,forest4)] = forest.GetAbilities()[0].PayAndExecute(game,forest)
    assert( game != cp4)
    assert( cp3 == cp4 )
    assert( not (cp3 is cp4) )
    
    #can I put these in a set?
    testset = set([game,cp,cp3])
    assert(len(testset)==2)
    assert(cp4 in testset)
    
    #two lands. put into play in opposite order. Should be equivalent.
    game1 = GameState.GameState()
    game1.verbose = False
    game1.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND) )
    game1.AddToZone( Cardboard.Cardboard(Decklist.Plains,ZONE.HAND) )
    game2 = game1.copy()
    #game 1: [0] into play, then the other
    game1.MoveZone(game1.hand[0],ZONE.FIELD)
    game1.Untap()
    game1.MoveZone(game1.hand[0],ZONE.FIELD)
    #game 2: [1] into play, then the other
    game2.MoveZone(game2.hand[1],ZONE.FIELD)
    game2.Untap()
    game2.MoveZone(game2.hand[0],ZONE.FIELD)
    assert(game1==game2)
    
    #two creatures. put into play in opposite order. Should NOT be equivalent.
    game1 = GameState.GameState()
    game1.verbose = False
    game1.AddToZone( Cardboard.Cardboard(Decklist.Caryatid,ZONE.HAND) )
    game1.AddToZone( Cardboard.Cardboard(Decklist.Roots,ZONE.HAND) )
    game2 = game1.copy()
    #game 1: [0] into play, then the other
    game1.MoveZone(game1.hand[0],ZONE.FIELD)
    game1.Untap()
    game1.MoveZone(game1.hand[0],ZONE.FIELD)
    #game 2: [1] into play, then the other
    game2.MoveZone(game2.hand[1],ZONE.FIELD)
    game2.Untap()
    game2.MoveZone(game2.hand[0],ZONE.FIELD)
    assert(game1!=game2)  #creatures DO get summoning-sick. 
    
    
    ###--------------------------------------------------------------------
    
    #testing TurnTracker
    game = GameState.GameState()
    game.verbose = False
    forest = Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD)
    game.AddToZone( forest )
    game.AddToZone( Cardboard.Cardboard(Decklist.Plains,ZONE.FIELD))
    game.AddToZone( Cardboard.Cardboard(Decklist.HallowedFountain,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND) )
    game.AddToZone( Cardboard.Cardboard(Decklist.Roots,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Caryatid,ZONE.HAND))
    

    tracker = PlayTree.TurnTracker.InitFromGameState(game)
    tracker.PlayTurn()
    
    assert(len(tracker.finalnodes)==8)
    assert(len(tracker.allnodes)==58)
    assert(tracker.traverse_counter == 105)
    # print(len(tracker.finalnodes))
    # for node in tracker.finalnodes:
    #     print("-----------")
    #     print(node)
    # print("\n\n")
    
    #fixing TurnTracker history duplication: second minor test
    game2 = GameState.GameState()
    game2.verbose = False
    game2.AddToZone( Cardboard.Cardboard(Decklist.HallowedFountain,ZONE.HAND))
    game2.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND) )
    
    tracker2 = PlayTree.TurnTracker.InitFromGameState(game2)
    tracker2.PlayTurn()
    
    assert(len(tracker2.finalnodes)==4)
    assert(len(tracker2.allnodes)==7)
    assert(tracker2.traverse_counter == 6)
    
    ###--------------------------------------------------------------------
    
    #testing PlayTree
    game = GameState.GameState()
    game.verbose = False
    game.AddToZone( Cardboard.Cardboard(Decklist.Plains,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Roots ,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Caryatid,ZONE.HAND))
    for x in range(10):
        game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.DECK))

    tree = PlayTree.PlayTree(game,5)
    # tree.PrintLatest()
    assert(len(tree.LatestNodes())==2)
    
    tree.PlayATurn()
    # tree.PrintLatest()
    assert(len(tree.LatestNodes())==4)

    tree.PlayATurn()
    # tree.PrintLatest()
    assert(len(tree.LatestNodes())==4)
    assert(all([len(n.state.hand)==2 for n in tree.LatestNodes()]))
    assert(all([len(n.state.field)==5 for n in tree.LatestNodes()]))


    ###--------------------------------------------------------------------

    ###Testing Caretakers
    game = GameState.GameState()
    game.verbose = False
    game.AddToZone( Cardboard.Cardboard(Decklist.Caretaker,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Caretaker,ZONE.HAND))
    game.MoveZone(game.hand[0],ZONE.FIELD)
    
    assert(game.field[0].summonsick)
    assert(len(game.GetValidActions())==0)
    #what if I give the caretaker something to tap?
    caryatid = Cardboard.Cardboard(Decklist.Caryatid,ZONE.FIELD)
    game.AddToZone(caryatid)
    assert(len(game.GetValidActions())==0) #no, caretaker still summonsick. good.
    game.field.remove(caryatid)
    
    game.Untap()
    assert(len(game.GetValidActions())==0)  #nothing to tap
    
    #give it something to tap
    game.AddToZone(caryatid)
    assert(len(game.GetValidActions())==1)
    [(univ1,_)] = game.GetValidActions()[0].Run()
    assert(univ1.pool == ManaHandler.ManaPool("A"))
    assert(all([c.tapped for c in univ1.field]))
    
    #give it TWO things to tap
    game.MoveZone(game.hand[0],ZONE.FIELD)
    assert(len(game.GetValidActions())==1)
    universes = game.GetValidActions()[0].Run()
    assert(len(universes)==2) #two possible things to tap
    [(univ2,care2),(univ3,care3)] = universes
    assert(univ2.pool == ManaHandler.ManaPool("A"))
    assert(univ3.pool == ManaHandler.ManaPool("A"))
    assert(care2.tapped and care3.tapped)
    assert(len(univ2.field)==len(univ3.field))
    assert([c.tapped for c in univ2.field] != [c.tapped for c in univ3.field])

    #see what happens with two active caretakers
    game3 = univ3
    game3.Untap()
    assert(len(game3.GetValidActions())==2)  #2 caretakers are combined to one action
    universes = care3.GetAbilities()[0].PayAndExecute(univ3,care3)
    assert(len(universes)==2)
    [(univ4,care4),(univ5,care5)] = universes
    assert(univ4.pool == ManaHandler.ManaPool("A"))
    assert(univ5.pool == ManaHandler.ManaPool("A"))
    assert(care4.tapped and care5.tapped)
    assert(len(univ4.field)==len(univ5.field))
    assert([c.tapped for c in univ4.field] != [c.tapped for c in univ5.field])
    #one universe should have 1 action left (caryatid), other doesn't (lone caretaker)
    assert({len(univ4.GetValidActions()),len(univ5.GetValidActions())}  == {0,1})


    #may as well use this setup to test Axebane and Battlement as well
    axe = Cardboard.Cardboard(Decklist.Axebane,ZONE.FIELD)
    battle = Cardboard.Cardboard(Decklist.Battlement,ZONE.FIELD)
    game6 = game3.copy()
    game6.AddToZone(axe)
    game6.AddToZone(battle)
    game6.Untap()
    [(u_axe,_)] = axe.GetAbilities()[0].PayAndExecute(game6,axe)
    assert(u_axe.pool == ManaHandler.ManaPool("AAAAA"))
    [(u_bat,_)] = battle.GetAbilities()[0].PayAndExecute(game6,battle)
    assert(u_bat.pool == ManaHandler.ManaPool("GGGGG"))
    

    ###--------------------------------------------------------------------

    #testing PlayTree -- can it find the line for 8 mana on turn 3
    game = GameState.GameState()
    game.verbose = False
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Roots ,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Caretaker,ZONE.HAND))
    game.AddToZone( Cardboard.Cardboard(Decklist.Battlement,ZONE.HAND))
    for x in range(10):
        game.AddToZone( Cardboard.Cardboard(Decklist.Forest,ZONE.DECK))
    
    tree = PlayTree.PlayTree(game,5)
    assert(len(tree.LatestNodes())==1)
    tree.PlayATurn()
    assert(len(tree.LatestNodes())==2)
    tree.PlayATurn()
    # tree.PrintLatest()
    assert(len(tree.LatestNodes())==2)
    assert(any([n.state.pool.CanAffordCost(ManaHandler.ManaCost("8"))
                                     for n in tree.LatestNodes()] ))




    
    print("\n\npasses all tests!")