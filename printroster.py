# ViPER: Victoria Police Electronic Rostering
# Copyright 2017, Peter van den Berg

# Project Monk: SOCIT Fawkner
# This file implements a function [cleanroster] that processes the printroster for use as an input into the solve function

def cleanroster(rosterdat):

    print rosterdat
    for i in rosterdat:
        if rosterdat['d1] == 'R/D':
            rosterdat['d1'] = 'XR'

    return rosterdat
