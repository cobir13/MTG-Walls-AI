# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from typing import List
from GameState import GameState
from Cardboard import Cardboard
from RulesText import Creature
import ManaHandler
import Choices
import ZONE


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


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
    
    @property
    def zone(self):
        if "zone" in self.dict_of_params:
            return self.dict_of_params["zone"]
        else:
            return None


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


class Getter:
    
    def get(self, state:GameState, subject:Cardboard):
        raise Exception


# ----------


class GetCardboardList(Getter):
    
    def get(self, state:GameState, subject:Cardboard) -> List[Cardboard]:
        raise Exception


# ----------


class MatchCardboardFromZone(GetCardboardList):
    
    def __init__(self, wildcard:WildCard):
        super().__init__()
        self.wildcard = wildcard
        
    def get(self, state:GameState, subject:Cardboard) -> List[Cardboard]:
        zone = state._GetZone(self.wildcard.zone)
        return [c for c in zone if self.wildcard.compare(c)]


# ----------


class MatchOtherFromZone(GetCardboardList):
    
    def __init__(self, wildcard:WildCard):
        super().__init__()
        self.wildcard = wildcard
        
    def get(self, state:GameState, subject:Cardboard) -> List[Cardboard]:
        zone = state._GetZone(self.wildcard.zone)
        return [c for c in zone if self.wildcard.compare(c) and not c is subject]


# ----------


class MatchCardboardFromTopOfDeck(GetCardboardList):
    
    def __init__(self, wildcard:WildCard, num_of_cards_deep:int):
        super().__init__()
        self.wildcard = wildcard
        self.num_of_cards_deep = num_of_cards_deep
        
    def get(self, state:GameState, subject:Cardboard) -> List[Cardboard]:
        top_of_deck = state.deck[:self.num_of_cards_deep]
        return [c for c in top_of_deck if self.wildcard.compare(c)]


# ----------


class GetConstantValue(Getter):
    
    def __init__(self, constant_value:list):
        super().__init__()
        self.constant_value = constant_value
        
    def get(self, state:GameState, subject:Cardboard):
        return self.constant_value


# ----------


class GetConstantCardboard(GetCardboardList):
    
    def __init__(self, cardboard):
        super().__init__()
        self.constant_value = cardboard
        
    def get(self, state:GameState, subject:Cardboard):
        return [self.constant_value]


# ----------


class GetSelf(GetCardboardList):
    
    def __init__(self):
        super().__init__()
        
    def get(self, state:GameState, subject:Cardboard):
        return [subject]


# ----------


class Count(Getter):
    """Get the number of Cardboards which match the wildcard"""
    
    def __init__(self, wildcard:WildCard):
        super().__init__()
        self.wildcard = wildcard
    
    def get(self, state:GameState, subject:Cardboard):
        zone = state._GetZone(self.wildcard.zone)
        return len( [c for c in zone if self.wildcard.compare(c)] )




# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


class Chooser:
    
    def __init__(self, getter:Getter, num_to_choose:int, can_be_less:bool ):
        self.getter = getter
        self.num_to_choose = num_to_choose
        self.can_be_less = can_be_less

    def choose(self,  state:GameState, subject:Cardboard) -> List[tuple]:
        """returns a list of all choices that have been selected. Each element
        of the list is a tuple of length N, where N is the number of items
        requested."""
        options = self.getter.get(state,subject) #list of tuples of items
        if self.must_be_exact:
            if self.num_to_choose == 1:
                return [(c,) for c in Choices.ChooseExactlyOne(options)]
            else:
                return Choices.ChooseExactlyN(options, self.num_to_choose)
        else:
            return Choices.ChooseNOrFewer(options, self.num_to_choose)


# ----------


class ChooseOneCardboard(Chooser):
    
    def __init__(self, getter:GetCardboardList, num_to_choose, can_be_less):
        super().__init__()
        self.getter = getter
        self.num_to_choose = num_to_choose
        self.can_be_less = can_be_less

        
# ----------


class ChooseOneOther(ChooseOneCardboard):
    """Choose exactly one cardboard that matches the given WildCard. Chosen
    card can't be self, either.  Returns empty list if fail, I guess."""
    def __init__(self, wildcard:WildCard ):
        super().__init__(MatchOtherFromZone(wildcard), 1,False)
        

# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------
        
class Action:
    def can_be_done(self, state:GameState, subject:Cardboard) -> bool:
        raise Exception
        
    def do_it(self, state:GameState, subject:Cardboard):
        raise Exception

    def __str__(self):
        return type(self).__name__



class ActionNoChoice(Action):
    
    def can_be_done(self, state:GameState, subject:Cardboard) -> bool:
        raise Exception
        
    def do_it(self, state:GameState, subject:Cardboard) -> GameState:
        """mutates!"""
        raise Exception



# -----------

class ActionWithChoice(Action):
    def __init__(self, action:ActionNoChoice, chooser:ChooseOneCardboard):
        super().__init__()
        self.action = action
        self.chooser = chooser
    
    def can_be_done(self, state:GameState, subject:Cardboard) -> bool:
        card_list = self.chooser.choose(state,subject)
        return any([ self.action.can_be_done(state,t[0]) for t in card_list])

    def do_it(self, state:GameState, subject:Cardboard) -> List[(GameState,Cardboard)]:
        """does NOT mutate."""
        new_state_list = []
        for opt in self.chooser.choose(state,subject):
            if self.action.can_be_done(state,opt[0]):
                output = state.copy_and_track(state,[subject,opt[0]])
                new_state,[new_subject,new_target] = output
                self.action.do_it(new_state,new_target)  #mutates
                new_state_list.append( (new_state,new_subject) )
        return new_state_list





#------------------------------------------------------------------------------


class PayMana(ActionNoChoice):
    """deducts the given amount of mana from the gamestate's mana pool"""
    
    def __init__(self, mana_string:str):
        super().__init__()
        self.mana_cost = ManaHandler.ManaCost(mana_string)
    
    def can_be_done(self, state, subject):
        return state.pool.CanAffordCost(self.mana_cost)
    
    def do_it(self, state, subject): 
        state.pool.PayCost(self.mana_cost)
        
    def __str__(self):
        return str(self.mana_cost)


# ----------


class AddMana(ActionNoChoice):
    """adds the given amount of mana to the gamestate's mana pool"""
    
    def __init__(self, mana_string:str):
        super().__init__()
        self.mana_value = ManaHandler.ManaPool(mana_string)
    
    def can_be_done(self, state, subject):
        return True
    
    def do_it(self, state, subject): 
        state.pool.AddMana(self.mana_value)
        
    def __str__(self):
        return str(self.mana_value)


# ----------


class TapSelf(ActionNoChoice):
    """taps `subject` if it was not already tapped."""
    
    def can_be_done(self, state, subject):
        return (not subject.tapped and subject.zone == ZONE.FIELD)
    
    def do_it(state, subject): 
        subject.tapped = True


# ----------


class TapSymbol(TapSelf):
    """{T}. `subject` gets tapped if it's not a summoning-sick creature"""
    
    def can_be_done(self, state, subject):
        return (super().can_be_done(state,subject) 
                and not (subject.has_type(Creature) and subject.summon_sick))
    
    def __str__(self):
        return "{T}"

# ----------


class TapAny(ActionWithChoice):
    
    def __init__(self, target:ChooseOneCardboard ):
        super().__init__(action=TapSelf(),target=target)
        

# #------------------------------------------------------------------------------


class ActivateOncePerTurn(ActionNoChoice):
    """Marks the given `subject` as only able to activate this ability once
    per turn"""
    
    def __init__(self, ability_name:str):
        super().__init__()
        self.counter_text = "@"+ability_name #marks using an "invisible" counter
    
    def can_be_done(self, state, subject):
        return (subject.zone == ZONE.FIELD
                and self.counter_text not in subject.counters)
    
    def do_it(self, state, subject):
        subject.add_counter(self.counter_text)
        

# #------------------------------------------------------------------------------


class ActivateOnlyAsSorcery(ActionNoChoice):
    """Checks that the stack is empty and cannot be done otherwise"""

    def can_be_done(self, state, subject):
        return len(state.stack)==0
    
    def do_it(self, state, subject):
        return #doesn't actually DO anything, only exists as a check
    

# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------
        


        
    
class Cost2:
    def __init__(self, pay_no_choice:List[ActionNoChoice] ):
        self.actions_no = pay_no_choice

    def CanAfford(self, gamestate, source):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return all([a.can_be_done(gamestate,source) for a in self.actions_no])


    def Pay(self, gamestate, source):
        """Returns list of GameStates where the cost has been paid.
        Takes in the GameState in which the cost is supposed to be paid and
            the source Cardboard that is generating the cost.
        Returns a list of (GameState,Cardboard) pairs in which the cost has
            been paid. The list is length 1 if there is exactly one way to pay
            the cost, and the list is length 0 if the cost cannot be paid.
        The original GameState and Source are NOT mutated.
        """
        ### RIGHT NOW THIS ONLY WORKS FOR ACTIONS WHICH RETURN A SINGLE
        ### MUTATED GAMESTATE
        newstate, [newsource] = gamestate.copy_and_track([source])
        for action in self.actions_no:
            action.do_it(newstate,newsource) #mutates
        return [(newstate,newsource)]


    def __str__(self):
        return " ".join([str(a) for a in self.actions_no])

    @property
    def mana_cost(self):
        mana_actions = [a for a in self.actions_no if isinstance(a,PayMana)]
        if len(mana_actions)>0:
            assert(len(mana_actions)==0)  #should only ever be one mana cost
            return mana_actions[0].mana_cost
        else:
            return ManaHandler.ManaCost("")
    
    @property
    def mana_value(self):
        return self.mana_cost.cmc()
            

    

    
    