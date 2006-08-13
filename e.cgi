#!/usr/local/bin/perl -w

use strict;

use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);

my $title = "PGSEM 2006-07 Quarter 2 Electives Submission";
print header(), start_html($title), h3($title);
print "<img src=\"http://sankara.net/images/terminator-2.jpg\"/> We will be back.";
print end_html();

