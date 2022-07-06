# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    import Verb
# from Verbs import PlayLandForTurn
import ZONE


# ------------------------------------------------------------------------------

class RulesText:

    def __init__(self, name: str, cost: Verb, keywords: List[str]):
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
        self.trig_verb = []  # triggered by verbs (actions that are done)
        self.trig_upkeep = []
        self.trig_attack = []
        self.trig_endstep = []
        # I don't actually USE these, but in theory I could in the future
        # self.static = []     #static effects
        self.cast_destination = ZONE.UNKNOWN

    # abilities and triggers within a card are always called by the gamestate
    # by passing the source Cardboard into the function. Thus, the ability
    # doesn't need to know parent Cardboard ahead of time.  This allows me to
    # make CardTypes that are generic and never mutated and maintain the
    # distinction between Cardboard and RulesText. This distinction makes it much
    # easier to copy and iterate Gamestates.

    def can_afford(self, gamestate, source):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return self.cost.can_be_done(gamestate, source)

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


# class Human(Creature):
#     pass

# class Plant(Creature):
#     pass

# class Wall(Creature):
#     pass


class Land(Permanent):
    pass


#     def __init__(self, name, keywords):
#         super().__init__(name, PlayLandForTurn, keywords)
#         # if "land" not in self.keywords:
#         #     self.keywords = ["land"] + self.keywords
#
#
#
#
#     def EnterTapped(gamestate, source):
#         """useful for tap-lands. GameState,Cardboard -> [GameState]. MUTATES."""
#         effects = gamestate.TapPermanent(source)
#         gamestate.stack += effects
#         return [gamestate]
#
#     def ShockIntoPlay(gamestate, source):
#         """useful for shock lands.  GameState,Cardboard -> [GameState]. MUTATES."""
#         gamestate2, [source2] = gamestate.copy_and_track([source])
#         # Either the land enters tapped OR we take 2 damage
#         source.tapped = True  # effect is allowed to mutate
#         gamestate2.life -= 2
#         return [gamestate, gamestate2]
#
#     def LandAvailable(gamestate, source):
#         """useful for abilities checking if the land can be tapped for mana,
#         GameState,Cardboard -> bool"""
#         return (not source.tapped and source.zone == ZONE.FIELD)


###----------------------------------------------------------------------------


class Spell(RulesText):

    def __init__(self, name, cost: Verb, keywords: List[str],
                 effect: Verb, dest_zone=ZONE.GRAVE):
        """
        name (str)  : name of this card.
        cost (Cost) : mana and additional cost to cast this card.
        keywords (list(str)):
                      List of lowercase tags describing this card. Includes
                      MtG types as well as relevant keywords.
                      
        dest_zone   : The ZONE the Cardboard is moved to after resolution.
        """
        super().__init__(name, cost, keywords)
        self.cast_destination = dest_zone
        self.effect = effect

    # def ResolveSpell(self, gamestate):
    #     """Note: assumes that the relevant Cardboard is the final element of
    #     the stack."""
    #     card = gamestate.stack[-1]
    #     assert (self is card.rules_text)
    #     statelist = []
    #     for state in self.resolve_fn(gamestate, card):  # [GameStates]
    #         # nothing new on stack. triggers go to SUPERstack, not stack.
    #         assert (card.is_equiv_to(state.stack[-1]))
    #         state.MoveZone(state.stack[-1], self.dest_zone)
    #         statelist += state.ClearSuperStack()
    #     return statelist
