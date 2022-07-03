# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""

import random
# import Decklist
from typing import List

import Cardboard
from Abilities import StackEffect, ManaAbility, AsEnterEffect
import RulesText
import ZONE
from ManaHandler import ManaPool
import Choices
import tkinter as tk

class WinTheGameError(Exception):
    pass


class LoseTheGameError(Exception):
    pass


"""
Notes comparing this program to the real Magic:The Gathering rules:
    - cannot activate mana abilities WHILE casting a spell. (must pre-float
        all mana to pay for the spell)
    

Notes on actually-correct things:
    - "casting" a land doesn't use the stack
    - mana abilities don't use the stack
    
"""


class GameState:
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
        self.deck: List[Cardboard] = []  # list of Cardboard objects
        self.hand: List[Cardboard] = []  # list of Cardboard objects
        self.field: List[Cardboard] = []  # list of Cardboard objects
        self.grave: List[Cardboard] = []  # list of Cardboard objects
        self.pool: ManaPool = ManaPool("")

        self.stack = []  # list of Cardboards and StackEffects
        self.super_stack = []  # list of StackEffects waiting to be
        # put on the stack. NOTHING CAN BE EXECUTED WHILE
        # STUFF IS ON THE SUPERSTACK (incl state-based)

        self.turn_count = 1
        self.is_my_turn = True

        self.life = 20
        self.opponent_life = 20
        self.has_played_land = False

        self.verbose = False

    def __str__(self):
        txt = "HAND:    " + ",".join([str(card) for card in self.hand])
        if len(self.field) > 0:
            txt += "\nFIELD:   " + ",".join([str(card) for card in self.field])
        if len(self.grave) > 0:
            txt += "\nGRAVE:   " + ",".join([str(card) for card in self.grave])
        if len(self.stack) > 0:
            txt += "\nSTACK:   " + ",".join([str(obj) for obj in self.stack])
        txt += "\nLife: %2i vs %2i" % (self.life, self.opponent_life)
        txt += "    Deck: %2i" % len(self.deck)
        txt += "    Mana: (%s)" % str(self.pool)
        return txt

    def __eq__(self, other):
        # easy disqualifications first
        if not (len(self.deck) == len(other.deck)
                and len(self.hand) == len(other.hand)
                and len(self.field) == len(other.field)
                and len(self.grave) == len(other.grave)
                and len(self.stack) == len(other.stack)
                and len(self.super_stack) == len(other.super_stack)
                and self.turn_count == other.turn_count
                and self.is_my_turn == other.is_my_turn
                and self.life == other.life
                and self.opponent_life == other.opponent_life
                and self.has_played_land == other.has_played_land
                and self.pool == other.pool):
            return False
        # also need to compare hands, fields, etc. We know they are sorted
        # and have the same length, so just step through them
        for ii in range(len(self.hand)):
            if not self.hand[ii].is_equiv_to(other.hand[ii]):
                return False
        for ii in range(len(self.grave)):
            if not self.grave[ii].is_equiv_to(other.grave[ii]):
                return False
        for ii in range(len(self.field)):
            if not self.field[ii].is_equiv_to(other.field[ii]):
                return False
        # stack isn't SORTED but it's ORDERED so can treat it the same
        for ii in range(len(self.stack)):
            if not self.stack[ii].is_equiv_to(other.stack[ii]):
                return False
        # if got to here, we're good!
        return True

    def get_id(self):
        my_turn = "MY" if self.is_my_turn else "OP"
        played_land = "_PL" if self.is_my_turn else ""
        s = "%s%i_%02ivs%02i%s" % (my_turn, self.turn_count,
                                   self.life, self.opponent_life, played_land)
        s += "_" + ",".join([c.get_id() for c in self.hand])
        s += "_" + ",".join([c.get_id() for c in self.field])
        s += "_" + ",".join([c.get_id() for c in self.grave])
        s += "_" + ",".join([c.get_id() for c in self.stack])
        s += "(%s)" % str(self.pool)
        return s

    def __hash__(self):
        return self.get_id().__hash__()  # hash the string of the get_id

    def copy_and_track(self, tracklist):
        """Returns a disconnected copy of the gamestate and also a list of
        Cardboards in the new gamestate corresponding to the list of
        Cardboards we were asked to track. This allows tracking "between
        split universes."
        If tracklist has non-Cardboard objects, they're also returned
        Return signature is: GameState, [Cardboard] """
        # make new Gamestate and start copying attributes by value
        state = GameState()
        # copy mana pool
        state.pool = self.pool.copy()
        # these are all ints or bools, so safe to copy directly
        state.turn_count = self.turn_count
        state.is_my_turn = self.is_my_turn
        state.life = self.life
        state.opponent_life = self.opponent_life
        state.has_played_land = self.has_played_land
        state.verbose = self.verbose
        # need to track any pointers in StackObjects
        stackindex = len(tracklist)  # index for where stack portion begins
        for obj in self.stack + self.super_stack:
            if isinstance(obj, StackCardboard):
                tracklist += [obj.card] + obj.choices
            elif isinstance(obj, StackAbility):
                tracklist += [obj.source] + obj.choices
        # blank list to fill with corresponding copies of each card in tracklist
        newtracklist = tracklist[:] #a copy of tracklist

        def copy_list_and_update_pointers_to_it(original_list):
            """Goes through a list and returns a list of
            copies of each element in the original list. Also
            checks against tracklist to make sure that any pointers
            to the original elements now points at the new copies of
            the elements. Maintains order so that the new list
            does not need to be re-sorted."""
            new_list = []
            for obj in original_list:
                if isinstance(obj,list) or isinstance(obj,tuple):
                    #recurse. I don't THINK this ever happens but just in case.
                    new_object = copy_list_and_update_pointers_to_it(obj)
                elif hasattr(obj,"copy"):
                    new_object = obj.copy()
                else:
                    # not copiable, probably int or similar
                    new_object = obj 
                new_list.append(new_object)
                # now spin through tracklist. if we just copied a
                # Cardboard that we are tracking, replace the old
                # pointer in newtracklist with a pointer to the new
                # copy.
                # (For things like ints, we don't care if it's
                # technically the old object or a new copy.)
                if isinstance(new_object,Cardboard):
                    for index, tracked_object in enumerate(tracklist):
                        # try to iterate through tracked_object just in case
                        try:
                            newtracklist[index] = [new_object if obj is c else c
                                                   for c in tracked_object]
                        except TypeError:
                            if obj is tracked_object:
                                newtracklist[index] = new_object
            return new_list
        
        state.deck = copy_list_and_update_pointers_to_it(self.deck)
        state.hand = copy_list_and_update_pointers_to_it(self.hand)
        state.field = copy_list_and_update_pointers_to_it(self.field)
        state.grave = copy_list_and_update_pointers_to_it(self.grave)
        
        def copy_stack_objects(original_list):
            """Goes through a list of StackObjects and rebuilds
            copies of them. StackObjects contain pointers to
            Cardboards, so we get the new pointers to the newly
            copied Cardboards by looking in the newtracklist.
            This assumes that the StackObjects are checked in the
            same order that they were placed into the newtracklist.
            Returns a list of new StackObjects and the new newtracklist"""
            new_list = []
            for obj in original_list:
                new_card = newtracklist[stackindex]
                i_end = stackindex+1+len(obj.choices)
                new_choices = newtracklist[stackindex+1:i_end]
                # build the new StackObject
                if isinstance(obj, StackCardboard):
                    new_stack_obj = StackCardboard(new_card, new_choices)
                elif isinstance(obj, StackAbility):
                    abil = obj.ability  # does this need a copy?
                    new_stack_obj = StackAbility(new_card, abil, new_choices)
                new_list.append(new_stack_obj)                
                # get rid of the references I just used. done with them now.
                return new_list, newtracklist[:stackindex]+newtracklist[i_end:]
        
        #copy stack and superstack, replacing pointers in StackObjects as I go
        state.stack, newtracklist = copy_stack_objects(self.stack)
        state.super_stack, newtracklist = copy_stack_objects(self.super_stack)
        # return
        return state, newtracklist

    def copy(self):
        return self.copy_and_track([])[0]

    ###-----MUTATING FUNCTIONS. They all return a list of StackEffects

    def AddToPool(self, colorstr):
        """MUTATES. Adds any triggered StackEffects to the super_stack."""
        self.pool.AddMana(colorstr)

    def TapPermanent(self, cardboard):
        """MUTATES. Adds any triggered StackEffects to the super_stack."""
        cardboard.tapped = True

    def UntapPermanent(self, cardboard):
        """MUTATES. Adds any triggered StackEffects to the super_stack."""
        cardboard.tapped = False

    def LoseLife(self, amount):
        """MUTATES. Adds any triggered StackEffects to the super_stack."""
        self.life -= amount

    def get_zone(self, zonename):
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

    def MoveZone(self, cardboard, destination):
        """Move the specified piece of cardboard from the zone it is currently
        in to the specified destination zone.  Raises IndexError if the
        cardboard is not in the zone it claims to be in.
        Adds any triggered StackEffects to the super_stack.
        MUTATES.
        """
        # remove from origin
        origin = cardboard.zone
        if origin in [ZONE.DECK, ZONE.HAND, ZONE.FIELD, ZONE.GRAVE, ZONE.STACK]:
            oldlist = self.get_zone(origin)
            assert (cardboard in oldlist)
            oldlist.remove(cardboard)
        # add to destination
        cardboard.zone = destination
        zonelist = self.get_zone(destination)
        zonelist.append(cardboard)
        if destination in [ZONE.HAND, ZONE.FIELD, ZONE.GRAVE]:  # these zones must
            zonelist.sort(key=Cardboard.Cardboard.get_id)  # always be sorted
        # any time you change zones, reset the cardboard parameters
        cardboard.tapped = False
        cardboard.summon_sick = True
        cardboard.counters = []
        # return a list of anything that triggers off of this move! (this
        # includes "as enters" abilities as well as normal etbs)
        for source in self.field + self.grave + self.hand:
            for abil in source.rules_text.trig_move:
                if abil.IsTriggered(self, source, cardboard, origin):
                    newEffect = StackEffect(source, [cardboard], abil)
                    self.super_stack.append(newEffect)

    ##-----------------------------------------------------------------------##

    def StateBasedActions(self):
        """MUTATES. Performs any state-based actions like killing creatures if
        toughness is less than 0.
        Adds any triggered StackEffects to the super_stack.
        """
        i = 0
        while i < len(self.field):
            cardboard = self.field[i]
            if cardboard.has_type(RulesText.Creature):
                # look for counters with "/", which modify power or toughness
                modifier = sum([int(v[:v.index("/")]) for v in cardboard.counters if "/" in v])
                if cardboard.rules_text.toughness + modifier <= 0:
                    self.MoveZone(cardboard, ZONE.GRAVE)
                    continue
            i += 1
        # legend rule   --------------------------------------------------------ADD IN THE LEGEND RULE

    def UntapStep(self):
        """MUTATES. Adds any triggered StackEffects to the super_stack."""
        # newstate,_ = self.copy_and_track([])  #copy, but nothing to track
        self.pool = ManaPool("")
        self.stack = []
        self.turn_count += 1
        self.has_played_land = False
        for cardboard in self.field:
            self.UntapPermanent(cardboard)  # adds effects to self's super_stack
            cardboard.summon_sick = False
            cardboard.counters = [c for c in cardboard.counters if c[0] != "@"]

    def UpkeepStep(self):
        """MUTATES. Adds any triggered StackEffects to the super_stack."""
        for cardboard in self.hand + self.field + self.grave:
            for abil in cardboard.rules_text.trig_upkeep:
                newEffect = StackEffect(cardboard, [], abil)
                self.super_stack.append(newEffect)

    def Draw(self):
        """MUTATES. Adds any triggered StackEffects to the super_stack.
           Draws from index 0 of deck."""
        if len(self.deck) > 0:
            self.MoveZone(self.deck[0], ZONE.HAND)  # adds effects to super_stack
            # #return a list of anything that triggers off of "draw" specifically
            # for source in self.field+self.grave+self.hand:
            #     for abil in source.cardtype.trig_draw:
            #         if abil.IsTriggered(state,source,cardboard,origin):
            #             newEffect = StackEffect(source,[cardboard],abil)
            #             self.super_stack.append( newEffect )
        else:
            raise LoseTheGameError

    ###-----BRANCHING FUNCTIONS. Return a list of gamestates but do not mutate

    def CastSpell(self, cardboard):
        """
        DOES NOT MUTATE. Instead returns a list of GameStates in which the
            given Cardboard has been cast and any effects of that casting have
            been put onto the super_stack.
        """
        # check to make sure the execution is legal
        if not cardboard.rules_text.cost.CanAfford(self, cardboard):
            return []
        cast_list = []
        for state, card in cardboard.rules_text.cost.Pay(self, cardboard):
            # Iterate through all possible ways the cost could have been paid.
            # Each has a GameState and a Cardboard being cast. Move the card
            # being cast to the stack, which adds any triggers to super_stack.
            if card.has_type(RulesText.Land):
                # special exception for Lands, which don't use the stack. Just
                # move it directly to play and then resolve super_stack
                # state is a copy so can mutate it safely.
                state.MoveZone(card, ZONE.FIELD)
            else:
                state.MoveZone(card, ZONE.STACK)
            state.StateBasedActions()  # check state-based actions
            cast_list += state.ClearSuperStack()  # list of GameStates
        return cast_list

    def ActivateAbilities(self, cardboard, ability):
        """
        DOES NOT MUTATE. Instead, returns a list of GameStates in which the
            ActivatedAbility of the source Cardboard has been paid for and put
            on the stack.
        """
        # check to make sure the execution is legal
        if not ability.CanAfford(self, cardboard):
            return []
        # pay for ability
        pairlist = ability.Pay(self, cardboard)  # [(GameState,Cardboard)] pairs
        statelist = []
        for game, source in pairlist:
            if isinstance(ability, ManaAbility):
                # special exception for ManaAbilities, which don't use the stack
                statelist += ability.Execute(game, source)
            else:
                # add ability to stack
                game.stack.append(StackEffect(source, [], ability))
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
        if len(self.stack) == 0:
            return []
        elif isinstance(self.stack[-1], Cardboard.Cardboard):
            card = self.stack[-1]
            # Copy the gamestate so that we can mutate the copy safely.
            # Move the card to its destination zone. This will probably put
            # some effect on the super_stack, which we will then resolve
            newstate = self.copy()
            card = newstate.stack[-1]
            if card.has_type(RulesText.Spell):
                # returns [GameStates]. Card also moved to destination zone.
                return card.rules_text.ResolveSpell(newstate)
            elif card.has_type(RulesText.Permanent):
                newstate.MoveZone(card, ZONE.FIELD)  # adds effects to super_stack
                return newstate.ClearSuperStack()  # [GameStates]
            else:
                raise IOError("not permanent, instant, OR sorcery???")
        elif isinstance(self.stack[-1], StackEffect):
            newstate, _ = self.copy_and_track([])
            effect = newstate.stack.pop(-1)
            # this already includes putting all resulting triggers on the stack
            # and clearing the super_stack
            return effect.Enact(newstate)  # [GameStates]

    def ClearSuperStack(self):
        """Returns a list of GameStates where the objects on the super_stack
        have been placed onto the stack in all possible orders or otherwise
        dealt with. If super_stack is empty, returns [self].
        DOES NOT MUTATE."""
        # base case: no items on super_stack
        if len(self.super_stack) == 0:
            return [self]
        results = []
        # pick a super_stack effect to move to the stack
        for item in Choices.ChooseExactlyOne(list(enumerate(self.super_stack)),
                                             "Add to stack"):
            ii = item[0]  # index first, then object second
            newstate = self.copy()
            effect = newstate.super_stack.pop(ii)
            if isinstance(effect.ability, AsEnterEffect):
                # if the StackEffect contains an AsEntersEffect, then enact
                # it immediately rather than putting it on the stack.
                results += effect.Enact(newstate)
            else:
                newstate.stack.append(effect)
                results.append(newstate)
        # recurse
        finalresults = []
        for state in results:
            finalresults += state.ClearSuperStack()
        return finalresults

    ##-----------------------------------------------------------------------##

    def GetValidActivations(self):
        """
        Return a list of all abilities that can be put on the stack right
        now. Returned as list of StackEffects that have not yet been paid for.
        """
        effects = []
        # look for all activated abilities that can be activated (incl. mana ab)
        activeobjects = []
        for source in self.hand + self.field + self.grave:
            if any([source.is_equiv_to(ob) for ob in activeobjects]):
                continue  # skip cards that are equivalent to cards already used
            addobject = False
            for ability in source.get_activated():
                # check whether price can be paid
                if ability.CanAfford(self, source):
                    e = StackEffect(source, [], ability)
                    effects.append(e)
                    addobject = True
            if addobject:  # only add each object once, even if many abilities
                activeobjects.append(source)
        return effects

    def GetValidCastables(self):
        """Return a list of all castable cards that can be put on the stack
        right now, as a list of Cardboards which have not yet been paid for
        or moved from their current zones. Think of these like pointers."""
        cards = []
        # look for all cards that can be cast
        activeobjects = []
        for card in self.hand:
            if any([card.is_equiv_to(ob) for ob in activeobjects]):
                continue  # skip cards that are equivalent to cards already used
            if len(self.stack) > 0 and "instant" not in card.rules_text.keywords:
                continue  # if stack is full, can only cast instants
            if card.rules_text.CanAfford(self, card):
                cards.append(card)
                activeobjects.append(card)
        return cards

    def Shuffle(self):
        """Mutates. Reorder deck randomly."""
        random.shuffle(self.deck)

    ##-----------------------------------------------------------------------##

    # def Attack(self):
    #     """Attack with anything that can"""
    #     attackerlist = [] #keep track of what attacked, to print if verbose
    #     oldlife = self.opponent_life
    #     haveArcades = any( [isinstance(c,Decklist.Arcades) for c in self.field])
    #     #attack with everything that can
    #     for critter in self.field:
    #         if not isinstance(critter,RulesText.Creature): #only attack with creatures
    #             continue
    #         if critter.summon_sick or critter.tapped: #creature needs to be able to attack
    #             continue
    #         if "defender" in critter.keywords:
    #             if haveArcades: #have an Arcades, so can attack with the defenders!
    #                 self.opponent_life -= critter.toughness
    #                 attackerlist.append(critter)
    #         else: #non-defenders
    #             self.opponent_life -= critter.power
    #             attackerlist.append(critter)
    #     #attacking taps the attacker 
    #     for critter in attackerlist:
    #         if not "vigilance" in critter.keywords:
    #                 critter.tapped = True  
    #         if "lifelink" in critter.keywords:
    #             self.life += critter.power
    #     if self.verbose and len(attackerlist)>0: #print what just happened
    #         print("COMBAT  ",",".join([att.name for att in attackerlist]),"for %i damage" %(oldlife-self.opponent_life))
    #     if self.opponent_life <= 0:
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
    #     if self.verbose and self.pool.cmc()>0:
    #         print("end with %s" %(str(self.pool)))
    #     for color in self.pool.data.keys():
    #         self.pool.data[color] = 0 
    #     #pass the turn
    #     if not self.is_my_turn:
    #         self.turn_count += 1
    #         self.has_played_land = False
    #     self.is_my_turn = not self.is_my_turn


#     def TakeDamage(self,damage):
#         self.life -= damage
#         if self.life <= 0:
#             raise IOError("LOSE DUE TO DAMAGE!")


###----------------------------------------------------------------------------


class ManualGame(tk.Tk):

    def __init__(self, startstate):
        super().__init__()
        self.history = [startstate]
        # if you win or lose, game raises an error
        self.report_callback_exception = self.HandleError
        # how to pass and allow stack to resolve. sort of like F2 on MagicOnline
        self.var_resolveall = tk.IntVar(self, 1)
        # stack
        tk.Label(self, text="STACK", wraplength=1).grid(row=0, column=0)
        self.stack = tk.Frame(self, borderwidth=1, relief="solid")
        self.stack.grid(row=0, column=1, padx=5, pady=5, sticky="W")
        # current situation
        tk.Label(self, text="STATE", wraplength=1).grid(row=1, column=0)
        self.status = tk.Frame(self, borderwidth=1, relief="solid")
        self.status.grid(row=1, column=1, padx=5, pady=5, sticky="W")
        # battlefield
        tk.Label(self, text="FIELD", wraplength=1).grid(row=2, column=0)
        self.field = tk.Frame(self, bg="lightgray", borderwidth=1, relief="solid")
        self.field.grid(row=2, column=1, padx=5, pady=15, sticky="W")
        # hand
        tk.Label(self, text="HAND", wraplength=1).grid(row=3, column=0)
        self.hand = tk.Frame(self, borderwidth=1, relief="solid")
        self.hand.grid(row=3, column=1, padx=5, pady=5, sticky="W")
        # populate the display and start the game
        self.RebuildDisplay()
        self.mainloop()

    @property
    def game(self):
        assert (not isinstance(self.history[-1], str))
        return self.history[-1]

    def RebuildStack(self):
        for widgets in self.stack.winfo_children():
            widgets.destroy()
        for ii, obj in enumerate(self.game.stack):
            # obj is either Cardboard or StackEffect. both have TkDisplay method
            butt = obj.build_tk_display(self.stack)
            butt.config(command=self.ResolveTopOfStack)
            butt.grid(row=1, column=ii, padx=5, pady=3)

    def RebuildStatus(self):
        for widgets in self.status.winfo_children():
            widgets.destroy()
        # turn count
        tk.Label(self.status, text="Turn:\n%i" % self.game.turn_count,
                 ).grid(row=1, column=1, rowspan=2, padx=5, pady=5)
        # life totals
        tk.Label(self.status, text="Life total: %i" % self.game.life
                 ).grid(row=1, column=2, padx=5, pady=2)
        tk.Label(self.status, text="Opponent: %i" % self.game.opponent_life
                 ).grid(row=2, column=2, padx=5, pady=2)
        # cards remaining
        tk.Label(self.status, text="Cards in deck: %i" % len(self.game.deck)
                 ).grid(row=1, column=3, padx=5, pady=2)
        tk.Label(self.status, text="Cards in grave: %i" % len(self.game.grave)
                 ).grid(row=2, column=3, padx=5, pady=2)
        # mana and land-drops
        if str(self.game.pool) != "":
            manastr = "Mana floating: (%s)" % str(self.game.pool)
        else:
            manastr = "Mana floating: None"
        landstr = "Played land: %s" % ("yes" if self.game.has_played_land else "no")
        tk.Label(self.status, text=manastr
                 ).grid(row=1, column=4, padx=5, pady=2)
        tk.Label(self.status, text=landstr
                 ).grid(row=2, column=4, padx=5, pady=2)
        # button to do the next thing
        if len(self.game.stack) == 0:
            b = tk.Button(self.status, text="Pass\nturn", bg="yellow", width=7,
                          command=self.PassTurn)
            b.grid(row=1, column=5, padx=5, pady=5)
        else:
            b = tk.Button(self.status, text="Resolve\nnext", bg="yellow", width=7,
                          command=self.ResolveTopOfStack)
            b.grid(row=1, column=5, padx=5, pady=2)
        # undo button
        b2 = tk.Button(self.status, text="undo", bg="yellow", command=self.Undo)
        b2.grid(row=1, column=6, padx=5, pady=2)
        # auto-resolve button
        b3 = tk.Checkbutton(self.status, text="Auto-resolve all",
                            variable=self.var_resolveall,
                            indicatoron=True)  # ,onvalue=1,background='grey')#,selectcolor='green')
        b3.grid(row=2, column=5, columnspan=2, padx=5, pady=5)

    def RebuildHand(self):
        for widgets in self.hand.winfo_children():
            widgets.destroy()
        for ii, card in enumerate(self.game.hand):
            butt = card.build_tk_display(self.hand)
            abils = [a for a in card.get_activated() if a.CanAfford(self.game, card)]
            assert (len(abils) == 0)  # activated abilities in hand not yet implemented
            if card.rules_text.CanAfford(self.game, card):
                butt.config(state="normal",
                            command=lambda c=card: self.CastSpell(c))
            else:
                butt.config(state="disabled")
            butt.grid(row=1, column=ii, padx=5, pady=3)

    def RebuildField(self):
        for widgets in self.field.winfo_children():
            widgets.destroy()
        toprow = 0  # number in bottom row
        botrow = 0  # number in top row
        for card in self.game.field:
            butt = card.build_tk_display(self.field)
            # make the button activate this card's abilities
            abils = [a for a in card.get_activated() if a.CanAfford(self.game, card)]
            if len(abils) == 0:
                butt.config(state="disabled")  # nothing to activate
            elif len(abils) == 1:
                command = lambda c=card, a=abils[0]: self.ActivateAbility(c, a)
                butt.config(state="normal", command=command)
            else:  # len(abils)>1:
                # ask the user which one to use
                print("ask the user which ability to use, I guess")
            # add card-button to the GUI. Lands on bottom, cards on top
            if card.has_type(RulesText.Creature):
                butt.grid(row=1, column=toprow, padx=5, pady=3)
                toprow += 1
            else:
                butt.grid(row=2, column=botrow, padx=5, pady=3)
                botrow += 1

    def RebuildDisplay(self):
        self.RebuildStack()
        self.RebuildStatus()
        self.RebuildField()
        self.RebuildHand()

    def Undo(self):
        if len(self.history) > 1:
            self.history.pop(-1)  # delete last gamestate from history list
            self.RebuildDisplay()

    def CastSpell(self, spell):
        universes = self.game.CastSpell(spell)
        if len(universes) == 0:
            return  # casting failed, nothing changed so do nothing
        assert (len(universes) == 1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.EmptyEntireStack()
        else:
            self.RebuildDisplay()

    def ActivateAbility(self, source, ability):
        universes = self.game.ActivateAbilities(source, ability)
        if len(universes) == 0:
            return  # activation failed, nothing changed so do nothing
        assert (len(universes) == 1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.EmptyEntireStack()
        else:
            self.RebuildDisplay()

    def ResolveTopOfStack(self):
        if len(self.game.stack) == 0:
            return  # nothing to resolve, so don't change anything
        universes = self.game.ResolveTopOfStack()
        # if len(universes)==0:
        #     return #nothing changed so do nothing
        assert (len(universes) == 1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.EmptyEntireStack()
        else:
            self.RebuildDisplay()

    def EmptyEntireStack(self):
        while len(self.game.stack) > 0:
            universes = self.game.ResolveTopOfStack()
            # if len(universes)==0:
            #     return #nothing changed so do nothing
            assert (len(universes) == 1)
            self.history.append(universes[0])
        self.RebuildDisplay()

    def PassTurn(self):
        newstate = self.game.copy()
        newstate.UntapStep()
        newstate.UpkeepStep()
        newstate.Draw()  # technically should clear super_stack FIRST but whatever
        # clear the super stack, then clear the normal stack
        activelist = newstate.ClearSuperStack()
        finalstates = set()
        while len(activelist) > 0:
            state = activelist.pop(0)
            if len(state.stack) == 0:
                finalstates.add(state)
            else:
                activelist += state.ResolveTopOfStack()
        # all untap/upkeep/draw abilities are done
        assert (len(finalstates) == 1)
        self.history.append(finalstates.pop())
        self.RebuildDisplay()

    def HandleError(self, exc, val, tb, *args):
        """overwrite tkinter's usual error-handling routine if it's something
        I care about (like winning or losing the game)
        exc is the error type (it is of class 'type')
        val is the error itself (it is some subclass of Exception)
        tb is the traceback object (it is of class 'traceback')
        See https://stackoverflow.com/questions/4770993/how-can-i-make-silent-exceptions-louder-in-tkinter
        """
        if isinstance(val, WinTheGameError):
            tk.Label(self.status, text="CONGRATS! YOU WON THE GAME!", bg="red",
                     ).grid(row=0, column=0, columnspan=10, padx=5, pady=5)
            for frame in [self.field, self.hand, self.stack, self.status]:
                for widget in frame.winfo_children():
                    if isinstance(widget, tk.Button):
                        widget.config(state="disabled")
        elif isinstance(val, LoseTheGameError):
            tk.Label(self.status, text="SORRY, YOU LOST THE GAME", bg="red",
                     ).grid(row=0, column=0, columnspan=10, padx=5, pady=5)
            for frame in [self.field, self.hand, self.stack, self.status]:
                for widget in frame.winfo_children():
                    if isinstance(widget, tk.Button):
                        widget.config(state="disabled")
        elif isinstance(val, Choices.AbortChoiceError):
            return  # just don't panic. gamestate is unchanged.
        else:
            super().report_callback_exception(exc, val, tb, *args)





# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class StackObject:
    def resolve(self, gamestate):
        pass
    def get_id(self):
        pass
    def is_equiv_to(self,other):
        pass
    @property
    def name(self):
        pass



class StackCardboard(StackObject):

    def __init__(self, card:Cardboard=None, choices:list=[]):
        #the Cardboard that is being cast. It is NOT just a pointer. The
        #Cardboard really has been moved to the Stack zone
        self.card = card
        #list of any modes or targets or other choices made during casting
        #or activation.  If targets are Cardboards, they are pointers.
        self.choices = choices

    def resolve(self, gamestate):
        """Returns list of GameStates resulting from performing this effect"""
        return self.card.Execute(gamestate)

    def __str__(self):
        return self.card.name

    def __repr__(self):
        return "Spell: " + self.card.name

    def get_id(self):
        choices = ",".join([c.get_id() if isinstance(c,Cardboard) else str(c)
                            for c in self.choices])
        return "S(%s|%s)" %(self.card.get_id(),choices)

    def is_equiv_to(self, other):
        return self.get_id() == other.get_id()

    @property
    def name(self):
        return self.card.name

    # def build_tk_display(self, parentframe, ):
    #     return tk.Button(parentframe,
    #                      text="Effect: %s" % self.name,
    #                      anchor="w",
    #                      height=7, width=10, wraplength=80,
    #                      padx=3, pady=3,
    #                      relief="solid", bg="lightblue")




class StackAbility(StackObject):

    def __init__(self, ability, source:Cardboard, choices:list=[]):
        #The Ability that is being activated
        self.ability = ability
        #The source Cardboard as a "pointer"
        self.source = source
        #list of any modes or targets or other choices made during casting
        #or activation.  If targets are Cardboards, they are pointers.
        self.choices = choices  # list of other relevant Cardboards. "Pointers".


    def resolve(self, gamestate):
        """Returns list of GameStates resulting from performing this effect"""
        return self.ability.apply_effect(gamestate, self.source, self.choices)

    def __str__(self):
        return self.ability.name

    def __repr__(self):
        return "Effect: " + self.ability.name

    def get_id(self):
        choices = ",".join([c.get_id() if isinstance(c,Cardboard) else str(c)
                            for c in self.choices])
        return "E(%s|%s)" %(self.ability.get_id(),choices)

    def is_equiv_to(self, other):
        return self.get_id() == other.get_id()

    @property
    def name(self):
        return self.card.name

    # def build_tk_display(self, parentframe, ):
    #     return tk.Button(parentframe,
    #                      text="Effect: %s" % self.name,
    #                      anchor="w",
    #                      height=7, width=10, wraplength=80,
    #                      padx=3, pady=3,
    #                      relief="solid", bg="lightblue")
















if __name__ == "__main__":
    print("testing ManualGame...")
    import Decklist
    import Choices

    Choices.AUTOMATION = False

    game = GameState()
    game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.FIELD)
    game.MoveZone(Cardboard.Cardboard(Decklist.Caretaker), ZONE.FIELD)

    game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Roots), ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Battlement), ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Company), ZONE.HAND)

    for _ in range(5):
        game.MoveZone(Cardboard.Cardboard(Decklist.Blossoms), ZONE.DECK)
    for _ in range(5):
        game.MoveZone(Cardboard.Cardboard(Decklist.Omens), ZONE.DECK)
        game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.DECK)
        game.MoveZone(Cardboard.Cardboard(Decklist.Battlement), ZONE.DECK)

    # window = tk.Tk()

    # Choices.SelecterGUI(game.hand,"test chooser GUI",1,False)

    # window.mainloop()

    game.UntapStep()
    game.UpkeepStep()
    gui = ManualGame(game)
