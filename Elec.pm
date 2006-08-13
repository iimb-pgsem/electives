
# $Id: Elec.pm,v 1.3 2006/08/13 11:38:22 a14562 Exp $

# Copyright (c) 2006
# Sankaranaryananan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

# Elec.pm
# This module contains data structures populated by reading input files
# and routines to populate those data structures.

package Elec;

use strict;
use vars qw($VERSION @ISA @EXPORT @EXPORT_OK);

require Exporter;

@ISA = qw(Exporter AutoLoader);
# Items to export into callers namespace by default. Note: do not export
# names by default without a very good reason. Use EXPORT_OK instead.
# Do not simply export all your public functions/methods/constants.

@EXPORT = qw(
    %courses
    %students
    %project_students
    %p1_students
    %choices
    %p3choices

    year_from_rollno
    seniority_from_rollno
    load_courses
    print_courses
    load_students
    print_students
    load_project_students
    load_p1_students
    load_choices
    print_choices
);

my $VERSION = '0.01';

use ElecConfig;
use ElecUtils;

# begin data structures

our %courses;
# courses hash (read from courses.txt):
# key is course code
# value is a hash keyed by attributes:
# name, instructor, cap, slot
# invariants:
# code is never ''
# name, instructor never are undef but can be ''
# cap is always a valid number
# slot can be undef

our %students;
# students hash (read from students.txt):
# key is rollno
# value is a hash keyed by attributes:
# name, email, cgpa, credits, seniority, site (all loaded at the beginning) 
# and slot which is a hash keyed by integers 1..$max_slots
# where the value can be undef or 1
# 
# invariants:
# name, email are never undef but can be ''
# cgpa can be undef

our %project_students;
# project_students hash (read from project-students.txt; used in Phase 2 and 3)
# TODO: document

our %p1_students;
# p1 students hash (read from choices-p1.txt; used only in Phase 2):
# TODO: document

our %choices;
# choices hash (read from choices.txt):
# key is rollno; exists in students hash
# value is a hash keyed by attributes:
# ncourses - number of courses applied for
# preflist - list of course codes in the order of preference
#            course code exists in courses hash

our %p3choices;
# choices hash (read from choices.txt; used in Phase 2):
# key is rollno; exists in students hash
# value is a hash keyed by attributes:
# trtype - transaction type =~ /^[ADB]$/
# add - course to be added, defined if trtype =~ /^[AB]$/
# drop - course to be dropped, defined if trtype =~ /^[DB]$/
# status =~ /^[PDN]$/ meanings - Pending, Done, Not possible

# end data structures

sub year_from_rollno($)
{
    my $rollno = shift;

    my $year = substr($rollno, 0, 4);

    if ($rollno == 2004165) {
      # TODO: find a better way to handle this
      # Special exception
      $year = 2005;
    }

    $year =~ s/2021/2000/;
    $year =~ s/2104/2001/;
    $year =~ s/2204/2002/;

    return $year;
}

sub seniority_from_rollno($)
{
    my ($rollno) = shift;
    
    my $year = year_from_rollno($rollno);
    my $credits = $students{$rollno}{"credits"};
    if ($credits < $credits_pass && ($phase != 2 || defined($p1_students{$rollno}))) {
        return $year;
    } else {
        return $current_year;
    }
}

# load roll numbers of students who registered in phase 1
sub load_p1_students ($)
{
    my $filename = shift;

    open IN, "<$filename" or die "Can't open $filename: $!";

    while (<IN>) {
       chomp;
       s/;.*//;
       s/^\s*//g;
       s/\s*$//g;
       $p1_students{$_} = 1;
    }

    close IN;
}

# load roll numbers of students doing projects
sub load_project_students ($)
{
    my $filename = shift;

    open IN, "<$filename" or die "Can't open $filename: $!";

    while (<IN>) {
       chomp;
       s/^\s*//g;
       s/\s*$//g;
       $project_students{$_} = 1;
    }

    close IN;
}

sub load_courses($$)
{
    my $file = shift;
    my $internal = shift;  # TODO: find a better name

    open IN, "<$file" or die "Can't open file $file: $!";
    while (<IN>) {
        chomp;
        next if skip_line($_);
        my ($code, $name, $instructor, $cap, $slot, $status, $site, $barred, $mincap) = 
            split(/\s*\;\s*/, $_) unless skip_line($_); 

        $cap = undef if (defined($cap) && ($cap eq ''));
        $mincap = undef if (defined($mincap) && ($mincap eq ''));
        $slot = undef if (defined($slot) && ($slot eq ''));
        $status = undef if (defined($status) && ($status eq ''));
        $site = undef if (defined($site) && ($site eq ''));
        # status can be 'A' (active) or 'D' dropped
        my @sites_list = split(/\+/, $site);

        if (!defined($code) || ($code eq "")) {
            err_print("error:$file:$.: no course code");
            next;
        }

        if ($internal && defined($cap) && ($cap < 1)) {
            err_print("error:$file:$.: invalid cap '$cap'");
            next;
        }

        if ($internal && defined($cap) && defined($mincap) && ($cap <= $mincap)) {
            err_print("error:$file:$.: invalid cap mincap combination '$cap', '$mincap'");
            next;
        }

        if (defined($status) && !($status =~ /[ADN]/)) {
            err_print("error:$file:$.: invalid status '$status'");
            next;
        }

        if ($internal && defined($site) && !($site =~ /^.$/)) {
            err_print("error:$file:$.: invalid site '$site'");
            next;
        }

        $name ||= "";
        $instructor ||= "";
        $cap ||= $default_cap;
        $mincap ||= $default_mincap;
        $status ||= $default_status;
        $site ||= $default_site;
	    $code .= "-" . $site if ($internal);

        if (defined($courses{$code})) {
            err_print("error:$file:$.: course '$code' already defined");
            next;
        }


        $courses{$code}{"name"} = $name;
        $courses{$code}{"instructor"} = $instructor;
        $courses{$code}{"cap"} = $cap;
        $courses{$code}{"slot"} = $slot;
        $courses{$code}{"site"} = $site;
        $courses{$code}{"distributed"} = (@sites_list > 1 ? 1: 0);
        $courses{$code}{"status"} = $status;
        $courses{$code}{"mincap"} = $mincap;

    }
    close IN;
}

sub print_courses ()
{
    print "=== Courses ===\n";
    foreach my $code (sort keys %courses) {
        print join('; ',
            $code,
            $courses{$code}{"name"},
            $courses{$code}{"instructor"},
            $courses{$code}{"cap"},
            $courses{$code}{"slot"} || ""),
            $courses{$code}{"mincap"}, "\n";
    }
    print "\n";
}


sub load_students($)
{
    my $errors = 0;
    my $file = shift;
    open IN, "<$file" or die "Can't open file $file: $!";
    while (<IN>) {
        chomp;
        next if skip_line($_);

        my ($rollno, $name, $email, $cgpa, $credits, $site) = 
            split(/\s*\;\s*/, $_) unless skip_line($_); 

        $cgpa = $default_cgpa if (defined($cgpa) && ($cgpa eq ''));
        $credits = $min_credits if (defined($credits) && ($credits eq ''));

        if (!defined($rollno) || ($rollno eq "")) {
            err_print("error:$file:$.: no roll number");
            ++$errors;
            next;
        }

        if (defined($students{$rollno})) {
            err_print("error:$file:$.: roll number '$rollno' already defined");
            ++$errors;
            next;
        }

        if (defined($cgpa) && (($cgpa < 0) || ($cgpa > $max_cgpa))) {
            err_print("error:$file:$.: invalid cgpa '$cgpa'");
            ++$errors;
            next;
        }

        if (defined($credits) && ($credits < $min_credits)) {
            err_print("error:$file:$.: invalid credits '$credits'");
            ++$errors;
            next;
        }

        $name ||= "";
        $email ||= "";
	    $site ||= $default_site;

        $students{$rollno}{"name"} = $name;
        $students{$rollno}{"email"} = $email;
        $students{$rollno}{"cgpa"} = $cgpa;
        $students{$rollno}{"credits"} = $credits;
        $students{$rollno}{"seniority"} = seniority_from_rollno($rollno);
        $students{$rollno}{"site"} = $site;
    }

    close IN;
    return $errors;
}

sub print_students ()
{
    print "=== Students ===\n";
    foreach my $rollno (sort keys %students) {

        print join('; ',
            $rollno,
            $students{$rollno}{"name"},
            $students{$rollno}{"email"},
            $students{$rollno}{"cgpa"},
            $students{$rollno}{"credits"}), "\n";
    }
    print "\n";
}

sub load_choices($)
{
    my $file = shift;
    open IN, "<$file" or die "Can't open file $file: $!";
    LINE: while (<IN>) {
        chomp;
        next if skip_line($_);
        my ($rollno, $ncourses, $courselist) = 
            split(/\s*\;\s*/, $_) unless skip_line($_); 

        $ncourses = undef if (defined($ncourses) && ($ncourses eq ''));
        $courselist = undef if (defined($courselist) && ($courselist eq ''));

        if (!defined($rollno) || ($rollno eq "")) {
            err_print("error:$file:$.: no roll number");
            next;
        }

        unless (defined($students{$rollno})) {
            err_print("error:$file:$.: roll number '$rollno' not defined");
            next;
        }

        if (defined($choices{$rollno})) {
            err_print("error:$file:$.: roll number '$rollno' already defined");
            next;
        } 

        if (!defined($ncourses)) {
            err_print("error:$file:$.: number of courses not defined");
            next;
        }

        if (defined($ncourses) && 
            !(($ncourses >= 1) && ($ncourses <= $max_courses))) {
            err_print("error:$file:$.: invalid number of courses: '$ncourses'");
            next;
        }

        if (!defined($courselist)) {
            err_print("error:$file:$.: course list not defined");
            next;
        }

        my @student_courses = split(/\s*,\s*/, $courselist);
        my %student_courses;
        foreach my $course (@student_courses) {

	    $course .= "-" . $students{$rollno}{"site"};

            unless (defined($courses{$course})) {
                err_print("error:$file:$.: invalid course '$course'");
                next LINE;
            }
            if (defined($student_courses{$course})) {
                err_print("error:$file:$.: redefinition of course");
                next LINE;
            }
            $student_courses{$course} = 1;
        }

        if ($ncourses > (keys %student_courses)) {
            err_print("error:$file:$.: #choices < #courses");
            next LINE;
        }

        $choices{$rollno}{"ncourses"} = $ncourses;
        $choices{$rollno}{"courselist"} = \@student_courses;
                
    }
    close IN;
}

sub print_choices ()
{
    print "=== Choices ===\n";
    foreach my $rollno (sort keys %choices) {
        print join('; ',
            $rollno,
            $choices{$rollno}{"ncourses"},
            join(',', @{$choices{$rollno}{"courselist"}})), "\n";
    }
    print "\n";
}

1;

# end of file
