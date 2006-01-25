#!/usr/bin/perl -w

# $Id: elec.pl,v 1.2 2006/01/25 18:59:04 a14562 Exp $

# Copyright (c) 2006
# Sankaranaryananan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

# This program reads three files 
# 
# - courses.txt (course code, name, instructor, cap, slot)
# - students.txt (rollno, name, email, cgpa)
# - choices.txt (rollno, #courses, list of courses)
# 
# and allocates courses as per student preferences.
# 
# Seniority (yearwise), course priority, and CGPA are considered.
#
# invariants (at the end of allocation):
# 
# #students allotted per course < cap for the course
# 
# if (si, cj) is an allottement (si, cj) is a request
# -- only requested courses are allotted
# 
# if (si, cj) is not allotted with a reason capped,
# then all of the following are true:
# 
# number of allottments for cj == cap for cj
#
# there does not exist an allocation (sk, cj) where
# seniority(sk) < seniority(si) AND
#
# there does not exist an allocation (sk, cj) where
# seniority(sk) == senirority(si) AND
# priority(sk, ci) LOWER TO priority(si, cj)
#
# there does not exist an allocation (sk, ci) where
# seniority(sk) == senirority(si) AND
# priority(sk, cj) EQUALS priority(si, cj) AND
# cgpa(sk) < cgpa(si)
# 
# there does not exist an allocation (sk, ci) where
# seniority(sk) == senirority(si) AND
# priority(sk, cj) EQUALS priority(si, cj) AND
# cgpa(sk) == cgpa(si) AND
# rollno(sk) < rollno(si)
#
# if (si, cj) is not allotted with a reason schedule_conflict,
#
# there exists an (si, ck) which is allotted where 
# priority(si, ck) HIGHER TO priority(si, cj)
#


use strict;

# constants
my $default_cap = 70;
my $max_cgpa = 4.0;
my $min_credits = 36; # TODO verify
my $max_credits = 105; # TODO verify

my $credits_pass = 93; 
# >=93 credits already taken => no seniority preference
my $senior_year = 2003;
# latest year upto which seniority preference is given

my $max_courses = 4;
my $give_priority_to_seniors = 1;
my $give_priority_to_cgpa = 1;

my %courses;
# courses hash:
# key is course code
# value is a hash keyed by attributes:
# name, instructor, cap, slot
# invariants:
# code is never ''
# name, instructor never are undef but can be ''
# cap is always a valid number
# slot can be undef

my %students;
# students hash:
# key is rollno
# value is a hash keyed by attributes:
# name, email, cgpa (all loaded at the beginning) 
# and slot which is a hash keyed by integers 1..$max_slots
# where the value can be undef or 1
# 
# invariants:
# name, email are never undef but can be ''
# cgpa can be undef

my %choices;
# choices hash:
# key is rollno; exists in students hash
# value is a hash keyed by attributes:
# ncourses - number of courses applied for
# preflist - list of course codes in the order of preference
#            course code exists in courses hash

my %allocation;
# allocation hash:
# key is course code
# value is a hash keyed by attributes:
# studentlist - an array sorted by (seniority, priority, grade)
# nallotted - holds the number of students allotted
# rollno - hash keyed by rollno where value is a studentlist element
# 
# each studentlist element is hash reference where the hash holds
# rollno, priority, cgpa

sub err_print($)
{
    my $msg = shift;
    print STDERR $msg, "\n";
}

sub skip_line($)
{
    my $line = shift;
    return 1 if ($line =~ /^\s*\#/); # comment lines
    return 1 if ($line =~ /^\s*$/); # blank lines
    return 0;
}

sub load_courses($)
{
    my $file = shift;
    open IN, "<$file" or die "Can't open file $file: $!";
    while (<IN>) {
        chomp;
        next if skip_line($_);
        my ($code, $name, $instructor, $cap, $slot) = 
            split(/\s*\;\s*/, $_) unless skip_line($_); 

        $cap = undef if (defined($cap) && ($cap eq ''));
        $slot = undef if (defined($slot) && ($slot eq ''));

        if (!defined($code) || ($code eq "")) {
            err_print("error:$file:$.: no course code");
            next;
        }

        if (defined($courses{$code})) {
            err_print("error:$file:$.: course '$code' already defined");
            next;
        }

        if (defined($cap) && (($cap < 1) || ($cap > $default_cap))) {
            err_print("error:$file:$.: invalid cap '$cap'");
            next;
        }

        if (defined($slot) && !($slot =~ /[1234]/)) {
            err_print("error:$file:$.: invalid slot '$slot' - must be [1234]");
            next;
        }

        $name ||= "";
        $instructor ||= "";
        $cap ||= $default_cap;

        $courses{$code}{"name"} = $name;
        $courses{$code}{"instructor"} = $instructor;
        $courses{$code}{"cap"} = $cap;
        $courses{$code}{"slot"} = $slot;

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
            $courses{$code}{"slot"} || ""), "\n";
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
        my ($rollno, $name, $email, $cgpa, $credits) = 
            split(/\s*\;\s*/, $_) unless skip_line($_); 

        $cgpa = undef if (defined($cgpa) && ($cgpa eq ''));
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

        if (defined($credits) && (($credits < $min_credits) || ($cgpa > $max_credits))) {
            err_print("error:$file:$.: invalid credits '$credits'");
            ++$errors;
            next;
        }

        $name ||= "";
        $email ||= "";

        $students{$rollno}{"name"} = $name;
        $students{$rollno}{"email"} = $email;
        $students{$rollno}{"cgpa"} = $cgpa;
        $students{$rollno}{"credits"} = $credits;

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
            $students{$rollno}{"credits"} || ""), "\n";
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

        if ($ncourses != (keys %student_courses)) {
            err_print("error:$file:$.: mismatch in number of courses");
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

sub by_rank ($)
{
    my $course = shift;

    if ($give_priority_to_seniors) {
        my $ayear = substr($a->{"rollno"}, 0, 4);
        my $byear = substr($b->{"rollno"}, 0, 4);
        my $acredits = $students{$a->{"rollno"}}{"credits"};
        my $bcredits = $students{$b->{"rollno"}}{"credits"};
        if (($ayear <= $senior_year) && ($acredits < $credits_pass) && ($byear > $senior_year)) {
            return -1;
        }
        if (($ayear > $senior_year) && ($byear <= $senior_year) && ($bcredits < $credits_pass)) {
            return 1;
        }
    }

    my $retval = ($a->{"priority"} <=> $b->{"priority"});

    if ($give_priority_to_cgpa && ($retval == 0)) {
        if (defined($a->{"cgpa"}) && defined($b->{"cgpa"})) {
            $retval = ($b->{"cgpa"} <=> $a->{"cgpa"});
        }
        if ($retval == 0) {
            $retval = $a->{"rollno"} <=> $b->{"rollno"};
            err_print("warning: roll number based allocation: " .
                "'$course': $a->{'rollno'},$b->{'rollno'}");
        }
    }

    return $retval;
}

sub map_choices_to_courses 
{
    foreach my $rollno (keys %choices) {

        my @courselist = @{$choices{$rollno}{"courselist"}};
        for (my $index = 0; $index < @courselist; ++$index) {
            my $course = $courselist[$index];
            my %rec;
            $rec{"rollno"} = $rollno;
            $rec{"priority"} = $index + 1;
            $rec{"cgpa"} = $students{$rollno}{"cgpa"};
            push @{$allocation{$course}{"studentlist"}}, \%rec; 
        }
    }
}

sub sort_by_rank
{
    foreach my $course (keys %allocation) {
       @{$allocation{$course}{"studentlist"}} = 
           (sort { by_rank($course) } 
               @{$allocation{$course}{"studentlist"}});
    }
}

sub allocate_course($$)
{
    my ($rec, $course) = @_;

    $allocation{$course}{"nallotted"} ||= 0;

    $allocation{$course}{"rollno"}{$rec->{"rollno"}} = $rec;

    if ($allocation{$course}{"nallotted"} >= $courses{$course}{"cap"}) {
        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "capped";
        return 0;
    }

    my $slot = $courses{$course}{"slot"};

    my $already_allotted_course = $students{$rec->{"rollno"}}{"slot"}{$slot};
    
    if (defined($already_allotted_course)) {

        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "schedule_conflict: $already_allotted_course";
        return 0;
    }

    $rec->{"allotted"} = 1;
    $rec->{"reason"} = "allotted";
    $students{$rec->{"rollno"}}{"slot"}{$slot} = $course;
    ++$allocation{$course}{"nallotted"};
    return 1;
}

sub allocate_in_round($$)
{
    my ($round, $rec) = @_;

    my $year = substr($rec->{"rollno"}, 0, 4);
    my $credits = $students{$rec->{"rollno"}}{"credits"};
    my $flag = (($year <= $senior_year) && ($credits < $credits_pass));

    if ($round == 1) {
        return $flag;
    }

    if ($round == 2) {
        return !$flag;
    }
}

sub do_allocation ($)
{
    my $round = shift;

    my $maxpriority = scalar(keys %courses);

    for (my $priority = 1; $priority < $maxpriority; ++$priority) {

        foreach my $course (keys %allocation) {
            my @studentlist = @{$allocation{$course}{"studentlist"}};

            foreach my $rec (@studentlist) {
                next unless (allocate_in_round($round, $rec));
                next if ($rec->{"priority"} != $priority);
                allocate_course($rec, $course);
                print "$rec->{'rollno'}:$course:$rec->{'reason'}\n";
            }
        }
    }
}

sub allocate_courses
{
    map_choices_to_courses;
    sort_by_rank;

    my $errors = 0;
    foreach my $course (keys %courses) {
        unless (defined($courses{$course}{"slot"})) {
            ++$errors;
            err_print("error: no slot defined for $course");
        }
    }

    if ($errors) {
        err_print("error: can't do allocation due to previous error(s)");
        return 0;
    }

    do_allocation(1);
    do_allocation(2);

    return 1;
}

sub print_allocation_by_course
{
    print "=== Allocation by course ===\n";
    foreach my $course (sort keys %allocation) {
      print "$course:\n";
      foreach my $rec (@{$allocation{$course}{"studentlist"}}) {
        print "    ", 
            "rollno = ", $rec->{"rollno"}, ", ",
            "priority = ", $rec->{"priority"}, ", ",
            "cgpa = ", $rec->{"cgpa"} || "", ", ", 
            "reason = ", $rec->{"reason"} || "", "\n";
      }
      print "\n";
    }
    print "\n";
}

sub print_allocation_by_student
{
    print "=== Allocation by student ===\n";
    foreach my $rollno (sort keys %choices) {
        print "$rollno\n";
        foreach my $course (@{$choices{$rollno}{"courselist"}}) {
            print "    $course = ", 
                $allocation{$course}{"rollno"}{$rollno}->{"reason"} || "", "\n";

        }
    }
    print "\n";
}

sub get_students_for_course($$)
{
  my $course = shift;
  my $priority = shift;

  my %rollnoset;
  
  foreach my $rec (@{$allocation{$course}{"studentlist"}}) {
     $rollnoset{$rec->{"rollno"}} = 1 if ($rec->{"priority"} <= $priority);
  }

  return %rollnoset;
}

my @conflicts;

sub compute_conflicts
{
    foreach my $i (keys %courses) {
        foreach my $j (keys %courses) {
            next if $i eq $j;

            my %iset = get_students_for_course($i, 3); 
            my %jset = get_students_for_course($i, 3); 
            my %isect = ();

            foreach my $roll (keys %iset) {
                $isect{$roll} = 1 if (defined($jset{$roll}));
            }

            push @conflicts, 
                {"a" => $i, "b" => $j, "n" => scalar(keys %isect)};
        }
    }

    @conflicts = sort { $a->{"n"} <=> $b->{"n"} } @conflicts;

    print "=== Course conflicts ===\n";
    foreach my $rec (@conflicts) {
        print "$rec->{'a'} - $rec->{'b'}: $rec->{'n'}\n";
    } 
}

sub main
{
    load_courses("courses.txt");
    print_courses;

    load_students("students.txt");
    print_students;

    load_choices("choices.txt");
    print_choices;


    allocate_courses;
    print_allocation_by_course;
    print_allocation_by_student;

    compute_conflicts;
}

main;

# end of file
