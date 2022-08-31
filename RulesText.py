# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING

import Match as Match
import Costs
import Verbs

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard
    from Verbs import INPUTS

from Abilities import ActivatedAbility, TriggeredAbility, Trigger,\
    AlwaysTrigger
from Verbs import MarkAsPlayedLand, NullVerb, Tap, Verb, \
    PlayCardboard, PlayLand, PlayPermanent
import Zone


# ------------------------------------------------------------------------------

class RulesText:
    caster_verb: PlayCardboard = PlayCardboard()

    def __init__(self):
        self.name: str = ""
        self.cost: Costs.Cost = Costs.Cost()  # no mana or Verb costs
        self.keywords: List[str] = []
        # activated abilities
        self.activated: List[ActivatedAbility] = []  # includes mana abilities
        # triggered by verbs (actions that are done)
        self.trig_verb: List[TriggeredAbility] = []
        self.trig_upkeep = []
        self.trig_attack = []
        self.trig_endstep = []
        # I don't actually USE these, but in theory I could in the future
        # self.static = []     #static effects
        # NOTE: cast_destination.player=None, as don't know which player yet
        self.cast_destination: Zone.Zone = Zone.Unknown()
        self.effect: Verb = NullVerb()

    @property
    def mana_value(self):
        return self.cost.mana_value

    @property
    def mana_cost(self):
        return self.cost.mana_cost

    def add_keywords(self, words: List[str]):
        self.keywords += [w.lower() for w in words]

    def add_activated(self, name: str, cost: Costs.Cost, effect: Verb):
        self.activated.append(ActivatedAbility(name, cost, effect))

    def add_triggered(self, name: str, trigger: Trigger, effect: Verb):
        self.trig_verb.append(TriggeredAbility(name, trigger, effect))


# ----------------------------------------------------------------------------


class Permanent(RulesText):
    caster_verb: PlayCardboard = PlayPermanent()

    def __init__(self):
        super().__init__()
        self.cast_destination = Zone.Field(player=None)


class Creature(Permanent):

    def __init__(self):
        super().__init__()
        self.power = 0
        self.toughness = 0

    def set_power_toughness(self, power: int, toughness: int):
        self.power = power
        self.toughness = toughness


# class Human(Creature):
#     pass

# class Plant(Creature):
#     pass

# class Wall(Creature):
#     pass


class Land(Permanent):
    caster_verb: PlayCardboard = PlayLand()

    def __init__(self):
        super().__init__()
        self.cost = Costs.Cost(MarkAsPlayedLand())


# ---------------------------------------------------------------------------

class Spell(RulesText):
    caster_verb: PlayCardboard = PlayCardboard()

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


class Sorcery(Spell):
    def __init__(self):
        super().__init__()


# ---------------------------------------------------------------------------


class TapSymbol(Tap):
    """{T}. `subject` gets tapped if it's not a summoning-sick creature"""

    def can_be_done(self, state: GameState, controller, source: Cardboard,
                    other_input: INPUTS = []) -> bool:
        return (super().can_be_done(state, controller, source, other_input)
                and not (Match.CardType(Creature).match(source, state,
                                                        controller, source)
                         and source.summon_sick
                         and not Match.Keyword("haste").match(source, state,
                                                              controller,
                                                              source)))

    def __str__(self):
        return "{T}"


# ----------

class Revert(Verbs.AffectSourceCard):
    def can_be_done(self, state: GameState, controller, source: Cardboard,
                    other_input: INPUTS = []) -> bool:
        return True

    def do_it(self, state, player, source: Cardboard, other_inputs,
              check_triggers=True):
        while hasattr(source.rules_text, "former"):
            source.rules_text = getattr(source.rules_text, "former")
        return [(state, controller, source, other_input)]


class Animate(Verbs.AffectSourceCard):
    def __init__(self, creature_type: Creature):
        super().__init__()
        self.creature_type = creature_type

    def can_be_done(self, state, controller, source: Cardboard,
                    other_input: INPUTS = []) -> bool:
        return source.is_in(Zone.Field)

    def do_it(self, state, player, source: Cardboard, other_inputs,
              check_triggers=True):
        # make the new RulesText
        rules = self.creature_type.__init__()
        # overwrite the name
        rules.name = source.name
        # add the previous keywords and abilities in addition to the new ones
        rules.keywords += source.rules_text.keywords
        rules.activated += source.rules_text.activated
        rules.trig_verb += source.rules_text.trig_verb
        rules.trig_upkeep += source.rules_text.trig_upkeep
        rules.trig_attack += source.rules_text.trig_attack
        rules.trig_endstep += source.rules_text.trig_endstep
        # add a "revert at end of turn" ability
        rules.former = source.rules_text
        rules.trig_endstep.append(TriggeredAbility("revert " + source.name,
                                                   AlwaysTrigger(), Revert()))
        # overwrite with new RulesText
        source.rules_text = rules
        return super().do_it(state, controller, source, other_input)

    @property
    def mutates(self):
        return True
