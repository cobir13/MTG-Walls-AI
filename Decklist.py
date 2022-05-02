# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""

from CardType import Creature,Spell
from Abilities import ActivatedAbility
from Costs import Cost

import ZONE


# from ManaHandler import ManaPool
# import AI #hopefully not circular dependency...




##---------------------------------------------------------------------------##

Roots = Creature("Roots",Cost("1G",None,None),["defender"],0,5)

def RootsAfford(gamestate,source):
    return ("used" not in source.counters) and (source.zone == ZONE.FIELD)
def RootsPay(gamestate,source):
    newstate,[newsource] = gamestate.CopyAndTrack([source])
    newsource.counters.append("used")
    newsource.counters.append("-0/-1")
    return [(newstate,newsource)]
def RootsExecute(gamestate,source):
    newstate,[newsource] = gamestate.CopyAndTrack([source])
    newstate.pool.AddMana("G")
    return [(newstate,newsource)]
Roots.activated.append( ActivatedAbility("Roots add G",
                                               Cost(None,RootsAfford,RootsPay),
                                               RootsExecute) )
def RootsUpkeep(gamestate,source):
    #remove "used" from the list of counters
    source.counters = [c for c in source.counters if c!="used"]
Roots.upkeep.append(RootsUpkeep)

##---------------------------------------------------------------------------##
      
Caryatid = Creature("Caryatid",Cost("1G",None,None),["defender","hexproof"],0,3)

def CaryatidAfford(gamestate,source):
    return (not source.tapped and not source.summonsick and 
            source.zone == ZONE.FIELD)
def CaryatidPay(gamestate,source):
    newstate,[newsource] = gamestate.CopyAndTrack([source])
    newsource.tapped = True
    return [(newstate,newsource)]
def CaryatidExecute(gamestate,source):
    newstate,[newsource] = gamestate.CopyAndTrack([source])
    newstate.pool.AddMana("A")  #add gold mana
    return [(newstate,newsource)]
Caryatid.activated.append( ActivatedAbility("Caryatid add Au",
                                            Cost(None,CaryatidAfford,CaryatidPay),
                                            CaryatidExecute) )

      
##---------------------------------------------------------------------------##
# class Caryatid(CardType.Creature,CardType.ManaSource):
#     def __init__(self):
#         super().__init__("Caryatid","1G",0,3,["defender","plant"])
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool(c) for c in ["W","U","B","R","G"]]
#     @property
#     def unavailable(self):
#         return self.tapped or self.summonsick
#     def MakeMana(self,color):
#         if super().MakeMana(color):  #added mana, so tap or the like
#             self.tapped = True
    




















# ##---------------------------------------------------------------------------##
# class Caretaker(CardType.Creature,CardType.ManaSource):
#     def __init__(self):
#         super().__init__("Caretaker","G" ,0,3,["defender"])
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool(c) for c in ["W","U","B","R","G"]]
#     @property
#     def unavailable(self):
#         if self.tapped or self.summonsick:
#             return True #truly not available
#         elif self.GetTargetToTap() is None:
#             return True #can't tap anything else for mana, so not available
#         else:
#             return False #available to tap for mana!
#     def GetTargetToTap(self):
#         if self.tapped or self.summonsick: return None #no target to tap because SELF can't tap 
#         safetotap = []
#         caretakers = []
#         for perm in self.gamestate.field:
#             if isinstance(perm,CardType.Creature) and not perm.tapped:
#                 #can't make mana right now (or ever), so safe to tap
#                 if perm.summonsick or not isinstance(perm,CardType.ManaSource):
#                     safetotap.append(perm)
#                 if isinstance(perm,Caretaker) and not perm.summonsick:
#                     caretakers.append(perm)
#         i = caretakers.index(self) #which number usable caretaker are you?
#         if i<len(safetotap):
#             return safetotap[i]
#         elif (i-len(safetotap)) % 2 == 1:
#             return caretakers[i-1]
#         else:
#             return None #you're an even leftover caretaker. sorry, no mana for you
#     def MakeMana(self,color):
#         target = self.GetTargetToTap()
#         assert(target is not None)
#         if super().MakeMana(color):  #added mana, so tap or the like
#             target.tapped = True
#             self.tapped = True
        
# ##---------------------------------------------------------------------------##
# class Caryatid(CardType.Creature,CardType.ManaSource):
#     def __init__(self):
#         super().__init__("Caryatid","1G",0,3,["defender","plant"])
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool(c) for c in ["W","U","B","R","G"]]
#     @property
#     def unavailable(self):
#         return self.tapped or self.summonsick
#     def MakeMana(self,color):
#         if super().MakeMana(color):  #added mana, so tap or the like
#             self.tapped = True
# ##---------------------------------------------------------------------------##
# class Roots(CardType.Creature,CardType.ManaSource):
#     def __init__(self):
#         super().__init__("Roots","1G",0,5,["defender"])
#         self.unused = True
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool("G")]
#     @property
#     def unavailable(self):
#         return not self.unused
#     def MakeMana(self,color):
#         if super().MakeMana(color):  #added mana, so tap or the like
#             self.unused = False
#             self.toughness -= 1
#             if self.toughness == 0:
#                 self.gamestate.field.remove(self)
#     def Upkeep(self):
#         super().Upkeep()
#         self.unused = True
# ##---------------------------------------------------------------------------##
# class Battlement(CardType.Creature,CardType.ManaSource):
#     def __init__(self):
#         super().__init__("Battlement","1G",0,4,["defender"])
#     @property
#     def tapsfor(self):
#         if self.unavailable():
#             return []
#         numwalls = len([p for p in self.gamestate.field if "defender" in p.typelist])
#         return [ CardType.ManaPool("G"*numwalls)]
#     @property
#     def unavailable(self):
#         return self.tapped or self.summonsick
#     def MakeMana(self,color):
#         if super().MakeMana(color):  #added mana, so tap or the like
#             self.tapped = True
# ##---------------------------------------------------------------------------##
# #####-NOTE: AXEBANE COLORS AREN'T QUITE CORRECT---#--#-#---__###__#_#-#---
# class Axebane(CardType.Creature,CardType.ManaSource):
#     def __init__(self):
#         super().__init__("Axebane","2G",0,3,["defender","human"])
#     @property
#     def tapsfor(self):
#         if self.unavailable:
#             return []
#         numwalls = len([perm for perm in self.gamestate.field if "defender" in perm.typelist])
#         if numwalls==0:
#             return []
#         #if reached here, will tap for AT LEAST 1 mana
#         canmake = [CardType.ManaPool(c) for c in ["W","U","B","R","G"]]
#         for k in range(numwalls-1):
#             newoptions = []
#             for oldpool in canmake:
#                 for color in ["W","U","B","R","G"]:
#                     newpool = CardType.ManaPool(str(oldpool)+color)
#                     if not (newpool in newoptions):
#                         newoptions.append(newpool)
#             canmake = newoptions
#         return canmake
#     @property
#     def unavailable(self):
#         return self.tapped or self.summonsick
#     def MakeMana(self,color):
#         if super().MakeMana(color):  #added mana, so tap or the like
#             self.tapped = True
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
# class Forest(CardType.Land):
#     def __init__(self):
#         super().__init__("Forest",["basic"])
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool("G")]
# ##---------------------------------------------------------------------------##
# class Plains(CardType.Land):
#     def __init__(self):
#         super().__init__("Plains",["basic"])
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool("W")]
# ##---------------------------------------------------------------------------##
# class Island(CardType.Land):
#     def __init__(self):
#         super().__init__("Island",["basic"])
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool("U")]
# ##---------------------------------------------------------------------------##
# class TempleGarden(Forest,Plains):
#     def __init__(self):
#         CardType.Land.__init__(self, "Temple Garden", ["shock"])
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool("W"),CardType.ManaPool("G")]
#     def Trigger(self,card):
#         if card == self:
#             self.gamestate.TakeDamage(2)
# ##---------------------------------------------------------------------------##
# class BreedingPool(Forest,Island):
#     def __init__(self):
#         CardType.Land.__init__(self, "Breeding Pool", ["shock"])
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool("U"),CardType.ManaPool("G")]
#     def Trigger(self,card):
#         if card == self:
#             self.gamestate.TakeDamage(2)
# ##---------------------------------------------------------------------------##
# class HallowedFountain(Plains,Island):
#     def __init__(self):
#         CardType.Land.__init__(self, "Hallowed Fountain", ["shock"])
#     @property
#     def tapsfor(self):
#         return [] if self.unavailable else [CardType.ManaPool("W"),CardType.ManaPool("U")]
#     def Trigger(self,card):
#         if card == self:
#             self.gamestate.TakeDamage(2)
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