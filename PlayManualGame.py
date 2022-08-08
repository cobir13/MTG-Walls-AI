from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from Stack import StackObject

import tkinter as tk

import RulesText  # for Creature
from GameState import GameState


class ManualGame(tk.Tk):

    def __init__(self, startstate: GameState, player_index: int):
        super().__init__()
        self.player_index: int = player_index
        self.history: List[GameState] = [startstate]
        # option to pass and allow stack to resolve. like F2 on MagicOnline
        self.var_resolveall = tk.IntVar(self, 1)
        # opponents
        self.player_frame_list = []  # frames, indexed by player_index
        for pl in self.game.player_list:
            fr = tk.Frame(self, borderwidth=1, relief="solid")
            self.player_frame_list.append(fr)
            if pl.player_index != self.player_index:
                fr.grid(row=pl.player_index, column=1,
                        padx=5, pady=5, sticky="W")
        # stack
        tk.Label(self, text="STACK", wraplength=1).grid(row=0, column=0)
        self.stack_frame = tk.Frame(self, borderwidth=1, relief="solid")
        self.stack_frame.grid(row=len(self.player_frame_list), column=1,
                              padx=5, pady=5, sticky="W")
        # main player
        fr = self.player_frame_list[self.player_index]
        fr.grid(row=len(self.player_frame_list) + 1, column=1,
                padx=5, pady=5, sticky="W")
        # populate the display and start the game
        self.rebuild_display()
        self.mainloop()

    @property
    def game(self):
        assert (not isinstance(self.history[-1], str))
        return self.history[-1]

    @property
    def player(self):
        return game.player_list[self.player_index]

    def _caster(self, options: List[StackObject]):
        chosen = Choices.choose_exactly_one(options, "choose to activate",
                                            self.player.decision_maker)
        if len(chosen) == 0:
            return  # no valid choice, so just pass
        elif len(chosen) == 1:
            self._put_on_stack(chosen[0])
        else:
            assert False  # problem!

    def _put_on_stack(self, stack_obj: StackObject):
        universes = stack_obj.put_on_stack(self.game)
        if len(universes) == 0:
            return  # casting failed, nothing changed so do nothing
        assert (len(universes) == 1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.empty_entire_stack()
        else:
            self.rebuild_display()

    def build_player_display(self, player):
        # clear previous
        for widgets in self.stack_frame.winfo_children():
            widgets.destroy()
        self_frame = self.player_frame_list[player.player_index]
        # status zone for life, mana, etc
        status_frame = tk.Frame(self_frame, borderwidth=1, relief="solid")
        status_frame.grid(row=0, rowspan=3, column=0, padx=5, pady=5)
        tk.Label(status_frame, text="Turn:\n%i" % player.turn_count,
                 ).grid(row=0, column=1, rowspan=2, padx=5, pady=5)
        tk.Label(status_frame, text="Life total: %i" % player.life
                 ).grid(row=1, column=1, padx=5, pady=2)
        tk.Label(status_frame, text="Cards in deck: %i" % len(player.deck)
                 ).grid(row=2, column=1, padx=5, pady=2)
        tk.Label(status_frame, text="Cards in grave: %i" % len(player.grave)
                 ).grid(row=3, column=1, padx=5, pady=2)
        if str(player.pool) != "":
            manastr = "Mana floating: (%s)" % str(player.pool)
        else:
            manastr = "Mana floating: None"
        tk.Label(status_frame, text=manastr
                 ).grid(row=4, column=1, padx=5, pady=2)
        tk.Label(status_frame,
                 text="Land drops left: %i" % player.land_drops_left
                 ).grid(row=5, column=1, padx=5, pady=2)
        # field
        field_frame = tk.Frame(self_frame, borderwidth=1, relief="solid")
        field_frame.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(field_frame, text="FIELD", wraplength=1).grid(row=0, column=0,
                                                               rowspan=2)
        toprow = 0  # number in bottom row
        botrow = 0  # number in top row
        for ii, card in enumerate(player.field):
            butt = card.build_tk_display(field_frame)
            # add option for user to activate abilities, if is human player.
            if player.player_index == self.player_index:
                opts = []
                for ab in card.get_activated():
                    opts += ab.valid_stack_objects(player.gamestate,
                                                   player.player_index, card)
                if len(opts) >= 1:
                    cast_fn = lambda options=opts: self._caster(options)
                    butt.config(state="normal", command=cast_fn)
                else:
                    butt.config(state="disabled")
            if card.has_type(RulesText.Creature):
                butt.grid(row=1, column=toprow, padx=5, pady=3)
                toprow += 1
            else:
                butt.grid(row=2, column=botrow, padx=5, pady=3)
                botrow += 1
        # hand
        hand_frame = tk.Frame(self_frame, borderwidth=1, relief="solid")
        hand_frame.grid(row=0, column=3, padx=5, pady=5)
        tk.Label(field_frame, text="HAND", wraplength=1).grid(row=0, column=0)
        for ii, card in enumerate(player.hand):
            butt = card.build_tk_display(hand_frame)
            # add option for user to activate abilities, if is human player.
            if player.player_index == self.player_index:
                opts = []
                for ab in card.get_activated():
                    opts += ab.valid_stack_objects(player.gamestate,
                                                   player.player_index, card)
                opts += card.valid_stack_objects(player.gamestate)  # cast card
                if len(opts) >= 1:
                    cast_fn = lambda options=opts: self._caster(options)
                    butt.config(state="normal", command=cast_fn)
                else:
                    butt.config(state="disabled")
            butt.grid(row=1, column=ii, padx=5, pady=3)

    def build_stack_display(self):
        # clear previous
        for widgets in self.stack_frame.winfo_children():
            widgets.destroy()
        # button to do the next thing
        if len(self.game.stack) == 0:
            b = tk.Button(self.stack_frame, text="Pass\nturn", bg="yellow",
                          width=7, command=self.PassTurn)
            b.grid(row=1, column=0, padx=5, pady=5)
        else:
            b = tk.Button(self.stack_frame, text="Resolve\nnext", bg="yellow",
                          width=7, command=self.resolve_top_of_stack)
            b.grid(row=1, column=0, padx=5, pady=2)
        # undo button
        b2 = tk.Button(self.stack_frame, text="undo", bg="yellow",
                       command=self.undo_action)
        b2.grid(row=1, column=1, padx=5, pady=2)
        # auto-resolve button
        b3 = tk.Checkbutton(self.stack_frame, text="Auto-resolve all",
                            variable=self.var_resolveall, indicatoron=True)
        b3.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        # show the items on the stack
        for widgets in self.stack_frame.winfo_children():
            widgets.destroy()
        for ii, obj in enumerate(self.game.stack):
            butt = obj.build_tk_display(self.stack_frame)
            butt.config(command=self.resolve_top_of_stack)
            butt.grid(row=1, column=ii+5, padx=5, pady=3, rowspan=2)

    def rebuild_display(self):
        self.build_stack_display()
        for player in self.game.player_list:
            self.build_player_display(player)

    def undo_action(self):
        if len(self.history) > 1:
            self.history.pop(-1)  # delete last gamestate from history list
            self.rebuild_display()

    def resolve_top_of_stack(self):
        if len(self.game.stack) == 0:
            return  # nothing to resolve, so don't change anything
        universes = self.game.resolve_top_of_stack()
        # if len(universes)==0:
        #     return #nothing changed so do nothing
        assert (len(universes) == 1)
        self.history.append(universes[0])
        if self.var_resolveall.get():
            self.empty_entire_stack()
        else:
            self.rebuild_display()

    def empty_entire_stack(self):
        while len(self.game.stack) > 0:
            universes = self.game.resolve_top_of_stack()
            # if len(universes)==0:
            #     return #nothing changed so do nothing
            assert (len(universes) == 1)
            self.history.append(universes[0])
        self.rebuild_display()

    def PassTurn(self):
        newstate = self.game.copy()
        newstate.UntapStep()
        newstate.UpkeepStep()
        newstate.step_draw()  # should clear super_stack FIRST? but whatever
        # clear the super stack, then clear the normal stack
        activelist = newstate.ClearSuperStack()
        finalstates = set()
        while len(activelist) > 0:
            state = activelist.pop(0)
            if len(state.stack) == 0:
                finalstates.add(state)
            else:
                activelist += state.resolve_top_of_stack()
        # all untap/upkeep/draw abilities are done
        assert (len(finalstates) == 1)
        self.history.append(finalstates.pop())
        self.rebuild_display()


if __name__ == "__main__":
    print("testing ManualGame...")
    import Decklist
    import Choices
    import Cardboard
    import Zone

    Choices.AUTOMATION = False

    game = GameState(1)
    game.give_to(Cardboard.Cardboard(Decklist.Forest()), ZONE.FIELD)
    game.give_to(Cardboard.Cardboard(Decklist.Caretaker()), ZONE.FIELD)

    game.give_to(Cardboard.Cardboard(Decklist.Forest()), ZONE.HAND)
    game.give_to(Cardboard.Cardboard(Decklist.Forest()), ZONE.HAND)
    game.give_to(Cardboard.Cardboard(Decklist.Roots()), ZONE.HAND)
    game.give_to(Cardboard.Cardboard(Decklist.Battlement()), ZONE.HAND)
    game.give_to(Cardboard.Cardboard(Decklist.Company()), ZONE.HAND)

    for _ in range(5):
        game.give_to(Cardboard.Cardboard(Decklist.Blossoms()), ZONE.DECK)
    for _ in range(5):
        game.give_to(Cardboard.Cardboard(Decklist.Omens()), ZONE.DECK)
        game.give_to(Cardboard.Cardboard(Decklist.Forest()), ZONE.DECK)
        game.give_to(Cardboard.Cardboard(Decklist.Battlement()), ZONE.DECK)

    # window = tk.Tk()

    # Choices.SelecterGUI(game.hand,"test chooser GUI",1,False)

    # window.mainloop()

    game.UntapStep()
    game.UpkeepStep()
    gui = ManualGame(game)
