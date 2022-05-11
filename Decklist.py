# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""

from CardType import Creature,Land#,Spell
from Abilities import ManaAbility,TriggeredByMove #,ActivatedAbility
from Costs import Cost

import ZONE


# from ManaHandler import ManaPool
# import AI #hopefully not circular dependency...









##---------------------------------------------------------------------------##



def RootsAfford(gamestate,source):
    return ("@used" not in source.counters) and (source.zone == ZONE.FIELD)
def RootsPay(gamestate,source):
    newstate,[newsource] = gamestate.CopyAndTrack([source])
    newsource.AddCounter("@used")  #"@" counters are cleared automatically at untap
    newsource.AddCounter("-0/-1")
    return [(newstate,newsource)]
# def RootsUpkeep(gamestate,source):
#     #remove "used" from the list of counters
#     source.counters = [c for c in source.counters if c!="@used"]
    
Roots = Creature("Roots",Cost("1G",None,None),["defender"],0,5)
Roots.activated.append(
                ManaAbility("Roots add G",
                            Cost(None,RootsAfford,RootsPay),
                            lambda g,s : ManaAbility.AddColor(g,s,"g") ))
# Roots.upkeep.append(RootsUpkeep)

##---------------------------------------------------------------------------##
      
Caryatid = Creature("Caryatid",Cost("1G",None,None),["defender","hexproof"],0,3)
Caryatid.activated.append(
                ManaAbility("Caryatid add Au",
                            Cost(None,
                                 ManaAbility.DorkAvailable,
                                 ManaAbility.TapToPay),
                            lambda g,s : ManaAbility.AddColor(g,s,"A") ))

##---------------------------------------------------------------------------##

def CaretakerAfford(gamestate,source):
    if (source.tapped or source.summonsick or source.zone != ZONE.FIELD):
        return False  #caretaker itself isn't available
    #also need another untapped creature to tap
    for c in gamestate.field:
        if isinstance(c.cardtype,Creature) and not c.tapped and not c is source:
            return True  #if it's another uptapped creature, we're good!
    return False  #couldn't find another untapped creature
def CaretakerPay(gamestate,source):
    #for each thing that could be tapped to pay, return a gamestate where
    #THAT target is the one which is tapped (in addition to the caretaker)
    universes = []
    for c in gamestate.field:
        if isinstance(c.cardtype,Creature) and not c.tapped and not c is source:
            #this is a safe target to tap!
            newstate,[newsource,target] = gamestate.CopyAndTrack([source,c])
            newsource.tapped = True
            target.tapped = True
            universes.append( (newstate,newsource) )
    return universes

Caretaker = Creature("Caretaker",Cost("G",None,None),["defender"],0,3)
Caretaker.activated.append(
                ManaAbility("Caretaker add Au",
                            Cost(None,CaretakerAfford,CaretakerPay),
                            lambda g,s : ManaAbility.AddColor(g,s,"A") ))

##---------------------------------------------------------------------------##

def BattlementAddColor(gamestate,source):
    num = sum(["defender" in c.cardtype.typelist for c in gamestate.field])
    newstate,[newsource] = gamestate.CopyAndTrack([source])
    newstate.pool.AddMana("G"*num)  #add mana
    return [newstate]

Battlement = Creature("Battlement",Cost("1G",None,None),["defender"],0,4)
Battlement.activated.append(
                ManaAbility("Battlement add G",
                            Cost(None,
                                 ManaAbility.DorkAvailable,
                                 ManaAbility.TapToPay),
                            BattlementAddColor ))

##---------------------------------------------------------------------------##

def AxebaneAddColor(gamestate,source):
    num = sum(["defender" in c.cardtype.typelist for c in gamestate.field])
    newstate,[newsource] = gamestate.CopyAndTrack([source])
    newstate.pool.AddMana("A"*num)  #add mana
    return [newstate]

Axebane = Creature("Axebane",Cost("2G",None,None),["defender"],0,3)
Axebane.activated.append(
                ManaAbility("Axebane add Au",
                            Cost(None,
                                 ManaAbility.DorkAvailable,
                                 ManaAbility.TapToPay),
                            AxebaneAddColor ))

##---------------------------------------------------------------------------##

def DrawACard(gamestate,source):
    newstate = gamestate.copy()
    effects = newstate.Draw()
    newstate.stack += effects
    return [newstate]

Blossoms = Creature("Blossoms",Cost("1G",None,None),["defender"],0,4)
Blossoms.trig_move.append(
                TriggeredByMove("Blossoms etb draw",
                                TriggeredByMove.ETB_self,
                                DrawACard) )

##---------------------------------------------------------------------------##

Omens = Creature("Omens",Cost("1W",None,None),["defender"],0,4)
Omens.trig_move.append(
                TriggeredByMove("Omens etb draw",
                                TriggeredByMove.ETB_self,
                                DrawACard) )

##---------------------------------------------------------------------------##

def ETB_defender(gamestate,source,trigger,origin):
    return (    source.zone == ZONE.FIELD
            and trigger.zone == ZONE.FIELD
            and "defender" in trigger.cardtype.typelist)

Arcades = Creature("Arcades",Cost("1WUG",None,None),["flying","vigilance"],3,5)
Arcades.trig_move.append(
                TriggeredByMove("Arcades draw trigger",
                                ETB_defender,
                                DrawACard) )










##---------------------------------------------------------------------------##




# next: CoCo






















# ##---------------------------------------------------------------------------##
# class Blossoms(CardType.Creature):
#     def __init__(self):
#         super().__init__("Blossoms","1G",0,4,["defender"])
#     def Trigger(self,card):
#         if card == self: #if IT is the thing which just entered the battlefield
#             self.gamestate.Draw()
# ##---------------------------------------------------------------------------##
# ##===========================================================================##
# ##---------------------------------------------------------------------------##
# class Arcades(CardType.Creature):
#     def __init__(self):
#         super().__init__("Arcades","1GWU",3,5,["legendary","vigilance","flying","dragon"])
#     def Trigger(self,card):
#         if "defender" in card.typelist:
#             self.gamestate.Draw()
#         if card.name == self.name and card != self:
#             if self.gamestate.verbose:
#                 print("LEGEND RULE! SACRIFICING THE NEW ARCADES")
#             self.gamestate.field.remove(card)












##---------------------------------------------------------------------------##

###---basic lands

Forest = Land("Forest",["basic","forest"])
Forest.activated.append(
                ManaAbility("Forest add G",
                            Cost(None,Land.LandAvailable,ManaAbility.TapToPay),
                            lambda g,s : ManaAbility.AddColor(g,s,"G") ))


Plains = Land("Plains",["basic","plains"])
Plains.activated.append(
                ManaAbility("Plains add W",
                            Cost(None,Land.LandAvailable,ManaAbility.TapToPay),
                            lambda g,s : ManaAbility.AddColor(g,s,"W") ))


Island = Land("Island",["basic","island"])
Island.activated.append(
                ManaAbility("Island add U",
                            Cost(None,Land.LandAvailable,ManaAbility.TapToPay),
                            lambda g,s : ManaAbility.AddColor(g,s,"U") ))


###---shock lands

TempleGarden = Land("TempleGarden",["forest","plains"])
TempleGarden.activated.append(
                ManaAbility("TempleGarden add W/G",
                            Cost(None,Land.LandAvailable,ManaAbility.TapToPay),
                            lambda g,s : ManaAbility.AddDual(g,s,"W","G") ))
TempleGarden.as_enter = Land.ShockIntoPlay


BreedingPool = Land("BreedingPool",["forest","island"])
BreedingPool.activated.append(
                ManaAbility("BreedingPool add U/G",
                            Cost(None,Land.LandAvailable,ManaAbility.TapToPay),
                            lambda g,s : ManaAbility.AddDual(g,s,"U","G") ))
BreedingPool.as_enter = Land.ShockIntoPlay


HallowedFountain = Land("HallowedFountain",["plains","island"])
HallowedFountain.activated.append(
                ManaAbility("HallowedFountain add W/U",
                             Cost(None,Land.LandAvailable,ManaAbility.TapToPay),
                             lambda g,s : ManaAbility.AddDual(g,s,"W","U") ))
HallowedFountain.as_enter = Land.ShockIntoPlay






        
# ##---------------------------------------------------------------------------##
# class Recruiter(CardType.Creature):
#     def __init__(self):
#         super().__init__("Recruiter","1G",2,2,["human"])
#         self.frontface = True
#         def recruit(gamestate):
#             options = [c for c in gamestate.deck[:3] if isinstance(c,CardType.Creature)]
#             if len(options)>0: #might wiff entirely
#                 card = AI.ChooseRecruit(gamestate,options)
#                 gamestate.deck.remove(card)
#                 gamestate.hand.append(card)
#                 if gamestate.verbose:
#                     print("    hit: %s" %card.name)
#                 gamestate.deck = gamestate.deck[2:]+gamestate.deck[:2] #put to bottom, ignores order
#             else:
#                 gamestate.deck = gamestate.deck[3:]+gamestate.deck[:3]     #put all 3 to bottom
#         self.abilitylist = [CardType.Ability("recruit",self, "2G", recruit)]
                
# ##---------------------------------------------------------------------------##       
# class Shalai(CardType.Creature):
#     def __init__(self):
#         super().__init__("Shalai", "3W", 3, 4, ["flying"])
#         def pump(gamestate):
#             for critter in gamestate.field:
#                 if not isinstance(critter,CardType.Creature): #only pumps creatures
#                     continue 
#                 critter.power += 1
#                 critter.toughness += 1
#         self.abilitylist = [CardType.Ability("pump",self, "4GG", pump)]


# ##---------------------------------------------------------------------------##
# class TrophyMage(CardType.Creature):
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
# class Staff(CardType.Permanent):
#     def __init__(self):
#         super().__init__("Staff","3",["artifact"])
#     def Trigger(self,card):
#         #when it or a defender enters the field, check if we can combo-win
#         if card == self or "defender" in card.typelist:
#             defenders = []
#             scalers = []
#             for perm in self.gamestate.field:
#                 if "defender" in perm.typelist:
#                     defenders.append(perm)
#                 if isinstance(perm,Axebane) or isinstance(perm,Battlement):
#                     scalers.append(perm)
#             if len(defenders)<5:
#                 return #never mind, don't have 5 defenders
#             atleastthree = self.gamestate.CMCAvailable()>3
#             for wall in scalers:
#                 #if scaler can tap for 5, we win!
#                 if (not wall.unavailable) or (not wall.summonsick and atleastthree):
#                     raise IOError("STAFF COMBO WINS THE GAME!")
# ##---------------------------------------------------------------------------##       
# class Company(CardType.Spell):
#     def __init__(self):
#         super().__init__("Company", "3G", ["instant"])
#     def Effect(self):
#         options = [card for card in self.gamestate.deck[:6] if (isinstance(card,CardType.Creature) and card.cost.CMC()<=3)]
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

# class WindsweptHeath(CardType.Land):
#     def __init__(self):
#         super().__init__("Windswept Heath",["fetch"])
#     @property
#     def tapsfor(self):
#         return []
#     def Trigger(self,card):
#         if card == self: #if IT is the thing which just entered the battlefield
#             self.gamestate.field.remove(self) #sacrifice itself    
#             self.gamestate.TakeDamage(1)
#             tutortarget = AI.ChooseFetchTarget(self.gamestate,[Forest,Plains])
#             if tutortarget is not None: #might be no valid targets
#                 self.gamestate.deck.remove(tutortarget)
#                 self.gamestate.field.append(tutortarget)
#                 if self.gamestate.verbose:
#                     print("    fetch",tutortarget.name)
#             self.gamestate.Shuffle()
#             if tutortarget is not None:
#                 self.gamestate.ResolveCastingTriggers(tutortarget)
#     @property
#     def unavailable(self): #fetches are never available to tap for mana
#         return True
# ##---------------------------------------------------------------------------##
# class Westvale(CardType.Land):
#     def maketoken(self,gamestate):
#         gamestate.TakeDamage(1)
#         gamestate.AddToField( CardType.Creature("Cleric","",1,1,["token"]) )
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
#         ormendahl = CardType.Creature("Ormendahl","",9,7,["legendary","lifelink","flying"])
#         ormendahl.summonsick = False #hasty
#         gamestate.AddToField( ormendahl )
    
#     def canpayforflip(self):
#         return len([c for c in self.gamestate.field if isinstance(c,CardType.Creature)])>=5 and not self.tapped
    
#     def __init__(self):
#         super().__init__("Westvale Abbey",[])
#         self.abilitylist = [CardType.Ability("makecleric",self, "5", self.maketoken),
#                             CardType.Ability("ormendahl", self, "5", self.flip     )]
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool("C")]
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
#         if card == self or isinstance(card,CardType.Creature): #if IT or a creature entered
#             #if enough creatures to sac, AND we don't already have Ormendahl-maker ability...
#             if self.canpayforflip(self.gamestate) and len(self.abilitylist)==1:
#                 self.abilitylist.append( CardType.Ability("ormendahl" ,self, "5", self.flip) )
#                 print("adding ormendahl ability")
#     def Untap(self):
#         super().Untap()
#         self.abilitylist = [CardType.Ability("makecleric",self, "5", self.maketoken),
#                             CardType.Ability("ormendahl", self, "5", self.flip     )]
#     def MakeMana(self,color):
#         super().MakeMana(color)
#         if self.tapped:
#             self.abilitylist = []
# ##---------------------------------------------------------------------------##
# class Wildwoods(CardType.Land):
#     def __init__(self):
#         super().__init__("Stirring Wildwoods",["manland"])
#         self.tapped = True
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool("W"),CardType.ManaPool("G")]
# ##---------------------------------------------------------------------------##
# class LumberingFalls(CardType.Land):
#     def __init__(self):
#         super().__init__("Lumbering Falls",["manland"])
#         self.tapped = True
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool("U"),CardType.ManaPool("G")]
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