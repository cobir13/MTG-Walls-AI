# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 12:06:04 2020

@author: Cobi
"""

import Cards
import Decklist
# import ManaHandler




def ChooseActionToTake(gamestate):
    """For the given gamestate, what action should we take next? Land-drop,
        cast a spell, activate ability, or pass turn?
    Returns a string from {"land","spell","ability","pass"} and an object
        to take the action with (or None, for the "pass" option)   
    """
    lands,castables,uncastables = gamestate.ShowHandAsSorted()
    abilities = gamestate.GetAvailableAbilities()
    
    #simple logic: play land; then cast spells; then activate abilities if mana left
    
    if lands and not gamestate.playedland:
        return "land",ChooseLandToPlay(gamestate)
    
    if castables:
        totalmana = gamestate.CMCAvailable()
        def NetCostToCast(card): #might be negative
            return totalmana - gamestate.CMCAvailableIfCast(card)
        netcosts = [ NetCostToCast(c) for c in castables ]
        minn = min(netcosts)
        #if any spells are free or GAIN us mana, restrict our attention to cast
        #those first. They're literally free!
        if minn<=0: 
            castables=[c for c in castables if NetCostToCast(c)==minn]
        #rank within these remaining options, b/c might still be ties.
        #...really should do something involving whether I can cast any more spells afterwards...
        castables.sort(key=lambda c: RankerSpells(c,gamestate))
        #look aheady to see if we can do several spells at once?
        return "spell",castables[0]
    
    if abilities:
        #GetAvailableAbilities already checked, they're affordable
        #if given a choice, I want to use duskwatch before making tokens with westvale.
        #so I will do a Stupid Sort based on CMC, since recruiting is cheaper
        abilities.sort(key=lambda ab:ab.cost.CMC())
        return "ability",abilities[0]

    #if reached here, then there's nothing to do. be sad and pass turn
    return "pass",None





def ChooseLandToPlay(gamestate):
    landsinhand = [card for card in gamestate.hand if isinstance(card,Cards.Land)]
    landsinplay = [card for card in gamestate.field if isinstance(card,Cards.Land)]
    
    #if no 1-drops and no lands in play, play a tapland
    onedrops = [c for c in gamestate.hand if (not isinstance(c,Cards.Land) and c.cost.CMC()==1)]
    if len(onedrops)==0:
        taplands = [c for c in landsinhand if c.tapped]
        if taplands:
            return taplands[0]

    #if green in hand but not in play, play a green source
    greeninplay  = [c for c in landsinplay if "G" in c.tapsfor]
    greensinhand = [c for c in landsinhand if "G" in c.tapsfor]
    
    if len(greensinhand)>0 and len(greeninplay)==0:
        return greensinhand[0]
    
    return landsinhand[0]
    
    
    
    
    
def ChooseCardstoDiscard(gamestate):
    """Return a list of cards to discard at end of turn, if more than 7 cards in hand"""
    return gamestate.hand[:len(gamestate.hand)-7]

def ChooseTrophyMageTarget(gamestate):
    options = []
    for card in gamestate.deck:
        if "artifact" in card.typelist and card.cost.CMC()==3:
            options.append(card)
    if len(options)>0:
        return options[0] #if no options, return None
    
def ChooseRecruit(gamestate,options):
    return options[0] #for now, no logic at all

def ChooseCompany(gamestate,options):
    ranked = sorted(options,key=lambda c: RankerSpells(c,gamestate))
    return ranked[:2] #for now, no logic at all





def RankerMana(source,gamestate):
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


def RankerSpells(spell,gamestate):
    """Assign a "priority" number to a given spell. Low number means should be
    played as quickly as possible, high number means less critical."""
    rank = 100
    if isinstance(spell,Cards.ManaSource):
        rank = 10
        if isinstance(spell,Decklist.Battlement) or isinstance(spell,Decklist.Axebane):
            rank = 7
    elif isinstance(spell,Decklist.Company): #company is usually better than Walls
        rank = 4
    elif isinstance(spell,Decklist.Arcades):
        if len([c for c in gamestate.hand if "defender" in c.typelist])>1:
            rank = 4
        else:
            rank = 15
    elif isinstance(spell,Decklist.TrophyMage) or isinstance(spell,Decklist.Staff):
        rank = 20
        defenderlist = [c for c in gamestate.field if "defender" in c.typelist]
        if len(defenderlist)>=5:
            rank -= 9
        scaler_ready = False
        for c in defenderlist:
            if (isinstance(c,Decklist.Battlement) or isinstance(c,Decklist.Axebane)) and not c.unavailable:
                scaler_ready = True
                break
        if scaler_ready:
            rank -= 9
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






    


