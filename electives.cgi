#!/usr/bin/perl -w

# $Id: electives.cgi,v 1.11 2006/02/06 21:17:23 a14562 Exp $

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
my $login = '';
my $password = '';
my $datasource = "DBI:mysql:sankara_q42005";
my $dblogin = 'sankara_sankar';
my $dbpassword = 'sankar123';
# === end sensitive information ===

# === begin configurable information ===
my $send_email = 1;
my $pop_required = 0;
my $config_dir = "$FindBin::Bin"; # at least for the present
my $title = "PGSEM 2005-06 Quarter 4 (February - April 2006) Electives Submission";
# === end configurable information

my %states = (
              'default' => \&print_login_page,
              'Get Passcode' => \&print_authentication_page,
              'Login' => \&print_electives_page,
              'Submit Preferences' => \&print_ack_page
             );

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

sub local_end_html()
{
  return <<'EOF' . "<br>Page generated at " . localtime() . end_html();
<hr>&copy; 2006 Sankaranarayanan K. V. and Abhay Ghaisas. If you face any 
problems, please contact <a href="mailto:pgsemelectives@sankara.net">
pgsemelectives@sankara.net</a>.
EOF

}

sub print_login_page()
{
    print header(), start_html($title), h3($title);

    print <<'EOF';
<div style="background-color:#ffd; border:black solid
2px;margin:1em;padding:5px">This page is to be used by the IIMB PGSEM
students for applying for elective courses for the quarter starting
Feb. 2006.<br>Submission deadline is 24:00 IST, Monday, 6 February, 2006.<br>
<font color='red'>Submissions after the deadline will only be considered 
subject to the PGSEM Chairperson's approval.</font></div>
<div style="">The process of applying for the electives
can be accomplished in three easy steps. These are as
follows:<ol><li>Get a passcode: Use the form below, enter your roll
number and press the "Get Passcode" button. A passcode will be e-mailed
to you at your IIMB email id. This is necessary so as to ensure that no
one else can enter elective choices on your behalf.</li> <li>Login: You
can now login by entering <b>both</b> your roll number <b>and</b> this passcode and
pressing the "Login" button. You will be sent to the elective choice
page.</li><li>Choose: In the elective choice page, give your choices as
per the priority (first course is highest priority) and submit the
choices you want to take. This will acknowledge the choices you selected
by listing them and will also send you a mail about the courses you
chose.</li></ol> </div>
EOF

    print
        start_form(),
        
        "<table><tr>\n",

        "<td>Roll Number:</td>",
        "<td>", textfield(-name=>'rollno',  -size=>20, -maxlength=>7),
        to_page('Get Passcode'), "</td></tr>",

        "<tr><td>Passcode:</td>",
        "<td>", textfield(-name=>'authcode',  -size=>20, -maxlength=>20),
        to_page('Login'), "</td></tr></table>", 

        br,

        local_end_html();
}

sub create_authentication_code($)
  {
    my $rollno = shift;

    my $code = srand($rollno ^ time ^ $$);
    $code = int(rand(0x7FFFFFFF)); # invariant: $code > 0
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

      unless ($smtp) {
        print "Transient error: unable to send e-mail; please try again after a few minutes";
        log_db("FAIL: smtp: $subject: rollno=$rollno"); 
        print local_end_html;
        return -1;
      }

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
      log_db("FAIL: pop3: $subject: rollno=$rollno"); 
      print local_end_html;
      return -1;
    }

    if ($errors) {
      print "Internal error: unable to send e-mail; please try again";
      log_db("FAIL: smtp: $subject: rollno=$rollno"); 
      print local_end_html;
      return -1;
    }

    return 0;
}

sub send_mail_sendmail($$$$$)
{
    return 0 unless ($send_email);

    my ($rollno, $from, $to, $subject, $body) = @_;

    my $sendmail = "/usr/sbin/sendmail -t";

    my $errors = 0;

    my $status = open(SENDMAIL, "|$sendmail");
    unless ($status) {
      print "Transient error sending mail: please try again later after a few minutes";
      log_db("FAIL: sendmail: $subject: rollno=$rollno"); 
      print local_end_html;
      return -1;
    }

    print SENDMAIL "From: $from\n";
    print SENDMAIL "To: $to\n";
    print SENDMAIL "Subject: $subject\n";
    print SENDMAIL "X-CGIMailer: sendmail\n";
    print SENDMAIL "Content-type: text/plain\n\n";
    print SENDMAIL $body;
    close(SENDMAIL);
    return 0;
}

sub store_authcode_to_db ($$)
{
    my ($rollno, $authcode) = @_;

    my $dbh = DBI->connect($datasource, $dblogin, $dbpassword,
        {AutoCommit => 1, RaiseError => 1} );

    unless ($dbh) {
      print br, "Error: unable to connect to database",
        br, local_end_html();
      return -1;
    }

    my $status;
    eval {
      # $dbh->begin_work();
      $status = $dbh->do("DELETE FROM authcode WHERE rollno = '$rollno';");
      die "DELETE failed" unless $status;
      $dbh->do("INSERT INTO authcode VALUES ('$rollno', '$authcode');");
      die "INSERT failed" unless $status;
      # $dbh->commit();
    };

    if ($@) {
      # eval { $dbh->rollback() };
      print br, "Error: unable to update database: $@",
        br, local_end_html();
      $dbh->disconnect();
      return -1;
    }

    $dbh->disconnect();
    return 0;
}

sub print_authentication_page()
  {
    my $rollno;

    print header(), start_html($title), h3($title);

    if (!defined(param('rollno'))) {

      print "Invalid input: please try again", local_end_html();
      return;
    }

    $rollno = param('rollno');

    my $errors = load_students("$config_dir/students.txt");

    unless (defined($students{$rollno})) {
      print br, "Error: roll number '$rollno' is not present in the database.", br,
        "If this is a valid roll number, please send e-mail to ",
        "<a href=\"mailto:pgsemelectives\@sankara.net\">pgsemelectives\@sankara.net</a>",
        " reporting the problem.", br,
        br, local_end_html();
      return;
    }

    print "<table>\n";
    print "<tr><td>Roll Number:</td><td>$rollno</td></tr>\n";
    print "<tr><td>Name:</td><td>$students{$rollno}{'name'}</td></tr>";
    print "<tr><td>E-Mail:</td><td>$students{$rollno}{'email'}</td></tr>";
    print "</table>\n";
    print br;

    my $code = get_authcode_from_db($rollno);

    return if (($code < 0) && ($code != -2));

    if ($code == -2) {

        $code = create_authentication_code($rollno);
        my $rv = store_authcode_to_db($rollno, $code);
        return if ($rv != 0);
        log_db("OK: passcode_created: rollno=$rollno code=$code");

    } else {

        log_db("OK: passcode_loaded: rollno=$rollno code=$code");
    }

    my $from = "PGSEM Electives Submission \<pgsemelectives\@sankara\.net\>";
    my $subject = "Passcode";
    my $body = "Roll Number: $rollno\n\nPasscode: $code\n";
    my $to = $students{$rollno}{"email"};

    my $rv = send_mail_sendmail($rollno, $from, $to, $subject, $body);
    return if ($rv != 0);

    log_db("OK: passcode_sent: rollno=$rollno code=$code");

        
    print
      start_form(),

      #hidden('rollno'),
    
      "An e-mail has been sent to '$to' with the passcode.", br,
      "Please use that code to fill the form below.", br, br,

      "<table><tr>\n",

      "<td>Roll Number:</td>",
      "<td>", textfield(-name=>'rollno',  -size=>20, -maxlength=>8, -value=>'$rollno'),
      to_page('Get Passcode'), "</td></tr>",

      "<tr><td>Passcode:</td>",
      "<td>", textfield(-name=>'authcode',  -size=>20, -maxlength=>20),
      to_page('Login'), "</td></tr></table>", 

      br,

      local_end_html();
}

sub get_authcode_from_db($)
{
    my $rollno = shift;

    my $dbh = DBI->connect($datasource, $dblogin, $dbpassword,
        {AutoCommit => 1, RaiseError => 1} );
    
    unless ($dbh) {
      print br, "Error: unable to connect to database",
        br, local_end_html();
      return -1;
    }
    
    my $status;
    my $sth;
    $sth = $dbh->prepare("SELECT authcode FROM authcode WHERE rollno = '$rollno'");
    $status = $sth->execute();
    
    unless ($status) {
      print br, "Error: unable to read from database",
        br, local_end_html();
      $dbh->disconnect();
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

    return $dbauthcode; # invariant: $dbauthcode > 0
}

sub get_preferences_from_db($$)
{
    my $rollno = shift;
    my $rec = shift;

    my $dbh = DBI->connect($datasource, $dblogin, $dbpassword,
        {AutoCommit => 1, RaiseError => 1} );
    
    unless ($dbh) {
      print br, "Error: unable to connect to database",
        br, local_end_html();
      return -1;
    }
    
    my $status;
    my $sth;
    $sth = $dbh->prepare("SELECT priority, ncourses, course FROM choices WHERE rollno = '$rollno'");
    $status = $sth->execute();
    
    unless ($status) {
      print br, "Error: unable to read from database",
        br, local_end_html();
      $dbh->disconnect();
      return -1;
    }
    
    my ($priority, $ncourses, $course);

    $sth->bind_columns(\$priority, \$ncourses, \$course);
    while ($sth->fetch()) {
      $#{$rec->{"courses"}} = $priority-1;
      ${$rec->{"courses"}}[$priority-1] = $course;
      $rec->{"ncourses"} = $ncourses;
    }
    
    $sth->finish();
    $dbh->disconnect();
    
    return 0; 
}

sub is_authcode_ok($$)
{
    my ($rollno, $authcode) = @_;

    my $rv = get_authcode_from_db($rollno);

    return 0 if ($rv < 0);
    return ($rv == $authcode);
}

sub print_electives_page ()
{
    print header(), start_html($title), h3($title);
    
    if (!defined(param('rollno')) ||
        !defined(param('authcode'))) {
    
      print "Invalid input: please try again", local_end_html();
      return;
    }
    
    my $rollno = param('rollno');
    my $authcode = param('authcode');
   
    unless (is_authcode_ok($rollno, $authcode)) {
      print br, "Error: invalid passcode '$authcode' for '$rollno'", 
        br, local_end_html();
      log_db("FAIL: login: rollno=$rollno code=$authcode");
      return;
    }

    log_db("OK: login: rollno=$rollno");
   
    my $errors = load_students("$config_dir/students.txt");

    print "<table>\n";
    print "<tr><td>Roll Number:</td><td>$rollno</td></tr>\n";
    print "<tr><td>Name:</td><td>$students{$rollno}{'name'}</td></tr>";
    print "<tr><td>E-Mail:</td><td>$students{$rollno}{'email'}</td></tr>";
    print "</table>\n";
   
    load_courses("$config_dir/courses.txt");
    
    print
      start_form(),
      hidden('rollno'),
      hidden('authcode');
      
    print br;
    print "Courses offered for your reference:", br;

    print "<font size=\"-1\"><table border='1'>\n";
    
    print "<tr>\n";
    print "<td><b>Slot</b></td>\n";
    print "<td><b>Code</b></td>\n";
    print "<td><b>Name</b></td>\n";
    print "<td><b>Instructor</b></td>\n";
    print "<td><b>Cap</b></td>\n";
    print "</tr>\n";
   
    my @courselist = "--------";
    my %coursecode_to_menuitem;

    foreach my $course (sort 
      { my $val = $courses{$a}{"slot"} <=> $courses{$b}{"slot"};
        return $val || ($a cmp $b) } 
    
      keys %courses) {
     
      print "<tr>\n";
    
      print "<td>$courses{$course}{'slot'}</td>";
      print "<td>$course</td>";
      print "<td>$courses{$course}{'name'}</td>";
      print "<td>$courses{$course}{'instructor'}</td>";
      print "<td>", $courses{$course}{'cap'}||"No cap", "</td>";
   
      my $menuitem = "$course:Slot $courses{$course}{'slot'}:$courses{$course}{'name'}";
      push @courselist, $menuitem; 
      $coursecode_to_menuitem{$course} = $menuitem;

      print "</tr>\n";
    }
   
    print "</table></font>\n";
    print br;

    print <<'EOF';
<div style="background-color:#ffd; border:black solid
2px;margin:1em;padding:5px">The slots indicate the day and the time in
which the course will happen. Thus F1 is first slot on Friday or S4 is
fourth slot on Saturday</div>
EOF

   my %rec;
   my $rec = \%rec;
   my $rv = get_preferences_from_db($rollno, $rec);

   if (($rv == 0) && ($rec->{'ncourses'} > 0)) {
     print "<font color='blue'>";
     print "Note: preferences you submitted earlier are shown below.";
     print "</font><br><br>\n";
   }

   print
        "Number of courses: ", 
          popup_menu(-name=>'ncourses', 
                     -values=>['-', '1', '2', '3', '4'],
                     -default=>($rv == 0 ? $rec->{"ncourses"} : '-')), br;
   

    for (my $i = 0; $i < scalar(@courselist)-1; ++$i) {

      my $pref = $i + 1;
      print "Preference $pref: ";
      print popup_menu(
        -name=>"pref$pref", 
        -values=>\@courselist,
        -default=>($rv == 0 ?
          ($coursecode_to_menuitem{${$rec->{"courses"}}[$i]} || $courselist[0])
          : $courselist[0]));
      print br;
    }

    print br, to_page('Submit Preferences'), br;

    print local_end_html();

    return;
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
        br, local_end_html();
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
        br, local_end_html();
      return -1;
    }

    $dbh->disconnect();

    return 0;
}

sub print_ack_page ()
  {
    print header(), start_html($title), h3($title);
    
    if (!defined(param('rollno')) ||
        !defined(param('authcode')) ||
        !defined(param('ncourses'))) {
    
      print "Invalid input: please try again", local_end_html();
      return;
    }
    
    my $rollno = param('rollno');
    my $authcode = param('authcode');
    my $ncourses = param('ncourses');
   
    my $errors = load_students("$config_dir/students.txt");

    unless (defined($students{$rollno})) {
      print br, "Error: roll number '$rollno' is not present in the database", 
        br, local_end_html();
      return;
    }

    return unless (is_authcode_ok($rollno, $authcode));

    unless (defined($students{$rollno})) {
      print br, "Error: roll number '$rollno' is not present in the database.", br,
        "If this is a valid roll number, please send e-mail to ",
        "<a href=\"mailto:pgsemelectives\@sankara.net\">pgsemelectives\@sankara.net</a>",
        " reporting the problem.", br,
        br, local_end_html();
      return;
    }

    print "<table>\n";
    print "<tr><td>Roll Number:</td><td>$rollno</td></tr>\n";
    print "<tr><td>Name:</td><td>$students{$rollno}{'name'}</td></tr>";
    print "<tr><td>E-Mail:</td><td>$students{$rollno}{'email'}</td></tr>";
    print "</table>\n";
    print br;

    unless ($ncourses =~ /[1234]/) {
        print "Error: invalid number of courses", br, local_end_html();
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
            br, local_end_html();
          log_db("FAIL: preferences: invalid set of preferences: rollno=$rollno");
          return;
      }

      if (!($code =~ /^-/) && !$courses{$code}) {
          print br, "Error: invalid preference(s) such as '$code'",
              br, local_end_html();
          log_db("FAIL: preferences: invalid preferences: rollno=$rollno");
          return;
      }

      if ($choices{$code}) {
          print br, "Error: duplicate preferences",
            br, local_end_html();
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
        print br, local_end_html();
        return;
    }

    my $rv = update_db_with_preferences($rollno, $ncourses, join(',', @choices));
    return if ($rv != 0);

    log_db("OK: preferences: rollno=$rollno, ncourses=$ncourses, courselist=" . join(':', @choices));

    my %rec;
    my $rec = \%rec;
    $rv = get_preferences_from_db($rollno, $rec);
    return if ($rv != 0);

    my $from = "PGSEM Electives Submission \<pgsemelectives\@sankara\.net\>";
    my $subject = "Course preferences";

    my $body = "\n";
    $body .= "Roll Number: $rollno\n\n";
    $body .= "Number of courses: $rec->{'ncourses'}\n\n";
    $body .= "Course preferences:\n";
    my $index = 1;
    foreach my $course (@{$rec->{'courses'}}) {
        $body .= "Preference $index: $course: $courses{$course}{'name'}\n"; 
        ++$index;
    }
    $body .= "\n\n";
    my $to = $students{$rollno}{"email"};

    $rv = send_mail_sendmail($rollno, $from, $to, $subject, $body);
    return if ($rv != 0);

    print "Course preferences have been succesfully updated.", br;
    print "An e-mail has been sent to '$to' as an acknowledgement.", br;
    print "You may also want to print this page for future reference.", br, br;

    print "<i>Roll Number: </i><b>$rollno</b>", br, br;
    print "<i>Number of courses: </i><b>$ncourses</b>", br, br;
    print "<i>Course preferences:</i>", br;

    $index = 1;
    foreach my $course (@{$rec->{'courses'}}) {
      print "<b>Preference $index: $course: $courses{$course}{'name'}</b>", br; 
      ++$index;
    }

    print br;

    print local_end_html();
  }

sub main()
{
    # February 8, 2006, 00:00 hrs IST
    # mktime(second, minute, hour, day, month-1, year-1900)

    my $deadline = POSIX::mktime(0, 00, 00, 8, 1, 106);
    if (time > $deadline) {
      print header(), start_html($title), h3($title);

      print "Electives submission deadline is over. ";
      print "Please contact PGSEM office for further assistance. ";
      print local_end_html();
      return;
    }

    my $page = param(".state") || "default";

    if ($states{$page}) {
      $states{$page}->();
    } else {
      no_such_page();
    }
}

main;

# end of file
