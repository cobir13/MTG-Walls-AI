# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""


import itertools
# import tkinter.filedialog
import tkinter as tk


AUTOMATION = True

class AbortChoiceError(Exception):
    pass


def ChooseExactlyOne(options,sourcename="Choose from:"):
    """
    Given a list of options, return a list of ways to choose exactly one of
        those options.
    Either automated (give all possibilities) or user-controlled (give only
        one possibility).
    Either way, returns a list of selections. Each selection is a single one
        of the given options.
    NOTE: if each option is a tuple, the entire tuple will be returned as a
        selection. However, in user-controlled mode, only the last element of
        the tuple will be shown to the user. This allows the code to pass a
        tuple of (backend info, user-viewable info).
    """
    assert(len(options)>0)
    if AUTOMATION:
        return options
    else:
        if len(options)==1:
            return options
        return SelecterGUI(options,sourcename,1,False)


def ChooseExactlyN(options,N, sourcename="Choose from:"):
    """
    Given a list of options, return a list of ways to choose exactly N of
        those options.
    Either automated (give all possibilities, including the empty list) or
        user-controlled (give only one possibility).
    Either way, returns a list of selections, each of which is a tuple
        containing N options from the list.
    NOTE: it may not be possible to choose N options. For example, you
        cannot select 5 elements from a list of 3.  In that case, it will
        return selections of the maximal possible length.
    NOTE: if each option is a tuple, the entire tuple will be returned as a
        selection. However, in user-controlled mode, only the last element of
        the tuple will be shown to the user. This allows the code to pass a
        tuple of (backend info, user-viewable info).
    """
    if AUTOMATION:
        if N>len(options):
            N = len(options)
        return list(itertools.combinations(options,N)) #exactly N only
    else:
        if len(options)==0:
            return [ () ]
        elif len(options)==1:
            return options
        else:
            return [ tuple(SelecterGUI(options,sourcename,N,False)) ]
    

def ChooseNOrFewer(options,N,sourcename="Choose from:"):
    """
    Given a list of options, return a list of ways to choose up to N of
        those options.
    Either automated (give all possibilities, including the empty list) or
        user-controlled (give only one possibility).
    Either way, returns a list of selections, each of which is a tuple
        containing N or fewer options from the list.
    NOTE: if each option is a tuple, the entire tuple will be returned as a
        selection. However, in user-controlled mode, only the last element of
        the tuple will be shown to the user. This allows the code to pass a
        tuple of (backend info, user-viewable info).
    """
    if AUTOMATION:
        #get all tuples with N things. Then also all tuples with N-1.
        #Enforce that N can never be larger than number of options:
        if N>len(options):
            return ChooseNOrFewer(options,len(options))
        #base case: N==0. Return empty tuple
        if N==0:
            return [ () ]
        #recurse: Get all pairs of size exactly N, plus all shorter pairs
        exactlyN = list(itertools.combinations(options,N))
        return exactlyN + ChooseNOrFewer(options,N-1)
    else:
        if len(options)==0:
            return [ () ]
        return [ tuple(SelecterGUI(options,sourcename,N,True)) ]
    
    
        
    
def SelecterGUI(options,name,numtoselect,canbeless):
    """
    Makes a pop-up window to allow the user to select from a list of options.
    `name` CURRENTLY DOES NOTHING, BUT EVENTUALLY defines pop-up title.
    `numtoselect` defines the maximum number of options the user can choose.
    `canbeless` controls whether the user must choose exactly `numtoselect` or
        whether they can choose fewer options.
    Returns: a list of selected elements from `options`.
    NOTE: if each option is a tuple, the entire tuple will be returned as a
        selection. However, in user-controlled mode, only the last element of
        the tuple will be shown to the user. This allows the code to pass a
        tuple of (backend info, user-viewable info).
    """
    assert(not (not canbeless and len(options)<numtoselect))
    #make a floating display window
    disp = tk.Toplevel()  
    #lists of buttons, frames (for highlight effect), and "is selected" bools.
    buttlist  = [None]*len(options)
    framelist = [None]*len(options)
    selected  = [False]*len(options)
    #label saying how many are left for the user to select
    instr = "Choose %s %i" %("up to" if canbeless else "exactly",numtoselect)
    textvar = tk.StringVar()
    textvar.set("%s: %i remaining" %(instr,numtoselect-sum(selected)))
    l = tk.Label(disp,textvariable=textvar)
    l.grid(row=0,column=0,columnspan=20)
    #build the toggle function. each button will call this function, later.
    def toggle(index):
        if sum(selected) >= numtoselect and not selected[index]:
            return #user cannot select this option, too many already selected
        selected[index] = not selected[index] #toggle between True and False
        #make everything match: green if selected, grey if not, pink if can't
        unselcolor = "lightgrey" if sum(selected)<numtoselect else "pink"
        for jj in range(len(options)):
            framelist[jj].config( bg = "green" if selected[jj] else unselcolor)
            textvar.set("%s: %i remaining" %(instr,numtoselect-sum(selected)))
    #add buttons (and highlight-frames) for each of the options
    for ii,obj in enumerate(options):
        if isinstance(obj,tuple):
            obj = obj[-1]
        frame = tk.Frame(disp,borderwidth=0,background="lightgrey")
        frame.grid(row=1,column=ii,padx=2,pady=2)
        framelist[ii] = frame
        if hasattr(obj,"TkDisplay"):
            butt = obj.build_tk_display(frame)
        else:
            butt = tk.Button(frame,text=str(obj),height=7,width=10,
                              wraplength=80,padx=2,pady=2,
                              relief="solid",bg="lightgray")
        butt.config(command = lambda index=ii: toggle(index) )
        butt.grid(padx=10,pady=10)
        buttlist[ii] = butt
    #add an "accept" button
    def accept():
        numchosen = len([f for f in framelist if f.cget("bg")=="green"])
        if (not canbeless) and numchosen == numtoselect:
            disp.destroy()  #we have exactly correct number of selections
        if canbeless and numchosen <= numtoselect:
            disp.destroy()  #we have a permitted number of selections
    b = tk.Button(disp,text="ACCEPT",bg="green",command=accept,width=20,height=2)
    b.grid(row=20,columnspan=20) #very bottom
    #hitting "X" to close the window abandons the choice early
    def giveup():
        disp.destroy()
        raise AbortChoiceError
    disp.protocol("WM_DELETE_WINDOW",giveup)
    #run the GUI window
    disp.grab_set()
    disp.wait_window() #code hangs here until user accepts 
    #get the user's choices
    chosen = [options[jno[0]] for jno in enumerate(selected) if jno[1]]
    return chosen







if __name__ == "__main__":
    print("testing Choices...")
    
    opts = ["a","b","c","d"]
    
    w = tk.Tk()
    res = SelecterGUI(opts,"choose a number",2,canbeless=False)
    print(res)
    w.destroy()
    
    # print( ChooseNOrFewer(opts,2) )