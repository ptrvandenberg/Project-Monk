# VIPER: VIctoria Police Electronic Rostering
# Copyright 2017, Peter van den Berg

# Project Monk: SOCAU Fawkner
# This file implements a function [solve] that formulates and solves the model as well as codifies the resulting roster

# Import dependencies
from pandas import ExcelFile
from pulp import LpVariable, lpSum, LpProblem, LpMaximize, LpInteger, LpBinary, LpStatus, value

# Define the input schema

# Foreign keys on input schema

# Set data types of input schema

# Define the output schema

# Define solve function that formulates and solves the model
def solve(dat):

    print("< < < Importing input data > > >")
    
    settings = dat.parse('settings')
    members = dat.parse('members')
    days = dat.parse('days')
    shifts = dat.parse('shifts')
    shiftdates = dat.parse('shiftdates')
    carryover = dat.parse('carryover')
    longshift = dat.parse('longshift')
    shortshift = dat.parse('shortshift')
    restricted = dat.parse('restricted')
    
    print("< < < Testing input data > > >")
    
    print("< < < Input data testing completed, formulating model > > >")
    
    # Commence model definition
    model = Model("roster")
    
    # Create and define the problem variables
    
    # Create and define the additional variables
    
    # Set the objective
    
    # Set optimisation direction
    
    # Update model to integrate new variables
    model.update()
    
    # STRUCTURAL CONSTRAINTS
    
    # Structure of defined problem variables
    
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
    model.optimize()
    
    if model.status <> GRB.status.OPTIMAL:
        print("< < < Optimisation completed, infeasible > > >")
    else:
        print("< < < Optimisation completed, codifying roster > > >")
    
    sln = freeze_me(sln)
    print("< < < Roster codifying completed, finished > > >")
    return sln
