# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from typing import List
from GameState import GameState
from Cardboard import Cardboard
from RulesText import RulesText,Creature
import ManaHandler
import Choices
import ZONE
import MatchCardPatterns as Match
from Verbs import Verb,MoveSelfToZone,PayMana,ManyVerbs



class Trigger:
    def __init__(self, verb_type:type, patterns_for_subject:List[Match.CardPattern]):
        self.verb_type = verb_type
        self.patterns = patterns_for_subject


    def is_triggered(self, verb:Verb, state:GameState, source:Cardboard, triggerer:Cardboard):
        """`source` is source of possible trigger. `triggerer` is the
        thing which caused the trigger to be checked for viability."""
        return (isinstance(verb,self.verb_type)
                and all([p.match(triggerer,state,source) for p in self.patterns]) )


class TriggerOnMove(Trigger):
    def __init__(self, patterns_for_subject:List[Match.CardPattern],origin,destination):
        self.ver_type = MoveSelfToZone
        self.patterns = patterns_for_subject
        self.origin = origin
        self.destination = destination
    
    def is_triggered(self, verb:Verb, state:GameState, source:Cardboard, triggerer:Cardboard):
        return (super().is_triggered(verb,state,source,triggerer)
                and (self.origin == verb.origin or self.origin is None)  #MoveSelfToZone has origin
                and (self.destination == triggerer.zone or self.destination is None)
                )
            
        
# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------
             






        
    
# class Cost2:
#     def __init__(self, payment_verbs:List[Verb] ):
#         self.verb = ManyVerbs(payment_verbs)

#     def can_afford(self, state:GameState, source:Cardboard):
#         """Returns boolean: can this gamestate afford the cost?
#         DOES NOT MUTATE."""
#         choices = self.verb.choose_choices(state,source)
#         return self.verb.can_be_done(state,source,choices)
        
#     def pay(self, state:GameState, source:Cardboard, choices:list):
#         """Returns list of GameStates where the cost has been paid.
#         Takes in the GameState in which the cost is supposed to be paid and
#             the source Cardboard that is generating the cost.
#         Returns a list of (GameState,Cardboard) pairs in which the cost has
#             been paid. The list is length 1 if there is exactly one way to pay
#             the cost, and the list is length 0 if the cost cannot be paid.
#         The original GameState and Source are NOT mutated.
#         """
#         # choices = self.verb.choose_choices(state,source)
#         return self.verb.do_it(state,source,choices)

#     def __str__(self):
#         return str(self.verb)

    # @property
    # def mana_cost(self):
    #     mana_actions = [a for a in self.verbs if isinstance(a,PayMana)]
    #     if len(mana_actions)>0:
    #         assert(len(mana_actions)==0)  #should only ever be one mana cost
    #         return mana_actions[0].mana_cost
    #     else:
    #         return None
    
    # @property
    # def mana_value(self):
    #     if self.mana_cost is not None:
    #         return self.mana_cost.cmc()
    #     else:
    #         return None
            




class ActivatedAbility2:
    def __init__(self, name, cost:Verb, effect:Verb):
        self.name = name
        self.cost = cost
        self.effect = effect

    def can_afford(self, gamestate:GameState, source:Cardboard):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return self.cost.can_be_done(gamestate, source)
    
    def pay(self, gamestate:GameState, source:Cardboard, choices):
        """
        Returns a list of (GameState,Cardboard) pairs in which the
        cost has been paid. The list is length 1 if there is exactly
        one way to pay the cost, and the list is length 0 if the cost
        cannot be paid.
        The original GameState and Source are NOT mutated.
        """
        if not self.CanAfford(gamestate,source):
            return []
        else:
            return self.cost.pay(gamestate, source)
    
    
    
    
    
    
    def apply_effect(self, gamestate:GameState, source:Cardboard, choices):
        """
        Returns a list of GameStates where the effect has been performed:
            - length 1 if there is exactly one way to do this
            - length 0 if this cannot be done (costs, lack of targets, etc)
            - length >1 if there are options that can be decided differently.
        The original GameState and source Cardboard are NOT mutated.
        """
        state_copy, [source_copy] = gamestate.copy_and_track([source])
        old_tuple_list = [(state_copy,source_copy)]
        new_tuple_list = []
        for verb in self.effect_list:
            if isinstance(verb, VerbNoChoice):
                #mutate the gamestates in old_tuple_list directly
                [verb.do_it(g,c,choices) for g,c in old_tuple_list]
            elif isinstance(verb, VerbWithChoice):
                #collect output of applying verb to each tuple in old_list
                for g,c in old_tuple_list:
                    new_tuple_list += verb.do_it(g,c,choices)
                old_tuple_list = new_tuple_list
                new_tuple_list = []
        #clear the superstack of all the new gamestates
        for g in old_tuple_list:
            new_tuple_list += g.ClearSuperStack()
        return new_tuple_list

    def __str__(self):
        return self.name
    




class TriggeredAbility2:
    def __init__(self, name, trigger:Trigger, effect_list:List[Verb]):
        self.name = name
        self.trigger = trigger
        self.effect_list = effect_list
    
    def is_triggered(self, verb:Verb, state:GameState, source:Cardboard,
                                                     triggerer:Cardboard):
        """
        Returns boolean "the given Verb meets the trigger condition"
        """
        return self.trigger.is_triggered(verb, state, source, triggerer)
        
    def apply_effect(self, gamestate:GameState, source:Cardboard):
        """
        Returns a list of GameStates where the effect has been performed:
            - length 1 if there is exactly one way to do this
            - length 0 if this cannot be done (costs, lack of targets, etc)
            - length >1 if there are options that can be decided differently.
        The original GameState and source Cardboard are NOT mutated.
        """
        state_copy, [source_copy] = gamestate.copy_and_track([source])
        old_tuple_list = [(state_copy,source_copy)]
        new_tuple_list = []
        for verb in self.effect_list:
            if isinstance(verb, VerbNoChoice):
                #mutate the gamestates in old_tuple_list directly
                [verb.do_it(g,c) for g,c in old_tuple_list]
            elif isinstance(verb, VerbWithChoice):
                #collect output of applying verb to each tuple in old_list
                for g,c in old_tuple_list:
                    new_tuple_list += verb.do_it(g,c)
                old_tuple_list = new_tuple_list
                new_tuple_list = []
        #clear the superstack of all the new gamestates
        for g in old_tuple_list:
            new_tuple_list += g.ClearSuperStack()
        return new_tuple_list

    def __str__(self):
        return self.name








    
    
# def CastSpell(self, cardboard):
#     """
#     DOES NOT MUTATE. Instead returns a list of GameStates in which the
#         given Cardboard has been cast and any effects of that casting have
#         been put onto the super_stack.
#     """
#     # check to make sure the execution is legal
#     if not cardboard.rules_text.cost.CanAfford(self, cardboard):
#         return []
    
#     game,[spell] = self.copy_and_track([cardboard])
#     #601.2a: move spell to stack
#     game.MoveZone(spell, ZONE.STACK)
#     #601.2b: choose modes and cost (additional costs, choose X, choose hybrid)
#     if hasattr(spell,"choose_modes"):
#         modes = spell.choose_modes(game)      #this will split the gamestate!
#     else:
#         modes = []
#     #601.2c: choose targets
#     if hasattr(spell,"choose_targets"):
#         targets = spell.choose_targets(game)  #this will split the gamestate!
#     else:
#         targets = []
#     #601.2f: determine total cost
#     #601.2g: activate mana abilities
#     #601.2h: pay costs
#     #601.2i: spell has now "been cast".  trigger abilities
    
    
#     #check state-based
#     #clear super_stack
    
#     # cast_list = []
#     # for state, card in cardboard.rules_text.cost.Pay(self, cardboard):
#     #     # Iterate through all possible ways the cost could have been paid.
#     #     # Each has a GameState and a Cardboard being cast. Move the card
#     #     # being cast to the stack, which adds any triggers to super_stack.
#     #     if card.has_type(RulesText.Land):
#     #         # special exception for Lands, which don't use the stack. Just
#     #         # move it directly to play and then resolve super_stack
#     #         # state is a copy so can mutate it safely.
#     #         state.MoveZone(card, ZONE.FIELD)
#     #     else:
#     #         state.MoveZone(card, ZONE.STACK)
#     #     state.StateBasedActions()  # check state-based actions
#     #     cast_list += state.ClearSuperStack()  # list of GameStates
#     # return cast_list