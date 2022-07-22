# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""

from typing import List
import itertools
# import tkinter.filedialog
import tkinter as tk

AUTOMATION = True


class AbortChoiceError(Exception):
    pass


def choose_exactly_one(options, source_name: str = "Choose from:") -> list:
    """
    Given a list of options, return a list of ways to choose
        exactly one of those options. If there are no ways
        (e.g. the options-list is empty) then return [].
    Either automated (returns all possibilities) or user
        controlled (returns only one possibility).
    Either way, returns a list of selections. Each selection
        is a single one of the given options.
    NOTE: if each option is a tuple, the entire tuple will
        be returned as a selection. However, in user
        controlled mode, only the last element of  the tuple
        will be shown to the user. This allows the code to
        pass a tuple of (backend info, user-viewable info).
    """
    if AUTOMATION:
        return options
    else:
        if len(options) == 1 or len(options) == 0:
            return options
        return run_gui_to_select(options, source_name, 1, False)


def choose_exactly_n(options: list, num_to_choose: int,
                     source_name="Choose from:") -> List[tuple]:
    """
    Given a list of options, return a list of ways to choose
        exactly N of those options. If there are no ways
        (e.g. the options-list is empty) then return [].
    Either automated (returns all possibilities) or user
        controlled (returns only one possibility).
    Either way, returns a list of selections, each of which
        is a tuple containing N options from the list.
    NOTE: it may not be possible to choose N options. For
        example, you cannot select 5 elements from a list of
        3.  In that case, it will return selections of the
        maximal possible length.
    NOTE: if each option is a tuple, the entire tuple will
        be returned as a selection. However, in user-controlled
        mode, only the last element of the tuple will be
        shown to the user. This allows the code to pass a
        tuple of (backend info, user-viewable info).
    """
    if AUTOMATION:
        if num_to_choose > len(options):
            num_to_choose = len(options)
        # exactly N only
        return list(itertools.combinations(options, num_to_choose))
    else:
        if len(options) == 0:
            return [()]
        elif len(options) == 1:
            return options
        else:
            return [tuple(run_gui_to_select(options, source_name,
                                            num_to_choose, False))]
    # I should remove duplicates HERE (rather than where Choice gets used    


def choose_n_or_fewer(options: list, num_to_choose: int,
                      source_name: str = "Choose from:") -> List[tuple]:
    """
    Given a list of options, return a list of ways to choose
        up to N of those options. If there are no ways (e.g.
        the options-list is empty) then return [].
    Either automated (give all possibilities, including the
        empty list) or user-controlled (give only one
        possibility).
    Either way, returns a list of selections, each of which
        is a tuple containing N or fewer options from the
        list of options.
    NOTE: if each option is a tuple, the entire tuple will
        be returned as a selection. However, in user
        controlled mode, only the last element of the tuple
        will be shown to the user. This allows the code to
        pass a tuple of (backend info, user-viewable info).
    """
    if AUTOMATION:
        # get all tuples with N things. Then also all tuples with N-1.
        # Enforce that N can never be larger than number of options:
        if num_to_choose > len(options):
            return choose_n_or_fewer(options, len(options))
        # base case: N==0. Return empty tuple
        if num_to_choose == 0:
            return [()]
        # recurse: Get all pairs of size exactly N, plus all shorter pairs
        exactly_n = list(itertools.combinations(options, num_to_choose))
        return exactly_n + choose_n_or_fewer(options, num_to_choose - 1)
    else:
        if len(options) == 0:
            return [()]
        return [tuple(run_gui_to_select(options, source_name, num_to_choose,
                                        True))]


def run_gui_to_select(options, name, num_to_select, can_be_less):
    """
    Makes a pop-up window to allow the user to select from a
    list of options.
    `name` CURRENTLY DOES NOTHING, BUT EVENTUALLY defines
    pop-up title.
    `num_to_select` defines the maximum number of options the
    user can choose.
    `can_be_less` controls whether the user must choose
        exactly `num_to_select` or whether they can choose
        fewer options.
    Returns: a list of selected elements from `options`.
    NOTE: if each option is a tuple, the entire tuple will be
        returned as a selection. However, in user-controlled
        mode, only the last element of the tuple will be shown
        to the user. This allows the code to pass a tuple of
        (backend info, user-viewable info).
    """
    assert (not (not can_be_less and len(options) < num_to_select))
    # make a floating display window
    disp = tk.Toplevel()
    # lists of buttons, frames (for highlight effect), and "is selected" bools.
    butt_list = []
    frame_list = []
    selected = [False] * len(options)
    # label saying how many are left for the user to select
    instr = "Choose %s %i" % ("up to" if can_be_less else "exactly",
                              num_to_select)
    text_var = tk.StringVar()
    text_var.set("%s: %i remaining" % (instr, num_to_select - sum(selected)))
    tk.Label(disp, textvariable=text_var).grid(row=0, column=0, columnspan=20)

    # build the toggle function. each button will call this function, later.
    def toggle(index):
        if sum(selected) >= num_to_select and not selected[index]:
            return  # user cannot select this option, too many already selected
        selected[index] = not selected[index]  # toggle between True and False
        # make everything match: green if selected, grey if not, pink if can't
        unselcolor = "lightgrey" if sum(selected) < num_to_select else "pink"
        for jj in range(len(options)):
            frame_list[jj].config(bg="green" if selected[jj] else unselcolor)
            text_var.set(
                "%s: %i remaining" % (instr, num_to_select - sum(selected)))

    # add buttons (and highlight-frames) for each of the options
    for ii, obj in enumerate(options):
        if isinstance(obj, tuple):
            obj = obj[-1]
        frame = tk.Frame(disp, borderwidth=0, background="lightgrey")
        frame.grid(row=1, column=ii, padx=2, pady=2)
        frame_list.append(frame)
        if hasattr(obj, "TkDisplay"):
            butt = obj.build_tk_display(frame)
        else:
            butt = tk.Button(frame, text=str(obj), height=7, width=10,
                             wraplength=80, padx=2, pady=2,
                             relief="solid", bg="lightgray")
        butt.config(command=lambda index=ii: toggle(index))
        butt.grid(padx=10, pady=10)
        butt_list.append(butt)
    assert (len(butt_list) == len(options))
    assert (len(frame_list) == len(options))

    # add an "accept" button
    def accept():
        num_chosen = len([f for f in frame_list if f.cget("bg") == "green"])
        if (not can_be_less) and num_chosen == num_to_select:
            disp.destroy()  # we have exactly correct number of selections
        if can_be_less and num_chosen <= num_to_select:
            disp.destroy()  # we have a permitted number of selections

    b = tk.Button(disp, text="ACCEPT", bg="green", command=accept, width=20,
                  height=2)
    b.grid(row=20, columnspan=20)  # very bottom

    # hitting "X" to close the window abandons the choice early
    def give_up():
        disp.destroy()
        raise AbortChoiceError

    disp.protocol("WM_DELETE_WINDOW", give_up)
    # run the GUI window
    disp.grab_set()
    disp.wait_window()  # code hangs here until user accepts
    # get the user's choices
    chosen = [options[jno[0]] for jno in enumerate(selected) if jno[1]]
    return chosen


if __name__ == "__main__":
    print("testing Choices...")

    opts = ["a", "b", "c", "d"]

    w = tk.Tk()
    res = run_gui_to_select(opts, "choose a number", 2, can_be_less=False)
    print(res)
    w.destroy()

    # print( ChooseNOrFewer(opts,2) )
