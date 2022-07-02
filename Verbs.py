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
    def can_be_done(self, state:GameState, subject:Cardboard, *args) -> bool:
        return True
        
    def do_it(self, state:GameState, subject:Cardboard, *args):
        raise Exception

    def __str__(self):
        return type(self).__name__

#------------------------------------------------------------------------------

class VerbDeterministic(Verb):
    """A Verb which already contains all info needed to complete. It
    might use info about the boardstate on resolution, but there are
    no CHOICES to be made. Everything that will happen will happen
    automatically.
    As such, when these Verbs `do_it` they mutate the GameState they
    are given, rather than splitting into multiple possibilities.
    """
    def can_be_done(self, state:GameState, subject:Cardboard, *args) -> bool:
        return True
        
    def do_it(self, state:GameState, subject:Cardboard, *args) -> None:
        """mutates!"""
        for source in state.field + state.grave + state.hand:
            for abil in source.rules_text.trig_verb:
                if abil.is_triggered(self, state, source, subject):
                    new_effect = Actions.StackEffect2(source, [subject], abil)
                    state.super_stack.append(new_effect)

#------------------------------------------------------------------------------

class PayMana(VerbDeterministic):
    """deducts the given amount of mana from the gamestate's mana pool"""
    
    def __init__(self, mana_string:str):
        super().__init__()
        self.mana_cost = ManaHandler.ManaCost(mana_string)
    
    def can_be_done(self, state, subject, *args):
        return state.pool.CanAffordCost(self.mana_cost)
    
    def do_it(self, state, subject, *args):
        state.pool.PayCost(self.mana_cost)
        super().do_it(state,subject,*args)  #adds triggers to super_stack
        
    def __str__(self):
        return str(self.mana_cost)

# ----------

class AddMana(VerbDeterministic):
    """adds the given amount of mana to the gamestate's mana pool"""
    
    def __init__(self, mana_string:str):
        super().__init__()
        self.mana_value = ManaHandler.ManaPool(mana_string)
    
    def can_be_done(self, state, subject ,*args):
        return True
    
    def do_it(self, state, subject, *args): 
        state.pool.AddMana(self.mana_value)
        super().do_it(state,subject,*args)  #adds triggers to super_stack
        
    def __str__(self):
        return str(self.mana_value)

# ----------

class RepeatBasedOnState(VerbDeterministic):
    def __init__(self, action:Verb, getter:Get.Integer):
        super().__init__()
        self.action = action
        self.getter = getter
    
    def can_be_done(self, state:GameState, subject:Cardboard ,*args) -> bool:
        return self.action.can_be_done(state,subject)
    
    def do_it(self, state:GameState, subject:Cardboard ,*args) -> GameState:
        """mutates!"""
        num_to_repeat = self.getter.get(state,subject)
        for _ in range(num_to_repeat):
            if self.action.can_be_done(state,subject,*args):
                self.action.do_it(state,subject,*args)
        super().do_it(state,subject,*args)  #adds triggers to super_stack

# ----------

class TapSelf(VerbDeterministic):
    """taps `subject` if it was not already tapped."""
    
    def can_be_done(self, state, subject ,*args):
        return (not subject.tapped and subject.zone == ZONE.FIELD)
    
    def do_it(state, subject ,*args):
        subject.tapped = True
        super().do_it(state,subject,*args)  #adds triggers to super_stack


class TapSymbol(TapSelf):
    """{T}. `subject` gets tapped if it's not a summoning-sick creature"""
    
    def can_be_done(self, state, subject ,*args):
        return (super().can_be_done(state,subject,*args) 
                and not (subject.has_type(Creature) and subject.summon_sick))
    
    def __str__(self):
        return "{T}"

# ----------

class ActivateOncePerTurn(VerbDeterministic):
    """Marks the given `subject` as only able to activate this ability once
    per turn"""
    
    def __init__(self, ability_name:str):
        super().__init__()
        self.counter_text = "@"+ability_name #marks using an "invisible" counter
    
    def can_be_done(self, state, subject,*args):
        return (subject.zone == ZONE.FIELD
                and self.counter_text not in subject.counters)
    
    def do_it(self, state, subject, *args):
        subject.add_counter(self.counter_text)
        super().do_it(state,subject,*args)  #adds triggers to super_stack
        
# ----------

class ActivateOnlyAsSorcery(VerbDeterministic):
    """Checks that the stack is empty and cannot be done otherwise"""

    def can_be_done(self, state, subject ,*args):
        return len(state.stack)==0
    
    def do_it(self, state, subject ,*args):
        return #doesn't actually DO anything, only exists as a check
    
# ----------

class MoveToZone(VerbDeterministic):
    def __init__(self, destination_zone):
        super().__init__()
        self.destination = destination_zone
        self.origin = None
    
    def can_be_done(self, state, subject ,*args):
        if subject.zone in [ZONE.DECK,ZONE.HAND,ZONE.FIELD,ZONE.GRAVE,ZONE.STACK]:
            return  subject in state.get_zone(subject.zone)
    
    def do_it(self, state, subject ,*args):
        self.origin = subject.zone
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
        super().do_it(state,subject,*args)  #adds triggers to super_stack

# ----------

class DrawCard(VerbDeterministic):
    """draw from index 0 of deck"""
    
    def can_be_done(self, state, subject ,*args):
        return True  #yes, even if the deck is 0, you CAN draw. you'll just lose
    
    def do_it(self, state, subject ,*args):
        mover = MoveToZone(ZONE.HAND)
        mover.do_it(state, state.deck[0]) #adds move triggers to super_stack
        super().do_it(state, subject ,*args)     #adds draw-specific triggers

#------------------------------------------------------------------------------

class VerbOnSplitList(Verb):
    def __init__(self, act_on_chosen:Verb, options:list, chosen:list,
                 act_on_non_chosen:Verb = None):
        super().__init__()
        self.act_on_chosen = act_on_chosen
        self.act_on_non_chosen = act_on_non_chosen
        self.options = options
        self.chosen = chosen
        #TODO


#------------------------------------------------------------------------------

class VerbNondeterministic(Verb):
    """A Verb which has many possible ways of completing. This is
    usually related to a choice that a player could make (say, the
    selection of targets).
    As such, when these Verbs `do_it` they do not mutate the
    GameState they are given.  Rather, they split the GameState
    into multiple copies, each of which resolves differently.
    """
    def __init__(self, action:Verb, chooser_fn, getter:Get.Getter):
        super().__init__()
        self.action = action
        self.chooser_fn = chooser_fn
        self.getter = getter
    
    def can_be_done(self, state:GameState, subject:Cardboard ,*args) -> bool:
        options = self.getter.get(state,subject)
        return any([ self.action.can_be_done(state,t[0]) for t in options])

    def do_it(self, state:GameState, subject:Cardboard ,*args) -> List[tuple]:
        """does NOT mutate."""
        new_state_list = []
        for opt in self.chooser.choose(state,subject):
            if self.action.can_be_done(state,opt[0]):
                output = state.copy_and_track(state,[subject,opt[0]])
                new_state,[new_subject,new_target] = output
                #TODO
                self.action.do_it(new_state,new_target,*args)  #mutates
                new_state_list.append( (new_state,new_subject) )
        return new_state_list
    
#------------------------------------------------------------------------------


# class CastSpell


# ----------

# ----------


# class TapAny(VerbNondeterministic):
    
#     def __init__(self, target:ChooseOneCardboard ):
#         super().__init__(action=TapSelf(),target=target)
        