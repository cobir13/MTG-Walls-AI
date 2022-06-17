# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:28 2020

@author: Cobi
"""


import ZONE
import CardType
import tkinter as tk




##---------------------------------------------------------------------------##

class Cardboard():
    """Represents the physical piece of cardboard that is a Magic card.
    """
    
    #needs to not overwrite equality, because I often check if a card is in
    #a list and I need the `in` functionality to use `is` rather than `==`.
    #Unfortunately, this also means I can't drop Cardboards into sets to sort.
    
    
    
    def __init__(self,cardtype):
        """cardtype: a Cardtype instance."""
        self.cardtype = cardtype
        self.tapped = False
        self.summonsick = True
        self.counters = []  #sorted list of counters. Also other trackers
        self.zone = ZONE.NEW
    


    def __str__(self):
        s = self.cardtype.name
        if self.zone == ZONE.FIELD and self.tapped:
            s += "(T)"
        if len(self.counters)>0:
            s += "[%s]" %",".join(self.counters)
        return s
    
    def __repr__(self):
        return "Card "+self.ID()
    
    def copy(self):
        newcard = Cardboard(self.cardtype)
        #safe to copy by reference since they're all ints, str, etc
        newcard.tapped    = self.tapped
        newcard.summonsick= self.summonsick
        newcard.zone      = self.zone
        #counters is a LIST so it needs to be copied carefully, without reference
        newcard.counters = self.counters.copy()
        #cardtype never mutates so it's ok that they're both pointing at the
        #same instance of a CardType
        newcard.cardtype  = self.cardtype
        return newcard
    
    def AddCounter(self,addition):
        self.counters = sorted(self.counters + [addition])
        
    @property
    def name(self):
        return self.cardtype.name

    def GetActivated(self):
        return self.cardtype.activated
    
    def ID(self):
        s = type(self.cardtype).__name__ #MtG card type (creature, land, etc)
        s += self.cardtype.name + "_"
        if self.tapped:
            s += "T"
        if self.summonsick and self.HasType(CardType.Creature):
            s += "S"
        s += str(self.zone)
        if len(self.counters)>0:
            s += "["+",".join(self.counters)+"]"
        return s
        
    def EquivTo(self,other):
        if not isinstance(other,Cardboard):
            return False
        else:
            return self.ID() == other.ID()
    
    def __eq__(self,other):
        return self is other  #pointer equality. 
        #I need "is" equality for "is Cardboard in GameState list". That needs
        #to care about same-object not just whether two cardboards are
        #equivalent or not. I defined EquivTo as a more intuitive, descriptive
        #definition of equality that I use for comparing two GameStates.
        
    def HasType(self,cardtype):
        """Returns bool: "this Cardboard refers to a card which is the given
        CardType type (in addition to possibly other types as well)" """
        return isinstance(self.cardtype,cardtype)
        
    def CMC(self):
        return self.cardtype.cost.manacost.CMC()



    def TkDisplay(self,parentframe,):
        """Returns a tkinter button representing the Cardboard.
        Note: clicking the button won't do anything yet. Setting up the button
        so that clicking it will cast the card or activate its abilities is
        the responsibility of whatever is building the GUI.
        Similarly, whatever calls this function is responsible for adding the
        button to the tkinter frame so that it actually appears on screen.
        """
        #string for mana cost (if any)
        coststr = ""
        if self.CMC()>0:
            coststr = "(" + str(self.cardtype.cost.manacost) + ")"
        #string for name
        # text += "".join([l if l.islower() else " "+l for l in self.name])[1:]
        namestr = self.name
        #string for power and toughness, if any
        ptstr = ""
        if self.HasType(CardType.Creature):
            ptstr = "%i/%i" %(self.cardtype.basepower,self.cardtype.basetoughness)    
        #string for counters, if any
        countstr = ""
        for c in set(self.counters):
            if c[0] != "@":
                countstr += "[%s]" %c
                if self.counters.count(c)>1:
                    countstr += "x%i" %self.counters.count(c)
                countstr += "\n"
        #configure text. tapped and untapped display differently
        if self.tapped:
            text = " "*(27-len(namestr)) + namestr + "\n"
            text += countstr
            while text.count("\n")<3:
                text += "\n"
            text += ptstr 
            text += " "*(30-len(ptstr)-len(coststr))
            text += coststr
        else:
            text = " "*(20-len(coststr)) + coststr + "\n"
            text += namestr + "\n"
            text += countstr
            while text.count("\n")<6:
                text += "\n"
            text += " "*(20-len(ptstr)) + ptstr
        #build the button and return it
        button = tk.Button(parentframe,
                           text=text,anchor="w",
                           height=4 if self.tapped else 7,
                           width=15 if self.tapped else 10,
                           wraplength=110 if self.tapped else 80,
                           padx=3,pady=3,
                           relief="raised",bg="lightgreen")
        return button
    
    
    
if __name__ == "__main__":
    import Decklist
    window = tk.Tk()
    frame = tk.Frame(window)
    frame.grid(padx=5,pady=5)
    
    c1 = Cardboard(Decklist.Roots)
    c1.TkDisplay(frame).grid(row=0,column=0,padx=5)
    c2 = Cardboard(Decklist.Caretaker)
    c2.TkDisplay(frame).grid(row=0,column=1,padx=5)
    
    c4 = Cardboard(Decklist.Caretaker)
    c4.tapped = True
    c4.TkDisplay(frame).grid(row=0,column=2,padx=5)
    
    
    c3 = Cardboard(Decklist.WindsweptHeath)
    c3.tapped = True
    c3.TkDisplay(frame).grid(row=0,column=3,padx=5)
    
    
    
    window.mainloop()
    