# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""

import Cards
import AI #hopefully not circular dependency...


##---------------------------------------------------------------------------##
class Caretaker(Cards.Creature,Cards.ManaSource):
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
            if isinstance(perm,Cards.Creature) and not perm.tapped:
                #can't make mana right now (or ever), so safe to tap
                if perm.summonsick or not isinstance(perm,Cards.ManaSource):
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
            if isinstance(perm,Cards.Creature) and not perm.tapped:
                #can't make mana right now (or ever), so safe to tap
                if perm.summonsick or not isinstance(perm,Cards.ManaSource):
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
class Caryatid(Cards.Creature,Cards.ManaSource):
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
class Roots(Cards.Creature,Cards.ManaSource):
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
    def Upkeep(self):
        super().Upkeep()
        self.unused = True
##---------------------------------------------------------------------------##
class Battlement(Cards.Creature,Cards.ManaSource):
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
class Axebane(Cards.Creature,Cards.ManaSource):
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
class Blossoms(Cards.Creature):
    def __init__(self):
        super().__init__("Blossoms","1G",0,4,["defender"])
    def Trigger(self,gamestate,card):
        if card == self: #if IT is the thing which just entered the battlefield
            gamestate.Draw(verbose=False)
##---------------------------------------------------------------------------##
##===========================================================================##
##---------------------------------------------------------------------------##
class Arcades(Cards.Creature):
    def __init__(self):
        super().__init__("Arcades","1GWU",3,5,["legendary","vigilance","dragon"])
    def Trigger(self,gamestate,card):
        if "defender" in card.typelist:
            gamestate.Draw(verbose=False)
        if card.name == self.name and card != self:
            # print("LEGEND RULE! SACRIFICING THE NEW ARCADES")
            gamestate.field.remove(card)
        
##---------------------------------------------------------------------------##
class Recruiter(Cards.Creature):
    def __init__(self):
        super().__init__("Recruiter","1G",2,2,["human"])
        self.frontface = True
        def recruit(gamestate):
            options = [c for c in gamestate.deck[:3] if isinstance(c,Cards.Creature)]
            if len(options)>0: #might wiff entirely
                card = AI.ChooseRecruit(gamestate,options)
                gamestate.deck.remove(card)
                gamestate.hand.append(card)
                gamestate.deck = gamestate.deck[2:]+gamestate.deck[:2] #put to bottom, ignores order
            else:
                gamestate.deck = gamestate.deck[3:]+gamestate.deck[:3]     #put all 3 to bottom
        self.abilitylist = [Cards.Ability(self, "2G", recruit)]
                
                
##---------------------------------------------------------------------------##
class TrophyMage(Cards.Creature):
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
class Staff(Cards.Permanent):
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
class Company(Cards.Spell):
    def __init__(self):
        super().__init__("Company", "3G", ["instant"])
    def Effect(self,gamestate):
        options = [card for card in gamestate.deck[:6] if (isinstance(card,Cards.Creature) and card.cost.CMC()<=3)]
        if len(options)>0: #might wiff entirely   
            chosen = AI.ChooseCompany(gamestate,options)
            for card in chosen:
                gamestate.deck.remove(card)
                gamestate.field.append(card)
            # print("    hit:",[str(card) for card in chosen])
            gamestate.deck = gamestate.deck[6-len(chosen):]+gamestate.deck[:6-len(chosen)] #put to bottom, ignores order
            for card in chosen:
                gamestate.ResolveCastingTriggers(card)
        else:
            gamestate.deck = gamestate.deck[6:]+gamestate.deck[:6] #all 6 to bottom
                
            
##---------------------------------------------------------------------------##
##===========================================================================##
##---------------------------------------------------------------------------##
class Forest(Cards.Land):
    def __init__(self):
        super().__init__("Forest",["basic"])
        self.tapsfor = ["G"]
##---------------------------------------------------------------------------##
class Plains(Cards.Land):
    def __init__(self):
        super().__init__("Plains",["basic"])
        self.tapsfor = ["W"]
##---------------------------------------------------------------------------##
class Island(Cards.Land):
    def __init__(self):
        super().__init__("Island",["basic"])
        self.tapsfor = ["U"]
##---------------------------------------------------------------------------##
class TempleGarden(Forest,Plains):
    def __init__(self):
        Cards.Land.__init__(self, "Temple Garden", ["shock"])
        self.tapsfor = ["G","W"]
    def Trigger(self,gamestate,card):
        if card == self:
            gamestate.life -= 2
##---------------------------------------------------------------------------##
class BreedingPool(Forest,Island):
    def __init__(self):
        Cards.Land.__init__(self, "Breeding Pool", ["shock"])
        self.tapsfor = ["U","G"]
    def Trigger(self,gamestate,card):
        if card == self:
            gamestate.life -= 2
##---------------------------------------------------------------------------##
class HallowedFountain(Plains,Island):
    def __init__(self):
        Cards.Land.__init__(self, "Hallowed Fountain", ["shock"])
        self.tapsfor = ["U","W"]
    def Trigger(self,gamestate,card):
        if card == self:
            gamestate.life -= 2
class WindsweptHeath(Cards.Land):
    def __init__(self):
        super().__init__("Windswept Heath",["fetch"])
        self.tapsfor = ["U","W","G"] #can't ACTUALLY make these colors, but can fetch any one of them
    def Trigger(self,gamestate,card):
        if card == self: #if IT is the thing which just entered the battlefield
            gamestate.field.remove(self) #sacrifice itself    
            gamestate.life -= 1
            tutortarget = AI.ChooseFetchTarget(gamestate,[Forest,Plains])
            if tutortarget is not None: #might be no valid targets
                gamestate.deck.remove(tutortarget)
                gamestate.field.append(tutortarget)
            gamestate.Shuffle()
            if tutortarget is not None:
                gamestate.ResolveCastingTriggers(tutortarget)
    @property
    def unavailable(self): #fetches are never available to tap for mana
        return True
##---------------------------------------------------------------------------##
class Westvale(Cards.Land):
    def maketoken(self,gamestate):
        gamestate.life -= 1
        token = Cards.Creature("Cleric","",1,1,["token"])
        gamestate.field.append(token)
        self.abilitylist = []
        self.tapped = True
    def __init__(self):
        super().__init__("Westvale Abbey",[])
        self.tapsfor = ["C"]
        
        self.abilitylist = [Cards.Ability(self, "5", self.maketoken)]
    def Untap(self):
        super().Untap()
        self.abilitylist = [Cards.Ability(self, "5", self.maketoken)]
    def MakeMana(self,gamestate,color):
        super().MakeMana(gamestate,color)
        if self.tapped:
            self.abilitylist = []
##---------------------------------------------------------------------------##
class Wildwoods(Cards.Land):
    def __init__(self):
        super().__init__("Stirring Wildwoods",["manland"])
        self.tapped = True
        self.tapsfor = ["G","W"]
##---------------------------------------------------------------------------##
class LumberingFalls(Cards.Land):
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