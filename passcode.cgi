#!/usr/bin/perl -w

# $Id: passcode.cgi,v 1.1 2006/08/23 12:26:57 a14562 Exp $

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

use ElecConfig;
use Elec;

my $config_dir = "$FindBin::Bin"; # at least for the present

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

    print header(), start_html($title), h3($title);

    unless (param('passcode')) {

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
    
        my $status;
        my $sth;
        $sth = $dbh->prepare("SELECT * FROM authcode WHERE 1");
        $status = $sth->execute();
        
        unless ($status) {
          print br, "Error: unable to read from database",
            br, local_end_html();
          $dbh->disconnect();
          return;
        }
        
        my ($rollno, $code);
        $sth->bind_columns(\$rollno, \$code);
        while ($sth->fetch()) {
            print "$rollno $code<br>\n";
        }
        
        $sth->finish();
        
    
    $dbh->disconnect();


    print local_end_html;
}

main;

# end of file
