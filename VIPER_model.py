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
    settings = dat.parse('settings', index_col = 'parameter')
    members = dat.parse('members')
    days = dat.parse('days', index_col = 'dayseq')
    shifts = dat.parse('shifts', index_col = 'shiftcd')    
    shiftdates = dat.parse('shiftdates', index_col = 'shiftcd')
    carryover = dat.parse('carryover', index_col = 'memid')
    longshift = dat.parse('longshift')
    longshift = longshift.set_index('memid','week')
    shortshift = dat.parse('shortshift', index_col = 'memid')
    restricted = dat.parse('restricted')
    restricted = restricted.set_index('memid','dayseq','shiftcd')
    
    # Commence model definition and set optimisation direction
    model = LpProblem("roster", LpMaximize)
    
    # Create and define the problem variables
    x = LpVariable.dicts("x_%s_%s_%s", (members.index, days.index, shifts.index), 0, 1, LpBinary)
#    x_mg = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_am1 = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_am2 = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_am3 = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_pm1 = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_pm2 = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_ng = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_oc = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_oe = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_or = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_xl = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_xp = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
#    x_xr = LpVariable.dicts("roster_%s_%s", (members, days), 0, 1, LpBinary)
    
    # Create and define the additional variables

    r2_rests = LpVariable.dicts("r2_rests_%s", members.index, 0, 2, LpInteger)
    r1_night = LpVariable.dicts("r1_night_%s", members.index, 0, 1, LpBinary)
    
    # Set the objective
    mds = [(m,d,s) for m in members.index for d in days.index for s in shifts.index]
    model += lpSum([x[m][d][s] for (m,d,s) in mds])
    
    # STRUCTURAL CONSTRAINTS

    # Each member on each day has to be assigned to one and only one shift, including part-time, rest and leave shifts
    for m in members.index:
        for d in days.index:
            model += lpSum([x[m][d][s] for s in shifts.index]) == 1

    # INPUT CONSTRAINTS
    
    # Assign shifts based on the Committed input
    
    # Restrict shifts based on the Restricted input
    
    # BASIC CONSTRAINTS
    
    # COMPLEX CONSTRAINTS
    
    # Each member needs to be assigned to 5*FTE*weeks -/+ carryover rests shifts, excluding part-time and rest shift
    for m in members.index:
        model += lpSum([x[m][d][s] for d in days.index for s in shifts.index if s <> "XP" and s <> "XR"]) == settings.ix['nbr_roster_weeks','value'] * 5 * members.ix[m,'fte'] - carryover.ix[m,'r0_rests'] + r2_rests[m]
    
    # Each member needs to be assigned 2*weeks +/- carryover rest shifts
    for m in members.index:
        model += lpSum([x[m][d]["XR"] for d in days.index]) == settings.ix['nbr_roster_weeks','value'] * 2 + carryover.ix[m,'r0_rests'] - r2_rests[m]
    
    # Each member can carryover up to 2 rests if he/she is on night shift in the current roster; 0 if not
    for m in members.index:
        model += r1_night[m] == x[m][7]["NG"] + x[m][14]["NG"]
        model += r2_rests[m] <= 2 * r1_night[m]
    
    # COMPOUNDED CONSTRAINTS
    
    # STABILITY CONSTRAINTS
    
    # LOCAL CONSTRAINTS
    
    # Solve
    print("< < < Model formulated, commencing optimisation > > >")
    model.solve()
    
    print("Status:", LpStatus[model.status])
    print("Value = ", value(model.objective))
    
    model.writeLP("c:\git\Project_Monk.lp")
    
#    if model.status <> GRB.status.OPTIMAL:
#        print("< < < Optimisation completed, infeasible > > >")
#    else:
#        print("< < < Optimisation completed, codifying roster > > >")
    
#    sln = freeze_me(sln)
#    print("< < < Roster codifying completed, finished > > >")
#    return sln
