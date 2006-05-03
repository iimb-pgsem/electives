#!perl -w

# $Id: sendphaseonemails.pl,v 1.1 2006/05/03 12:47:37 a14562 Exp $

use strict;

use Net::SMTP;
use Net::POP3;
use MIME::Lite;

my $pop_required = 1;
my $login = 'sankara';
my $password = 'brealy16myers';

my $debug = 1;

sub send_mail ($$$$$)
{
    my ($from, $to, $subject, $body, $filename) = @_;

    my $pop = Net::POP3->new('mail.sankara.net', Timeout=>60, Debug=>$debug);

    my $errors = 0;

    if (!$pop_required || $pop->login($login, $password)) {
       
        my $msg = MIME::Lite->new(
            From => $from,
            To => $to,
            Subject => $subject,
            Type => 'multipart/mixed');

        
        $msg->attach(
            Type => 'TEXT',
            Data => $body);

        MIME::Lite->send('smtp', "mail.sankara.net", 
                         Timeout=>60, Debug=>$debug) or
          die "Can't send mail to $to: $!";
        $msg->send() or die "Can't send mail to $to: $!";

    } else {

       print STDERR "Error sending mail: unable to authenticate using POP3";
       return;
    }
   
    # success

    if ($errors) {
        print STDERR "Error sending mail using SMTP";
        return;
    }
}

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
      my ($rollno, $name, $email, $cgpa, $credits, $site) = 
        split(/\s*\;\s*/, $_) unless skip_line($_); 

      $cgpa = undef if (defined($cgpa) && ($cgpa eq ''));
      $site = undef if (defined($site) && ($site eq ''));

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

      if (!defined($site) || ($site eq "")) {
        err_print("error:$file:$.: site undefined for $rollno");
        ++$errors;
        next;
      }

      $name ||= "";
      $email ||= "";

      $students{$rollno}{"name"} = $name;
      $students{$rollno}{"email"} = $email;
      $students{$rollno}{"cgpa"} = $cgpa;
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
                 $students{$rollno}{"credits"},
                 $students{$rollno}{"site"} || ""), "\n";
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
      my ($code, $name, $instructor, $cap, $slot, $dummy, $sites, $rbatch) = 
        split(/\s*\;\s*/, $_) unless skip_line($_); 

      $cap = undef if (defined($cap) && ($cap eq ''));
      $slot = undef if (defined($slot) && ($slot eq ''));
      $sites =~ s/\+/\,/g;

      if (!defined($code) || ($code eq "")) {
        err_print("error:$file:$.: no course code");
        next;
      }

      if (defined($courses{$code})) {
        err_print("error:$file:$.: course '$code' already defined");
        next;
      }

      if (defined($cap) && (($cap < 1))) {
        err_print("error:$file:$.: invalid cap '$cap'");
        next;
      }

      $name ||= "";
      $instructor ||= "";

      $courses{$code}{"name"} = $name;
      $courses{$code}{"instructor"} = $instructor;
      $courses{$code}{"cap"} = $cap;
      $courses{$code}{"slot"} = $slot;
      $courses{$code}{"sites"} = $sites;
      $courses{$code}{"rbatch"} = $rbatch;

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
                 $courses{$code}{"sites"},
                 $courses{$code}{"rbatch"},
                 $courses{$code}{"slot"} || ""), "\n";
    }
    print "\n";
  }

# === above to be moved to a library module === 

sub main
{
    open IN, "<phaseonemail.txt" or die "Can't open 'phaseonemail.txt': $!";
    my @lines = <IN>;
    close IN;

    load_students("students.txt");

    foreach my $rollno (sort keys %students) {

        my $email = $students{$rollno}{'email'}; 
        my $name = $students{$rollno}{'name'}; 
   
        print "Sending mail to $email: ";
        
        eval {
            send_mail("PGSEM Electives <pgsemelectives\@sankara.net>",
                      "$name <$email>",
                      "PGSEM Q1 2006-07 Phase 1 Electives Submission Instructions",
                      join("", @lines), 
                      "")
        }; 

        if ($@) {
            print "FAIL: $@\n";
        } else {
            print "OK\n";
        }
    }
}

main;

# end of file
