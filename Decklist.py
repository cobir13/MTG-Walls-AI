# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""

import Cards

##---------------------------------------------------------------------------##
class Caretaker(Cards.Creature,Cards.ManaSource):
    def __init__(self):
        super().__init__("Saruli Caretaker"    ,"G" ,0,3,["defender","dryad"])
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
        super().__init__("Sylvan Caryatid"     ,"1G",0,3,["defender","plant"])
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
        super().__init__("Wall of Roots"       ,"1G",0,5,["defender","plant","wall"])
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
        super().__init__("Overgrown Battlement","1G",0,4,["defender","wall"])
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
        super().__init__("Axebane Guardian"    ,"2G",0,3,["defender","human","druid"])
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


        





arcades   = Cards.Creature("Arcades, the Strategist","1GWU",3,5,["vigilance","elder","dragon"])
recruiter = Cards.Creature("Duskwatch Recruiter","1G",2,2,["human","warrier","werewolf"])
trophymage= Cards.Creature("Trophy Mage","2U",2,2,["human","wizard"])

staff     = Cards.Permanent("Staff of Domination", "3", ["artifact"])
company   = Cards.Spell("Collected Company", "3G", "instant")







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
class TempleGarden(Cards.Land):
    def __init__(self):
        super().__init__("Temple Garden",["shock"])
        self.tapsfor = ["G","W"]
    def Effect(self,gamestate):
        gamestate.life -= 2
##---------------------------------------------------------------------------##
class BreedingPool(Cards.Land):
    def __init__(self):
        super().__init__("Breeding Pool",["shock"])
        self.tapsfor = ["U","G"]
    def Effect(self,gamestate):
        gamestate.life -= 2
##---------------------------------------------------------------------------##
class HallowedFountain(Cards.Land):
    def __init__(self):
        super().__init__("Hallowed Fountain",["shock"])
        self.tapsfor = ["U","W"]
    def Effect(self,gamestate):
        gamestate.life -= 2
##---------------------------------------------------------------------------##
class Westvale(Cards.Land):
    def __init__(self):
        super().__init__("Westvale Abbey",[])
        self.tapsfor = ["C"]
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