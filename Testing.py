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
        decklist.append(Decklist.Caretaker())
        decklist.append(Decklist.Caryatid())
        decklist.append(Decklist.Battlement())
        decklist.append(Decklist.Roots())
        decklist.append(Decklist.Axebane())
        decklist.append(Decklist.Recruiter())
        decklist.append(Decklist.Company())
    decklist.append(Decklist.Arcades())
    decklist.append(Decklist.Arcades())
    decklist.append(Decklist.Arcades())
    decklist.append(Decklist.TrophyMage())
    decklist.append(Decklist.TrophyMage())
    decklist.append(Decklist.Staff())    
    
    #22 lands, right now
    for i in range(4):
        decklist.append(Decklist.Westvale())
        decklist.append(Decklist.Forest())
    for i in range(2):
        decklist.append(Decklist.TempleGarden())
        decklist.append(Decklist.BreedingPool())
        decklist.append(Decklist.HallowedFountain())
        decklist.append(Decklist.Wildwoods())
        decklist.append(Decklist.LumberingFalls())
    decklist.append(Decklist.Forest())    
    decklist.append(Decklist.Forest())
    decklist.append(Decklist.Plains())
    decklist.append(Decklist.Island())
    
    
    game = GameState.GameState()
    game.deck = decklist
    game.Shuffle()
    
    for i in range(7):
        game.Draw()

    
    print(game)
    
    while game.turncount<=5 and len(game.hand)>0:
        print("\n--------------------turn %i------------------\n" %game.turncount)
        game.Upkeep(    verbose=True)
        if game.turncount>1:
            game.Draw(  verbose=True)
        game.MainPhase( verbose=True)
        game.PassTurn(  verbose=True)  #pass to opponent
        game.PassTurn(  verbose=True)  #pass back to self
    print("\n----------------------end--------------------\n")
    print(game)