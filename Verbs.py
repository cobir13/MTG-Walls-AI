# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from typing import List
from GameState import GameState
from Cardboard import Cardboard
import ManaHandler
import ZONE
import MatchCardPatterns as Match
import GettersAndChoosers as Get

from RulesText import Creature,Spell,Land

import Actions



class WinTheGameError(Exception):
    pass

class LoseTheGameError(Exception):
    pass



# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------
        
class Verb:
    def __init__(self, getter_list:List[Get.Getter]):
        self.getter_list = getter_list
    
    def can_be_done(self, state:GameState, source:Cardboard) -> bool:
        return True
        
    def do_it(self, state:GameState, source:Cardboard, choices:list):
        """if this Verb has `single_output`, then this function
        mutates the original gamestate.
        If it does not have `single_output` (which is to say, if it
        has multiple possible outputs), then it copies the original
        gamestate rather than mutating it.
        
        In either case, the function returns a list of 
        (GameState,Cardboard,List[Cardboard]) tuples, one tuple
        per possible way that this Verb can be executed. The
        elements in the tuple are the new GameState, the new source
        Cardboard, and any (copied) choices which have not yet been
        used up.
        """
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
            return [(state,source,choices[self.num_inputs:])]
        
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
#Multiple verbs, all of which are executed
#Multiple verbs, which are chosen between

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
        # first things first, copy gamestate so that it's safe to mutate
        state_copy, copied_cards = state.copy_and_track([source]+choices)
        source_copy = copied_cards[0]
        choices_copy = copied_cards[1:]
        old_tuple_list = [(state_copy,source_copy,choices_copy)]
        new_tuple_list = []
        # apply each verb to each gamestate possibility. each time, this
        # reduces the length of the choice_list left for the next verb to use.
        for verb in self.verbs:
            for g, c, ch in old_tuple_list:
                if verb.single_output:
                    # mutate the gamestates in old_tuple_list, return tuple
                    new_tuple = verb.do_it(g,c,ch)
                    # add them to the new_tuple_list
                    new_tuple_list.append( new_tuple )
                else:
                    new_tuple_list += verb.do_it(g,c,ch)
            old_tuple_list = new_tuple_list
            new_tuple_list = []
        #clear the superstack of all the new gamestates?
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
    
class VerbManyTimes(Verb):
    def __init__(self, verb:Verb, getter:Get.Integer):
        super().__init__([getter])
        self.verb = verb
    
    def can_be_done(self, state:GameState, source:Cardboard, choices) -> bool:
        return self.verb.can_be_done(state,source)
    
    def do_it(self, state:GameState, source:Cardboard, choices):
        """mutates!"""
        num_to_repeat = choices[0]        
        multi_verb = ManyVerbs( [self.verb]*num_to_repeat )
        return multi_verb.do_it(state, source, choices[1:])

    def __str__(self):
        return super().__str__(self)+"(%s)" %str(self.verb)

    def choose_choices(self, state:GameState, source:Cardboard):
        list_of_list_of_nums = self.getter_list[0].get(state, source)
        verb_choices = self.verb.choose_choices(state,source)
        #if many options, make more sublists (one with each added)
        newchoices = []
        for sublist in verb_choices:
            # need to duplicate the sublist according to the number of
            # repeats I'm going to do. otherwise we run out of choices!
            newchoices += [list_of_num+(sublist*list_of_num[0])
                               for list_of_num in list_of_list_of_nums]
        return newchoices

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
    
    def do_it(self, state, source, choices):
        # mana_string = choices[0]
        mana_string = self.getter_list[0].get(state,source)
        mana_cost = ManaHandler.ManaCost( mana_string)
        state.pool.PayCost(mana_cost)
        #add triggers to super_stack, reduce length of choices list
        return super().do_it(state,source,choices)
        
# ----------   
    
class AddMana(VerbAtomic):
    """adds the given amount of mana to the gamestate's mana pool"""
    def __init__(self, mana_string_getter:Get.Const):
        super().__init__( [mana_string_getter] )
        
    def can_be_done(self, state, source ,choices):
        return True
    
    def do_it(self, state, source, choices): 
        mana_string = self.getter_list[0].get(state,source)
        mana_to_add = ManaHandler.ManaPool( mana_string)
        state.pool.AddMana(mana_to_add)
        #add triggers to super_stack, reduce length of choices list
        return super().do_it(state,source,choices)

# ----------

class LoseOwnLife(VerbAtomic):
    def __init__(self, damage_getter:Get.Integer):
        super().__init__( [damage_getter] )
        
    def can_be_done(self, state, source ,choices):
        return True
    
    def do_it(self, state, source, choices): 
        damage = choices[0]
        state.life -= damage
        #add triggers to super_stack, reduce length of choices list
        return super().do_it(state,source,choices)

# ----------

class DealDamageToOpponent(VerbAtomic):
    def __init__(self, damage_getter:Get.Integer):
        super().__init__( [damage_getter] )
        
    def can_be_done(self, state, source ,choices):
        return True
    
    def do_it(self, state, source, choices): 
        damage = choices[0]
        state.opponentlife -= damage
        #add triggers to super_stack, reduce length of choices list
        return super().do_it(state,source,choices)

# ----------

class TapSelf(VerbOnSourceCard):
    """taps `subject` if it was not already tapped."""
    
    def __init__(self):
        super().__init__([])
    
    def can_be_done(self, state, source ,choices):
        return (not source.tapped and source.zone == ZONE.FIELD)
    
    def do_it(state, source ,choices):
        source.tapped = True
        #add triggers to super_stack, reduce length of choices list
        return super().do_it(state,source,choices)

# ----------

class TapSymbol(TapSelf):
    """{T}. `subject` gets tapped if it's not a summoning-sick creature"""
    
    def can_be_done(self, state, source ,choices):
        return (super().can_be_done(state,source,choices) 
                and not (Match.CardType(Creature).match(source,state,source)
                         and source.summon_sick))
    
    def __str__(self):
        return "{T}"

# ----------

class TapAny(VerbOnTarget):
    
    def __init__(self, patterns:List[Match.CardPattern] ):
        getter = Get.Chooser( Get.ListFromZone(patterns,ZONE.FIELD), 1, False)
        super().__init__( TapSelf(), [getter] )

# ----------

class UntapSelf(VerbOnSourceCard):
    
    def __init__(self):
        super().__init__([])
    
    def can_be_done(self, state, source ,choices):
        return (source.tapped and source.zone == ZONE.FIELD)
    
    def do_it(state, source ,choices):
        source.tapped = False
        #add triggers to super_stack, reduce length of choices list
        return super().do_it(state,source,choices)

# ----------

class ActivateOncePerTurn(VerbOnSourceCard):
    """Marks the given `subject` as only able to activate this ability once
    per turn"""
    
    def __init__(self, ability_name:str):
        super().__init__([])
        self.counter_text = "@"+ability_name #marks using an "invisible" counter
    
    def can_be_done(self, state, source, choices):
        return (source.zone == ZONE.FIELD
                and self.counter_text not in source.counters)
    
    def do_it(self, state, source, choices):
        source.add_counter(self.counter_text)
        #add triggers to super_stack, reduce length of choices list
        return super().do_it(state,source,choices)
        
# ----------

class ActivateOnlyAsSorcery(VerbAtomic):
    """Checks that the stack is empty and cannot be done otherwise"""

    def __init__(self):
        super().__init__([])

    def can_be_done(self, state, source, choices):
        return len(state.stack)==0
    
    def do_it(self, state, source, choices):
        #add triggers to super_stack, reduce length of choices list
        return super().do_it(state,source,choices)
    
# ----------

class MoveToZone(VerbOnSourceCard):
    def __init__(self, destination_zone):
        super().__init__([])
        self.destination = destination_zone
        self.origin = None #to let triggers check where card moved from
    
    def can_be_done(self, state, subject, choices):
        if subject.zone in [ZONE.DECK,ZONE.HAND,ZONE.FIELD,ZONE.GRAVE]:
            return  subject in state.get_zone(subject.zone)
    
    def do_it(self, state, source, choices):
        self.origin = source.zone  #to let triggers check where card moved from
        #remove from origin
        if self.origin in [ZONE.DECK, ZONE.HAND, ZONE.FIELD, ZONE.GRAVE]:
            state.get_zone(self.origin).remove(source)
        # add to destination
        source.zone = self.destination
        zonelist = state.get_zone(self.destination)
        zonelist.append(source)
        #sort the zones that need to always be sorted
        if self.destination in [ZONE.HAND, ZONE.FIELD, ZONE.GRAVE]:
            zonelist.sort(key=Cardboard.Cardboard.get_id)
        # any time you change zones, reset the cardboard parameters
        source.tapped = False
        source.summon_sick = True
        source.counters = [c for c in source.counters if c[0]=="$"] #sticky counters stay
        #add triggers to super_stack, reduce length of choices list
        return super().do_it(state,source,choices)

# ----------

class DrawCard(VerbAtomic):
    """draw from index 0 of deck"""
    
    def __init__(self):
        super().__init__([])
    
    def can_be_done(self, state, subject ,choices):
        return True  #yes, even if the deck is 0, you CAN draw. you'll just lose
    
    def do_it(self, state, source, choices):
        if len(state.deck)>0:
            mover = MoveToZone(ZONE.HAND)
            mover.do_it(state, state.deck[0]) #adds move triggers to super_stack
            #add triggers to super_stack, reduce length of choices list
            return super().do_it(state,source,choices)
        else:
            raise LoseTheGameError
    
# ----------

class PlayLandForTurn(VerbAtomic):
    """Doesn't actually move any cards, just toggles the gamestate to say
    that we have played a land this turn"""
    
    def __init__(self):
        super().__init__([])
    
    def can_be_done(self, state, subject ,choices):
        return not state.has_played_land
    
    def do_it(self, state, source, choices):
        state.has_played_land = True
        #add triggers to super_stack, reduce length of choices list
        return super().do_it(state,source,choices)

# ----------

class AsEnterEffect(Verb):
    pass #TODO






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

class ActivateAbility(VerbAtomic):
    def __init__(self):
        super().__init__([])

    def can_be_done(self, state, source, choices):
        """Activate the ability which is the first element of
        `choices`.  The source of the ability is assumed to be
        the `source` Cardboard.
        """
        assert(len(choices)==1)
        ability = choices[0]
        payment_choices = ability.cost.choose_choices(state,source)
        return any( [ability.cost.can_afford(state,source,ch)
                     for ch in payment_choices])
    
    def do_it(self, state, source, choices):
        """Activate the ability which is the first element of
        `choices`, including making any choices necessary to do that.
        The source of the ability is assumed to be the `source`
        Cardboard.
        """
        assert(len(choices)==1)
        ability = choices[0]
        # check to make sure the execution is legal
        if not ability.cost.can_afford(state,source,choices=None):
            return []
        game,[spell] = state.copy_and_track([source])
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payment_choices = ability.cost.choose_choices(game,spell)
        # 601.2c: choose targets and modes
        target_choices = []
        if isinstance(spell, Spell):
            target_choices = ability.effect.choose_choices(game,spell)            
        # 601.2f: determine total cost
        # 601.2g: activate mana abilities -- I don't actually permit this.
        # 601.2h: pay costs
        new_tuple_list = [] # (GameState, source, choices) list
        for choices1 in payment_choices:
            for choices2 in target_choices:
                # concatenate choice lists. the casting will chew through all
                # the payment choices, leaving only the target choices in
                # the resulting tuples. Then attach those to the StackCardboard
                new_tuple_list = []
                all_choices = choices1+choices2 # concatenated lists
                if ability.cost.single_output: #mutates
                    g,things = state.copy_and_track([source]+all_choices)
                    new_tuple_list += ability.cost.do_it(g,things[0],things[1:])
                else:
                    new_tuple_list += ability.cost.do_it(game,spell,all_choices)
        final_results = []
        for g,s,targets in new_tuple_list:
            # create the StackAbility and put it on the stack.
            g.stack.append( GameState.StackAbility(ability, s, targets) )            
            # 601.2i: ability has now "been activated".  Trigger abilities.
            # for actually activating the ability
            for g2,_,_ in super().do_it(g,s,[]):
                # Mana Abilities resolve instantly
                if ability.is_type(AddMana):
                    games_list = g2.stack[-1].resolve(g)
                else:
                    games_list = [g2]
                # clear the super_stack
                for g3 in games_list:
                    final_results += g3.ClearSuperStack()
        return final_results


    def choose_choices(self, state:GameState, source:Cardboard):
        return []

    def single_output(self):
        return False
    
    def num_inputs(self):
        return 1

#------------------------------------------------------------------------------  

class CastCard(VerbOnSourceCard):
    def __init__(self):
        super().__init__([])

    def can_be_done(self, state, source, *args):
        """Cast the `source` card"""
        payment_choices = source.cost.choose_choices(state,source)
        return any( [source.cost.can_afford(state,source,ch)
                     for ch in payment_choices])
    
    def do_it(self, state, source, *args):
        """Puts the `source` card on the stack, including making any
        choices necessary to do that. Returns (GameState,Cardboard)
        copies but does not mutate."""
        # check to make sure the execution is legal
        if not source.cost.can_afford(state,source,choices=None):
            return []
        game,[spell] = state.copy_and_track([source])
        # 601.2a: remove spell from hand in prep for moving to stack
        # I move it manually because MoveToZone can't do StackObjects properly
        if spell.origin in [ZONE.DECK, ZONE.HAND, ZONE.FIELD, ZONE.GRAVE, ZONE.STACK]:
            game.get_zone(spell.origin).remove(spell)
        spell.zone = ZONE.STACK
        spell.tapped = False
        spell.summon_sick = True
        spell.counters = [c for c in spell.counters if c[0]=="$"] #sticky counters stay
        # 601.2b: choose costs (additional costs, choose X, choose hybrid)
        payment_choices = spell.cost.choose_choices(game,spell)
        # 601.2c: choose targets and modes
        target_choices = []
        if isinstance(spell, Spell):
            target_choices = spell.effect.choose_choices(game,spell)            
        # 601.2f: determine total cost
        # 601.2g: activate mana abilities -- I don't actually permit this.
        # 601.2h: pay costs
        new_tuple_list = [] # (GameState, source, choices) list
        for choices1 in payment_choices:
            for choices2 in target_choices:
                # concatenate choice lists. the casting will chew through all
                # the payment choices, leaving only the target choices in
                # the resulting tuples. Then attach those to the StackCardboard
                new_tuple_list = []
                all_choices = choices1+choices2 # concatenated lists
                if spell.cost.single_output: #mutates
                    g,things = state.copy_and_track([source]+all_choices)
                    new_tuple_list += spell.cost.do_it(g,things[0],things[1:])
                else:
                    new_tuple_list += spell.cost.do_it(game,spell,all_choices)
        final_results = []
        for g,c,targets in new_tuple_list:
            # Finally finish moving the card to the stack (601.2a)
            # Special exception for lands, which go directly to play
            if c.has_type(Land):
                mover = MoveToZone(ZONE.FIELD)
                mover.do_it(g,c,targets)
            else:
                g.stack.append( GameState.StackCardboard(c,targets) )
            # 601.2i: spell has now "been cast".  trigger abilities
            # I already triggered abilities from paying costs. Now just
            # trigger for actually casting the spell, and clear super_stack.
            for g2,_,_ in super().do_it(g,c,[]):
                g.StateBasedActions()
                final_results += g2.ClearSuperStack()
        return final_results


    def choose_choices(self, state:GameState, source:Cardboard):
        """this refers only to choices made DURING CASTING."""
        cost_choices = source.rules_text.cost.choose_choices(state,source)
        if isinstance(source,Spell):
            effect_choices = source.rules_text.effect.choose_choices(state,source)
        else:
            effect_choices = []
        return cost_choices + effect_choices

    def single_output(self):
        return False
    
    def num_inputs(self):
        return 0
        