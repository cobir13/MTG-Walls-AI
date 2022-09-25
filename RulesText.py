# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING, Type

import Getters
import Match as Match
import Costs
import Verbs

if TYPE_CHECKING:
    from GameState import GameState

from Abilities import ActivatedAbility, TriggeredAbility, TriggerWhenVerb,\
    TimedAbility
from Verbs import MarkAsPlayedLand, NullVerb, Tap, Verb, \
    PlayCardboard, PlayLand, PlayPermanent, AffectPlayer
import Zone
from Phases import Phases


# ------------------------------------------------------------------------------

class RulesText:
    caster_verb: Type[PlayCardboard] = PlayCardboard

    def __init__(self):
        self.name: str = ""
        self.cost: Costs.Cost = Costs.Cost()  # no mana or Verb costs
        self.keywords: List[str] = []
        # activated abilities
        self.activated: List[ActivatedAbility] = []  # includes mana abilities
        # triggered by verbs (actions that are done)
        self.trig_verb: List[TriggeredAbility] = []
        self.trig_timed: List[List[TimedAbility]] = [[] for ph in Phases]
        # I don't actually USE these, but in theory I could in the future
        # self.static = []     #static effects
        # NOTE: cast_destination.player=None, as don't know which player yet
        self.cast_destination: Zone.Zone = Zone.Unknown()
        self.effect: Verb | None = None

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

    def add_triggered(self, name: str, trigger: TriggerWhenVerb, effect: Verb):
        self.trig_verb.append(TriggeredAbility(name, trigger, effect))


# ----------------------------------------------------------------------------


class Permanent(RulesText):
    caster_verb: Type[PlayCardboard] = PlayPermanent

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
    caster_verb: Type[PlayCardboard] = PlayLand

    def __init__(self):
        super().__init__()
        self.cost = Costs.Cost(MarkAsPlayedLand())


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


class Sorcery(Spell):
    def __init__(self):
        super().__init__()


# ---------------------------------------------------------------------------


class TapSymbol(Tap):
    """{T}. `subject` gets tapped if it's not a summoning-sick creature"""

    def can_be_done(self, state: GameState) -> bool:
        is_critter = Match.CardType(Creature).match(self.subject, state,
                                                    self.player, self.source)
        is_sick = self.subject.summon_sick
        has_haste = Match.Keyword("haste").match(self.subject, state,
                                                 self.player, self.source)
        return (super().can_be_done(state)
                and (not is_critter or not is_sick or has_haste))

    def __str__(self):
        return "{T}"


class DeclareAttacker(AffectPlayer):
    """`source` is attacking card. `subject` is player (index)
    being attacked."""
    def can_be_done(self, state: GameState) -> bool:
        is_critter = Match.CardType(Creature).match(self.subject, state,
                                                    self.player, self.source)
        is_sick = self.subject.summon_sick
        has_haste = Match.Keyword("haste").match(self.subject, state,
                                                 self.player, self.source)
        is_defender = Match.Keyword("defender").match(self.subject, state,
                                                      self.player, self.source)
        return (super().can_be_done(state)
                and (is_critter and (not is_sick or has_haste)
                     and not is_defender))

    def do_it(self, state, to_track=[], check_triggers=True):
        has_vig = Match.Keyword("vigilance").match(self.subject, state,
                                                   self.player, self.source)
        if not has_vig:
            tapper = Tap()
            [tapper] = tapper.populate_options(state, self.player, self.source,
                                               self.cause)
            tapper = tapper.replace_subject(self.subject)
            tapper.do_it(state, check_triggers=False)
            # add tapper to sub_verbs, to be visible to triggers for tapping
            new_self = self.replace_verb(0, tapper)
            return Verb.do_it(new_self, state, to_track, check_triggers)
        else:
            # no visible action. Is no attacker list to add to, for example.
            return Verb.do_it(self, state, to_track, check_triggers)

    def __str__(self):
        return "Attack with " + str(self.subject)


# ----------

class Revert(Verbs.AffectCard):

    def do_it(self, state, to_track=[], check_triggers=True):
        """Reset the subject card back to its previous state. Mutates."""
        card = self.subject
        while hasattr(card.rules_text, "former"):
            card.rules_text = getattr(card.rules_text, "former")
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)


class Animate(Verbs.AffectCard):
    """Changes the subject card's RulesText to make it be a
    creature in addition to whatever else it was."""
    def __init__(self, creature_type: Creature):
        super().__init__()
        self.creature_type = creature_type

    def can_be_done(self, state: GameState) -> bool:
        return super().can_be_done(state) and self.subject.is_in(Zone.Field)

    def do_it(self, state, to_track=[], check_triggers=True):
        # make the new RulesText
        rules = self.creature_type.__init__()
        # overwrite the name
        rules.name = self.subject.name
        # add the previous keywords and abilities in addition to the new ones
        rules.keywords += self.subject.rules_text.keywords
        rules.activated += self.subject.rules_text.activated
        rules.trig_verb += self.subject.rules_text.trig_verb
        for ii in range(len(Phases)):
            rules.trig_timed[ii] += self.subject.rules_text.trig_timed[ii]
        # add a "revert at end of turn" ability
        rules.former = self.subject.rules_text
        abil_name = "revert " + self.subject.name,
        rules.trig_timed[Phases.ENDSTEP].append(
            TimedAbility(abil_name, Getters.ConstBool(True), Revert()))
        # overwrite with new RulesText
        self.subject.rules_text = rules
        # add history. maybe check_triggers (add to super_stack, trim inputs)
        return Verb.do_it(self, state, to_track, check_triggers)
