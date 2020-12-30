# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""

import random
import Decklist
import Cards
from ManaHandler import ManaPool
import AI



class GameState():
    def __init__(self):
        self.deck = []
        self.hand = []
        self.field = []
        self.pool = ManaPool("")
        

        self.turncount = 1
        self.myturn = True
        
        self.life = 20
        self.playedland = False

        
    def Shuffle(self):
        random.shuffle(self.deck)
        
    def Upkeep(self):
        """untap, upkeep, and draw"""
        for permanent in self.field:
            permanent.Untap()
        for permanent in self.field:
            permanent.Upkeep()
            
    def Draw(self):
        if self.deck: #if at least one card left
            self.hand.append(self.deck.pop(0)) #removes from 0th index of deck
        else: #ran out of cards
            print("YOU LOSE")
            raise IOError
            
    def MainPhase(self):
        while (game.ShouldPlayLand() or AI.ChooseCardToCast(game)):
            if game.ShouldPlayLand():
                land = game.ChooseLandToPlay()
                print("playing:",str(land))
                game.PlayLand(land)
            else:
                card = AI.ChooseCardToCast(game)
                print("casting:",str(card))
                #generate the necessary mana.
                game.GenerateManaForCost(card.cost)
                #cast the chosen spell
                oldpool = str(game.pool)
                game.CastSpell(card)
                print(oldpool,"|",str(game.pool),"|")
            
            
            
    def Attack(self):
        pass
    
    
    def PassTurn(self):
        #discard to hand size?
        if not self.myturn:
            self.turncount += 1
            self.playedland = False
        self.myturn = not self.myturn
        
        #start the new turn
  
##---------------------------------------------------------------------------##   

    def __str__(self):
        #sort first somehow? locally only, not mutating
        txt = "HAND:\n   "+",".join([str(card) for card in self.hand])
        txt+= "\n"
        txt+= "FIELD:\n   "+",".join([str(card) for card in self.field])
        return txt



##---------------------------------------------------------------------------##      
  
    def PlayLand(self,land):
        assert(not self.playedland)
        if hasattr(land, "Effect"):
            getattr(land,"Effect")(self)
        self.hand.remove(land)
        self.field.append(land)
        self.playedland = True
        
    def ShouldPlayLand(self):
        return not self.playedland and len([card for card in self.hand if isinstance(card,Cards.Land)])>0
    
    def ChooseLandToPlay(self):
        lands = [card for card in self.hand if isinstance(card,Cards.Land)]
        #insert rankings here later
        return lands[0]
    
##---------------------------------------------------------------------------##   
        
    def CastSpell(self,card):
        assert(self.pool.CanAffordCost(card.cost))
        self.pool.PayCost(card.cost)        
        if hasattr(card, "Effect"):
            getattr(card,"Effect")(self)
        self.hand.remove(card)
        if isinstance(card,Cards.Permanent):
            self.field.append(card)
    
    
    def GenerateManaForCost(self,cost):
        sources = AI.RankedSources(self)
        #flipped duskwatch recruiter?
        k=0
        while not self.pool.CanAffordCost(cost):
            #be slightly less stupid here. don't tap a Plains if I need GG, for example...
            sources[k].MakeMana(self)
            k+=1




##-------------------Alternate Universe Functions----------------------------##

    def ManaAvailableIfCast(self,card):
        """casting defenders sometimes nets mana back. if I cast this card,
        how much mana will I have available afterwards?  Assumes card IS castable"""
        #just casts the card in an alternate gamestate and evaluates the result
        hypothet = GameState()
        hypothet.field = [c.copy() for c in self.field]
        coil = card.copy()
        hypothet.hand = [coil]
        hypothet.pool = self.pool.copy()
        hypothet.GenerateManaForCost(coil.cost)
        hypothet.CastSpell(coil)
        return hypothet.ManaAvailable()
        #flipped duskwatch recruiter?
        

    def ManaAvailable(self):
        hypothet = GameState()
        hypothet.field = [c.copy() for c in self.field]
        hypothet.pool = self.pool.copy()
        for permanent in hypothet.field:
            if hasattr(permanent, "MakeMana"):
                permanent.MakeMana(hypothet) #mutates the "hypothet" gamestate
        return hypothet.pool




##---------------------------------------------------------------------------##











if __name__ == "__main__":
    decklist = []
    for i in range(4):
        decklist.append(Decklist.Caretaker())
        decklist.append(Decklist.Caryatid())
        decklist.append(Decklist.Battlement())
        decklist.append(Decklist.Roots())
        decklist.append(Decklist.Axebane())
    for i in range(15):
        decklist.append(Decklist.Forest())
    
    
    game = GameState()
    game.deck = decklist
    game.Shuffle()
    
    
    
    for i in range(6):
        game.Draw()
    
    # game.hand.append(Decklist.Caretaker())
    # game.hand.append(Decklist.Caryatid())
    # game.hand.append(Decklist.Battlement())
    # game.hand.append(Decklist.Roots())
    # game.hand.append(Decklist.Axebane())
    # game.hand.append(Decklist.Forest())
    # game.hand.append(Decklist.Forest())
    
    
    # game.hand.append(Decklist.Caretaker())
    # game.hand.append(Decklist.Caretaker())
    # game.hand.append(Decklist.Caretaker())
    # game.hand.append(Decklist.Battlement())
    # game.hand.append(Decklist.Caryatid())
    # game.hand.append(Decklist.Forest())
    # game.hand.append(Decklist.Forest())
    
    
    print(game)

    while game.turncount<5 and len(game.hand)>0:
        
        print("\n--------------------turn %i------------------\n" %game.turncount)
        game.Upkeep()
        game.Draw()
        game.MainPhase()
        game.PassTurn()
        game.PassTurn()
        

        
    print(game)