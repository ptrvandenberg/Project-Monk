# ViPER: Victoria Police Electronic Rostering
# Copyright 2017, Peter van den Berg

# Project Monk: SOCIT Fawkner
# This file implements a function [solve] that formulates and solves the model as well as codifies the resulting roster

# Import dependencies
from pandas import DataFrame, ExcelFile, isnull
from pulp import LpVariable, lpSum, LpProblem, LpMaximize, LpContinuous, LpInteger, LpBinary, LpStatus, value
from datetime import timedelta

# Validate input data (including keys, data types)
def validate_input(dat):
    rtn = {}
    
    # Input test 1: Weeks = 2 (model only designed for this???)

    if dat.parse('periods', index_col = 'period_id').loc[dat.parse('settings', index_col = 'parameter').loc['period_id', 'value'], 'weeks'] <> 2:
        rtn['Test 1 - Weeks'] = 'value <> 2'
    
    return rtn
    
def solve(dat):

    print("< < < Initiated, validating inputs > > >")

    invalid_input = validate_input(dat)
    assert not invalid_input, invalid_input

    print("< < < Inputs validated, formulating model > > >")

    # Parse input data

    settings = dat.parse('settings', index_col = 'parameter')
    unit = settings.ix['unit_id','value']
    period = settings.ix['period_id','value']

    units = dat.parse('units', index_col = 'unit_id')
    
    periods = dat.parse('periods', index_col = 'period_id')
    weeks = periods.ix[period,'weeks']
    days = range(1, weeks * 7 + 1)
    startdate = periods.ix[period,'start_date']

    rosters = dat.parse('rosters').query('unit_id == @unit').drop('unit_id', 1) # to be filtered for FY only for carryover
    rosters = rosters.set_index(['member_id','period_id','week'])
    
    rules = dat.parse('rules', index_col = 'rule_id')
    
    members = dat.parse('members', index_col = 'member_id').query('unit_id == @unit').drop('unit_id', 1)
    
    shifts = dat.parse('shifts', index_col = 'shift_id')    
    
    shortshifts = dat.parse('shortshifts').query('unit_id == @unit').query('period_id == @period').drop('period_id', 1).drop('unit_id', 1)
    shortshifts = shortshifts.set_index(['member_id','week'])
    
    longshifts = dat.parse('longshifts').query('unit_id == @unit').drop('unit_id', 1)
    longshifts = longshifts.set_index(['member_id','longshift'])

    # TO BE DELETED
    print 'members'
    print members
    print 'rosters'
    print rosters
    print 'shortshifts'
    print shortshifts
    print 'longshifts'
    print longshifts

    # Pre-process input data [carryover]
    
    roster0 = rosters.xs(periods.index.values[periods.index.get_loc(period)-1], level='period_id')
    weeks0 = periods.ix[periods.index.values[periods.index.get_loc(period)-1],'weeks']

    # TO BE DELETED
    print 'roster0'
    print roster0

    carryover = DataFrame(columns=['member_id','d0_shift','w0_nights','w0_fri_shift','w0_longshift','r0_co_rests','fy_2d_off','fy_we_off'])

    for m in members.index:
        carryover = carryover.append({
                        'member_id': m,
                        'd0_shift': roster0.ix[m].ix[weeks0,'d7'],
                        'w0_nights': (roster0.ix[m].ix[weeks0,'d1']=='RN')+(roster0.ix[m].ix[weeks0,'d2']=='RN')+(roster0.ix[m].ix[weeks0,'d3']=='RN')+(roster0.ix[m].ix[weeks0,'d4']=='RN')+(roster0.ix[m].ix[weeks0,'d5']=='RN')+(roster0.ix[m].ix[weeks0,'d6']=='RN')+(roster0.ix[m].ix[weeks0,'d7']=='RN'),
                        'w0_fri_shift': roster0.ix[m].ix[weeks0,'d6'],
                        'w0_longshift': roster0.ix[m].ix[weeks0,'longshift'],
                        'r0_co_rests': 0},
                    ignore_index=True)
    
    carryover = carryover.set_index(['member_id'])

    for m in members.index:
        for w in range(1,weeks0+1):
            carryover.ix[m,'r0_co_rests'] += (roster0.ix[m].ix[w,'d1']=='XR')+(roster0.ix[m].ix[w,'d2']=='XR')+(roster0.ix[m].ix[w,'d3']=='XR')+(roster0.ix[m].ix[w,'d4']=='XR')+(roster0.ix[m].ix[w,'d5']=='XR')+(roster0.ix[m].ix[w,'d6']=='XR')+(roster0.ix[m].ix[w,'d7']=='XR')
        carryover.ix[m,'r0_co_rests'] = max(2 * weeks0 - (carryover.ix[m,'r0_co_rests']),0)
            
    # TO BE DELETED
    print 'carryover'
    print carryover

    # Consolidate predetermined long- and shortshifts
    
    predetermined = shortshifts.copy()

    for m in members.index:
        print '1. ', m, members.ix[m,'longshifts']
        if members.ix[m,'longshifts'] >= 1:
            ls = carryover.ix[m,'w0_longshift']
            print '2. ', m, ls
            for w in range(1,weeks+1):
                if ls < members.ix[m,'longshifts']:
                    ls += 1
                else:
                    ls = 1
                print '2. ', m, ls
                for d in range(1,7+1):
                    print '3. ', m, predetermined.ix[m].ix[w,d-1]
                    if isnull(predetermined.ix[m].ix[w,d-1]):
                        print '4. ', m, longshifts.ix[m].ix[ls,d-1]
                        if not isnull(longshifts.ix[m].ix[ls,d-1]):
                            predetermined.ix[m].ix[w,d-1] = longshifts.ix[m].ix[ls,d-1]
                            print '5. ', m, predetermined.ix[m].ix[w,d-1]

    # TO BE DELETED
    
    print 'predetermined'
    print predetermined
    
    # [0000] OBJECTIVE – Commence model definition and set optimisation direction.
    if rules.ix[0, unit] == 'Yes':
        model = LpProblem("roster", LpMaximize)
    
    # Create and define the problem variables
    x = LpVariable.dicts("x_m%s_d%s_s%s", (members.index, days, shifts.index), 0, 1, LpBinary)
    
    # Create and define the additional variables
    r2_co_rests = LpVariable.dicts("r2_rests_%s", members.index, 0, 2, LpInteger)
    RN_bin1 = LpVariable.dicts("NG_bin1_%s", members.index, 0, 1, LpBinary)
    RN_bin4 = LpVariable.dicts("NG_bin4_%s", members.index, 0, 1, LpBinary)
    RN_bin5 = LpVariable.dicts("NG_bin5_%s", members.index, 0, 1, LpBinary)
    RN_bin8 = LpVariable.dicts("NG_bin8_%s", members.index, 0, 1, LpBinary)
    eor = LpVariable.dicts("eor_%s_%s", (members.index, days), 0, 1, LpBinary)
    crew_am_bin1 = LpVariable.dicts("crew_am_bin1_%s", days, 0, 1, LpBinary)
    crew_am_bin2 = LpVariable.dicts("crew_am_bin2_%s", days, 0, 1, LpBinary)
    crew_am_bin3 = LpVariable.dicts("crew_am_bin3_%s", days, 0, 1, LpBinary)
    crew_pm_bin1 = LpVariable.dicts("crew_pm_bin1_%s", days, 0, 1, LpBinary)
    crew_pm_bin2 = LpVariable.dicts("crew_pm_bin2_%s", days, 0, 1, LpBinary)
    crew_pm_bin3 = LpVariable.dicts("crew_pm_bin3_%s", days, 0, 1, LpBinary)
    
    # [0000] OBJECTIVE – Set the objective.
    if rules.ix[0, unit] == 'Yes':
        model += lpSum([x[m][d][s] * 1 for m in members.index for d in days for s in shifts.index if members.ix[m,'rank']<>"S" and s in ("RA1","RA2","RA3","RP1","RP2")]) + lpSum([x[m][d][s] * 2 for m in members.index for d in days for s in shifts.index if members.ix[m,'rank']=="S" and s in ("RA1","RA2","RA3","RP1","RP2")]) + lpSum([x[m][d][s] for m in members.index for d in days for s in shifts.index if s in ("RS","RN")])
    
    # STRUCTURAL CONSTRAINTS

    # [0010] SHIFTS – Each member on each day has to be assigned to one and only one shift, including part-time, rest and leave shifts.
    if rules.ix[10, unit] == 'Yes':
        for m in members.index:
            for d in days:
                model += lpSum([x[m][d][s] for s in shifts.index]) == 1

    # INPUT CONSTRAINTS
    
    # [0020] PREDETERMINED – Each member for each day is assigned their pre-determined shift if allocated; if not pre-determined then not rostered on pre-determined shifts.
    if rules.ix[20, unit] == 'Yes':
        for m in members.index:
            for d in days:
                if not isnull(predetermined.ix[m,d-1]):
                    model += x[m][d][predetermined.ix[m,d-1]] == 1
                else:
                    for s in shifts.index:
                        if shifts.ix[s,'predetermined'] == 1:
                            model += x[m][d][s] == 0
    
    # RULE CONSTRAINTS
    
    # [0030] FTE – Each member needs to be assigned to 5*FTE*weeks -/+ carryover rests shifts, excluding part-time and rest shift.
    if rules.ix[30, unit] == 'Yes':
        for m in members.index:
            model += lpSum([x[m][d][s] for d in days for s in shifts.index if s <> "XP" and s <> "XR"]) == weeks * 5 * members.ix[m,'fte'] - carryover.ix[m,'r0_co_rests'] + r2_co_rests[m]
    
    # [0040] REST – Each member needs to be assigned 2*weeks +/- carryover rest shifts.
    if rules.ix[40, unit] == 'Yes':
        for m in members.index:
            model += lpSum([x[m][d]["XR"] for d in days]) == weeks * 2 + carryover.ix[m,'r0_co_rests'] - r2_co_rests[m]
    
    # [0050] PART-TIME – Each member needs to be assigned to 5*(1-FTE)*weeks part-time shifts.
    if rules.ix[50, unit] == 'Yes':
        for m in members.index:
            model += lpSum([x[m][d]["XP"] for d in days]) == weeks * 5 * (1 - members.ix[m,'fte'])
    
    # [0060] 10 HOURS – Each member needs to have at least 10 hours between shifts.
    if rules.ix[60, unit] == 'Yes':
        for m in members.index:
            for d in days:
                if d == 1:
                    model += lpSum([x[m][d][s] * shifts.ix[s,'starttime'] for s in shifts.index]) >=  shifts.ix[carryover.ix[m,'d0_shift'],'endtime'] + 10 - 24
                else:
                    model += lpSum([x[m][d][s] * shifts.ix[s,'starttime'] for s in shifts.index]) >= lpSum([x[m][d-1][s] * shifts.ix[s,'endtime'] for s in shifts.index]) + 10 - 24

    # [0070] REST CARRYOVER – Each member can carryover up to 2 rests if he/she is on 7 consecutive night shifts in the current roster; 0 if not.
    if rules.ix[70, unit] == 'Yes':
        for m in members.index:
            model += r2_co_rests[m] <= 2 * (RN_bin1[m] + RN_bin4[m] + RN_bin5[m] + RN_bin8[m])
            model += RN_bin1[m] <= lpSum([x[m][d]["RN"] for d in range(1,8)]) / 7
            model += RN_bin1[m] > lpSum([x[m][d]["RN"] for d in range(1,8)]) / 7 - 1
            model += RN_bin4[m] <= lpSum([x[m][d]["RN"] for d in range(4,11)]) / 7
            model += RN_bin4[m] > lpSum([x[m][d]["RN"] for d in range(4,11)]) / 7 - 1
            model += RN_bin5[m] <= lpSum([x[m][d]["RN"] for d in range(5,12)]) / 7
            model += RN_bin5[m] > lpSum([x[m][d]["RN"] for d in range(5,12)]) / 7 - 1
            model += RN_bin8[m] <= lpSum([x[m][d]["RN"] for d in range(8,15)]) / 7
            model += RN_bin8[m] > lpSum([x[m][d]["RN"] for d in range(8,15)]) / 7 - 1
    
    # [0080] RECOVERY – Each member is eligble for one recovery shift following 4+ consecutive night shifts; ineligible if not.
    if rules.ix[80, unit] == 'Yes':
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
            else:
                model += eor[m][4] == 0

            for w in range(1,weeks):
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
            
            for w in range(weeks,weeks+1):
                model += eor[m][5+7*(w-1)] <= lpSum([x[m][d]["RN"] for d in range(1+7*(w-1),5+7*(w-1))]) / 4
                model += eor[m][5+7*(w-1)] <= 1 - x[m][5+7*(w-1)]["RN"]
                model += eor[m][5+7*(w-1)] > lpSum([x[m][d]["RN"] for d in range(1+7*(w-1),5+7*(w-1))]) / 4 - x[m][5+7*(w-1)]["RN"] - 1

                model += eor[m][6+7*(w-1)] == 0
                model += eor[m][7+7*(w-1)] == 0

    # [0090] RECOVERY – Each member is assigned one recovery shift if they are eligible and work the following day; 0 if not.
    if rules.ix[90, unit] == 'Yes':
        for m in members.index:
            for d in days:
                if d <> weeks*7:
                    model += x[m][d]["OR"] <= eor[m][d]
                    model += x[m][d]["OR"] <= lpSum([x[m][d+1][s] for s in shifts.index if s not in ("XL","XP","XR")])
                    model += x[m][d]["OR"] > eor[m][d] + lpSum([x[m][d+1][s] for s in shifts.index if s not in ("XL","XP","XR")]) - 2
            model += x[m][weeks*7]["OR"] <= eor[m][weeks*7]

    # [0100] STATION 1700 – Each member can only be rostered on the Station 1700 shift when 3 night shifts before.
    if rules.ix[100, unit] == 'Yes':
        for m in members.index:
            if carryover.ix[m,'w0_nights'] <> 3 or carryover.ix[m,'d0_shift'] <> "RN": 
                model += x[m][1]["SP2"] == 0

            for w in range(1,weeks+1):
                if w <> 1:
                    model += x[m][1+7*(w-1)]["SP2"] <= lpSum([x[m][d]["RN"] for d in range(-2+7*(w-1),1+7*(w-1))]) / 3
                model += x[m][2+7*(w-1)]["SP2"] == 0
                model += x[m][3+7*(w-1)]["SP2"] == 0
                model += x[m][4+7*(w-1)]["SP2"] <= lpSum([x[m][d]["RN"] for d in range(1+7*(w-1),4+7*(w-1))]) / 3
                model += x[m][5+7*(w-1)]["SP2"] == 0
                model += x[m][6+7*(w-1)]["SP2"] == 0
                model += x[m][7+7*(w-1)]["SP2"] == 0
    
    # [0110] WEEKEND – All shifts on the weekend, except recovery and rest, are self-nominated only (i.e. pre-determined).
    if rules.ix[110, unit] == 'Yes':
        for m in members.index:
            for w in range(1,weeks+1):
                for s in shifts.index:
                    if s not in ("OR","XR"):
                        if predetermined.ix[m,1+7*(w-1)-1] <> s:
                            model += x[m][1+7*(w-1)][s] == 0
                        if predetermined.ix[m,7+7*(w-1)-1] <> s:
                            model += x[m][7+7*(w-1)][s] == 0
    
    # [0120] WEEKEND – Weekend morning 700 1 member, 900 1 member; weekend afternoon 1500 2 members; none on all other response and station day shifts.
    if rules.ix[120, unit] == 'Yes':
        for w in range(1,weeks+1):
            for d in (1,7):
                model += lpSum([x[m][d+7*(w-1)]["RA1"] for m in members.index]) == 1
                model += lpSum([x[m][d+7*(w-1)]["RA2"] for m in members.index]) == 0
                model += lpSum([x[m][d+7*(w-1)]["RA3"] for m in members.index]) == 1
                model += lpSum([x[m][d+7*(w-1)]["RP1"] for m in members.index]) == 0
                model += lpSum([x[m][d+7*(w-1)]["RP2"] for m in members.index]) == 2
                model += lpSum([x[m][d+7*(w-1)]["SA1"] for m in members.index]) == 0
                model += lpSum([x[m][d+7*(w-1)]["SA2"] for m in members.index]) == 0
                model += lpSum([x[m][d+7*(w-1)]["SP1"] for m in members.index]) == 0
                model += lpSum([x[m][d+7*(w-1)]["SP2"] for m in members.index]) == 0
    
    # [0130] WEEKDAY – On weekdays, the morning response 700 needs to have 1 member only.
    if rules.ix[130, unit] == 'Yes':
        for w in range(1,weeks+1):
            for d in range(2,6+1):
                model += lpSum([x[m][d]["RA1"] for m in members.index]) == 1

    # [0140] WEEKDAY – On weekdays, the morning response 900 and station 900 shifts only allowed if 1500 day before.
    if rules.ix[140, unit] == 'Yes':
        for m in members.index:
            for w in range(1,weeks+1):
                for d in range(2,6+1):
                    model += x[m][d+7*(w-1)]["RA3"] <= x[m][d+7*(w-1)-1]["RP2"] + x[m][d+7*(w-1)-1]["SP1"]
                    model += x[m][d+7*(w-1)]["SA2"] <= x[m][d+7*(w-1)-1]["RP2"] + x[m][d+7*(w-1)-1]["SP1"]

    # [0150] WEEKDAY – On weekdays, the afternoon response 1300 shift only allowed if 700 next day.
    if rules.ix[150, unit] == 'Yes':
        for m in members.index:
            for w in range(1,weeks+1):
                for d in range(2,6+1):
                    model += x[m][d+7*(w-1)]["RP1"] <= x[m][d+7*(w-1)+1]["RS"] + x[m][d+7*(w-1)+1]["RA1"]
    
    # [0170] FRIDAY AVO – Member are not allowed to be rostered on Friday afternoon shift and Saturday morning or afternoon shift.
    if rules.ix[170, unit] == 'Yes':
        for m in members.index:
            for w in range(1,weeks+1):
                model += x[m][6+7*(w-1)]["RP1"] + x[m][6+7*(w-1)]["RP2"] + x[m][6+7*(w-1)]["SP1"] + x[m][6+7*(w-1)]["SP2"] + x[m][7+7*(w-1)]["RA1"] + x[m][7+7*(w-1)]["RA2"] + x[m][7+7*(w-1)]["RA3"] + x[m][7+7*(w-1)]["SA1"] + x[m][7+7*(w-1)]["SA2"] + x[m][7+7*(w-1)]["RP1"] + x[m][7+7*(w-1)]["RP2"] + x[m][7+7*(w-1)]["SP1"] + x[m][7+7*(w-1)]["SP2"] <= 1
    
    # [0180] FRIDAY AVO – Members are not allowed to be rostered on Friday afternoon shifts two consecutive weeks.
    if rules.ix[180, unit] == 'Yes':
        for m in members.index:
            for w in range(1,weeks+1):
                if w == 1:
                    if carryover.ix[m,'w0_fri_shift'] in ("RP1","RP2","SP1","SP2"):
                        model += x[m][6]["RP1"] + x[m][6]["RP2"] + x[m][6]["SP1"] + x[m][6]["SP2"] == 0
                else:
                    model += x[m][6+7*(w-2)]["RP1"] + x[m][6+7*(w-2)]["RP2"] + x[m][6+7*(w-2)]["SP1"] + x[m][6+7*(w-2)]["SP2"] + x[m][6+7*(w-1)]["RP1"] + x[m][6+7*(w-1)]["RP2"] + x[m][6+7*(w-1)]["SP1"] + x[m][6+7*(w-1)]["SP2"] <= 1
    
    # [0190] SERGEANT – On weekdays, no 7am response shifts for Sergeants.
    if rules.ix[190, unit] == 'Yes':
        for m in members.index:
            if members.ix[m,'rank'] == "S":
                for w in range(1,weeks+1):
                    for d in range(2,6+1):
                        model += x[m][d+7*(w-1)]["RA1"] == 0

    # [0200] CREW – On weekdays, morning and afternoon response needs to have at least 3 members, but 4 is preferred.
    if rules.ix[200, unit] == 'Yes':
        for w in range(1,weeks+1):
            for d in range(2,6+1):
                model += lpSum([x[m][d+7*(w-1)]["RA1"] + x[m][d+7*(w-1)]["RA2"] + x[m][d+7*(w-1)]["RA3"] for m in members.index]) >= 3
                model += lpSum([x[m][d+7*(w-1)]["RA1"] + x[m][d+7*(w-1)]["RA2"] + x[m][d+7*(w-1)]["RA3"] for m in members.index]) <= 4
                model += lpSum([x[m][d+7*(w-1)]["RP1"] + x[m][d+7*(w-1)]["RP2"] for m in members.index]) >= 3
                model += lpSum([x[m][d+7*(w-1)]["RP1"] + x[m][d+7*(w-1)]["RP2"] for m in members.index]) <= 4
    
    # [0210] CREW – On weekdays, both morning and afternoon response shifts each have to be from the same crew.
    if rules.ix[210, unit] == 'Yes':
        for w in range(1,weeks+1):
            for d in range(2,6+1):
                model += crew_am_bin1[d+7*(w-1)] + crew_am_bin2[d+7*(w-1)] + crew_am_bin3[d+7*(w-1)] == 1
                model += crew_pm_bin1[d+7*(w-1)] + crew_pm_bin2[d+7*(w-1)] + crew_pm_bin3[d+7*(w-1)] == 1
                for m in members.index:
                    if members.ix[m,'crew'] == 1:
                        model += x[m][d+7*(w-1)]["RA1"] + x[m][d+7*(w-1)]["RA2"] + x[m][d+7*(w-1)]["RA3"] <= crew_am_bin1[d+7*(w-1)]
                        model += x[m][d+7*(w-1)]["RP1"] + x[m][d+7*(w-1)]["RP2"] <= crew_pm_bin1[d+7*(w-1)]
                    if members.ix[m,'crew'] == 2:
                        model += x[m][d+7*(w-1)]["RA1"] + x[m][d+7*(w-1)]["RA2"] + x[m][d+7*(w-1)]["RA3"] <= crew_am_bin2[d+7*(w-1)]
                        model += x[m][d+7*(w-1)]["RP1"] + x[m][d+7*(w-1)]["RP2"] <= crew_pm_bin2[d+7*(w-1)]
                    if members.ix[m,'crew'] == 3:
                        model += x[m][d+7*(w-1)]["RA1"] + x[m][d+7*(w-1)]["RA2"] + x[m][d+7*(w-1)]["RA3"] <= crew_am_bin3[d+7*(w-1)]
                        model += x[m][d+7*(w-1)]["RP1"] + x[m][d+7*(w-1)]["RP2"] <= crew_pm_bin3[d+7*(w-1)]
    
    # [0215] CREW – On weekdays, if a member’s crew is on morning or afternoon (excluding 1700) response then the member can’t be on an afternoon or morning shift respectively.
    if rules.ix[215, unit] == 'Yes':
        for w in range(1,weeks+1):
            for d in range(2,6+1):
                for m in members.index:
                    if members.ix[m,'crew'] == 1:
                        model += x[m][d+7*(w-1)]["SP1"] <= 1 - crew_am_bin1[d+7*(w-1)]
                        model += x[m][d+7*(w-1)]["SA1"] + x[m][d+7*(w-1)]["SA2"] <= 1 - crew_pm_bin1[d+7*(w-1)]
                    if members.ix[m,'crew'] == 2:
                        model += x[m][d+7*(w-1)]["SP1"] <= 1 - crew_am_bin2[d+7*(w-1)]
                        model += x[m][d+7*(w-1)]["SA1"] + x[m][d+7*(w-1)]["SA2"] <= 1 - crew_pm_bin2[d+7*(w-1)]
                    if members.ix[m,'crew'] == 3:
                        model += x[m][d+7*(w-1)]["SP1"] <= 1 - crew_am_bin3[d+7*(w-1)]
                        model += x[m][d+7*(w-1)]["SA1"] + x[m][d+7*(w-1)]["SA2"] <= 1 - crew_pm_bin3[d+7*(w-1)]
    
    # [0220] ...
#    if rules.ix[220, unit] == 'Yes':
    
    # [0230] MEMBER – Hooper one self-nominated afternoon shift per month, i.e. no afternoon shift unless pre-determined.
    if rules.ix[230, unit] == 'Yes':
        for d in days:
            for s in ("RP1","RP2","SP1","SP2"):
                if predetermined.ix["VP34315",d-1] <> s:
                    model += x["VP34315"][d][s] == 0
    
    # [0240] MEMBER – Spencer no 7am shift unless pre-determined.
    if rules.ix[240, unit] == 'Yes':
        for d in days:
            if predetermined.ix["VP33968",d-1] <> "RA1":
                model += x["VP33968"][d]["RA1"] == 0
    
    # Solve
    print("< < < Model formulated, commencing optimisation > > >")
    model.solve()
    
    print("Status:", LpStatus[model.status])
    print("Value = ", value(model.objective))
    
    model.writeLP("c:\git\Project_Monk.lp")
    
    if LpStatus[model.status] == 'Infeasible':
        print("< < < Optimisation completed, infeasible > > >")
        roster = {}
    elif LpStatus[model.status] == 'Undefined':
        print("< < < Optimisation completed, undefined > > >")
        roster = {}
    elif LpStatus[model.status] == 'Optimal':
        print("< < < Optimisation completed, codifying roster > > >")
        roster = DataFrame(columns=['Unit', 'Crew', 'Member_ID', 'Member', 'Rank'])
        for w in range(1,weeks+1):
            roster['Sun '+str(startdate + timedelta(days=0+7*(w-1)))[8:-9]+'/'+str(startdate + timedelta(days=0+7*(w-1)))[5:-12]] = ''
            roster['Mon '+str(startdate + timedelta(days=1+7*(w-1)))[8:-9]+'/'+str(startdate + timedelta(days=1+7*(w-1)))[5:-12]] = ''
            roster['Tue '+str(startdate + timedelta(days=2+7*(w-1)))[8:-9]+'/'+str(startdate + timedelta(days=2+7*(w-1)))[5:-12]] = ''
            roster['Wed '+str(startdate + timedelta(days=3+7*(w-1)))[8:-9]+'/'+str(startdate + timedelta(days=3+7*(w-1)))[5:-12]] = ''
            roster['Thu '+str(startdate + timedelta(days=4+7*(w-1)))[8:-9]+'/'+str(startdate + timedelta(days=4+7*(w-1)))[5:-12]] = ''
            roster['Fri '+str(startdate + timedelta(days=5+7*(w-1)))[8:-9]+'/'+str(startdate + timedelta(days=5+7*(w-1)))[5:-12]] = ''
            roster['Sat '+str(startdate + timedelta(days=6+7*(w-1)))[8:-9]+'/'+str(startdate + timedelta(days=6+7*(w-1)))[5:-12]] = ''
        roster = roster.set_index(['Member_ID'])
        for v in model.variables():
            if v.name[0:2] == "x_" and v.varValue == 1:
                m = v.name[v.name.find("_m")+2:v.name.find("_d")]
                d = v.name[v.name.find("_d")+2:v.name.find("_s")]
                s = v.name[v.name.find("_s")+2:]
                roster.ix[m,'Unit'] = unit
                roster.ix[m,'Crew'] = members.ix[m,'crew']
                roster.ix[m,'Member'] = members.ix[m,'lastname'] + ' ' + members.ix[m,'firstname']
                roster.ix[m,'Rank'] = members.ix[m,'rank']
                roster.ix[m,int(d)+3] = s
        print("< < < Roster codifying completed, finished > > >")

    return roster
