# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


from ManaHandler import ManaCost,ManaPool
import Costs
import ZONE
import Abilities






##---------------------------------------------------------------------------##

class CardType():
    
    def __init__(self,name,cost,typelist):
        """
        name (str)  : name of this card.
        cost (Cost) : mana and additional cost to cast this card.
        typelist (list(str)):
                      List of lowercase tags describing this card. Includes
                      MtG types as well as relevant keywords.

        on_resolve  : function describing the resolution of spell being cast.
                      Gamestate, source Cardboard -> list of all (Gamestate,
                      source Cardboard) pairs where the effect has been
                      resolved.
                      This includes moving the card from the stack to other
                      zones, if relevant.
        
        
        OTHER THINGS TO FILL IN LATER
        """
        self.name = name
        self.cost = cost
        self.typelist = [s.lower() for s in typelist]
        #activated abilities
        self.activated = []  #includes mana abilities
        #triggered abilities
        self.trig_move = []
        self.trig_upkeep = []
        self.trig_attack = []
        self.trig_endstep = []
        ###---I don't actually USE these, but in theory I could in the future
        # self.trig_activate   #abilities that trigger when an ability is activated
        # self.trig_draw = []  #abilities that trigger when a card is drawn
        # self.static = []     #static effects

    #abilities and triggers within a card are always called by the gamestate
    #by passing the source Cardboard into the function. Thus, the ability
    #doesn't need to know parent Cardboard ahead of time.  This allows me to
    #make CardTypes that are generic and never mutated and maintain the
    #distinction between Cardboard and CardType. This distinction makes it much
    #easier to copy and iterate Gamestates.

    def CanAfford(self,gamestate,source):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        return self.cost.CanAfford(gamestate,source)  
    
    def ResolveSpell(self,gamestate,cardboard):
        """function: gamestate,cardboard->[gamestate]"""
        return [gamestate] #placeholder for children to overwrite




class Permanent(CardType):
    
    def __init__(self,name,cost,typelist):
        super().__init__(name,cost,typelist)
        
    
    def ResolveSpell(self,gamestate,cardboard):
        newstate,[perm] = gamestate.CopyAndTrack([cardboard])
        newstate.MoveZone(perm,ZONE.FIELD)
        return newstate.ClearSuperStack()  #list of GameStates





class Creature(Permanent):
    
    def __init__(self,name,cost,typelist,power,toughness):
        super().__init__(name,cost,typelist)
        self.basepower = power
        self.basetoughness = toughness
        if "creature" not in self.typelist:
            self.typelist = ["creature"] + self.typelist




class Land(Permanent):
    
    def __init__(self,name,typelist):
        #build the "cost" of casting a land
        def canplayland(gamestate,source):
            return not gamestate.playedland
        def playland(gamestate,source):
            #doesn't actually move, just pays the "cost" of saying we've played a land
            newstate,[newsource] = gamestate.CopyAndTrack([source])
            newstate.playedland = True
            return [(newstate,newsource)]
        cost = Costs.Cost(None,canplayland,playland)
        #use normal initializer
        super().__init__(name,cost,typelist)
        if "land" not in self.typelist:
            self.typelist = ["land"] + self.typelist
    
    def EnterTapped(gamestate,source):
        """useful for tap-lands. GameState,Cardboard -> [GameState]. MUTATES."""
        effects = gamestate.TapPermanent(source)
        gamestate.stack += effects
        return [gamestate]

    def ShockIntoPlay(gamestate,source):
        """useful for shock lands.  GameState,Cardboard -> [GameState]. MUTATES."""
        gamestate2,[source2] = gamestate.CopyAndTrack([source])
        #Either the land enters tapped OR we take 2 damage
        source.tapped = True     #effect is allowed to mutate
        gamestate2.life -= 2
        return [gamestate,gamestate2]

    def LandAvailable(gamestate,source):
        """useful for abilities checking if the land can be tapped for mana,
        GameState,Cardboard -> bool"""
        return (not source.tapped and source.zone == ZONE.FIELD)




# class Spell(CardType):
    
#     def __init__(self,name,cost,typelist,on_resolve):      
#         super().__init__(name,cost,typelist)
#         self.on_resolve = on_resolve

#     def ResolveSpell(self,gamestate,cardboard):
#         assert(gamestate.stack[-1] is cardboard)
#         newstate,perm = gamestate.CopyAndTrack([cardboard])
#         #resolve the effects of the spell as Gamestate,Cardboard pairs
#         universes = perm.on_resolve(gamestate,perm)
#         #move the spell to wherever it goes
        
#         effects = newstate.MoveZone(perm,ZONE.FIELD)
#         #need to reorder effects???  later ------------------------------------Add reshuffling of effects?
#         newstate.stack += effects
#         return [(newstate,perm)]
    
    