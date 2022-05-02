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
# import AI



if __name__ == "__main__":

    decklist = []
    for i in range(4):
        decklist.append( Cardboard.Cardboard(Decklist.Roots,ZONE.HAND) )

    game = GameState.GameState()
    game.verbose = False #True
    game.hand = decklist
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
    game.field.append(Cardboard.Cardboard(Decklist.Caryatid,ZONE.FIELD))
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
                print("Taking 0th option in list")
            universes = options[0].Run()
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
    game.verbose = True
    game.field.append( Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD))
    game.field.append( Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD))
    forest = Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD)
    game.field.append( forest )
    game.hand.append( Cardboard.Cardboard(Decklist.Plains,ZONE.HAND))
    plains = Cardboard.Cardboard(Decklist.Plains,ZONE.HAND)
    game.hand.append( plains )
    
    print(game.GetValidActions())
    assert(len(game.GetValidActions())==2)
    #tap one forest, I'll still have the option to tap more forests
    [(gameF,forestF)] = forest.cardtype.activated[0].PayAndExecute(game,forest)
    print(gameF.GetValidActions())
    assert(len(gameF.GetValidActions())==2)
    assert(gameF.pool == ManaHandler.ManaPool("G"))
    assert(forest.tapped == False)  #original forest untouched
    assert(forestF.tapped == True)  #copy of forest is tapped
    print("done testing forest")
    #play one plains, I'll lose option to play plains but get to tap plains now
    [(gameP,plainsP)] = plains.cardtype.Cast(game,plains)
    print(gameP.GetValidActions())
    assert(len(gameP.GetValidActions())==2)
    assert(len(gameP.hand)==1)
    assert(len(gameP.field)==4)
    assert(gameP.pool == ManaHandler.ManaPool(""))
    #untap and go to next turn, should have 3 options again: play, tap W, tap G
    gameP.Untap()
    gameP.Upkeep()
    print("untap,upkeep...\n",gameP)
    print(gameP.GetValidActions())
    assert(len(gameP.GetValidActions())==3)
    
    
    
    #original game is untouched
    assert(len(game.hand)==2)
    assert(game.pool == ManaHandler.ManaPool(""))
    
    # ###--------------------------------------------------------------------
    
    
    # #testing basic lands
    # game = GameState.GameState()
    # game.verbose = False
    # game.field.append( Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD))
    # game.field.append( Cardboard.Cardboard(Decklist.Plains,ZONE.FIELD))
    # game.hand.append( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND))
    # game.hand.append( Cardboard.Cardboard(Decklist.Forest,ZONE.HAND))
    # game.hand.append( Cardboard.Cardboard(Decklist.Roots,ZONE.HAND))
    # game.hand.append( Cardboard.Cardboard(Decklist.Caryatid,ZONE.HAND))
                      
    # gameN = BasicLoop(game)
    # assert(len(gameN.hand)==1)
    # assert(len(gameN.field)==5)
    # assert(gameN.pool == ManaHandler.ManaPool(""))
    # assert(len(game.field)==2)  #orig game is untouched

    # ###--------------------------------------------------------------------
    
    # #testing shocklands
    # game = GameState.GameState()
    # game.verbose = False
    # game.field.append( Cardboard.Cardboard(Decklist.Forest,ZONE.FIELD))
    # game.hand.append( Cardboard.Cardboard(Decklist.BreedingPool,ZONE.HAND))
    # game.hand.append( Cardboard.Cardboard(Decklist.Caryatid,ZONE.HAND))
                      
    # gameN = BasicLoop(game)
    # assert(len(gameN.hand)==0)
    # assert(len(gameN.field)==3)
    # assert(gameN.pool == ManaHandler.ManaPool(""))
    # assert(gameN.life == 18)


























    # decklist = []
    # #34 nonlands, right now
    # for i in range(4):
    #     #walls
    #     decklist.append(Decklist.Caretaker())
    #     decklist.append(Decklist.Caryatid())
    #     decklist.append(Decklist.Battlement())
    #     decklist.append(Decklist.Roots())
    #     decklist.append(Decklist.Axebane())
    #     #everything else
    #     decklist.append(Decklist.Recruiter())
    #     decklist.append(Decklist.Company())
    # for i in range(3):
    #     decklist.append(Decklist.Arcades())
    # for i in range(2):
    #     decklist.append(Decklist.Blossoms())
    #     decklist.append(Decklist.TrophyMage())
    # decklist.append(Decklist.Shalai())
    # decklist.append(CardType.Creature("Deputy", "1WU", 1,3, []))
    # decklist.append(CardType.Creature("Ooze", "1G", 2,2, []))
    # # decklist.append(Decklist.Staff())    
    
    # #22 lands, right now
    # for i in range(4):
    #     decklist.append(Decklist.Westvale())
    #     decklist.append(Decklist.WindsweptHeath())
    # for i in range(5):
    #     decklist.append(Decklist.Forest())
    # for i in range(2):
    #     decklist.append(Decklist.Wildwoods())
    #     decklist.append(Decklist.LumberingFalls())
    # decklist.append(Decklist.TempleGarden())
    # decklist.append(Decklist.BreedingPool())
    # decklist.append(Decklist.HallowedFountain())
    # decklist.append(Decklist.Plains())
    # decklist.append(Decklist.Island())
    

    
    
    # winturn = []
    
    # # for trial in range(500):

    # game = GameState.GameState()
    # for c in decklist:
    #     game.AddToDeck(c)
    # game.Shuffle()        
    # for i in range(7):
    #     game.Draw()


    # game.verbose = True
        
    # try:
    #     while game.turncount<10:
    #         game.TurnCycle()
    # except IOError as e:
    #     resultstring = repr(e)
    #     if "WINS" in resultstring:
    #         winturn.append(game.turncount)
    #         if game.verbose:
    #             print("\n----------------------end--------------------\n")
    #             print(resultstring[resultstring.index("("):].strip("()'"),"turn %i" %game.turncount)
    #             print(game)
            
    #     elif "LOSE" in resultstring:
    #         print(resultstring[resultstring.index("("):].strip("()'"))
    #         print(game)
    #         print(len(game.hand),len(game.field),len(game.deck))
    #         print(len(game.hand)+len(game.field)+len(game.deck))
    #         print([c.name for c in game.deck])
    #         # break
                
            
    # # import numpy as np
    # # hist,turns = np.histogram(winturn,bins=np.arange(1,np.max(winturn)+1))

    # # print("")
    # # print("wins:"," ".join(["%4i" %n for n in hist]))
    # # print("turn:"," ".join(["%4i" %n for n in turns[:-1]]))

    # # print(np.sum(hist),"total games")