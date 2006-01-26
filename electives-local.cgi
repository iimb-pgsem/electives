#!perl -w

# $Id: electives-local.cgi,v 1.3 2006/01/26 09:16:04 a14562 Exp $

# Copyright (c) 2006
# Sankaranarayanan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

use strict;

use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use Net::SMTP;
use Net::POP3;
use FindBin;
use DBI;
use POSIX qw(strftime);

# === begin sensitive information ===
my $login = 'sankara';
my $password = 'brealy16myers';
my $datasource = "DBI:mysql:q4_2005";
my $dblogin = 'root';
my $dbpassword = 'root123';
# === end sensitive information ===

# === begin configurable information ===
my $send_email = 0;
my $pop_required = 1;
my $config_dir = "$FindBin::Bin"; # at least for the present
my $title = "PGSEM 2005-06 Quarter 3 Electives Submission";
# === end configurable information

my %states = (
              'default' => \&print_start_page,
              'Submit Roll Number' => \&print_authentication_page,
              'Authenticate' => \&print_electives_page,
              'Submit Preferences' => \&print_ack_page
             );

# === below to be moved to a library module ===

my %students;
my %courses;
my $max_cgpa = 4.0;
my $default_cap = 70;

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

# === above to be moved to a library modele === 

sub to_page ($)
  {
    return submit(-NAME => ".state", -VALUE => shift) 
  }

sub no_such_page()
  {
    die "No such page exists";
  }

sub print_start_page()
  {
    print 
      header(), 
      start_html($title),
      start_form(),
    
      b("Step 1 of 3: submit roll number"), br,
      "Step 2 of 3: Submit authentication code", br,
      "Step 3 of 3: Submit preferences", br,

      br,

      "Roll Number (e.g., 2004101): ",
      textfield(-name=>'rollno',  -size=>50, -maxlength=>80), br,
      br, to_page('Submit Roll Number'),

      br,

      "Once submitted, you will soon receive an e-mail with an authentication code. ",
      "Please use the authentication code in Step 2.",

      br,

      end_html();
  }

sub get_authentication_code($)
  {
    my $rollno = shift;

    my $code = srand($rollno ^ time ^ $$);
    $code = int(rand(0xFFFFFFFF));
    return $code; 
  }

sub send_mail($$$$$)
{
    return 0 unless ($send_email);

    my ($rollno, $from, $to, $subject, $body) = @_;

    my $pop = Net::POP3->new('mail.sankara.net', Timeout => 30, Debug => 1);

    my $errors = 0;

    if (!$pop_required || $pop->login($login, $password)) {
   
      my $smtp = Net::SMTP->new("mail.sankara.net", 
                                Debug => 1);

      my $retval;

      $retval = $smtp->mail($from);
      $errors += ($retval != 1);
      $retval = $smtp->to($to);
      $errors += ($retval != 1);

      $retval = $smtp->data();
      $errors += ($retval != 1);

      $smtp->datasend("To: $to\n");
      $smtp->datasend("From: $from\n");
      $smtp->datasend("Subject: $subject\n");
      $smtp->datasend("\n");
      $smtp->datasend("$body\n\n");

      $retval = $smtp->dataend();
      $errors += ($retval != 1);

      $smtp->quit();

    } else {

      print "Error sending mail: unable to authenticate using POP3";
      log_db("FAIL: authrequest: error sending mail: POP3: rollno=$rollno"); 
      print end_html;
      return -1;
    }

    if ($errors) {
      print "Internal error: unable to send e-mail; please try again";
      log_db("FAIL: authrequest: error sending mail: SMTP: rollno=$rollno"); 
      print end_html;
      return -1;
    }

    return 0;
}

sub print_authentication_page()
  {
    my $rollno;

    print header(), start_html($title);

    if (!defined(param('rollno'))) {

      print "Invalid input: please try again", end_html();
      return;
    }

    $rollno = param('rollno');

    my $errors = load_students("$config_dir/students.txt");
    if ($errors) {
      print "Internal error: error loading students database", br, end_html();
      return;
    }

    unless (defined($students{$rollno})) {
      print br, "Error: roll number '$rollno' is not present in the database", 
        br, end_html();
      return;
    }

    my $code = get_authentication_code($rollno);

    # update database

    my $dbh = DBI->connect($datasource, $dblogin, $dbpassword,
        {AutoCommit => 1, RaiseError => 1} );

    unless ($dbh) {
      print br, "Error: unable to connect to database",
        br, end_html();
      return;
    }

    my $status;
    eval {
      # $dbh->begin_work();
      $status = $dbh->do("DELETE FROM authcode WHERE rollno = '$rollno';");
      die "DELETE failed" unless $status;
      $dbh->do("INSERT INTO authcode VALUES ('$rollno', '$code');");
      die "INSERT failed" unless $status;
      # $dbh->commit();
    };

    if ($@) {
      # eval { $dbh->rollback() };
      print br, "Error: unable to update database: $@",
        br, end_html();
      return;
    }

    $dbh->disconnect();

    log_db("OK: authrequest: created: rollno=$rollno code=$code");

    my $from = "PGSEM Electives Submission \<pgsemelectives\@sankara\.net\>";
    my $subject = "Authentication code";
    my $body = "\nAuthentication code: $code\n";
    my $to = $students{$rollno}{"email"};

    my $rv = send_mail($rollno, $from, $to, $subject, $body);
    return if ($rv != 0);

    log_db("OK: authrequest: mail sent: rollno=$rollno");

    print
      start_form(),

      hidden('rollno'),
    
      "Step 1 of 3: submit roll number", br,
      b("Step 2 of 3: Submit authentication code"), br,
      "Step 3 of 3: Submit preferences", br,

      br,

      "An e-mail has been sent to '$to' with the authentication code.", br,
      "Please use that code to fill the form below.", br, br,

      "Roll Number: $rollno", br,
      "Authentication code: ", br,
      textfield(-name=>'authcode',  -size=>50, -maxlength=>80), br,
      br, to_page('Authenticate'),

      br,

      "Once authenticated, you will be able to enter and submit your course preferences.", 

      br,

      end_html();
  }

sub validate_auth_code ($$)
{
    my ($rollno, $authcode) = @_;

    my $dbh = DBI->connect($datasource, $dblogin, $dbpassword,
        {AutoCommit => 1, RaiseError => 1} );
    
    unless ($dbh) {
      print br, "Error: unable to connect to database",
        br, end_html();
      return -1;
    }
    
    my $status;
    my $sth;
    do {
      $sth = $dbh->prepare("SELECT authcode FROM authcode WHERE rollno = '$rollno'");
      $status = $sth->execute();
      last unless $status;
    } while (0);
    
    unless ($status) {
      print br, "Error: unable to read from database",
        br, end_html();
      return -1;
    }
    
    my $dbauthcode;
    $sth->bind_columns(\$dbauthcode);
    while ($sth->fetch()) {
      last;
    }
    
    $sth->finish();
    $dbh->disconnect();
    
    unless ($dbauthcode) {
      return -2;
    } 

    if ($dbauthcode ne $authcode) {
      return -3;
    }
   
    return 0;
}

sub print_electives_page ()
  {
    print header(), start_html($title);
    
    if (!defined(param('rollno')) ||
        !defined(param('authcode'))) {
    
      print "Invalid input: please try again", end_html();
      return;
    }
    
    my $rollno = param('rollno');
    my $authcode = param('authcode');
   
    my $rv = validate_auth_code($rollno, $authcode);

    return if ($rv == -1);

    if ($rv == -2) {
      print br, "Error: no record exists for Roll No: '$rollno'", 
        br, end_html();
      return;
    } 
    
    if ($rv == -3) {
      print br, "Error: invalid authentication code '$authcode' for '$rollno'", 
        br, end_html();
      return;
    }

    log_db("OK: authresponse: rollno=$rollno");
   
    if ($rv == 0) {
      load_courses("$config_dir/courses.txt");
    
      print
        start_form(),
    
        hidden('rollno'),
        hidden('authcode'),
        
        "Step 1 of 3: Submit roll number", br,
        "Step 2 of 3: Submit authentication code", br,
        b("Step 3 of 3: Submit preferences"), br;
    
   
      print br;
      print "Courses offered for your reference:", br;

      print "<table border='1'>\n";
    
      print "<tr>\n";
      print "<td><b>Slot</b></td>\n";
      print "<td><b>Code</b></td>\n";
      print "<td><b>Name</b></td>\n";
      print "<td><b>Instructor</b></td>\n";
      print "<td><b>Cap</b></td>\n";
      print "</tr>\n";
   
      my @courselist = "--------";

      foreach my $course (sort 
        { my $val = $courses{$a}{"slot"} <=> $courses{$b}{"slot"};
          return $val || ($a cmp $b) } 
    
        keys %courses) {
       
        print "<tr>\n";
    
        print "<td>$courses{$course}{'slot'}</td>";
        print "<td>$course</td>";
        print "<td>$courses{$course}{'name'}</td>";
        print "<td>$courses{$course}{'instructor'}</td>";
        print "<td>$courses{$course}{'cap'}</td>";
   
        push @courselist, "$course:Slot $courses{$course}{'slot'}:$courses{$course}{'name'}";

        print "</tr>\n";
      }
   
      print "</table>\n";
      print br;

      print
        "Roll Number: $rollno", br,
    
          "Number of courses: ", 
            popup_menu(-name=>'ncourses', -values=>['1', '2', '3', '4']), br;
   

      for (my $i = 0; $i < scalar(@courselist)-1; ++$i) {

        my $pref = $i + 1;
        print "Preference $pref: ";
        print popup_menu(-name=>"pref$pref", -values=>\@courselist);
        print br;
      }

      print br, to_page('Submit Preferences'), br;

      print 
        "Soon after submission you will receive an e-mail acknowledgement.", 
    
        br,
    
        end_html();

      return;
    }
  }

sub log_db ($)
{
    my $msg = shift;

    my $timestr = strftime("%Y-%m-%d %H-%M-%S", localtime);

    # first update a log file in text format for redundancy 
    open IN, ">>electives.log";
    print IN "$timestr: $msg\n";
    close IN;

    my $dbh = DBI->connect($datasource, $dblogin, $dbpassword);
    
    unless ($dbh) {
      return -1;
    }
    
    my $status = $dbh->do("INSERT INTO log VALUES ('$timestr', '$msg');");

    unless ($status) {
      return -1;
    }

    $dbh->disconnect();

    return 0;
}

sub update_db_with_preferences ($$$)
{
    my ($rollno, $ncourses, $courselist) = @_;

    my $dbh = DBI->connect($datasource, $dblogin, $dbpassword,
        {AutoCommit => 1, RaiseError => 1} );
    
    unless ($dbh) {
      print br, "Error: unable to connect to database",
        br, end_html();
      return -1;
    }
    
    my $status;
    eval {
      # $dbh->begin_work();
      $status = $dbh->do("DELETE FROM choices WHERE rollno = '$rollno';");
      die "DELETE failed" unless $status;

      my @codes = split(',', $courselist);
      for (my $i = 0; $i < @codes; ++$i) { 
        $status = $dbh->do("INSERT INTO choices VALUES ('$rollno', $i+1, $ncourses, '$codes[$i]');");
        die "INSERT failed" unless $status;
      }
      # $dbh->commit();
    };

    if ($@) {
      # eval { $dbh->rollback() };
      print br, "Error: unable to update database: $@",
        br, end_html();
      return -1;
    }

    $dbh->disconnect();

    return 0;
}

sub print_ack_page ()
  {
    print header(), start_html($title);
    
    if (!defined(param('rollno')) ||
        !defined(param('authcode')) ||
        !defined(param('ncourses'))) {
    
      print "Invalid input: please try again", end_html();
      return;
    }
    
    my $rollno = param('rollno');
    my $authcode = param('authcode');
    my $ncourses = param('ncourses');
   
    my $errors = load_students("$config_dir/students.txt");
    if ($errors) {
      print "Internal error: error loading students database", br, end_html();
      return;
    }

    unless (defined($students{$rollno})) {
      print br, "Error: roll number '$rollno' is not present in the database", 
        br, end_html();
      return;
    }

    my $code = get_authentication_code($rollno);

    my $rv = validate_auth_code($rollno, $authcode);

    return if ($rv == -1);

    if ($rv == -2) {
      print br, "Error: no record exists for Roll No: '$rollno'", 
        br, end_html();
      return;
    } 
    
    if ($rv == -3) {
      print br, "Error: invalid authentication code '$authcode' for '$rollno'", 
        br, end_html();
      return;
    }
 
    unless ($ncourses =~ /[1234]/) {
        print "Error: invalid number of courses", br, end_html();
        log_db("FAIL: preferences: invalid number of courses: rollno=$rollno");
        return;
    }

    my @choices;

    load_courses("$config_dir/courses.txt");

    my %choices;
    my $sepfound = 0;

    for (my $i = 0; $i < scalar(keys %courses); ++$i) {

      my $pref = $i + 1;
      my $code = param("pref$pref");
      $code =~ s/:.+//g;

      if ($sepfound && !($code =~ /^-/)) {
          print br, "Error: invalid set of preferences; preferences need to be contiguous",
            br, end_html();
          log_db("FAIL: preferences: invalid set of preferences: rollno=$rollno");
          return;
      }

      if (!($code =~ /^-/) && !$courses{$code}) {
          print br, "Error: invalid preference(s) such as '$code'",
              br, end_html();
          log_db("FAIL: preferences: invalid preferences: rollno=$rollno");
          return;
      }

      if ($choices{$code}) {
          print br, "Error: duplicate preferences",
            br, end_html();
          log_db("FAIL: preferences: duplicate preferences: rollno=$rollno");
          return;
      }

      unless ($code =~ /^-/) {
          $choices{$code} = 1;
          push @choices, $code;
      }

      $sepfound = 1 if ($code =~ /^-/); # remains set
    }

    if ($ncourses > @choices) {
        print br, "Error: number of courses ($ncourses) is greater than ",
            "the number of preferences (", scalar(@choices), ") given.";
        print br, end_html();
        return;
    }

    $rv = update_db_with_preferences($rollno, $ncourses, join(',', @choices));
    return if ($rv != 0);

    log_db("OK: preferences: rollno=$rollno, ncourses=$ncourses, courselist=" . join(':', @choices));

    my $from = "PGSEM Electives Submission \<pgsemelectives\@sankara\.net\>";
    my $subject = "Course preferences";

    my $body = "\n";
    $body .= "Roll No: $rollno\n\n";
    $body .= "Number of courses: $ncourses\n\n";
    $body .= "Course preferences:\n";
    my $index = 1;
    foreach my $course (@choices) {
        $body .= "Preference $index: $course: $courses{$course}{'name'}\n"; 
        ++$index;
    }
    $body .= "\n\n";
    my $to = $students{$rollno}{"email"};

    $rv = send_mail($rollno, $from, $to, $subject, $body);
    return if ($rv != 0);

    print "Course preferences have been succesfully updated.", br;
    print "An e-mail has been sent to '$to' as an acknowledgement.", br;
    print "You may also want to print this page for future reference.", br, br;

    print "<i>Roll No: </i><b>$rollno</b>", br, br;
    print "<i>Number of courses: </i><b>$ncourses</b>", br, br;
    print "<i>Course preferences:</i>", br;

    $index = 1;
    foreach my $course (@choices) {
      print "<b>Preference $index: $course: $courses{$course}{'name'}</b>", br; 
      ++$index;
    }

    print br;

    print end_html();
  }

sub main()
{
    my $page = param(".state") || "default";

    if ($states{$page}) {
      $states{$page}->();
    } else {
      no_such_page();
    }
}

main;

# end of file
