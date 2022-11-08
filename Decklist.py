# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""
import RulesText
from RulesText import Creature, Land  # , Instant, Sorcery
import Zone
import Match2
from Match2 import MoveType, SelfEnter, SelfAsEnter
import Verbs
from Verbs import TapSymbol
from Costs import Cost


import Getters as Get


# -----------------------------------------------------------------------------

class Roots(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Roots"
        self.cardtypes.extend(["plant", "wall"])
        self.cost = Cost("1G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 5)
        self.add_activated("Roots add G",
                           Cost(Verbs.AddCounter("-0/-1"),
                                Verbs.ActivateOncePerTurn("Roots add G")),
                           Verbs.AddMana("G"))


# -----------------------------------------------------------------------------

class Caryatid(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Caryatid"
        self.cardtypes.append("plant")
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
        self.cardtypes.append("dryad")
        self.cost = Cost("G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 3)
        self.add_activated("Caretaker add Au",
                           Cost(TapSymbol(),
                                Verbs.Tap().on(
                                    Get.Any(Match2.Another()
                                            & Match2.Untapped()
                                            & Match2.CardType("creature")),
                                    Get.CardListFrom(Zone.Field(Get.You()))
                                )),
                           Verbs.AddMana("A"))


# -----------------------------------------------------------------------------

class Battlement(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Battlement"
        self.cardtypes.append("wall")
        self.cost = Cost("1G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 4)
        self.add_activated(
            "Battlement add G",
            Cost(TapSymbol()),
            Verbs.AddMana(
                Get.RepeatString(
                    "G",
                    Get.Count(Match2.Keyword("defender"),
                              Zone.Field(Get.You()))))
        )


# -----------------------------------------------------------------------------

class Axebane(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Axebane"
        self.cardtypes.extend(["human", "druid"])
        self.cost = Cost("2G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 3)
        self.add_activated(
            "Axebane add Au",
            Cost(TapSymbol()),
            Verbs.AddMana(
                Get.RepeatString(
                    "A",
                    Get.Count(Match2.Keyword("defender"),
                              Zone.Field(Get.You()))))
        )


# -----------------------------------------------------------------------------

class Blossoms(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Blossoms"
        self.cardtypes.extend(["plant", "wall"])
        self.cost = Cost("1G")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 4)
        self.add_triggered("Blossoms etb draw", SelfEnter(), Verbs.DrawCard())


# -----------------------------------------------------------------------------

class Omens(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Omens"
        self.cardtypes.extend(["plant", "wall"])
        self.cost = Cost("1W")
        self.add_keywords(["defender"])
        self.set_power_toughness(0, 4)
        self.add_triggered("Omens etb draw", SelfEnter(), Verbs.DrawCard())


# -----------------------------------------------------------------------------

class Arcades(Creature):

    def __init__(self):
        super().__init__()
        self.name = "Arcades"
        self.cardtypes.extend(["elder", "dragon"])
        self.cost = Cost("1WUG")
        self.add_keywords(["flying", "vigilance"])
        self.set_power_toughness(3, 5)
        self.add_triggered("Arcades draw trigger",
                           MoveType(Match2.Keyword("defender"),
                                    None, Zone.Field(Get.Controllers())),
                           Verbs.DrawCard())


# -----------------------------------------------------------------------------

class Company(RulesText.Instant):
    def __init__(self):
        super().__init__()
        self.name = "CollectedCompany"
        self.cost = Cost("3G")
        self.effect = Verbs.Defer(
            Verbs.LookDoThenDo(
                Get.CardListFrom(Zone.DeckTopN(Get.You(), 6)),
                Get.Chooser(Match2.CardType("creature")
                            & Match2.ManaValue("<=", 3),
                            2, can_be_fewer=True),
                Verbs.MoveToZone(Zone.Field(Get.You())),
                Verbs.MoveToZone(Zone.DeckBottom(Get.You()))
            ))


# =============================================================================

# -----basic lands

class Forest(Land):

    def __init__(self):
        super().__init__()
        self.name = "Forest"
        self.cardtypes.extend(["basic", "forest"])
        self.add_activated("Forest add G", Cost(TapSymbol()),
                           Verbs.AddMana("G"))


class Plains(Land):

    def __init__(self):
        super().__init__()
        self.name = "Plains"
        self.cardtypes.extend(["basic", "plains"])
        self.add_activated("Plains add W", Cost(TapSymbol()),
                           Verbs.AddMana("W"))


class Island(Land):

    def __init__(self):
        super().__init__()
        self.name = "Island"
        self.cardtypes.extend(["basic", "island"])
        self.add_activated("Island add U", Cost(TapSymbol()),
                           Verbs.AddMana("U"))


class Swamp(Land):

    def __init__(self):
        super().__init__()
        self.name = "Swamp"
        self.cardtypes.extend(["basic", "swamp"])
        self.add_activated("Swamp add B", Cost(TapSymbol()),
                           Verbs.AddMana("B"))


class Mountain(Land):

    def __init__(self):
        super().__init__()
        self.name = "Mountain"
        self.cardtypes.extend(["basic", "plains"])
        self.add_activated("Mountain add R", Cost(TapSymbol()),
                           Verbs.AddMana("R"))


# -----shock lands

class TempleGarden(Forest, Plains):

    def __init__(self):
        super().__init__()
        self.name = "TempleGarden"
        self.cardtypes = [t for t in self.cardtypes if t != "basic"]
        # activating for two colors comes from the two inheritances
        self.add_triggered("shock",
                           SelfAsEnter(),
                           Verbs.Defer(Verbs.Modal([Verbs.Tap(),
                                                    Verbs.PayLife(2)]))
                           )


class BreedingPool(Forest, Island):

    def __init__(self):
        super().__init__()
        self.name = "BreedingPool"
        self.cardtypes = [t for t in self.cardtypes if t != "basic"]
        # activating for two colors comes from the two inheritances
        self.add_triggered("shock",
                           SelfAsEnter(),
                           Verbs.Defer(Verbs.Modal([Verbs.Tap(),
                                                    Verbs.PayLife(2)]))
                           )


class HallowedFountain(Plains, Island):

    def __init__(self):
        super().__init__()
        self.name = "HallowedFountain"
        self.cardtypes = [t for t in self.cardtypes if t != "basic"]
        # activating for two colors comes from the two inheritances
        self.add_triggered("shock",
                           SelfAsEnter(),
                           Verbs.Defer(Verbs.Modal([Verbs.Tap(),
                                                    Verbs.PayLife(2)]))
                           )


# -----fetch lands (simplified, etb trigger instead of tap ability)

class WindsweptHeath(Land):

    def __init__(self):
        super().__init__()
        self.name = "WindsweptHeath"
        # activating for two colors comes from the two inheritances
        self.add_triggered("GW fetch etb",
                           SelfEnter(),
                           Verbs.PayLife(1)
                           + Verbs.Sacrifice()
                           + Verbs.Defer(
                               Verbs.SearchDeck(Zone.Field(Get.You()),
                                                1,
                                                Match2.CardType("forest")
                                                | Match2.CardType("forest")))
                           )


class MistyRainforest(Land):

    def __init__(self):
        super().__init__()
        self.name = "MistyRainforest"
        # activating for two colors comes from the two inheritances
        self.add_triggered("GW fetch etb",
                           SelfEnter(),
                           Verbs.PayLife(1)
                           + Verbs.Sacrifice()
                           + Verbs.Defer(
                               Verbs.SearchDeck(Zone.Field(Get.You()),
                                                1,
                                                Match2.CardType("forest")
                                                | Match2.CardType("island")))
                           )


class FloodedStrand(Land):

    def __init__(self):
        super().__init__()
        self.name = "WindsweptHeath"
        # activating for two colors comes from the two inheritances
        self.add_triggered("GW fetch etb",
                           SelfEnter(),
                           Verbs.PayLife(1)
                           + Verbs.Sacrifice()
                           + Verbs.Defer(
                               Verbs.SearchDeck(Zone.Field(Get.You()),
                                                1,
                                                Match2.CardType("island")
                                                | Match2.CardType("plains")))
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
