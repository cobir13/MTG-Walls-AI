# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING

import ManaHandler

if TYPE_CHECKING:
    from VerbParents import Verb
    from GameState import GameState
    from Cardboard import Cardboard
    from Abilities import ActivatedAbility, TriggeredAbility
from Verbs import PlayLandForTurn, PayMana
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
        self.name: str = name
        self.cost: Verb = cost
        self.keywords: List[str] = [s.lower() for s in keywords]
        # activated abilities
        self.activated: List[ActivatedAbility] = []  # includes mana abilities
        # triggered by verbs (actions that are done)
        self.trig_verb: List[TriggeredAbility] = []
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
    # distinction between Cardboard and RulesText. This distinction makes it
    # easier to copy and iterate Gamestates.

    def can_afford(self, state: GameState, source: Cardboard):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        choice_list = self.cost.choose_choices(state, source)
        return any([self.cost.can_be_done(state, source, ch)
                    for ch in choice_list])

    @property
    def mana_value(self):
        mana_verbs = self.cost.get_sub_verbs(PayMana)
        if len(mana_verbs) == 0:
            return 0
        else:
            return sum([pay_mana.mana_cost.mana_value() for pay_mana in mana_verbs])

    @property
    def mana_cost(self):
        mana_verbs = self.cost.get_sub_verbs(PayMana)
        cost_str = "".join([str(v.mana_cost) for v in mana_verbs])
        return ManaHandler.ManaCost(cost_str)

# ----------------------------------------------------------------------------


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

    def __init__(self, name, keywords):
        super().__init__(name, PlayLandForTurn(), keywords)
        # if "land" not in self.keywords:
        #     self.keywords = ["land"] + self.keywords


#
#
#
#     def EnterTapped(gamestate, source) -> List[GameState]:
#         """useful for tap-lands. MUTATES."""
#         effects = gamestate.TapPermanent(source)
#         gamestate.stack += effects
#         return [gamestate]
#
#     def ShockIntoPlay(gamestate, source) -> List[GameState]:
#         """useful for shock lands.  MUTATES."""
#         gamestate2, [source2] = gamestate.copy_and_track([source])
#         # Either the land enters tapped OR we take 2 damage
#         source.tapped = True  # effect is allowed to mutate
#         gamestate2.life -= 2
#         return [gamestate, gamestate2]
#
#     def LandAvailable(gamestate, source) -> List[GameState]:
#         """useful for abilities checking if the land can be tapped for mana,
#         GameState,Cardboard -> bool"""
#         return (not source.tapped and source.zone == ZONE.FIELD)


# -----------------------------------------------------------------------------


class Spell(RulesText):

    def __init__(self, name, cost: Verb, keywords: List[str],
                 effect: Verb, destination_zone=ZONE.GRAVE):
        """
        name (str)  : name of this card.
        cost (Cost) : mana and additional cost to cast this card.
        keywords (list(str)):
                      List of lowercase tags describing this card.
                      Includes MtG types as well as relevant
                      keywords.
                      
        destination_zone   : The ZONE the Cardboard is moved to
                             after resolution.
        """
        super().__init__(name, cost, keywords)
        self.cast_destination = destination_zone
        self.effect = effect
