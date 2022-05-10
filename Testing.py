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
import Abilities
import PlayTree
# import AI



if __name__ == "__main__":
    ###--------------------------------------------------------------------
    print("Testing Wall of Roots...")
    
    game = GameState.GameState()
    game.verbose = False #True
    assert(len(game.GetValidActivations())==0)
    assert(len(game.GetValidCastables())==0)
    
    for i in range(4):
        game.MoveZone(Cardboard.Cardboard(Decklist.Roots),ZONE.HAND)
    effects = game.MoveZone(game.hand[0],ZONE.FIELD)
    assert(len(effects)==0) #nothing to trigger, yet

    #activate the one ability!
    assert(len(game.GetValidActivations())==1)  #1 ability to activate
    assert(len(game.GetValidCastables())==0)    #no castable cards
    [copygame1] = game.GetValidActivations()[0].PutOnStack(game)
    #remember, mana abilities don't use the stack! so mana is added immediately
    assert(len(copygame1.field[0].counters)>0)  #counters on the Wall of Roots
    assert(len(copygame1.GetValidActivations())==0)
    assert(len(copygame1.GetValidCastables())==0)
    assert(len(copygame1.stack)==0)
    assert(copygame1.pool == ManaHandler.ManaPool("G"))
    
    #add in an extra mana to see what happens
    copygame2 = copygame1.copy()
    copygame2.pool.AddMana("G")
    assert(len(copygame2.GetValidActivations())==0)  #no abilities to activate
    #all 3 roots only generate 1 option--to cast Roots
    assert(len(copygame2.GetValidCastables())==1)
    #cast the newly castable spell
    cardboard = copygame2.GetValidCastables()[0]
    assert([o is cardboard for o in copygame2.hand] == [True,False,False]) #1st spell in hand

    [copygame3] = copygame2.CastSpell(cardboard)  #puts it on the stack
    assert(copygame3.pool == ManaHandler.ManaPool(""))  #no mana anymore
    assert(len(copygame3.stack)==1)  #one spell on the stack
    assert(len(copygame3.hand)==2)   #two cards in hand
    assert(len(copygame3.field)==1)  #one card in play
    
    [copygame4] = copygame3.ResolveTopOfStack()
    assert(copygame4.pool == ManaHandler.ManaPool(""))  #no mana anymore
    assert(len(copygame4.stack)==0)  #nothing on the stack
    assert(len(copygame4.hand)==2)   #two cards in hand
    assert(len(copygame4.field)==2)  #two cards in play
    
    #should be one ability (new Roots) and no castable spells (not enough mana)
    assert(len(copygame4.GetValidActivations())==1)
    assert(len(copygame4.GetValidCastables())==0)  
    #Stack should be empty, so resolving the stack should be impossible
    assert([] == copygame4.ResolveTopOfStack() )
    
    #Just to check, original game is still unchanged:
    assert(len(game.field)==1)
    assert(str(game.pool)=="")

    
    ###--------------------------------------------------------------------
    print("Testing Sylvan Caryatid, Untap, and Upkeep...")
    
    #add a caryatid to the all-roots game
    carygame1,_ = game.CopyAndTrack([])
    carygame1.MoveZone(Cardboard.Cardboard(Decklist.Caryatid),ZONE.FIELD)
    #should only see one valid ability to activate, since Caryatid not hasty
    assert(len(carygame1.GetValidActivations())==1)  
    assert(len(carygame1.GetValidCastables())==0)    #no castable cards

    #try untap and upkeep
    carygame1.UntapStep()
    carygame1.UpkeepStep()
    assert(len(carygame1.GetValidCastables())==0)    #no castable cards
    gameN = carygame1
    options = gameN.GetValidActivations()+gameN.GetValidCastables()
    assert(len(options)==2)
    while len(options)>0:
        if isinstance(options[0],Abilities.StackEffect):
            [gameN] = options[0].PutOnStack(gameN)
        elif isinstance(options[0],Cardboard.Cardboard):
            [gameN] = gameN.CastSpell(options[0])  #puts it on the stack
        else:
            raise ValueError("incorrect type of object on stack!")
        while len(gameN.stack)>0:
            [gameN] = gameN.ResolveTopOfStack()
        options = gameN.GetValidActivations()+gameN.GetValidCastables()
    assert(len(gameN.hand)==2)
    assert(len(gameN.field)==3)
    assert(gameN.pool == ManaHandler.ManaPool("G"))
    
    
    ###--------------------------------------------------------------------

    #basic game-loop
    def BasicLoop(gamestate):
        gameN = gamestate
        options = gameN.GetValidActivations()+gameN.GetValidCastables()
        while len(options)>0:
            if gameN.verbose:
                print("\n")
                print(gameN)
            if len(options)>1 and gameN.verbose:
                print("\nSplit! options are:",options)
                print("Taking last option in list")
            if isinstance(options[-1],Abilities.StackEffect):
                universes = options[-1].PutOnStack(gameN)
            elif isinstance(options[-1],Cardboard.Cardboard):
                universes = gameN.CastSpell(options[-1])  #puts it on the stack
            else:
                raise ValueError("incorrect type of object on stack!")
            #universes is a list of GameStates
            if len(universes)>1 and gameN.verbose:
                print("\nSplit! universes are:")
                for u in universes:
                    print("     ---\n",u,"\n     ---")
                print("Taking last option in list")
            gameN = universes[-1]
            while len(gameN.stack)>0:
                universes = gameN.ResolveTopOfStack()
                if len(universes)>1 and gameN.verbose:
                    print("Split! universes are:")
                    for u,_ in universes:
                        print("     ---\n",u,"\n     ---")
                    print("Taking last option in list")
                gameN = universes[-1]
            options = gameN.GetValidActivations()+gameN.GetValidCastables()
        return gameN

    
    ###--------------------------------------------------------------------
    print("Testing basic lands and BasicLoop...")
    
    game = GameState.GameState()
    game.verbose = False
    #field
    game.MoveZone(Cardboard.Cardboard(Decklist.Forest),ZONE.FIELD)
    game.MoveZone(Cardboard.Cardboard(Decklist.Plains),ZONE.FIELD)
    #hand
    game.MoveZone(Cardboard.Cardboard(Decklist.Forest),ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Forest),ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Roots),ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Caryatid),ZONE.HAND)
                       
    gameN = BasicLoop(game)
    assert(len(gameN.hand)==1)
    assert(len(gameN.field)==5)
    assert(gameN.pool == ManaHandler.ManaPool(""))
    assert(len(game.field)==2)  #orig game is untouched


    ###--------------------------------------------------------------------
    print("Testing shock-lands...")
    
    game = GameState.GameState()
    game.verbose = False
    game.MoveZone(Cardboard.Cardboard(Decklist.Forest),ZONE.FIELD)
    #hand
    game.MoveZone(Cardboard.Cardboard(Decklist.BreedingPool),ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Caryatid),ZONE.HAND)
    
    #run all the way through, with the settings I've chosen, should end with
    #shocking in the Breeding Pool and using it to cast the Caryatid                  
    gameN = BasicLoop(game)
    assert(len(gameN.hand)==0)
    assert(len(gameN.field)==3)
    assert(gameN.pool == ManaHandler.ManaPool(""))
    assert(gameN.life == 18)
    
    #make sure we have shock and tapped options available
    options = game.GetValidCastables()
    assert(len(options)==1)
    assert(options[0] is game.hand[1]) #only castable is shockland
    universes = game.CastSpell(options[-1])  #puts it into play, b/c lands not on stack
    assert(len(universes)==2)  #shock or tapped
    
    #shock-universe
    assert( not [u for u in universes if u.life==18][0].field[0].tapped )
    #tapped-universe
    assert(     [u for u in universes if u.life==20][0].field[0].tapped )
    
    

    ###--------------------------------------------------------------------
    print("""Testing equality of gamestates...""")
    
    game = GameState.GameState()
    game.verbose = False
    #field
    game.MoveZone( Cardboard.Cardboard(Decklist.Plains)          ,ZONE.FIELD)
    #hand
    game.MoveZone( Cardboard.Cardboard(Decklist.HallowedFountain),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest)          ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Roots)           ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caryatid)        ,ZONE.HAND)
    
    #try to copy, make sure equality holds
    cp = game.copy()
    assert( cp == game )
    assert( cp is not game)

    #add this forest to one but not the other
    forest = Cardboard.Cardboard(Decklist.Forest)
    game.MoveZone( forest, ZONE.FIELD )    
    assert( game != cp )
    #add a copy of the forst to the other
    forest2 = forest.copy()
    forest2.zone = ZONE.NEW
    cp.MoveZone(forest2, ZONE.FIELD)
    assert(forest != forest2)  #Cardboard uses "is" for eq  (or else "in list" breaks)
    assert(forest is not forest2)
    assert( game == cp )
    #tap both of these forests for mana
    cp3 = game.ActivateAbilities(forest , forest.GetAbilities()[0])[0]
    assert(game != cp3)
    assert( cp != cp3)
    cp4 =   cp.ActivateAbilities(forest2,forest2.GetAbilities()[0])[0]
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
    game1.MoveZone( Cardboard.Cardboard(Decklist.Forest),ZONE.HAND)
    game1.MoveZone( Cardboard.Cardboard(Decklist.Plains),ZONE.HAND)
    game2 = game1.copy()
    #game 1: [0] into play, then the other
    game1.MoveZone(game1.hand[0],ZONE.FIELD)
    game1.UntapStep()
    game1.MoveZone(game1.hand[0],ZONE.FIELD)
    #game 2: [1] into play, then the other
    game2.MoveZone(game2.hand[1],ZONE.FIELD)
    game2.UntapStep()
    game2.MoveZone(game2.hand[0],ZONE.FIELD)
    assert(game1==game2)
    
    #two creatures. put into play in opposite order. Should be NOT equivalent
    #because of summoning sickness
    game1 = GameState.GameState()
    game1.verbose = False
    game1.MoveZone( Cardboard.Cardboard(Decklist.Caryatid), ZONE.HAND)
    game1.MoveZone( Cardboard.Cardboard(Decklist.Roots)   , ZONE.HAND)
    game2 = game1.copy()
    #game 1: [0] into play, then the other
    game1.MoveZone(game1.hand[0],ZONE.FIELD)
    game1.UntapStep()
    game1.MoveZone(game1.hand[0],ZONE.FIELD)
    #game 2: [1] into play, then the other
    game2.MoveZone(game2.hand[1],ZONE.FIELD)
    game2.UntapStep()
    game2.MoveZone(game2.hand[0],ZONE.FIELD)
    assert(game1!=game2)  #creatures DO get summoning-sick. 
    
    
    ###--------------------------------------------------------------------
    print("Testing TurnTracker...")
    
    game = GameState.GameState()
    game.verbose = False
    #field
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest          ),ZONE.FIELD)
    game.MoveZone( Cardboard.Cardboard(Decklist.Plains          ),ZONE.FIELD)
    #hand
    game.MoveZone( Cardboard.Cardboard(Decklist.HallowedFountain),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest          ),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Roots           ),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caryatid        ),ZONE.HAND)
    
    tracker = PlayTree.TurnTracker.InitFromGameState(game)
    tracker.PlayTurn()
    assert(len(tracker.finalnodes)==8)
    #58  pre-stack. 215 mana on stack.  98 mana off stack.  84 land off stack.
    assert(len(tracker.allnodes)==84)
    #105 pre-stack. 340 mana on stack. 170 mana off stack. 146 land off stack.
    assert(tracker.traverse_counter == 146)
    assert(len(tracker.GetFinal())==6 )
    assert(len(tracker.GetAll())  ==18)
    # for node in tracker.finalnodes:
    #     print("-----------")
    #     print(node)
    # print("\n\n")

    #fixing TurnTracker history duplication: second minor test
    game2 = GameState.GameState()
    game2.verbose = True
    game2.MoveZone( Cardboard.Cardboard(Decklist.HallowedFountain),ZONE.HAND)
    game2.MoveZone( Cardboard.Cardboard(Decklist.Forest          ),ZONE.HAND)
    
    tracker2 = PlayTree.TurnTracker.InitFromGameState(game2)
    tracker2.PlayTurn()
    assert(len(tracker2.finalnodes)==4)
    assert(len(tracker2.allnodes)==7)
    assert(tracker2.traverse_counter == 6)
    assert(len(tracker2.GetFinal())==3 )
    assert(len(tracker2.GetAll())  ==4 )
    histlength = [0,0,0,0]
    for n in tracker2.allnodes:
        histlength[len(n.history)] += 1
    assert(histlength==[1,3,3,0])  #1 with zero action, 3 with one...
    
    
    ###--------------------------------------------------------------------
    print("Testing PlayTree...")
    
    game = GameState.GameState()
    game.verbose = False
    game.MoveZone( Cardboard.Cardboard(Decklist.Plains   ),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest   ),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest   ),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Roots    ),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caryatid ),ZONE.HAND)
    for x in range(10):
        game.MoveZone( Cardboard.Cardboard(Decklist.Forest),ZONE.DECK)

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
    print("Testing Caretakers, Axebane, Battlement...")

    game = GameState.GameState()
    game.verbose = False
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker) ,ZONE.HAND)
    effects = game.MoveZone(game.hand[0],ZONE.FIELD)
    assert(len(effects)==0)  #nothing to trigger off of this move
    
    assert(game.field[0].summonsick)
    assert(len(game.GetValidActivations())==0)
    #what if I give the caretaker something to tap?
    caryatid = Cardboard.Cardboard(Decklist.Caryatid)
    game.MoveZone(caryatid,ZONE.FIELD)
    assert(len(game.GetValidActivations())==0) #no, caretaker still summonsick. good.
    game.field.remove(caryatid)
    
    game.UntapStep()
    assert(len(game.GetValidActivations())==0)  #nothing to tap
    
    #give it something to tap
    caryatid.zone = ZONE.NEW
    game.MoveZone(caryatid,ZONE.FIELD)
    assert(len(game.GetValidActivations())==1)
    
    [univ1] = game.GetValidActivations()[0].PutOnStack(game) #mana so just happens
    assert(univ1.pool == ManaHandler.ManaPool("A"))
    assert(all([c.tapped for c in univ1.field]))
    
    #give it TWO things to tap
    game.MoveZone(game.hand[0],ZONE.FIELD)
    assert(len(game.GetValidActivations())==1)  #still only 1 ability even if 2 "targets"   
    universes = game.GetValidActivations()[0].PutOnStack(game) #mana so just happens
    assert(len(universes)==2) #two possible things to tap
    [univ2,univ3] = universes
    assert(univ2.pool == ManaHandler.ManaPool("A"))
    assert(univ3.pool == ManaHandler.ManaPool("A"))
    assert(len(univ2.field)==len(univ3.field))
    #check that they are really tapped differently
    assert([c.tapped for c in univ2.field] != [c.tapped for c in univ3.field])

    #see what happens with two active caretakers
    game3 = univ3
    game3.UntapStep()
    assert(len(game3.GetValidActivations())==2)  #2 Caretakers combined, Caryatid
    care3 = [c for c in game3.field if c.cardtype == Decklist.Caretaker][0]
    universes = game3.ActivateAbilities(care3,care3.GetAbilities()[0])
    assert(len(universes)==2)
    [univ4,univ5] = universes
    assert(univ4.pool == ManaHandler.ManaPool("A"))
    assert(univ5.pool == ManaHandler.ManaPool("A"))
    assert(len(univ4.field)==len(univ5.field))
    assert([c.tapped for c in univ4.field] != [c.tapped for c in univ5.field])
    #one universe should have 1 action left (caryatid), other doesn't (lone caretaker)
    assert({len(univ4.GetValidActivations()),len(univ5.GetValidActivations())}  == {0,1})


    #may as well use this setup to test Axebane and Battlement as well
    axe = Cardboard.Cardboard(Decklist.Axebane)
    battle = Cardboard.Cardboard(Decklist.Battlement)
    game6 = univ2.copy()
    game6.MoveZone(axe   ,ZONE.FIELD)
    game6.MoveZone(battle,ZONE.FIELD)
    assert(len(game6.GetValidActivations())==0) #still summonsick. good.
    game6.UntapStep()
    [u_axe] = game6.ActivateAbilities(axe,axe.GetAbilities()[0])
    assert(u_axe.pool == ManaHandler.ManaPool("AAAAA"))
    [u_bat] = game6.ActivateAbilities(battle,battle.GetAbilities()[0])
    assert(u_bat.pool == ManaHandler.ManaPool("GGGGG"))

    

    ###--------------------------------------------------------------------
    print("Can PlayTree find 8 mana on turn 3...")

    #testing PlayTree -- can it find the line for 8 mana on turn 3
    game = GameState.GameState()
    game.verbose = False
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Roots ) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Battlement),ZONE.HAND)
    for x in range(10):
        game.MoveZone( Cardboard.Cardboard(Decklist.Forest) ,ZONE.DECK)
    
    tree = PlayTree.PlayTree(game,5)
    assert(len(tree.LatestNodes())==1)
    tree.PlayATurn()
    assert(len(tree.LatestNodes())==2)
    tree.PlayATurn()
    tree.PrintLatest()
    assert(len(tree.LatestNodes())==2)
    assert(any([n.state.pool.CanAffordCost(ManaHandler.ManaCost("8"))
                                     for n in tree.LatestNodes()] ))




    
    print("\n\npasses all tests!")