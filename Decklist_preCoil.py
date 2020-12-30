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
    def ManaCanMake(self,gamestate):
        if self.tapped or self.summonsick:
            return ""
        else:
            safetotap = []
            caretakers = []
            for perm in gamestate.field:
                if isinstance(perm,Cards.Creature) and not perm.tapped:
                    #can't make mana right now (or ever), so safe to tap
                    if perm.summonsick or not hasattr(perm,"ManaCanMake"):
                        safetotap.append(perm)
                    if isinstance(perm,Caretaker) and not perm.summonsick:
                        caretakers.append(perm)
            i = caretakers.index(self) #which number usable caretaker are you?
            if i<len(safetotap):
                return "L" #congrats! you have a matching tappable creature
            elif (i-len(safetotap)) % 2 == 1:
                return "L" #you're an odd caretaker, so you get to tap an even caretaker
            else:
                return "" #you're an even leftover caretaker. sorry
    def MakeMana(self,gamestate):
        assert(not self.tapped and not self.summonsick)
        safetotap = []
        caretakers = []
        for perm in gamestate.field:
            if isinstance(perm,Cards.Creature) and not perm.tapped:
                #can't make mana right now (or ever), so safe to tap
                if perm.summonsick or not hasattr(perm,"ManaCanMake"):
                    safetotap.append(perm)
                if isinstance(perm,Caretaker) and not perm.summonsick:
                    caretakers.append(perm)
        i = caretakers.index(self) #which number usable caretaker are you?
        if i<len(safetotap):
            safetotap[i].tapped = True #congrats! you have a matching tappable creature 
        elif (i-len(safetotap)) % 2 == 1:
            caretakers[i-1].tapped = True
        else:
            assert(False) #tried to make mana even though couldn't! should never get here!
        gamestate.pool.AddMana(self.ManaCanMake(gamestate))
        self.tapped = True
##---------------------------------------------------------------------------##
class Caryatid(Cards.Creature):
    def __init__(self):
        super().__init__("Sylvan Caryatid"     ,"1G",0,3,["defender","plant"])
    def ManaCanMake(self,gamestate):
        return "L" if (not self.tapped and not self.summonsick) else ""
    def MakeMana(self,gamestate):
        assert(not self.tapped and not self.summonsick)
        gamestate.pool.AddMana(self.ManaCanMake(gamestate))
        self.tapped = True
##---------------------------------------------------------------------------##
class Roots(Cards.Creature):
    def __init__(self):
        super().__init__("Wall of Roots"       ,"1G",0,5,["defender","plant","wall"])
        self.unused = True
    def ManaCanMake(self,gamestate):
        return "G" if self.unused else ""
    def MakeMana(self,gamestate):
        assert(self.unused)
        gamestate.pool.AddMana(self.ManaCanMake(gamestate))
        self.unused = False
##---------------------------------------------------------------------------##
class Battlement(Cards.Creature):
    def __init__(self):
        super().__init__("Overgrown Battlement","1G",0,4,["defender","wall"])
        self.unused = True
    def ManaCanMake(self,gamestate):
        if not self.tapped and not self.summonsick:
            return "G"*len([perm for perm in gamestate.field if "defender" in perm.typelist])
        else:
            return ""
    def MakeMana(self,gamestate):
        assert(not self.tapped and not self.summonsick)
        gamestate.pool.AddMana(self.ManaCanMake(gamestate))
        self.tapped = True
##---------------------------------------------------------------------------##
class Axebane(Cards.Creature):
    def __init__(self):
        super().__init__("Axebane Guardian"    ,"2G",0,3,["defender","human","druid"])
        self.unused = True
    def ManaCanMake(self,gamestate):
        if not self.tapped and not self.summonsick:
            return "L"*len([perm for perm in gamestate.field if "defender" in perm.typelist])
        else:
            return ""
    def MakeMana(self,gamestate):
        assert(not self.tapped and not self.summonsick)
        gamestate.pool.AddMana(self.ManaCanMake(gamestate))
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