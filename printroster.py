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
            elif rosterdat.ix[i,d] == 'PT':
                rosterdat.ix[i,d] = 'XP'
            elif rosterdat.ix[i,d] == '471':
                rosterdat.ix[i,d] = 'RN'
            elif rosterdat.ix[i,d] == '550 AM':
                rosterdat.ix[i,d] = 'RS'
            elif rosterdat.ix[i,d] == '600':
                rosterdat.ix[i,d] = 'TIO'
            elif rosterdat.ix[i,d] == 'MGT':
                rosterdat.ix[i,d] = 'MG'
            elif rosterdat.ix[i,d] == '0630 AM 265':
                rosterdat.ix[i,d] = 'SSA'
            elif rosterdat.ix[i,d] == '1430 PM 265':
                rosterdat.ix[i,d] = 'SSP'
            elif rosterdat.ix[i,d] == '2230 NS 265':
                rosterdat.ix[i,d] = 'SSN'
            elif rosterdat.ix[i,d] == 'RL':
                rosterdat.ix[i,d] = 'XL1'
            elif rosterdat.ix[i,d] == 'PL':
                rosterdat.ix[i,d] = 'XL2'
            elif rosterdat.ix[i,d] == 'MAT LEAVE':
                rosterdat.ix[i,d] = 'XL3'
            elif rosterdat.ix[i,d] == 'Pat leave':
                rosterdat.ix[i,d] = 'XL4'
            elif rosterdat.ix[i,d] == 'OSTT':
                rosterdat.ix[i,d] = 'OC1'
            elif rosterdat.ix[i,d] == 'I/P SOCIT':
                rosterdat.ix[i,d] = 'ISO1'
            elif rosterdat.ix[i,d] == 'ISO NFK':
                rosterdat.ix[i,d] = 'ISO2'
            else:
                rosterdat.ix[i,d] = '???'

    return rosterdat
