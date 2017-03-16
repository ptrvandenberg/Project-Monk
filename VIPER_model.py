# VIPER: VIctoria Police Electronic Rostering
# Copyright 2017, Peter van den Berg

# Project Monk: SOCAU Fawkner
# This file implements a function [solve] that formulates and solves the model as well as codifies the resulting roster

# Import dependencies
from pandas import ExcelFile
from pulp import LpVariable, lpSum, LpProblem, LpMaximize, LpInteger, LpBinary, LpStatus, value

# Validate input data (including keys, data types)
def validate_input(dat):
    rtn = {}
    
    # Input test 0: Settings

    # nbr_roster_weeks
    if 'nbr_roster_weeks' not in (param for param in dat.parse('settings')['parameter']):
        rtn['Test 0 - Setting / Weeks'] = 'parameter missing'
    elif dat.parse('settings', index_col = 'parameter').loc['nbr_roster_weeks', 'value'] <= 0:
        rtn['Test 0 - Setting / Weeks'] = 'value <= 0'
    elif dat.parse('settings', index_col = 'parameter').loc['nbr_roster_weeks', 'value'] % 1 <> 0:
        rtn["Test 0 - Setting / Weeks"] = 'value not integer'
        
    return rtn
    
def solve(dat):

    invalid_input = validate_input(dat)
    assert not invalid_input, invalid_input

    # Parse input data
    settings = dat.parse('settings')
    settings = settings.set_index('parameter')
    
    members = dat.parse('members')
    members = members.set_index('memid')

    days = dat.parse('days')
    days = days.set_index('dayseq')
    
    shifts = dat.parse('shifts')
    shifts = shifts.set_index('shiftcd')
    
    shiftdates = dat.parse('shiftdates')
    shiftdates = shiftdates.set_index('shiftcd')
    
    carryover = dat.parse('carryover')
    carryover = carryover.set_index('memid')

    longshift = dat.parse('longshift')
    longshift = longshift.set_index(['memid','week'])
    
    shortshift = dat.parse('shortshift')
    shortshift = shortshift.set_index('memid')

    restricted = dat.parse('restricted')
    restricted = restricted.set_index(['memid','dayseq','shiftcd'])
    
    # Commence model definition and set optimisation direction
    model = LpProblem("roster", LpMaximize)
    
    # Create and define the problem variables
    x = LpVariable.dicts("rostered", (members, days), 0, 1, LpBinary)
    
    # Create and define the additional variables
    
    # Set the objective
#    model += ...
    
    # STRUCTURAL CONSTRAINTS
#    model += ...
    
    # INPUT CONSTRAINTS
    
    # Assign shifts based on the Committed input
    
    # Restrict shifts based on the Restricted input
    
    # BASIC CONSTRAINTS
    
    # COMPLEX CONSTRAINTS
    
    # COMPOUNDED CONSTRAINTS
    
    # STABILITY CONSTRAINTS
    
    # LOCAL CONSTRAINTS
    
    # Solve
    print("< < < Model formulated, commencing optimisation > > >")
#    model.optimize()
    
#    if model.status <> GRB.status.OPTIMAL:
#        print("< < < Optimisation completed, infeasible > > >")
#    else:
#        print("< < < Optimisation completed, codifying roster > > >")
    
#    sln = freeze_me(sln)
#    print("< < < Roster codifying completed, finished > > >")
#    return sln
