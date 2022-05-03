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
    [(cp3,forest3)] = forest2.activated[0].PayAndExecute(cp,forest2)
    assert( game != cp3)
    assert( cp != cp3)
    [(cp4,forest4)] = forest.activated[0].PayAndExecute(game,forest)
    assert( game != cp4)
    assert( cp3 == cp4 )
    assert( not (cp3 is cp4) )
    
    #can I put these in a set?
    testset = set([game,cp,cp3])
    assert(len(testset)==2)
    assert(cp4 in testset)
    
    
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
    
    # ###--------------------------------------------------------------------
    
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



    
    print("\n\npasses all tests!")