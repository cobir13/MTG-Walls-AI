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
import tkinter as tk

    
    
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
            newstate.Draw()  #technically should clear superstack FIRST but whatever
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
    
    


###----------------------------------------------------------------------------


class ManualPlay(tk.Tk):
    
    def __init__(self,startstate):
        super().__init__()
        self.history = [startstate]
        self.report_callback_exception = self.HandleError
        self.var_resolveall = tk.IntVar(self,1)
        
        tk.Label(self,text="STACK",wraplength=1).grid(row=0,column=0)
        self.stack = tk.Frame(self,borderwidth=1,relief="solid")
        self.stack.grid(row=0,column=1,padx=5,pady=5,sticky="W")
        
        tk.Label(self,text="STATE",wraplength=1).grid(row=1,column=0)
        self.status = tk.Frame(self,borderwidth=1,relief="solid")
        self.status.grid(row=1,column=1,padx=5,pady=5,sticky="W")
        
        tk.Label(self,text="FIELD",wraplength=1).grid(row=2,column=0)
        self.field = tk.Frame(self,bg="lightgray",borderwidth=1,relief="solid")
        self.field.grid(row=2,column=1,padx=5,pady=15,sticky="W")
        
        tk.Label(self,text="HAND",wraplength=1).grid(row=3,column=0)
        self.hand = tk.Frame(self,borderwidth=1,relief="solid")
        self.hand.grid(row=3,column=1,padx=5,pady=5,sticky="W")

        self.RebuildDisplay()
 
        self.mainloop()
        
        
    @property
    def game(self):
        assert(not isinstance(self.history[-1],str))
        return self.history[-1]


    def RebuildStack(self):
        for widgets in self.stack.winfo_children():
            widgets.destroy()
        for ii,obj in enumerate(self.game.stack):
            butt = obj.TkDisplay(self.stack)
            butt.config(command=self.ResolveTopOfStack)
            butt.grid(row=1,column=ii,padx=5,pady=3)


    def RebuildStatus(self):
        for widgets in self.status.winfo_children():
            widgets.destroy()
        #turn count
        tk.Label(self.status,text="Turn:\n%i" %self.game.turncount,
                 ).grid(row=1,column=1,rowspan=2,padx=5,pady=5)
        #life totals
        tk.Label(self.status,text="Life total: %i" %self.game.life
                 ).grid(row=1,column=2,padx=5,pady=2)
        tk.Label(self.status,text="Opponent: %i" %self.game.opponentlife
                 ).grid(row=2,column=2,padx=5,pady=2)
        #cards remaining
        tk.Label(self.status,text="Cards in deck: %i" %len(self.game.deck)
                 ).grid(row=1,column=3,padx=5,pady=2)
        tk.Label(self.status,text="Cards in grave: %i" %len(self.game.grave)
                 ).grid(row=2,column=3,padx=5,pady=2)
        #mana and land-drops
        if str(self.game.pool) != "":
            manastr = "Mana floating: (%s)" %str(self.game.pool)
        else:
            manastr = "Mana floating: None"
        landstr = "Played land: %s" %("yes" if self.game.playedland else "no")
        tk.Label(self.status,text=manastr
                 ).grid(row=1,column=4,padx=5,pady=2)
        tk.Label(self.status,text=landstr
                 ).grid(row=2,column=4,padx=5,pady=2)
        #button to do the next thing
        if len(self.game.stack)==0:
            b = tk.Button(self.status,text="Pass\nturn",bg="yellow",
                          command = self.PassTurn)
            b.grid(row=1,column=5,padx=5,pady=5)
        else:
            b = tk.Button(self.status,text="Resolve next",bg="yellow",
                          command=self.ResolveTopOfStack)
            b.grid(row=1,column=5,padx=5,pady=2)
        b2 = tk.Checkbutton(self.status,text="Auto-resolve all",
                            variable=self.var_resolveall,indicatoron=True)#,onvalue=1,background='grey')#,selectcolor='green')
        b2.grid(row=2,column=5,padx=5,pady=5)
            
        
        
    def RebuildHand(self):
        for widgets in self.hand.winfo_children():
            widgets.destroy()
        for ii,card in enumerate(self.game.hand):
            butt = card.TkDisplay(self.hand)
            abils = [a for a in card.GetActivated() if a.CanAfford(self.game,card)]
            assert(len(abils)==0)  #activated abilities in hand not yet implemented
            if card.cardtype.CanAfford(self.game,card):
                butt.config(state="normal",
                            command = lambda c=card: self.CastSpell(c) )
            else:
                butt.config(state="disabled")
            butt.grid(row=1,column=ii,padx=5,pady=3)


    def RebuildField(self):
        for widgets in self.field.winfo_children():
            widgets.destroy()
        toprow = 0 #number in bottom row
        botrow = 0 #number in top row
        for card in self.game.field:
            butt = card.TkDisplay(self.field)
            #make the button activate this card's abilities
            abils = [a for a in card.GetActivated() if a.CanAfford(self.game,card)]
            if len(abils)==0:
                butt.config(state="disabled")  #nothing to activate
            elif len(abils)==1:
                command = lambda c=card,a=abils[0]: self.ActivateAbility(c,a)
                butt.config(state="normal", command=command)
            else: #len(abils)>1:
                #ask the user which one to use
                print("ask the user which ability to use, I guess")
            #add card-button to the GUI. Lands on bottom, cards on top
            if card.HasType(CardType.Creature):
                butt.grid(row=1,column=toprow,padx=5,pady=3)
                toprow += 1
            else:
                butt.grid(row=2,column=botrow,padx=5,pady=3)
                botrow += 1

    def RebuildDisplay(self):
        self.RebuildStack()
        self.RebuildStatus()
        self.RebuildField()
        self.RebuildHand()

    def CastSpell(self,spell):
        universes = self.game.CastSpell(spell)
        assert(len(universes)==1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.EmptyEntireStack()
        else:
            self.RebuildDisplay()
        
    def ActivateAbility(self,source,ability):
        universes = self.game.ActivateAbilities(source,ability)
        assert(len(universes)==1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.EmptyEntireStack()
        else:
            self.RebuildDisplay()
    
    def ResolveTopOfStack(self):
        if len(self.game.stack)==0:
            return  #nothing to resolve, so don't change anything
        universes = self.game.ResolveTopOfStack()
        assert(len(universes)==1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.EmptyEntireStack()
        else:
            self.RebuildDisplay()
        
    def EmptyEntireStack(self):
        while len(self.game.stack)>0:
            universes = self.game.ResolveTopOfStack()
            assert(len(universes)==1)
            self.history.append(universes[0])
        self.RebuildDisplay()
    
    def PassTurn(self):
        newstate = self.game.copy()
        newstate.UntapStep()
        newstate.UpkeepStep()
        newstate.Draw()  #technically should clear superstack FIRST but whatever
        #clear the super stack, then clear the normal stack
        activelist = newstate.ClearSuperStack()
        finalstates = set()
        while len(activelist)>0:
            state = activelist.pop(0)
            if len(state.stack)==0:
                finalstates.add(state)
            else:
                activelist += state.ResolveTopOfStack()
        #all untap/upkeep/draw abilities are done
        assert(len(finalstates)==1)
        self.history.append( finalstates.pop() )
        self.RebuildDisplay()
    
    def HandleError(self,exc, val, tb, *args):
        """overwrite tkinter's usual error-handling routine if it's something
        I care about (like a message).
        exc is the error type (it is of class 'type')
        val is the error itself (it is some subclass of Exception)
        tb is the traceback object (it is of class 'traceback')
        See https://stackoverflow.com/questions/4770993/how-can-i-make-silent-exceptions-louder-in-tkinter
        """
        if isinstance(val,GameState.WinTheGameError):
            tk.Label(self.status,text="CONGRATS! YOU WON THE GAME!",bg="red",
                     ).grid(row=0,column=0,columnspan=10,padx=5,pady=5)
            for frame in [self.field,self.hand,self.stack,self.status]:
                for widget in frame.winfo_children():
                    if isinstance(widget,tk.Button):
                        widget.config(state="disabled")           
        elif isinstance(val,GameState.LoseTheGameError):
            tk.Label(self.status,text="SORRY, YOU LOST THE GAME",bg="red",
                     ).grid(row=0,column=0,columnspan=10,padx=5,pady=5)
            for frame in [self.field,self.hand,self.stack,self.status]:
                for widget in frame.winfo_children():
                    if isinstance(widget,tk.Button):
                        widget.config(state="disabled")   
        else:
            super().report_callback_exception(exc,val,tb,*args)
                  
        
        


if __name__ == "__main__":
    print("testing ManualPlay...")

    game = GameState.GameState()
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest   ) ,ZONE.FIELD)
    game.MoveZone( Cardboard.Cardboard(Decklist.Caretaker) ,ZONE.FIELD)
    
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Forest) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Roots ) ,ZONE.HAND)
    game.MoveZone( Cardboard.Cardboard(Decklist.Battlement),ZONE.HAND)
    
    for _ in range(20):
        game.MoveZone( Cardboard.Cardboard(Decklist.Blossoms),ZONE.DECK)
    
    
    game.UntapStep()
    game.UpkeepStep()
    
    tree = ManualPlay(game)
    # tree.mainloop()
