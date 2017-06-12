# ViPER: Victoria Police Electronic Rostering
# Copyright 2017, Peter van den Berg

# Project Monk: SOCIT Fawkner
# This file implements a function [cleanroster] that processes the printroster for use as an input into the solve function

def cleanroster(rosterdat):

    print rosterdat
    
    for i in rosterdat.index:
        for d in range(1,7*2+1):    # 2 weeks only at this time
            if rosterdat.ix[i,d] == 'R/D':
                rosterdat.ix[i,d] = 'XR'

    return rosterdat
