# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 12:06:04 2020

@author: Cobi
"""

import Cards
import Decklist






    
    
    
def RankedSources(gamestate):
    """make a ranked list of mana sources. Early in the list means should use first"""
    sources = []
    for perm in gamestate.field:
        if hasattr(perm,"MakeMana") and hasattr(perm,"unavailable") and not perm.unavailable:
            sources.append(perm)
    def GetRankOfManaSource(card):
        #low rank is use first, high rank is use as late as possible
        return [Decklist.Roots,
                Decklist.Plains,
                Decklist.Forest,
                Decklist.Shock,
                Decklist.ManLand,
                Decklist.Westvale,
                Decklist.Caretaker,
                Decklist.Caryatid,
                Decklist.Battlement,
                Decklist.Axebane    ].index(type(card))
    sources.sort(key=GetRankOfManaSource)
    return sources



def ChooseCardToCast(gamestate):
    """Out of the list of cards in hand, return the card to cast next"""
    #in theory could also consider activating abilities here...?
    #in evaluating which is better, don't forget that Arcades draws cards...
    #get list of castable cards
    potentialpool = gamestate.ManaAvailable()
    totalmana = potentialpool.CMC()
    options = []
    mostafter = 0 #the amount of mana available after casting the card which generates the most mana
    
    for card in gamestate.hand:
        if card.cost is None: continue #it's a land
        if not potentialpool.CanAffordCost(card.cost): continue #too expensive
        options.append(card)
        futuremana = gamestate.ManaAvailableIfCast(card).CMC()
        if futuremana>mostafter:
            mostafter = futuremana
    
    if len(options)==0:
        return False
    
    #if any spells are free or net mana, cast those. List b/c might be tie
    #really should do something fancier here, involving whether I can cast any more spells afterwards
    if mostafter>=totalmana:    
        options=[c for c in options if gamestate.ManaAvailableIfCast(c).CMC()==mostafter]
    
    
    
    
    #sort options by priority order. better logic for this ordering?
    def rank(card):
        return [Decklist.Battlement,
                Decklist.Axebane,
                Decklist.Roots,
                Decklist.Caryatid,
                Decklist.Caretaker  ].index(type(card))
    options.sort(key=rank)
    
    #options[0] is the best thing to cast, we've decided. but if we can ALSO cast
    #option 1 and still be able to cast option[0] afterwards, do that
    
    
    return options[0]
    
    
    

    
        
        
def CanICoverCost(gamestate,cost):
    """given a gamestate and a cost, can I cover that cost?"""
    sourcelist = [] #list of all available mana sources I can draw on
    for perm in gamestate.field:
        if hasattr(perm,"MakeMana") and hasattr(perm,"unavailable") and not perm.unavailable:
            sourcelist.append(perm)

    
