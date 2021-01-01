# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 22:15:57 2020

@author: Cobi
"""


import GameState
import ManaHandler
import Cards
import Decklist
import AI



if __name__ == "__main__":


    decklist = []
    #34 nonlands, right now
    for i in range(4):
        #walls
        decklist.append(Decklist.Caretaker())
        decklist.append(Decklist.Caryatid())
        decklist.append(Decklist.Battlement())
        decklist.append(Decklist.Roots())
        decklist.append(Decklist.Axebane())
        #everything else
        decklist.append(Decklist.Recruiter())
        decklist.append(Decklist.Company())
    for i in range(3):
        decklist.append(Decklist.Arcades())
    for i in range(2):
        decklist.append(Decklist.Blossoms())
        decklist.append(Decklist.TrophyMage())
    decklist.append(Cards.Creature("Shalai", "3W", 3, 4, ["flying"]))
    decklist.append(Cards.Creature("Deputy", "1WU", 1,3, []))
    decklist.append(Cards.Creature("Ooze", "1G", 2,2, []))
    decklist.append(Decklist.Staff())    
    
    #22 lands, right now
    for i in range(4):
        decklist.append(Decklist.Westvale())
        decklist.append(Decklist.WindsweptHeath())
    for i in range(5):
        decklist.append(Decklist.Forest())
    for i in range(2):
        decklist.append(Decklist.Wildwoods())
        decklist.append(Decklist.LumberingFalls())
    decklist.append(Decklist.TempleGarden())
    decklist.append(Decklist.BreedingPool())
    decklist.append(Decklist.HallowedFountain())
    decklist.append(Decklist.Plains())
    decklist.append(Decklist.Island())
    

    
    
    winturn = []
    
    for trial in range(500):

        game = GameState.GameState()
        game.deck = decklist[:]
        game.Shuffle()        

        try:
            for i in range(7):
                game.Draw()
                
            # print(game)
            
            while True:
                # print("\n--------------------turn %i------------------\n" %game.turncount)
                game.Upkeep(    verbose=False)
                if game.turncount>1:
                    game.Draw(  verbose=False)
                game.MainPhase( verbose=False)
                game.PassTurn(  verbose=False)  #pass to opponent
                game.PassTurn(  verbose=False)  #pass back to self
            # print("\n----------------------end--------------------\n")
            # print(game)
        except IOError as e:
            resultstring = repr(e)
            if "WINS" in resultstring:
                winturn.append(game.turncount)
                # print("wins on turn %i" %game.turncount)
                
            elif "LOSE" in resultstring:
                print(resultstring[resultstring.index("("):].strip("()'"))
                print(game)
                print(len(game.hand),len(game.field),len(game.deck))
                print(len(game.hand)+len(game.field)+len(game.deck))
                print([c.name for c in game.deck])
                break
                
            
    import numpy as np
    hist,turns = np.histogram(winturn,bins=np.arange(1,np.max(winturn)+1))

    print("")
    print("wins:"," ".join(["%4i" %n for n in hist]))
    print("turn:"," ".join(["%4i" %n for n in turns[:-1]]))

    print(np.sum(hist),"total games")