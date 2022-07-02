# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""

from RulesText import Creature, Land, Spell
import RulesText
from Abilities import ManaAbility, TriggeredByMove, AsEnterEffect  # ,ActivatedAbility
from Costs import Cost

import ZONE
import Choices




import MatchCardPatterns as Match
import GettersAndChoosers as Get



from Actions import Ability2,Cost2, TriggeredAbility2
from Actions import PayMana,AddMana,TapSymbol,AddCounterToSelf,ActivateOncePerTurn,RepeatBasedOnState,DrawCard
from Actions import TapAny
from Actions import ChooseOneCardboard
from Actions import Trigger,TriggerOnMove
# from Actions import MatchCardboardFromZone,MatchUntapped,MatchType,MatchKeyword,CountInZone,MatchNotSelf,MatchSelf,MatchCardboardFromTopOfDeck



##---------------------------------------------------------------------------##




Roots = Creature("Roots", Cost2([PayMana("1G")]), ["defender"], 0, 5)
Roots.activated.append(
        Ability2("Roots add G",
                 Cost2([AddCounterToSelf("-0/-1"),ActivateOncePerTurn()]),
                 [AddMana("A")] ))

##---------------------------------------------------------------------------##

Caryatid = Creature("Caryatid", Cost2([PayMana("1G")]), ["defender", "hexproof"], 0, 3)
Caryatid.activated.append(
        Ability2("Caryatid add Au", Cost2([TapSymbol()]), [AddMana("A")] ) )

##---------------------------------------------------------------------------##

Caretaker = Creature("Caretaker", Cost2([PayMana("1G")]), ["defender"], 0, 3)
Caretaker.activated.append(
        Ability2("Caretaker add Au",
                 Cost2( [TapSymbol(),
                         TapAny(ChooseOneCardboard(MatchCardboardFromZone(
                                     [MatchNotSelf(),MatchUntapped(),MatchType(Creature)],
                                     ZONE.FIELD) ) )
                        ]),
                 [AddMana("A")] ))


##---------------------------------------------------------------------------##

def BattlementAddColor(gamestate, source):
    num = sum(["defender" in c.rules_text.keywords for c in gamestate.field])
    newstate, [newsource] = gamestate.copy_and_track([source])
    newstate.pool.AddMana("G" * num)  # add mana
    return [newstate]


Battlement = Creature("Battlement", Cost2([PayMana("1G")]), ["defender"], 0, 4)
Battlement.activated.append(
        Ability2("Battlement add G",
                 Cost2([TapSymbol()]),
                 [RepeatBasedOnState(AddMana("G"),
                                     CountInZone([MatchKeyword("defender")],
                                                 ZONE.FIELD)
                                    )]
                 ))


##---------------------------------------------------------------------------##

def AxebaneAddColor(gamestate, source):
    num = sum(["defender" in c.rules_text.keywords for c in gamestate.field])
    newstate, [newsource] = gamestate.copy_and_track([source])
    newstate.pool.AddMana("A" * num)  # add mana
    return [newstate]


Axebane = Creature("Axebane", Cost2([PayMana("2G")]), ["defender"], 0, 3)
Axebane.activated.append(
    Ability2("Battlement add G",
             Cost2([TapSymbol()]),
             [RepeatBasedOnState(AddMana("G"),
                                 CountInZone([MatchKeyword("defender")],
                                             ZONE.FIELD)
                                )]
             ))

##---------------------------------------------------------------------------##

Blossoms = Creature("Blossoms", Cost2([PayMana("1G")]), ["defender"], 0, 4)
Blossoms.trig_move.append(
    TriggeredByMove("Blossoms etb draw",
                    TriggerOnMove( [MatchSelf], None, ZONE.FIELD),
                    [DrawCard()] ))

##---------------------------------------------------------------------------##

Omens = Creature("Omens", Cost2([PayMana("1G")]), ["defender"], 0, 4)
Omens.trig_move.append(
    TriggeredByMove("Omens etb draw",
                    TriggerOnMove( [MatchSelf], None, ZONE.FIELD),
                    [DrawCard()] ))

##---------------------------------------------------------------------------##

Arcades = Creature("Arcades", Cost2([PayMana("1WUG")]), ["flying", "vigilance"], 3, 5)
Arcades.trig_move.append(
    TriggeredByMove("Arcades draw trigger",
                TriggerOnMove( [MatchKeyword("defender")], None, ZONE.FIELD),
                [DrawCard()] ))


##---------------------------------------------------------------------------##

Company = Spell("Company", Cost2([PayMana("3G")]), 
                [ MatchCardboardFromTopOfDeck()]
                
                
                
                
                )

##---------------------------------------------------------------------------##

###---basic lands

Forest = Land("Forest", ["basic", "forest"])
Forest.activated.append(
    ManaAbility("Forest add G",
                Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
                lambda g, s: ManaAbility.AddColor(g, s, "G")))

Plains = Land("Plains", ["basic", "plains"])
Plains.activated.append(
    ManaAbility("Plains add W",
                Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
                lambda g, s: ManaAbility.AddColor(g, s, "W")))

Island = Land("Island", ["basic", "island"])
Island.activated.append(
    ManaAbility("Island add U",
                Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
                lambda g, s: ManaAbility.AddColor(g, s, "U")))

###---shock lands
AsEnterShock = AsEnterEffect("ShockIntoPlay", Land.ShockIntoPlay)

TempleGarden = Land("TempleGarden", ["forest", "plains"])
TempleGarden.activated.append(
    ManaAbility("TempleGarden add W/G",
                Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
                lambda g, s: ManaAbility.AddDual(g, s, "W", "G")))
TempleGarden.trig_move.append(AsEnterShock)

BreedingPool = Land("BreedingPool", ["forest", "island"])
BreedingPool.activated.append(
    ManaAbility("BreedingPool add U/G",
                Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
                lambda g, s: ManaAbility.AddDual(g, s, "U", "G")))
BreedingPool.trig_move.append(AsEnterShock)

HallowedFountain = Land("HallowedFountain", ["plains", "island"])
HallowedFountain.activated.append(
    ManaAbility("HallowedFountain add W/U",
                Cost(None, Land.LandAvailable, ManaAbility.TapToPay),
                lambda g, s: ManaAbility.AddDual(g, s, "W", "U")))
HallowedFountain.trig_move.append(AsEnterShock)


###---fetch lands

def FetchLandType(gamestate, source, keywords):
    targets = []
    for card in gamestate.deck:
        if "land" in card.rules_text.keywords:
            # if it's the right type of land...
            if any([t in keywords for t in card.rules_text.keywords]):
                # and if we don't have it already...
                if not any([card.is_equiv_to(ob) for ob in targets]):
                    targets.append(card)
    if len(targets) == 0:  # fail to find. fetch still sacrificed
        newstate, [fetch] = gamestate.copy_and_track([source])
        newstate.LoseLife(1)
        newstate.MoveZone(fetch, ZONE.GRAVE)
        newstate.Shuffle()
        return newstate.ClearSuperStack()
    universes = []
    for landcard in targets:
        newstate, [newland, fetch] = gamestate.copy_and_track([landcard, source])
        newstate.LoseLife(1)
        newstate.MoveZone(fetch, ZONE.GRAVE)
        newstate.MoveZone(newland, ZONE.FIELD)
        newstate.Shuffle()
        universes += newstate.ClearSuperStack()
    return universes


WindsweptHeath = Land("WindsweptHeath", [])
WindsweptHeath.trig_move.append(
    AsEnterEffect("Fetch G/W",
                  lambda g, s: FetchLandType(g, s, ["forest", "plains"])))

FloodedStrand = Land("FloodedStrand", [])
FloodedStrand.trig_move.append(
    AsEnterEffect("Fetch G/W",
                  lambda g, s: FetchLandType(g, s, ["island", "plains"])))

MistyRainforest = Land("MistyRainforest", [])
MistyRainforest.trig_move.append(
    AsEnterEffect("Fetch G/W",
                  lambda g, s: FetchLandType(g, s, ["forest", "island"])))

# ##---------------------------------------------------------------------------##
# class Recruiter(RulesText.Creature):
#     def __init__(self):
#         super().__init__("Recruiter","1G",2,2,["human"])
#         self.frontface = True
#         def recruit(gamestate):
#             options = [c for c in gamestate.deck[:3] if isinstance(c,RulesText.Creature)]
#             if len(options)>0: #might wiff entirely
#                 card = AI.ChooseRecruit(gamestate,options)
#                 gamestate.deck.remove(card)
#                 gamestate.hand.append(card)
#                 if gamestate.verbose:
#                     print("    hit: %s" %card.name)
#                 gamestate.deck = gamestate.deck[2:]+gamestate.deck[:2] #put to bottom, ignores order
#             else:
#                 gamestate.deck = gamestate.deck[3:]+gamestate.deck[:3]     #put all 3 to bottom
#         self.abilitylist = [RulesText.Ability("recruit",self, "2G", recruit)]

# ##---------------------------------------------------------------------------##       
# class Shalai(RulesText.Creature):
#     def __init__(self):
#         super().__init__("Shalai", "3W", 3, 4, ["flying"])
#         def pump(gamestate):
#             for critter in gamestate.field:
#                 if not isinstance(critter,RulesText.Creature): #only pumps creatures
#                     continue 
#                 critter.power += 1
#                 critter.toughness += 1
#         self.abilitylist = [RulesText.Ability("pump",self, "4GG", pump)]


# ##---------------------------------------------------------------------------##
# class TrophyMage(RulesText.Creature):
#     def __init__(self):
#         super().__init__("Trophy Mage","2U",2,2,["human"])
#     def Trigger(self,card):
#         if card == self: #if IT is the thing which just entered the battlefield
#             tutortarget = AI.ChooseTrophyMageTarget(self.gamestate)
#             if tutortarget is not None: #might be no valid targets
#                 self.gamestate.deck.remove(tutortarget)
#                 self.gamestate.hand.append(tutortarget)
#             self.gamestate.Shuffle()
# ##---------------------------------------------------------------------------##
# class Staff(RulesText.Permanent):
#     def __init__(self):
#         super().__init__("Staff","3",["artifact"])
#     def Trigger(self,card):
#         #when it or a defender enters the field, check if we can combo-win
#         if card == self or "defender" in card.keywords:
#             defenders = []
#             scalers = []
#             for perm in self.gamestate.field:
#                 if "defender" in perm.keywords:
#                     defenders.append(perm)
#                 if isinstance(perm,Axebane) or isinstance(perm,Battlement):
#                     scalers.append(perm)
#             if len(defenders)<5:
#                 return #never mind, don't have 5 defenders
#             atleastthree = self.gamestate.CMCAvailable()>3
#             for wall in scalers:
#                 #if scaler can tap for 5, we win!
#                 if (not wall.unavailable) or (not wall.summon_sick and atleastthree):
#                     raise IOError("STAFF COMBO WINS THE GAME!")
# ##---------------------------------------------------------------------------##       
# class Company(RulesText.Spell):
#     def __init__(self):
#         super().__init__("Company", "3G", ["instant"])
#     def Effect(self):
#         options = [card for card in self.gamestate.deck[:6] if (isinstance(card,RulesText.Creature) and card.cost.cmc()<=3)]
#         if len(options)>0: #might wiff entirely   
#             chosen = AI.ChooseCompany(self.gamestate,options)
#             for card in chosen:
#                 self.gamestate.deck.remove(card)
#                 self.gamestate.field.append(card)
#             if self.gamestate.verbose:
#                 print("    hit:",[str(card) for card in chosen])
#             self.gamestate.deck = self.gamestate.deck[6-len(chosen):]+self.gamestate.deck[:6-len(chosen)] #put to bottom, ignores order
#             for card in chosen:
#                 self.gamestate.ResolveCastingTriggers(card)
#         else:
#             self.gamestate.deck = self.gamestate.deck[6:]+self.gamestate.deck[:6] #all 6 to bottom

# ##---------------------------------------------------------------------------##
# ##===========================================================================##
# ##---------------------------------------------------------------------------##

# ##---------------------------------------------------------------------------##
# class Westvale(RulesText.Land):
#     def maketoken(self,gamestate):
#         gamestate.TakeDamage(1)
#         gamestate.AddToField( RulesText.Creature("Cleric","",1,1,["token"]) )
#         self.abilitylist = []
#         self.tapped = True
#     def flip(self,gamestate):
#         sacrifices = AI.ChooseSacToOrmendahl(gamestate)
#         if len(sacrifices)<5: return #not enough fodder to sac!
#         if gamestate.verbose:
#             print("sacrificing",[c.name for c in sacrifices],"to Ormendahl")
#         for critter in sacrifices:
#             gamestate.field.remove(critter)
#         #legend rule
#         alreadythere = [c for c in gamestate.field if c.name == "Ormendahl"]
#         for ormendahl in alreadythere:
#             print("LEGEND RULE! SACRIFICING THE OLD ORMENDAHL")
#             gamestate.field.remove(ormendahl)
#         gamestate.field.remove(self)
#         #make the new Ormendahl
#         ormendahl = RulesText.Creature("Ormendahl","",9,7,["legendary","lifelink","flying"])
#         ormendahl.summon_sick = False #hasty
#         gamestate.AddToField( ormendahl )

#     def canpayforflip(self):
#         return len([c for c in self.gamestate.field if isinstance(c,RulesText.Creature)])>=5 and not self.tapped

#     def __init__(self):
#         super().__init__("Westvale Abbey",[])
#         self.abilitylist = [RulesText.Ability("makecleric",self, "5", self.maketoken),
#                             RulesText.Ability("ormendahl", self, "5", self.flip     )]
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [RulesText.ManaPool("C")]
#     def Activate(self):
#         """Deducts payment for the ability and then performs the ability"""
#         #overwriting to make sure we actually HAVE the creatures to sacrifice, 
#         #since I can't check that without a gamestate object and I don't have
#         #one during init or Untap
#         if not self.canpayforflip(self.gamestate):
#             #not actually able to use the ability right now! whoops. remove it from the ability list...
#             self.abilitylist = [ab for ab in self.abilitylist if ab.name != "ormendahl"]
#             print("removing ormendahl ability")
#         else:
#             super().Activate()
#     def Trigger(self,card):
#         #only add the Ormendahl ability when it's usable, so when have 5 creatures
#         if card == self or isinstance(card,RulesText.Creature): #if IT or a creature entered
#             #if enough creatures to sac, AND we don't already have Ormendahl-maker ability...
#             if self.canpayforflip(self.gamestate) and len(self.abilitylist)==1:
#                 self.abilitylist.append( RulesText.Ability("ormendahl" ,self, "5", self.flip) )
#                 print("adding ormendahl ability")
#     def Untap(self):
#         super().Untap()
#         self.abilitylist = [RulesText.Ability("makecleric",self, "5", self.maketoken),
#                             RulesText.Ability("ormendahl", self, "5", self.flip     )]
#     def MakeMana(self,color):
#         super().MakeMana(color)
#         if self.tapped:
#             self.abilitylist = []
# ##---------------------------------------------------------------------------##
# class Wildwoods(RulesText.Land):
#     def __init__(self):
#         super().__init__("Stirring Wildwoods",["manland"])
#         self.tapped = True
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [RulesText.ManaPool("W"),RulesText.ManaPool("G")]
# ##---------------------------------------------------------------------------##
# class LumberingFalls(RulesText.Land):
#     def __init__(self):
#         super().__init__("Lumbering Falls",["manland"])
#         self.tapped = True
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [RulesText.ManaPool("U"),RulesText.ManaPool("G")]
# ##---------------------------------------------------------------------------##


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
