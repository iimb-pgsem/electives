#!/usr/bin/perl -Tw 

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

# my $config_dir = "$FindBin::Bin";

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

    print header(), start_html($title);
    open IN, "<$config_dir/feedback.log" or die "Can't open feedback.log: $!";
    my $pstate = 0;
    my $tstate = 0;
    while (<IN>) {

      s#^(\w+):#<b>$1:</b>#;

      if (/Time:/) {
        print "</table><br>\n" if ($tstate);
        print "<table>\n";
        $tstate = 1;
      }
      if (/(Time|Name|Satisfaction|Loyalty):/) {
        print "</td></tr>\n" if ($pstate);
        $pstate = 0;
        print "<tr><td>$_</td></tr>\n";
        next;
      }
      if (/(Rules|Impl):/) {
        $pstate = 1; 
        print "<tr><td>\n";
      }
      if ($pstate) {
        print;
      }
    }

    close IN;
    print end_html();
}

main;

# end of file
