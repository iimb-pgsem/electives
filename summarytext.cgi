#!/usr/bin/perl -w

# $Id: summarytext.cgi,v 1.4 2006/05/17 15:30:18 a14562 Exp $

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
    unless (param('passcode')) {

      print header(), start_html($title), h3($title);
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
    
    unless ($dbh) {
      print header(), start_html($title), h3($title);
      print br, "Error: unable to connect to database",
        br, local_end_html();
      return;
    }
  
    my $sth = $dbh->prepare("SELECT rollno, ncourses, course, priority FROM choices");
    my $status = $sth->execute();
    
    unless ($status) {
      print header(), start_html($title), h3($title);
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
      $choices{$rollno}{"priority"}{$priority} = $course;
      $choices{$rollno}{"courses"}{$course} = $priority;
    }
  
    $sth->finish();
    
    $dbh->disconnect();

    print "Content-type: text/plain\n\n";

    foreach $rollno (sort keys %choices) {

      my @courses;
      for (my $priority = 1; $priority <= (keys %courses); ++$priority) {
        my $course = $choices{$rollno}{'priority'}{$priority};
        push @courses, $course if ($course);
      }

      print "$rollno; ";
      print "$choices{$rollno}{'ncourses'}; ";
      print join(',', @courses);
      print "\n";
    }
}

main;

# end of file
