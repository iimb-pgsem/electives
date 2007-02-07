#!/usr/local/bin/perl -w

# $Id: electives.cgi,v 1.34 2007/02/07 18:18:41 a14562 Exp $

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

use ElecConfig;
use Elec;
use ElecUtils;

my $config_dir = "$FindBin::Bin"; # at least for the present

my $page;

my %states;

my %p1states = (
              'default' => \&print_login_page,
              'Get Passcode' => \&print_authentication_page,
              'Login' => \&print_electives_page,
              'Submit Preferences' => \&print_p2ack_page
             );

my %p2states = (
              'default' => \&print_login_page,
              'Get Passcode' => \&print_authentication_page,
              'Login' => \&print_electives_page,
              'Submit Preferences' => \&print_p2ack_page
             );

my %p3states = (
              'default' => \&print_login_page,
              'Get Passcode' => \&print_authentication_page,
              'Login' => \&print_changes_page,
              'Submit Drop' => \&print_p3ack_page,
              'Submit Add' => \&print_p3ack_page,
              'Submit Swap' => \&print_p3ack_page,
              'Cancel Request' => \&print_p3ack_page
             );


my %p3salloc;
# allocation hash as input for phase 3 by students
# key is student roll no
# value is a hash keyed by attributes:
# courses - a hash on course ids allotted

my %p3calloc;
# allocation hash as input for phase 3 by courses
# key is course id
# nstudents is no of students
# students - a hash on student rollno allotted

sub load_allocations($)
{
    my $file = shift;
    open IN, "<$file" or die "Can't open file $file: $!";
    LINE: while (<IN>) {
        chomp;
        next if skip_line($_);
        my ($rollno, $name, $email, $asked, $allowed, $alloted, $sen, $senreason, $allocationlist) = 
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

              $course =~ s/\-[BC]//; # get rid of -B and -C
            $student_courses{$course} = 1;
	    $p3calloc{$course}{"students"}{$rollno} = 1;
	    $p3calloc{$course}{"nstudents"}++;
          }
	}

        $p3salloc{$rollno}{"courses"} = \%student_courses;
    }
    close IN;

    return 0;
}

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
students for applying for elective courses
EOF

    if ($phase =~ /2R/) {

      print <<'EOF';
. You can view your phase 2 results by logging in here.</div>
EOF

    }
    elsif ($phase =~ /3R/) {

      print <<'EOF';
. You can view your phase 3 results by logging in here.</div>
EOF

    }
    else {

      print " (<b>Phase $phase";
      print <<'EOF';
</b>) for the quarter starting
EOF
      
      print " $quarter_starts_str.";
      print <<'EOF';
<br>Submission deadline is
EOF

      print " $deadline_str.";
      print <<'EOF';
<br><br>

<font color='red'>Submissions after the deadline will only be considered 
subject to the PGSEM Chairperson's approval.</font><br><br>

EOF

      if ($phase =~ /1/) {

        print <<'EOF';
<font color='red'>As per PGSEM rules, you will be allowed to participate in Phase 2 
<i>only if</i> you submit your Phase 1 preferences.</font><br><br>
EOF
      }
      elsif ($phase =~ /2/) {
        print <<'EOF';
<font color='red'>As per PGSEM rules, if you have not participated in phase 1, your
choices for phase 2 will be considered after considering the choices
of all other students.</font><br><br>
EOF
      }

      print <<"EOF";

The official rules and processes are provided in the 
<a href=\"$moodle_url">IIMB moodle site</a>.
These rules and processes are explained with examples 
<a href="http://sankara.net/pgsem/electives-allocation.html">here</a>.
</div>

<div style="">The process of applying for the electives
can be accomplished in three easy steps. These are as
follows:

<ol>

<li>Get a passcode: Use the form below, enter your roll
number and press the "Get Passcode" button. A passcode will be e-mailed
to you at your IIMB email id. This is necessary so as to ensure that no
one else can enter elective choices on your behalf. 

A passcode is valid only for a single quarter.
You need to get a new passcode for Phase 1.
However, once a passcode is generated in Phase 1,
you can continue to use it for Phases 2 and 3.
Even if you forget your passcode, you can fetch it later.</li><br>

<li>Login: You can now login by entering <b>both</b> your roll number <b>and</b>
this passcode and pressing the "Login" button. You will be sent to the
elective choice page.</li><br>
EOF

      if (($phase =~ /1/) || ($phase =~ /2/)) {
        print <<'EOF';
        <li>Choose: In the elective choice page,
select the number of elective courses you wish to do, then give your choices as
per the priority (first elective course is highest priority) and submit the
choices you want to take. This will acknowledge the choices you
selected by listing them and will also send you a mail about the
elective courses you chose. In Phase 1 you can give a maximum of 3 choices only. 
EOF
      } elsif ($phase =~ /3/) {
        print <<'EOF';
        <li>Drop/Add/Swap: In the elective choice page,
select the elective course to be addded/dropped/swapped and submit
using the appropriate button.
EOF
      }

      print <<'EOF';
 </li><br></ol> </div>
EOF
      if ($phase =~ /2A/) {
          print "<br><b>Note for Phase 2A</b>:<br>\n";
          print "<ol>\n";
          print "<li>The current phase (Phase 2A) is meant for seniors only. If you are a junior, please note that your choices will not be considered as part of phase 2A even if you submit them\n";
          print "<li>Please remember to indicate whether you are doing a project course in Phase 2.</li><br>";
          print "</ol>"
      }

      if ($phase =~ /2B/) {
          print "<br><b>Note for Phase 2B</b>:<br>\n";
          print "<ol>\n";
          print "<li>The current phase (Phase 2B) is meant for juniors and those who missed Phase 1 or 2A.\n";
          print "If you have been allotted courses based on Phase 2A, you can't access Phase 2B.</li>\n";
          print "<li>Please remember to indicate whether you are doing a project course in Phase 2.</li><br>";
          print "</ol>"
      }
  }

    print
        start_form(),
        
        "<table><tr>\n",

        "<td>Roll Number:</td>",
        "<td>", textfield(-name=>'rollno',  -size=>20, -maxlength=>13),
        to_page('Get Passcode'), "</td></tr>",

        "<tr><td>Passcode:</td>",
        "<td>", password_field(-name=>'authcode',  -size=>20, -maxlength=>20),
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

    my $sendmail = "/usr/sbin/sendmail $to";

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

    my $origrollno = $rollno; # preserve admin: prefix if one exists
    $rollno =~ s/^admin://;

    unless (defined($students{$rollno})) {
      print br, "Error: roll number '$rollno' is not present in the database.", br,
        "If this is a valid roll number, please send e-mail to ",
        "<a href=\"mailto:pgsemelectives\@sankara.net\">pgsemelectives\@sankara.net</a>",
        " reporting the problem.", br,
        br, local_end_html();
      return;
    }

    my $site = $students{$rollno}{'site'};
    my $displayed_site;
    $displayed_site = 'Bangalore' if ($site =~ /B/);
    $displayed_site = 'Chennai' if ($site =~ /C/);

    print "<table>\n";
    print "<tr><td>Roll Number:</td><td>$rollno</td></tr>\n";
    print "<tr><td>Name:</td><td>$students{$rollno}{'name'}</td></tr>";
    print "<tr><td>E-Mail:</td><td>$students{$rollno}{'email'}</td></tr>";
    print "<tr><td>Site:</td><td>$displayed_site</td></tr>";
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
      "<td>", textfield(-name=>'rollno',  -size=>20, -maxlength=>13, -value=>'$rollno'),
      to_page('Get Passcode'), "</td></tr>",

      "<tr><td>Passcode:</td>",
      "<td>", password_field(-name=>'authcode',  -size=>20, -maxlength=>20),
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
    $sth = $dbh->prepare("SELECT priority, ncourses, course, project FROM choices WHERE rollno = '$rollno'");
    $status = $sth->execute();
    
    unless ($status) {
      print br, "Error: unable to read from database",
        br, local_end_html();
      $dbh->disconnect();
      return -1;
    }
    
    my ($priority, $ncourses, $course, $project);

    $sth->bind_columns(\$priority, \$ncourses, \$course, \$project);
    while ($sth->fetch()) {
      if ($course ne "PROJECT") {
        $#{$rec->{"courses"}} = $priority-1;
        ${$rec->{"courses"}}[$priority-1] = $course;
        $rec->{"ncourses"} = $ncourses;
        $rec->{"project"} = ($project ? "Yes" : "No"); # to be deprecated
      } else {
        $rec->{"project"} = "Yes";
      }
    }
    
    $sth->finish();
    $dbh->disconnect();
    
    return 0; 
}

sub is_authcode_ok($$)
{
    my ($rollno, $authcode) = @_;

    if ($rollno =~ /^admin:/) {
        return ($authcode eq $adminpassword);
    }

    my $rv = get_authcode_from_db($rollno);

    return 0 if ($rv < 0);
    return ($rv == $authcode);
}

my %p2a_students;

sub load_p2a_students($) 
{
    my $file = shift;
    open IN, "<$file" or die "Can't load $file: $!\n";
    while (<IN>) {
        chomp;
        next if skip_line($_);
        $p2a_students{$_} = 1;
    }
    close IN;
}

my %allocation;

sub load_p2_allocation ($)
{
    my $filename = shift;

    open IN, "<$filename" or die "Can't open $filename: $!";

    while (<IN>) {
        chomp;
        
        my ($rollno, $name, $email, $nasked, $nallowed, 
	    $nallotted, $seniority, $senreason, $ca) = 
          split(/\s*;\s*/);

        my @calist = split(/,/, $ca);

        my @clist;
        my %alloc;

        foreach my $token (@calist) {
            my ($course, $status) = split(/=/, $token);
            push @clist, $course;
            $alloc{$course} = $status;
        }

        $allocation{$rollno}{'name'} = $name;
        $allocation{$rollno}{'email'} = $email;
        $allocation{$rollno}{'nasked'} = $nasked;
        $allocation{$rollno}{'nallowed'} = $nallowed;
        $allocation{$rollno}{'nallotted'} = $nallotted;
        $allocation{$rollno}{'seniority'} = $seniority;
        $allocation{$rollno}{'senreason'} = $senreason;
        $allocation{$rollno}{'clist'} = \@clist;
        $allocation{$rollno}{'alloc'} = \%alloc;
    }

    close IN;
}

my %senreasons = 
  (
   "NO:P1" => "Missed phase 1",
   "NO:CRED" => "Completion of credits",
   "NO:P2A" => "Missed phase 2A",
   "NO:LATE" => "Late submission"
  );

sub print_p2_result($)
{
  my $rollno = shift;
  if (!defined($allocation{$rollno})) {

    print "No courses have been allocated to you as you did not participate in phase 2.<br/>\n";
    return;
  }
  print "Here are the results of your phase 2 course allocations.<br/>\n";

  print "Roll number: $rollno<br/>\n";
  print "Name: $allocation{$rollno}{'name'}<br/>\n";
  print "E-Mail: $allocation{$rollno}{'email'}<br/>\n";
  print "Seniority: "
    . (($allocation{$rollno}{'seniority'} ne $allocation{$rollno}{'senreason'})
       ? "None ($senreasons{$allocation{$rollno}{'senreason'}})"
       : "$allocation{$rollno}{'seniority'}")
      . "<br/>\n";
  print "<br/>";
  print "#Courses asked: $allocation{$rollno}{'nasked'}<br/>\n";
  print "#Courses max allowed: $allocation{$rollno}{'nallowed'}<br/>\n";
  print "#Courses allotted: $allocation{$rollno}{'nallotted'}<br/>\n";
  print "<br/>\n";

  print '<h3>Allocation results</h3><table border="2">';
  print "<tr><th>Preference #</th><th>Course</th><th>Status</th>\n";
  my $count = 1;
  foreach my $course (@{$allocation{$rollno}{'clist'}}) {

    print "<tr>";
    my $status = $allocation{$rollno}{'alloc'}->{$course};
    
    print "<td>$count</td><td>",
      $allocation{$rollno}{'clist'}->[$count-1], "</td><td>",
	$status;

    if ($status =~ /Allotted/) {
      print " (", $courses{$course}{'slot'}, ")";
      print "</td></tr>\n"
    }
    
    ++$count;
  }
  print "</table>";
  print <<'EOF';
<br/>
For any clarifications regarding the allocation, 
please get in touch with the PGSEM office.<br/>

We would be grateful if you can provide us feedback
on the the preferences submission, allocation, and 
communication processes at our <a href="http://sankara.net/cgi-bin/feedback.cgi">feedback page</a>.


<h3>Legend for status</h3>
<dl>
<dt>Allotted</dt><dd>Course is allotted.</dd>
<dt>Allowed:n</dt>
<dd>
Course is NOT allotted. Reasons coud be either of<br/>
<ol>
<li>CGPA <  2.75, doing project course, 3 requested</li>
<li>CGPA <  2.75, not doing project course, 4 requested</li>
<li>CGPA >= 2.75, doing project course, 4 requested</li>
</ol>
</dd>
<dt>Capped</dt>
<dd>Course NOT allotted. Reasons can be either of<br/>
<ol>
<li>Course capped due to instructor set cap.</li>
<li>Course capped due to class capacity constraints.</li>
</ol>
</dd>
<dt>Complete</dt><dd>Course NOT allotted.<br/>
Number of courses asked for has been allotted.</dd>
<dt>Dropped</dt><dd>Course NOT allotted.<br\>
Course has been dropped.</dd>
<dt>SC:XXX</dt><dd>Course NOT allotted.<br/>
There is a schedule conflict with the course XXX requested
by you at a higher preference and XXX has been allotted.</dd>
</dl>
EOF

}

my %p3allocation;

sub load_p3_allocation ($)
{
    my $filename = shift;

    open IN, "<$filename" or die "Can't open $filename: $!";

    while (<IN>) {
        chomp;
        
        my ($rollno, $oldcourses, $trtype, $drop, $add,
	    $status, $reason, $newcourses) = 
          split(/\s*;\s*/);

        my @oldclist = split(/,/, $oldcourses);
        my @newclist = split(/,/, $newcourses);

        $p3allocation{$rollno}{'oldcourses'} = \@oldclist;
        $p3allocation{$rollno}{'trtype'} = $trtype;
        $p3allocation{$rollno}{'drop'} = $drop;
        $p3allocation{$rollno}{'add'} = $add;
        $p3allocation{$rollno}{'status'} = $status;
        $p3allocation{$rollno}{'reason'} = $reason;
        $p3allocation{$rollno}{'newcourses'} = \@newclist;
    }

    close IN;
}

sub print_p3_result($)
{
  my $rollno = shift;
  if (!defined($p3allocation{$rollno})) {

    print "There is no change in your allocations in phase 3 as you did not participate in this phase.<br/>\n";
    return;
  }
  print "Here are the results of your phase 3 allocation change request.<br/>\n";

  print "Roll number: $rollno<br/>\n";
  print "Name: $students{$rollno}{'name'}<br/>\n";
  print "E-Mail: $students{$rollno}{'email'}<br/>\n";
  print "<br/>";

  my $ncourses = scalar(@{$p3allocation{$rollno}{"oldcourses"}});
  if ($ncourses > 0) {

    if ($ncourses == 1) {

      print "Your only course before phase 3 was as follows:<br/>\n";
    }
    else {

      print "Your $ncourses courses before phase 3 were as follows:<br/>\n";
    }
    print "<ol>\n";
    for my $course (sort @{$p3allocation{$rollno}{"oldcourses"}}) {

      print "<li>$course - " . $courses{$course}{"name"} . "</li>\n";
    }
    print "</ol>\n";
  }
  else {

    print "Your had no courses before phase 3.<br/>\n";
  }

  print "<br/>Your request was to ";
  if ($p3allocation{$rollno}{"trtype"} eq "A") {

    print "add course " . $p3allocation{$rollno}{"add"} . ".<br/><br/>\n";
  }
  elsif ($p3allocation{$rollno}{"trtype"} eq "D") {

    print "drop course " . $p3allocation{$rollno}{"drop"} . ".<br/><br/>\n";
  }
  else {

    print "swap course " . $p3allocation{$rollno}{"drop"} . " with " . $p3allocation{$rollno}{"add"} . ".<br/><br/>\n";
  }

  if ($p3allocation{$rollno}{"status"} eq "D") {

    print "This request was successful.<br/><br/>\n";
  }
  elsif ($p3allocation{$rollno}{"status"} eq "N") {

    print "This request was not successful as ";
    if ($p3allocation{$rollno}{"reason"} eq "Capped") {

      print "the course you wished to add (" . $p3allocation{$rollno}{"add"} . ") is capped.<br/><br/>\n";
    }
    elsif ($p3allocation{$rollno}{"reason"} eq "Quorum") {

      print "the course you wished to drop (" . $p3allocation{$rollno}{"drop"} . ") will fall short of minimum requirements.<br/><br/>\n";
    }
    elsif ($p3allocation{$rollno}{"reason"} =~ "Allowed:") {

      print "you have already taken maximum number of courses and are not allowed to take one more.<br/><br/>\n";
    }
    else {

      print "it happens.<br/><br/>\n";
    }
  }
  else {

    print "This request is still pending, please contact PGSEM office.<br/><br/>\n";
  }

  $ncourses = scalar(@{$p3allocation{$rollno}{"newcourses"}});
  if ($ncourses > 0) {

    if ($ncourses == 1) {

      print "Your only course after phase 3 is as follows:<br/>\n";
    }
    else {

      print "Your $ncourses courses after phase 3 are as follows:<br/>\n";
    }
    print "<ol>\n";
    for my $course (sort @{$p3allocation{$rollno}{"newcourses"}}) {

      print "<li>$course - " . $courses{$course}{"name"} . "</li>\n";
    }
    print "</ol>\n";
  }
  else {

    print "Your have no courses after phase 3.<br/>\n";
  }

  print "<br/>For any clarifications regarding the allocation, please get in touch with the PGSEM office.<br/>\n";
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
  
    my $loggedin = 0;

    if ($rollno =~ /^admin:(\d+)$/) {
        $rollno = $1;
        if ($authcode eq $adminpassword) {
            # admin access for roll number $rollno
            log_db("OK: login.admin: rollno=$rollno");
            $loggedin = 1;
        } 

    } elsif (is_authcode_ok($rollno, $authcode)) {
            $loggedin = 1;
            log_db("OK: login: rollno=$rollno");
    }
     
    unless ($loggedin) {
          print br, "Error: invalid passcode '$authcode' for '$rollno'", 
            br, local_end_html();
          log_db("FAIL: login: rollno=$rollno code=$authcode");
          return;
    }


    my $errors = load_students("$config_dir/students.txt");

    if ($phase =~ /2R/) {

      load_courses("$config_dir/courses-internal.txt", 1);
      load_p2_allocation("$config_dir/allocation-internal.txt");
      print_p2_result($rollno);
      print local_end_html();
      return;
    }
    if ($phase =~ /3R/) {

      load_courses("$config_dir/courses-internal.txt", 1);
      load_p3_allocation("$config_dir/p3-allocation.txt");
      print_p3_result($rollno);
      print local_end_html();
      return;
    }
    if ($phase =~ /2B/) {

      load_p2a_students("$config_dir/p2a-students.txt");

      if (defined($p2a_students{$rollno})) {

        print "You have been allotted courses based on Phase 2A.<br>\n";
        print "Hence you cannot participate in the current phase (Phase 2B).<br>\n";
        print local_end_html();
        return;
      }
    }

    load_courses("$config_dir/courses.txt", 0);
    my $site = $students{$rollno}{'site'};

    my %courses_for_student;

    foreach my $course (keys %courses) {
      my $course_sites = $courses{$course}{"site"};
      my $student_can_take_course = 0;
      if (index($course_sites, $site) >= 0) {
          $student_can_take_course = 1;
      }
      if (index($courses{$course}{'barred'}, year_from_rollno($rollno)) >= 0) {
          $student_can_take_course = 0;
      }
      if ($student_can_take_course) {
          $courses_for_student{$course} = 1;
      }
    }
      
    my $displayed_site;
    $displayed_site = 'Bangalore' if ($site =~ /B/);
    $displayed_site = 'Chennai' if ($site =~ /C/);

    print "<table>\n";
    print "<tr><td>Roll Number:</td><td>$rollno</td></tr>\n";
    print "<tr><td>Name:</td><td>$students{$rollno}{'name'}</td></tr>";
    print "<tr><td>E-Mail:</td><td>$students{$rollno}{'email'}</td></tr>";
    print "<tr><td>Site:</td><td>$displayed_site</td></tr>";
    print "</table>\n";
   
    
    print
      start_form(),
      hidden('rollno'),
      hidden('authcode');
      
    print br;
    print "Courses offered for your reference:", br;

    print "<font size=\"-1\"><table border='1'>\n";
    
    print "<tr>\n";
    print "<td><b>Slot</b></td>\n" unless ($phase =~ /1/);
    print "<td><b>Code</b></td>\n";
    print "<td><b>Name</b></td>\n";
    print "<td><b>Instructor</b></td>\n";
    print "<td><b>Cap</b></td>\n";
    print "<td><b>Sites</b></td>\n";
    print "<td><b>Batches <i>not</i> Allowed<b></td>";
    print "<td><b>Available to You</b></td>\n";
    print "</tr>\n";
   
    my @courselist = "--------";
    my %coursecode_to_menuitem;

    foreach my $course (sort 
      { my $val = $courses{$a}{"slot"} <=> $courses{$b}{"slot"};
        return $val || ($a cmp $b) } 
    
      keys %courses) {

      my $sites = $courses{$course}{"site"};
      my $sites_displayed = '';
      if ($courses{$course}{"distributed"}) {
          $sites_displayed = ($phase =~ /1/ ? "Potentially " : "") . "Distributed";
      } elsif ($sites eq 'B') {
        $sites_displayed = 'Bangalore';
      } elsif ($sites eq 'C') {
        $sites_displayed = 'Chennai';
      } 

      my $student_can_take_course = 0;
      my $bgcolor = 'white';

      if (index($sites, $site) >= 0) {
        # B =~ B, B =~ B+C, C =~ C, C =~ B+C
        $student_can_take_course = 1;
      }
     
      if (index($courses{$course}{'barred'}, year_from_rollno($rollno)) >= 0) {
          $student_can_take_course = 0;
      }

      $bgcolor = '#D0D0D0' unless $student_can_take_course;

      print "<tr bgcolor='$bgcolor'>\n";
    
      print "<td>$courses{$course}{'slot'}</td>" unless ($phase =~ /1/);
      print "<td>$course</td>";
      print "<td>$courses{$course}{'name'}</td>";
      print "<td>$courses{$course}{'instructor'}</td>";
      print "<td>", $courses{$course}{'cap'}||"No cap", "</td>";
      print "<td>", $sites_displayed, "</td>";
      print "<td>", $courses{$course}{'barred'}, "</td>";
      print "<td>", $student_can_take_course ? "Yes" : "No", "</td>";
   
      my $menuitem = "$course:" . 
        (($phase =~ /1/) ? ":" : "Slot $courses{$course}{'slot'}:") . 
        "$courses{$course}{'name'}:" . "$sites_displayed";

      if ($student_can_take_course) {
        push @courselist, $menuitem; 
        $coursecode_to_menuitem{$course} = $menuitem;
      }

      print "</tr>\n";
    }
   
    print "</table></font>\n";
    print br;




    if ($phase =~ /2A/) {
        print "<br><b>Note for Phase 2A</b>:<br>\n";
        print "<ol>\n";
        print "<li>The current phase (Phase 2A) is meant for seniors only. If you are a junior, please note that your choices will not be considered as part of phase 2A even if you submit them\n";
        print "<li>Please remember to indicate whether you are doing a project course in Phase 2.</li><br>";
        print "</ol>"
    }

    if ($phase =~ /2B/) {
        print "<br><b>Note for Phase 2B</b>:<br>\n";
        print "<ol>\n";
        print "<li>The current phase (Phase 2B) is meant for juniors and those who missed Phase 1 or 2A.\n";
        print "If you have been allotted courses based on Phase 2A, you can't access Phase 2B.</li>\n";
        print "<li>Please remember to indicate whether you are doing a project course in Phase 2.</li><br>";
        print "</ol>"
    }

   my %rec;
   my $rec = \%rec;
   my $rv = get_preferences_from_db($rollno, $rec);

   my $history = ($rv == 0) && 
                 ((defined($rec->{'ncourses'}) && ($rec->{'ncourses'} > 0)) ||
                 ((defined($rec->{'project'}) && ($rec->{'project'} eq "Yes"))));

   if ($history) {
     print "<font color='blue'>";
     print "Note: preferences you submitted earlier are shown below.";
     print "</font><br><br>\n";
   }

   print
        br, "Number of elective courses you are planning to take: ", "<blink>*</blink>", 
          popup_menu(-name=>'ncourses', 
                     -values=>['-', '0', '1', '2', '3', '4'],
                     -default=>($history ? $rec->{"ncourses"} : '-')), br, br;
   
   print
        br, "Planning to take a project course?", "<blink>*</blink>", 
          popup_menu(-name=>'project', 
                     -values=>['-', 'No', 'Yes'],
                     -default=>($history ? $rec->{"project"} : '-')), br, br;
   

    for (my $i = 0; $i < scalar(@courselist)-1; ++$i) {

      last if (($phase =~ /1/) && ($i == 3)); 
      # only 3 choices for Phase 1 as per PGSEM office

      my $pref = $i + 1;
      print "Preference $pref: ";
      print popup_menu(
        -name=>"pref$pref", 
        -values=>\@courselist,
        -default=>($history ? 
        ($coursecode_to_menuitem{${$rec->{"courses"}}[$i]} || $courselist[0]) :$courselist[0]));
      print br;
    }

    print br, to_page('Submit Preferences'), br;

    print local_end_html();

    return;
}

sub get_drop_list ($)
{
  my $rollno = shift;

  return keys %{$p3salloc{$rollno}{"courses"}};
}

sub get_add_list ($$)
{
  my $rollno = shift;
  my $swap = shift;

  my @all_courses = available_courses_for_student($rollno); 
  my %allocated_courses = %{$p3salloc{$rollno}{"courses"}};

  my %allocated_slots;

  foreach my $course (keys %allocated_courses) {
      $allocated_slots{$courses{$course}{'slot'}} = 1;
  }

  my @add_courses;

  foreach my $course (@all_courses) {
    my $slot = $courses{$course}{'slot'};
    unless (defined($allocated_courses{$course})) {
        push @add_courses, $course unless 
          (!$swap && defined($allocated_slots{$slot}));
    }
  }

  return @add_courses;
}

sub available_courses_for_student ($) 
{
  my $rollno = shift;

  my $site = $students{$rollno}{'site'};
  my @available_courses_for_student;

  foreach my $course (keys %courses) {
    my $course_sites = $courses{$course}{"site"};
    my $student_can_take_course = 0;
    if (index($course_sites, $site) >= 0) {
        $student_can_take_course = 1;
    }
    if (index($courses{$course}{'barred'}, year_from_rollno($rollno)) >= 0) {
        $student_can_take_course = 0;
    }
    if ($student_can_take_course) {
        push @available_courses_for_student, $course;
    }
  }

  return @available_courses_for_student; 
}

sub menulist_from_courselist
{
  my $rollno = shift;
  my $clistref = shift;

  my $site = $students{$rollno}{'site'};
  
  my @clist = @$clistref;

  my @menulist = "--------";
  my %coursecode_to_menuitem;

  foreach my $course (sort 
    { my $val = $courses{$a}{"slot"} <=> $courses{$b}{"slot"};
      return $val || ($a cmp $b) } @clist) {

    my $sites = $courses{$course}{"site"};
    my $sites_displayed = '';
    if ($courses{$course}{"distributed"}) {
        $sites_displayed = ($phase =~ /1/ ? "Potentially " : "") . "Distributed";
    } elsif ($sites eq 'B') {
      $sites_displayed = 'Bangalore';
    } elsif ($sites eq 'C') {
      $sites_displayed = 'Chennai';
    } 

    my $student_can_take_course = 0;

    if (index($sites, $site) >= 0) {
      # B =~ B, B =~ B,C, C =~ C, C =~ B,C
      $student_can_take_course = 1;
    }
   
    if (index($courses{$course}{'barred'}, year_from_rollno($rollno)) >= 0) {
        $student_can_take_course = 0;
    }
  
    my $menuitem = "$course:" . 
      (($phase =~ /1/) ? ":" : "Slot $courses{$course}{'slot'}:") . 
      "$courses{$course}{'name'}:" . "$sites_displayed";

    if ($student_can_take_course) {
      push @menulist, $menuitem; 
      $coursecode_to_menuitem{$course} = $menuitem;
    }
  }

  return (\@menulist, \%coursecode_to_menuitem);
}

sub print_changes_page ()
{
    print header(), start_html($title), h3($title);
    
    if (!defined(param('rollno')) ||
        !defined(param('authcode'))) {
    
      print "Invalid input: please try again", local_end_html();
      return;
    }
    
    my $rollno = param('rollno');
    my $authcode = param('authcode');
 
    my $loggedin = 0;

    if ($rollno =~ /^admin:(\d+)$/) {
        $rollno = $1;
        if ($authcode eq $adminpassword) {
            # admin access for roll number $rollno
            log_db("OK: login.admin: rollno=$rollno");
            $loggedin = 1;
        } 

    } elsif (is_authcode_ok($rollno, $authcode)) {
            $loggedin = 1;
            log_db("OK: login: rollno=$rollno");
    }
     
    unless ($loggedin) {
          print br, "Error: invalid passcode '$authcode' for '$rollno'", 
            br, local_end_html();
          log_db("FAIL: login: rollno=$rollno code=$authcode");
          return;
    }

    load_students("$config_dir/students.txt");
    load_courses("$config_dir/courses.txt", 0);
    load_allocations("$config_dir/allocation-internal.txt");
   
    my @droplist = get_drop_list($rollno);
    my ($droplist_menu_ref, $drop_coursecode_to_menuitem_ref) =
      menulist_from_courselist($rollno, \@droplist);

    my @addlist = get_add_list($rollno, 0); # swap set to 0
    my ($addlist_menu_ref, $add_coursecode_to_menuitem_ref) =
      menulist_from_courselist($rollno, \@addlist);

    my @swapaddlist = get_add_list($rollno, 1); # swap set to 0
    my ($swapaddlist_menu_ref, $swapadd_coursecode_to_menuitem_ref) =
      menulist_from_courselist($rollno, \@swapaddlist);

    print
      start_form(),
      hidden('rollno'),
      hidden('authcode');
    
    my $request; 
    my $rv = get_changes_from_db($rollno, \$request);
   
    if ($rv != 0) {
        print "Error: database error; plase try again later", br;
        print local_end_html;
        return;
    }

    if (($rv == 0) && defined($request)) {

        my $request_displayed = $request;
        $request_displayed =~ s/A:/Add /;
        $request_displayed =~ s/D:/Drop /;
        $request_displayed =~ s/S:([\w\-]+)\,\s*([\w\-]+)/Swap $1 with $2/;

        print "<font color='blue'>Your earlier request was: $request_displayed</font>", br;

        print br, to_page('Cancel Request'), br;
    }

    print <<EOF;
<div style="background-color:#ffd; border:black solid 2px;
margin:1em; padding:5px">
EOF

    print "<b>Drop</b>", br;

    print br, popup_menu(
        -name=>'drop', 
        -values=>$droplist_menu_ref), br;

    print br, to_page('Submit Drop'), br;

    print "</div>";

    print br, "<b><i>Or</i></b>", br;

    print <<EOF;
<div style="background-color:#ffd; border:black solid 2px;
margin:1em; padding:5px">
EOF

    print "<b>Add</b>", br;

    print br, popup_menu(
        -name=>'add', 
        -values=>$addlist_menu_ref), br;

    print br, to_page('Submit Add'), br;

    print "</div>";

    print br, "<b><i>Or</i></b>", br;

    print <<EOF;
<div style="background-color:#ffd; border:black solid 2px;
margin:1em; padding:5px">
EOF
    print "<b>Swap</b>", br;

    print br, popup_menu(
        -name=>'swapdrop', 
        -values=>$droplist_menu_ref), br;

    print br, popup_menu(
        -name=>'swapadd', 
        -values=>$swapaddlist_menu_ref), br;

    print br, to_page('Submit Swap'), br;

    print "</div>";

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

sub update_db_with_changes ($$)
{
    my ($rollno, $request) = @_;

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
      $status = $dbh->do("DELETE FROM changes WHERE rollno = '$rollno';");
      die "DELETE failed" unless $status;

      $status = $dbh->do("INSERT INTO changes VALUES ('$rollno', '$request');");
        die "INSERT failed" unless $status;
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

sub delete_changes_from_db ($)
{
    my ($rollno) = @_;

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
      $status = $dbh->do("DELETE FROM changes WHERE rollno = '$rollno';");
      die "DELETE failed" unless $status;
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

sub get_changes_from_db($$) 
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
    $sth = $dbh->prepare("SELECT request FROM changes WHERE rollno = '$rollno'");
    $status = $sth->execute();
    
    unless ($status) {
      print br, "Error: unable to read from database",
        br, local_end_html();
      $dbh->disconnect();
      return -1;
    }
    
    my ($request);

    $sth->bind_columns(\$request);
    while ($sth->fetch()) {
        $$rec = $request;
    }
    
    $sth->finish();
    $dbh->disconnect();
    
    return 0; 
}

sub update_db_with_preferences ($$$$)
{
    my ($rollno, $ncourses, $courselist, $project) = @_;

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
        my $project_code = (($project eq "Yes") ? 1 : 0);
        $status = $dbh->do("INSERT INTO choices VALUES ('$rollno', $i+1, $ncourses, '$codes[$i]', '1', '$project_code');");
        die "INSERT failed" unless $status;
      }
      if ($project eq "Yes") {
        $status = $dbh->do("INSERT INTO choices VALUES ('$rollno', 0, $ncourses, 'PROJECT', '1', '1');");
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

sub print_p2ack_page ()
  {
    print header(), start_html($title), h3($title);
   
    if (!defined(param('rollno')) ||
        !defined(param('authcode')) ||
        !defined(param('ncourses')) ||
        !defined(param('project'))) {
    
      print "Invalid input: please try again", local_end_html();
      return;
    }
    
    my $rollno = param('rollno');
    my $authcode = param('authcode');
    my $ncourses = param('ncourses');
    my $project = param('project');
   
    my $errors = load_students("$config_dir/students.txt");

    my $origrollno = $rollno; # preserve admin: prefix if one exists
    $rollno =~ s/^admin://;

    unless (defined($students{$rollno})) {
      print br, "Error: roll number '$rollno' is not present in the database.", br,
        "If this is a valid roll number, please send e-mail to ",
        "<a href=\"mailto:pgsemelectives\@sankara.net\">pgsemelectives\@sankara.net</a>",
        " reporting the problem.", br,
        br, local_end_html();
      return;
    }

    return unless (is_authcode_ok($origrollno, $authcode));

    my $site = $students{$rollno}{'site'};
    my $displayed_site;
    $displayed_site = 'Bangalore' if ($site =~ /B/);
    $displayed_site = 'Chennai' if ($site =~ /C/);

    print "<table>\n";
    print "<tr><td>Roll Number:</td><td>$rollno</td></tr>\n";
    print "<tr><td>Name:</td><td>$students{$rollno}{'name'}</td></tr>";
    print "<tr><td>E-Mail:</td><td>$students{$rollno}{'email'}</td></tr>";
    print "<tr><td>Site:</td><td>$displayed_site</td></tr>";
    print "</table>\n";
    print br;

    unless ($ncourses =~ /[01234]/) {
        print "Error: invalid number of courses", br, local_end_html();
        log_db("FAIL: preferences: invalid number of courses: rollno=$rollno");
        return;
    }

    unless ($project =~ /Yes|No/) {
        print "Error: invalid option for project course", br, local_end_html();
        log_db("FAIL: preferences: invalid option for project course: rollno=$rollno");
        return;
    }

    my @choices;

    load_courses("$config_dir/courses.txt", 0);

    my %choices;
    my $sepfound = 0;

    my %courses_for_student;

    foreach my $course (keys %courses) {
      my $course_sites = $courses{$course}{"site"};
      my $student_can_take_course = 0;
      if (index($course_sites, $site) >= 0) {
          $student_can_take_course = 1;
      }
      if (index($courses{$course}{'barred'}, year_from_rollno($rollno)) >= 0) {
          $student_can_take_course = 0;
      }
      if ($student_can_take_course) {
          $courses_for_student{$course} = 1;
      }
    }
      
    for (my $i = 0; $i < scalar(keys %courses_for_student); ++$i) {

      last if (($phase =~ /1/) && ($i == 3));
      # max 3 preferences for Phase 1 as per PGSEM office

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

    if (($ncourses == 0) && (@choices > 0)) {
        print br, "Error: number of courses ($ncourses) does not ",
            "equal the number of preferences (", scalar(@choices), ") given.";
        print br, local_end_html();
        return;
    }

    if ($ncourses > @choices) {
        unless (($phase =~ /1/) && ($ncourses == 4) && (@choices == 3)) {
             
        print br, "Error: number of courses ($ncourses) is greater than ",
            "the number of preferences (", scalar(@choices), ") given.";
        print br, local_end_html();
        return;
        }
    }

    my $rv = update_db_with_preferences($rollno, $ncourses, join(',', @choices), $project);
    return if ($rv != 0);

    log_db("OK: preferences: rollno=$rollno, ncourses=$ncourses, " .
        "courselist=" . join(':', @choices) . ", project=$project");

    my %rec;
    my $rec = \%rec;
    $rv = get_preferences_from_db($rollno, $rec);
    return if ($rv != 0);

    my $from = "PGSEM Electives Submission \<pgsemelectives\@sankara\.net\>";
    my $subject = "Phase $phase elective course preferences";

    my $body = "\n";
    $body .= "Phase $phase elective course preferences\n\n";
    $body .= "Roll Number: $rollno\n";
    $body .= "Name: $students{$rollno}{'name'}\n";
    $body .= "Site: $displayed_site\n\n";
    $body .= "Number of elective courses: " . ($rec->{'ncourses'} || "0") . "\n\n";
    $body .= "Whether doing project course: " . ($rec->{'project'} || "No") . "\n\n";
    $body .= "Elective course preferences:\n";
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
    print "<i>Number of elective courses: </i><b>$ncourses</b>", br, br;
    print "<i>Whether doing project course: </i><b>$project</b>", br, br;
    print "<i>Course preferences:</i>", br;

    $index = 1;
    foreach my $course (@{$rec->{'courses'}}) {
      print "<b>Preference $index: $course: $courses{$course}{'name'}</b>", br; 
      ++$index;
    }

    print br;

    print local_end_html();
  }

sub print_p3ack_page ()
  {
    print header(), start_html($title), h3($title);
  
    unless (defined(param('rollno')) &&
            defined(param('authcode')) &&
            (defined(param('cancel')) || defined(param('drop')) || defined(param('add')) || 
                (defined(param('swapdrop')) && defined(param('swapadd'))))) {

      print "Invalid input: please try again", local_end_html();
      return;
    }

    my $rollno = param('rollno');
    my $authcode = param('authcode');

    my $drop = param('drop');
    my $add = param('add');
    my $swapdrop = param('swapdrop');
    my $swapadd = param('swapadd');

    load_students("$config_dir/students.txt");

    my $origrollno = $rollno; # preserve admin: prefix if one exists
    $rollno =~ s/^admin://;

    unless (defined($students{$rollno})) {
      print br, "Error: roll number '$rollno' is not present in the database.", br,
        "If this is a valid roll number, please send e-mail to ",
        "<a href=\"mailto:pgsemelectives\@sankara.net\">pgsemelectives\@sankara.net</a>",
        " reporting the problem.", br,
        br, local_end_html();
      return;
    }

    return unless (is_authcode_ok($origrollno, $authcode));

    load_courses("$config_dir/courses.txt", 0);
    load_allocations("$config_dir/allocation-internal.txt");

    # TODO: change the following dirty switching

    my $request;
    my $request_displayed;
    my $dcourse;
    my $acourse;

    if ($page eq 'Cancel Request') {

        my $rv = delete_changes_from_db($rollno);
        return if ($rv != 0);

        log_db("OK: changes: rollno=$rollno, request=cancel");

        print "Your previous request has been cancelled.", br;
        print local_end_html;
        return;

    } elsif ($page eq 'Submit Drop') {

        if ($drop =~ /^--/) {
            print br, "Error: No course selected to be dropped.", br;
            print local_end_html;
            return;
        }

        $dcourse = (split(/:/, $drop))[0];
        $request = "D:$dcourse";
        $request_displayed = "Drop $dcourse (Slot " . $courses{$dcourse}{'slot'} . ")";

    } elsif ($page eq 'Submit Add') {

        if ($add =~ /^--/) {
            print br, "Error: No course selected to be added.", br;
            print local_end_html;
            return;
        }

        $acourse = (split(/:/, $add))[0];
        $request = "A:$acourse";
        $request_displayed = "Add $acourse (Slot " . $courses{$acourse}{'slot'} . ")";

    } elsif ($page eq 'Submit Swap') {

        if ($swapdrop =~ /^--/) {
            print br, "Error: No course selected to be dropped for the swap.", br;
            print local_end_html;
            return;
        }
        if ($swapadd =~ /^--/) {
            print br, "Error: No course selected to be added for the swap.", br;
            print local_end_html;
            return;
        }

        $dcourse = (split(/:/, $swapdrop))[0];
        $acourse = (split(/:/, $swapadd))[0];
        my $dcourse_slot = $courses{$dcourse}{'slot'};
        my $acourse_slot = $courses{$acourse}{'slot'};

        my %allotted_courses = %{$p3salloc{$rollno}{"courses"}};
        foreach my $course (keys %allotted_courses) {

            next if ($course eq $dcourse);

            if ($courses{$course}{'slot'} eq $acourse_slot) {
                print br, "Error: $acourse cannot be added as it conflicts with $course in Slot $acourse_slot", br;
                print local_end_html;
                return;
            }
        }

        $request = "S:$dcourse,$acourse";
        $request_displayed = "Swap $dcourse (Slot $dcourse_slot) with $acourse (Slot $acourse_slot)";
    }


    my $site = $students{$rollno}{'site'};
    my $displayed_site;
    $displayed_site = 'Bangalore' if ($site =~ /B/);
    $displayed_site = 'Chennai' if ($site =~ /C/);

    print "<table>\n";
    print "<tr><td>Roll Number:</td><td>$rollno</td></tr>\n";
    print "<tr><td>Name:</td><td>$students{$rollno}{'name'}</td></tr>";
    print "<tr><td>E-Mail:</td><td>$students{$rollno}{'email'}</td></tr>";
    print "<tr><td>Site:</td><td>$displayed_site</td></tr>";
    print "</table>\n";
    print br;

    my $rv = update_db_with_changes($rollno, $request);
    return if ($rv != 0);

    log_db("OK: changes: rollno=$rollno, request=$request");

    my $rec;
    $rv = get_changes_from_db($rollno, \$rec);
    return if ($rv != 0);
    return unless (defined($rec));
    $request = $rec;

    my $from = "PGSEM Electives Submission \<pgsemelectives\@sankara\.net\>";
    my $subject = "Phase 3 Change Request";

    my $body = "\n";
    $body .= "Phase 3 elective course preferences\n\n";
    $body .= "Roll Number: $rollno\n";
    $body .= "Name: $students{$rollno}{'name'}\n";
    $body .= "Site: $displayed_site\n\n";
    $body .= "Change Request: $request_displayed\n\n";

    $body .= "\n\n";
    my $to = $students{$rollno}{"email"};

    $rv = send_mail_sendmail($rollno, $from, $to, $subject, $body);
    return if ($rv != 0);

    print "Course preferences have been succesfully updated.", br;
    print "An e-mail has been sent to '$to' as an acknowledgement.", br;
    print "You may also want to print this page for future reference.", br, br;

    print "Change Request: $request_displayed", br, br;

    print local_end_html();
  }

sub main()
{
    read_config_info("$config_dir/config.txt");
    assign_config_info;

    if (time > $deadline) {
      print header(), start_html($title), h3($title);

      print "Phase " . $phase . " submission deadline is over.",  br;
      print "Please contact the PGSEM office for further assistance.", br;
      print br;

      print local_end_html();
      return;
    }

    $page = param(".state") || "default";

    if ($phase =~ /1/) {
        %states = %p1states;
    } elsif ($phase =~ /2/ || $phase =~ /3R/) {
        %states = %p2states;
    } else {
        %states = %p3states;
    }

    if ($states{$page}) {
      $states{$page}->();
    } else {
      print header(), start_html($title), h3($title);
      print "Internal error: unable to fetch page for \'$page\'.<br>\n";
      print local_end_html;
    }
}

$ENV{'TZ'} = 'IST-5:30';
main;

# end of file
