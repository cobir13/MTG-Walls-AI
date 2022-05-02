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
    game.verbose = True
    game.hand = decklist

    # print(game,"\n-------------\n")
    
    game.MoveZone(game.hand[0],ZONE.FIELD)


    options = game.GetValidActions()
    # print(options,"\n")
    [(copygame2,_)] = options[0].Run()
    # print(copygame2,"\n-------------\n")

    assert(copygame2.GetValidActions() == [] )
    
    # print("I add in an extra mana to see what happens\n")
    copygame2.pool.AddMana("G")
    # print(copygame2,"\n\n")
    
    options = copygame2.GetValidActions()
    # print(options,"\n")
    assert(len(options)==3)
    
    [(copygame3,_)] = options[0].Run()
    # print(copygame3,"\n\n")
    # print(copygame3.GetValidActions())
    assert(len(copygame3.field)==2)
    assert(len(copygame3.hand)==2)
    assert(str(copygame3.pool)=="")
    
    # print("\n-------------\nJust to check, game0 is still unchanged:")
    # print(game,"\n-------------\n")
    assert(len(game.field)==1)
    assert(str(game.pool)=="")
    
    ###---finished testing wall of Roots.  let's try Caryatid
    
    print("\n\n-------------")
    game.field.append(Cardboard.Cardboard(Decklist.Caryatid,ZONE.FIELD))
    print(game,"\n-------------\n")
    options = game.GetValidActions()
    print(options,"\n")
    [(carygame1,_)] = options[0].Run()
    assert(len(options)==1)
    print(carygame1,"\n-------------\n")
    
    print("\nuntap and upkeep\n")
    carygame1.Untap()
    carygame1.Upkeep()
    print(carygame1,"\n")
    options = carygame1.GetValidActions()
    print(options,"\n")
    assert(len(options)==2)
    # print(carygame1,"\n-------------\n")
    
    while len(options)>0:
        (gameN,_) = options[0].Run()[0]
        options = gameN.GetValidActions()
        print(options)
    print("\n\n",gameN,"\n-------------\n")
    assert(len(gameN.hand)==2)
    assert(len(gameN.field)==3)
    assert(gameN.pool == ManaHandler.ManaPool("G"))
    
    

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