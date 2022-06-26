# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""

import random

import RulesText
import ZONE
from ManaHandler import ManaPool
import GameState


    
    
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
            #options are: cast spell, activate ability, let stack resolve
            stackeffs = node.state.GetValidActivations()
            castables = node.state.GetValidCastables()
            #if no valid actions, this is a final node
            if len(stackeffs)+len(castables)+len(node.state.stack) == 0:
                self.finalnodes.add(node)
                #it's already in allnodes so don't need to add it to that
                continue    
            #if there ARE valid actions, make new nodes by taking them
            newnodes = []
            for effect in stackeffs:
                #list of GameStates with the ability effect paid for, on stack
                for gamestate in effect.PutOnStack(node.state):
                    histlog = node.history + ["Use "+effect.name]
                    newnodes.append(TurnTracker.ActionNode(gamestate,histlog))
            for card in castables:
                #list of GameStates with the card cost paid for, card on stack
                for gamestate in node.state.CastSpell(card):
                    histlog = node.history + ["Cast "+card.name]
                    newnodes.append(TurnTracker.ActionNode(gamestate,histlog))
            if len(node.state.stack)>0:
                #list of GameStates with the top effect on the stack resolved
                for gamestate in node.state.ResolveTopOfStack():
                    newnodes.append(TurnTracker.ActionNode(gamestate,node.history))
            #add these new nodes to the tracker
            for newnode in newnodes:
                self.traverse_counter += 1
                #if node already exists, then we're done with this node
                if newnode in self.allnodes:
                    continue #already seen this state, so we're done.
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
                untapped.UntapStep()
                untapped_other = other.node.state.copy()
                untapped_other.UntapStep()
                return untapped == untapped_other #usual _eq_ for GameStates
            def __hash__(self):
                untapped = self.node.state.copy()
                untapped.UntapStep()
                return untapped.__hash__()
        fancyset = set()
        for node in self.finalnodes:
            fancyset.add(FancyNode(node))
        return [fn.node for fn in fancyset]

    def GetAll(self):
        """Return a list of all nodes. Uses a fancier version of equivalency,
        where nodes are equal if their states would be equal WHEN WE UNTAP
        NEXT TURN. They aren't actually untapped yet, this just checks ahead.
        I can use this if I want to permit the AI to "stop early" before
        exhausting all possible moves."""
        class FancyNode():
            def __init__(self,node):
                self.node = node
            def __eq__(self,other):
                untapped = self.node.state.copy()
                untapped.UntapStep()
                untapped_other = other.node.state.copy()
                untapped_other.UntapStep()
                return untapped == untapped_other #usual _eq_ for GameStates
            def __hash__(self):
                untapped = self.node.state.copy()
                untapped.UntapStep()
                return untapped.__hash__()
        fancyset = set()
        for node in self.allnodes:
            fancyset.add(FancyNode(node))
        #return the not-yet-untapped nodes, but only those with empty stacks
        return [fn.node for fn in fancyset if len(fn.node.state.stack)==0]
    
    
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
        
        def copy(self):
            return TurnTracker.ActionNode(self.state.copy(),
                                          [s for s in self.history])
        
            
    
class PlayTree():
    
    def __init__(self,startstate,turnlimit):
        self.startstate = startstate  #initial GameState
        self.turnlimit = turnlimit
        turn1 = TurnTracker.InitFromGameState(startstate)
        self.trackerlist = [turn1]  #one tracker object per turn of the game
                            #[-1].finalnodes should always be full
        turn1.PlayTurn() #do this AFTER adding tracker, in case Win or Lose error

                                    
    
    def PlayNextTurn(self):
        #get final state of previous turn
        prevtracker = self.trackerlist[-1]
        #apply untap, upkeep, and draw to these nodes
        newnodes = set()
        for node in prevtracker.GetFinal():
            oldstate = node.state
            newstate = oldstate.copy()
            newstate.UntapStep()
            newstate.UpkeepStep()
            newstate.Draw()  #technically should clear super_stack FIRST but whatever
            #clear the super stack, then clear the normal stack
            activelist = newstate.ClearSuperStack()
            finalstates = set()
            while len(activelist)>0:
                state = activelist.pop(0)
                if len(state.stack)==0:
                    finalstates.add(state)
                else:
                    activelist += state.ResolveTopOfStack()
            #all untap/upkeep/draw abilities are done. make nodes for these.
            for final in finalstates:
                newnode = node.copy()
                newnode.AddToHistory("untap,upkeep,draw")
                newnode.state = final
                newnodes.add(newnode)
        #use these nodes as starting point for next turn's tracker
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
    
    


