#!/usr/bin/perl -w

# $Id: feedback.cgi,v 1.2 2006/08/13 14:37:05 a14562 Exp $

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

my $title = "PGSEM Electives Submission - Feedback";

my %states = (
              'default' => \&print_feedback_form,
              'Submit Feedback' => \&print_thanks
             );

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

sub print_feedback_form()
{
    print header(), start_html($title), h3($title);

    print
        start_form(),
        
        "Name (optional): ",
        textfield(-name=>'name',  -size=>60, -maxlength=>60), br, br,

        "Comments and suggestions on the rules: ", br,
        "(we will convey these to the PGSEM office)", br,
        textarea(-name=>'rules',  -rows=>5, -columns=>60), br, br,

        "Comments and suggestions on the implementation: ", br,
        "(submission, allocation implementation, and communication -- ",
        "these are for Sankar and Abhay)", br, 
        textarea(-name=>'impl',  -rows=>5, -columns=>60), br, br,

        "How would you rate your overall experience?", br,
        radio_group(-name=>'satisfaction', 
                    -values=>['Very bad', 'Bad', 'Neutral', 
                              'Good', 'Very good'], 
                    -default=>'Neutral', 
                    -linebreak=>'true'), br, br,

        "Would you prefer to use the same process the next time?", br,
        radio_group(-name=>'loyalty', -values=>['Yes', 'No']), br, br,

        to_page('Submit Feedback'), br, br,

        local_end_html();
}

sub print_thanks
{
    my $name = param('name');
    my $rules = param('rules');
    my $impl = param('impl');
    my $satisfaction = param('satisfaction');
    my $loyalty = param('loyalty');
   
    my $timestr = strftime("%Y-%m-%d %H-%M-%S", localtime);

    open IN, ">>feedback.log";
    print IN "<record>\n";
    print IN "Time: $timestr\n";
    print IN "Name: $name\n";
    print IN "Rules: $rules\n";
    print IN "Impl: $impl\n";
    print IN "Satisfaction: $satisfaction\n";
    print IN "Loyalty: $loyalty\n";
    print IN "</record>\n";
    close IN;

    print header(), start_html($title), h3($title);
    print "Thank you for your feedback.";
    print local_end_html();
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
