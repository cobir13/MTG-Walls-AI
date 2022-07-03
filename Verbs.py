# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from typing import List
from GameState import GameState
from Cardboard import Cardboard
import ManaHandler
import Choices
import ZONE
import MatchCardPatterns as Match
import GettersAndChoosers as Get

from RulesText import Creature

import Actions



# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------
        
class Verb:
    def __init__(self, getter_list:List[Get.Getter]):
        self.getter_list = getter_list
    
    def can_be_done(self, state:GameState, source:Cardboard, choices:list) -> bool:
        return True
        
    def do_it(self, state:GameState, source:Cardboard, choices:list):
        """if this Verb has `single_output`, then this function
        mutates the given gamestate. If it does not have
        `single_output` (which is to say, if it has multiple
        possible outputs), then it will return a list of
        (GameState,Cardboard) tuples, one for each possible
        way that this Verb can be executed."""
        if self.single_output:
            #`trigger_source` is source of the trigger. Not to be confused
            #with `source`, which is the source of the Verb which is
            #potentially CAUSING the trigger.
            for trigger_source in state.field + state.grave + state.hand:
                for abil in trigger_source.rules_text.trig_verb:
                    if abil.is_triggered(self, state, trigger_source, source):
                        effect = Actions.StackAbility(abil, trigger_source,
                                                      [source])
                        state.super_stack.append(effect)

    def __str__(self):
        return type(self).__name__
    
    def choose_choices(self, state:GameState, source:Cardboard):
        """returns a list of sublists. Each sublists is the length
        of `getter_list` and represents one possible way to choose
        modes and/or targets for this Verb."""
        #list of sublists. start with 1 sublist, which is empty
        choices = [[]] 
        for getter in self.getter_list:
            gotten = getter.get(state, source)
            if getter.single_output:
                #if only one option, add it to each sublist
                choices = [sublist+[gotten] for sublist in choices]
            else:
                #if many options, make more sublists (one with each added)
                newchoices = []
                for x in gotten:
                    newchoices += [sublist+[x] for sublist in choices]
                choices = newchoices
        return choices
    
    @property
    def num_inputs(self):
        return len(self.getter_list)
    
    @property
    def single_output(self):
        #note: all([])==True. So Verbs with no options are single_output. good.
        return all([g.single_output for g in self.getter_list])
    
    def is_type(self, verb_type):
        return isinstance(self, verb_type)
    
    
    
    
#Verbs with no cardboard targets (draw a card, lose life, etc)
#Verbs that act on "source" cardboard (tap symbol, add counter)
#Verbs that apply a verb to a target cardboard

#EVERY VERB (CAN) HAVE PARAMETERS (how much mana to add, how much life to lose)
#Describe these as Getters. Sometimes those Getters are Const, that's fine.
#Sometimes I'll make a subclass so that I don't have to type out Const every
#time, that's also fine.  But they're all Getters. Notably, parameters
#are different than targets! Parameters shouldn't be cardboards!
#BUT WAIT. AM I SURE THEY HAVE TO BE GETTERS? subclasses using str, int, etc
#seems much easier...  
#TODO


class VerbAtomic(Verb):
    pass


class VerbOnSourceCard(Verb):
    """acts on the source passed into the `do_it` method"""
    pass


class VerbOnTarget(Verb):
    """Applies the given VerbOnSourceCard to the first element of the
    `choices` argument passed into the `do_it` method (which should
    be a Cardboard) rather than on the `source` argument. The
    remaining elements of `choices` are passed along to the Verb.
    Note: `getter_list` should be length 1 and should get the target
    Cardboard.
    """
    def __init__(self, verb:VerbOnSourceCard, getter_list:List[Get.Getter]):
        super().__init__(getter_list)
        self.verb = verb
    
    def can_be_done(self, state:GameState, source:Cardboard, choices:list) -> bool:
        return (len(choices)>=1
                and self.verb.can_be_done(state,choices[0],choices[1:]) )
    
    def __str__(self):
        return str(self.verb)
    
    @property
    def single_output(self):
        return super().single_output and self.verb.single_output
    
    def is_type(self, verb_type):
        return super().is_type(verb_type) or self.verb.is_type(verb_type)
    
    
    
class ManyVerbs(Verb):
    def __init__(self, list_of_verbs:List[Verb]):
        super().__init__( [] )
        self.list_of_verbs = list_of_verbs
    
    def can_be_done(self, state, source, choices):
        i_start = 0
        for v in self.list_of_verbs:
            i_end = i_start + v.num_inputs
            if not v.can_be_done(state, source, choices[i_start:i_end]):
                #if any verb cannot be done, the whole list cannot be done
                return False
            i_start = i_end  #increment to use the next choices for next verb
        return True #if reached here, all verbs are doable!
    
    def do_it(self, state, source, choices):
        #first things first, copy gamestate so that it's safe to mutate
        state_copy, copied_cards = state.copy_and_track([source]+choices)
        source_copy = copied_cards[0]
        choices_copy = copied_cards[1:]
        old_tuple_list = [(state_copy,source_copy)]
        new_tuple_list = []
        i_start = 0
        for verb in self.verbs:
            for_this_verb = choices_copy[:verb.num_inputs]
            if verb.single_output:
                #mutate the gamestates in old_tuple_list directly
                [verb.do_it(g,c,for_this_verb) for g,c in old_tuple_list]
            else:
                #collect output of applying verb to each tuple in old_list
                for g,c in old_tuple_list:
                    new_tuple_list += verb.do_it(g,c,for_this_verb)
                    #TODO: need to copy choices list also?
                old_tuple_list = new_tuple_list
                new_tuple_list = []
            choices_copy = choices_copy[verb.num_inputs:]
        #clear the superstack of all the new gamestates
        for g in old_tuple_list:
            new_tuple_list += g.ClearSuperStack()
        return new_tuple_list
    
    def __str__(self):
        return "["+",".join([str(v) for v in self.list_of_verbs])+"]"
    
    def choose_choices(self, state:GameState, source:Cardboard):
        """returns a list of sublists. Each sublists is the length
        of `getter_list` and represents one possible way to choose
        modes and/or targets for this Verb."""
        #list of sublists. start with 1 sublist, which is empty
        choices = [[]] 
        for v in self.list_of_verbs:
            for getter in v.getter_list:
                gotten = getter.get(state, source)
                if getter.single_output:
                    #if only one option, add it to each sublist
                    choices = [sublist+[gotten] for sublist in choices]
                else:
                    #if many options, make more sublists (one with each added)
                    newchoices = []
                    for x in gotten:
                        newchoices += [sublist+[x] for sublist in choices]
                    choices = newchoices
        return choices
    
    @property
    def num_inputs(self):
        return sum([v.num_inputs for v in self.list_of_verbs])
    
    @property
    def single_output(self):
        return all([v.single_output for v in self.list_of_verbs])
    
    def is_type(self, verb_type):
        return any( [v.is_type(verb_type) for v in self.list_of_verbs] )
    
    
#------------------------------------------------------------------------------
    


class RepeatBasedOnState(Verb):
    def __init__(self, action:Verb, getter:Get.Integer):
        super().__init__([getter])
        self.action = action
    
    def can_be_done(self, state:GameState, subject:Cardboard, choices) -> bool:
        return self.action.can_be_done(state,subject)
    
    def do_it(self, state:GameState, subject:Cardboard, choices):
        """mutates!"""
        # num_to_repeat = self.getter.get(state,subject)
        num_to_repeat = choices[0]
        for _ in range(num_to_repeat):
            if self.action.can_be_done(state,subject,choices[1:]):
                self.action.do_it(state,subject,choices[1:])

    def num_inputs(self):
        return super().num_inputs + self.action.num_inputs
    
    def single_output(self):
        return super().single_output and self.action.single_output
    
    def is_type(self, verb_type):
        return super().is_type(verb_type) or self.action.is_type(verb_type)
    
    




    
#------------------------------------------------------------------------------


# =============================================================================
# class PayMana(VerbAtomic):
#     """deducts the given amount of mana from the gamestate's mana pool"""
#     
#     def __init__(self, mana_string:str):
#         super().__init__( [] )
#         self.mana_cost = ManaHandler.ManaCost(mana_string)
#         
#     def can_be_done(self, state, subject, choices):
#         return state.pool.CanAffordCost(self.mana_cost)
#     
#     def do_it(self, state, subject, choices):
#         state.pool.PayCost(self.mana_cost)
#         super().do_it(state,subject,choices)  #adds triggers to super_stack
#         
# # ----------
# 
# class AddMana(Verb):
#     """adds the given amount of mana to the gamestate's mana pool"""
#     def __init__(self, mana_string_getter:str):
#         super().__init__( [mana_string_getter] )
#     def can_be_done(self, state, subject ,choices):
#         return True
#     def do_it(self, state, subject, choices): 
#         mana_string = self.getter_list[0].get(state,subject)
#         mana_to_add = ManaHandler.ManaPool( mana_string)
#         state.pool.AddMana(mana_to_add)
#         super().do_it(state,subject,choices)  #adds triggers to super_stack
# =============================================================================


class PayMana(VerbAtomic):
    """deducts the given amount of mana from the gamestate's mana pool"""
    def __init__(self, mana_string_getter:Get.Const ):
        super().__init__( [mana_string_getter] )
        # self.mana_cost = ManaHandler.ManaCost(mana_string)
        
    def can_be_done(self, state, subject, choices):
        # mana_string = choices[0]
        mana_string = self.getter_list[0].get(state,subject)
        mana_cost = ManaHandler.ManaCost( mana_string)
        return state.pool.CanAffordCost(mana_cost)
    
    def do_it(self, state, subject, choices):
        # mana_string = choices[0]
        mana_string = self.getter_list[0].get(state,subject)
        mana_cost = ManaHandler.ManaCost( mana_string)
        state.pool.PayCost(mana_cost)
        super().do_it(state,subject,choices)  #adds triggers to super_stack
        
    
class AddMana(VerbAtomic):
    """adds the given amount of mana to the gamestate's mana pool"""
    def __init__(self, mana_string_getter:Get.Const):
        super().__init__( [mana_string_getter] )
        
    def can_be_done(self, state, subject ,choices):
        return True
    
    def do_it(self, state, subject, choices): 
        mana_string = self.getter_list[0].get(state,subject)
        mana_to_add = ManaHandler.ManaPool( mana_string)
        state.pool.AddMana(mana_to_add)
        super().do_it(state,subject,choices)  #adds triggers to super_stack

# ----------

class TapSelf(VerbOnSourceCard):
    """taps `subject` if it was not already tapped."""
    
    def __init__(self):
        super().__init__([])
    
    def can_be_done(self, state, source ,choices):
        return (not source.tapped and source.zone == ZONE.FIELD)
    
    def do_it(state, source ,choices):
        source.tapped = True
        super().do_it(state,source,choices)  #adds triggers to super_stack


class TapSymbol(TapSelf):
    """{T}. `subject` gets tapped if it's not a summoning-sick creature"""
    
    def can_be_done(self, state, source ,choices):
        return (super().can_be_done(state,source,choices) 
                and not (Match.CardType(Creature).match(source,state,source)
                         and source.summon_sick))
    
    def __str__(self):
        return "{T}"

# ----------

class ActivateOncePerTurn(VerbOnSourceCard):
    """Marks the given `subject` as only able to activate this ability once
    per turn"""
    
    def __init__(self, ability_name:str):
        super().__init__([])
        self.counter_text = "@"+ability_name #marks using an "invisible" counter
    
    def can_be_done(self, state, subject, choices):
        return (subject.zone == ZONE.FIELD
                and self.counter_text not in subject.counters)
    
    def do_it(self, state, subject, choices):
        subject.add_counter(self.counter_text)
        super().do_it(state,subject,choices)  #adds triggers to super_stack
        
# ----------

class ActivateOnlyAsSorcery(VerbAtomic):
    """Checks that the stack is empty and cannot be done otherwise"""

    def __init__(self):
        super().__init__([])

    def can_be_done(self, state, subject, choices):
        return len(state.stack)==0
    
    def do_it(self, state, subject, choices):
        return #doesn't actually DO anything, only exists as a check
    
# ----------

class MoveToZone(VerbOnSourceCard):
    def __init__(self, destination_zone):
        super().__init__([])
        self.destination = destination_zone
        self.origin = None #to let triggers check where card moved from
    
    def can_be_done(self, state, subject, choices):
        if subject.zone in [ZONE.DECK,ZONE.HAND,ZONE.FIELD,ZONE.GRAVE,ZONE.STACK]:
            return  subject in state.get_zone(subject.zone)
    
    def do_it(self, state, subject, choices):
        self.origin = subject.zone  #to let triggers check where card moved from
        #remove from origin
        if self.origin in [ZONE.DECK, ZONE.HAND, ZONE.FIELD, ZONE.GRAVE, ZONE.STACK]:
            state.get_zone(self.origin).remove(subject)
        # add to destination
        subject.zone = self.destination
        zonelist = state.get_zone(self.destination)
        zonelist.append(subject)
        #sort the zones that need to always be sorted
        if self.destination in [ZONE.HAND, ZONE.FIELD, ZONE.GRAVE]:
            zonelist.sort(key=Cardboard.Cardboard.get_id)
        # any time you change zones, reset the cardboard parameters
        subject.tapped = False
        subject.summon_sick = True
        subject.counters = [c for c in subject.counters if c[0]=="$"] #sticky counters stay
        super().do_it(state,subject,choices)  #adds triggers to super_stack

# ----------

class DrawCard(VerbAtomic):
    """draw from index 0 of deck"""
    
    def __init__(self):
        super().__init__([])
    
    def can_be_done(self, state, subject ,choices):
        return True  #yes, even if the deck is 0, you CAN draw. you'll just lose
    
    def do_it(self, state, subject, choices):
        mover = MoveToZone(ZONE.HAND)
        mover.do_it(state, state.deck[0]) #adds move triggers to super_stack
        super().do_it(state, subject, choices)     #adds draw-specific triggers

#------------------------------------------------------------------------------

# class VerbOnSplitList(Verb):
#     def __init__(self, act_on_chosen:Verb, options:list, chosen:list,
#                  act_on_non_chosen:Verb = None):
#         super().__init__()
#         self.act_on_chosen = act_on_chosen
#         self.act_on_non_chosen = act_on_non_chosen
#         self.options = options
#         self.chosen = chosen
#         #TODO


    
#------------------------------------------------------------------------------


# class CastSpell


# ----------

# ----------


class TapAny(Verb):
    
    def __init__(self, patterns:List[Match.CardPattern] ):
        getter = Get.Chooser( Get.ListFromZone(patterns,ZONE.FIELD), 1, False)
        super().__init__( TapSelf(), [getter] )







        
        
        