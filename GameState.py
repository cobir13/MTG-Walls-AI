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
            if verbose: print("draw:   ",str(card))
            self.hand.append(card) #removes from 0th index of deck
        else: #ran out of cards
            raise IOError("DRAW FROM AN EMPTY LIBRARY")
            
    def MainPhase(self,verbose=False):
        while True:
            command,obj = AI.ChooseActionToTake(self) #{"land","spell","ability","pass"}
            if command == "pass":
                break
            elif command == "land":
                assert(isinstance(obj,Cards.Land)) #so obj is a Land object
                if verbose: print("playing:",str(obj))
                self.PlayLand(obj)
            elif command in ["spell","ability"]: #casting and activating are very similar
                assert(hasattr(obj,"cost"))    
                #generate the necessary mana.
                firingsolution = self.TappingSolutionForCost(obj.cost)
                if verbose:
                    lst = ["(%s,%s)" %(s.name,color) for s,color in firingsolution]
                    print("floating","[ %s ]" %",".join(lst))
                self.GenerateManaForCasting(firingsolution)
                if command == "spell":
                    assert(isinstance(obj,Cards.Card))
                    #cast the chosen spell
                    if verbose: print("   cast:",str(obj))
                    self.CastSpell(obj)
                if command == "ability":
                    assert(isinstance(obj,Cards.Ability))
                    #activate the chosen ability
                    if verbose: print("    use: %s's ability" %obj.card.name)
                    obj.Activate(self)

            
            
            
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
            print("end with %s" %(str(self.pool)))
        for color in self.pool.data.keys():
            self.pool.data[color] = 0 
        #pass the turn
        if not self.myturn:
            self.turncount += 1
            self.playedland = False
        self.myturn = not self.myturn
        

  
##---------------------------------------------------------------------------##   

    def __str__(self):
        #sort first. locally only, not mutating.  Do the hand first
        handlands,castables,uncastables = self.ShowHandAsSorted()
        castables.  sort(key=lambda c: (c.cost.CMC(),str(c)) ) #str not c.name to include (T)"tapped"
        uncastables.sort(key=lambda c: (c.cost.CMC(),str(c)) )
        handlands.  sort(key=lambda c:               str(c)  )
        sortedhand = handlands+castables+uncastables
        #now sort the battlefield
        lands = []
        nonlands= []
        for card in self.field:
            if isinstance(card,Cards.Land):
                lands.append(card)
            else:
                nonlands.append(card)
        nonlands.sort(key=lambda c: (c.cost.CMC(),str(c)) )
        lands.   sort(key=lambda c:               str(c)  )
        sortedfield = lands+nonlands
        #now print
        txt = "HAND:\n   "+",".join([str(card) for card in sortedhand])
        txt+= "\n"
        txt+= "FIELD:\n   "+",".join([str(card) for card in sortedfield])
        return txt


##---------------------------------------------------------------------------##      
  
    def PlayLand(self,land):
        assert(not self.playedland)
        self.hand.remove(land)
        self.field.append(land)
        self.playedland = True
        self.ResolveCastingTriggers(land)
        

    def GenerateManaForCasting(self,firingsolution):
        """MUTATES SELF BY ADDING MANA AND TAPPING THINGS!!!"""
        for source,color in firingsolution:
            source.MakeMana(self,color)
        #flipped duskwatch recruiter?
        

    def CastSpell(self,card):
        self.pool.PayCost(card.cost)        
        self.hand.remove(card)
        if isinstance(card,Cards.Permanent):
            self.field.append(card)
        self.ResolveCastingTriggers(card)
    
    
    def ResolveCastingTriggers(self,card):
        """When any card is cast (or a permanent enters the field), resolve any
        effects that it triggers (including its own ETBs, if any).  Call this
        function AFTER the permanent has entered, technically."""
        if hasattr(card, "Effect"):
            card.Effect(self)
        for perm in self.field: #which should include card, too
            if hasattr(perm,"Trigger"):
                perm.Trigger(self,card)
            
    def GetAvailableAbilities(self):
        """return a list of all abilities which currently can be activated 
            (in play already and also affordable)"""
        abilities = []
        for c in self.field:
            if hasattr(c,"abilitylist"):
                for ab in c.abilitylist:
                    tappingsolution = self.TappingSolutionForCost(ab.cost)
                    if tappingsolution is not None: #possible to pay for ability!
                        abilities.append(ab)
        return abilities
    
    def ShowHandAsSorted(self):
        """returns 3 lists: all lands, all castable spells, and all uncastable
        spells.  Every card in the hand will be in one of these three lists."""
        lands = []
        castables = []
        uncastables = []
        for card in self.hand:
            if isinstance(card,Cards.Land):
                lands.append(card)
            else:
                tappingsolution = self.TappingSolutionForCost(card.cost)
                if tappingsolution is None:
                    uncastables.append(card)
                else:
                    castables.append(card)
        return lands,castables,uncastables


##-------------------Alternate Universe Functions----------------------------##


    def TappingSolutionForCost(self,cost):
        """given a gamestate and a cost, can I cover that cost?  Returns None if
        no, returns a list of (source,color) tuples to use if yes."""
        hypothet = GameState()
        hypothet.field = [c.copy() for c in self.field]
        hypothet.pool = self.pool.copy()
        
        #check our mana pool, see if we've got any floating
        if hypothet.pool.CanAffordCost(cost):
            return [] #we can cover the cost with just our floating mana!
        
        #OK, we're going to have to do some REAL work. Get a list of actual mana sources.
        sourcelist = [] #list of indices in hypothet.field, b/c index translates across universes
        for k,perm in enumerate(hypothet.field):
            if isinstance(perm,Cards.ManaSource) and not perm.unavailable:         
                if isinstance(perm,Decklist.Caretaker) and not perm.CanMakeMana(hypothet):
                    continue #"unavailable" is unreliable for Caretakers, need special check
                sourcelist.append(k)
        #sort the sourcelist: try beginning sources first, save last sources for later
        #monocolors at the beginning, pure gold at the end
        sourcelist.sort(key=lambda i: AI.RankerMana(hypothet.field[i],hypothet))
                
        #First, can we afford the colors?
        colorcost = cost.copy()
        colorcost.data["gen"] = 0
        colorsolution = []
        #Use our mana pool to pay for as much colored bits as we can
        for color,amount in hypothet.pool.data.items():
            assert(amount>=0) #mana pools should be positive...
            colorcost.data[color] = max(colorcost.data[color]-amount,0)
        
        if colorcost.CMC()>0:
            #we couldn't cover the colors with just our floating mana. What about mana sources?
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
        try:
            hypothet.CastSpell(coil)
        except IOError: #I didn't bother to populate the fake-gamestate deck, but
            pass        #drawing from an empty deck is fine in a fake universe
        return hypothet.CMCAvailable()
        #flipped duskwatch recruiter?
        


##---------------------------------------------------------------------------##




