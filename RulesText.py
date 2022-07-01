# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""

from typing import List

from ManaHandler import ManaCost, ManaPool
import Costs
import ZONE
import Abilities


##---------------------------------------------------------------------------##

class RulesText():

    def __init__(self, name:str, cost:Costs.Cost, keywords:List[str]):
        """
        name (str)  : name of this card.
        cost (Cost) : mana and additional cost to cast this card.
        keywords (list(str)):
                      List of lowercase tags describing this card. Includes
                      MtG types as well as relevant keywords.
        """
        self.name = name
        self.cost = cost
        self.keywords = [s.lower() for s in keywords]
        # activated abilities
        self.activated = []  # includes mana abilities
        # triggered 
        self.trig_move = []
        self.trig_upkeep = []
        self.trig_attack = []
        self.trig_endstep = []
        ###---I don't actually USE these, but in theory I could in the future
        # self.trig_activate   #abilities that trigger when an ability is activated
        # self.trig_draw = []  #abilities that trigger when a card is drawn
        # self.static = []     #static effects
        self.cast_destination = ZONE.UNKNOWN

    # abilities and triggers within a card are always called by the gamestate
    # by passing the source Cardboard into the function. Thus, the ability
    # doesn't need to know parent Cardboard ahead of time.  This allows me to
    # make CardTypes that are generic and never mutated and maintain the
    # distinction between Cardboard and RulesText. This distinction makes it much
    # easier to copy and iterate Gamestates.

    def CanAfford(self, gamestate, source):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return self.cost.CanAfford(gamestate, source)

    ###----------------------------------------------------------------------------


class Permanent(RulesText):

    def __init__(self, name, cost, keywords):
        super().__init__(name, cost, keywords)
        self.cast_destination = ZONE.FIELD


class Creature(Permanent):

    def __init__(self, name, cost, keywords, power, toughness):
        super().__init__(name, cost, keywords)
        self.power = power
        self.toughness = toughness
        # if "creature" not in self.keywords:
        #     self.keywords = ["creature"] + self.keywords


class Human(Creature):
    pass

class Plant(Creature):
    pass

class Wall(Creature):
    pass





class Land(Permanent):

    def __init__(self, name, keywords):
        # build the "cost" of casting a land
        def canplayland(gamestate, source):
            return not gamestate.has_played_land

        def playland(gamestate, source):
            # doesn't actually move, just pays the "cost" of saying we've played a land
            newstate, [newsource] = gamestate.copy_and_track([source])
            newstate.has_played_land = True
            return [(newstate, newsource)]

        cost = Costs.Cost(None, canplayland, playland)
        # use normal initializer
        super().__init__(name, cost, keywords)
        if "land" not in self.keywords:
            self.keywords = ["land"] + self.keywords

    def EnterTapped(gamestate, source):
        """useful for tap-lands. GameState,Cardboard -> [GameState]. MUTATES."""
        effects = gamestate.TapPermanent(source)
        gamestate.stack += effects
        return [gamestate]

    def ShockIntoPlay(gamestate, source):
        """useful for shock lands.  GameState,Cardboard -> [GameState]. MUTATES."""
        gamestate2, [source2] = gamestate.copy_and_track([source])
        # Either the land enters tapped OR we take 2 damage
        source.tapped = True  # effect is allowed to mutate
        gamestate2.life -= 2
        return [gamestate, gamestate2]

    def LandAvailable(gamestate, source):
        """useful for abilities checking if the land can be tapped for mana,
        GameState,Cardboard -> bool"""
        return (not source.tapped and source.zone == ZONE.FIELD)


###----------------------------------------------------------------------------


class Spell(RulesText):

    def __init__(self, name, cost, keywords, resolve_fn, dest_zone=ZONE.GRAVE):
        """
        name (str)  : name of this card.
        cost (Cost) : mana and additional cost to cast this card.
        keywords (list(str)):
                      List of lowercase tags describing this card. Includes
                      MtG types as well as relevant keywords.
        resolve_fn  : gamestate,source -> [GameStates]
                      Applies the effect of the card.
                      NOTE: the card itself should still be on the stack when
                      resolve_fn is done. It will be moved automatically later.
                      NOTE: the super_stack should NOT be cleared by resolve_fn.
                      
        dest_zone   : The ZONE the Cardboard is moved to after resolution.
        """
        super().__init__(name, cost, keywords)
        self.dest_zone = dest_zone
        self.resolve_fn = resolve_fn

    def ResolveSpell(self, gamestate):
        """Note: assumes that the relevant Cardboard is the final element of
        the stack."""
        card = gamestate.stack[-1]
        assert (self is card.rules_text)
        statelist = []
        for state in self.resolve_fn(gamestate, card):  # [GameStates]
            # nothing new on stack. triggers go to SUPERstack, not stack.
            assert (card.is_equiv_to(state.stack[-1]))
            state.MoveZone(state.stack[-1], self.dest_zone)
            statelist += state.ClearSuperStack()
        return statelist
