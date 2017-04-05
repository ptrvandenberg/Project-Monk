# VIPER: VIctoria Police Electronic Rostering
# Copyright 2017, Peter van den Berg

# Project Monk: SOCAU Fawkner
# This file implements a function [solve] that formulates and solves the model as well as codifies the resulting roster

# Import dependencies
from pandas import ExcelFile, isnull
from pulp import LpVariable, lpSum, LpProblem, LpMaximize, LpContinuous, LpInteger, LpBinary, LpStatus, value

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
    
    # Weeks = 2 (model only designed for this)
    # Carry-in rest=[0,1,2]
    
    return rtn
    
def solve(dat):

    invalid_input = validate_input(dat)
    assert not invalid_input, invalid_input

    # Parse input data
    settings = dat.parse('settings', index_col = 'parameter')
    members = dat.parse('members', index_col = 'memid')
    days = dat.parse('days', index_col = 'dayseq')
    shifts = dat.parse('shifts', index_col = 'shiftcd')    
#    shiftdates = dat.parse('shiftdates', index_col = 'shiftcd')
    carryover = dat.parse('carryover', index_col = 'memid')
    longshift = dat.parse('longshift')
    longshift = longshift.set_index(['memid','roster'])
    shortshift = dat.parse('shortshift', index_col = 'memid')
#    restricted = dat.parse('restricted')
#    restricted = restricted.set_index(['memid','dayseq','shiftcd'])

    # Preprocess input data
    predetermined = shortshift.copy()
    
    for m in members.index:
        for d in days.index:
            if isnull(predetermined.ix[m,d-1]):
                if members.ix[m,'longshift'] == 1:
                    if not isnull(longshift.ix[m].ix[1,d-1]):
                        predetermined.ix[m,d-1] = longshift.ix[m].ix[1,d-1]
                elif members.ix[m,'longshift'] > 1:
                    if carryover.ix[m,'r0_longshift'] < members.ix[m,'longshift']:
                        if not isnull(longshift.ix[m].ix[carryover.ix[m,'r0_longshift']+1, d-1]):
                            predetermined.ix[m,d-1] = longshift.ix[m].ix[carryover.ix[m,'r0_longshift']+1, d-1]
                    else:
                        if not isnull(longshift.ix[m].ix[1,d-1]):
                            predetermined.ix[m,d-1] = longshift.ix[m].ix[1,d-1]

    # [001] OBJECTIVE – Commence model definition and set optimisation direction.
    model = LpProblem("roster", LpMaximize)
    
    # Create and define the problem variables
    x = LpVariable.dicts("x_%s_%s_%s", (members.index, days.index, shifts.index), 0, 1, LpBinary)
    
    # Create and define the additional variables
    r2_rests = LpVariable.dicts("r2_rests_%s", members.index, 0, 2, LpInteger)
    RN_bin1 = LpVariable.dicts("NG_bin1_%s", members.index, 0, 1, LpBinary)
    RN_bin4 = LpVariable.dicts("NG_bin4_%s", members.index, 0, 1, LpBinary)
    RN_bin5 = LpVariable.dicts("NG_bin5_%s", members.index, 0, 1, LpBinary)
    RN_bin8 = LpVariable.dicts("NG_bin8_%s", members.index, 0, 1, LpBinary)
    eor = LpVariable.dicts("eor_%s_%s", (members.index, days.index), 0, 1, LpBinary)
    
    # [001] OBJECTIVE – Set the objective.
    model += lpSum([x[m][d][s] for m in members.index for d in days.index for s in shifts.index])
    
    # STRUCTURAL CONSTRAINTS

    # [002] SHIFTS – Each member on each day has to be assigned to one and only one shift, including part-time, rest and leave shifts.
    for m in members.index:
        for d in days.index:
            model += lpSum([x[m][d][s] for s in shifts.index]) == 1

    # INPUT CONSTRAINTS
    
    # [003] PREDETERMINED – Each member for each day is assigned their pre-determined shift if allocated.
    # [004] PREDETERMINED – If not pre-determined then not rostered on pre-determined shifts.
    
    for m in members.index:
        for d in days.index:
            if not isnull(predetermined.ix[m,d-1]):
                model += x[m][d][predetermined.ix[m,d-1]] == 1
            else:
                for s in shifts.index:
                    if shifts.ix[s,'predetermined'] == 1:
                        model += x[m][d][s] == 0
    
    # RULE CONSTRAINTS
    
    # [005] FTE – Each member needs to be assigned to 5*FTE*weeks -/+ carryover rests shifts, excluding part-time and rest shift.
    for m in members.index:
        model += lpSum([x[m][d][s] for d in days.index for s in shifts.index if s <> "XP" and s <> "XR"]) == settings.ix['nbr_roster_weeks','value'] * 5 * members.ix[m,'fte'] - carryover.ix[m,'r0_rests'] + r2_rests[m]
    
    # [006] REST – Each member needs to be assigned 2*weeks +/- carryover rest shifts.
    for m in members.index:
        model += lpSum([x[m][d]["XR"] for d in days.index]) == settings.ix['nbr_roster_weeks','value'] * 2 + carryover.ix[m,'r0_rests'] - r2_rests[m]
    
    # [007] PART-TIME – Each member needs to be assigned to 5*(1-FTE)*weeks part-time shifts.
    for m in members.index:
        model += lpSum([x[m][d]["XP"] for d in days.index]) == settings.ix['nbr_roster_weeks','value'] * 5 * (1 - members.ix[m,'fte'])
    
    # [008] 10 HOURS – Each member needs to have at least 10 hours between shifts.
    
#    for m in members.index:
#        for d in days.index:
#            if d == 1:
#                model += lpSum([x[m][d][s] * shifts.ix[s,'starttime'] for s in shifts.index]) >=  shifts.ix[carryover.ix[m,'d0_shift'],'endtime'] + 10 - 24
#            else:
#                model += lpSum([x[m][d][s] * shifts.ix[s,'starttime'] for s in shifts.index]) >= lpSum([x[m][d-1][s] * shifts.ix[s,'starttime'] for s in shifts.index]) + 10 - 24

    # [009] REST CARRYOVER – Each member can carryover up to 2 rests if he/she is on 7 consecutive night shifts in the current roster; 0 if not.
    for m in members.index:
        model += r2_rests[m] <= 2 * (RN_bin1[m] + RN_bin4[m] + RN_bin5[m] + RN_bin8[m])
        model += RN_bin1[m] <= lpSum([x[m][d]["RN"] for d in range(1,8)]) / 7
        model += RN_bin1[m] > lpSum([x[m][d]["RN"] for d in range(1,8)]) / 7 - 1
        model += RN_bin4[m] <= lpSum([x[m][d]["RN"] for d in range(4,11)]) / 7
        model += RN_bin4[m] > lpSum([x[m][d]["RN"] for d in range(4,11)]) / 7 - 1
        model += RN_bin5[m] <= lpSum([x[m][d]["RN"] for d in range(5,12)]) / 7
        model += RN_bin5[m] > lpSum([x[m][d]["RN"] for d in range(5,12)]) / 7 - 1
        model += RN_bin8[m] <= lpSum([x[m][d]["RN"] for d in range(8,15)]) / 7
        model += RN_bin8[m] > lpSum([x[m][d]["RN"] for d in range(8,15)]) / 7 - 1
    
    # [010] RECOVERY – Each member is eligble for one recovery shift following 4+ consecutive night shifts; ineligible if not.
    for m in members.index:
        if carryover.ix[m,'w0_nights'] == 7:
            model += eor[m][1] == 1
        elif carryover.ix[m,'w0_nights'] == 4 and carryover.ix[m,'d0_shift'] == "RN":
            model += eor[m][1] == 1 - x[m][1]["RN"]
        else:
            model += eor[m][1] == 0

        model += eor[m][2] == 0
        model += eor[m][3] == 0

        if carryover.ix[m,'w0_nights'] == 4 and carryover.ix[m,'d0_shift'] == "RN":
            model += eor[m][4] == x[m][1]["RN"]

        for w in range(1,settings.ix['nbr_roster_weeks','value']):
            model += eor[m][5+7*(w-1)] >= lpSum([x[m][d]["RN"] for d in range(1+7*(w-1),5+7*(w-1))]) / 4 + (1 - x[m][5+7*(w-1)]["RN"]) - 1
            model += eor[m][5+7*(w-1)] <= lpSum([x[m][d]["RN"] for d in range(1+7*(w-1),5+7*(w-1))]) / 4
            model += eor[m][5+7*(w-1)] <= 1 - x[m][5+7*(w-1)]["RN"]

            model += eor[m][6+7*(w-1)] == 0
            model += eor[m][7+7*(w-1)] == 0
            
            model += eor[m][8+7*(w-1)] > lpSum([x[m][d]["RN"] for d in range(1+7*(w-1),8+7*(w-1))]) / 7 - 1
            model += eor[m][8+7*(w-1)] <= 1 - x[m][8+7*(w-1)]["RN"]
            model += eor[m][8+7*(w-1)] <= lpSum([x[m][d]["RN"] for d in range(4+7*(w-1),8+7*(w-1))]) / 4
            model += eor[m][8+7*(w-1)] > lpSum([x[m][d]["RN"] for d in range(4+7*(w-1),8+7*(w-1))]) / 4 - x[m][8+7*(w-1)]["RN"] - 1

            model += eor[m][9+7*(w-1)] == 0
            model += eor[m][10+7*(w-1)] == 0
            
            model += eor[m][11+7*(w-1)] <= lpSum([x[m][d]["RN"] for d in range(4+7*(w-1),11+7*(w-1))]) / 7
            model += eor[m][11+7*(w-1)] > lpSum([x[m][d]["RN"] for d in range(4+7*(w-1),11+7*(w-1))]) / 7 - 1
            
        for w in range(settings.ix['nbr_roster_weeks','value'],settings.ix['nbr_roster_weeks','value']+1):
            model += eor[m][5+7*(w-1)] <= lpSum([x[m][d]["RN"] for d in range(1+7*(w-1),5+7*(w-1))]) / 4
            model += eor[m][5+7*(w-1)] <= 1 - x[m][5+7*(w-1)]["RN"]
            model += eor[m][5+7*(w-1)] > lpSum([x[m][d]["RN"] for d in range(1+7*(w-1),5+7*(w-1))]) / 4 - x[m][5+7*(w-1)]["RN"] - 1

            model += eor[m][6+7*(w-1)] == 0
            model += eor[m][7+7*(w-1)] == 0

    # [011] RECOVERY – Each member is assigned one recovery shift if they are eligible and work the following day; 0 if not.
    
    for m in members.index:
        for d in days.index:
            if d <> settings.ix['nbr_roster_weeks','value'] * 7:
                model += x[m][d]["OR"] <= eor[m][d]
                model += x[m][d]["OR"] <= lpSum([x[m][d+1][s] for s in shifts.index if s not in ("XL","XP","XR")])
                model += x[m][d]["OR"] > eor[m][d] + lpSum([x[m][d+1][s] for s in shifts.index if s not in ("XL","XP","XR")]) - 2

    # [012] STATION 1700 – Each is member can only be rostered on the Station 1700 shift when 3 night shifts before.
    
    for m in members.index:
        if carryover.ix[m,'w0_nights'] <> 3 or carryover.ix[m,'d0_shift'] <> "RN": 
            model += x[m][1]["SP2"] == 0

        for w in range(1,settings.ix['nbr_roster_weeks','value']+1):
            if w <> 1:
                model += x[m][1+7*(w-1)]["SP2"] <= lpSum([x[m][d]["RN"] for d in range(-2+7*(w-1),1+7*(w-1))]) / 3
            model += x[m][2+7*(w-1)]["SP2"] == 0
            model += x[m][3+7*(w-1)]["SP2"] == 0
            model += x[m][4+7*(w-1)]["SP2"] <= lpSum([x[m][d]["RN"] for d in range(1+7*(w-1),4+7*(w-1))]) / 3
            model += x[m][5+7*(w-1)]["SP2"] == 0
            model += x[m][6+7*(w-1)]["SP2"] == 0
            model += x[m][7+7*(w-1)]["SP2"] == 0
    
    # STABILITY CONSTRAINTS

    # []
    
    # LOCAL CONSTRAINTS
    
    # []
    
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
