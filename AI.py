# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 12:06:04 2020

@author: Cobi
"""

import Cards
import Decklist
# import ManaHandler




def ShouldPlayLand(gamestate):
    return not gamestate.playedland and len([card for card in gamestate.hand if isinstance(card,Cards.Land)])>0

def ChooseLandToPlay(gamestate):
    lands = [card for card in gamestate.hand if isinstance(card,Cards.Land)]
    #insert rankings here later  #needs actual logic!
    return lands[0]
    
    
    
def ChooseCardstoDiscard(gamestate):
    """Return a list of cards to discard at end of turn, if more than 7 cards in hand"""
    return gamestate.hand[len(gamestate.hand)-7:]


def ChooseCardToCast(gamestate):
    """Out of the list of cards in hand, return the card to cast next"""
    #in theory could also consider activating abilities here...?
    #in evaluating which is better, don't forget that Arcades draws cards...
    #get list of castable cards
    totalmana = gamestate.CMCAvailable()
    options = []
    mostafter = 0 #the amount of mana available after casting the card which generates the most mana
    
    for card in gamestate.hand:
        if isinstance(card,Cards.Land): continue #it's a land
        tappingsolution = gamestate.TappingSolutionForCost(card.cost)
        if tappingsolution is None: continue #too expensive or wrong colors
        options.append(card)
        futuremana = gamestate.CMCAvailableIfCast(card)
        if futuremana>mostafter:
            mostafter = futuremana
    
    if len(options)==0:
        return False
    
    #if any spells are free or net mana, cast those. List b/c might be tie
    #really should do something fancier here, involving whether I can cast any more spells afterwards
    if mostafter>=totalmana:    
        options=[c for c in options if gamestate.CMCAvailableIfCast(c)==mostafter]

    #sort options by priority order. better logic for this ordering?
    def rank(card):
        return [Decklist.Battlement,
                Decklist.Axebane,
                Decklist.Roots,
                Decklist.Caryatid,
                Decklist.Caretaker  ].index(type(card))
    options.sort(key=rank)
    
    return options[0]
    
    



def RankerMana(source):
    """Assign a "ranking" number to a given mana source. Low rank means should
    attempt to use first, high rank means valuable and should be saved for later.
    Note: function assumes input is a ManaSource objects."""
    assert(isinstance(source,Cards.ManaSource))
    rank = 0
    #most important: sort land->wall->scaling wall
    if isinstance(source,Cards.Creature): #all my creature mana dorks are defenders
        rank += 20
    if isinstance(source,Decklist.Battlement) or isinstance(source,Decklist.Axebane):
        rank += 20
    #and use mono-colored before multi-colored, where possible
    rank += len(source.tapsfor)
    #caretaker color identification may not work properly for caretakers with nothing to tap...
    if isinstance(source,Decklist.Caretaker):
        rank += 5
    return rank




def FindSolutionForGeneric(fullcost,colorsolution,source_indices,hypothet):
    """Find the mana sources to tap, and the colors to tap them for, to
       generate enough mana to pay the given cost.
    colorsolution - a list of (source index,color) pairs guaranteed to cover
                    the color needs of the given cost
    source_indices- indices (into hypothet.field) of all available mana sources
    hypothet      - a "fake" gamestate object where we can safely try
                    tapping for mana without affecting the real game"""
    #we know we'll need the sources from colorsolution, so get mana from those
    fullsolution = []
    for i,color in colorsolution:
        source = hypothet.field[i]
        source.MakeMana(hypothet,color) #add mana (mutates "hypothet" gamestate)
        fullsolution.append((i,color))
    #if we need even more mana (perhaps for generic costs?), work on that here
    k=0
    while k<len(source_indices) and not hypothet.pool.CanAffordCost(fullcost):
        index = source_indices[k]
        if index in [ind for ind,color in colorsolution]:
            k += 1 #skip, we already tapped this source
        else:
            source = hypothet.field[index]
            color = source.tapsfor[-1] #color doesn't matter here
            source.MakeMana(hypothet,color)
            fullsolution.append((index,color))
            k+=1
    if hypothet.pool.CanAffordCost(fullcost):
        return fullsolution
    else:
        return False #couldn't find a solution
        


def FindSolutionForColors(coloredcost,source_indices,hypothet):
    """Find the mana sources to tap, and the colors to tap them for, to
       generate enough mana to pay the COLORED PART of the given cost. The
       function entirely ignores the generic part of the cost.
       
    source_indices- indices (into hypothet.field) of all available mana sources.
    hypothet      - a "fake" gamestate object where we can safely try
                    tapping for mana without affecting the real game.
    Returns:  a list of tuples: (source index in hypothet.field,color) which will
              successfully pay the colored cost, or False if cost can't be paid."""
    
    coloredcost = coloredcost.copy()
    coloredcost.data["gen"] = 0
    #go through each source, seeing how each one contributes to the
    #colored part of the cost. Stop as soon as the cost is paid.
    accumulator = [(coloredcost,[])] #tuples: remaining colored cost,list of sources
    for k in source_indices:
        s = hypothet.field[k]
        newlist = []
        for color in s.tapsfor:
            for cost,firingsolution in accumulator:
                if cost.data[color]>0: #this cost needs this color
                    newcost = cost.copy()
                    newcost.data[color] -= 1
                    if newcost.CMC()==0: #we've found a good solution!
                        return firingsolution+[(k,color)]
                    else: #making progress, should track it, but we're not done yet
                        tup = (newcost,firingsolution+[(k,color)])    
                        newlist.append(tup)
        #replace the old accumulator with our progress.  maybe not safe???
        if len(newlist)>0:
            accumulator = newlist
        # #some nice print statements
        # for cost,firingsolution in accumulator:
        #     print("   ",str(cost),firingsolution)
    #if reached here, then couldn't cover the cost. Be sad.
    return False






    


