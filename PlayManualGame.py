from __future__ import annotations
import tkinter as tk
from Verbs import WinTheGameError, LoseTheGameError
import RulesText  # for Creature
from GameState import GameState


class ManualGame(tk.Tk):

    def __init__(self, startstate):
        super().__init__()
        self.history = [startstate]
        # if you win or lose, game raises an error
        self.report_callback_exception = self.HandleError
        # option to pass and allow stack to resolve. like F2 on MagicOnline
        self.var_resolveall = tk.IntVar(self, 1)
        # stack
        tk.Label(self, text="STACK", wraplength=1).grid(row=0, column=0)
        self.stack = tk.Frame(self, borderwidth=1, relief="solid")
        self.stack.grid(row=0, column=1, padx=5, pady=5, sticky="W")
        # current situation
        tk.Label(self, text="STATE", wraplength=1).grid(row=1, column=0)
        self.status = tk.Frame(self, borderwidth=1, relief="solid")
        self.status.grid(row=1, column=1, padx=5, pady=5, sticky="W")
        # battlefield
        tk.Label(self, text="FIELD", wraplength=1).grid(row=2, column=0)
        self.field = tk.Frame(self, bg="lightgray", borderwidth=1,
                              relief="solid")
        self.field.grid(row=2, column=1, padx=5, pady=15, sticky="W")
        # hand
        tk.Label(self, text="HAND", wraplength=1).grid(row=3, column=0)
        self.hand = tk.Frame(self, borderwidth=1, relief="solid")
        self.hand.grid(row=3, column=1, padx=5, pady=5, sticky="W")
        # populate the display and start the game
        self.RebuildDisplay()
        self.mainloop()

    @property
    def game(self):
        assert (not isinstance(self.history[-1], str))
        return self.history[-1]

    def RebuildStack(self):
        for widgets in self.stack.winfo_children():
            widgets.destroy()
        for ii, obj in enumerate(self.game.stack):
            butt = obj.build_tk_display(self.stack)
            butt.config(command=self.ResolveTopOfStack)
            butt.grid(row=1, column=ii, padx=5, pady=3)

    def RebuildStatus(self):
        for widgets in self.status.winfo_children():
            widgets.destroy()
        # turn count
        tk.Label(self.status, text="Turn:\n%i" % self.game.turn_count,
                 ).grid(row=1, column=1, rowspan=2, padx=5, pady=5)
        # life totals
        tk.Label(self.status, text="Life total: %i" % self.game.life
                 ).grid(row=1, column=2, padx=5, pady=2)
        tk.Label(self.status, text="Opponent: %i" % self.game.opponent_life
                 ).grid(row=2, column=2, padx=5, pady=2)
        # cards remaining
        tk.Label(self.status, text="Cards in deck: %i" % len(self.game.deck)
                 ).grid(row=1, column=3, padx=5, pady=2)
        tk.Label(self.status, text="Cards in grave: %i" % len(self.game.grave)
                 ).grid(row=2, column=3, padx=5, pady=2)
        # mana and land-drops
        if str(self.game.pool) != "":
            manastr = "Mana floating: (%s)" % str(self.game.pool)
        else:
            manastr = "Mana floating: None"
        landstr = "Played land: %s" % (
            "yes" if self.game.has_played_land else "no")
        tk.Label(self.status, text=manastr
                 ).grid(row=1, column=4, padx=5, pady=2)
        tk.Label(self.status, text=landstr
                 ).grid(row=2, column=4, padx=5, pady=2)
        # button to do the next thing
        if len(self.game.stack) == 0:
            b = tk.Button(self.status, text="Pass\nturn", bg="yellow", width=7,
                          command=self.PassTurn)
            b.grid(row=1, column=5, padx=5, pady=5)
        else:
            b = tk.Button(self.status, text="Resolve\nnext", bg="yellow",
                          width=7,
                          command=self.ResolveTopOfStack)
            b.grid(row=1, column=5, padx=5, pady=2)
        # undo button
        b2 = tk.Button(self.status, text="undo", bg="yellow",
                       command=self.Undo)
        b2.grid(row=1, column=6, padx=5, pady=2)
        # auto-resolve button
        b3 = tk.Checkbutton(self.status, text="Auto-resolve all",
                            variable=self.var_resolveall,
                            indicatoron=True)
        # onvalue=1,background='grey')#,selectcolor='green')
        b3.grid(row=2, column=5, columnspan=2, padx=5, pady=5)

    def RebuildHand(self):
        for widgets in self.hand.winfo_children():
            widgets.destroy()
        for ii, card in enumerate(self.game.hand):
            butt = card.build_tk_display(self.hand)
            abils = [a for a in card.get_activated()
                     if a.CanAfford(self.game, card)]
            # activated abilities in hand are not yet implemented
            assert (len(abils) == 0)
            if card.rules_text.CanAfford(self.game, card):
                butt.config(state="normal",
                            command=lambda c=card: self.CastSpell(c))
            else:
                butt.config(state="disabled")
            butt.grid(row=1, column=ii, padx=5, pady=3)

    def RebuildField(self):
        for widgets in self.field.winfo_children():
            widgets.destroy()
        toprow = 0  # number in bottom row
        botrow = 0  # number in top row
        for card in self.game.field:
            butt = card.build_tk_display(self.field)
            # make the button activate this card's abilities
            abils = [a for a in card.get_activated() if
                     a.CanAfford(self.game, card)]
            if len(abils) == 0:
                butt.config(state="disabled")  # nothing to activate
            elif len(abils) == 1:
                command = lambda c=card, a=abils[0]: self.ActivateAbility(c, a)
                butt.config(state="normal", command=command)
            else:  # len(abils)>1:
                # ask the user which one to use
                print("ask the user which ability to use, I guess")
            # add card-button to the GUI. Lands on bottom, cards on top
            if card.has_type(RulesText.Creature):
                butt.grid(row=1, column=toprow, padx=5, pady=3)
                toprow += 1
            else:
                butt.grid(row=2, column=botrow, padx=5, pady=3)
                botrow += 1

    def RebuildDisplay(self):
        self.RebuildStack()
        self.RebuildStatus()
        self.RebuildField()
        self.RebuildHand()

    def Undo(self):
        if len(self.history) > 1:
            self.history.pop(-1)  # delete last gamestate from history list
            self.RebuildDisplay()

    def CastSpell(self, spell):
        universes = self.game.CastSpell(spell)
        if len(universes) == 0:
            return  # casting failed, nothing changed so do nothing
        assert (len(universes) == 1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.EmptyEntireStack()
        else:
            self.RebuildDisplay()

    def ActivateAbility(self, source, ability):
        universes = self.game.ActivateAbilities(source, ability)
        if len(universes) == 0:
            return  # activation failed, nothing changed so do nothing
        assert (len(universes) == 1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.EmptyEntireStack()
        else:
            self.RebuildDisplay()

    def ResolveTopOfStack(self):
        if len(self.game.stack) == 0:
            return  # nothing to resolve, so don't change anything
        universes = self.game.ResolveTopOfStack()
        # if len(universes)==0:
        #     return #nothing changed so do nothing
        assert (len(universes) == 1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.EmptyEntireStack()
        else:
            self.RebuildDisplay()

    def EmptyEntireStack(self):
        while len(self.game.stack) > 0:
            universes = self.game.ResolveTopOfStack()
            # if len(universes)==0:
            #     return #nothing changed so do nothing
            assert (len(universes) == 1)
            self.history.append(universes[0])
        self.RebuildDisplay()

    def PassTurn(self):
        newstate = self.game.copy()
        newstate.UntapStep()
        newstate.UpkeepStep()
        newstate.step_draw()  # technically should clear super_stack FIRST but whatever
        # clear the super stack, then clear the normal stack
        activelist = newstate.ClearSuperStack()
        finalstates = set()
        while len(activelist) > 0:
            state = activelist.pop(0)
            if len(state.stack) == 0:
                finalstates.add(state)
            else:
                activelist += state.ResolveTopOfStack()
        # all untap/upkeep/draw abilities are done
        assert (len(finalstates) == 1)
        self.history.append(finalstates.pop())
        self.RebuildDisplay()

    def HandleError(self, exc, val, tb, *args):
        """overwrite tkinter's usual error-handling routine if it's something
        I care about (like winning or losing the game)
        exc is the error type (it is of class 'type')
        val is the error itself (it is some subclass of Exception)
        tb is the traceback object (it is of class 'traceback')
        See https://stackoverflow.com/questions/4770993/how-can-i-make-silent-exceptions-louder-in-tkinter
        """
        if isinstance(val, WinTheGameError):
            tk.Label(self.status, text="CONGRATS! YOU WON THE GAME!", bg="red",
                     ).grid(row=0, column=0, columnspan=10, padx=5, pady=5)
            for frame in [self.field, self.hand, self.stack, self.status]:
                for widget in frame.winfo_children():
                    if isinstance(widget, tk.Button):
                        widget.config(state="disabled")
        elif isinstance(val, LoseTheGameError):
            tk.Label(self.status, text="SORRY, YOU LOST THE GAME", bg="red",
                     ).grid(row=0, column=0, columnspan=10, padx=5, pady=5)
            for frame in [self.field, self.hand, self.stack, self.status]:
                for widget in frame.winfo_children():
                    if isinstance(widget, tk.Button):
                        widget.config(state="disabled")
        elif isinstance(val, Choices.AbortChoiceError):
            return  # just don't panic. gamestate is unchanged.
        else:
            super().report_callback_exception(exc, val, tb, *args)


if __name__ == "__main__":
    print("testing ManualGame...")
    import Decklist
    import Choices
    import Cardboard
    import ZONE

    Choices.AUTOMATION = False

    game = GameState()
    game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.FIELD)
    game.MoveZone(Cardboard.Cardboard(Decklist.Caretaker), ZONE.FIELD)

    game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Roots), ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Battlement), ZONE.HAND)
    game.MoveZone(Cardboard.Cardboard(Decklist.Company), ZONE.HAND)

    for _ in range(5):
        game.MoveZone(Cardboard.Cardboard(Decklist.Blossoms), ZONE.DECK)
    for _ in range(5):
        game.MoveZone(Cardboard.Cardboard(Decklist.Omens), ZONE.DECK)
        game.MoveZone(Cardboard.Cardboard(Decklist.Forest), ZONE.DECK)
        game.MoveZone(Cardboard.Cardboard(Decklist.Battlement), ZONE.DECK)

    # window = tk.Tk()

    # Choices.SelecterGUI(game.hand,"test chooser GUI",1,False)

    # window.mainloop()

    game.UntapStep()
    game.UpkeepStep()
    gui = ManualGame(game)
