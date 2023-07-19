# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING, Type

if TYPE_CHECKING:
    from Match2 import VerbPattern

import Costs
from Abilities import ActivatedAbility, TriggeredAbility, TimedAbility,\
    ContinuousEffect
from Verbs import MarkAsPlayedLand, NullVerb, Verb, PlayCardboard, PlayLand,\
    PlayPermanent
import Zone


# ------------------------------------------------------------------------------

class RulesText:
    caster_verb: Type[PlayCardboard] = PlayCardboard

    def __init__(self):
        self.name: str = ""
        self.cost: Costs.Cost = Costs.Cost()  # no mana or Verb costs
        self.keywords: List[str] = []  # all lowercase
        self.cardtypes: List[str] = []  # all lowercase
        # activated abilities
        self.activated: List[ActivatedAbility] = []  # includes mana abilities
        # triggered by verbs (actions that are done)
        self.trig_verb: List[TriggeredAbility] = []
        self.trig_timed: List[TimedAbility] = []
        self.static: List[ContinuousEffect] = []  # static effects
        # NOTE: cast_destination.player=None, as don't know which player yet
        self.cast_destination: Zone.Zone = Zone.Unknown()
        self.effect: Verb | None = None

    @property
    def mana_value(self):
        return self.cost.mana_value

    @property
    def mana_cost(self):
        return self.cost.base_mana_cost

    def add_keywords(self, words: List[str]):
        self.keywords += [w.lower() for w in words]

    def add_activated(self, name: str, cost: Costs.Cost, effect: Verb):
        self.activated.append(ActivatedAbility(name, cost, effect))

    def add_triggered(self, name: str, condition: VerbPattern, effect: Verb):
        self.trig_verb.append(TriggeredAbility(name, condition, effect))


# ----------------------------------------------------------------------------


class Permanent(RulesText):
    caster_verb: Type[PlayCardboard] = PlayPermanent

    def __init__(self):
        super().__init__()
        self.cast_destination = Zone.Field(player=None)
        self.cardtypes.append("permanent")


class Creature(Permanent):

    def __init__(self):
        super().__init__()
        self.power = 0
        self.toughness = 0
        self.cardtypes.append("creature")

    def set_power_toughness(self, power: int, toughness: int):
        self.power = power
        self.toughness = toughness


class Land(Permanent):
    caster_verb: Type[PlayCardboard] = PlayLand

    def __init__(self):
        super().__init__()
        self.cost = Costs.Cost(MarkAsPlayedLand())
        self.cardtypes.append("land")


# ---------------------------------------------------------------------------

class Spell(RulesText):
    caster_verb: Type[PlayCardboard] = PlayCardboard

    def __init__(self):
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
        super().__init__()
        self.cast_destination = Zone.Grave(player=None)
        self.effect: Verb = NullVerb()


class Instant(Spell):
    def __init__(self):
        super().__init__()
        self.cardtypes.append("instant")


class Sorcery(Spell):
    def __init__(self):
        super().__init__()
        self.cardtypes.append("sorcery")


# ----------

# class Revert(Verbs.AffectCard):
#
#     def do_it(self, state, to_track=[], check_triggers=True):
#         """Reset the subject card back to its previous state. Mutates."""
#         card = self.subject
#         while hasattr(card.rules_text, "former"):
#             card.rules_text = getattr(card.rules_text, "former")
#         # add history. maybe check_triggers (add to super_stack, trim inputs)
#         return Verb.do_it(self, state, to_track, check_triggers)
#
#
# class Animate(Verbs.AffectCard):
#     """Changes the subject card's RulesText to make it be a
#     creature in addition to whatever else it was."""
#     def __init__(self, creature_type: Creature):
#         super().__init__()
#         self.creature_type = creature_type
#
#     def can_be_done(self, state: GameState) -> bool:
#         return super().can_be_done(state) and self.subject.is_in(Zone.Field)
#
#     def do_it(self, state, to_track=[], check_triggers=True):
#         # make the new RulesText
#         rules = self.creature_type.__init__()
#         # overwrite the name
#         rules.name = self.subject.name
#         # add the previous keywords and abilities in addition to the new ones
#         rules.keywords += self.subject.rules_text.keywords
#         rules.activated += self.subject.rules_text.activated
#         rules.trig_verb += self.subject.rules_text.trig_verb
#         for ii in range(len(Phases)):
#             rules.trig_timed[ii] += self.subject.rules_text.trig_timed[ii]
#         # add a "revert at end of turn" ability
#         rules.former = self.subject.rules_text
#         abil_name = "revert " + self.subject.name,
#         rules.trig_timed[Times.ENDSTEP].append(
#             TimedAbility(abil_name, Getters.ConstBool(True), Revert()))
#         # overwrite with new RulesText
#         self.subject.rules_text = rules
#         # add history. maybe check_triggers (add to super_stack, trim inputs)
#         return Verb.do_it(self, state, to_track, check_triggers)
