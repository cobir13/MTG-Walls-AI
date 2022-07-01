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


# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------


class CardPattern:
    def match(self, card:Cardboard, gamestate=None, source=None) -> bool:
        raise Exception

class MatchType(CardPattern):
    def __init__(self, card_type:RulesText):
        self.type_to_match = card_type
    def match(self, card, gamestate=None, source=None):
        return isinstance(card,self.type_to_match)
    
class MatchKeyword(CardPattern):
    def __init__(self, keyword:str):
        self.keyword_to_match = keyword
def match(self, card, gamestate=None, source=None):
        return self.keyword_to_match in card.rules_text.keywords

class MatchName(CardPattern):
    def __init__(self, name:str):
        self.name_to_match = name
    def match(self, card, gamestate=None, source=None):
        return self.name_to_match == card.rules_text.name

# class MatchZone(CardPattern):
#     def __init__(self, zone):
#         self.zone = zone
#     def match(self, card):
#         self.zone == card.zone

class MatchCounter(CardPattern):
    def __init__(self, counter_to_match:str):
        self.counter_to_match = counter_to_match
    def match(self, card, gamestate=None, source=None):
        return self.counter_to_match in card.counters

class MatchTapped(CardPattern):
    def match(self, card, gamestate=None, source=None):
        return card.tapped

class MatchUntapped(CardPattern):
    def match(self, card, gamestate=None, source=None):
        return not card.tapped

class MatchNumeric(CardPattern):
    """ 'card comparator value' """
    def __init__(self, comparator:str, value:int):
        assert(comparator in [">","<","=","==","<=",">=","!=",])
        self.comparator = comparator
        self.value = value
    def get_card_value(self,card:Cardboard):
        return None
    def match(self, card, gamestate=None, source=None):
        card_value = self.get_card_value(card)
        if card_value is None:
            return False
        if self.comparator == "=" or self.comparator == "==":
            return card_value == self.value 
        elif self.comparator == "<":
            return card_value < self.value
        elif self.comparator == "<=":
            return card_value <= self.value 
        elif self.comparator == ">":
            return card_value > self.value 
        elif self.comparator == ">=":
            return card_value >= self.value 
        elif self.comparator == "!=":
            return card_value != self.value
        else:
            raise ValueError("shouldn't be possible to get here!")
        
class MatchPower(MatchNumeric):
    """ 'card comparator value' """
    def get_card_value(self,card:Cardboard):
        if hasattr(card,"power"):
            return card.rules_text.power
        
class MatchToughness(MatchNumeric):
    """ 'card comparator value' """
    def get_card_value(self,card:Cardboard):
        if hasattr(card,"toughness"):
            return card.rules_text.toughness

class MatchManaValue(MatchNumeric):
    """ 'card comparator value' """
    def get_card_value(self,card:Cardboard):
        return card.rules_text.mana_value

class MatchNotSelf(CardPattern):
    def match(self, card, gamestate, source):
        return not (card is source)

class MatchSelf(CardPattern):
    def match(self, card, gamestate, source):
        return card is source


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


class GetConst(Getter):
    
    def __init__(self, constant_value):
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


class GetInteger(Getter):
    def get(self, state:GameState, subject:Cardboard) -> int:
        return super().get(state,subject)


class CountInZone(GetInteger):
    """Get the number of Cardboards which match the wildcard patterns"""
    
    def __init__(self, patterns:List[CardPattern],zone):
        super().__init__()
        self.patterns = patterns
        self.zone = zone
    
    def get(self, state:GameState, subject:Cardboard):
        zone = state.get_zone(self.zone)
        return len( [c for c in zone
                                 if all([p.match(c,state,subject) for p in self.patterns])] )


class GetConstInteger(GetInteger):
    def __init__(self, constant_value:int):
        super().__init__()
        self.constant_value = constant_value
        
    def get(self, state:GameState, subject:Cardboard):
        return self.constant_value


# ----------

class GetFromZone(GetCardboardList):
    
    def __init__(self, patterns:List[CardPattern], zone):
        super().__init__()
        self.patterns = patterns
        self.zone = zone
        
    def get(self, state:GameState, subject:Cardboard) -> List[Cardboard]:
        zone = state.get_zone(self.zone)
        return [c for c in zone if all([p.match(c,state,subject) for p in self.patterns])]
        

# ----------


class GetFromTopOfDeck(GetCardboardList):
    
    def __init__(self, patterns:List[CardPattern], get_depth:GetConstInteger):
        super().__init__()
        self.patterns = patterns
        self.get_depth = get_depth
        
    def get(self, state:GameState, subject:Cardboard) -> List[Cardboard]:
        num_of_cards_deep = self.get_depth.get(state,subject)
        top_of_deck = state.deck[:num_of_cards_deep]
        return [c for c in top_of_deck
                            if all([p.match(c,state,subject) for p in self.patterns])]




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
    
    def __init__(self, getter:GetCardboardList):
        super().__init__()
        self.getter = getter
        self.num_to_choose = 1
        self.can_be_less = False

    
        

# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------
        
class Verb:
    def can_be_done(self, state:GameState, subject:Cardboard) -> bool:
        return True
        
    def do_it(self, state:GameState, subject:Cardboard):
        raise Exception

    def __str__(self):
        return type(self).__name__



class VerbNoChoice(Verb):
    
    def can_be_done(self, state:GameState, subject:Cardboard) -> bool:
        return True
        
    def do_it(self, state:GameState, subject:Cardboard) -> None:
        """mutates!"""
        for source in state.field + state.grave + state.hand:
            for abil in source.rules_text.trig_do:
                if abil.is_triggered(self, state, source, subject):
                    new_effect = StackEffect2(source, [subject], abil)
                    state.super_stack.append(new_effect)


class VerbWithChoice(Verb):
    def __init__(self, action:Verb, chooser:ChooseOneCardboard):
        super().__init__()
        self.action = action
        self.chooser = chooser
    
    def can_be_done(self, state:GameState, subject:Cardboard) -> bool:
        card_list = self.chooser.choose(state,subject)
        return any([ self.action.can_be_done(state,t[0]) for t in card_list])

    def do_it(self, state:GameState, subject:Cardboard) -> List[tuple]:
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


class PayMana(VerbNoChoice):
    """deducts the given amount of mana from the gamestate's mana pool"""
    
    def __init__(self, mana_string:str):
        super().__init__()
        self.mana_cost = ManaHandler.ManaCost(mana_string)
    
    def can_be_done(self, state, subject):
        return state.pool.CanAffordCost(self.mana_cost)
    
    def do_it(self, state, subject): 
        state.pool.PayCost(self.mana_cost)
        super().do_it(state,subject)  #adds triggers to super_stack
        
    def __str__(self):
        return str(self.mana_cost)


# ----------


class AddMana(VerbNoChoice):
    """adds the given amount of mana to the gamestate's mana pool"""
    
    def __init__(self, mana_string:str):
        super().__init__()
        self.mana_value = ManaHandler.ManaPool(mana_string)
    
    def can_be_done(self, state, subject):
        return True
    
    def do_it(self, state, subject): 
        state.pool.AddMana(self.mana_value)
        super().do_it(state,subject)  #adds triggers to super_stack
        
    def __str__(self):
        return str(self.mana_value)



# ----------


class RepeatBasedOnState(VerbNoChoice):
    def __init__(self, action:Verb, getter:GetInteger):
        super().__init__()
        self.action = action
        self.getter = getter
    
    def can_be_done(self, state:GameState, subject:Cardboard) -> bool:
        return self.action.can_be_done(state,subject)
    
    def do_it(self, state:GameState, subject:Cardboard) -> GameState:
        """mutates!"""
        num_to_repeat = self.getter.get(state,subject)
        for _ in range(num_to_repeat):
            if self.action.can_be_done(state,subject):
                self.action.do_it(state,subject)
        super().do_it(state,subject)  #adds triggers to super_stack


# ----------


class TapSelf(VerbNoChoice):
    """taps `subject` if it was not already tapped."""
    
    def can_be_done(self, state, subject):
        return (not subject.tapped and subject.zone == ZONE.FIELD)
    
    def do_it(state, subject):
        subject.tapped = True
        super().do_it(state,subject)  #adds triggers to super_stack


# ----------


class TapSymbol(TapSelf):
    """{T}. `subject` gets tapped if it's not a summoning-sick creature"""
    
    def can_be_done(self, state, subject):
        return (super().can_be_done(state,subject) 
                and not (subject.has_type(Creature) and subject.summon_sick))
    
    def __str__(self):
        return "{T}"

# ----------


class TapAny(VerbWithChoice):
    
    def __init__(self, target:ChooseOneCardboard ):
        super().__init__(action=TapSelf(),target=target)
        

# ----------


class ActivateOncePerTurn(VerbNoChoice):
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
        super().do_it(state,subject)  #adds triggers to super_stack
        

# ----------


class ActivateOnlyAsSorcery(VerbNoChoice):
    """Checks that the stack is empty and cannot be done otherwise"""

    def can_be_done(self, state, subject):
        return len(state.stack)==0
    
    def do_it(self, state, subject):
        return #doesn't actually DO anything, only exists as a check
    

# ----------


# class CastSpell


# ----------


class MoveSelfToZone(VerbNoChoice):
    def __init__(self, destination_zone):
        super().__init__()
        self.destination = destination_zone
        self.origin = None
    
    def can_be_done(self, state, subject):
        if subject.zone in [ZONE.DECK,ZONE.HAND,ZONE.FIELD,ZONE.GRAVE,ZONE.STACK]:
            return  subject in state.get_zone(subject.zone)
    
    def do_it(self, state, subject):
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
        super().do_it(state,subject)  #adds triggers to super_stack

# ----------


class DrawCard(VerbNoChoice):
    """draw from index 0 of deck"""
    
    def can_be_done(self, state, subject):
        return True  #yes, even if the deck is 0, you CAN draw. you'll just lose
    
    def do_it(self, state, subject):
        mover = MoveSelfToZone(ZONE.HAND)
        mover.do_it(state, state.deck[0]) #adds move triggers to super_stack
        super().do_it(state, subject)     #adds draw-specific triggers



# #------------------------------------------------------------------------------
# #------------------------------------------------------------------------------
        

class Trigger:
    def __init__(self, verb_type:type, patterns_for_subject:List[CardPattern]):
        self.verb_type = verb_type
        self.patterns = patterns_for_subject


    def is_triggered(self, verb:Verb, state:GameState, source:Cardboard, triggerer:Cardboard):
        """`source` is source of possible trigger. `triggerer` is the
        thing which caused the trigger to be checked for viability."""
        return (isinstance(verb,self.verb_type)
                and all([p.match(triggerer,state,source) for p in self.patterns]) )


class TriggerOnMove(Trigger):
    def __init__(self, patterns_for_subject:List[CardPattern],origin,destination):
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
             






        
    
class Cost2:
    def __init__(self, pay_no_choice:List[VerbNoChoice] ):
        self.actions_no = pay_no_choice

    def can_afford(self, gamestate, source):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return all([a.can_be_done(gamestate,source) for a in self.actions_no])


    def pay(self, gamestate, source):
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
            return None
    
    @property
    def mana_value(self):
        if self.mana_cost is not None:
            return self.mana_cost.cmc()
        else:
            return None
            

class ActivatedAbility2:
    def __init__(self, name, cost:Cost2, effect_list:List[Verb]):
        self.name = name
        self.cost = cost
        self.effect_list = effect_list

    def can_afford(self, gamestate:GameState, source:Cardboard):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return self.cost.CanAfford(gamestate, source)
    
    def pay(self, gamestate:GameState, source:Cardboard):
        """
        Returns a list of (GameState,Cardboard) pairs in which the
        cost has been paid. The list is length 1 if there is exactly
        one way to pay the cost, and the list is length 0 if the cost
        cannot be paid.
        The original GameState and Source are NOT mutated.
        """
        if not self.cost.CanAfford(gamestate,source):
            return []
        else:
            return self.cost.pay(gamestate, source)
    
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




class StackEffect2:

    def __init__(self, source, otherlist, ability):
        self.source = source  # Cardboard source of the effect. "Pointer".
        self.otherlist = []  # list of other relevant Cardboards. "Pointers".
        self.ability = ability  # GenericAbility

    def PutOnStack(self, gamestate):
        """Returns list of GameStates where ability is paid for and now on
        stack.  Note: super_stack is empty in returned states."""
        return gamestate.ActivateAbilities(self.source, self.ability)

    def Enact(self, gamestate):
        """Returns list of GameStates resulting from performing this effect"""
        return self.ability.Execute(gamestate, self.source)

    def __str__(self):
        return self.ability.name

    def __repr__(self):
        return "Effect: " + self.ability.name

    def get_id(self):
        cards = ",".join([c.get_id() for c in [self.source] + self.otherlist])
        return "E(%s|%s)" % (cards, self.ability.name)

    def is_equiv_to(self, other):
        return self.get_id() == other.get_id()
        # return (    type(self) == type(other)
        #         and self.source == other.source
        #         and set(self.otherlist) == set(other.otherlist)
        #         and self.ability.name == other.ability.name)

    @property
    def name(self):
        return self.ability.name

    # def build_tk_display(self, parentframe, ):
    #     return tk.Button(parentframe,
    #                      text="Effect: %s" % self.name,
    #                      anchor="w",
    #                      height=7, width=10, wraplength=80,
    #                      padx=3, pady=3,
    #                      relief="solid", bg="lightblue")
