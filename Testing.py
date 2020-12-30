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
# =============================================================================
#     game = GameState.GameState()
#     game.field.append(Decklist.Westvale())
#     game.field.append(Decklist.HallowedFountain())
#     game.field.append(Decklist.Caryatid())
#     game.field.append(Decklist.Battlement())
#     game.hand.append(Decklist.Axebane())
#     game.Upkeep()
#     
#     
#     #check heritability of Manasource as a second inheritance
#     assert(isinstance(game.field[0],Cards.ManaSource))
#     
#     firingsolution = AI.TappingSolutionForCost(game,ManaHandler.ManaCost("1WUG"))
#     print( [(str(source),color) for source,color in firingsolution])
#     
#     firingsolution = AI.TappingSolutionForCost(game,ManaHandler.ManaCost("3G"))
#     print( [(str(source),color) for source,color in firingsolution])
#     
#     
#     print("\n\n\n")
# =============================================================================
##---------------------------------------------------------------------------##
    
    decklist = []
    for i in range(4):
        decklist.append(Decklist.Caretaker())
        decklist.append(Decklist.Caryatid())
        decklist.append(Decklist.Battlement())
        decklist.append(Decklist.Roots())
        decklist.append(Decklist.Axebane())
    for i in range(3):
        decklist.append(Decklist.Forest())
        decklist.append(Decklist.TempleGarden())
        decklist.append(Decklist.BreedingPool())
        decklist.append(Decklist.HallowedFountain())
    decklist.append(Decklist.Forest())
    decklist.append(Decklist.Plains())
    decklist.append(Decklist.Island())
    
    game = GameState.GameState()
    game.deck = decklist
    game.Shuffle()
    
    for i in range(7):
        game.Draw()
    

    # game.hand.append(Decklist.Forest())
    # game.hand.append(Decklist.BreedingPool())
    # game.hand.append(Decklist.Battlement())
    # game.hand.append(Decklist.Caryatid())
    # game.hand.append(Decklist.HallowedFountain())
    # game.hand.append(Decklist.Forest())
    
    print(game)
    while game.turncount<5 and len(game.hand)>0:
        print("\n--------------------turn %i------------------\n" %game.turncount)
        game.Upkeep(    verbose=True)
        if game.turncount>1:
            game.Draw(  verbose=True)
        game.MainPhase( verbose=True)
        game.PassTurn(  verbose=True)
        game.PassTurn(  verbose=True)
    print(game)