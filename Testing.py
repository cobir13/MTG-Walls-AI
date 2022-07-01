# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 22:15:57 2020

@author: Cobi
"""

import ZONE
import GameState
import ManaHandler
import RulesText
import Decklist
import Cardboard
import Abilities
import PlayTree
import Actions


import time


if __name__ == "__main__":

    ###--------------------------------------------------------------------
    print("Testing Wall of Roots...")
    startclock = time.perf_counter()
    
    game = GameState.GameState()
    game.verbose = False #True
    assert(len(game.GetValidActivations())==0)
    assert(len(game.GetValidCastables())==0)
    
    for i in range(4):
        game.MoveZone(Cardboard.Cardboard(Decklist.Roots),ZONE.HAND)
    game.MoveZone(game.hand[0],ZONE.FIELD)
    assert(len(game.super_stack) == 0) #nothing to trigger, yet

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

    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )

    
    
    ###--------------------------------------------------------------------
    print("Testing Sylvan Caryatid, Untap, and Upkeep...")
    startclock = time.perf_counter()
    
    #add a caryatid to the all-roots game
    carygame1,_ = game.copy_and_track([])
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
    
    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )
    
    
    
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
    startclock = time.perf_counter()
    
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

    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )


    ###--------------------------------------------------------------------
    print("Testing shock-lands...")
    startclock = time.perf_counter()
    
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
    
    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )
    
    

    ###--------------------------------------------------------------------
    print("""Testing equality of gamestates...""")
    startclock = time.perf_counter()
    
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
    cp3 = game.ActivateAbilities(forest, forest.get_activated()[0])[0]
    assert(game != cp3)
    assert( cp != cp3)
    cp4 =   cp.ActivateAbilities(forest2, forest2.get_activated()[0])[0]
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
    
    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )
    
    
    
    ###--------------------------------------------------------------------
    print("Testing TurnTracker...")
    startclock = time.perf_counter()
    
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
    
    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )
    
    
    
    
    ###--------------------------------------------------------------------
    print("Testing PlayTree...")
    startclock = time.perf_counter()
    
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

    tree.PlayNextTurn()
    # tree.PrintLatest()

    tree.PlayNextTurn()
    # tree.PrintLatest()
    assert(len(tree.LatestNodes())==4)
    assert(all([len(n.state.hand)==2 for n in tree.LatestNodes()]))
    assert(all([len(n.state.field)==5 for n in tree.LatestNodes()]))

    assert(all([n.state.turn_count == 1 for n in tree.trackerlist[0].allnodes]))
    assert(all([n.state.turn_count == 2 for n in tree.trackerlist[1].allnodes]))
    assert(all([n.state.turn_count == 3 for n in tree.trackerlist[2].allnodes]))
    
    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )
    
    

    ###--------------------------------------------------------------------
    print("Testing Caretakers, Axebane, Battlement...")
    startclock = time.perf_counter()

    game = GameState.GameState()
    game.verbose = False
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker) ,ZONE.HAND)
    game.MoveZone(game.hand[0],ZONE.FIELD)
    assert(len(game.super_stack) == 0)  #nothing to trigger off of this move
    
    assert(game.field[0].summon_sick)
    assert(len(game.GetValidActivations())==0)
    #what if I give the caretaker something to tap?
    caryatid = Cardboard.Cardboard(Decklist.Caryatid)
    game.MoveZone(caryatid,ZONE.FIELD)
    assert(len(game.GetValidActivations())==0) #no, caretaker still summon_sick. good.
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
    care3 = [c for c in game3.field if c.rules_text == Decklist.Caretaker][0]
    universes = game3.ActivateAbilities(care3, care3.get_activated()[0])
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
    assert(len(game6.GetValidActivations())==0) #still summon_sick. good.
    game6.UntapStep()
    [u_axe] = game6.ActivateAbilities(axe, axe.get_activated()[0])
    assert(u_axe.pool == ManaHandler.ManaPool("AAAAA"))
    [u_bat] = game6.ActivateAbilities(battle, battle.get_activated()[0])
    assert(u_bat.pool == ManaHandler.ManaPool("GGGGG"))

    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )



    ###--------------------------------------------------------------------
    print("Can PlayTree find 8 mana on turn 3...")
    startclock = time.perf_counter()

    game = GameState.GameState()
    game.verbose = True
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Roots ) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Battlement),ZONE.HAND)
    #deck
    for x in range(10):
        game.MoveZone( Cardboard.Cardboard(Decklist.Forest) ,ZONE.DECK)
    
    tree = PlayTree.PlayTree(game,5)
    assert(len(tree.trackerlist[-1].finalnodes)==1)
    assert(len(tree.LatestNodes())==1)
    
    tree.PlayNextTurn()
    assert(len(tree.trackerlist[-1].finalnodes)==2)
    assert(len(tree.LatestNodes())==2)
    
    tree.PlayNextTurn()
    assert(len(tree.trackerlist[-1].finalnodes)==6)
    #if I untap, only difference is counters on Roots. I lose track of mana
    assert(len(tree.LatestNodes())==2)
    #mana not visible in LatestNodes necessarily, but IS visible in finalnodes
    assert(any([n.state.pool.CanAffordCost(ManaHandler.ManaCost("8"))
                for n in tree.trackerlist[-1].finalnodes] ))
    
    # for n in tree.trackerlist[-1].finalnodes:
    #     print(n)
    #     print("")
    # print("-----------\n")
    
    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )




    ###--------------------------------------------------------------------
    print("Testing Wall of Blossoms, Arcades, and ETBs")
    startclock = time.perf_counter()

    game = GameState.GameState()
    game.verbose = True
    #field
    game.MoveZone( Cardboard.Cardboard(Decklist.Plains) ,ZONE.FIELD)
    #hand
    game.MoveZone( Cardboard.Cardboard(Decklist.Blossoms),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Blossoms),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest  ),ZONE.HAND)
    #deck
    for x in range(10):
        game.MoveZone( Cardboard.Cardboard(Decklist.Island) ,ZONE.DECK)
    
    tree = PlayTree.PlayTree(game,5)
    
    #only option is play Forest, play Blossoms, draw Island
    assert(len(tree.LatestNodes())==1)
    assert(len(tree.trackerlist[-1].finalnodes)==1)  
    [node] = tree.trackerlist[-1].finalnodes
    final = node.state 
    assert(len(final.hand )==2)
    assert(len(final.field)==3)
    assert(len(final.deck )==9)
    assert(any([c.rules_text == Decklist.Island for c in final.hand]))
    assert(not any([c.rules_text == Decklist.Island for c in final.field]))
    
    #play next turn: draw Island, play Island, play Blossoms, draw Island
    tree.PlayNextTurn()
    assert(len(tree.LatestNodes())==1)
    assert(len(tree.trackerlist[-1].finalnodes)==2)  #floating W or U
    [node,_] = tree.trackerlist[-1].finalnodes
    final = node.state
    assert(len(final.hand )==2)
    assert(len(final.field)==5)
    assert(len(final.deck )==7)
    
    assert(any([c.rules_text == Decklist.Island for c in final.hand]))
    assert(any([c.rules_text == Decklist.Island for c in final.field]))
    
    #add Caryatid to hand and cast it, to be sure I didn't make all defenders draw
    final.MoveZone( Cardboard.Cardboard(Decklist.Caryatid),ZONE.HAND)
    final.UntapStep()
    tree2 = PlayTree.PlayTree(final,5)
    tree2.PlayNextTurn()
    assert(len(tree2.LatestNodes())==1)
    final2 = tree2.LatestNodes()[0].state
    assert(len(final2.hand )==1)
    assert(len(final2.field)==8)
    assert(len(final2.deck )==6)
    
    #but what if there was an Arcades in play?
    gameA = GameState.GameState()
    #deck
    for x in range(10):
        gameA.MoveZone( Cardboard.Cardboard(Decklist.Island) ,ZONE.DECK)
    gameA.MoveZone( Cardboard.Cardboard(Decklist.Arcades),ZONE.FIELD)
    assert(len(gameA.super_stack) == 0)  #Arcades doesn't trigger itself
    #add Blossoms to field and hopefully draw 2
    gameA.MoveZone( Cardboard.Cardboard(Decklist.Blossoms),ZONE.FIELD)
    assert(len(gameA.super_stack) == 2)
    assert(len(gameA.stack)==0)
    assert(len(gameA.hand)==0)  #haven't draw or put triggers on stack
    assert(len(gameA.deck)==10)  #haven't draw or put triggers on stack
    #clear the super_stack and then stack. should come to the same thing.
    gameA,gameA1 = gameA.ClearSuperStack()
    assert( gameA != gameA1)  #different order of triggers
    while len(gameA.stack)>0:
        universes = gameA.ResolveTopOfStack()
        assert(len(universes)==1)
        gameA = universes[0]
    while len(gameA1.stack)>0:
        universes = gameA1.ResolveTopOfStack()
        assert(len(universes)==1)
        gameA1 = universes[0]
    assert(gameA==gameA1)
    assert(len(gameA.super_stack) == 0)
    #should have drawn 2 cards
    assert(len(gameA.hand)==2)
    assert(len(gameA.deck)==8)
    #now let's try to add a Caryatid to field and hopefully draw 1
    gameA.MoveZone( Cardboard.Cardboard(Decklist.Caryatid),ZONE.FIELD)
    assert(len(gameA.super_stack) == 1)
    assert(len(gameA.hand)==2)  #haven't draw or put triggers on stack
    assert(len(gameA.deck)==8)  #haven't draw or put triggers on stack
    [gameA] = gameA.ClearSuperStack()
    while len(gameA.stack)>0:
        universes = gameA.ResolveTopOfStack()
        assert(len(universes)==1)
        gameA = universes[0]
    #should have drawn 2 cards
    assert(len(gameA.hand)==3)
    assert(len(gameA.deck)==7)
    
    #set up a sample game and play the first few turns. Should be able to 
    #cast Arcades on turn 3 and then draw a lot of cards
    
    game = GameState.GameState()
    game.verbose = False
    #hand
    game.MoveZone( Cardboard.Cardboard(Decklist.Plains  ),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest  ),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Island  ),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caryatid),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Blossoms),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Arcades ),ZONE.HAND)
    #deck
    for x in range(4):
        game.MoveZone( Cardboard.Cardboard(Decklist.Roots) ,ZONE.DECK)
    for x in range(4):
        game.MoveZone( Cardboard.Cardboard(Decklist.Island) ,ZONE.DECK)

    tree = PlayTree.PlayTree(game,5)
    tree.PlayNextTurn()  #turn 2
    tree.PlayNextTurn()  #turn 3
    waystohaveArcades = 0
    for n in tree.LatestNodes():
        if any([c.rules_text == Decklist.Arcades for c in n.state.field]):
            # print(n.state,"\n")
            waystohaveArcades += 1
    assert(waystohaveArcades==2) #use Roots OR Caryatid to cast on T3
    
    tree.PlayNextTurn()  #turn 4
    assert(min( [len(n.state.deck) for n in tree.LatestNodes()] )==0)
    for n in tree.LatestNodes():
        if len(n.state.deck)==0:
            assert(len(n.state.hand)==4)
            assert(n.state.pool == ManaHandler.ManaPool(""))

    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )



    ###--------------------------------------------------------------------
    print("Testing fetchlands")
    startclock = time.perf_counter()


    #make a game with some fetchable lands in deck and fetchlands in hand
    game = GameState.GameState()
    game.verbose = False
    #deck
    game.MoveZone( Cardboard.Cardboard(Decklist.Plains  ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest  ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest  ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest  ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest  ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Island  ),ZONE.DECK)
    #hand
    game.MoveZone( Cardboard.Cardboard(Decklist.WindsweptHeath    ),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.WindsweptHeath    ),ZONE.HAND)

    #pre-shuffle check
    assert(game.deck[0 ].rules_text == Decklist.Plains)
    assert(game.deck[-1].rules_text == Decklist.Island)
    
    #play the fetch
    universes = game.CastSpell(game.hand[0])
    for g in universes:
        assert(len(g.deck)==5)
        assert(len(g.hand)==1)
        assert(len(g.grave)==1)
        assert(g.life == 19)
        # print([str(c) for c in g.deck])
    assert(len(universes)==2)
    assert(not universes[0].field[0].is_equiv_to(universes[1].field[0]))
    
    #I will MOVE the fetch into play instead. should put onto super_stack first
    game2 = game.copy()
    game2.MoveZone(game2.hand[0],ZONE.FIELD)
    assert(game2.stack==[])
    assert(len(game2.super_stack) == 1)
    assert(len(game2.ClearSuperStack())==2)  #same 2 as before
    
    #add two shocks to the deck.  should both be fetchable. I expect four
    #fetchable targets and six total gamestates (due to shocked vs tapped)
    game.MoveZone( Cardboard.Cardboard(Decklist.HallowedFountain  ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.TempleGarden      ),ZONE.DECK)
    
    #play the fetch
    universes = game.CastSpell(game.hand[0])
    landstrings = []
    totallife = 0
    for g in universes:
        assert(len(g.deck)==7)
        assert(len(g.hand)==1)
        assert(len(g.grave)==1)
        assert(len(g.super_stack) == 0)
        assert(len(g.stack)==0)
        landstrings.append(g.field[0].get_id())
        totallife += g.life
    assert(len(universes)==6)
    assert(landstrings == ["LandPlains_2","LandForest_2",
                           "LandHallowedFountain_T2","LandHallowedFountain_2",
                           "LandTempleGarden_T2","LandTempleGarden_2"])
    assert(totallife == (19*4)+(17*2) )
    
    #what if deck has no valid targets?
    gameE = GameState.GameState()
    #deck
    for i in range(10):
        gameE.MoveZone( Cardboard.Cardboard(Decklist.Island  ),ZONE.DECK)
    #hand
    gameE.MoveZone( Cardboard.Cardboard(Decklist.WindsweptHeath    ),ZONE.HAND)
    universes = gameE.CastSpell(gameE.hand[0])
    assert(len(universes)==1)
    assert(len(universes[0].deck)==10)
    assert(len(universes[0].hand)== 0)
    assert(len(universes[0].grave)==1)
    
    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )


    ###--------------------------------------------------------------------
    print("Testing Collected Company and simultaneous ETBs")
    startclock = time.perf_counter()

    game = GameState.GameState()
    #deck of 6 cards
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Axebane   ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Battlement),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest    ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest    ),ZONE.DECK)
    #put Collected Company directly onto the stack
    game.MoveZone( Cardboard.Cardboard(Decklist.Company   ),ZONE.STACK)
    assert(len(game.super_stack) == 0)
    
    #resolve Collected Company
    universes = game.ResolveTopOfStack()
    assert(len(universes)==4)
    for u in universes:
        assert(len(u.deck)==4)
        assert(len(u.field)==2)
        assert(len(u.grave)==1)
        if any([c.rules_text == Decklist.Axebane for c in u.field]):
            assert(not any([c.rules_text == Decklist.Axebane for c in u.deck]))
        if any([c.rules_text == Decklist.Battlement for c in u.field]):
            assert(not any([c.rules_text == Decklist.Battlement for c in u.deck]))
        assert(not any(["land" in c.rules_text.keywords for c in u.field]))

    #deck of 6 forests on top, then 10 islands
    gameF = GameState.GameState()
    for _ in range(6):
        gameF.MoveZone( Cardboard.Cardboard(Decklist.Forest ),ZONE.DECK)
    for _ in range(10):
        gameF.MoveZone( Cardboard.Cardboard(Decklist.Island ),ZONE.DECK)
    #should be forests on top
    assert(all([c.rules_text == Decklist.Forest for c in gameF.deck[:6]]))
    gameF.MoveZone( Cardboard.Cardboard(Decklist.Company    ),ZONE.STACK)
    universes = gameF.ResolveTopOfStack()
    assert(len(universes)==1)
    u = universes[0]
    #now should be islands on top, forests on bottom
    assert(all([c.rules_text == Decklist.Island for c in u.deck[:10]]))
    assert(all([c.rules_text == Decklist.Forest for c in u.deck[-6:]]))
    assert(len(u.field)==0)
    assert(len(u.grave)==1)
    
    #deck of 5 forests on top, one Caretaker, then 10 islands
    game1 = GameState.GameState()
    for _ in range(5):
        game1.MoveZone( Cardboard.Cardboard(Decklist.Forest ),ZONE.DECK)
    game1.MoveZone( Cardboard.Cardboard(Decklist.Caretaker ),ZONE.DECK)
    for _ in range(10):
        game1.MoveZone( Cardboard.Cardboard(Decklist.Island ),ZONE.DECK)
    assert(len(game1.deck)==16)
    game1.MoveZone( Cardboard.Cardboard(Decklist.Company    ),ZONE.STACK)
    universes = game1.ResolveTopOfStack()
    assert(len(universes)==1)
    u = universes[0]
    #now should be islands on top, forests on bottom
    assert(all([c.rules_text == Decklist.Island for c in u.deck[:10]]))
    assert(all([c.rules_text == Decklist.Forest for c in u.deck[-5:]]))
    assert(u.deck[-6].rules_text == Decklist.Island)
    assert(len(u.field)==1)
    assert(len(u.grave)==1)
    
    #deck of only 4 cards total, all Caretakers
    game4 = GameState.GameState()
    for _ in range(4):
        game4.MoveZone( Cardboard.Cardboard(Decklist.Caretaker ),ZONE.DECK)
    #should be forests on top
    assert( len(game4.deck)==4)
    game4.MoveZone( Cardboard.Cardboard(Decklist.Company    ),ZONE.STACK)
    universes = game4.ResolveTopOfStack()
    assert(len(universes)==1)
    u = universes[0]
    assert(len(u.deck )==2)
    assert(len(u.field)==2)
    assert(len(u.grave)==1)
 
    #Does Blossoms trigger correctly? start with 12 cards in deck
    game = GameState.GameState()
    game.MoveZone( Cardboard.Cardboard(Decklist.Blossoms  ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Omens     ),ZONE.DECK)
    for _ in range(10):
        game.MoveZone( Cardboard.Cardboard(Decklist.Forest),ZONE.DECK)
    #put Collected Company directly onto the stack
    game.MoveZone( Cardboard.Cardboard(Decklist.Company   ),ZONE.STACK)
    universes = game.ResolveTopOfStack()
    assert(len(universes)==2)  #the two draws could be on stack in either order
    u0,u1 = universes
    assert(u0 != u1)
    while len(u0.stack)>0:
        [u0] = u0.ResolveTopOfStack()
    while len(u1.stack)>0:
        [u1] = u1.ResolveTopOfStack()
    assert(u0==u1)
    assert(len(u0.hand)==2 and len(u0.deck)==8)
    
    #Note: if I put two identical Blossoms into play simultaneously, I STILL
    #will get two GameStates even though they are identical! And that's ok.
    #it's not worth the effort to optimize this out, right now.
    game = GameState.GameState()
    game.MoveZone( Cardboard.Cardboard(Decklist.Blossoms  ),ZONE.DECK)
    game.MoveZone( Cardboard.Cardboard(Decklist.Blossoms  ),ZONE.DECK)
    for _ in range(10):
        game.MoveZone( Cardboard.Cardboard(Decklist.Forest),ZONE.DECK)
    #put Collected Company directly onto the stack
    game.MoveZone( Cardboard.Cardboard(Decklist.Company   ),ZONE.STACK)
    universes = game.ResolveTopOfStack()
    assert(len(universes)==2)  #the two draws could be on stack in either order
    u0,u1 = universes
    assert(u0 == u1)
    while len(u0.stack)>0:
        [u0] = u0.ResolveTopOfStack()
    while len(u1.stack)>0:
        [u1] = u1.ResolveTopOfStack()
    assert(u0==u1)
    assert(len(u0.hand)==2 and len(u0.deck)==8)

    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )

    ###--------------------------------------------------------------------

    print("Testing WildCards, Cost2, and other new templating tech")
    startclock = time.perf_counter()

    game = GameState.GameState()
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker ),ZONE.FIELD)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker ),ZONE.FIELD)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest    ),ZONE.FIELD)
    game.MoveZone( Cardboard.Cardboard(Decklist.Battlement   ),ZONE.FIELD)
    game.MoveZone( Cardboard.Cardboard(Decklist.Axebane),ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest    ),ZONE.HAND)

    # ###---testing WildCards
    
    # wild = Actions.WildCard( zone=ZONE.DECK )
    # assert(sum([wild.compare(c) for c in game.field])==0)
    # assert(sum([wild.compare(c) for c in game.hand])==0)
    # wild = Actions.WildCard( zone=ZONE.FIELD )
    # assert(sum([wild.compare(c) for c in game.field])==4)
    # assert(sum([wild.compare(c) for c in game.hand])==0)

    # wild = Actions.WildCard( zone=ZONE.FIELD, rules_text=RulesText.Creature )
    # assert(sum([wild.compare(c) for c in game.field])==3)    
    # wild = Actions.WildCard( zone=ZONE.FIELD, rules_text=RulesText.Creature,
    #                          toughness=3)
    # assert(sum([wild.compare(c) for c in game.field])==2)
    # wild = Actions.WildCard( zone=ZONE.FIELD, rules_text=RulesText.Creature,
    #                          toughness=(">",3))
    # assert(sum([wild.compare(c) for c in game.field])==1)
    # wild = Actions.WildCard( zone=ZONE.FIELD, rules_text=RulesText.Creature,
    #                          toughness=(">",2))
    # assert(sum([wild.compare(c) for c in game.field])==3)
    # wild = Actions.WildCard( zone=ZONE.FIELD, toughness=("<",5))
    # assert(sum([wild.compare(c) for c in game.field])==3)
    
    # wild = Actions.WildCard( zone=ZONE.FIELD, rules_text=RulesText.Land)
    # assert(sum([wild.compare(c) for c in game.field])==1)
    # assert(sum([wild.compare(c) for c in game.hand])==0)
    # wild = Actions.WildCard( zone=ZONE.HAND, rules_text=RulesText.Land)
    # assert(sum([wild.compare(c) for c in game.field])==0)
    # assert(sum([wild.compare(c) for c in game.hand])==1)

    ###---testing Cost2 with ActionNoChoice's
    
    battle = [c for c in game.field if "battle" in c.name.lower()][0]
    forest = [c for c in game.field if "forest" in c.name.lower()][0]
    
    tapsymbol = Actions.Cost2( [Actions.TapSymbol()] )
    payGG = Actions.Cost2( [Actions.PayMana("GG")] )
    assert(not tapsymbol.CanAfford(game,battle )) #summon-sick
    assert(    tapsymbol.CanAfford(game,forest )) #land so it's fine
    assert(not payGG.CanAfford(game,forest )) #source irrelevant here
    game.pool.AddMana("GGG")
    assert( payGG.CanAfford(game,forest ))  #source still irrelevant
    univ_list = payGG.Pay(game,forest)
    assert(len(univ_list)==1)
    new_univ = univ_list[0][0]  #1st in list, then 1st of gamestate,source
    assert( new_univ.pool == ManaHandler.ManaPool("G") )
    assert( game.pool == ManaHandler.ManaPool("GGG") )  #didn't mutate
    game.UntapStep()
    assert( tapsymbol.CanAfford(game,battle )) #no longer summon-sick
    assert( tapsymbol.CanAfford(game,forest )) #land so it's fine
    assert( not tapsymbol.CanAfford(game,game.hand[0] )) #land so it's fine










    print ("      ...done, %0.2f sec" %(time.perf_counter()-startclock) )

    print("\n\npasses all tests!")