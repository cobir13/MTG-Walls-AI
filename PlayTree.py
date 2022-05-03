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
    Node of a tree structure that holds a gamestate, actions taken to change
    the gamestate, and the new gamestate
    """
    
    
    def __init__(self,gamestate,recorder):
        self.state = gamestate
        self.moveresults = []  #list of (action,PlayTree node)
        self.recorder = recorder #TurnResult where leaves are recorded into
        
    def TakeNextAction(self,recurse=True):
        for option in self.state.GetValidActions():
            description = option.name
            universes = option.Run()  #list of GameState,Cardboard pairs
            for gamestate,_ in universes: 
                node = ActionNode(gamestate,self)
                self.moveresults.append((description,node))
                if recurse:
                    node.TakeNextAction(recurse)

    def Flatten(self):
        pass
    
    
    def PrintNicely(self):
        #say own state
        s = str(self.state)
        #then add nodes with an indentation
        for descrip,node in self.moveresults:
            s += "\n|\n|---------%s-------" %str(descrip)
            s += "\n|  "
            s += node.PrintNicely().replace("\n","\n|  ")
        return s
            
    
    
    
    



class TurnResult():
    """
    Node of a tree structure that holds a gamestate, actions taken to change
    the gamestate, and the new gamestate
    """
    
    
    def __init__(self,gamestate):
        self.rootnode = ActionNode(gamestate,None)
        self.turnends = []  #list of (actions,PlayTree node)
        

    def PlayTurn(self):
        pass




    def Flatten(self):
        pass
    
    
    def PrintNicely(self):
        #say own state
        s = str(self.state)
        #then add nodes with an indentation
        for descrip,node in self.moveresults:
            s += "\n|\n|---------%s-------" %str(descrip)
            s += "\n|  "
            s += node.PrintNicely().replace("\n","\n|  ")
        return s
            
    
    