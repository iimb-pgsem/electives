#!/usr/bin/perl -w

# $Id: summary.cgi,v 1.4 2006/05/17 15:30:07 a14562 Exp $

# Copyright (c) 2006
# Sankaranarayanan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

use strict;

use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use FindBin;
use DBI;
use POSIX;

# === begin sensitive information ===
my $login = '';
my $password = '';
my $datasource = "DBI:mysql:sankara_q42005";
my $dblogin = 'sankara_sankar';
my $dbpassword = 'sankar123';
# === end sensitive information ===

# === begin configurable information ===
my $config_dir = "$FindBin::Bin"; # at least for the present
my $title = "PGSEM 2005-06 Quarter 4 (February - April 2006) Electives Submission";
# === end configurable information

# === below to be moved to a library module ===

my %students;
my %courses;
my $max_cgpa = 4.0;

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

sub load_students($)
  {
    my $errors = 0;
    my $file = shift;
    open IN, "<$file" or die "Can't open file $file: $!";
    while (<IN>) {
      chomp;
      next if skip_line($_);
      my ($rollno, $name, $email, $cgpa) = 
        split(/\s*\;\s*/, $_) unless skip_line($_); 

      $cgpa = undef if (defined($cgpa) && ($cgpa eq ''));

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

      $name ||= "";
      $email ||= "";

      $students{$rollno}{"name"} = $name;
      $students{$rollno}{"email"} = $email;
      $students{$rollno}{"cgpa"} = $cgpa;

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
                 $students{$rollno}{"cgpa"} || ""), "\n";
    }
    print "\n";
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

      $name ||= "";
      $instructor ||= "";

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

# === above to be moved to a library modele === 

sub local_end_html()
{
  return <<'EOF' . "<br>Page generated at " . localtime() . end_html();
<hr>&copy; 2006 Sankaranarayanan K. V. and Abhay Ghaisas. If you face any 
problems, please contact <a href="mailto:pgsemelectives@sankara.net">
pgsemelectives@sankara.net</a>.
EOF

}

sub main()
{
    print header(), start_html($title), h3($title);

    unless (param('passcode')) {

      print start_form, "Passcode: ",
        textfield(-name=>'passcode',  -size=>20, -maxlength=>20), br;
      print end_html();
      return;
    }

    my $passcode = param('passcode');
    unless ($passcode eq "REDACTED_CREDENTIAL") {
      print header(), start_html($title), h3($title);
      print "Invalid passcode";
      print end_html();
      return;
    }

    load_courses("$config_dir/courses.txt");
    load_students("$config_dir/students.txt");

    my $dbh = DBI->connect($datasource, $dblogin, $dbpassword,
        {AutoCommit => 1, RaiseError => 1} );
    
    my %counts;

    foreach my $course (sort keys %courses) {
      for (my $priority = 1; $priority <= (keys %courses); ++$priority) {

        my $status;
        my $sth;
        $sth = $dbh->prepare("SELECT COUNT(*) FROM choices WHERE course = '$course' AND priority = '$priority'");
        $status = $sth->execute();
        
        unless ($status) {
          print br, "Error: unable to read from database",
            br, local_end_html();
          $dbh->disconnect();
          return;
        }
        
        my $count;
        $sth->bind_columns(\$count);
        while ($sth->fetch()) {
          last;
        }
        
        $sth->finish();
        
        $counts{$course}{"priority"}->{$priority} = ($count || 0);
        $counts{$course}{"total"}+= ($count || 0);
      }
    }
    
    print "<table border='1'>\n";
    print "<tr><td>Code</td><td>Name</td><td>Total</td>\n";
    for (my $priority = 1; $priority <= (keys %courses); ++$priority) {
      print "<td>$priority</td>\n";
    }
    print "</tr>\n";

    foreach my $course (sort keys %counts) {
      print "<tr>";
      print "<td>", $course, "</td>\n";
      print "<td>", $courses{$course}{"name"}, "</td>\n";
      print "<td align='right'>", $counts{$course}{"total"}, "</td>\n";
      
      for (my $priority = 1; $priority <= (keys %courses); ++$priority) {
        print "<td align='right' width='20'>", 
          $counts{$course}{"priority"}->{$priority} || 0, "</td>\n";
      }
      print "</tr>\n";
    }

    print "</table>\n";

    unless ($dbh) {
      print br, "Error: unable to connect to database",
        br, local_end_html();
      return;
    }
  
    my $status;
    my $sth;
    $sth = $dbh->prepare("SELECT COUNT(DISTINCT rollno) FROM choices");
    $status = $sth->execute();
    
    unless ($status) {
      print br, "Error: unable to read from database",
        br, local_end_html();
      $dbh->disconnect();
      return;
    }
    
    my $count;
    $sth->bind_columns(\$count);
    while ($sth->fetch()) {
      last;
    }
    
    $sth->finish();

    print "<br>Number of students submitted: $count<br><br>\n";

    $sth = $dbh->prepare("SELECT rollno, ncourses, course, priority FROM choices");
    $status = $sth->execute();
    
    unless ($status) {
      print br, "Error: unable to read from database",
        br, local_end_html();
      $dbh->disconnect();
      return;
    }
    
    my ($rollno, $ncourses, $course, $priority);
    $sth->bind_columns(\$rollno, \$ncourses, \$course, \$priority);
    my %choices;

    while ($sth->fetch()) {
      $choices{$rollno}{"ncourses"} = $ncourses;
      $choices{$rollno}{"priority"}->{$priority} = $course;
      $choices{$rollno}{"courses"}->{$course} = $priority;
    }
  
    $sth->finish();
    
#    $sth = $dbh->prepare("SELECT DISTINCT(rollno) FROM choices");
#    $status = $sth->execute();
#    
#    unless ($status) {
#      print br, "Error: unable to read from database",
#        br, local_end_html();
#      $dbh->disconnect();
#      return;
#    }
#    
#    my $rollno;
#    my @rollnos;
#    $sth->bind_columns(\$rollno);
#    while ($sth->fetch()) {
#      push @rollnos, $rollno;
#    }
#  
#    $sth->finish();

    $dbh->disconnect();

    print "<table border='1'>\n";

    print "<tr><td>Roll Number</td><td>Name</td>\n";
    print "<td>#Courses</td>\n";
    
    foreach my $course (sort keys %courses) {
        print "<td width='30'>$course</td>\n";
    }

    print "</tr>\n";

    foreach $rollno (sort keys %choices) {

      print "<tr>\n";
      print "<td>$rollno</td>\n";
      print "<td>$students{$rollno}{'name'}</td>\n";
      print "<td>$choices{$rollno}{'ncourses'}</td>\n";

      foreach my $course (sort keys %courses) {
        print "<td align='right'>", 
        $choices{$rollno}{'courses'}->{$course} || "-",
        "</td>\n";
      }

      print "</tr>\n";
    }

    print "</table>\n";

    print local_end_html;
}

main;

# end of file
