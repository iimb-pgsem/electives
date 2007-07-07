#!/usr/bin/perl -Tw

# $Id: summary.cgi,v 1.5 2006/08/13 14:37:05 a14562 Exp $

# Copyright (c) 2006
# Sankaranarayanan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

BEGIN {
    unshift @INC, '/home/kvsankar/public_html/cgi-bin/';
}

use strict;

use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use FindBin;
use DBI;
use POSIX;

use ConfigDir;
use ElecConfig;
use Elec;

# my $config_dir = "$FindBin::Bin"; # at least for the present

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
        $sth = $dbh->prepare("SELECT * FROM log WHERE 1");
        $status = $sth->execute();
        
        unless ($status) {
          print br, "Error: unable to read from database",
            br, local_end_html();
          $dbh->disconnect();
          return;
        }
        
        my ($timestamp, $msg);
        $sth->bind_columns(\$timestamp, \$msg);
        while ($sth->fetch()) {
            print "$timestamp $msg<br>\n";
        }
        
        $sth->finish();
        
    
    $dbh->disconnect();


    print local_end_html;
}

main;

# end of file
