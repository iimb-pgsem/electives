
# $Id: ElecConfig.pm,v 1.1 2006/08/12 20:17:05 a14562 Exp $

# Copyright (c) 2006
# Sankaranaryananan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

package ElecConfig;

use strict;
use vars qw($VERSION @ISA @EXPORT @EXPORT_OK);

require Exporter;

@ISA = qw(Exporter AutoLoader);
# Items to export into callers namespace by default. Note: do not export
# names by default without a very good reason. Use EXPORT_OK instead.
# Do not simply export all your public functions/methods/constants.

@EXPORT = qw(
    $title
    $footer
    $phase
    $default_cap
    $default_mincap
    $default_status
    $default_site
    $default_cgpa
    $max_cgpa
    $min_cgpa_four_courses
    $min_credits
    $credits_pass
    $current_year
    $max_courses
    $give_priority_to_seniors
    $give_priority_to_cgpa
);

our $VERSION = '0.01';

# begin configurable information

# Change according to current phase

our $title = "PGSEM 2006-07 Q2";
our $footer = "Indian Institute of Management, Bangalore";

our $phase = 2;

our $default_cap = 65;
our $default_mincap = 15;
our $default_status = 'R'; # running
our $default_site = 'B'; # Bangalore
our $default_cgpa = 3.0; # CGPA used for allocation if data not available

our $max_cgpa = 4.0;
our $min_cgpa_four_courses = 2.75;
our $min_credits = 0; 

our $credits_pass = 93; 
# >=93 credits already taken => no seniority preference
# latest joining year upto which seniority preference is given
our $current_year = 2006;

our $max_courses = 4;
our $give_priority_to_seniors = 1;
our $give_priority_to_cgpa = 1;

# end configurable information

# end of file
