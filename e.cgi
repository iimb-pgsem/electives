#!/usr/local/bin/perl -w

use strict;

use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);

my $title = "PGSEM 2006-07 Quarter 2 Electives Submission";
print header(), start_html($title), h3($title);
# print "<img src=\"http://sankara.net/images/terminator-2.jpg\"/>\n";
# print "We will be back.<br>\n";
# print "<br>\n";

print "Phase 1 submission will be enabled by 2 pm IST, Friday, August 18, 2006.<br>\n";
print "We are awaiting a potential update to the course list from the PGSEM office.<br>\n";

print end_html();

