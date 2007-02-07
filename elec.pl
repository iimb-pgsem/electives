#!/usr/bin/perl -w

# $Id: elec.pl,v 1.25 2007/02/07 18:14:30 a14562 Exp $

# Copyright (c) 2006
# Sankaranaryananan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

# This program reads the following files 
# 
# - courses.txt (code, name, instructor, cap, slot, status, site, barred)
# - students.txt (rollno, name, email, cgpa, credits, site)
# - choices.txt (rollno, #courses, list of courses)
# - project_students.txt (rollno)
# 
# and allocates courses as per student preferences
# for Phases 2 and 3 of the allocation process.
#
# The electives allocation process is explained in detail at:
# http://sankara.net/pgsem/electives-allocation.html
#
# The following factors determine the student "rank" for a course:
#
# seniority (based on batch and #credits)
# course priority
# CGPA
#
# conditions (at the end of allocation):
# TODO: sync up with http://sankara.net/pgsem/electives-allocation.html
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
use ElecUtils;
use ElecConfig;
use Elec;

my $p3mailbodies_path = "p3mailbodies/";

my %allocation;
# allocation hash (computed hash):
# key is course code
# value is a hash keyed by attributes:
# studentlist - an array sorted by (seniority, priority, grade)
# nallotted - holds the number of students allotted
# rollno - hash keyed by rollno where value is a studentlist element
# 
# each studentlist element is hash reference where the hash holds
# rollno, priority, cgpa

my %p3choices;
# choices hash:
# key is rollno; exists in students hash
# value is a hash keyed by attributes:
# trtype - transaction type =~ /^[ADS]$/
# add - course to be added, defined if trtype =~ /^[AS]$/
# drop - course to be dropped, defined if trtype =~ /^[DS]$/
# status =~ /^[PDN]$/ meanings - Pending, Done, Not possible

my @late_changes;
# late changes list
# each item is a hash keyed by attributes:
# rollno - roll no
# trtype - transaction type =~ /^[ADX]$/
# courses - a list of course ids

my %p3salloc;
# allocation hash (computed) as input for phase 3 by students
# key is student roll no
# value is a hash keyed by attributes:
# courses - a hash on course ids allotted

my %p3calloc;
# allocation hash (computed) as input for phase 3 by courses
# key is course id
# nstudents is no of students
# students - a hash on student rollno allotted

my %courses_capped;
# list of courses capped (computed)
# key is course code
# value is a hash keyed by attributes
# year, priority, cgpa at which the course capped

my %trtype_label =
  (
   "A" => "Add",
   "D" => "Drop",
   "S" => "Swap"
  );

my %status_label =
  (
   "D" => "Successful",
   "N" => "Unsuccessful",
   "P" => "Pending"
  );

my @ranklist; 
# ranklist (computed) covering all students (not specific to courses)

# Excel properties
my $rollno_width = 15;
my $name_width = 35;
my $email_width = 35;
my $status_width = 20;

my $allotted_color = '#CCFFFF';
my $capped_color = '#FFCC00';
my $complete_color = '#C0C0C0';
my $sc_color = '#FF00FF';
my $ot_color = '#FF9900';
my $dropped_color = '#008080';
my $successful_color = '#80FF80';
my $unsuccessful_color = '#FF8080';
my $pending_color = '#0000FF';

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
            # err_print("warning: roll number based ranking: " .
            #   "'$course': $a->{'rollno'},$b->{'rollno'}");
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

sub courses_conflict($$)
{
    my ($c1, $c2) = @_;
    return undef if (!defined($courses{$c1}{"slot"}));
    return undef if (!defined($courses{$c2}{"slot"}));
    my @c1s = split(/\s*,\s*/, $courses{$c1}{"slot"});
    my @c2s = split(/\s*,\s*/, $courses{$c2}{"slot"});
    for my $s1 (@c1s) {

      for my $s2 (@c2s) {

	return 1 if ($s1 eq $s2);
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

sub allocate_course($$$)
{
    my ($rec, $course, $priority) = @_;

    my $rollno = $rec->{"rollno"};
    $choices{$rollno}{"nallotted"} ||= 0;
    $allocation{$course}{"nallotted"} ||= 0;

    $allocation{$course}{"rollno"}{$rollno} = $rec;

    if ($choices{$rollno}{"nallotted"} >= $choices{$rollno}{"ncourses"}) {
        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "Complete";
        return 0;
    }

    my $allowed = $students{$rollno}{"nallowed"};

    if (($choices{$rollno}{"nallotted"} == $allowed) &&
        ($allowed < $max_courses)) {

        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "Allowed:" . $allowed;
        return 0;
    }

    if ($courses{$course}{"status"} eq 'D') {
        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "Dropped";
        return 0;
    }

    if ($courses{$course}{"status"} eq 'N') {
        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "NotAvailable";
        return 0;
    }

    my $slot = $courses{$course}{"slot"};

    my $already_allotted_course = get_allotted_course($rec, $slot);

    if (defined($already_allotted_course)) {

        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "SC:$already_allotted_course";
        return 0;
    }

    if ($allocation{$course}{"nallotted"} >= $courses{$course}{"cap"}) {
        $rec->{"allotted"} = 0;
        $rec->{"reason"} = "Capped";
	++$courses_capped{$course}{"nrejected"};
        return 0;
    }

    $rec->{"allotted"} = 1;
    $rec->{"reason"} = "Allotted";
    fill_student_slots($rollno, $slot, $course);
    ++$choices{$rollno}{"nallotted"};
    ++$allocation{$course}{"nallotted"}; 
    if ($allocation{$course}{"nallotted"} == $courses{$course}{"cap"}) {

      # Course is capped
      $courses_capped{$course}{"year"} = $students{$rollno}{"seniority"};
      $courses_capped{$course}{"priority"} = $priority;
      $courses_capped{$course}{"cgpa"} = $students{$rollno}{"cgpa"};
    }
    return 1;
}

sub allocate_in_round($$)
{
    my ($round, $rec) = @_;

    my $seniority = $students{$rec->{"rollno"}}{"seniority"};
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
                allocate_course($rec, $course, $priority);
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

    for (my $year = 2002; $year <= $current_year + 1; ++$year) {
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

  if ($rec->{'reason'} eq 'Allotted') {
    return $formats->[0];
  }
  if ($rec->{'reason'} eq 'Capped') {
    return $formats->[1];
  }
  if ($rec->{'reason'} eq 'Complete') {
    return $formats->[2];
  }
  if ($rec->{'reason'} =~ 'SC') {
    return $formats->[3];
  }
  if ($rec->{'reason'} =~ 'Allowed') {
    return $formats->[4];
  }
  if ($rec->{'reason'} eq 'Dropped') {
    return $formats->[5];
  }
}

sub all_students
{
  return 1;
}

sub chennai_students
{
  my $roll = shift;
  if ($students{$roll}{"site"} eq "C") {

    return 1;
  }
  return 0;
}

sub only_2005_students
{
  my $roll = shift;
  if ($students{$roll}{"seniority"} == 2005) { # TODO fix hard coding

    return 1;
  }
  return 0;
}

sub only_senior_students
{
  my $roll = shift;
  if ($students{$roll}{"seniority"} != 2005) { # TODO fix hard coding

    return 1;
  }
  return 0;
}

sub write_conflicts
{
  my $fptr = shift;
  my $conflictint = shift;
  my $title = shift;
  my $rowoffset = shift;
  my $formatint = shift;

  $rowoffset *= (scalar(keys %courses) + 4);
  $conflictint->write($rowoffset, 0, $title, $formatint);
  ++$rowoffset;

    my $count = 0;
    my %courseNum;
    my @conflictsall;
    compute_conflicts(\@conflictsall, $fptr);

    foreach my $i (sort keys %courses) {

      #print "Course $i is $count\n";
      $courseNum{$i} = $count;
      $conflictint->write($rowoffset, $count + 1, $i);
      $conflictint->write($rowoffset + $count + 1, 0, $i);
      ++$count;
    }
  
    foreach my $rec (@conflictsall) {

      #print "Conflict: $rec->{'a'} ($courseNum{$rec->{'a'}}) - $rec->{'b'} ($courseNum{$rec->{'b'}}): $rec->{'n'}\n";
      if ($courseNum{$rec->{'a'}} >= $courseNum{$rec->{'b'}}) {

	$conflictint->write($rowoffset + $courseNum{$rec->{'a'}} + 1,
			    $courseNum{$rec->{'b'}} + 1,
			    $rec->{'n'});
      }
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
    $workbookint->set_custom_color(45, $dropped_color);

    $workbookext->set_custom_color(40, $allotted_color);
    $workbookext->set_custom_color(41, $capped_color);
    $workbookext->set_custom_color(42, $complete_color);
    $workbookext->set_custom_color(43, $sc_color);
    $workbookext->set_custom_color(44, $ot_color);
    $workbookext->set_custom_color(45, $dropped_color);

    my $allotted_cfint = $workbookint->add_format(bg_color=>40);
    my $capped_cfint = $workbookint->add_format(bg_color=>41);
    my $complete_cfint = $workbookint->add_format(bg_color=>42);
    my $sc_cfint = $workbookint->add_format(bg_color=>43);
    my $ot_cfint = $workbookint->add_format(bg_color=>44);
    my $dropped_cfint = $workbookint->add_format(bg_color=>45);
    my @intformats = ($allotted_cfint, $capped_cfint, $complete_cfint, 
                      $sc_cfint, $ot_cfint, $dropped_cfint);

    my $allotted_cfext = $workbookext->add_format(bg_color=>40);
    my $capped_cfext = $workbookext->add_format(bg_color=>41);
    my $complete_cfext = $workbookext->add_format(bg_color=>42);
    my $sc_cfext = $workbookext->add_format(bg_color=>43);
    my $ot_cfext = $workbookext->add_format(bg_color=>44);
    my $dropped_cfext = $workbookext->add_format(bg_color=>45);
    my @extformats = ($allotted_cfext, $capped_cfext, $complete_cfext, 
                      $sc_cfext, $ot_cfext, $dropped_cfext);

    # Headers for both
    my @headerint = ('Rank', 'Alloc No', 'Roll Number', 'Name', 'E-mail',
                     'Priority', 'Credits', 'CGPA', 'Status');

    my @headerext = ('SNo', 'Roll Number', 'Name', 'E-mail');

    my $formatint = $workbookint->add_format();
    $formatint->set_bold();
    my $formatext = $workbookext->add_format();
    $formatext->set_bold();

    write_choices_excel($workbookint, "Choices", 0, \@intformats);
    write_choices_excel($workbookint, "Allocation", 1, \@intformats);

    my $summaryint = $workbookint->add_worksheet("Summary");
    $summaryint->set_paper(9);
    $summaryint->set_landscape();
    $summaryint->fit_to_pages(1);
    $summaryint->set_header("&C$title: &A");
    $summaryint->set_footer("&C$footer&R&P of &N");

    my $summaryext = $workbookext->add_worksheet("Summary");
    $summaryext->set_paper(9);
    $summaryext->set_landscape();
    $summaryext->fit_to_pages(1);
    $summaryext->set_header("&C$title: &A");
    $summaryext->set_footer("&C$footer&A&R&P of &N");

    $summaryint->write(0, 0, "Roll Number", $formatint);
    $summaryint->set_column(0, 0, $rollno_width);
    $summaryint->write(0, 1, "Name", $formatint);
    $summaryint->set_column(1, 1, $name_width);
    $summaryint->write(0, 2, "#Courses", $formatint);

    $summaryext->write(0, 0, "Roll Number", $formatext);
    $summaryext->set_column(0, 0, $rollno_width);
    $summaryext->write(0, 1, "Name", $formatext);
    $summaryext->set_column(1, 1, $name_width);
    $summaryext->write(0, 2, "#Courses", $formatext);


    my $capsint = $workbookint->add_worksheet("Caps");
    $capsint->set_paper(9);
    $capsint->set_landscape();
    $capsint->fit_to_pages(1);
    $capsint->set_header("&C$title: &A");
    $capsint->set_footer("&C$footer&R&P of &N");

    my $capsext = $workbookext->add_worksheet("Caps");
    $capsext->set_paper(9);
    $capsext->set_landscape();
    $capsext->fit_to_pages(1);
    $capsext->set_header("&C$title: &A");
    $capsext->set_footer("&C$footer&A&R&P of &N");

    $capsint->write(0, 0, "Course id", $formatint);
    $capsint->write(0, 1, "Seniority", $formatint);
    $capsint->write(0, 2, "Priority", $formatint);
    $capsint->write(0, 3, "CGPA", $formatint);
    $capsint->write(0, 4, "# rejected", $formatint);
    $capsint->write(0, 5, "# enrolled", $formatint);
    $capsint->write(0, 6, "# available", $formatint);

    $capsext->write(0, 0, "Course id", $formatint);
    $capsext->write(0, 1, "Seniority", $formatext);
    $capsext->write(0, 2, "Priority", $formatext);
    $capsext->write(0, 3, "CGPA", $formatext);
    $capsext->write(0, 4, "# rejected", $formatext);
    $capsext->write(0, 5, "# enrolled", $formatext);
    $capsext->write(0, 6, "# available", $formatext);

    {
      my $row = 1;
      for my $c (sort keys %courses) {

        if ($courses{$c}{"status"} ne 'A') {

	  $capsint->write($row, 0, $c, $formatint);
	  $capsint->write($row, 1, "---------- Course dropped ----------");

	  $capsext->write($row, 0, $c);
	  $capsext->write($row, 1, "---------- Course dropped ----------");
	}
	elsif (defined($courses_capped{$c})) {

	  my $y = $courses_capped{$c}{"year"};
	  my $yi = $y;
	  my $ye = $y;
	  if ($y == $current_year + 1) {

	    $yi = "LATE";
	    $ye = "None";
	  }
	  elsif ($y == $current_year) {

	    $yi = "MISSED";
	    $ye = "None";
	  }
	  $capsint->write($row, 0, $c, $formatint);
	  $capsint->write($row, 1, $yi);
	  $capsint->write($row, 2, $courses_capped{$c}{"priority"});
	  $capsint->write($row, 3, $courses_capped{$c}{"cgpa"});
	  $capsint->write($row, 4, $courses_capped{$c}{"nrejected"} || 0);
	  $capsint->write($row, 5, $allocation{$c}{"nallotted"});
	  $capsint->write($row, 6, 0);

	  $capsext->write($row, 0, $c);
	  $capsext->write($row, 1, $ye);
	  $capsext->write($row, 2, $courses_capped{$c}{"priority"});
	  $capsext->write($row, 3, $courses_capped{$c}{"cgpa"});
	  $capsext->write($row, 4, $courses_capped{$c}{"nrejected"} || 0);
	  $capsext->write($row, 5, $allocation{$c}{"nallotted"});
	  $capsext->write($row, 6, 0);
	}
	else {
	  $capsint->write($row, 0, $c, $formatint);
	  $capsint->write($row, 1, "-");
	  $capsint->write($row, 2, "-");
	  $capsint->write($row, 3, "-");
	  $capsint->write($row, 4, "-");
	  $capsint->write($row, 5, $allocation{$c}{"nallotted"} || 0);
	  $capsint->write($row, 6, $courses{$c}{"nocap"}
			  ?"NA"
			  :($courses{$c}{"cap"} - ($allocation{$c}{"nallotted"}||0)));

	  $capsext->write($row, 0, $c);
	  $capsext->write($row, 1, "-");
	  $capsext->write($row, 2, "-");
	  $capsext->write($row, 3, "-");
	  $capsext->write($row, 4, "-");
	  $capsext->write($row, 5, $allocation{$c}{"nallotted"} || 0);
	  $capsext->write($row, 6, $courses{$c}{"nocap"}
			  ?"NA"
			  :($courses{$c}{"cap"} - ($allocation{$c}{"nallotted"}||0)));
	}
	++$row;
      }
    }

    {
      my $col = 0;
      my $row = 0;
      my $statsint = $workbookint->add_worksheet("Stats");
      $statsint->set_paper(9);
      $statsint->set_landscape();
      $statsint->fit_to_pages(1);
      $statsint->set_header("&C$title: &A");
      $statsint->set_footer("&C$footer&R&P of &N");

      $statsint->write($row, $col++, "Seniority", $formatint);
      $statsint->write($row, $col++, "Students", $formatint);
      $statsint->write($row, $col++, "Demand", $formatint);
      $statsint->write($row, $col++, "Allocation", $formatint);
      ++$row;

      my %stats;
      foreach my $rollno (@ranklist) {

	next unless $choices{$rollno};
	my $demand = ($students{$rollno}{'nallowed'}
		      < $choices{$rollno}{'ncourses'}
		      ? $students{$rollno}{'nallowed'}
		      : $choices{$rollno}{'ncourses'});
	my $alloc = $choices{$rollno}{'nallotted'};
	my $s = $students{$rollno}{'seniority'}; 
	++$stats{$s}{'students'};
	$stats{$s}{'demand'} += $demand;
	$stats{$s}{'alloc'} += $alloc;
	++$stats{'total'}{'students'};
	$stats{'total'}{'demand'} += $demand;
	$stats{'total'}{'alloc'} += $alloc;
      }
      
      for my $s (sort keys (%stats)) {

	my $label = $s;
	if ($s ne "total") {

	  if ($s == $current_year) {

	    $label = "MISSED";
	  }
	  elsif ($s == $current_year + 1) {

	    $label = "LATE";
	  }
	}
	$col = 0;
	$statsint->write($row, $col++, $label);
	$statsint->write($row, $col++, $stats{$s}{'students'});
	$statsint->write($row, $col++, $stats{$s}{'demand'});
	$statsint->write($row, $col++, $stats{$s}{'alloc'});
	++$row;
      }
    }

    my $coursecount = 0;
    my %studentrow;


    my $conflictint = $workbookint->add_worksheet("Conflicts");
    $conflictint->set_paper(9);
    $conflictint->set_landscape();
    $conflictint->fit_to_pages(1);
    $conflictint->set_header("&C$title: &A");
    $conflictint->set_footer("&C$footer&R&P of &N");

    write_conflicts(\&all_students, $conflictint, "All students", 0, $formatint);
    write_conflicts(\&chennai_students, $conflictint, "Chennai students", 1, $formatint);
    write_conflicts(\&only_2005_students, $conflictint, "Only 2005 batch students", 2, $formatint);
    write_conflicts(\&only_senior_students, $conflictint, "Only senior batch students", 3, $formatint);

    foreach my $course (sort keys %courses) {

        next if ($courses{$course}{"status"} eq 'D');

        print "Writing spreadsheet information for $course\n";
        my $sheetint = $workbookint->add_worksheet($course);
        $sheetint->set_paper(9);
        $sheetint->set_portrait();
        $sheetint->fit_to_pages(1);
        $sheetint->set_header("&C$title: &A");
        $sheetint->set_footer("&C$footer&R&P of &N");

        my $sheetext = $workbookext->add_worksheet($course);
        $sheetext->set_paper(9);
        $sheetext->set_portrait();
        $sheetext->fit_to_pages(1);
        $sheetext->set_header("&C$title: &A");
        $sheetext->set_footer("&C$footer&R&P of &N");

        $summaryint->write(0, $coursecount + 3, $course, $formatint);
        $summaryext->write(0, $coursecount + 3, $course, $formatext);

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
        my $allocno = 1;

        foreach my $rec (@{$allocation{$course}{"studentlist"}}) {

            $sheetint->write($row, $col++, $count, get_format($rec, \@intformats));
            $sheetint->write($row, $col++, ($rec->{'allotted'} ? $allocno++ : ""), get_format($rec, \@intformats));

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

            $studentrow{$rec->{"rollno"}}{$course} =
              ($rec->{"allotted"} == 1 ? 1 : undef);
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
                $sheetext->write($row, $col++, $row);
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

        # print "Writing summary for $studentno\n";
        $summaryint->write($row, 0, $studentno);
        $summaryint->write($row, 1, $students{$studentno}->{"name"});
        $summaryint->write($row, 2, $choices{$studentno}->{"nallotted"});

        $summaryext->write($row, 0, $studentno);
        $summaryext->write($row, 1, $students{$studentno}->{"name"});
        $summaryext->write($row, 2, $choices{$studentno}->{"nallotted"});
       
        my $courseno = 0;
        foreach my $course (sort keys %courses) {
            
            next if ($courses{$course}{'status'} eq 'D');

            if (defined($studentrow{$studentno}{$course})) {

                $summaryint->write($row, $courseno + 3, $course);
                $summaryext->write($row, $courseno + 3, $course);
            }

            ++$courseno;
        }
        ++$row;
    }
}

sub write_choices_excel ($$$$) 
{
    my $workbook = shift;
    my $worksheet_name = shift;
    my $show_results = shift;
    my $formats = shift;

    my $sheet = $workbook->add_worksheet($worksheet_name);
    $sheet->set_paper(9);
    $sheet->set_landscape(1);
    $sheet->fit_to_pages(1);
    $sheet->set_header("&C$title: &A");
    $sheet->set_footer("&C$footer&R&P of &N");

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
    $sheet->write($row, $col++, "Seniority", $formatbold);
    $sheet->write($row, $col++, "CGPA", $formatbold);
    $sheet->write($row, $col++, "Project", $formatbold);
    $sheet->write($row, $col++, "Asked", $formatbold);
    $sheet->write($row, $col++, "Allowed", $formatbold) if $show_results;
    $sheet->write($row, $col++, "Allotted", $formatbold) if $show_results;

    for (my $priority = 1; $priority <= (keys %courses); ++$priority) {
      $sheet->write($row, $col++, "P$priority", $formatbold);
      $sheet->write($row, $col++, "P$priority Status", $formatbold) if $show_results;
    }

    ++$row;
    $col = 0;

    foreach my $rollno (@ranklist) {

      next unless $choices{$rollno};

      $sheet->write($row, $col++, $row);
      $sheet->write($row, $col++, $rollno);
      $sheet->write($row, $col++, $students{$rollno}{'name'});
      $sheet->write($row, $col++, $students{$rollno}{'credits'});
      $sheet->write($row, $col++, $students{$rollno}{'senreason'});
      $sheet->write($row, $col++, $students{$rollno}{'cgpa'});
      $sheet->write($row, $col++, defined($project_students{$rollno})?"Y":"N");
      $sheet->write($row, $col++, $choices{$rollno}{'ncourses'});
      $sheet->write($row, $col++, $students{$rollno}{'nallowed'}) if $show_results;
      $sheet->write($row, $col++, $choices{$rollno}{'nallotted'}) if $show_results;

      for (my $priority = 1; $priority <= (keys %courses); ++$priority) {
        my $course = $choices{$rollno}{'courselist'}->[$priority-1];
        if ($course) {
          my $rec = $allocation{$course}{"rollno"}{$rollno};
          $sheet->write($row, $col++, $course, $show_results ? get_format($rec, $formats) : undef);
          $sheet->write($row, $col++, $rec->{'reason'}, get_format($rec, $formats)) if $show_results;
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

sub write_allocation_by_student ($)
{
    my $filename = shift;

    open OUT, ">$filename" or die "Can't open $filename: $!";

    foreach my $rollno (sort keys %choices) {
        print OUT "$rollno; ";
        print OUT "$students{$rollno}{'name'}; ";
        print OUT "$students{$rollno}{'email'}; ";
        print OUT "$choices{$rollno}{'ncourses'}; ";
        print OUT "$students{$rollno}{'nallowed'}; ";
        print OUT "$choices{$rollno}{'nallotted'}; ";
        print OUT "$students{$rollno}{'seniority'}; ";
        print OUT ($students{$rollno}{'senreason'} || "") . "; ";

        foreach my $course (@{$choices{$rollno}{"courselist"}}) {
            print OUT "$course=", 
                $allocation{$course}{"rollno"}{$rollno}->{"reason"} || "", ",";
        }
        print OUT "\n";
    }
    close OUT;
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


sub compute_conflicts
{
  my $conflicts = shift;
  my $studentselect = shift;
    foreach my $i (keys %courses) {
        foreach my $j (keys %courses) {
            # next if $i eq $j;

            my %iset = get_students_for_course($i, 3); 
            my %jset = get_students_for_course($j, 3); 
            my %isect = ();

            foreach my $roll (keys %iset) {

	      if (&$studentselect($roll)) {

                $isect{$roll} = 1 if (defined($jset{$roll}));
	      }
            }

            push @$conflicts, 
                {"a" => $i, "b" => $j, "n" => scalar(keys %isect)};
        }
    }

    @$conflicts = sort { $a->{"n"} <=> $b->{"n"} } @$conflicts;

  #print "=== Course conflicts ===\n";
  #foreach my $rec (@$conflicts) {
  #print "$rec->{'a'} - $rec->{'b'}: $rec->{'n'}\n";
  #} 
}

sub load_allocations($)
{
    my $file = shift;
    open IN, "<$file" or die "Can't open file $file: $!";
    LINE: while (<IN>) {
        chomp;
        next if skip_line($_);

        my ($rollno, $name, $email, $asked, $allowed,
	    $alloted, $seniority, $senreason, $allocationlist) = 
	      split(/\s*\;\s*/, $_) unless skip_line($_); 

        $allocationlist = undef if (defined($allocationlist) && ($allocationlist eq ''));

        if (!defined($rollno) || ($rollno eq "")) {
            err_print("error:$file:$.: no roll number");
            next;
        }

        unless (defined($students{$rollno})) {
            err_print("error:$file:$.: roll number '$rollno' not defined");
            next;
        }

        if (defined($p3salloc{$rollno})) {
            err_print("error:$file:$.: roll number '$rollno' already defined");
            next;
        } 

        if (!defined($allocationlist)) {
            err_print("error:$file:$.: allocation list not defined");
            next;
        }

	my %student_courses;
	
	for my $alloc (split(/\s*,\s*/, $allocationlist)) {

          my ($course, $status) = (split(/\s*=\s*/, $alloc));
          if ($status eq "Allotted") {

            $student_courses{$course} = 1;
	    $p3calloc{$course}{"students"}{$rollno} = 1;
	    $p3calloc{$course}{"nstudents"}++;
          }
	}

        $p3salloc{$rollno}{"courses"} = \%student_courses;
    }
    close IN;
}

sub print_allocations ()
{
    print "=== Allocations ===\n";
    foreach my $rollno (sort keys %p3salloc) {
        print join('; ',
            $rollno,
            join(',', keys %{$p3salloc{$rollno}{"courses"}})), "\n";
    }
    print "\n";
    foreach my $course (sort keys %p3calloc) {
        print join('; ',
		   $course,
		   $p3calloc{$course}{nstudents}), "\n";
	foreach my $rollno (sort keys %{$p3calloc{$course}{"students"}}) {

            print join('; ',
                       $rollno,
                       $students{$rollno}{"name"}), "\n";
        }
        print "\n";
    }
    print "\n";
}

sub load_p3choices($)
{
    my $file = shift;
    open IN, "<$file" or die "Can't open file $file: $!";
    LINE: while (<IN>) {
        chomp;
        next if skip_line($_);
        my ($rollno, $trtype, $courselist) = 
            split(/\s*\;\s*/, $_) unless skip_line($_); 

        $courselist = undef if (defined($courselist) && ($courselist eq ''));
        $trtype = undef if (defined($trtype) && ($trtype eq ''));

        if (!defined($rollno) || ($rollno eq "")) {
            err_print("error:$file:$.: no roll number");
            next;
        }

        unless (defined($students{$rollno})) {
            err_print("error:$file:$.: roll number '$rollno' not defined");
            next;
        }

        if (defined($p3choices{$rollno})) {
            err_print("error:$file:$.: roll number '$rollno' already defined");
            next;
        } 

	if (!defined($trtype) || ($trtype !~ /^[DAS]$/)) {
            err_print("error:$file:$.: transaction type '$trtype' invalid");
            next;
	}

        if (!defined($courselist)) {
            err_print("error:$file:$.: course list not defined");
            next;
        }

	my ($drop, $add) = (undef, undef);
	if ($trtype eq "S") {

	  ($drop, $add) = split(/\s*,\s*/, $courselist);
	  if (!defined($drop) || !defined($add)) {

	    err_print("error:$file:$.: both drop and add should be given");
            next;
	  }
	}
	elsif ($trtype eq "D") {

	  $drop = $courselist;
	}
	else {

	  $add = $courselist;
	}

	$add .= "-" . $students{$rollno}{"site"} if (defined($add));
	$drop .= "-" . $students{$rollno}{"site"} if (defined($drop));

	if (defined($add) && !(defined($courses{$add}))) {

	  err_print("error:$file:$.: invalid course '$add'");
	  next;
	}

	if (defined($drop) && !(defined($courses{$drop}))) {

	  err_print("error:$file:$.: invalid course '$drop'");
	  next;
	}

	if (defined($drop) && !(defined($p3salloc{$rollno}{"courses"}{$drop}))) {

	  err_print("error:$file:$.: cannot drop '$drop' for '$rollno', not allotted");
	  next;
	}

	if ($trtype =~ /^[AS]$/) {

	  my @curcourses = (keys %{$p3salloc{$rollno}{"courses"}});
	  for my $c (@curcourses) {

	    next if ($trtype eq "S" && $c eq $drop);
	    if (courses_conflict($c, $add)) {

	      err_print("error:$file:$.: cannot add '$add' for '$rollno', conflicts with '$c'");
	      next LINE;
	    }
	  }
	}
	

	$p3choices{$rollno}{"trtype"} = $trtype;
	$p3choices{$rollno}{"add"} = $add if (defined($add));
	$p3choices{$rollno}{"drop"} = $drop if (defined($drop));
	$p3choices{$rollno}{"status"} = 'P';
	for my $course (sort keys %{$p3salloc{$rollno}{"courses"}}) {

	  $p3choices{$rollno}{"courses"}{$course} = 1;
	}
    }
    close IN;
}

sub print_p3choices ()
{
    print "=== P3 choices ===\n";
    foreach my $rollno (sort keys %p3choices) {
        print join('; ',
		   $rollno,
		   $p3choices{$rollno}{"trtype"},
		   $p3choices{$rollno}{"drop"} || "-",
		   $p3choices{$rollno}{"add"} || "-",
		   $p3choices{$rollno}{"status"}), "\n";
    }
    print "\n";
}

sub print_given_p3choices
{
    my $choices = shift;
    print "=== Remaining P3 choices ===\n";
    foreach my $rollno (@{$choices}) {

      print_p3request($rollno);
    }
    print "\n";
}

sub execute_p3request {

  my $rollno = shift;
  if ($p3choices{$rollno}{"trtype"} eq "D") {
 
    my $c = $p3choices{$rollno}{"drop"};
    if ($p3calloc{$c}{"nstudents"} > $courses{$c}{"mincap"}) {

      # Possible to drop
      $p3calloc{$c}{"nstudents"}--;
      delete($p3calloc{$c}{"students"}{$rollno});
      delete($p3salloc{$rollno}{"courses"}{$c});
      $p3choices{$rollno}{"status"} = "D";
      return 1;
    }
    else {

      $p3choices{$rollno}{"reason"} = "Quorum";
      return 0;
    }
  }
  if ($p3choices{$rollno}{"trtype"} eq "A") {
 
    # Check for max allowed
    my $allowed = $students{$rollno}{"nallowed"};
    my $allotted = (keys %{$p3salloc{$rollno}{"courses"}});
    if ($allotted >= $allowed) {
      
      $p3choices{$rollno}{"status"} = "N";
      $p3choices{$rollno}{"reason"} = "Allowed: " . $allowed;
      return 0;
    }

    my $c = $p3choices{$rollno}{"add"};
    if ($p3calloc{$c}{"nstudents"} < $courses{$c}{"cap"}) {

      # Possible to add
      $p3calloc{$c}{"nstudents"}++;
      $p3calloc{$c}{"students"}{$rollno} = 1;
      $p3salloc{$rollno}{"courses"}{$c} = 1;
      $p3choices{$rollno}{"status"} = "D";
      return 1;
    }
    else {

      $p3choices{$rollno}{"reason"} = "Capped";
      return 0;
    }
  }
  if ($p3choices{$rollno}{"trtype"} eq "S") {
 
    my $a = $p3choices{$rollno}{"add"};
    my $d = $p3choices{$rollno}{"drop"};
    if ($p3calloc{$a}{"nstudents"} < $courses{$a}{"cap"}
	&& $p3calloc{$d}{"nstudents"} > $courses{$d}{"mincap"}) {

      # Possible to add and drop
      # Add
      $p3calloc{$a}{"nstudents"}++;
      $p3calloc{$a}{"students"}{$rollno} = 1;
      $p3salloc{$rollno}{"courses"}{$a} = 1;
      # Drop
      $p3calloc{$d}{"nstudents"}--;
      delete($p3calloc{$d}{"students"}{$rollno});
      delete($p3salloc{$rollno}{"courses"}{$d});
      $p3choices{$rollno}{"status"} = "D";
      return 1;
    }
    else {

      if ($p3calloc{$a}{"nstudents"} >= $courses{$a}{"cap"}) {

	$p3choices{$rollno}{"reason"} = "Capped";
      }
      elsif ($p3calloc{$d}{"nstudents"} <= $courses{$d}{"mincap"}) {

	$p3choices{$rollno}{"reason"} = "Quorum";
      }
    }
  }
  return 0;
}

sub print_p3request
{
  my $rollno = shift;
  print join('; ',
	     $rollno,
	     $p3choices{$rollno}{"trtype"},
	     $p3choices{$rollno}{"drop"} || "-",
	     $p3choices{$rollno}{"add"} || "-",
	     $p3choices{$rollno}{"status"}), "\n";
}

sub add_drop_p3choices ()
{
 ROUND1:
  while (1) {

    my @p3pending = sort { $students{$b}{"cgpa"} <=> $students{$a}{"cgpa"} } grep { $p3choices{$_}{"status"} eq "P" } keys %p3choices;
    last if (scalar(@p3pending) == 0);
    for my $rollno (@p3pending) {

      if (execute_p3request($rollno)) {

	print "Successful: ";
	print_p3request($rollno);
	# Restart the work
	next ROUND1;
      }
    }
    # If we reach here, there was no work to do
    last ROUND1;
  }
  # Done with round 1 where all non-cyclical requests are executed
  # No more "A" and "D" are possible. Only "S" may be possible due
  # to their cyclical nature. Thus mark all "A" and "D" with
  # status "N".
  my @p3pending = sort { $students{$b}{"cgpa"} <=> $students{$a}{"cgpa"} } grep { $p3choices{$_}{"status"} eq "P" } keys %p3choices;
  for my $rollno (@p3pending) {

    if ($p3choices{$rollno}{trtype} =~ /^[AD]$/) {
      
      print "Unuccessful: ";
      print_p3request($rollno);
      $p3choices{$rollno}{status} = "N";
    }
  }
  @p3pending = sort { $students{$b}{"cgpa"} <=> $students{$a}{"cgpa"} } grep { $p3choices{$_}{"status"} eq "P" } keys %p3choices;
  print_given_p3choices(\@p3pending);
  # Now find out the surely non-cyclic ones and throw them out
 ROUND2:
  my $not_done = 1;
  while ($not_done) {

    $not_done = 0;
    # First do a count
    my %swaps;
    my @p3pending = sort { $students{$b}{"cgpa"} <=> $students{$a}{"cgpa"} }
      grep { $p3choices{$_}{"status"} eq "P" && $p3choices{$_}{"trtype"} eq "S"} keys %p3choices;
    for my $rollno (@p3pending) {

      $swaps{$p3choices{$rollno}{"add"}}{"add"}++;
      $swaps{$p3choices{$rollno}{"drop"}}{"drop"}++;
    }
    for my $rollno (@p3pending) {

      if ((!defined($swaps{$p3choices{$rollno}{"drop"}}{"add"})
	   || $swaps{$p3choices{$rollno}{"drop"}}{"add"} == 0) ||
	  (!defined($swaps{$p3choices{$rollno}{"add"}}{"drop"}) ||
	   $swaps{$p3choices{$rollno}{"add"}}{"drop"} == 0)) {

	# Ends or starts in a one way node. Not possible to execute
	print "Unuccessful: ";
	print_p3request($rollno);
	$p3choices{$rollno}{status} = "N";
	$not_done = 1;
      }
    }    
  }
  @p3pending = sort { $students{$b}{"cgpa"} <=> $students{$a}{"cgpa"} } grep { $p3choices{$_}{"status"} eq "P" } keys %p3choices;
  print_given_p3choices(\@p3pending);
}

sub print_remaining_p3choices ()
{
  print_p3choices;
}

sub get_p3format
{
  my $rollno = shift;
  my $formats = shift;
  if ($p3choices{$rollno}{"status"} eq "D") {

    return $formats->[0];
  }
  elsif ($p3choices{$rollno}{"status"} eq "N") {

    return $formats->[1];
  }
  else {

    return $formats->[2];
  }
}

sub write_p3excel ()
{
    # Generate two workbooks, internal and external.
    my $workbookint = Spreadsheet::WriteExcel->new("final-allocation-internal.xls");
    my $workbookext = Spreadsheet::WriteExcel->new("final-allocation.xls");

    # color pallettes for both
    $workbookint->set_custom_color(40, $successful_color);
    $workbookint->set_custom_color(41, $unsuccessful_color);
    $workbookint->set_custom_color(42, $pending_color);

    $workbookext->set_custom_color(40, $successful_color);
    $workbookext->set_custom_color(41, $unsuccessful_color);
    $workbookext->set_custom_color(42, $pending_color);

    my $successful_cfint = $workbookint->add_format(bg_color=>40);
    my $unsuccessful_cfint = $workbookint->add_format(bg_color=>41);
    my $pending_cfint = $workbookint->add_format(bg_color=>42);
    my @intformats = ($successful_cfint, $unsuccessful_cfint, $pending_cfint);

    my $successful_cfext = $workbookext->add_format(bg_color=>40);
    my $unsuccessful_cfext = $workbookext->add_format(bg_color=>41);
    my $pending_cfext = $workbookext->add_format(bg_color=>42);
    my @extformats = ($successful_cfext, $unsuccessful_cfext, $pending_cfext);

    # Headers for both
    my @header = ('SNo', 'Roll Number', 'Name', 'E-mail');

    my $formatint = $workbookint->add_format();
    $formatint->set_bold();
    my $formatext = $workbookext->add_format();
    $formatext->set_bold();

    my $summaryint = $workbookint->add_worksheet("Summary");
    $summaryint->set_paper(9);
    $summaryint->set_landscape();
    $summaryint->fit_to_pages(1);
    $summaryint->set_header("&C$title: &A");
    $summaryint->set_footer("&C$footer&R&P of &N");

    my $summaryext = $workbookext->add_worksheet("Summary");
    $summaryext->set_paper(9);
    $summaryext->set_landscape();
    $summaryext->fit_to_pages(1);
    $summaryext->set_header("&C$title: &A");
    $summaryext->set_footer("&C$footer&A&R&P of &N");

    $summaryint->write(0, 0, "Roll Number", $formatint);
    $summaryint->set_column(0, 0, $rollno_width);
    $summaryint->write(0, 1, "Name", $formatint);
    $summaryint->set_column(1, 1, $name_width);
    $summaryint->write(0, 2, "#Courses", $formatint);

    $summaryext->write(0, 0, "Roll Number", $formatext);
    $summaryext->set_column(0, 0, $rollno_width);
    $summaryext->write(0, 1, "Name", $formatext);
    $summaryext->set_column(1, 1, $name_width);
    $summaryext->write(0, 2, "#Courses", $formatext);

    my $capsint = $workbookint->add_worksheet("Courses");
    $capsint->set_paper(9);
    $capsint->set_landscape();
    $capsint->fit_to_pages(1);
    $capsint->set_header("&C$title: &A");
    $capsint->set_footer("&C$footer&R&P of &N");

    my $capsext = $workbookext->add_worksheet("Courses");
    $capsext->set_paper(9);
    $capsext->set_landscape();
    $capsext->fit_to_pages(1);
    $capsext->set_header("&C$title: &A");
    $capsext->set_footer("&C$footer&A&R&P of &N");

    my $col = 0;
    $capsint->write(0, $col++, "Course id", $formatint);
    $capsint->write(0, $col++, "Maxcap", $formatint);
    $capsint->write(0, $col++, "Mincap", $formatint);
    $capsint->write(0, $col++, "# enrolled", $formatint);
    $capsint->write(0, $col++, "# available", $formatint);

    $col = 0;
    $capsext->write(0, $col++, "Course id", $formatint);
    $capsext->write(0, $col++, "Maxcap", $formatint);
    $capsext->write(0, $col++, "Mincap", $formatint);
    $capsext->write(0, $col++, "# enrolled", $formatint);
    $capsext->write(0, $col++, "# available", $formatint);

    my $row = 1;
    for my $c (sort keys %courses) {

      next if ($courses{$c}{"status"} ne 'A');

      $col = 0;
      $capsint->write($row, $col++, $c, $formatint);
      $capsint->write($row, $col++, ($courses{$c}{"nocap"}
				    ?"NA"
				    :$courses{$c}{"cap"}));
      $capsint->write($row, $col++, $courses{$c}->{"mincap"});
      $capsint->write($row, $col++, $p3calloc{$c}{"nstudents"});
      $capsint->write($row, $col++, ($courses{$c}{"nocap"}
				    ?"NA"
				    :($courses{$c}{"cap"}
				      - $p3calloc{$c}{"nstudents"})));

      $col = 0;
      $capsext->write($row, $col++, $c, $formatint);
      $capsext->write($row, $col++, ($courses{$c}{"nocap"}
				    ?"NA"
				    :$courses{$c}{"cap"}));
      $capsext->write($row, $col++, $courses{$c}->{"mincap"});
      $capsext->write($row, $col++, $p3calloc{$c}{"nstudents"});
      $capsext->write($row, $col++, ($courses{$c}{"nocap"}
				    ?"NA"
				    :($courses{$c}{"cap"}
				      - $p3calloc{$c}{"nstudents"})));
      
      ++$row;
    }

    my $p3int = $workbookint->add_worksheet("Phase 3");
    $p3int->set_paper(9);
    $p3int->set_landscape();
    $p3int->fit_to_pages(1);
    $p3int->set_header("&C$title: &A");
    $p3int->set_footer("&C$footer&R&P of &N");

    $col = 0;
    $p3int->write(0, $col++, "S. No.", $formatint);
    $p3int->set_column($col, $col, $rollno_width);
    $p3int->write(0, $col++, "Roll No.", $formatint);
    $p3int->set_column($col, $col, $name_width);
    $p3int->write(0, $col++, "Name", $formatint);
    $p3int->write(0, $col++, "CGPA", $formatint);
    $p3int->write(0, $col++, "Request", $formatint);
    $p3int->write(0, $col++, "Drop", $formatint);
    $p3int->write(0, $col++, "Add", $formatint);
    $p3int->set_column($col, $col, $status_width);
    $p3int->write(0, $col++, "Status", $formatint);
    $p3int->write(0, $col++, "Reason", $formatint);

    $row = 1;
    for my $rollno (sort { $students{$b}{"cgpa"} <=> $students{$a}{"cgpa"} } keys %p3choices) {

      $col = 0;
      $p3int->write($row, $col++, $row, get_p3format($rollno, \@intformats));
      $p3int->write($row, $col++, $rollno." ", get_p3format($rollno, \@intformats));
      $p3int->write($row, $col++, $students{$rollno}{"name"}, get_p3format($rollno, \@intformats));
      $p3int->write($row, $col++, $students{$rollno}{"cgpa"}, get_p3format($rollno, \@intformats));
      $p3int->write($row, $col++, $trtype_label{$p3choices{$rollno}{"trtype"}}, get_p3format($rollno, \@intformats));
      $p3int->write($row, $col++, $p3choices{$rollno}{"drop"} || "-", get_p3format($rollno, \@intformats));
      $p3int->write($row, $col++, $p3choices{$rollno}{"add"} || "-", get_p3format($rollno, \@intformats));
      $p3int->write($row, $col++, $status_label{$p3choices{$rollno}{"status"}}, get_p3format($rollno, \@intformats));
      $p3int->write($row, $col++, ($p3choices{$rollno}{"status"} eq "N") ? $p3choices{$rollno}{"reason"} : "", get_p3format($rollno, \@intformats));
      ++$row;
    }

    my $coursecount = 0;
    my %studentrow;

    foreach my $course (sort keys %courses) {

        next if ($courses{$course}{"status"} eq 'D');

        print "Writing spreadsheet information for $course\n";
        my $sheetint = $workbookint->add_worksheet($course);
        $sheetint->set_paper(9);
        $sheetint->set_portrait();
        $sheetint->fit_to_pages(1);
        $sheetint->set_header("&C$title: &A");
        $sheetint->set_footer("&C$footer&R&P of &N");

        my $sheetext = $workbookext->add_worksheet($course);
        $sheetext->set_paper(9);
        $sheetext->set_portrait();
        $sheetext->fit_to_pages(1);
        $sheetext->set_header("&C$title: &A");
        $sheetext->set_footer("&C$footer&R&P of &N");

        $summaryint->write(0, $coursecount + 3, $course, $formatint);
        $summaryext->write(0, $coursecount + 3, $course, $formatext);

        $row = 0;
        $col = 0;

        for ($col = 0; $col < @header; ++$col) {
            $sheetint->write($row, $col, $header[$col], $formatint);
            $sheetext->write($row, $col, $header[$col], $formatext);
        }

        $row = 1;
        $col = 0;
	for my $rollno (sort keys %{$p3calloc{$course}{"students"}}) {

	  $sheetext->set_column($col, $col, $rollno_width);
	  $sheetext->write($row, $col++, $row);
	  $sheetext->set_column($col, $col, $rollno_width);
	  $sheetext->write($row, $col++, $rollno." ");
	  $sheetext->set_column($col, $col, $name_width);
	  $sheetext->write($row, $col++, $students{$rollno}{"name"});
	  $sheetext->set_column($col, $col, $email_width);
	  $sheetext->write($row, $col++, $students{$rollno}{"email"});
	  $col = 0;

	  $sheetint->set_column($col, $col, $rollno_width);
	  $sheetint->write($row, $col++, $row);
	  $sheetint->set_column($col, $col, $rollno_width);
	  $sheetint->write($row, $col++, $rollno." ");
	  $sheetint->set_column($col, $col, $name_width);
	  $sheetint->write($row, $col++, $students{$rollno}{"name"});
	  $sheetint->set_column($col, $col, $email_width);
	  $sheetint->write($row, $col++, $students{$rollno}{"email"});
	  $col = 0;

	  ++$row;
	}


        ++$coursecount;
    }

    $row = 1;
    foreach my $rollno (sort keys %p3salloc) {

        # print "Writing summary for $rollno\n";
        $summaryint->write($row, 0, $rollno." ");
        $summaryint->write($row, 1, $students{$rollno}->{"name"});
        $summaryint->write($row, 2, scalar(keys %{$p3salloc{$rollno}{"courses"}}));

        $summaryext->write($row, 0, $rollno." ");
        $summaryext->write($row, 1, $students{$rollno}->{"name"});
        $summaryext->write($row, 2, scalar(keys %{$p3salloc{$rollno}{"courses"}}));
       
        my $courseno = 0;
        foreach my $course (sort keys %courses) {
            
            next if ($courses{$course}{'status'} eq 'D');

            if (defined($p3salloc{$rollno}{"courses"}{$course})) {

                $summaryint->write($row, $courseno + 3, $course);
                $summaryext->write($row, $courseno + 3, $course);
            }

            ++$courseno;
        }
        ++$row;
    }
}

sub write_p3mailbodies
{
  for my $rollno (sort keys %p3choices) {

    my $filename = "$p3mailbodies_path$rollno.txt";
    open OUT, ">$filename" or die "Can't open $filename: $!";
    print OUT "Please find the results of the phase 3 of the course allocation below:\n\n";
    print OUT "Roll number: $rollno\n";
    print OUT "Name: ". $students{$rollno}{"name"} . "\n";
    print OUT "E-Mail: " . $students{$rollno}{"email"} . "\n\n";
    my $ncourses = scalar(keys %{$p3choices{$rollno}{"courses"}});
    if ($ncourses > 0) {

      if ($ncourses == 1) {

	print OUT "Your only course before phase 3 was as follows:\n";
      }
      else {

	print OUT "Your $ncourses courses before phase 3 were as follows:\n";
      }
      for my $course (sort keys %{$p3choices{$rollno}{"courses"}}) {

	print OUT "$course - " . $courses{$course}{"name"} . "\n";
      }
    }
    else {

      print OUT "Your had no courses before phase 3.\n";
    }
    print OUT "\nYour request was to ";
    if ($p3choices{$rollno}{"trtype"} eq "A") {

      print OUT "add course " . $p3choices{$rollno}{"add"} . ".\n\n";
    }
    elsif ($p3choices{$rollno}{"trtype"} eq "D") {

      print OUT "drop course " . $p3choices{$rollno}{"drop"} . ".\n\n";
    }
    else {

      print OUT "swap course " . $p3choices{$rollno}{"drop"} . " with " . $p3choices{$rollno}{"add"} . ".\n\n";
    }
    if ($p3choices{$rollno}{"status"} eq "D") {

      print OUT "This request was successful.\n\n";
    }
    elsif ($p3choices{$rollno}{"status"} eq "N") {

      print OUT "This request was not successful as ";
      if ($p3choices{$rollno}{"reason"} eq "Capped") {

	print OUT "the course you wished to add (" . $p3choices{$rollno}{"add"} . ") is capped.\n\n";
      }
      elsif ($p3choices{$rollno}{"reason"} eq "Quorum") {

	print OUT "the course you wished to drop (" . $p3choices{$rollno}{"drop"} . ") will fall short of minimum requirements.\n\n";
      }
      elsif ($p3choices{$rollno}{"reason"} =~ "Allowed:") {

	print OUT "you have already taken maximum number of courses and are not allowed to take one more.\n\n";
      }
      else {

	print OUT "it happens.\n\n";
      }
    }
    else {

      print OUT "This request is still pending, please contact PGSEM office.\n\n";
    }
    $ncourses = scalar(keys %{$p3salloc{$rollno}{"courses"}});
    if ($ncourses > 0) {

      if ($ncourses == 1) {

	print OUT "Your only course after phase 3 is as follows:\n";
      }
      else {

	print OUT "Your $ncourses courses after phase 3 are as follows:\n";
      }
      for my $course (sort keys %{$p3salloc{$rollno}{"courses"}}) {

	print OUT "$course - " . $courses{$course}{"name"} . "\n";
      }
    }
    else {

      print OUT "Your have no courses after phase 3.\n";
    }
    print OUT "\nFor any clarifications regarding the allocation, please get in touch with the PGSEM office.\n";
    print OUT "-- \nAbhay Ghaisas and Sankaranaryananan K. V.\n";
    print OUT "pgsemelectives\@sankara.net\n";
    close OUT;
  }
}

sub write_p3allocations($)
{
  my $filename = shift;

  open OUT, ">$filename" or die "Can't open $filename: $!";

  for my $rollno (sort keys %p3choices) {

    print OUT "$rollno;";
    for my $course (sort keys %{$p3choices{$rollno}{"courses"}}) {

      print OUT "$course,";
    }
    print OUT ";";

    print OUT "$p3choices{$rollno}{'trtype'};";
    if ($p3choices{$rollno}{"trtype"} eq "A") {

      print OUT ";$p3choices{$rollno}{'add'};";
    }
    elsif ($p3choices{$rollno}{"trtype"} eq "D") {

      print OUT "$p3choices{$rollno}{'drop'};;";
    }
    else {

      print OUT "$p3choices{$rollno}{'drop'};$p3choices{$rollno}{'add'};";
    }
    if ($p3choices{$rollno}{"status"} eq "N") {

      print OUT "N;$p3choices{$rollno}{'reason'};";
    }
    else {

      print OUT "$p3choices{$rollno}{'status'};;";
    }
    for my $course (sort keys %{$p3salloc{$rollno}{"courses"}}) {

      print OUT "$course,";
    }
    print OUT "\n";
  }
}

sub load_late_changes($)
{
  my $file = shift;
  open IN, "<$file" or die "Can't open file $file: $!";
 LINE: while (<IN>) {
    chomp;
    next if skip_line($_);
    my ($rollno, $trtype, $courselist) = 
      split(/\s*\;\s*/, $_) unless skip_line($_); 

    $courselist = undef if (defined($courselist) && ($courselist eq ''));
    $trtype = undef if (defined($trtype) && ($trtype eq ''));
    
    if (!defined($rollno) || ($rollno eq "")) {
      err_print("error:$file:$.: no roll number");
      next;
    }

    unless (defined($students{$rollno})) {
      err_print("error:$file:$.: roll number '$rollno' not defined");
      next;
    }

    if (!defined($trtype) || ($trtype !~ /^[ADX]$/)) {
      err_print("error:$file:$.: transaction type '$trtype' invalid");
      next;
    }

    my @cour = ();
    if (defined($courselist)) {

      for my $c (split(/,/, $courselist)) {

	$c .= "-" . $students{$rollno}{"site"};
	if (!(defined($courses{$c}))) {

	  err_print("error:$file:$.: invalid course '$c'");
	  next LINE;
	}
	push (@cour, $c);
      }
    }
    my %rec = ();
    $rec{"rollno"} = $rollno;
    $rec{"trtype"} = $trtype;
    $rec{"courselist"} = \@cour;
    push(@late_changes, \%rec);
  }
}

sub print_late_changes ()
{
    print "=== Late changes ===\n";
    foreach my $rec (@late_changes) {
      my $cl = $rec->{"courselist"};
        print join('; ',
		   $rec->{"rollno"},
		   $rec->{"trtype"},
		   join(', ', @$cl)), "\n";
    }
    print "\n";
}

sub execute_late_request
{
  my $rollno = shift;
  my $trtype = shift;
  my $course = shift;
  if ($trtype eq "D") {

    if ($p3calloc{$course}{"nstudents"}
	> $courses{$course}{"mincap"}) {

      # Possible to drop
      $p3calloc{$course}{"nstudents"}--;
      delete($p3calloc{$course}{"students"}{$rollno});
      delete($p3salloc{$rollno}{"courses"}{$course});
      print("Late req succeeded:$rollno, $trtype, $course\n");
    }
    else {

      print("Late req failed:Mincap:$rollno, $trtype, $course\n");
    }
  }
  else {

    my $allowed = $students{$rollno}{"nallowed"};
    my $allotted = (keys %{$p3salloc{$rollno}{"courses"}});
    if ($allotted >= $allowed) {
      
      print("Late req failed:Allowed $allowed:$rollno, $trtype, $course\n");
      return;
    }
    if ($p3calloc{$course}{"nstudents"} < $courses{$course}{"cap"}) {

      # Possible to add
      $p3calloc{$course}{"nstudents"}++;
      $p3calloc{$course}{"students"}{$rollno} = 1;
      $p3salloc{$rollno}{"courses"}{$course} = 1;
      print("Late req succeeded:$rollno, $trtype, $course\n");
    }
    else {

      print("Late req failed:Maxcap:$rollno, $trtype, $course\n");
    }
  }
}

sub clear_late_changes ()
{
    print "=== Cleared late changes ===\n";
    @late_changes = ();
}

sub do_late_changes
{
  foreach my $rec (@late_changes) {

    my $rollno = $rec->{"rollno"};
    my $trtype = $rec->{"trtype"};
    my $clr = $rec->{"courselist"};
    my @cl = ();

    if ($trtype =~ "X") {

      my $ar = $p3salloc{$rollno}{"courses"};
      @cl = keys %$ar;
      $trtype = "D";
    }
    else {

      @cl = @$clr;
    }
    for my $c (@cl) {

      execute_late_request($rollno, $trtype, $c);
    }
  }
}

sub main
{
    read_config_info("config.txt");
    assign_config_info;

    load_courses("courses-internal.txt", 1);

    print_courses;

    if ($phase =~ /2/) {

      load_p1_students("choices-p1.txt");
    }
    if ($phase =~ /2B/) {

      load_p2a_students("p2a-students.txt");
      load_p2_students("p2-students.txt");
    }
    load_project_students("project-students.txt");
    load_students("students.txt");
    print_students;

    if ($phase =~ /1/ || $phase =~ /2/) {

      load_choices("choices.txt");
      print_choices;


      allocate_courses;
      print_allocation_by_course;
      print_allocation_by_student;


      @ranklist = sort { by_student_rank } (keys %students);
      print join("\n", @ranklist);
      print "\n";

      write_excel();

      write_allocation_by_student("allocation-internal.txt");
    }
    else {

      # phase 3 only

      # load allocations as at end of p2
      load_allocations("allocation-internal.txt");
      print_allocations;

      # Do late changes
      load_late_changes("post-p2-changes.txt");
      print_late_changes;
      do_late_changes;
      print_allocations;

      # load choices given in p3
      load_p3choices("p3choices.txt");
      print_p3choices;

      add_drop_p3choices;
      print_remaining_p3choices;

      clear_late_changes;
      load_late_changes("post-p3-changes.txt");
      print_late_changes;
      do_late_changes;

      write_p3excel;
      write_p3mailbodies;
      write_p3allocations("p3-allocation.txt");

      print_allocations;
    }
}

main;

# end of file
