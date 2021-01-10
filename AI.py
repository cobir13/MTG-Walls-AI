# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 12:06:04 2020

@author: Cobi
"""

import CardType
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
    
    #simple logic: play land; then cast spells and activate abilities according to rank
    
    if lands and not gamestate.playedland:
        return "land",ChooseLandToPlay(gamestate)
    
    #if any free castables, grab those
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
        #...really should do something involving whether I can cast any more spells afterwards...
        
    #decorate the castables and abilities with their rank
    card_ranking,ability_ranking = MasterRanker(gamestate)
    fulllist = []
    for spell in castables:
        if type(spell) in card_ranking:
            fulllist.append( (card_ranking[type(spell)],spell) )
        else:
            fulllist.append( (200,spell) )
    for ab in abilities:
        tup = type(ab.card),ab.cost.CMC()
        if tup in ability_ranking:
            fulllist.append( (ability_ranking[tup],ab) )
        else:
            fulllist.append( (205,ab) )
    #sort according to their rank
    fulllist.sort(key=lambda tup: (tup[0],str(tup[1])) )
    if len(fulllist)>0:
        telltype = "ability" if isinstance(fulllist[0][1],CardType.Ability) else "spell"
        return telltype,fulllist[0][1]

    #if reached here, fulllist is empty and there's nothing to do. be sad and pass turn
    return "pass",None





def ChooseLandToPlay(gamestate):
    landsinhand = [card for card in gamestate.hand if isinstance(card,CardType.Land)]
    landsinplay = [card for card in gamestate.field if isinstance(card,CardType.Land)]
    
    #if no 1-drops and no lands in play, play a tapland
    onedrops = [c for c in gamestate.hand if (not isinstance(c,CardType.Land) and c.cost.CMC()==1)]
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
    ranked = sorted(gamestate.hand,key=lambda c: RankerSpellsToCast(c,gamestate))
    save_at_all_costs = []
    for card in ranked:
        if isinstance(card,Decklist.Staff) or isinstance(card,Decklist.Arcades):
            ranked.remove(card)
            save_at_all_costs.append(card)
    ranked = save_at_all_costs + ranked
    return ranked[7:]

def ChooseTrophyMageTarget(gamestate):
    opts = [c for c in gamestate.deck if ("artifact" in c.typelist and c.cost.CMC()==3)]
    if len(opts)>0: #if no options, returns None
        return opts[0] 
    
def ChooseRecruit(gamestate,options):
    ranked = sorted(options,key=lambda c: RankerSpellsToCast(c,gamestate))
    return ranked[0]

def ChooseCompany(gamestate,options):
    ranked = sorted(options,key=lambda c: RankerSpellsToCast(c,gamestate))
    return ranked[:2]

def ChooseSacToOrmendahl(gamestate):
    critters = [c for c in gamestate.field if isinstance(c,CardType.Creature)]
    ranked = sorted(critters,key=lambda c: RankerSpellsToCast(c,gamestate)) #this is JUST WRONG RANKER but ok logic for now
    return ranked[-5:]


def ChooseFetchTarget(gamestate,landtypes):    
    """Decide what land to fetch. Current logic doesn't look at hand, only at field"""
    fetchables = [c for c in gamestate.deck if any([isinstance(c,t) for t in landtypes]) ]
    #see what colors we need in play
    landsinplay = [card for card in gamestate.field if isinstance(card,CardType.Land)]
    missingcolors = []
    for color in ["G","U","W"]:
        if not any([color in c.tapsfor for c in landsinplay]):
            missingcolors.append(color)
    #try to get a land that matches the colors we want
    if len(missingcolors) == 3:
        missingcolors = ["G","U"] #no tri-lands, so prioritize getting green and blue
    while len(missingcolors) in [1,2]:
        options = []
        for card in fetchables:
            if all([color in card.tapsfor for color in missingcolors]):
                options.append(card) #grab any card that taps for all the colors we want
        if len(options)>0:
            break
        #if we couldn't get both, settle for one. G if we need it, otherwise whatever. breaks look if len 1
        missingcolors = missingcolors[:-1] if missingcolors[0]=="G" else missingcolors[1:]
    if len(missingcolors) == 0: #either b/c we tried to find colors and gave up, or we
        options = fetchables    #had all our colors to start with     
    if options:
        #ideally get a dual.  if not, get anything
        choice = sorted(options,key=lambda c: len(c.tapsfor))[0]
        # print("      fetch",choice)
        return choice

    


def RankerMana(source,gamestate):
    """Assign a "ranking" number to a given mana source. Low rank means should
    attempt to use first, high rank means valuable and should be saved for later.
    Note: function assumes input is a ManaSource objects."""
    assert(isinstance(source,CardType.ManaSource))
    rank = 0
    #most important: sort land->wall->scaling wall
    if isinstance(source,CardType.Creature): #all my creature mana dorks are defenders
        rank += 20
    if isinstance(source,Decklist.Battlement) or isinstance(source,Decklist.Axebane):
        rank += 20
    #and use mono-colored before multi-colored, where possible
    rank += len(source.tapsfor)
    #caretaker color identification may not work properly for caretakers with nothing to tap...
    if isinstance(source,Decklist.Caretaker):
        rank += 5
    return rank



def MasterRanker(gamestate):
    """Returns a priority ranking for the given spell. Low number means should
    be played as quickly as possible, high number means less critical. Doesn't
    worry about castability, just what we WANT to do.
    Note: ranking of 300+ means "please never do unless you have NO other options" """
    #base rankings of the cards. Will change based on gamestate events
    card_ranking = {#Arcades turbocharges every other wall, and company is two cards
                    Decklist.Arcades    : 10,
                    Decklist.Company    : 11,
                    #mana-walls are the next most important
                    Decklist.Axebane    : 30,
                    Decklist.Battlement : 31,
                    Decklist.Caryatid   : 32,
                    Decklist.Roots      : 33,
                    Decklist.Caretaker  : 34,
                    #Need to get mana online before casting these, they're low priority
                    Decklist.Recruiter  : 51,
                    Decklist.Blossoms   : 52,
                    #our eventual wincons are very bad, until we meet certain conditions
                    Decklist.Staff      : 70,
                    Decklist.TrophyMage : 71    }
    #base ranks of abilities. keyed by cardname and CMC
    ability_ranking = { "recruit"       : 100, #duskwatch recruiter
                        "pump"          : 105, #shalai
                        "makecleric"    : 101, #westvale
                        "ormendahl"     : 1 } #flip westvale
    ###--OK, look at the gamestate and see if our priorities should change
    #list of things we might care about
    haveArcades = False
    haveRecruiter = False
    haveStaffPlay = False
    haveStaffHand = False
    defenders = 0
    scalers_notsick = 0
    #find out which of these things are really true or false
    for permanent in gamestate.field:
        haveArcades   = isinstance(permanent,Decklist.Arcades  ) or haveArcades
        haveRecruiter = isinstance(permanent,Decklist.Recruiter) or haveRecruiter
        haveStaffPlay = isinstance(permanent,Decklist.Staff    ) or haveStaffPlay
        if "defender" in permanent.typelist:
            defenders += 1
        if isinstance(permanent,Decklist.Battlement) or isinstance(permanent,Decklist.Axebane):
            if not permanent.summonsick:
                scalers_notsick += 1
    for permanent in gamestate.hand:
        haveStaffHand = isinstance(permanent,Decklist.Staff    ) or haveStaffHand
    ###---adjust the rankings accordingly   
    if haveArcades:
        card_ranking[Decklist.Arcades] = 300 #Arcades legend rule
        card_ranking[Decklist.Blossoms] = 50 #draw-wall beats recruiter if Arcades out
    if haveRecruiter:
        card_ranking[Decklist.Recruiter] = 300 #only ever need one recruiter
    if defenders >= 5:
        card_ranking[Decklist.Staff]       = 25  #staff is now more important than more walls
        card_ranking[Decklist.TrophyMage]  = 26  #staff is now more important than more walls
        if scalers_notsick: #LITERALLY ready to combo this moment
            ability_ranking[(Decklist.Recruiter,3)] = 27 #just keep spinning for Trophy Mage
        else:
            ability_ranking[(Decklist.Recruiter,3)] = 45 #Important but not CRITICAL
    if haveStaffPlay:
        card_ranking[Decklist.Staff]      = 300 #don't need two staffs in play
        card_ranking[Decklist.TrophyMage] = 300 #don't need to find a second staff
    if haveStaffHand:
        card_ranking[Decklist.TrophyMage] = 300 #don't need to find a second staff   

    return card_ranking,ability_ranking
    

def RankerSpellsToCast(spell,gamestate):
    card_ranking = MasterRanker(gamestate)[0]
    if type(spell) in card_ranking:
        return card_ranking[type(spell)]
    else:
        return 200



        
        
    


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






    


