# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""

import random
import Decklist
import CardType
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
        self.opponentlife = 20
        self.playedland = False
        
        self.verbose = False

        
    def Shuffle(self):
        random.shuffle(self.deck)
    
    def TurnCycle(self):
        if self.verbose:
            if self.turncount == 1:
                print(self)
            print("\n--------------------turn %i------------------\n" %self.turncount)
        self.Upkeep()
        if self.turncount>1:
            self.Draw()
        self.MainPhase()
        self.Attack()
        self.PassTurn()  #pass to opponent
        self.PassTurn()  #pass back to self

    
    
    def Upkeep(self):
        """untap, upkeep, and draw"""
        for permanent in self.field:
            permanent.Untap()
        for permanent in self.field:
            permanent.Upkeep()
            
    def Draw(self):
        if self.deck: #if at least one card left
            card = self.deck.pop(0)
            if self.verbose: print("draw:   ",str(card))
            self.hand.append(card) #removes from 0th index of deck
        else: #ran out of cards
            raise IOError("DRAW FROM AN EMPTY LIBRARY AND LOSE!")
            
    def MainPhase(self):
        while True:
            command,obj = AI.ChooseActionToTake(self) #{"land","spell","ability","pass"}
            if command == "pass":
                break
            elif command == "land":
                assert(isinstance(obj,CardType.Land)) #so obj is a Land object
                if self.verbose: print("playing:",str(obj))
                self.PlayLand(obj)
            elif command in ["spell","ability"]: #casting and activating are very similar
                assert(hasattr(obj,"cost"))    
                #generate the necessary mana.
                firingsolution = self.TappingSolutionForCost(obj.cost)
                if self.verbose:
                    lst = ["(%s,%s)" %(s.name,color) for s,color in firingsolution]
                    print("floating","[ %s ]" %",".join(lst))
                self.GenerateManaForCasting(firingsolution)
                if command == "spell":
                    assert(isinstance(obj,CardType.Card))
                    #cast the chosen spell
                    if self.verbose: print("    cast",str(obj))
                    self.CastSpell(obj)
                if command == "ability":
                    assert(isinstance(obj,CardType.Ability))
                    #activate the chosen ability
                    if self.verbose: print("    use: %s's %s ability" %(obj.card.name,obj.name))
                    obj.Activate(self)

            
            
            
    def Attack(self):
        """Attack with anything that can"""
        attackerlist = [] #keep track of what attacked, to print if verbose
        oldlife = self.opponentlife
        haveArcades = any( [isinstance(c,Decklist.Arcades) for c in self.field])
        #attack with everything that can
        for critter in self.field:
            if not isinstance(critter,CardType.Creature): #only attack with creatures
                continue
            if critter.summonsick or critter.tapped: #creature needs to be able to attack
                continue
            if "defender" in critter.typelist:
                if haveArcades: #have an Arcades, so can attack with the defenders!
                    self.opponentlife -= critter.toughness
                    attackerlist.append(critter)
            else: #non-defenders
                self.opponentlife -= critter.power
                attackerlist.append(critter)
        #attacking taps the attacker 
        for critter in attackerlist:
            if not "vigilance" in critter.typelist:
                    critter.tapped = True  
            if "lifelink" in critter.typelist:
                self.life += critter.power
        if self.verbose and len(attackerlist)>0: #print what just happened
            print("COMBAT  ",",".join([att.name for att in attackerlist]),"for %i damage" %(oldlife-self.opponentlife))
        if self.opponentlife <= 0:
            raise IOError("COMBAT DAMAGE WINS THE GAME!")
    
    
    def PassTurn(self):
        #discard down to 7 cards
        if len(self.hand)>7:
            discardlist = AI.ChooseCardstoDiscard(self)
            if self.verbose:
                print("discard:",[str(c) for c in discardlist])
            for card in discardlist:
                self.hand.remove(card)
        #clear any floating mana
        if self.verbose and self.pool.CMC()>0:
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
            if isinstance(card,CardType.Land):
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
        txt+= "\nLife: %i     Opponent: %i" %(self.life,self.opponentlife)
        return txt


##---------------------------------------------------------------------------##      
  
    def TakeDamage(self,damage):
        self.life -= damage
        if self.life <= 0:
            raise IOError("LOSE DUE TO DAMAGE!")


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
        if isinstance(card,CardType.Permanent):
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
            if isinstance(card,CardType.Land):
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
            if isinstance(perm,CardType.ManaSource) and not perm.unavailable:         
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
            if isinstance(permanent,CardType.ManaSource):
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




