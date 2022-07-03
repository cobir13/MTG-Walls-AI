# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 18:08:14 2022

@author: Cobi
"""

from typing import List
from GameState import GameState
from Cardboard import Cardboard
import Choices
import MatchCardPatterns as Match


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------

class Getter:
    def get(self, state:GameState, source:Cardboard):
        raise Exception
    @property
    def single_output(self):
        return True

class Const(Getter):
    def __init__(self, value):
        self.value = value
    def get(self, state:GameState, source:Cardboard):
        return self.value

class CardSingle(Getter):
    pass

class CardList(Getter):
    pass

class Integer(Getter):
    pass

class ConstInteger(Const,Integer):
    pass

class StringList(Getter):
    pass

class Bool(Getter):
    pass

class String(Getter):
    pass


# ----------

class NumberInZone(Integer):
    """Get the number of Cardboards which match the wildcard patterns"""
    def __init__(self, patterns:List[Match.CardPattern],zone):
        super().__init__()
        self.patterns = patterns
        self.zone = zone
    def get(self, state:GameState, source:Cardboard):
        zone = state.get_zone(self.zone)
        return len( [c for c in zone
                                 if all([p.match(c,state,source) for p in self.patterns])] )

# ----------

class ListFromZone(CardList):
    def __init__(self, patterns:List[Match.CardPattern], zone):
        super().__init__()
        self.patterns = patterns
        self.zone = zone
    def get(self, state:GameState, source:Cardboard) -> List[Cardboard]:
        zone = state.get_zone(self.zone)
        return [c for c in zone if all([p.match(c,state,source) for p in self.patterns])]

# ----------

class ListTopOfDeck(CardList):
    def __init__(self, patterns:List[Match.CardPattern], get_depth:Integer):
        super().__init__()
        self.patterns = patterns
        self.get_depth = get_depth
    def get(self, state:GameState, source:Cardboard) -> List[Cardboard]:
        num_of_cards_deep = self.get_depth.get(state,source)
        top_of_deck = state.deck[:num_of_cards_deep]
        return [c for c in top_of_deck
                            if all([p.match(c,state,source) for p in self.patterns])]

# ----------



class Keywords(StringList):
    def get(self, state:GameState, source:Cardboard) -> List[str]:
        return source.rules_text.keywords
    
class Name(String):
    def get(self, state:GameState, source:Cardboard) -> str:
        return source.rules_text.name
    
class Counters(StringList):
    def get(self, state:GameState, source:Cardboard) -> List[str]: 
        return source.counters

class IsTapped(Bool):
    def get(self, state:GameState, source:Cardboard) -> bool: 
        return source.tapped

class IsUntapped(Bool):
    def get(self, state:GameState, source:Cardboard) -> bool: 
        return not source.tapped
    
class Power(Integer):
    def get(self, state:GameState, source:Cardboard) -> int: 
        if hasattr(source.rules_text,"power"):
            return source.rules_text.power
        else:
            return None

class Toughness(Integer):
    def get(self, state:GameState, source:Cardboard) -> int: 
        if hasattr(source.rules_text,"toughness"):
            return source.rules_text.power
        else:
            return None
      
class ManaValue(Integer):
    """ 'card comparator value' """
    def get(self, state:GameState, source:Cardboard) -> int: 
        return source.rules_text.mana_value


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------




class Chooser(Getter):
    
    def __init__(self, getter:Getter, num_to_choose:int, can_be_less:bool ):
        self.getter = getter
        self.num_to_choose = num_to_choose
        self.can_be_less = can_be_less
    
    def get(self,  state:GameState, source:Cardboard) -> List[tuple]:
        """returns a list of all choices that have been selected. Each element
        of the list is a tuple of length N, where N is the number of items
        requested."""
        options = self.getter.get(state,source) #list of tuples of items
        if self.must_be_exact:
            if self.num_to_choose == 1:
                return [(c,) for c in Choices.ChooseExactlyOne(options)]
            else:
                return Choices.ChooseExactlyN(options, self.num_to_choose)
        else:
            return Choices.ChooseNOrFewer(options, self.num_to_choose)
   
    @property
    def single_output(self):
        return False



    
        
