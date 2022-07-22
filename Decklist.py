# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""
from RulesText import Creature, Land, Instant, TapSymbol  # , Sorcery
import ZONE
import MatchCardPatterns as Match
import Verbs
from Verbs import ChooseAVerb, VerbManyTimes, VerbOnSplitList
from Costs import Cost

from Abilities import TriggerOnMove, AsEnterEffect, TriggerOnSelfEnter
import Getters as Get


# TAP = Cost("", [TapSymbol()])

# -----------------------------------------------------------------------------

class Roots(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Roots"
        self.cost = Cost("1G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 5)
        self.add_activated("Roots add G",
                           Cost(Verbs.AddCounterToSelf("-0/-1"),
                                Verbs.ActivateOncePerTurn("Roots add G")),
                           Verbs.AddMana("G"))


# -----------------------------------------------------------------------------

class Caryatid(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Caryatid"
        self.cost = Cost("1G")
        self.add_keywords(["defender", "hexproof"])
        self.set_power_toughness(0, 3)
        self.add_activated("Caryatid add Au", Cost(TapSymbol()),
                           Verbs.AddMana("A"))


# -----------------------------------------------------------------------------

class Caretaker(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Caretaker"
        self.cost = Cost("G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 3)
        self.add_activated("Caretaker add Au",
                           Cost(TapSymbol(),
                                Verbs.TapAny(Match.NotSelf() & Match.Untapped()
                                             & Match.CardType(Creature))),
                           Verbs.AddMana("A"))


# -----------------------------------------------------------------------------

class Battlement(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Battlement"
        self.cost = Cost("1G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 4)
        self.add_activated("Battlement add G",
                           Cost(TapSymbol()),
                           VerbManyTimes(Verbs.AddMana("G"),
                                         Get.NumberInZone(
                                             Match.Keyword("defender"),
                                             ZONE.FIELD)))


# -----------------------------------------------------------------------------

class Axebane(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Axebane"
        self.cost = Cost("2G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 3)
        self.add_activated("Axebane add Au",
                           Cost(TapSymbol()),
                           VerbManyTimes(Verbs.AddMana("A"),
                                         Get.NumberInZone(
                                             Match.Keyword("defender"),
                                             ZONE.FIELD)))


# -----------------------------------------------------------------------------

class Blossoms(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Blossoms"
        self.cost = Cost("1G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 4)
        self.add_triggered("Blossoms etb draw", TriggerOnSelfEnter(),
                           Verbs.DrawCard())


# -----------------------------------------------------------------------------

class Omens(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Omens"
        self.cost = Cost("1W")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 4)
        self.add_triggered("Omens etb draw", TriggerOnSelfEnter(),
                           Verbs.DrawCard())


# -----------------------------------------------------------------------------

class Arcades(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Arcades"
        self.cost = Cost("1WUG")
        self.add_keywords(["flying", "vigilance"])
        self.set_power_toughness(3, 5)
        self.add_triggered("Arcades draw trigger",
                           TriggerOnMove(Match.Keyword("defender"), None,
                                         ZONE.FIELD),
                           Verbs.DrawCard())


# -----------------------------------------------------------------------------


class Company(Instant):
    def __int__(self):
        super().__init__()
        self.name = "CollectedCompany"
        self.cost = Cost("3G")
        get_from = Get.ListTopOfDeck(Match.CardType(Creature) &
                                     Match.ManaValue("<=", 3),
                                     get_depth=6)
        self.effect = VerbOnSplitList(
            act_on_chosen=Verbs.MoveToZone(ZONE.FIELD),
            act_on_non_chosen=Verbs.MoveToZone(ZONE.DECK_BOTTOM),
            chooser=Get.Chooser(getter=get_from,
                                num_to_choose=2,
                                can_be_fewer=True)
        )


# =============================================================================

# -----basic lands

class Forest(Land):

    def __init__(self):
        super().__init__()
        self.name = "Forest"
        self.add_activated("Forest add G", Cost(TapSymbol()),
                           Verbs.AddMana("G"))


class Plains(Land):

    def __init__(self):
        super().__init__()
        self.name = "Plains"
        self.add_activated("Plains add W", Cost(TapSymbol()),
                           Verbs.AddMana("W"))


class Island(Land):

    def __init__(self):
        super().__init__()
        self.name = "Island"
        self.add_activated("Island add U", Cost(TapSymbol()),
                           Verbs.AddMana("U"))


class Swamp(Land):

    def __init__(self):
        super().__init__()
        self.name = "Swamp"
        self.add_activated("Swamp add B", Cost(TapSymbol()),
                           Verbs.AddMana("B"))


class Mountain(Land):

    def __init__(self):
        super().__init__()
        self.name = "Mountain"
        self.add_activated("Mountain add R", Cost(TapSymbol()),
                           Verbs.AddMana("R"))


# -----shock lands

class TempleGarden(Forest, Plains):

    def __init__(self):
        super().__init__()
        self.name = "TempleGarden"
        # activating for two colors comes from the two inheritances
        self.add_triggered("shock",
                           AsEnterEffect(Match.IsSelf(), None, ZONE.FIELD),
                           ChooseAVerb([Verbs.TapSelf(), Verbs.LoseOwnLife(2)])
                           )


class BreedingPool(Forest, Island):

    def __init__(self):
        super().__init__()
        self.name = "BreedingPool"
        # activating for two colors comes from the two inheritances
        self.add_triggered("shock",
                           AsEnterEffect(Match.IsSelf(), None, ZONE.FIELD),
                           ChooseAVerb([Verbs.TapSelf(), Verbs.LoseOwnLife(2)])
                           )


class HallowedFountain(Plains, Island):

    def __init__(self):
        super().__init__()
        self.name = "HallowedFountain"
        # activating for two colors comes from the two inheritances
        self.add_triggered("shock",
                           AsEnterEffect(Match.IsSelf(), None, ZONE.FIELD),
                           ChooseAVerb([Verbs.TapSelf(), Verbs.LoseOwnLife(2)])
                           )


# -----fetch lands (simplified, etb trigger instead of tap ability)

class WindsweptHeath(Land):

    def __init__(self):
        super().__init__()
        self.name = "WindsweptHeath"
        # activating for two colors comes from the two inheritances
        self.add_triggered("GW fetch etb",
                           TriggerOnSelfEnter(),
                           Verbs.LoseOwnLife(1) + Verbs.Sacrifice()
                           + Verbs.Tutor(ZONE.FIELD, 1,
                                         Match.CardType(Forest)
                                         | Match.CardType(Plains))
                           )


class MistyRainforest(Land):

    def __init__(self):
        super().__init__()
        self.name = "WindsweptHeath"
        # activating for two colors comes from the two inheritances
        self.add_triggered("GW fetch etb",
                           TriggerOnSelfEnter(),
                           Verbs.LoseOwnLife(1) + Verbs.Sacrifice()
                           + Verbs.Tutor(ZONE.FIELD, 1,
                                         Match.CardType(Forest)
                                         | Match.CardType(Island))
                           )


class FloodedStrand(Land):

    def __init__(self):
        super().__init__()
        self.name = "WindsweptHeath"
        # activating for two colors comes from the two inheritances
        self.add_triggered("GW fetch etb",
                           TriggerOnSelfEnter(),
                           Verbs.LoseOwnLife(1) + Verbs.Sacrifice()
                           + Verbs.Tutor(ZONE.FIELD, 1,
                                         Match.CardType(Island)
                                         | Match.CardType(Plains))
                           )

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
