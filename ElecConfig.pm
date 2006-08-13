
# $Id: ElecConfig.pm,v 1.4 2006/08/13 13:57:04 a14562 Exp $

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
    %config_info

    $phase

    $adminpassword
    $login
    $password
    $datasource
    $dblogin
    $dbpassword

    $quarter_str
    $quarter_starts_str

    $send_email
    $pop_required
    $deadline
    $deadline_str

    $moodle_url

    $title
    $footer
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
    $footer

    read_config_info
    assign_config_info
);

our $VERSION = '0.01';

# === begin configurable information ===
# read from config.txt using read_config_info and assign_config_info

our %config_info;

# ==== shared information
our $phase;

# === CGI information

our $adminpassword;
our $login;
our $password;
our $datasource;
our $dblogin;
our $dbpassword;

our $quarter_str;
our $quarter_starts_str; # text field for printing

our $send_email;
our $pop_required;
our $deadline;
our $deadline_str; # derived from deadline

our $moodle_url;

our $title; # derived variable

# === internal information

our $default_cap;
our $default_mincap;
our $default_status; 
our $default_site;
our $default_cgpa;

our $max_cgpa;
our $min_cgpa_four_courses;
our $min_credits; 

our $credits_pass; 
our $current_year;

our $max_courses;
our $give_priority_to_seniors;
our $give_priority_to_cgpa;

our $footer;

# === end configurable information ===

use POSIX;

sub read_config_info ($)
{
    my $file = shift;
    open IN, "<$file" or die "Cannot read $file: $!";
    while (<IN>) {
        chomp;
        next if (/^\s*$/);
        next if (/^\s*\#/);
        my ($key, @value_tokens) = split(/\s*=\s*/);
        $config_info{$key} = join("=", @value_tokens);
    }
    close IN;
}

sub assign_config_info 
{
    $phase = $config_info{'phase'};

    $adminpassword = $config_info{'adminpassword'};
    $login = $config_info{'login'};
    $password = $config_info{'password'};
    $datasource = $config_info{'datasource'};
    $dblogin = $config_info{'dblogin'};
    $dbpassword = $config_info{'dbpassword'};
    $quarter_str = $config_info{'quarter_str'};
    $quarter_starts_str = $config_info{'quarter_starts_str'};
    $send_email = $config_info{'send_email'};
    $pop_required = $config_info{'pop_required'};

    my $d = $config_info{'deadline'};
    my ($year, $month, $day) = split(/-/, $d);
    $deadline = POSIX::mktime(0, 0, 0, $day, $month - 1, $year - 1900);
    $deadline_str = POSIX::strftime('00:00 hours %d %b, %Y', 0, 0, 0, $day, $month - 1, $year - 1900);

    $moodle_url = $config_info{'moodle_url'};

    # assign to derived variables
    $title = "PGSEM " . $quarter_str . " Phase $phase Electives Submission";
    $footer = "Indian Institute of Management, Bangalore";

    $default_cap = $config_info{'default_cap'};
    $default_mincap = $config_info{'default_mincap'};
    $default_status = $config_info{'default_status'};
    $default_site = $config_info{'default_site'};
    $default_cgpa = $config_info{'default_cgpa'};

    $max_cgpa = $config_info{'max_cgpa'};
    $min_cgpa_four_courses = $config_info{'min_cgpa_four_courses'};
    $min_credits = $config_info{'min_credits'};
    $credits_pass = $config_info{'credits_pass'};
    $current_year = $config_info{'current_year'};
    $max_courses = $config_info{'max_courses'};
    $give_priority_to_seniors = $config_info{'give_priority_to_seniors'};
    $give_priority_to_cgpa = $config_info{'give_priority_to_cgpa'};
}

1;

# end of file
