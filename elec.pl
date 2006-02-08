#!/usr/bin/perl -w

# $Id: elec.pl,v 1.8 2006/02/08 19:02:12 a14562 Exp $

# Copyright (c) 2006
# Sankaranaryananan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

# This program reads three files 
# 
# - courses.txt (course code, name, instructor, cap, slot)
# - students.txt (rollno, name, email, cgpa, credits)
# - choices.txt (rollno, #courses, list of courses)
# 
# and allocates courses as per student preferences.
# 
# seniority (based on batch and #credits), course priority, and CGPA are considered.
#
# conditions (at the end of allocation):
# 
# #students allotted per course < cap for the course
# #courses allotted to student <= #courses requested
# if (si, cj) is an allottement (si, cj) is a request
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
# priority(sk, cj) LOWER TO priority(si, cj)
#
# there does not exist an allocation (sk, ci) where
# seniority(sk) == senirority(si) AND
# priority(sk, cj) EQUALS priority(si, cj) AND
# cgpa(sk) < cgpa(si)
# 
# there does not exist an allocation (sk, cj) where
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

use Spreadsheet::WriteExcel;

# constants
my $default_cap = 65;
my $default_cgpa = 3.0;

my $max_cgpa = 4.0;
my $min_cgpa_four_courses = 2.75;
my $min_credits = 12; # TODO verify
my $max_credits = 105; # TODO verify

my $credits_pass = 93; 
# >=93 credits already taken => no seniority preference
my $senior_year = 2003;
# latest joining year upto which seniority preference is given
my $current_year = 2004;

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

my @ranklist; 
# ranklist covering all students (not specific to courses)

# Excel properties
my $rollno_width = 15;
my $name_width = 35;
my $email_width = 35;
my $allotted_color = '#CCFFFF';
my $capped_color = '#FFCC00';
my $complete_color = '#C0C0C0';
my $sc_color = '#FF00FF';
my $ot_color = '#FF9900';

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

sub year_from_rollno($)
{
    my $rollno = shift;

    my $year = substr($rollno, 0, 4);
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
    if (($year <= $senior_year) && ($credits < $credits_pass)) {
        return $year;
    } else {
        return $current_year;
    }
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
        $students{$rollno}{"seniority"} = seniority_from_rollno($rollno);

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

sub by_student_rank
{
    my $retval;

    if ($give_priority_to_seniors) {
        $retval = $students{$a}{"seniority"} <=> 
                  $students{$b}{"seniority"};
        return $retval if ($retval != 0);
    }

    if ($give_priority_to_cgpa) {
        if (defined($students{$a}{"cgpa"}) && defined($students{$b}{"cgpa"})) {
            $retval = ($students{$b}{"cgpa"} <=> $students{$a}{"cgpa"});
            return $retval if ($retval != 0);
        }
    }

    $retval = $a <=> $b;
    return $retval;
}

sub by_rank ($)
{
    my $course = shift;
    my $retval;

    if ($give_priority_to_seniors) {
        $retval = $students{$a->{"rollno"}}{"seniority"} <=> 
                  $students{$b->{"rollno"}}{"seniority"};
        return $retval if ($retval != 0);
    }

    $retval = ($a->{"priority"} <=> $b->{"priority"});

    if ($give_priority_to_cgpa && ($retval == 0)) {
        if (defined($a->{"cgpa"}) && defined($b->{"cgpa"})) {
            $retval = ($b->{"cgpa"} <=> $a->{"cgpa"});
        }
        if ($retval == 0) {
            $retval = $a->{"rollno"} <=> $b->{"rollno"};
            err_print("warning: roll number based ranking: " .
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
            $rec{"credits"} = $students{$rollno}{"credits"};
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

sub get_allotted_course($$)
{
    my ($rec, $slot) = @_;
    return undef if (!defined($slot));
    my @cslots = split(/\s*,\s*/, $slot);
    for my $s (@cslots) {

        if (defined($students{$rec->{"rollno"}}{"slot"}{$s})) {

            return $students{$rec->{"rollno"}}{"slot"}{$s};
        }
    }
    return undef;
}

sub fill_student_slots($$$)
{
    my ($rollno, $slot, $course) = @_;
    return if (!defined($slot));
    my @cslots = split(/\s*,\s*/, $slot);
    for my $s (@cslots) {

        $students{$rollno}{"slot"}{$s} = $course;
    }
}

sub allocate_course($$)
{
    my ($rec, $course) = @_;

    my $rollno = $rec->{"rollno"};
    $choices{$rollno}{"nallotted"} ||= 0;
    $allocation{$course}{"nallotted"} ||= 0;

    $allocation{$course}{"rollno"}{$rollno} = $rec;

    if ($choices{$rollno}{"nallotted"} >= $choices{$rollno}{"ncourses"}) {
        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "complete";
        return 0;
    }

    if (($choices{$rollno}{"nallotted"} == 3) &&
        ($students{$rollno}{'cgpa'} < $min_cgpa_four_courses)) {
        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "onlythree";
        return 0;
    }

    if ($allocation{$course}{"nallotted"} >= $courses{$course}{"cap"}) {
        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "capped";
        return 0;
    }

    my $slot = $courses{$course}{"slot"};

    my $already_allotted_course = get_allotted_course($rec, $slot);

    if (defined($already_allotted_course)) {

        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "schedule_conflict: $already_allotted_course";
        return 0;
    }

    $rec->{"allotted"} = 1;
    $rec->{"reason"} = "allotted";
    fill_student_slots($rollno, $slot, $course);
    ++$choices{$rollno}{"nallotted"};
    ++$allocation{$course}{"nallotted"};
    return 1;
}

sub allocate_in_round($$)
{
    my ($round, $rec) = @_;

    my $seniority = seniority_from_rollno($rec->{"rollno"});
    return ($round == $seniority);
}

sub do_allocation ($)
{
    my $round = shift;

    my $maxpriority = scalar(keys %courses);

    for (my $priority = 1; $priority <= $maxpriority; ++$priority) {

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

    # TODO: derive years automatically 

    for (my $year = 2002; $year <= $current_year; ++$year) {
      do_allocation($year);
    }

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
            "credits = ", $rec->{"credits"} || "", ", ", 
            "cgpa = ", $rec->{"cgpa"} || "", ", ", 
            "reason = ", $rec->{"reason"} || "", "\n";
      }
      print "\n";
    }
    print "\n";
}

sub get_format
{
  my ($rec, $formats) = @_;

  if ($rec->{'reason'} eq 'allotted') {
    return $formats->[0];
  }
  if ($rec->{'reason'} eq 'capped') {
    return $formats->[1];
  }
  if ($rec->{'reason'} eq 'complete') {
    return $formats->[2];
  }
  if ($rec->{'reason'} =~ 'schedule_conflict') {
    return $formats->[3];
  }
  if ($rec->{'reason'} eq 'onlythree') {
    return $formats->[4];
  }
}

sub write_excel
{
    # Generate two workbooks, internal and external.
    my $workbookint = Spreadsheet::WriteExcel->new("allocation-internal.xls");
    my $workbookext = Spreadsheet::WriteExcel->new("allocation.xls");

    # color pallettes for both
    $workbookint->set_custom_color(40, $allotted_color);
    $workbookint->set_custom_color(41, $capped_color);
    $workbookint->set_custom_color(42, $complete_color);
    $workbookint->set_custom_color(43, $sc_color);
    $workbookint->set_custom_color(44, $ot_color);

    $workbookext->set_custom_color(40, $allotted_color);
    $workbookext->set_custom_color(41, $capped_color);
    $workbookext->set_custom_color(42, $complete_color);
    $workbookext->set_custom_color(43, $sc_color);
    $workbookext->set_custom_color(44, $ot_color);

    my $allotted_cfint = $workbookint->add_format(bg_color=>40);
    my $capped_cfint = $workbookint->add_format(bg_color=>41);
    my $complete_cfint = $workbookint->add_format(bg_color=>42);
    my $sc_cfint = $workbookint->add_format(bg_color=>43);
    my $ot_cfint = $workbookint->add_format(bg_color=>44);
    my @intformats = ($allotted_cfint, $capped_cfint, $complete_cfint, $sc_cfint, $ot_cfint);

    my $allotted_cfext = $workbookext->add_format(bg_color=>40);
    my $capped_cfext = $workbookext->add_format(bg_color=>41);
    my $complete_cfext = $workbookext->add_format(bg_color=>42);
    my $sc_cfext = $workbookext->add_format(bg_color=>43);
    my $ot_cfext = $workbookext->add_format(bg_color=>44);
    my @extformats = ($allotted_cfext, $capped_cfext, $complete_cfext, $sc_cfext, $ot_cfext);

    # Headers for both
    my @headerint = ('Rank', 'Roll Number', 'Name', 'E-mail',
                     'Priority', 'Credits', 'CGPA', 'Status');

    my @headerext = ('Roll Number', 'Name', 'E-mail');

    my $formatint = $workbookint->add_format();
    $formatint->set_bold();
    my $formatext = $workbookext->add_format();
    $formatext->set_bold();

    my $summaryint = $workbookint->add_worksheet("Summary");
    my $summaryext = $workbookext->add_worksheet("Summary");
    my $coursecount = 0;
    my %studentrow;

    $summaryint->write(0, 0, "Roll Number", $formatint);
    $summaryint->set_column(0, 0, $rollno_width);
    $summaryint->write(0, 1, "Name", $formatint);
    $summaryint->set_column(1, 1, $name_width);

    $summaryext->write(0, 0, "Roll Number", $formatext);
    $summaryext->set_column(0, 0, $rollno_width);
    $summaryext->write(0, 1, "Name", $formatext);
    $summaryext->set_column(1, 1, $name_width);

    my @courses = sort keys %allocation;

    foreach my $course (sort keys %allocation) {

        print "Writing spreadsheet information for $course\n";
        my $sheetint = $workbookint->add_worksheet($course);
        my $sheetext = $workbookext->add_worksheet($course);

        $summaryint->write(0, $coursecount + 2, $course, $formatint);
        $summaryext->write(0, $coursecount + 2, $course, $formatext);

        my $row = 0;
        my $col = 0;

        for ($col = 0; $col < @headerint; ++$col) {
            $sheetint->write($row, $col, $headerint[$col], $formatint);
        }

        for ($col = 0; $col < @headerext; ++$col) {
            $sheetext->write($row, $col, $headerext[$col], $formatext);
        }

        $row = 1;
        $col = 0;

        my $count = 1;

        foreach my $rec (@{$allocation{$course}{"studentlist"}}) {

            $sheetint->write($row, $col++, $count, get_format($rec, \@intformats));

            $sheetint->set_column($col, $col, $rollno_width);
            $sheetint->write($row, $col++, $rec->{"rollno"}, get_format($rec, \@intformats));
            
            $sheetint->set_column($col, $col, $name_width);
            $sheetint->write($row, $col++, $students{$rec->{"rollno"}}{"name"}, get_format($rec, \@intformats));

            $sheetint->set_column($col, $col, $email_width);
            $sheetint->write($row, $col++, $students{$rec->{"rollno"}}{"email"}, get_format($rec, \@intformats));

            $sheetint->write($row, $col++, $rec->{"priority"}, get_format($rec, \@intformats));
            $sheetint->write($row, $col++, $rec->{"credits"}, get_format($rec, \@intformats));
            $sheetint->write($row, $col++, $rec->{"cgpa"}, get_format($rec, \@intformats));
            $sheetint->write($row, $col++, $rec->{"reason"}, get_format($rec, \@intformats));

            $studentrow{$rec->{"rollno"}}->[$coursecount]
              = ($rec->{"allotted"} == 1 ? 1 : undef);
            ++$row;
            ++$count;
            $col = 0;
        }

        $row = 1;
        $col = 0;

        foreach my $rec (sort {$a->{"rollno"} cmp $b->{"rollno"}}
                         @{$allocation{$course}{"studentlist"}}) {

            if ($rec->{"allotted"} == 1) {

                $sheetext->set_column($col, $col, $rollno_width);
                $sheetext->write($row, $col++, $rec->{"rollno"});
                $sheetext->set_column($col, $col, $name_width);
                $sheetext->write($row, $col++, $students{$rec->{"rollno"}}{"name"});
                $sheetext->set_column($col, $col, $email_width);
                $sheetext->write($row, $col++, $students{$rec->{"rollno"}}{"email"});

                ++$row;
                $col = 0;
            }
        }
        ++$coursecount;
    }

    my $row = 1;
    foreach my $studentno (sort keys %studentrow) {

        print "Writing summary for $studentno\n";
        $summaryint->write($row, 0, $studentno);
        $summaryint->write($row, 1, $students{$studentno}->{"name"});
        $summaryext->write($row, 0, $studentno);
        $summaryext->write($row, 1, $students{$studentno}->{"name"});
        for (my $courseno = 0; $courseno < $coursecount; ++$courseno) {

            if (defined($studentrow{$studentno}->[$courseno])) {

                $summaryint->write($row, $courseno + 2, $courses[$courseno]);
                $summaryext->write($row, $courseno + 2, $courses[$courseno]);
            }
        }
        ++$row;
    }
}

sub write_choices_excel ($$) 
{
    my $filename = shift;
    my $show_results = shift;

    @ranklist = sort { by_student_rank } (keys %students);
    print join("\n", @ranklist);

    my $workbook = Spreadsheet::WriteExcel->new($filename);
    my $sheet = $workbook->add_worksheet("Choices");

    # color pallettes for both
    $workbook->set_custom_color(40, $allotted_color);
    $workbook->set_custom_color(41, $capped_color);
    $workbook->set_custom_color(42, $complete_color);
    $workbook->set_custom_color(43, $sc_color);
    $workbook->set_custom_color(44, $ot_color);

    my $allotted_cf = $workbook->add_format(bg_color=>40);
    my $capped_cf = $workbook->add_format(bg_color=>41);
    my $complete_cf = $workbook->add_format(bg_color=>42);
    my $sc_cf = $workbook->add_format(bg_color=>43);
    my $ot_cf = $workbook->add_format(bg_color=>44);
    my @formats = ($allotted_cf, $capped_cf, $complete_cf, $sc_cf, $ot_cf);

    my $formatbold = $workbook->add_format();
    $formatbold->set_bold();

    my $row = 0;
    my $col = 0;

    $sheet->write($row, $col++, "Rank", $formatbold);

    $sheet->set_column($col, $col, $rollno_width);
    $sheet->write($row, $col++, "Roll Number", $formatbold);

    $sheet->set_column($col, $col, $name_width);
    $sheet->write($row, $col++, "Name", $formatbold);

    $sheet->write($row, $col++, "Credits", $formatbold);
    $sheet->write($row, $col++, "CGPA", $formatbold);
    $sheet->write($row, $col++, "#Courses", $formatbold);

    for (my $priority = 1; $priority <= (keys %courses); ++$priority) {
      $sheet->write($row, $col++, "P$priority", $formatbold);
      $sheet->write($row, $col++, "P$priority Status", $formatbold) if $show_results;
    }

    ++$row;
    $col = 0;

    foreach my $rollno (@ranklist) {

      next unless $choices{$rollno};

      $sheet->write($row, $col++, $row+1);
      $sheet->write($row, $col++, $rollno);
      $sheet->write($row, $col++, $students{$rollno}{'name'});
      $sheet->write($row, $col++, $students{$rollno}{'credits'});
      $sheet->write($row, $col++, $students{$rollno}{'cgpa'});
      $sheet->write($row, $col++, $choices{$rollno}{'ncourses'});

      for (my $priority = 1; $priority <= (keys %courses); ++$priority) {
        my $course = $choices{$rollno}{'courselist'}->[$priority-1];
        if ($course) {
          my $rec = $allocation{$course}{"rollno"}{$rollno};
          $sheet->write($row, $col++, $course, $show_results ? get_format($rec, \@formats) : undef);
          $sheet->write($row, $col++, $rec->{'reason'}, get_format($rec, \@formats)) if $show_results;
        } else {
          $col++;
          $col++ if $show_results;
        }
      }

      ++$row;
      $col = 0;
    }
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

    write_excel();
    write_choices_excel("choices.xls", 0);
    write_choices_excel("choices-and-results.xls", 1);
}

main;

# end of file

