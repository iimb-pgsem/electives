#!/usr/bin/perl -Tw

# $Id: project.cgi,v 1.5 2006/08/13 14:37:05 a14562 Exp $

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

# my $config_dir = "$FindBin::Bin";

use ConfigDir;
use ElecConfig;
use Elec;

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
    read_config_info("$config_dir/config.txt");
    assign_config_info;

    unless (param('passcode')) {

      print header(), start_html($title), h3($title);
      print start_form, "Passcode: ",
        password_field(-name=>'passcode',  -size=>20, -maxlength=>20), br;
      print end_html();
      return;
    }

    my $passcode = param('passcode');
    unless ($passcode eq $adminpassword) {
      print header(), start_html($title), h3($title);
      print "Invalid passcode";
      print end_html();
      return;
    }

    load_courses("$config_dir/courses.txt", 0);
    load_students("$config_dir/students.txt");

    my $dbh = DBI->connect($datasource, $dblogin, $dbpassword,
        {AutoCommit => 1, RaiseError => 1} );
    
    unless ($dbh) {
      print header(), start_html($title), h3($title);
      print br, "Error: unable to connect to database",
        br, local_end_html();
      return;
    }
  
    my $sth = $dbh->prepare("SELECT rollno FROM choices where course = 'PROJECT'");
    my $status = $sth->execute();
    
    unless ($status) {
      print header(), start_html($title), h3($title);
      print br, "Error: unable to read from database",
        br, local_end_html();
      $dbh->disconnect();
      return;
    }
    
    my ($rollno);
    $sth->bind_columns(\$rollno);
    my %choices;

    while ($sth->fetch()) {
        $choices{$rollno} = 1;
    }
  
    $sth->finish();
    
    $dbh->disconnect();

    print "Content-type: text/plain\n\n";

    foreach $rollno (sort keys %choices) {

      print "$rollno\n";
    }
}

main;

# end of file
