from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from Stack import StackObject

import tkinter as tk

import Zone
import Choices
import RulesText  # for Creature, maybe Land
from GameState import GameState, Player
import Decklist
import Cardboard


class ManualGame(tk.Tk):
    """THIS CLASS IS STILL UNFINISHED AND A FEW THINGS DON'T QUITE WORK."""

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
                pl.decision_maker = "try_one"
        # stack
        self.stack_frame = tk.Frame(self)
        self.stack_frame.grid(row=len(self.player_frame_list),
                              column=1, padx=5, pady=5, sticky="W")
        # main player
        fr = self.player_frame_list[self.player_index]
        fr.grid(row=len(self.player_frame_list) + 1, column=1,
                padx=5, pady=5, sticky="W")
        startstate.player_list[self.player_index].decision_maker = "manual"
        # populate the display and start the game
        self.rebuild_display()
        self.mainloop()

    @property
    def game(self):
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

    def build_player_display(self, player: Player):
        self_frame = self.player_frame_list[player.player_index]
        # clear previous
        for widgets in self_frame.winfo_children():
            widgets.destroy()
        # status zone for life, mana, etc
        color = "lightgrey"
        if player.player_index == self.game.priority_player_index:
            color = "lightgreen"
        status_frame = tk.Frame(self_frame, borderwidth=1, relief="solid",
                                bg=color)
        status_frame.grid(row=0, rowspan=3, column=0, padx=5, pady=0)
        txt = "PLAYER %i" % player.player_index
        if player.player_index == self.player_index:
            txt += " (YOU)"
        if player.player_index == self.game.active_player_index:
            txt = "THIS PLAYER'S TURN\n" + txt
        tk.Label(status_frame, text=txt, bg=color
                 ).grid(row=0, column=1, padx=5, pady=0)
        tk.Label(status_frame, text="Turn: %i" % player.turn_count, bg=color
                 ).grid(row=1, column=1, padx=5, pady=0)
        tk.Label(status_frame, text="Life total: %i" % player.life, bg=color
                 ).grid(row=2, column=1, padx=5, pady=0)
        tk.Label(status_frame, text="Cards in hand: %i" % len(player.hand),
                 bg=color).grid(row=3, column=1, padx=5, pady=0)
        tk.Label(status_frame, text="Cards in deck: %i" % len(player.deck),
                 bg=color).grid(row=4, column=1, padx=5, pady=0)
        tk.Label(status_frame, text="Cards in grave: %i" % len(player.grave),
                 bg=color).grid(row=5, column=1, padx=5, pady=0)
        if str(player.pool) != "":
            manastr = "Mana floating: (%s)" % str(player.pool)
        else:
            manastr = "Mana floating: None"
        tk.Label(status_frame, text=manastr, bg=color
                 ).grid(row=6, column=1, padx=5, pady=0)
        tk.Label(status_frame,
                 text="Land drops left: %i" % player.land_drops_left, bg=color
                 ).grid(row=7, column=1, padx=5, pady=0)
        # field
        field_frame = tk.Frame(self_frame, borderwidth=1, relief="solid",
                               height=250, width=800)
        field_frame.grid_propagate(False)  # don't resize
        field_frame.grid(row=0, column=1, padx=5, pady=3, sticky="W")
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
                    butt.config(state="disabled", disabledforeground="black",
                                bg="lightgrey")
            if card.has_type(RulesText.Creature):
                butt.grid(row=0, column=toprow+1, padx=2, pady=2, sticky="N")
                toprow += 1
            else:
                butt.grid(row=1, column=botrow+1, padx=2, pady=2, sticky="S")
                botrow += 1
        # hand
        if player.player_index == self.player_index:
            # the user-controller player:
            hand_frame = tk.Frame(self_frame, borderwidth=1, relief="solid")
            hand_frame.grid(row=1, column=1, padx=5, pady=3, sticky="W")
            tk.Label(hand_frame, text="HAND", wraplength=1).grid(row=0, column=0)
            for ii, card in enumerate(player.hand):
                butt = card.build_tk_display(hand_frame)
                # add option for user to activate abilities, if has priority
                if self.player_index == self.game.priority_player_index:
                    opts = []
                    for ab in card.get_activated():
                        opts += ab.valid_stack_objects(player.gamestate,
                                                       player.player_index,
                                                       card)
                    opts += card.valid_stack_objects(player.gamestate)  # cast
                    if len(opts) >= 1:
                        cast_fn = lambda options=opts: self._caster(options)
                        butt.config(state="normal", command=cast_fn)
                    else:
                        butt.config(state="disabled",
                                    disabledforeground="black",
                                    bg="lightgrey")
                else:
                    # not your priority, so can't do anything!
                    butt.config(state="disabled", disabledforeground="black",
                                bg="lightgrey")
                butt.grid(row=0, column=ii+1, padx=2, pady=2)

    def build_stack_display(self):
        # clear previous
        for widgets in self.stack_frame.winfo_children():
            widgets.destroy()
        # button to do the next thing
        if len(self.game.stack) == 0:
            b = tk.Button(self.stack_frame, text="Pass\nturn", bg="yellow",
                          width=7, command=self.pass_turn)
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
        obj_frame = tk.Frame(self.stack_frame, borderwidth=1, relief="solid",
                             height=120, width=800)
        obj_frame.grid(row=0, rowspan=5, column=5, padx=5, pady=3, sticky="EW")
        tk.Label(obj_frame, text="STACK", wraplength=1).grid(row=0, column=0)
        for ii, obj in enumerate(self.game.stack):
            butt = obj.build_tk_display(obj_frame)
            butt.config(command=self.resolve_top_of_stack)
            butt.grid(row=0, column=ii+5, padx=5, pady=3, rowspan=2)

    def rebuild_display(self):
        for player in self.game.player_list:
            self.build_player_display(player)
        self.build_stack_display()

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

    def pass_turn(self):
        newstate = self.game.copy()
        newstate.pass_turn()
        newstate.step_untap()
        newstate.step_upkeep()
        newstate.step_draw()  # should clear super_stack FIRST? but whatever
        # clear the super stack, then clear the normal stack
        activelist = newstate.clear_super_stack()
        finalstates = set()
        while len(activelist) > 0:
            state = activelist.pop(0)
            if len(state.stack) == 0:
                finalstates.add(state)
            else:
                activelist += state.resolve_top_of_stack()
        # all untap/upkeep/draw abilities are done
        assert (len(finalstates) == 1)
        self.history.append(finalstates.pop())  # use this state
        self.rebuild_display()


if __name__ == "__main__":
    print("testing ManualGame...")

    game = GameState(2)

    # player1 has entirely mountains. 3 in hand, 30 in deck.
    for _ in range(30):
        game.give_to(Cardboard.Cardboard(Decklist.Mountain()), Zone.DeckTop, 1)
    for _ in range(3):
        game.give_to(Cardboard.Cardboard(Decklist.Mountain()), Zone.Hand, 1)

    # player0 is playing Walls
    game.give_to(Cardboard.Cardboard(Decklist.Forest()), Zone.Hand, 0)
    game.give_to(Cardboard.Cardboard(Decklist.Caretaker()), Zone.Hand, 0)
    game.give_to(Cardboard.Cardboard(Decklist.Forest()), Zone.Hand, 0)
    game.give_to(Cardboard.Cardboard(Decklist.Forest()), Zone.Hand, 0)
    game.give_to(Cardboard.Cardboard(Decklist.Roots()), Zone.Hand, 0)
    game.give_to(Cardboard.Cardboard(Decklist.Battlement()), Zone.Hand, 0)
    game.give_to(Cardboard.Cardboard(Decklist.Company()), Zone.Hand, 0)

    for _ in range(5):
        game.give_to(Cardboard.Cardboard(Decklist.Omens()), Zone.DeckTop, 0)
        game.give_to(Cardboard.Cardboard(Decklist.Forest()), Zone.DeckTop, 0)
        game.give_to(Cardboard.Cardboard(Decklist.Battlement()),
                     Zone.DeckTop, 0)
    for _ in range(5):
        game.give_to(Cardboard.Cardboard(Decklist.Blossoms()), Zone.DeckTop, 0)

    gui = ManualGame(game, 0)
