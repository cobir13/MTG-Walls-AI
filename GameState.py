# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""

import random
# import Decklist
import Cardboard
from Abilities import StackEffect,ManaAbility
import CardType
import ZONE
from ManaHandler import ManaPool


class WinTheGameError(Exception):
    pass
class LoseTheGameError(Exception):
    pass


"""
Oddity notes:
    - must pre-float all mana to pay for a spell
    

Notes on actually-correct things:
    - "casting" a land doesn't use the stack
    - mana abilities don't use the stack
    
"""





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
        if len(self.stack)>0:
            txt+= "\nSTACK:   "+",".join([str(obj) for obj in self.stack])
        txt+= "\nLife: %2i vs %2i" %(self.life,self.opponentlife)
        txt+= "    Deck: %2i" %len(self.deck)
        txt+= "    Mana: (%s)" %str(self.pool)
        return txt


    def __eq__(self,other):
        #easy disqualifications first
        if not (    len(self.deck)==len(other.deck)
                and len(self.hand)==len(other.hand)
                and len(self.field)==len(other.field)
                and len(self.grave)==len(other.grave)
                and len(self.stack)==len(other.stack)
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
        #stack isn't SORTED but it's ORDERED so can treat it the same
        for ii in range(len(self.stack)):
            if not self.stack[ii].EquivTo( other.stack[ii] ):
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
        s += "_" + ",".join([c.ID() for c in self.stack])
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
                neweffect = StackEffect(source,otherlist,obj.ability)
                state.stack.append( neweffect )        #add to stack
        #return
        return state,newtracklist


    def copy(self):
        return self.CopyAndTrack([])[0]
    
    ###-----MUTATING FUNCTIONS. They all return a list of StackEffects

    def AddToPool(self,colorstr):
        """MUTATES. Returns list of StackEffects that adding mana caused."""
        self.pool.AddMana(colorstr)
        return []
    
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
    
    # def _AddToZone(self,cardboard,zone=None):
    #     """For testing.  Should not be used otherwise"""
    #     if zone is None:
    #         zone = cardboard.zone
    #     zonelist = self._GetZone(zone)
    #     zonelist.append(cardboard)
    #     zonelist.sort(key=Cardboard.Cardboard.ID)
    #     print("AAAAH SOMEONE USED _AddToZone TO MOVE %s AAAAAH" %str(cardboard))
    
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
                    newEffect = StackEffect(source,[cardboard],abil)
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

    def UntapStep(self):
        """MUTATES. Returns list of StackEffects that trigger during untap."""
        # newstate,_ = self.CopyAndTrack([])  #copy, but nothing to track
        self.pool = ManaPool("")
        self.stack = []
        self.turncount+=1
        self.playedland = False
        effects = []
        for cardboard in self.field:
            effects += self.UntapPermanent(cardboard)        
            cardboard.summonsick = False
            cardboard.counters = [c for c in cardboard.counters if c[0]!="@"]
        return effects

    def UpkeepStep(self):
        """MUTATES. Returns list of StackEffects that trigger during upkeep."""
        effects = []
        for cardboard in self.hand + self.field + self.grave:
            for abil in cardboard.cardtype.trig_upkeep:
                newEffect = StackEffect(cardboard,[],abil)
                effects.append (newEffect) 
        return effects

    def Draw(self):
        """MUTATES. Returns list of StackEffects that trigger due to draw.
           Draws from index 0 of deck."""
        effects = []
        if len(self.deck)>0:
            effects += self.MoveZone(self.deck[0],ZONE.HAND)
            # #return a list of anything that triggers off of "draw" specifically
            # for source in self.field+self.grave+self.hand:
            #     for abil in source.cardtype.trig_draw:
            #         if abil.IsTriggered(state,source,cardboard,origin):
            #             newEffect = StackEffect(source,[cardboard],abil)
            #             effects.append( newEffect )
            return effects
        else:
            raise LoseTheGameError


    ###-----BRANCHING FUNCTIONS. Return a list of gamestates but do not mutate


    def CastSpell(self,cardboard):
        """
        DOES NOT MUTATE. Instead returns a list of GameStates in which the
            given Cardboard has been cast and any effects of that casting have
            been put onto the stack.
        """
        #check to make sure the execution is legal
        if not cardboard.cardtype.cost.CanAfford(self,cardboard):
            return []
        cast_list = []
        for state,card in cardboard.cardtype.cost.Pay(self,cardboard):
            #Iterate through all possible ways the cost could have been paid.
            #Each has a GameState and a Cardboard being cast. Move the card
            #being cast to the stack, then see if this triggers any effects.
            #Note: these are COPIES so they are safe to mutate.
            if isinstance(card.cardtype,CardType.Land):
                #special exception for Lands, which don't use the stack
                cast_list += card.cardtype.ResolveSpell(state,card) #[GameStates]
            else:
                effects = state.MoveZone(card,ZONE.STACK)
                state.stack += effects   #------------------------------------------randomize order of triggers? for now, no    
                #check state-based actions, add any effects from THAT to the stack
                state.stack += state.StateBasedActions()
                cast_list.append( state )
        return cast_list
        
    
    def ActivateAbilities(self,cardboard,ability):
        """
        DOES NOT MUTATE. Instead, returns a list of GameStates in which the
            ActivatedAbility of the source Cardboard has been paid for and put
            on the stack.
        """
        #check to make sure the execution is legal
        if not ability.CanAfford(self,cardboard):
            return []
        #pay for ability
        pairlist = ability.Pay(self,cardboard)  #[(GameState,Cardboard)] pairs
        statelist = []
        for game,source in pairlist:
            if isinstance(ability,ManaAbility):
                #special exception for ManaAbilities, which don't use the stack
                statelist += ability.Execute(game,source)
            else:
                #add ability to stack    
                game.stack.append(StackEffect(source,[],ability))
                statelist.append(game)
        return statelist
    
    
    def ResolveTopOfStack(self):
        """
        DOES NOT MUTATE. Instead, returns a list of GameStates in which the
            top item of the stack has been resolved.
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
            universes = card.cardtype.ResolveSpell(self,card)  #[GameStates]
            #this already includes moving the card from the stack to a zone
            #and putting all resulting triggers on the stack
            return universes
        elif isinstance(self.stack[-1],StackEffect):
            newstate,_ = self.CopyAndTrack([])
            effect = newstate.stack.pop(-1)
            return effect.Enact(newstate)  #[GameStates]
        
        
    # def AddEffectsToStack(self,effectlist):
    #     """
    #     DOES NOT MUTATE. Instead, returns a list of GameStates in which the
    #         list of StackEffects has been added to the top of the stack in
    #         various orders.
    #     NOTE: as a shortcut, if effectlist is length 0 or 1 (so the return
    #         list will be length 1), it DOES mutate self and return [self].
    #     NOTE: this is buggy and won't actually work yet.
    #     """
    #     #we are going to TEMPORARILY mutate self and then undo it
    #     num = len(effectlist)       
    #     self.stack += effectlist  #final `num` of stack are a new mutation
    #     #a shortcut to save time
    #     if num<=1:
    #         return [self]
    #     else:
    #         newstate,_ = self.CopyAndTrack([])
    #         #in theory, this is where we'd try all possible permutations-------ADD PERMUTATIONS OF THE EFFECTLIST
    #         #but for now, just return the one
    #         returnlist = [newstate]
    #         self.stack = self.stack[:-num]  #fix the mutation of self
    #         return returnlist
        
        
        
        

    ##-----------------------------------------------------------------------##

    def GetValidActivations(self):
        """
        Return a list of all abilities that can be put on the stack right
        now. Returned as list of StackEffects that have not yet been paid for.
        """
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
                    e = StackEffect(source,[],ability)
                    effects.append(e)
                    addobject = True
            if addobject:  #only add each object once, even if many abilities
                activeobjects.append(source)
        return effects
    
    def GetValidCastables(self):
        """Return a list of all castable cards that can be put on the stack
        right now, as a list of Cardboards which have not yet been paid for
        or moved from their current zones. Think of these like pointers."""
        cards = []
        #look for all cards that can be cast
        activeobjects = []
        for card in self.hand:
            if any([card.EquivTo(ob) for ob in activeobjects]):
                continue  #skip cards that are equivalent to cards already used
            if len(self.stack)>0 and "instant" not in card.cardtype.typelist:
                continue  #if stack is full, can only cast instants
            if card.cardtype.CanAfford(self,card):
                cards.append(card)
                activeobjects.append(card)
        return cards
        
    def Shuffle(self):
        random.shuffle(self.deck)


    ##-----------------------------------------------------------------------##
            
            
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


#     def TakeDamage(self,damage):
#         self.life -= damage
#         if self.life <= 0:
#             raise IOError("LOSE DUE TO DAMAGE!")





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