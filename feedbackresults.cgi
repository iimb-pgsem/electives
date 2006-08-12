#!/usr/bin/perl -w 

use strict;

use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use FindBin;
use DBI;
use POSIX;

# === begin configurable information ===
my $config_dir = "$FindBin::Bin"; # at least for the present
my $title = "PGSEM 2005-06 Quarter 4 (February - April 2006) Electives Submission";
# === end configurable information


sub main()
{
    unless (param('passcode')) {

      print header(), start_html($title), h3($title);
      print start_form, "Passcode: ",
        password_field(-name=>'passcode',  -size=>20, -maxlength=>20), br;
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

    print header(), start_html($title);
    open IN, "<feedback.log" or die "Can't open feedback.log: $!";
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
