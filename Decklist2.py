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

#for now I'm importing these all separately to keep track of which I need and
#which are extraneous
from Actions import Ability2,Cost2
from Actions import PayMana,AddMana,TapSymbol,AddCounterToSelf,ActivateOncePerTurn
from Actions import TapAny
from Actions import ChooseOneOther
from Actions import MatchUntapped,MatchType



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
                         TapAny(ChooseOneOther(
                                     [MatchUntapped(),MatchType(Creature)],
                                     ZONE.FIELD) )
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
                 
                 
                 
                 BattlementAddColor))


##---------------------------------------------------------------------------##

def AxebaneAddColor(gamestate, source):
    num = sum(["defender" in c.rules_text.keywords for c in gamestate.field])
    newstate, [newsource] = gamestate.copy_and_track([source])
    newstate.pool.AddMana("A" * num)  # add mana
    return [newstate]


Axebane = Creature("Axebane", Cost("2G", None, None), ["defender"], 0, 3)
Axebane.activated.append(
    ManaAbility("Axebane add Au",
                Cost(None,
                     ManaAbility.DorkAvailable,
                     ManaAbility.TapToPay),
                AxebaneAddColor))


##---------------------------------------------------------------------------##

def DrawACard(gamestate, source):
    newstate = gamestate.copy()
    newstate.Draw()  # adds to super_stack if necessary
    return [newstate]


Blossoms = Creature("Blossoms", Cost("1G", None, None), ["defender"], 0, 4)
Blossoms.trig_move.append(
    TriggeredByMove("Blossoms etb draw",
                    TriggeredByMove.ETB_self,
                    DrawACard))

##---------------------------------------------------------------------------##

Omens = Creature("Omens", Cost("1W", None, None), ["defender"], 0, 4)
Omens.trig_move.append(
    TriggeredByMove("Omens etb draw",
                    TriggeredByMove.ETB_self,
                    DrawACard))


##---------------------------------------------------------------------------##

def ETB_defender(gamestate, source, trigger, origin):
    return (source.zone == ZONE.FIELD
            and trigger.zone == ZONE.FIELD
            and "defender" in trigger.rules_text.keywords)


Arcades = Creature("Arcades", Cost("1WUG", None, None), ["flying", "vigilance"], 3, 5)
Arcades.trig_move.append(
    TriggeredByMove("Arcades draw trigger",
                    ETB_defender,
                    DrawACard))


##---------------------------------------------------------------------------##

def ResolveCompany(gamestate, source):
    """NOTE: puts bottom in same order as they were on top of deck.
    Note: in automated mode, there's no point in looking at suboptimal choices.
    Always take as many creatures as possible, even if choosing fewer is
    technically legal."""
    # #get all valid Collected Company targets from top 6 cards of deck
    # targets = [ii for ii,card in enumerate(gamestate.deck[:6])
    #                              if card.HasType(Creature) and card.cmc()<=3]
    # #get all pairs of targets to put into play
    # if len(targets) == 0:
    #     pairs = [()]
    # elif len(targets) == 1:
    #     pairs = [ (targets[0],) ]
    # else:
    #     pairs = []
    #     for ii in range(len(targets)):
    #         for jj in range(ii+1,len(targets)):
    #             obj0 = gamestate.deck[ targets[ii] ]
    #             obj1 = gamestate.deck[ targets[jj] ]
    #             alreadygotone = False
    #             for ind0,ind1 in pairs:
    #                 p0 = gamestate.deck[ind0]
    #                 p1 = gamestate.deck[ind1]
    #                 if (       (obj0.EquivTo(p0) and obj1.EquivTo(p1)) 
    #                         or (obj0.EquivTo(p1) and obj1.EquivTo(p0))):
    #                     alreadygotone = True
    #                     continue
    #             if not alreadygotone:
    #                 pairs.append((ii,jj))
    # #make a copy of the gamestate where we choose each good pair
    # statelist = []
    # for tup in goodpairs:
    #     state = gamestate.copy()
    #     notchosen = []
    #     for index in range( min(6,len(state.deck)) ):
    #         #always pop 0. index still says where this card USED to be b/4 pop
    #         if index in tup:
    #             card = state.deck[0]
    #             state.MoveZone(card,ZONE.FIELD) #move CHOSEN to play
    #         else:
    #             notchosen.append( state.deck.pop(0) )
    #     state.deck = state.deck + notchosen #all 6 gone from top, now.
    #     statelist.append(state)
    # return statelist

    # targets = [card for card in gamestate.deck[:6]
    #                              if card.HasType(Creature) and card.cmc()<=3]
    # pairs = Choices.ChooseExactlyN(targets,2,sourcename="Collected Company")
    # #check for duplicates. NOT guaranteed to all be length 2, but YES
    # #guaranteed to all be the same length
    # goodpairs = []
    # def duplicatepair(a,b):
    #     if len(a)!=len(b):  #in case the "pair" is actually 1 or 0 cards chosen
    #         return False
    #     if len(a)==0:
    #         return True #there is only one empty list
    #     elif len(a)==1:
    #         return a[0].EquivTo(b[0])
    #     elif len(a)==2:
    #         return (   (a[0].EquivTo(b[0]) and a[1].EquivTo(b[1]))
    #                 or (a[0].EquivTo(b[1]) and a[1].EquivTo(b[0])) )
    # while len(pairs)>0:
    #     p0 = pairs.pop()
    #     if not any( [duplicatepair(p0,p1) for p1 in goodpairs] ):
    #         goodpairs.append(p0) #make it mutable for later
    # #make a copy of the gamestate where we choose each good pair
    # statelist = []
    # for tup in goodpairs:
    #     state = gamestate.copy()
    #     #look six cards deep, move all chosen cards from deck to field
    #     digdeep = 6
    #     for chosen in tup:
    #         card = [c for c in state.deck[:digdeep] if c.EquivTo(chosen)][0]
    #         state.MoveZone(card,ZONE.FIELD)     #move chosen card to field
    #         digdeep -= 1    #look slightly less deep, deck is smaller now
    #     #any remaining cards need to be put to the bottom (end of list)
    #     state.deck = state.deck[digdeep:] + state.deck[:digdeep]
    #     statelist.append(state)
    # return statelist

    # get all valid Collected Company targets from top 6 cards of deck
    targets = [(ii, card) for ii, card in enumerate(gamestate.deck[:6])
               if card.has_type(Creature) and card.cmc() <= 3]
    # list choices as pairs of targets. Each target is (Cardboard, deck index)
    # chosen = Choices.ChooseExactlyN(targets,2,sourcename="Collected Company")
    chosen = Choices.ChooseNOrFewer(targets, 2, sourcename="Collected Company")
    # only take the options which put the most creatures into play
    maxhits = max([len(option) for option in chosen])
    chosen = [option for option in chosen if len(option) == maxhits]
    # check for duplicate choices
    checked = []

    def equivchoices(a, b):  # check if two choices are equivalent
        if len(a) != len(b):  # in case the "pair" is actually 1 or 0 cards chosen
            return False
        if len(a) == 0:
            return True  # there is only one empty list
        elif len(a) == 1:
            cardA = a[-1]
            cardB = b[-1]
            return cardA.is_equiv_to(cardB)
        elif len(a) == 2:
            cardA0, cardA1 = [t[-1] for t in a]
            cardB0, cardB1 = [t[-1] for t in b]
            return ((cardA0.is_equiv_to(cardB0) and cardA1.is_equiv_to(cardB1))
                    or (cardA0.is_equiv_to(cardB1) and cardA1.is_equiv_to(cardB0)))

    while len(chosen) > 0:
        p0 = chosen.pop()
        if not any([equivchoices(p0, p1) for p1 in checked]):
            checked.append(p0)  # make it mutable for later
    # for each choice, copy the gamestate and we move chosen cards to field
    statelist = []
    for chosen_tuple in checked:
        state = gamestate.copy()
        notchosen = []
        for index in range(min(6, len(state.deck))):
            # always pop 0. index still says where this card USED to be b/4 pop
            if any([index == ii for ii, card in chosen_tuple]):
                card = state.deck[0]
                state.MoveZone(card, ZONE.FIELD)  # move top card into play
            else:
                notchosen.append(state.deck.pop(0))  # pop top card
        state.deck = state.deck + notchosen  # all 6 gone from top, now.
        statelist.append(state)
    return statelist


Company = Spell("Company", Cost("3G", None, None), ["instant"], ResolveCompany)

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
