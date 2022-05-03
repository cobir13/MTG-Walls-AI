# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""

import random
import Decklist
import Cardboard
import CardType
import ZONE
from ManaHandler import ManaPool
import GameState




# class SetEquiv():
#     def __init__(objs_to_wrap,hashfn):
#         self.obj = obj
        



    
    
class TurnTracker():
    """
    Holds all gamestates that occur over the course of a turn.
    
    It is given the starting state of a turn, after untap and upkeep and draw.
    It calculates all possible moves until it runs out of moves and the
    turn is over.
    
    Stores the initial states, the final states, and all intermediate states.
    """
    
    
    def __init__(self,startnodes):
        # startnode = TurnTracker.ActionNode(gamestate,[],None)
        self.allnodes = set(startnodes)     #set of all ActionNode intermediate states
        self.finalnodes = set()             #set of ActionNodes with no more options
        self.activenodes = set(startnodes)  #set of nodes that still need processing
        self.traverse_counter = 0 #for debug tracking, no real use

        
    def InitFromGameState(gamestate,history=[]):
        startnode = TurnTracker.ActionNode(gamestate,history)
        return TurnTracker([startnode])
    
    
    def PlayTurn(self):
        while len(self.activenodes)>0:
            node = self.activenodes.pop()  #pop a random node to work with
            valid_actions = node.state.GetValidActions()
            #if there are no valid actions, this is a final node
            if len(valid_actions)==0:
                self.finalnodes.add(node)
                #it's already in allnodes so don't need to add it to that
                continue
            #if there ARE valid actions, make new nodes by taking them
            for option in valid_actions:
                descrip = option.name
                #make new gamestates by performing the option
                universes = option.Run()  #list of GameState,Cardboard pairs
                for gamestate,_ in universes: 
                    #build the next node
                    histlog = node.history + [descrip] #add this action to log
                    newnode = TurnTracker.ActionNode(gamestate,histlog)
                    self.traverse_counter += 1
                    #if node already exists, then we're done with this node
                    if newnode in self.allnodes:
                        continue #already seen this state, no need to do it again
                    #if node is new, then add it to active nodes! & track it!
                    else:
                        self.activenodes.add(newnode)
                        self.allnodes.add(newnode)
            
   
    def GetFinal(self):
        """Return a list of final nodes. Uses a fancier version of equivalency,
        where nodes are equal if their states would be equal IF THEY WERE
        UNTAPPED. They aren't actually untapped yet, this just checks ahead."""
        class FancyNode():
            def __init__(self,node):
                self.node = node
            def __eq__(self,other):
                untapped = self.node.state.copy()
                untapped.Untap()
                untapped_other = other.node.state.copy()
                untapped_other.Untap()
                return untapped == untapped_other #usual _eq_ for GameStates
            def __hash__(self):
                untapped = self.node.state.copy()
                untapped.Untap()
                return untapped.__hash__()
        fancyset = set()
        for node in self.finalnodes:
            fancyset.add(FancyNode(node))
        return [fn.node for fn in fancyset]


    def GetAll(self):
        """Return a list of all nodes. Uses a fancier version of equivalency,
        where nodes are equal if their states would be equal IF THEY WERE
        UNTAPPED. They aren't actually untapped yet, this just checks ahead.
        I can use this if I want to permit the AI to "stop early" before
        exhausting all possible moves."""
        class FancyNode():
            def __init__(self,node):
                self.node = node
            def __eq__(self,other):
                untapped = self.node.state.copy()
                untapped.Untap()
                untapped_other = other.node.state.copy()
                untapped_other.Untap()
                return untapped == untapped_other #usual _eq_ for GameStates
            def __hash__(self):
                untapped = self.node.state.copy()
                untapped.Untap()
                return untapped.__hash__()
        fancyset = set()
        for node in self.allnodes:
            fancyset.add(FancyNode(node))
        return [fn.node for fn in fancyset]
    
    
    class ActionNode():
        """
        Node. Holds a gamestate and the history of actions taken this turn to
        reach this gamestate.  Class within class.
        """
        def __init__(self,gamestate,history):
            self.state = gamestate
            self.history = []       #list of descriptions of arriving at this
            if gamestate.verbose:   #state. Only use for verbose gamestates.
                self.history = history 
                
        def __hash__(self):
            return self.state.__hash__()
        
        def __eq__(self,other):
            return self.state == other.state
            
        def __str__(self):
            return str(self.state)
        
        def PrintEvolution(self):    
            print("\n".join(self.history)+"\n"+str(self.state))
            
        def AddToHistory(self,description):
            if self.state.verbose:
                self.history.append(description)
        
        
            
    
class PlayTree():
    
    
    def __init__(self,startstate,turnlimit):
        self.startstate = startstate  #initial GameState
        self.turnlimit = turnlimit
        turn1 = TurnTracker.InitFromGameState(startstate)
        self.trackerlist = [turn1]  #one tracker object per turn of the game
                            #[-1].finalnodes should always be full
        turn1.PlayTurn() #do this AFTER adding tracker, in case Win or Lose error

                                    
    
    def PlayATurn(self):
        #get final state of previous turn
        prevtracker = self.trackerlist[-1]
        #apply untap, upkeep, and draw to these nodes
        newnodes = set()
        for node in prevtracker.GetFinal():
            node.AddToHistory("untap,upkeep,draw")
            node.state.Untap()
            node.state.Upkeep()
            node.state.Draw()
            newnodes.add(node)
        #use these nodes as starting piont for next turn's tracker
        newtracker = TurnTracker(newnodes)
        self.trackerlist.append(newtracker)
        newtracker.PlayTurn() #do this AFTER adding tracker, in case Win or Lose error

    
    def LatestTracker(self):
        return self.trackerlist[-1]

    def LatestNodes(self):
        return self.trackerlist[-1].GetFinal()
    
    def PrintLatest(self):
        finalnodes = self.LatestNodes()
        if len(finalnodes)==0:
            print("\n-------start of upkeep of turn %i----------" %(len(self.trackerlist)) )
            for node in self.LatestTracker().activenodes:
                print(node)
                print("-----------------")
        else:
            print("\n-------end of turn %i----------" %(len(self.trackerlist)) )
            for node in finalnodes:
                print(node)
                print("-----------------")
    
    
    
    