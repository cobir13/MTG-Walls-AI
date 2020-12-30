# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 11:50:12 2020

@author: Cobi
"""

import Cards

##---------------------------------------------------------------------------##
class Caretaker(Cards.Creature):
    def __init__(self):
        super().__init__("Saruli Caretaker"    ,"G" ,0,3,["defender","dryad"])
    @property
    def unavailable(self):
        return self.tapped or self.summonsick
    def MakeMana(self,gamestate):
        """mutates the gamestate!"""
        if self.unavailable: return #do nothing 
        safetotap = []
        caretakers = []
        for perm in gamestate.field:
            if isinstance(perm,Cards.Creature) and not perm.tapped:
                #can't make mana right now (or ever), so safe to tap
                if perm.summonsick or not hasattr(perm,"MakeMana"):
                    safetotap.append(perm)
                if isinstance(perm,Caretaker) and not perm.summonsick:
                    caretakers.append(perm)
        i = caretakers.index(self) #which number usable caretaker are you?
        if i<len(safetotap):
            safetotap[i].tapped = True #congrats! you have a matching tappable creature
            gamestate.pool.AddMana("L")
            self.tapped = True
        elif (i-len(safetotap)) % 2 == 1:
            caretakers[i-1].tapped = True  #you're an odd caretaker, so you get to tap an even caretaker
            gamestate.pool.AddMana("L")
            self.tapped = True
        else:
            return #you're an even leftover caretaker. sorry, no mana for you
##---------------------------------------------------------------------------##
class Caryatid(Cards.Creature):
    def __init__(self):
        super().__init__("Sylvan Caryatid"     ,"1G",0,3,["defender","plant"])
    @property
    def unavailable(self):
        return self.tapped or self.summonsick
    def MakeMana(self,gamestate):
        """mutates the gamestate!"""
        if self.unavailable: return #do nothing 
        gamestate.pool.AddMana("L")
        self.tapped = True
##---------------------------------------------------------------------------##
class Roots(Cards.Creature):
    def __init__(self):
        super().__init__("Wall of Roots"       ,"1G",0,5,["defender","plant","wall"])
        self.unused = True
    @property
    def unavailable(self):
        return not self.unused
    def MakeMana(self,gamestate):
        """mutates the gamestate!"""
        if self.unavailable: return #already made mana this turn, can't do it again
        gamestate.pool.AddMana("G")
        self.unused = False
    def Upkeep(self):
        super().Upkeep()
        self.unused = True
##---------------------------------------------------------------------------##
class Battlement(Cards.Creature):
    def __init__(self):
        super().__init__("Overgrown Battlement","1G",0,4,["defender","wall"])
    @property
    def unavailable(self):
        return self.tapped or self.summonsick
    def MakeMana(self,gamestate):
        """mutates the gamestate!"""
        if self.unavailable: return #do nothing 
        gamestate.pool.AddMana( "G"*len([perm for perm in gamestate.field if "defender" in perm.typelist]) )
        self.tapped = True
##---------------------------------------------------------------------------##
class Axebane(Cards.Creature):
    def __init__(self):
        super().__init__("Axebane Guardian"    ,"2G",0,3,["defender","human","druid"])
    @property
    def unavailable(self):
        return self.tapped or self.summonsick
    def MakeMana(self,gamestate):
        """mutates the gamestate!"""
        if self.unavailable: return #do nothing 
        gamestate.pool.AddMana( "L"*len([perm for perm in gamestate.field if "defender" in perm.typelist]) )
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
class Shock(Cards.Land):
    def __init__(self):
        super().__init__("Shockland",["shock"])
        self.tapsfor = ["G","W"]
    def Effect(self,gamestate):
        gamestate.life -= 2
##---------------------------------------------------------------------------##
class Plains(Cards.Land):
    def __init__(self):
        super().__init__("Plains",["basic"])
        self.tapsfor = ["W"]
##---------------------------------------------------------------------------##
class Westvale(Cards.Land):
    def __init__(self):
        super().__init__("Westvale Abbey",[])
        self.tapsfor = ["C"]
##---------------------------------------------------------------------------##
class ManLand(Cards.Land):
    def __init__(self):
        super().__init__("ManLand",["manland"])
        self.tapped = True
        self.tapsfor = ["G","W"]
##---------------------------------------------------------------------------##