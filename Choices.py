# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 21:13:59 2020

@author: Cobi
"""


import itertools
# import tkinter.filedialog


AUTOMATION = True


def ChooseExactlyOne(options):
    """given a list of options, return a list of ways to choose exactly one of
    those options. Either automated (give all possibilities) or user-controlled
    (give only one possibility).  Either way, returns a list of selections,
    each of which is a single one of the given options."""
    if AUTOMATION:
        return options
    else:
        return options[:1]
       
    
# def ChooseUpToN(options,N):
#     """Given a list of options, returns a list of choices. Each choice is a
#     tuple containing N or fewer distinct items from the options list.
#     Note that the empty tuple will always be returned"""
#     if AUTOMATION:
#         #get all tuples with N things. Then also all tuples with N-1.
#         #Enforce that N can never be larger than number of options:
#         if N>len(options):
#             return ChooseUpToN(options,len(options))
#         #base case: N=0
        
        
        
        
        
        
        
        
#         #base case: no options or we want to choose 0 from the list
#         if len(options)==0:
#             return [ [] ]
#         if N<=0:
#             return [ [] ]
#         #recurse: pop one option
#         results = []
#         for index,opt in enumerate(options):
#             #


#     #base case: no items on superstack
#     if len(self.superstack)==0:
#         return [self]
#     results = []
#     #move one item from superstack onto stack.
#     for ii in range(len(self.superstack)):
#         newstate = self.copy()
#         effect = newstate.superstack.pop(ii)
#         if isinstance(effect.ability,AsEnterEffect):
#             #if the StackEffect contains an AsEntersEffect, then enact
#             #it immediately rather than putting it on the stack.
#             results += effect.Enact(newstate)
#         else:
#             newstate.stack.append(effect)
#             results.append(newstate)
#     #recurse
#     finalresults = []
#     for state in results:
#         finalresults += state.ClearSuperStack()
#     return finalresults