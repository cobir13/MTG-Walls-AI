# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from typing import List
from GameState import GameState
from Cardboard import Cardboard
from RulesText import Creature
import Choices
import ZONE




class WildCard:
    def __init__(self,**kwargs):
        self.dict_of_params = kwargs
    
    def compare(self, cardboard:Cardboard,quiet=True):
        if not quiet:
            print(" ")
            print(cardboard.name)
        for parameter in self.dict_of_params.keys():
            try:
                comparator,value = self.dict_of_params[parameter]
            except TypeError: #can't unpack one into two
                comparator = "instance" if parameter == "rules_text" else "="
                value = self.dict_of_params[parameter]
            #get value from the cardboard to compare to
            if hasattr(cardboard, parameter):
                other_value = getattr(cardboard,parameter)
            #if cardboard doesn't have it, then try rules_text
            elif hasattr(cardboard.rules_text, parameter):
                other_value = getattr(cardboard.rules_text,parameter)
            #if there is no comparable value, then cardboard fails comparison
            else:
                return False  #break loop, we found a False
            if callable(other_value):
                other_value = other_value()
            #compare
            if not quiet:
                print(parameter,value,comparator,other_value)
            
            if comparator == "instance" and not isinstance(other_value, value):
                return False
            elif comparator in ["is", "=", "=="] and not other_value == value:
                return False
            elif comparator == "<" and not other_value < value:
                return False
            elif comparator == ">" and not other_value > value:
                return False
            elif comparator == "!=" and not other_value != value:
                return False
        return True



# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


# class Getter:
#     def get(gamestate):
#         raise Exception


# class GetListUsingWildcard(Getter):
    
#     def __init__(self, wildcard:WildCard):
#         self.wildcard = wildcard
    
#     def get(self, gamestate):
#         zone = gamestate._GetZone(self.wildcard.zone)
#         return [c.is_equiv_to(self.wildcard) for c in zone]


# class GetFromTopOfDeck(Getter):

#     def __init__(self, num_of_cards_deep):
#         self.num_of_cards_deep = num_of_cards_deep
    
#     def get(self, gamestate):
#         return gamestate.deck[:self.num_of_cards_deep]


# class GetFromPresetList(Getter):
    
#     def __init__(self, preset_list:list):
#         self.preset_list = preset_list
    
#     def get(self, gamestate):
#         return self.preset_list


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


# class Chooser:
#     pass


# class ChooserConstant(Chooser):
    
#     def __init__(self,value):
#         self.value = value
   
#     def choose(self,**args):
#         return self.value


# class ChooserNFromList(Chooser):
    
#     def __init__(self, num_to_choose:int, must_be_exact:bool):
#         self.num_to_choose = num_to_choose
#         self.must_be_exact = must_be_exact
    
#     def choose(self, options:list):
#         """contains a LIST of all choices that have been made"""
#         if self.must_be_exact:
#             if self.num_to_choose == 1:
#                 return Choices.ChooseExactlyOne(options)
#             else:
#                 return Choices.ChooseExactlyN(options, self.num_to_choose)
#         else:
#             return Choices.ChooseNOrFewer(options, self.num_to_choose)


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


# class Act:
#     def can_be_done(self,state: GameState, subject: Cardboard) -> bool:
#         raise Exception
#     def do_it(self,state: GameState, subject: Cardboard) -> List[GameState]:
#         raise Exception    


# # class ActOnChosenCardboard(Act):

# #     def __init__(self, getter:Getter, chooser:Chooser,
# #                  act_on_chosen:Act, act_on_remainder:Act):
# #         super().__init__()
# #         self.getter = getter
# #         self.chooser = chooser
# #         self.act_on_chosen = act_on_chosen
# #         self.act_on_remainder = act_on_remainder

# #     def can_be_done(self,state, subject):
# #         options = self.getter.get(state)
# #         if len(options)==0:
# #             return False
        
        
    
# #     def do_it(self,state, subject):
# #         raise Exception 



        
        
# # class ActBasedOnGamestate(Act):

# #     def __init__(self, chooser:Chooser):
# #         super().__init__()
# #         self.chooser = chooser

# #     def can_be_done(state, subject):
# #         raise Exception 
    
# #     def do_it(state, subject):
# #         raise Exception 
        
# #------------------------------------------------------------------------------

# class AddMana(Act):
    
#     def __init__(self, color_string):
#         super().__init__()
#         self.color_string = color_string
    
#     def can_be_done(self, state, subject):
#         return True
    
#     def do_it(self, state, subject):
#         state.AddToPool(self.color_string)
    

# #------------------------------------------------------------------------------

# class TapSymbol(Act):
    
#     def can_be_done(self, state, subject):
#         return (not subject.tapped and subject.zone == ZONE.FIELD
#                 and (not subject.has_type(Creature) and subject.summon_sick))
    
#     def do_it(state, subject): 
#         subject.tapped = True

# #------------------------------------------------------------------------------

# class AddCounter(ActionWithChoice):
    
#     def can_be_done(self, state, subject):
#         return subject.zone == ZONE.FIELD
    
#     def do_it(self, state, subject): 
#         counter_string = self.Chooser.choose()
#         subject.add_counter(counter_string)

# #------------------------------------------------------------------------------

# class OncePerTurn(ActionWithChoice):
        
#     def can_be_done(self, state, subject):
#         counter_string = "@"+self.Chooser.choose()
#         return (counter_string not in subject.counters
#                 and subject.zone == ZONE.FIELD)
    
#     def do_it(self, state, subject):
#         counter_string = "@"+self.Chooser.choose()
#         subject.add_counter(counter_string)  #"@" counters clear at untap step

# #------------------------------------------------------------------------------



# class Ability2:
#     def __init__(self,name,cost,trigger,effect):
#         self.name = name
#         self.cost = [] if cost is None else cost  #list of Actions
#         self.trigger = [] if trigger is None else trigger
#         self.effect = effect
        
#     def can_afford(self, gamestate:GameState, source:Cardboard):
#         """Returns boolean: can this gamestate afford the cost?
#         DOES NOT MUTATE."""
#         if len(self.cost)>0:
#             return all([a.can_be_done(gamestate,source) for a in self.cost])
#         else:
#             return True
    
#     def pay_costs(self, gamestate:GameState, source:Cardboard):
#         """Returns list of GameState,Cardboard pairs in which the cost is paid.
#         Takes in the GameState in which the cost is supposed to be paid and
#             the source Cardboard that is generating the cost.
#         Returns a list of (GameState,Cardboard) pairs in which the cost has
#             been paid. The list is length 1 if there is exactly one way to pay
#             the cost, and the list is length 0 if the cost cannot be paid.
#         The original GameState and Source are NOT mutated.
#         """
#         if len(self.cost)>0:
#             old_states = [(gamestate,source)]
#             new_states = []
#             for action in self.cost:
#                 for g,s in old_states:
#                     # each action's do_it mutates the gamestate
#                     new_states += action.do_it(g,s)
#                 old_states = new_states
#                 new_states = []
#             return new_states
#         else:
#             # if there IS no cost, then paying the cost changes nothing
#             g, [s] = gamestate.copy_and_track([source])
#             return [(g, s)]
    
    

# # BELOW THIS POINT IS PSEUDO-CODE. I'LL COME BACK AND CHANGE IT TO BE REAL
# # CODE ONCE I DECIDE HOW IT SHOULD LOOK

# # Caryatid
# Ability2(name = "caryatid tap for Au",
#          cost = [TapSymbol()],
#          trigger = None,
#          effect = AddMana("A")
#          )

# # Roots
# Ability2(name = "Roots add G",
#          cost = [AddCounter("-0/-1"),OncePerTurn("Roots add G")],
#          trigger = None,
#          effect = AddMana("G")
#          )

# # Caretaker
# Ability2(name = "Caretaker add Au",
#          cost = [TapSymbol(),
#                  TapOther(Chooser( Match( WildCard( zone = ZONE.FIELD,
#                                                     rules_text = Creature,
#                                                     untapped = True
#                                                     ))))],
#          trigger = None,
#          effect = AddMana("A")
#          )