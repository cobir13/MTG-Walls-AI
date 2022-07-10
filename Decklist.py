# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""
import VerbParents
from RulesText import Creature, Land, Spell
import ZONE
import MatchCardPatterns as Match
import Verbs
from VerbCastAndActivate import TapSymbol
from VerbParents import VerbManyTimes, ManyVerbs, ChooseVerb
from Abilities import TriggerOnMove, AsEnterEffect

import Getters as Get


# -----------------------------------------------------------------------------

class Roots(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Roots"
        self.cost = Verbs.PayMana("1G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 5)
        self.add_activated("Roots add G",
                           ManyVerbs([Verbs.AddCounterToSelf("-0/-1"),
                                      Verbs.ActivateOncePerTurn(
                                          "Roots add G")]),
                           Verbs.AddMana("G"))


# -----------------------------------------------------------------------------

class Caryatid(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Caryatid"
        self.cost = Verbs.PayMana("1G")
        self.add_keywords(["defender", "hexproof"])
        self.set_power_toughness(0, 3)
        self.add_activated("Caryatid add Au", TapSymbol(), Verbs.AddMana("A"))


# -----------------------------------------------------------------------------

class Caretaker(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Caretaker"
        self.cost = Verbs.PayMana("G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 3)
        self.add_activated("Caretaker add Au",
                           ManyVerbs([TapSymbol(),
                                      Verbs.TapAny([Match.NotSelf(),
                                                    Match.Untapped(),
                                                    Match.CardType(Creature)
                                                    ])
                                      ]),
                           Verbs.AddMana("A"))


# -----------------------------------------------------------------------------

class Battlement(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Battlement"
        self.cost = Verbs.PayMana("1G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 4)
        self.add_activated("Battlement add G",
                           TapSymbol(),
                           VerbManyTimes(Verbs.AddMana("G"),
                                         Get.NumberInZone(
                                             [Match.Keyword("defender")],
                                             ZONE.FIELD)))


# -----------------------------------------------------------------------------

class Axebane(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Axebane"
        self.cost = Verbs.PayMana("2G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 3)
        self.add_activated("Axebane add Au",
                           TapSymbol(),
                           VerbManyTimes(Verbs.AddMana("A"),
                                         Get.NumberInZone(
                                             [Match.Keyword("defender")],
                                             ZONE.FIELD)))


# -----------------------------------------------------------------------------

class Blossoms(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Blossoms"
        self.cost = Verbs.PayMana("1G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 4)
        self.add_triggered("Blossoms etb draw",
                           TriggerOnMove([Match.IsSelf()], None, ZONE.FIELD),
                           Verbs.DrawCard())


# -----------------------------------------------------------------------------

class Omens(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Omens"
        self.cost = Verbs.PayMana("1W")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 4)
        self.add_triggered("Omens etb draw",
                           TriggerOnMove([Match.IsSelf()], None, ZONE.FIELD),
                           Verbs.DrawCard())


# -----------------------------------------------------------------------------

class Arcades(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Arcades"
        self.cost = Verbs.PayMana("1WUG")
        self.add_keywords(["flying", "vigilance"])
        self.set_power_toughness(3, 5)
        self.add_triggered("Arcades draw trigger",
                           TriggerOnMove([Match.Keyword("defender")], None,
                                         ZONE.FIELD),
                           Verbs.DrawCard())


# -----------------------------------------------------------------------------

# Company = Spell(name="Company",
#                 cost = Verbs.PayMana("3G"),
#                 keywords = ["instant"],
#                 [ MatchCardboardFromTopOfDeck()]
# TODO
# I know I don't have the tech for this yet
# I need the weird "Verb on half of the list and then do a
# different verb on the other half of the list" templating.
# maybe make a Choose.Split or something? Select half
# but return both halves?

# =============================================================================

# -----basic lands

class Forest(Land):

    def __init__(self):
        super().__init__()
        self.name = "Forest"
        self.add_activated("Forest add G", TapSymbol(), Verbs.AddMana("G"))


class Plains(Land):

    def __init__(self):
        super().__init__()
        self.name = "Plains"
        self.add_activated("Plains add W", TapSymbol(), Verbs.AddMana("W"))


class Island(Land):

    def __init__(self):
        super().__init__()
        self.name = "Island"
        self.add_activated("Island add U", TapSymbol(), Verbs.AddMana("U"))


###---shock lands


class TempleGarden(Forest, Plains):

    def __init__(self):
        super().__init__()
        self.name = "TempleGarden"
        # activating for two colors comes from the two inheritances
        self.add_triggered("shock",
                           AsEnterEffect([Match.IsSelf()], None, ZONE.FIELD),
                           ChooseVerb([Verbs.TapSelf(),
                                       Verbs.LoseOwnLife(Get.ConstInteger(2))],
                                      Get.Chooser(Get.Const([0, 1]), 1, False))
                           )

#
# BreedingPool = Land("BreedingPool", ["forest", "island"])
# BreedingPool.activated.append(
#     ManaAbility("BreedingPool add U/G",
#                 Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
#                 lambda g, s: ManaAbility.AddDual(g, s, "U", "G")))
# BreedingPool.trig_move.append(AsEnterShock)
#
# HallowedFountain = Land("HallowedFountain", ["plains", "island"])
# HallowedFountain.activated.append(
#     ManaAbility("HallowedFountain add W/U",
#                 Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
#                 lambda g, s: ManaAbility.AddDual(g, s, "W", "U")))
# HallowedFountain.trig_move.append(AsEnterShock)
# 
# 
# ###---fetch lands
# 
# def FetchLandType(gamestate, source, keywords):
#     targets = []
#     for card in gamestate.deck:
#         if "land" in card.rules_text.keywords:
#             # if it's the right type of land...
#             if any([t in keywords for t in card.rules_text.keywords]):
#                 # and if we don't have it already...
#                 if not any([card.is_equiv_to(ob) for ob in targets]):
#                     targets.append(card)
#     if len(targets) == 0:  # fail to find. fetch still sacrificed
#         newstate, [fetch] = gamestate.copy_and_track([source])
#         newstate.LoseLife(1)
#         newstate.MoveZone(fetch, ZONE.GRAVE)
#         newstate.shuffle_deck()
#         return newstate.ClearSuperStack()
#     universes = []
#     for landcard in targets:
#         newstate, [newland, fetch] = gamestate.copy_and_track([landcard,
#                                                                   source])
#         newstate.LoseLife(1)
#         newstate.MoveZone(fetch, ZONE.GRAVE)
#         newstate.MoveZone(newland, ZONE.FIELD)
#         newstate.shuffle_deck()
#         universes += newstate.ClearSuperStack()
#     return universes
# 
# 
# WindsweptHeath = Land("WindsweptHeath", [])
# WindsweptHeath.trig_move.append(
#     AsEnterEffect("Fetch G/W",
#                   lambda g, s: FetchLandType(g, s, ["forest", "plains"])))
# 
# FloodedStrand = Land("FloodedStrand", [])
# FloodedStrand.trig_move.append(
#     AsEnterEffect("Fetch G/W",
#                   lambda g, s: FetchLandType(g, s, ["island", "plains"])))
# 
# MistyRainforest = Land("MistyRainforest", [])
# MistyRainforest.trig_move.append(
#     AsEnterEffect("Fetch G/W",
#                   lambda g, s: FetchLandType(g, s, ["forest", "island"])))
# =============================================================================


# Caretaker
# Caryatid
# Roots
# Battlement
# Axebane
# Blossoms
# Arcades
# Recruiter
# TrophyMage
# Staff
# Company

# Forest
# Plains
# Island
# TempleGarden
# BreedingPool
# HallowedFountain
# WindsweptHeath
# Westvale
# Wildwoods
# LumberingFalls
