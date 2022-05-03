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







class ActionNode():
    """
    Node. Holds a gamestate and the history of actions taken this turn to
    reach this gamestate.
    """
    
    
    def __init__(self,gamestate,history,tracker):
        self.state = gamestate
        self.history = history   #list of descriptions of arriving at this state
        self.tracker = tracker   #TurnTracker where this node should report to
            
    def __hash__(self):
        return self.state.__hash__()
    
    def __eq__(self,other):
        return self.state == other.state
        
    def __str__(self):
        return str(self.state)
    
    def PrintEvolution(self):    
        print("\n".join(self.history)+"\n"+str(self.state))
    
    
    
class TurnTracker():
    """
    Node of a tree structure that holds a gamestate, actions taken to change
    the gamestate, and the new gamestate
    """
    
    
    def __init__(self,gamestate):
        self.startnode = ActionNode(gamestate,[],None)
        self.allnodes = set()     #set of ActionNodes
        self.finalnodes = set()   #set of ActionNodes
        self.activenodes = [self.startnode]  #nodes that still need processing
        self.traverse_counter = 0
        
        
    def PlayTurn(self):
        while len(self.activenodes)>0:
            node = self.activenodes.pop(-1)  #pop the last node
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
                    newnode = ActionNode(gamestate,histlog,self)
                    self.traverse_counter += 1
                    #if node already exists, then we're done with this node
                    if newnode in self.allnodes:
                        continue #already seen this state, no need to do it again
                    #if node is new, then add it to active nodes! & track it!
                    else:
                        self.activenodes.append(newnode)
                        self.allnodes.add(newnode)

    def NodesForNextTurn(self):
        """Returns a list of nodes that are meaningfully distinct, untapped,
        and ready to go"""
        final_set = set()
        for node in self.finalnodes:
            node.history.append("untap,upkeep")
            node.state.Untap()
            node.state.Upkeep()
            final_set.add(node)
        return list(final_set)
        
            
    
    