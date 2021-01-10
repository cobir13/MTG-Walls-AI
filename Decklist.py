# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""

import CardType
import AI #hopefully not circular dependency...


##---------------------------------------------------------------------------##
class Caretaker(CardType.Creature,CardType.ManaSource):
    def __init__(self):
        super().__init__("Caretaker","G" ,0,3,["defender"])
        self.tapsfor = ["W","U","B","R","G"]
    @property
    def unavailable(self):
        return self.tapped or self.summonsick
    def CanMakeMana(self,gamestate):
        """Caretakers need the rest of the gamestate to know if they are truly available..."""
        if self.unavailable: return False#do nothing 
        safetotap = []
        caretakers = []
        for perm in gamestate.field:
            if isinstance(perm,CardType.Creature) and not perm.tapped:
                #can't make mana right now (or ever), so safe to tap
                if perm.summonsick or not isinstance(perm,CardType.ManaSource):
                    safetotap.append(perm)
                if isinstance(perm,Caretaker) and not perm.summonsick:
                    caretakers.append(perm)
        i = caretakers.index(self) #which number usable caretaker are you?
        if i<len(safetotap):
            return True #congrats! you have a matching tappable creature
        elif (i-len(safetotap)) % 2 == 1:
            return True  #you're an odd caretaker, so you get to tap an even caretaker
        else:
            return False #you're an even leftover caretaker. sorry, no mana generation for you
    def MakeMana(self,gamestate,color):
        """mutates the gamestate!"""
        if self.unavailable or color not in self.tapsfor: return #do nothing 
        safetotap = []
        caretakers = []
        for perm in gamestate.field:
            if isinstance(perm,CardType.Creature) and not perm.tapped:
                #can't make mana right now (or ever), so safe to tap
                if perm.summonsick or not isinstance(perm,CardType.ManaSource):
                    safetotap.append(perm)
                if isinstance(perm,Caretaker) and not perm.summonsick:
                    caretakers.append(perm)
        i = caretakers.index(self) #which number usable caretaker are you?
        if i<len(safetotap):
            safetotap[i].tapped = True #congrats! you have a matching tappable creature
            gamestate.pool.AddMana(color)
            self.tapped = True
        elif (i-len(safetotap)) % 2 == 1:
            caretakers[i-1].tapped = True  #you're an odd caretaker, so you get to tap an even caretaker
            gamestate.pool.AddMana(color)
            self.tapped = True
        else:
            return #you're an even leftover caretaker. sorry, no mana for you
##---------------------------------------------------------------------------##
class Caryatid(CardType.Creature,CardType.ManaSource):
    def __init__(self):
        super().__init__("Caryatid","1G",0,3,["defender","plant"])
        self.tapsfor = ["W","U","B","R","G"]
    @property
    def unavailable(self):
        return self.tapped or self.summonsick
    def MakeMana(self,gamestate,color):
        """mutates the gamestate!"""
        if self.unavailable or color not in self.tapsfor: return #do nothing 
        gamestate.pool.AddMana(color)
        self.tapped = True
##---------------------------------------------------------------------------##
class Roots(CardType.Creature,CardType.ManaSource):
    def __init__(self):
        super().__init__("Roots","1G",0,5,["defender"])
        self.unused = True
        self.tapsfor = ["G"]
    @property
    def unavailable(self):
        return not self.unused
    def MakeMana(self,gamestate,color):
        """mutates the gamestate!"""
        if self.unavailable or color not in self.tapsfor: return #already made mana this turn, can't do it again
        gamestate.pool.AddMana("G")
        self.unused = False
        self.toughness -= 1
        if self.toughness == 0:
            gamestate.field.remove(self)
    def Upkeep(self):
        super().Upkeep()
        self.unused = True
##---------------------------------------------------------------------------##
class Battlement(CardType.Creature,CardType.ManaSource):
    def __init__(self):
        super().__init__("Battlement","1G",0,4,["defender"])
        self.tapsfor = ["G"]
    @property
    def unavailable(self):
        return self.tapped or self.summonsick
    def MakeMana(self,gamestate,color):
        """mutates the gamestate!"""
        if self.unavailable or color not in self.tapsfor: return #do nothing 
        gamestate.pool.AddMana( "G"*len([perm for perm in gamestate.field if "defender" in perm.typelist]) )
        self.tapped = True
##---------------------------------------------------------------------------##
#####-NOTE: AXEBANE COLORS AREN'T QUITE CORRECT---#--#-#---__###__#_#-#---
class Axebane(CardType.Creature,CardType.ManaSource):
    def __init__(self):
        super().__init__("Axebane","2G",0,3,["defender","human"])
        self.tapsfor = ["W","U","B","R","G"]
    @property
    def unavailable(self):
        return self.tapped or self.summonsick
    def MakeMana(self,gamestate,color):
        """mutates the gamestate!"""
        if self.unavailable or color not in self.tapsfor: return #do nothing 
        gamestate.pool.AddMana( color*len([perm for perm in gamestate.field if "defender" in perm.typelist]) )
        self.tapped = True
##---------------------------------------------------------------------------##
class Blossoms(CardType.Creature):
    def __init__(self):
        super().__init__("Blossoms","1G",0,4,["defender"])
    def Trigger(self,gamestate,card):
        if card == self: #if IT is the thing which just entered the battlefield
            gamestate.Draw()
##---------------------------------------------------------------------------##
##===========================================================================##
##---------------------------------------------------------------------------##
class Arcades(CardType.Creature):
    def __init__(self):
        super().__init__("Arcades","1GWU",3,5,["legendary","vigilance","flying","dragon"])
    def Trigger(self,gamestate,card):
        if "defender" in card.typelist:
            gamestate.Draw()
        if card.name == self.name and card != self:
            if gamestate.verbose:
                print("LEGEND RULE! SACRIFICING THE NEW ARCADES")
            gamestate.field.remove(card)
        
##---------------------------------------------------------------------------##
class Recruiter(CardType.Creature):
    def __init__(self):
        super().__init__("Recruiter","1G",2,2,["human"])
        self.frontface = True
        def recruit(gamestate):
            options = [c for c in gamestate.deck[:3] if isinstance(c,CardType.Creature)]
            if len(options)>0: #might wiff entirely
                card = AI.ChooseRecruit(gamestate,options)
                gamestate.deck.remove(card)
                gamestate.hand.append(card)
                if gamestate.verbose:
                    print("    hit: %s" %card.name)
                gamestate.deck = gamestate.deck[2:]+gamestate.deck[:2] #put to bottom, ignores order
            else:
                gamestate.deck = gamestate.deck[3:]+gamestate.deck[:3]     #put all 3 to bottom
        self.abilitylist = [CardType.Ability("recruit",self, "2G", recruit)]
                
##---------------------------------------------------------------------------##       
class Shalai(CardType.Creature):
    def __init__(self):
        super().__init__("Shalai", "3W", 3, 4, ["flying"])
        def pump(gamestate):
            for critter in gamestate.field:
                if not isinstance(critter,CardType.Creature): #only pumps creatures
                    continue 
                critter.power += 1
                critter.toughness += 1
        self.abilitylist = [CardType.Ability("pump",self, "4GG", pump)]


##---------------------------------------------------------------------------##
class TrophyMage(CardType.Creature):
    def __init__(self):
        super().__init__("Trophy Mage","2U",2,2,["human"])
    def Trigger(self,gamestate,card):
        if card == self: #if IT is the thing which just entered the battlefield
            tutortarget = AI.ChooseTrophyMageTarget(gamestate)
            if tutortarget is not None: #might be no valid targets
                gamestate.deck.remove(tutortarget)
                gamestate.hand.append(tutortarget)
            gamestate.Shuffle()
##---------------------------------------------------------------------------##
class Staff(CardType.Permanent):
    def __init__(self):
        super().__init__("Staff","3",["artifact"])
    def Trigger(self,gamestate,card):
        #when it or a defender enters the field, check if we can combo-win
        if card == self or "defender" in card.typelist:
            defenders = []
            scalers = []
            for perm in gamestate.field:
                if "defender" in perm.typelist:
                    defenders.append(perm)
                if isinstance(perm,Axebane) or isinstance(perm,Battlement):
                    scalers.append(perm)
            if len(defenders)<5:
                return #never mind, don't have 5 defenders
            atleastthree = gamestate.CMCAvailable()>3
            for wall in scalers:
                #if scaler can tap for 5, we win!
                if (not wall.unavailable) or (not wall.summonsick and atleastthree):
                    raise IOError("STAFF COMBO WINS THE GAME!")
##---------------------------------------------------------------------------##       
class Company(CardType.Spell):
    def __init__(self):
        super().__init__("Company", "3G", ["instant"])
    def Effect(self,gamestate):
        options = [card for card in gamestate.deck[:6] if (isinstance(card,CardType.Creature) and card.cost.CMC()<=3)]
        if len(options)>0: #might wiff entirely   
            chosen = AI.ChooseCompany(gamestate,options)
            for card in chosen:
                gamestate.deck.remove(card)
                gamestate.field.append(card)
            if gamestate.verbose:
                print("    hit:",[str(card) for card in chosen])
            gamestate.deck = gamestate.deck[6-len(chosen):]+gamestate.deck[:6-len(chosen)] #put to bottom, ignores order
            for card in chosen:
                gamestate.ResolveCastingTriggers(card)
        else:
            gamestate.deck = gamestate.deck[6:]+gamestate.deck[:6] #all 6 to bottom
                
##---------------------------------------------------------------------------##
##===========================================================================##
##---------------------------------------------------------------------------##
class Forest(CardType.Land):
    def __init__(self):
        super().__init__("Forest",["basic"])
        self.tapsfor = ["G"]
##---------------------------------------------------------------------------##
class Plains(CardType.Land):
    def __init__(self):
        super().__init__("Plains",["basic"])
        self.tapsfor = ["W"]
##---------------------------------------------------------------------------##
class Island(CardType.Land):
    def __init__(self):
        super().__init__("Island",["basic"])
        self.tapsfor = ["U"]
##---------------------------------------------------------------------------##
class TempleGarden(Forest,Plains):
    def __init__(self):
        CardType.Land.__init__(self, "Temple Garden", ["shock"])
        self.tapsfor = ["G","W"]
    def Trigger(self,gamestate,card):
        if card == self:
            gamestate.TakeDamage(2)
##---------------------------------------------------------------------------##
class BreedingPool(Forest,Island):
    def __init__(self):
        CardType.Land.__init__(self, "Breeding Pool", ["shock"])
        self.tapsfor = ["U","G"]
    def Trigger(self,gamestate,card):
        if card == self:
            gamestate.TakeDamage(2)
##---------------------------------------------------------------------------##
class HallowedFountain(Plains,Island):
    def __init__(self):
        CardType.Land.__init__(self, "Hallowed Fountain", ["shock"])
        self.tapsfor = ["U","W"]
    def Trigger(self,gamestate,card):
        if card == self:
            gamestate.TakeDamage(2)
class WindsweptHeath(CardType.Land):
    def __init__(self):
        super().__init__("Windswept Heath",["fetch"])
        self.tapsfor = ["U","W","G"] #can't ACTUALLY make these colors, but can fetch any one of them
    def Trigger(self,gamestate,card):
        if card == self: #if IT is the thing which just entered the battlefield
            gamestate.field.remove(self) #sacrifice itself    
            gamestate.TakeDamage(1)
            tutortarget = AI.ChooseFetchTarget(gamestate,[Forest,Plains])
            if tutortarget is not None: #might be no valid targets
                gamestate.deck.remove(tutortarget)
                gamestate.field.append(tutortarget)
                if gamestate.verbose:
                    print("    fetch",tutortarget.name)
            gamestate.Shuffle()
            if tutortarget is not None:
                gamestate.ResolveCastingTriggers(tutortarget)
    @property
    def unavailable(self): #fetches are never available to tap for mana
        return True
##---------------------------------------------------------------------------##
class Westvale(CardType.Land):
    def maketoken(self,gamestate):
        gamestate.TakeDamage(1)
        gamestate.field.append( CardType.Creature("Cleric","",1,1,["token"]) )
        self.abilitylist = []
        self.tapped = True
    def flip(self,gamestate):
        sacrifices = AI.ChooseSacToOrmendahl(gamestate)
        if len(sacrifices)<5: return #not enough fodder to sac!
        if gamestate.verbose:
            print("sacrificing",[c.name for c in sacrifices],"to Ormendahl")
        for critter in sacrifices:
            gamestate.field.remove(critter)
        #legend rule
        alreadythere = [c for c in gamestate.field if c.name == "Ormendahl"]
        for ormendahl in alreadythere:
            print("LEGEND RULE! SACRIFICING THE OLD ORMENDAHL")
            gamestate.field.remove(ormendahl)
        gamestate.field.remove(self)
        #make the new Ormendahl
        ormendahl = CardType.Creature("Ormendahl","",9,7,["legendary","lifelink","flying"])
        ormendahl.summonsick = False #hasty
        gamestate.field.append( ormendahl )
    
    def canpayforflip(self,gamestate):
        return len([c for c in gamestate.field if isinstance(c,CardType.Creature)])>=5 and not self.tapped
    
    def __init__(self):
        super().__init__("Westvale Abbey",[])
        self.tapsfor = ["C"]
        self.abilitylist = [CardType.Ability("makecleric",self, "5", self.maketoken),
                            CardType.Ability("ormendahl", self, "5", self.flip     )]
    def Activate(self,gamestate):
        """Deducts payment for the ability and then performs the ability"""
        #overwriting to make sure we actually HAVE the creatures to sacrifice, 
        #since I can't check that without a gamestate object and I don't have
        #one during init or Untap
        if not self.canpayforflip(gamestate):
            #not actually able to use the ability right now! whoops. remove it from the ability list...
            self.abilitylist = [ab for ab in self.abilitylist if ab.name != "ormendahl"]
            print("removing ormendahl ability")
        else:
            super().Activate(gamestate)
    def Trigger(self,gamestate,card):
        #only add the Ormendahl ability when it's usable, so when have 5 creatures
        if card == self or isinstance(card,CardType.Creature): #if IT or a creature entered
            #if enough creatures to sac, AND we don't already have Ormendahl-maker ability...
            if self.canpayforflip(gamestate) and len(self.abilitylist)==1:
                self.abilitylist.append( CardType.Ability("ormendahl" ,self, "5", self.flip) )
                print("adding ormendahl ability")
    def Untap(self):
        super().Untap()
        self.abilitylist = [CardType.Ability("makecleric",self, "5", self.maketoken),
                            CardType.Ability("ormendahl", self, "5", self.flip     )]
    def MakeMana(self,gamestate,color):
        super().MakeMana(gamestate,color)
        if self.tapped:
            self.abilitylist = []
##---------------------------------------------------------------------------##
class Wildwoods(CardType.Land):
    def __init__(self):
        super().__init__("Stirring Wildwoods",["manland"])
        self.tapped = True
        self.tapsfor = ["G","W"]
##---------------------------------------------------------------------------##
class LumberingFalls(CardType.Land):
    def __init__(self):
        super().__init__("Lumbering Falls",["manland"])
        self.tapped = True
        self.tapsfor = ["U","G"]
##---------------------------------------------------------------------------##





Caretaker
Caryatid
Roots
Battlement
Axebane
Blossoms
Arcades
Recruiter
TrophyMage
Staff
Company

Forest
Plains
Island
TempleGarden
BreedingPool
HallowedFountain
WindsweptHeath
Westvale
Wildwoods
LumberingFalls