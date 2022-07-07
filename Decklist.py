# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""

from RulesText import Creature, Land, Spell
import ZONE
import MatchCardPatterns as Match
import Verbs
from Abilities import ActivatedAbility, TriggeredAbility, TriggerOnMove

import Getters as Get

# -----------------------------------------------------------------------------

Roots = Creature("Roots", Verbs.PayMana("1G"), ["defender"], 0, 5)
Roots.activated.append(
    ActivatedAbility("Roots add G",
                     Verbs.ManyVerbs([Verbs.AddCounterToSelf("-0/-1"),
                                      Verbs.ActivateOncePerTurn(
                                          "Roots add G")]),
                     Verbs.AddMana("A")))

# -----------------------------------------------------------------------------

Caryatid = Creature("Caryatid", Verbs.PayMana("1G"),
                    ["defender", "hexproof"], 0, 3)
Caryatid.activated.append(
    ActivatedAbility("Caryatid add Au", Verbs.TapSymbol(), Verbs.AddMana("A")))

# -----------------------------------------------------------------------------

Caretaker = Creature("Caretaker", Verbs.PayMana("1G"), ["defender"], 0, 3)
Caretaker.activated.append(
    ActivatedAbility("Caretaker add Au",
                     Verbs.ManyVerbs([Verbs.TapSymbol(),
                                      Verbs.TapAny([Match.NotSelf(),
                                                    Match.Untapped(),
                                                    Match.CardType(Creature)
                                                    ])
                                      ]),
                     Verbs.AddMana("A")))

# -----------------------------------------------------------------------------

Battlement = Creature("Battlement", Verbs.PayMana("1G"),
                      ["defender"], 0, 4)
Battlement.activated.append(
    ActivatedAbility("Battlement add G",
                     Verbs.TapSymbol(),
                     Verbs.VerbManyTimes(Verbs.AddMana("G"), Get.NumberInZone(
                         [Match.Keyword("defender")], ZONE.FIELD))))

# -----------------------------------------------------------------------------

Axebane = Creature("Axebane", Verbs.PayMana("2G"), ["defender"], 0, 3)
Axebane.activated.append(
    ActivatedAbility("Axebane add Au",
                     Verbs.TapSymbol(),
                     Verbs.VerbManyTimes(Verbs.AddMana("A"), Get.NumberInZone(
                         [Match.Keyword("defender")], ZONE.FIELD))))

# -----------------------------------------------------------------------------

Blossoms = Creature("Blossoms", Verbs.PayMana("1G"), ["defender"], 0, 4)
Blossoms.trig_verb.append(
    TriggeredAbility("Blossoms etb draw",
                     TriggerOnMove([Match.IsSelf()], None, ZONE.FIELD),
                     Verbs.DrawCard()))

# -----------------------------------------------------------------------------

Omens = Creature("Omens", Verbs.PayMana("1W"), ["defender"], 0, 4)
Omens.trig_verb.append(
    TriggeredAbility("Omens etb draw",
                     TriggerOnMove([Match.IsSelf()], None, ZONE.FIELD),
                     Verbs.DrawCard()))

# -----------------------------------------------------------------------------

Arcades = Creature("Arcades", Verbs.PayMana("1WUG"),
                   ["flying", "vigilance"], 3, 5)
Arcades.trig_verb.append(
    TriggeredAbility("Arcades draw trigger",
                     TriggerOnMove([Match.Keyword("defender")], None,
                                   ZONE.FIELD),
                     Verbs.DrawCard()))

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
# # ---------------------------------------------------------------------------
# 
# ###---basic lands
# 
# Forest = Land("Forest", ["basic", "forest"])
# Forest.activated.append(
#     ManaAbility("Forest add G",
#                 Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
#                 lambda g, s: ManaAbility.AddColor(g, s, "G")))
# 
# Plains = Land("Plains", ["basic", "plains"])
# Plains.activated.append(
#     ManaAbility("Plains add W",
#                 Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
#                 lambda g, s: ManaAbility.AddColor(g, s, "W")))
# 
# Island = Land("Island", ["basic", "island"])
# Island.activated.append(
#     ManaAbility("Island add U",
#                 Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
#                 lambda g, s: ManaAbility.AddColor(g, s, "U")))
# 
# ###---shock lands
# AsEnterShock = AsEnterEffect("ShockIntoPlay", Land.ShockIntoPlay)
# 
# TempleGarden = Land("TempleGarden", ["forest", "plains"])
# TempleGarden.activated.append(
#     ManaAbility("TempleGarden add W/G",
#                 Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
#                 lambda g, s: ManaAbility.AddDual(g, s, "W", "G")))
# TempleGarden.trig_move.append(AsEnterShock)
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
