# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""

import random
import Decklist
import Cardboard
import CardType
import ZONE
from ManaHandler import ManaPool


class WinTheGameError(Exception):
    pass
class LoseTheGameError(Exception):
    pass



class StackEffect():
    def __init__(self,name,source,otherlist,effect_fn):
        self.name = name
        self.source = source  #Cardboard source of the effect. "Pointer".
        self.otherlist = []   #list of other relevant Cardboards. "Pointer".
        self.effect_fn = effect_fn
        
    def Apply(self,gamestate): 
        return self.effect_fn(gamestate,self.source,*self.otherlist)
        
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name



class GameState():
    """The current state of the game.
    
    For anything relating to a decision (paying a cost, activating an ability,
    casting a spell), do not mutate this state.  Rather, always create a new
    state representing the new situation.
    
    A GameState holds all of the Cardboard pieces representing the MtG cards.
    It keeps track of which zones they are in, but THEY keep track of which
    cards they represent.
    
    A GameState also tracks and executes all the actions that can be taken
    from this GameState. (It finds these by scraping the cards it contains,
    not by maintaining separate lists of abilities. "The Game" does not
    have abilities, only cards have abilities.) The GameState DOES have
    functions for gameplay actions which come from base MtG rules, for
    example emptying mana at the end of phases or untapping at the untap step.
    All of these actions should be called by an outside function of some sort.
    The GameState does not progress the game, it merely tracks the state of
    the game and provides tools for others to progress the game with.
    
    THESE ACTIONS DO NOT MUTATE THE GAMESTATE ITSELF! All of these actions,
    when executed, return copies of the GameState but with the action having
    been executed.
    
    
    
    GameState moves Cardboards, Cardboards don't move themselves.
    GameState activates abilities, abilities don't activate themselves.
    GameState triggers abilities, abilities don't trigger themselves.
    
             

    """
    
    
    
    def __init__(self):
        self.deck = []  #list of Cardboard objects
        self.hand = []  #list of Cardboard objects
        self.field = [] #list of Cardboard objects
        self.grave = [] #list of Cardboard objects
        self.pool = ManaPool("")
        self.stack = [] #list of Cardboards and StackEffects
        

        self.turncount = 1
        self.myturn = True
        
        self.life = 20
        self.opponentlife = 20
        self.playedland = False
        
        self.verbose = False


    def __str__(self):
        txt = "HAND:    "+",".join([str(card) for card in self.hand])
        if len(self.field)>0:
            txt+= "\nFIELD:   "+",".join([str(card) for card in self.field])
        if len(self.grave)>0:
            txt+= "\nGRAVE:   "+",".join([str(card) for card in self.grave])
        txt+= "\nLife: %2i vs %2i" %(self.life,self.opponentlife)
        txt+= "    Deck: %2i" %len(self.deck)
        txt+= "    Mana: (%s)" %str(self.pool)
        return txt


    def __eq__(self,other):
        #easy disqualifications first
        if not (len(self.deck)==len(other.deck)
                and len(self.hand)==len(other.hand)
                and len(self.field)==len(other.field)
                and len(self.grave)==len(other.grave)
                and self.turncount == other.turncount
                and self.myturn == other.myturn
                and self.life == other.life
                and self.opponentlife == other.opponentlife
                and self.playedland == other.playedland
                and self.pool == other.pool):
                    return False
        #also need to compare hands, fields, etc. We know they are sorted
        #and have the same length, so just step through them
        for ii in range(len(self.hand)):
            if not self.hand[ii].EquivTo( other.hand[ii] ):
                return False
        for ii in range(len(self.grave)):
            if not self.grave[ii].EquivTo( other.grave[ii] ):
                return False
        for ii in range(len(self.field)):
            if not self.field[ii].EquivTo( other.field[ii] ):
                return False
        #if got to here, we're good!
        return True
    
    def ID(self):
        myturn = "MY" if self.myturn else "OP"
        playedland = "_PL" if self.myturn else ""
        s = "%s%i_%02ivs%02i%s" %(myturn,self.turncount,
                                  self.life,self.opponentlife,playedland)
        s += "_" + ",".join([c.ID() for c in self.hand])
        s += "_" + ",".join([c.ID() for c in self.field])
        s += "_" + ",".join([c.ID() for c in self.grave])
        s += "(%s)" %str(self.pool)
        return s

    def __hash__(self):
        return self.ID().__hash__() #hash the string of the ID


      
    
    def CopyAndTrack(self,tracklist):
        """Returns a disconnected copy of the gamestate and also a list of
        Cardboards in the new gamestate corresponding to the list of
        Cardboards we were asked to track. This allows tracking "between
        split universes."
        Return signature is: GameState, [Cardboard] """

        #make new Gamestate and start copying attributes by value
        state = GameState()
        #copy mana pool
        state.pool = self.pool.copy()
        #these are all ints or bools, so safe to copy directly
        state.turncount = self.turncount
        state.myturn = self.myturn
        state.life = self.life
        state.opponentlife = self.opponentlife
        state.playedland = self.playedland
        state.verbose = self.verbose
        #need to track any pointers in StackEffects
        stackindex = len(tracklist)      #index for where stack portion begins
        for obj in self.stack:
            if isinstance(obj,StackEffect):
                tracklist += [obj.source] + obj.otherlist #pointers in StackEffect
        #blank list to fill with corresponding copies of each card in tracklist
        newtracklist = [None] * len(tracklist)
        #copy all the lists of Cardboards. Maintains order, no need to re-sort
        def copylist(origl):
            newl = []
            for cardboard in origl:
                newcardboard = cardboard.copy()  #copy each card
                newl.append(newcardboard)        #add copy to requested list
                for index,tracked in enumerate(tracklist):
                    if cardboard is tracked:     #card we just copied is card we care about
                        newtracklist[index] = newcardboard #mark at corresponding index
            return newl
        state.deck = copylist(self.deck)
        state.hand = copylist(self.hand)
        state.field = copylist(self.field)
        state.grave = copylist(self.grave)
        #copy the stack, replacing pointers in StackEffects as neede
        for obj in self.stack:
            if isinstance(obj,Cardboard.Cardboard):
                #card was cast so it's on stack. Copy & track as normal
                newcardboard = obj.copy()
                state.stack.append( newcardboard )  
                for index,tracked in enumerate(tracklist):
                    if obj is tracked:
                        newtracklist[index] = newcardboard
            elif isinstance(obj,StackEffect):
                #Pointers from this StackEffect are the first thing from the
                #stack to be put on the tracklist. So source is at
                #newtracklist[stackindex], and then the remaining otherlist
                #is the next however-many entries in newtracklist. Remove
                #all these from tracklist once I've put them back on the stack.
                source = newtracklist.pop(stackindex)
                otherlist = []
                for kk in range(len(obj.otherlist)):
                    otherlist.append( newtracklist.pop(stackindex) )
                neweffect = StackEffect(obj.name,source,otherlist,obj.effect_fn)
                state.stack.append( neweffect )        #add to stack
        #return
        return state,newtracklist
        
    
    
    
    
    
    
    
    
    
    ###-----MUTATING FUNCTIONS. They all return a list of StackEffects
    
    def TapPermanent(self,cardboard):
        """MUTATES. Returns list of StackEffects that this tapping caused."""
        cardboard.tapped = True
        return []
    
    def UntapPermanent(self,cardboard):
        """MUTATES. Returns list of StackEffects that this untapping caused."""
        cardboard.tapped = False
        return []
    
    
    
    
    
    def _GetZone(self,zonename):
        if zonename == ZONE.DECK:
            zone = self.deck
        elif zonename == ZONE.HAND:
            zone = self.hand
        elif zonename == ZONE.FIELD:
            zone = self.field
        elif zonename == ZONE.GRAVE:
            zone = self.grave
        elif zonename == ZONE.STACK:
            zone = self.stack
        else:
            raise IndexError
        return zone
    
    def _AddToZone(self,cardboard,zone=None):
        """For testing.  Should not be used otherwise"""
        if zone is None:
            zone = cardboard.zone
        zonelist = self._GetZone(zone)
        zonelist.append(cardboard)
        zonelist.sort(key=Cardboard.Cardboard.ID)
    
    
    def MoveZone(self,cardboard,destination):
        """Move the specified piece of cardboard from the zone it is currently
        in to the specified destination zone.  Raises IndexError if the
        cardboard is not in the zone it claims to be in.
        Returns list of StackEffects that this movement caused.
        MUTATES.
        """
        #remove from origin
        origin = cardboard.zone
        if origin in [ZONE.DECK, ZONE.HAND, ZONE.FIELD, ZONE.GRAVE, ZONE.STACK]:
            oldlist = self._GetZone(origin)
            assert(cardboard in oldlist)
            oldlist.remove(cardboard)
        #add to destination
        cardboard.zone = destination
        zonelist = self._GetZone(destination)
        zonelist.append(cardboard)
        if destination in [ZONE.HAND,ZONE.FIELD,ZONE.GRAVE]: #these zones must
            zonelist.sort(key=Cardboard.Cardboard.ID)        #always be sorted
        #any time you change zones, reset the cardboard parameters
        cardboard.tapped = False
        cardboard.summonsick = True
        cardboard.counters = []
        #return a list of anything that triggers off of this move!
        triggered = []
        for source in self.field+self.grave+self.hand:
            for abil in source.cardtype.trig_move:
                if abil.IsTriggered(self,source,cardboard,origin):
                    newEffect = StackEffect(abil.name,
                                            source,
                                            [cardboard],
                                            abil.effect_fn)
                    triggered.append( newEffect )
        return triggered
        
        








    ##-----------------------------------------------------------------------##


    def StateBasedActions(self):
        """MUTATES. Performs any state-based actions like killing creatures if
        toughness is less than 0
        Returns list of StackEffects that these state-based actions caused.
        """
        effects = []
        i = 0
        while i < len(self.field):
            cardboard = self.field[i]
            if isinstance(cardboard.cardtype,CardType.Creature):
                #look for counters with "/", which modify power or toughness
                modifier = sum([int(v[:v.index("/")]) for v in cardboard.counters if "/" in v])
                if cardboard.cardtype.basetoughness + modifier <= 0:
                    effects += self.MoveZone(cardboard,ZONE.GRAVE)
                    continue
            i += 1
        #legend rule   --------------------------------------------------------ADD IN THE LEGEND RULE
        return effects


    def UpkeepStep(self):
        """MUTATES. Returns list of StackEffects that trigger during upkeep."""
        effects = []
        for cardboard in self.hand + self.field + self.grave:
            for abil in cardboard.cardtype.upkeep:
                newEffect = StackEffect(abil.name,cardboard,[],abil.effect_fn)
                effects.append (newEffect) 
        return effects


    def UntapStep(self):
        """MUTATES. Returns list of StackEffects that trigger during untap."""
        newstate,_ = self.CopyAndTrack([])  #copy, but nothing to track
        newstate.pool = ManaPool("")
        newstate.turncount+=1
        newstate.playedland = False
        effects = []
        for cardboard in newstate.field:
            effects += newstate.UntapPermanent(cardboard)        
            cardboard.summonsick = False
            cardboard.counters = [c for c in cardboard.counters if c[0]!="@"]
        return effects



    def Draw(self):
        """MUTATES. Returns list of StackEffects that trigger due to draw."""
        effects = []
        if len(self.deck)>0:
            effects += self.MoveZone(self.deck[0],ZONE.HAND)
            # #return a list of anything that triggers off of "draw" specifically
            # for source in self.field+self.grave+self.hand:
            #     for abil in source.cardtype.trig_draw:
            #         if abil.IsTriggered(state,source,cardboard,origin):
            #             newEffect = StackEffect(abil.name,
            #                                     source,
            #                                     [cardboard],
            #                                     abil.effect_fn)
            #             effects.append( newEffect )
            return effects
        else:
            raise LoseTheGameError



    def CastSpell(self,cardboard):
        """
        Put Cardboard onto the stack, trigger "cast" triggers.
        Return a list of GameState objects in which the given
            Cardboard has been cast and any effects of that casting have been
            dealth with (including spell effects, moving the Cardboard to new
            zones, triggering other abilities, etc). List is length 0 if
            this Cardboard cannot be cast.
        """
        #check to make sure the execution is legal
        if not cardboard.cost.CanAfford(self,cardboard):
            return []
        cast_list = []
        for state,card in cardboard.cost.Pay(self,cardboard):
            #Iterate through all possible ways the cost could have been paid.
            #Each has a GameState and a Cardboard being cast. Move the card
            #being cast to the stack, then see if this triggers any effects.
            #Note: these are COPIES so they are safe to mutate.
            effects = self.MoveZone(card,ZONE.STACK)
            state.stack += effects   #------------------------------------------randomize order of triggers? for now, no    
            #check state-based actions, add any effects from THAT to the stack
            state.stack += state.StateBasedActions()
            cast_list.append( state )
        return cast_list
        
    
    
    def ActivateAbilities(self,cardboard,ability):
        """
        DOES NOT MUTATE. Instead returns a list of gamestates.
        Pay for an ActivatedAbility and put it onto the stack.
        Return a list of GameState objects in which the given Ability of the
            given Cardboard has been put onto the stack (as well as any
            abilities that trigged due to the cost or the activation).
            List is length 0 if this Ability cannot be activated.
        """
        #check to make sure the execution is legal
        if not ability.CanAfford(self,cardboard):
            return []
        newlist = ability.PayAndExecute(self,cardboard)
        return [tup[0] for tup in newlist]  #only need the GameStates of the pairs
        


    def ResolveTopOfStack(self):
        """Return a list of GameStates in which the top item of the stack has
            been resolved. DOES NOT MUTATE SELF.
        If it was a Cardboard, it has been moved to the appropriate zone. If it
            was a Spell specifically, the effect has been resolved. Any
            enter-the-battlefield effects or similar effects that trigger
            based on motion been placed on the stack.
        If it was an ability (or really, a tuple of source,trigger,ability), 
            then the ability has been resolved and any new abilities that
            triggered as a result have been placed on the stack."""
        if len(self.stack)==0:
            return []
        
        elif isinstance(self.stack[-1],Cardboard.Cardboard):
            card = self.stack[-1]
            universes = card.cardtype.ResolveSpell(self,card)
            #this already includes moving the card from the stack to a zone
            #and putting all resulting triggers on the stack
            return universes
        
        elif isinstance(self.stack[-1],StackEffect):
            newstate,_ = self.CopyAndTrack([])
            effect = newstate.stack.pop[-1]
            return effect.Apply(newstate)
    
    
    
    
    
    
    
    
    
    
    
    

    ##-----------------------------------------------------------------------##


    def GetValidActions(self):
        """Return a list of all things that can be put on the stack right now
        (including Cardboards, StackEffects from activated abilities, and
        StackEffects from mana abilities)."""
        effects = []
        #look for all activated abilities that can be activated (incl. mana ab)
        activeobjects = []
        for source in self.hand + self.field + self.grave:
            if any([source.EquivTo(ob) for ob in activeobjects]):
                continue  #skip cards that are equivalent to cards already used
            addobject = False
            for ability in source.GetAbilities():  #distinguish activated vs mana?
                #check whether price can be paid
                if ability.CanAfford(self,source):
                    e = StackEffect(ability.name,source,[],ability.execute_fn)
                    effects.append(e)
                    addobject = True
            if addobject:  #only add each object once, even if many abilities
                activeobjects.append(source)
        #look for all cards that can be cast
        activeobjects = []
        for card in self.hand:
            if any([card.EquivTo(ob) for ob in activeobjects]):
                continue  #skip cards that are equivalent to cards already used
            if len(self.stack)>0 and "instant" not in card.cardtype.typelist:
                continue  #if stack is full, can only cast instants
            if card.cardtype.CanAfford(self,card):
                effects.append(card)
                activeobjects.append(card)
        return effects



        
    def Shuffle(self):
        random.shuffle(self.deck)


    # ##-----------------------------------------------------------------------##
    
    # def TurnCycle(self):
    #     if self.verbose:
    #         if self.turncount == 1:
    #             print(self)
    #         print("\n--------------------turn %i------------------\n" %self.turncount)
    #     self.Upkeep()
    #     if self.turncount>1:
    #         self.Draw()
    #     self.MainPhase()
    #     self.Attack()
    #     self.PassTurn()  #pass to opponent
    #     self.PassTurn()  #pass back to self

    
    
    # def Upkeep(self):
    #     """untap, upkeep, and draw"""
    #     for permanent in self.field:
    #         permanent.Untap()
    #     for permanent in self.field:
    #         permanent.Upkeep()
            
    # def Draw(self):
    #     if self.deck: #if at least one card left
    #         card = self.deck.pop(0)
    #         if self.verbose: print("draw:   ",str(card))
    #         self.hand.append(card) #removes from 0th index of deck
    #     else: #ran out of cards
    #         raise IOError("DRAW FROM AN EMPTY LIBRARY AND LOSE!")
            
    # def MainPhase(self):
    #     while True:
    #         command,obj = AI.ChooseActionToTake(self) #{"land","spell","ability","pass"}
    #         if command == "pass":
    #             break
    #         elif command == "land":
    #             assert(isinstance(obj,CardType.Land)) #so obj is a Land object
    #             if self.verbose: print("playing:",str(obj))
    #             self.PlayLand(obj)
    #         elif command in ["spell","ability"]: #casting and activating are very similar
    #             assert(hasattr(obj,"cost"))    
    #             #generate the necessary mana.
    #             firingsolution = self.TappingSolutionForCost(obj.cost)
    #             if self.verbose:
    #                 lst = ["(%s,%s)" %(s.name,color) for s,color in firingsolution]
    #                 print("floating","[ %s ]" %",".join(lst))
    #             self.GenerateManaForCasting(firingsolution)
    #             if command == "spell":
    #                 assert(isinstance(obj,CardType.Card))
    #                 #cast the chosen spell
    #                 if self.verbose: print("    cast",str(obj))
    #                 self.CastSpell(obj)
    #             if command == "ability":
    #                 assert(isinstance(obj,CardType.Ability))
    #                 #activate the chosen ability
    #                 if self.verbose: print("    use: %s's %s ability" %(obj.card.name,obj.name))
    #                 obj.Activate(self)

            
            
            
    # def Attack(self):
    #     """Attack with anything that can"""
    #     attackerlist = [] #keep track of what attacked, to print if verbose
    #     oldlife = self.opponentlife
    #     haveArcades = any( [isinstance(c,Decklist.Arcades) for c in self.field])
    #     #attack with everything that can
    #     for critter in self.field:
    #         if not isinstance(critter,CardType.Creature): #only attack with creatures
    #             continue
    #         if critter.summonsick or critter.tapped: #creature needs to be able to attack
    #             continue
    #         if "defender" in critter.typelist:
    #             if haveArcades: #have an Arcades, so can attack with the defenders!
    #                 self.opponentlife -= critter.toughness
    #                 attackerlist.append(critter)
    #         else: #non-defenders
    #             self.opponentlife -= critter.power
    #             attackerlist.append(critter)
    #     #attacking taps the attacker 
    #     for critter in attackerlist:
    #         if not "vigilance" in critter.typelist:
    #                 critter.tapped = True  
    #         if "lifelink" in critter.typelist:
    #             self.life += critter.power
    #     if self.verbose and len(attackerlist)>0: #print what just happened
    #         print("COMBAT  ",",".join([att.name for att in attackerlist]),"for %i damage" %(oldlife-self.opponentlife))
    #     if self.opponentlife <= 0:
    #         raise IOError("COMBAT DAMAGE WINS THE GAME!")
    
    
    # def PassTurn(self):
    #     #discard down to 7 cards
    #     if len(self.hand)>7:
    #         discardlist = AI.ChooseCardstoDiscard(self)
    #         if self.verbose:
    #             print("discard:",[str(c) for c in discardlist])
    #         for card in discardlist:
    #             self.hand.remove(card)
    #     #clear any floating mana
    #     if self.verbose and self.pool.CMC()>0:
    #         print("end with %s" %(str(self.pool)))
    #     for color in self.pool.data.keys():
    #         self.pool.data[color] = 0 
    #     #pass the turn
    #     if not self.myturn:
    #         self.turncount += 1
    #         self.playedland = False
    #     self.myturn = not self.myturn
        

  
    # ##-----------------------------------------------------------------------##



##---------------------------------------------------------------------------##      
  
#     def TakeDamage(self,damage):
#         self.life -= damage
#         if self.life <= 0:
#             raise IOError("LOSE DUE TO DAMAGE!")


#     def PlayLand(self,land):
#         assert(not self.playedland)
#         self.hand.remove(land)
#         self.field.append(land)
#         self.playedland = True
#         self.ResolveCastingTriggers(land)
        

#     def GenerateManaForCasting(self,firingsolution):
#         """MUTATES SELF BY ADDING MANA AND TAPPING THINGS!!!"""
#         for source,color in firingsolution:
#             source.MakeMana(self,color)
#         #flipped duskwatch recruiter?
        

#     def CastSpell(self,card):
#         self.pool.PayCost(card.cost)        
#         self.hand.remove(card)
#         if isinstance(card,CardType.Permanent):
#             self.field.append(card)
#         self.ResolveCastingTriggers(card)
    
    
#     def ResolveCastingTriggers(self,card):
#         """When any card is cast (or a permanent enters the field), resolve any
#         effects that it triggers (including its own ETBs, if any).  Call this
#         function AFTER the permanent has entered, technically."""
#         if hasattr(card, "Effect"):
#             card.Effect(self)
#         for perm in self.field: #which should include card, too
#             if hasattr(perm,"Trigger"):
#                 perm.Trigger(self,card)
            
#     def GetAvailableAbilities(self):
#         """return a list of all abilities which currently can be activated 
#             (in play already and also affordable)"""
#         abilities = []
#         for c in self.field:
#             if hasattr(c,"abilitylist"):
#                 for ab in c.abilitylist:
#                     tappingsolution = self.TappingSolutionForCost(ab.cost)
#                     if tappingsolution is not None: #possible to pay for ability!
#                         abilities.append(ab)
#         return abilities
    
#     def ShowHandAsSorted(self):
#         """returns 3 lists: all lands, all castable spells, and all uncastable
#         spells.  Every card in the hand will be in one of these three lists."""
#         lands = []
#         castables = []
#         uncastables = []
#         for card in self.hand:
#             if isinstance(card,CardType.Land):
#                 lands.append(card)
#             else:
#                 tappingsolution = self.TappingSolutionForCost(card.cost)
#                 if tappingsolution is None:
#                     uncastables.append(card)
#                 else:
#                     castables.append(card)
#         return lands,castables,uncastables


# ##-------------------Alternate Universe Functions----------------------------##


#     def TappingSolutionForCost(self,cost):
#         """given a gamestate and a cost, can I cover that cost?  Returns None if
#         no, returns a list of (source,color) tuples to use if yes."""
#         hypothet = GameState()
#         hypothet.field = [c.copy() for c in self.field]
#         hypothet.pool = self.pool.copy()
        
#         #check our mana pool, see if we've got any floating
#         if hypothet.pool.CanAffordCost(cost):
#             return [] #we can cover the cost with just our floating mana!
        
#         #OK, we're going to have to do some REAL work. Get a list of actual mana sources.
#         sourcelist = [] #list of indices in hypothet.field, b/c index translates across universes
#         for k,perm in enumerate(hypothet.field):
#             if isinstance(perm,CardType.ManaSource) and not perm.unavailable:         
#                 if isinstance(perm,Decklist.Caretaker) and not perm.CanMakeMana(hypothet):
#                     continue #"unavailable" is unreliable for Caretakers, need special check
#                 sourcelist.append(k)
#         #sort the sourcelist: try beginning sources first, save last sources for later
#         #monocolors at the beginning, pure gold at the end
#         sourcelist.sort(key=lambda i: AI.RankerMana(hypothet.field[i],hypothet))
                
#         #First, can we afford the colors?
#         colorcost = cost.copy()
#         colorcost.data["gen"] = 0
#         colorsolution = []
#         #Use our mana pool to pay for as much colored bits as we can
#         for color,amount in hypothet.pool.data.items():
#             assert(amount>=0) #mana pools should be positive...
#             colorcost.data[color] = max(colorcost.data[color]-amount,0)
        
#         if colorcost.CMC()>0:
#             #we couldn't cover the colors with just our floating mana. What about mana sources?
#             colorsolution = AI.FindSolutionForColors(colorcost, sourcelist,hypothet)
#             if not colorsolution:
#                 return None #no, we can't cover the cost. couldn't get the colors to work out.
        
#         #now time to work out how to cover the non-colored bit
#         fullsolution = AI.FindSolutionForGeneric(cost,colorsolution,sourcelist,hypothet)
#         if not fullsolution:
#             return None #no, we can't cover the cost. don't have enough mana total
#         else:
#             return [ ( self.field[index],color ) for index,color in fullsolution]



#     def CMCAvailable(self):
#         """How much mana (ignoring color) is available to me right now?"""
#         hypothet = GameState()
#         for c in self.field:
#             hypothet.AddToField(c.copy)
#         hypothet.pool = self.pool.copy()
#         for permanent in hypothet.field:
#             if isinstance(permanent,CardType.ManaSource) and not permanent.unavailable:
#                 #add mana (by mutating "hypothet" gamestate)
#                 permanent.MakeMana(permanent.tapsfor[0])
#         return hypothet.pool.CMC()


#     def CMCAvailableIfCast(self,card):
#         """casting defenders sometimes nets mana back. if I cast this card,
#         how much mana will I have available afterwards?  Assumes card IS castable"""
#         #just casts the card in an alternate gamestate and evaluates the result
#         hypothet = GameState()
#         for c in self.field:
#             hypothet.AddToField(c.copy)
#         coil = card.copy()
#         hypothet.AddTohand(coil)
#         hypothet.pool = self.pool.copy()
#         firingsolution = hypothet.TappingSolutionForCost(card.cost)
#         hypothet.GenerateManaForCasting(firingsolution)
#         try:
#             hypothet.CastSpell(coil)
#         except IOError: #I didn't bother to populate the fake-gamestate deck, but
#             pass        #drawing from an empty deck is fine in a fake universe
#         return hypothet.CMCAvailable()
#         #flipped duskwatch recruiter?
        


# ##---------------------------------------------------------------------------##





    # def copy(self,omit=[]):
    #     """Return an identical copy.
    #     The copy has no references to the original.
    #     Any Cardboard objects in the omit-list are left out of the copy
    #     """
    #     state = GameState()
    #     #copy all the lists and hands. maintains order (except for omitted)
    #     state.deck  = [c.copy() for c in self.deck if c not in omit]
    #     state.hand  = [c.copy() for c in self.hand if c not in omit]
    #     state.field = [c.copy() for c in self.field if c not in omit]
    #     state.grave = [c.copy() for c in self.grave if c not in omit]
    #     #copy mana pool
    #     state.pool = self.pool.copy()
    #     #these are all ints or bools, so safe to copy directly
    #     state.turncount = self.turncount
    #     state.myturn = self.myturn
    #     state.life = self.life
    #     state.opponentlife = self.opponentlife
    #     state.playedland = self.playedland
    #     state.verbose = self.verbose
    #     #return
    #     return state
    
    
    # def CopyAndTrack(self,tracklist):
    #     """Returns a disconnected copy of the gamestate and also a list of
    #     Cardboards in the new gamestate corresponding to the list of
    #     Cardboards we were asked to track. This allows tracking "between
    #     split universes."
    #     Return signature is: GameState, [Cardboard] """
    #     newstate = self.copy(omit=tracklist)
    #     newlist = []
    #     for c in tracklist:
    #         new_c = c.copy()
    #         newstate._AddToZone( new_c, new_c.zone )
    #         newlist.append(new_c)
    #     return newstate,newlist