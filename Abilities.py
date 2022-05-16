# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


from ManaHandler import ManaCost,ManaPool
import ZONE
import copy




#abilities and triggers within a card are always called by the gamestate
#by passing the source Cardboard into the function. Thus, the ability
#doesn't need to know parent Cardboard ahead of time.  This allows me to
#make CardTypes that are generic and never mutated and maintain the
#distinction between Cardboard and CardType. This distinction makes it much
#easier to copy and iterate Gamestates.




class GenericAbility():
    
    def __init__(self,name,cost,trigger_fn,execute_fn):
        """
        name (str):
            The name of this ability. Meant to be human-readable
        cost (Cost or None):
            The mana and non-mana costs of activating this ability. If there
            is no cost (perhaps because this is a purely triggered ability)
            then set the cost as None.
        trigger_fn (function or None):
            Function that takes in (Gamestate,source,trigger,origin). That is:
            a GameState, a source Cardboard, a trigger Cardboard, and the Zone
            the trigger cardboard moved from.
            Returns a boolean: "in this GameState, did the movement of this
            trigger Cardboard from the origin Zone cause the source Cardboard's
            ability to trigger?"  DOES NOT MUTATE.
            Can also be None, if there is no trigger (perhaps because this is
            a purely activated ability)
        execute_fn (function):
            Function that takes in a GameState and a source Cardboard.
            Returns a list of GamesStates giving all possible ways the
            ability could be executed, accounting for all player choices and
            options.  Empty list if impossible to execute.
            DOES NOT MUTATE the original gamestate.
        NOTE: ABILITIES ONLY EVER HAVE ONE SOURCE.
        """
        self.name = name
        self.cost = cost                #Cost or None
        self.trigger_fn = trigger_fn    #function: GameState,Cardboard,Cardboard,Zone -> bool
        self.execute_fn = execute_fn    #function: GameState,Cardboard -> [GameState]
     
    def CanAfford(self,gamestate,source):
        """Returns boolean: can this gamestate afford the cost?
        DOES NOT MUTATE."""
        if self.cost is None:
            return True
        else:
            return self.cost.CanAfford(gamestate,source)   
    
    def Pay(self,gamestate,source):
        """Returns list of GameState,Cardboard pairs in which the cost is paid.
        Takes in the GameState in which the cost is supposed to be paid and
            the source Cardboard that is generating the cost.
        Returns a list of (GameState,Cardboard) pairs in which the cost has
            been paid. The list is length 1 if there is exactly one way to pay
            the cost, and the list is length 0 if the cost cannot be paid.
        The original GameState and Source are NOT mutated.
        """
        #check to make sure the execution is legal
        if not self.cost.CanAfford(gamestate,source):
            return []
        #if there IS no cost, then paying the cost changes nothing
        if self.cost is None:
            g,[s] = gamestate.CopyAndTrack([source])
            return [(g,s)]
        else:
            return self.cost.Pay(gamestate,source)
    
    
    def IsTriggered(self,gamestate,source,trigger,origin):
        """Returns a boolean: does this trigger-card cause the ability of this
        source-card to trigger?
        gamestate: the GameState where the source and trigger Cardboards live
        source:    the Cardboard which owns the ability
        trigger:   the Cardboard which has (potentially) triggered the ability    
        origin:    the Zone the trigger card moved from
        DOES NOT MUTATE."""
        if self.trigger_fn is None:
            return False    #if no trigger function, is NEVER triggered
        else:
            return self.trigger_fn(gamestate,source,trigger,origin)   
    
    def Execute(self,gamestate,source):
        """
        Takes in the GameState in which the ability is supposed to be performed
            and also the source Cardboard that is generating the ability.
        Returns a list of GameStates where the effect has been performed:
            - length 1 if there is exactly one way to do this
            - length 0 if this cannot be done (costs, lack of targets, etc)
            - length >1 if there are options that can be decided differently.
        The original GameState and source Cardboard are NOT mutated.
        """
        statelist = []
        for state in self.execute_fn(gamestate,source):
            statelist += state.ClearSuperStack()
        return statelist
    
    
    def __str__(self):
        return self.name



class TriggeredByMove(GenericAbility):
    """Also a good place to collect some useful functions that specific
    abilities might want to make use of.

    Remember: trigger_fn has the signature:
        GameState,source Cardboard, trigger Cardboard, origin Zone -> bool
    """
    def __init__(self,name,trigger_fn,execute_fn):
        super().__init__(name=name,cost=None,trigger_fn=trigger_fn,execute_fn=execute_fn)   

    def ETB_self(gamestate,source,trigger,origin):
        return (source is trigger and trigger.zone == ZONE.FIELD)
    
    def ETB_other(gamestate,source,trigger,origin):
        return (source.zone == ZONE.FIELD and trigger.zone == ZONE.FIELD)
    
    def Cast_self(gamestate,source,trigger,origin):
        return (source is trigger and trigger.zone == ZONE.STACK)

    def Dies_self(gamestate,source,trigger,origin):
        return (    source is trigger
                and trigger.zone == ZONE.GRAVE
                and origin == ZONE.FIELD)


class AsEnterEffect(TriggeredByMove):
    """A specific type of triggered ability. This represents effects which
    occur AS a permanent enters the battlefield. This bypasses the normal
    stack procedure, since it simply OCCURS rather than going onto the stack
    in the usual fashion. Examples include:
        A shock-land giving the options to enter tapped or make you pay 2 life;
        A clone choosing what to copy;
        A 0/0 entering with +1/+1 counters on it;
    They are a separate subclass so that they can be treated differently when
    they are found on the superstack. They are applied immediately rather
    than being put onto the stack.
    """
    def __init__(self,name,execute_fn):
        super().__init__(name=name,
                         trigger_fn=TriggeredByMove.ETB_self,
                         execute_fn=execute_fn)   
    







class ActivatedAbility(GenericAbility):
    
    def __init__(self,name,cost,execute_fn):
        super().__init__(name=name,cost=cost,trigger_fn=None,execute_fn=execute_fn)




class ManaAbility(ActivatedAbility):
    """No functional difference to ActivatedAbility, just for tracking so that
    ManaAbilities can skip the stack.  Also a good place to collect some
    useful functions that specific abilities might want to make use of."""
    
    def DorkAvailable(gamestate,source):
        return (not source.tapped and not source.summonsick and 
                source.zone == ZONE.FIELD)
    
    def TapToPay(gamestate,source):
        """Payment function must return states with empty superstacks"""
        newstate,[newsource] = gamestate.CopyAndTrack([source])
        newstate.TapPermanent(newsource)
        assert(len(newstate.superstack)==0)
        return [(newstate,newsource)]

    def AddColor(gamestate,source,color):
        newstate,[newsource] = gamestate.CopyAndTrack([source])
        newstate.AddToPool(color) #add mana
        assert(len(newstate.superstack)==0)
        return [newstate]

    def AddDual(gamestate,source,color1,color2):
        #make first game state where we choose the first option
        state1,[source1] = gamestate.CopyAndTrack([source])
        state1.AddToPool(color1) #add mana
        assert(len(state1.superstack)==0)
        #make second game state where we choose the second option
        state2,[source2] = gamestate.CopyAndTrack([source])
        state2.AddToPool(color2) #add mana
        assert(len(state2.superstack)==0)
        return [state1,state2]







class StackEffect():
    
    def __init__(self,source,otherlist,ability):
        self.source = source  #Cardboard source of the effect. "Pointer".
        self.otherlist = []   #list of other relevant Cardboards. "Pointers".
        self.ability = ability  #GenericAbility

    def PutOnStack(self,gamestate):
        """Returns list of GameStates where ability is paid for and now on
        stack.  Note: superstack is empty in returned states."""
        return gamestate.ActivateAbilities(self.source,self.ability)
    
    def Enact(self,gamestate):
        """Returns list of GameStates resulting from performing this effect"""
        return self.ability.Execute(gamestate,self.source)
        
    def __str__(self):
        return self.ability.name
    
    def __repr__(self):
        return "Effect: "+self.ability.name
    
    def ID(self):
        cards = ",".join([c.ID() for c in [self.source]+self.otherlist])
        return "E(%s|%s)" %(cards,self.ability.name)
    
    def EquivTo(self,other):
        return self.ID() == other.ID()
        # return (    type(self) == type(other)
        #         and self.source == other.source
        #         and set(self.otherlist) == set(other.otherlist)
        #         and self.ability.name == other.ability.name)

    @property
    def name(self):
        return self.ability.name