# ViPER: Victoria Police Electronic Rostering
# Copyright 2017, Peter van den Berg

# Project Monk: SOCIT Fawkner
# This file implements a function [cleanroster] that processes the printroster for use as an input into the solve function

def cleanroster(rosterdat):

    print rosterdat
    for i in rosterdat.index:
        print i
        if rosterdat.ix[i,'d1'] == 'R/D':
            rosterdat.ix[i,'d1'] = 'XR'

    return rosterdat
