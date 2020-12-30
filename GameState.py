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
        
    def Upkeep(self,verbose=False):
        """untap, upkeep, and draw"""
        for permanent in self.field:
            permanent.Untap()
        for permanent in self.field:
            permanent.Upkeep()
            
    def Draw(self,verbose=False):
        if self.deck: #if at least one card left
            card = self.deck.pop(0)
            if verbose: print("drawing:",str(card))
            self.hand.append(card) #removes from 0th index of deck
        else: #ran out of cards
            print("YOU LOSE")
            raise IOError
            
    def MainPhase(self,verbose=False):
        while (AI.ShouldPlayLand(self) or AI.ChooseCardToCast(self)):
            if AI.ShouldPlayLand(self):
                land = AI.ChooseLandToPlay(self)
                if verbose: print("playing:",str(land))
                self.PlayLand(land)
            else:
                card = AI.ChooseCardToCast(self)
                #generate the necessary mana.
                firingsolution = self.TappingSolutionForCost(card.cost)
                if verbose: print("floating",[ (str(source),color) for source,color in firingsolution] )
                self.GenerateManaForCasting(firingsolution)
                #cast the chosen spell
                if verbose: print("casting:",str(card))
                self.CastSpell(card)
            
            
            
    def Attack(self,verbose=False):
        pass
    
    
    def PassTurn(self,verbose=False):
        #discard down to 7 cards
        if len(self.hand)>7:
            discardlist = AI.ChooseCardstoDiscard(self)
            if verbose:
                print("discard:",[str(c) for c in discardlist])
            for card in discardlist:
                self.hand.remove(card)
        #clear any floating mana
        if verbose and self.pool.CMC()>0:
            print("end with %s" %(str(game.pool)))
        for color in self.pool.data.keys():
            self.pool.data[color] = 0 
        #pass the turn
        if not self.myturn:
            self.turncount += 1
            self.playedland = False
        self.myturn = not self.myturn
        

  
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
        

    def GenerateManaForCasting(self,firingsolution):
        for source,color in firingsolution:
            source.MakeMana(self,color)
        #flipped duskwatch recruiter?
        

    def CastSpell(self,card):
        assert(self.pool.CanAffordCost(card.cost))
        self.pool.PayCost(card.cost)        
        if hasattr(card, "Effect"):
            getattr(card,"Effect")(self)
        self.hand.remove(card)
        if isinstance(card,Cards.Permanent):
            self.field.append(card)
    


##-------------------Alternate Universe Functions----------------------------##


    def TappingSolutionForCost(self,cost):
        """given a gamestate and a cost, can I cover that cost?  Returns None if
        no, returns a list of (source,color) tuples to use if yes."""
        hypothet = GameState()
        hypothet.field = [c.copy() for c in self.field]
        hypothet.pool = self.pool.copy()
        
        #use up any floating mana, first
        colorcost = cost.copy()
        for color,amount in hypothet.pool.data.items():
            assert(amount>=0) #mana pools should be positive...
            colorcost.data[color] = max(colorcost.data[color]-amount,0)
        if colorcost.CMC()==0:
            return [] #we covered the cost with just our floating mana!
        
        #if reached here, we'll need to draw on actual mana sources. List possibilities.
        sourcelist = [] #list of indices in hypothet.field, b/c index translates across universes
        for k,perm in enumerate(hypothet.field):
            if isinstance(perm,Cards.ManaSource) and not perm.unavailable:         
                if isinstance(perm,Decklist.Caretaker) and not perm.CanMakeMana(hypothet):
                    continue #"unavailable" is unreliable for Caretakers, need special check
                sourcelist.append(k)
        
        #sort the sourcelist: try beginning sources first, save last sources for later
        #monocolors at the beginning, pure gold at the end
        sourcelist.sort(key=lambda i: AI.RankerMana(hypothet.field[i]))
        
        #is there a solution to covering the colored part of the cost?
        colorsolution = AI.FindSolutionForColors(colorcost, sourcelist,hypothet)
        if not colorsolution:
            return None #no, we can't cover the cost. couldn't get the colors to work out.
        
        #now time to work out how to cover the non-colored bit
        fullsolution = AI.FindSolutionForGeneric(cost,colorsolution,sourcelist,hypothet)
        if not fullsolution:
            return None #no, we can't cover the cost. don't have enough mana total
        else:
            return [ ( self.field[index],color ) for index,color in fullsolution]



    def CMCAvailable(self):
        """How much mana (ignoring color) is available to me right now?"""
        hypothet = GameState()
        hypothet.field = [c.copy() for c in self.field]
        hypothet.pool = self.pool.copy()
        for permanent in hypothet.field:
            if isinstance(permanent,Cards.ManaSource):
                #add mana (by mutating "hypothet" gamestate)
                permanent.MakeMana(hypothet,permanent.tapsfor[0])
        return hypothet.pool.CMC()


    def CMCAvailableIfCast(self,card):
        """casting defenders sometimes nets mana back. if I cast this card,
        how much mana will I have available afterwards?  Assumes card IS castable"""
        #just casts the card in an alternate gamestate and evaluates the result
        hypothet = GameState()
        hypothet.field = [c.copy() for c in self.field]
        coil = card.copy()
        hypothet.hand = [coil]
        hypothet.pool = self.pool.copy()
        firingsolution = hypothet.TappingSolutionForCost(card.cost)
        hypothet.GenerateManaForCasting(firingsolution)
        hypothet.CastSpell(coil)
        return hypothet.CMCAvailable()
        #flipped duskwatch recruiter?
        


##---------------------------------------------------------------------------##











if __name__ == "__main__":
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
    
# Westvale
# Wildwoods
# LumberingFalls
        
        
        
        
        
        
        
        
        
        
        
        
        
        
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