#!/usr/bin/perl -w

# $Id: graduation.cgi,v 1.1 2007/02/15 20:07:05 a14562 Exp $

# Copyright (c) 2006-07
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

my $config_dir = "$FindBin::Bin"; # at least for the present

my $title = "PGSEM Graduation 2007";

my $admin_rights = 0;

my %states = (
              'default' => \&print_login_form,
              'Login' => \&print_profile_form,
              'Submit' => \&print_thanks
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

sub print_login_form()
{
    
    print header(), start_html($title), h3($title);

    print
        start_form(),

        "<tr><td>", "Roll number (*): ", "</td><td>",
        textfield(-name=>'rollno',  -size=>40, -maxlength=>7), "</td></tr>", br,

        "<tr><td>", "IIMB e-mail address (*): ", "</td><td>",
        textfield(-name=>'email',  -size=>40, -maxlength=>50), "</td></tr>", br,

        to_page('Login'), br, br,

        local_end_html();
}

sub print_profile_form()
{
    print header(), start_html($title), h3($title);

    my $rollno;

    if (!defined(param('rollno'))) {

      print "Invalid input: please try again", local_end_html();
      return;
    }

    $rollno = param('rollno');

    my $errors = load_students("$config_dir/graduate-candidates.txt");

    unless (defined($students{$rollno})) {
      print br, "Error: roll number '$rollno' is not present in the database.", br,
        "If this is a valid roll number, please send e-mail to ",
        "<a href=\"mailto:pgsemelectives\@sankara.net\">pgsemelectives\@sankara.net</a>",
        " reporting the problem.", br,
        br, local_end_html();
      return;
    }

    my $email = param('email');

    if ($email ne $students{$rollno}->{'email'}) {
      print br, "Error: invalid login/password combination", br;
      return;
    }

    my $name = $students{$rollno}->{'name'};
    
    print "Roll number: $rollno", br;
    print "Name: $name", br;
    print br;

    print
        start_multipart_form(),
       
        "Information collected by PGSEM office:",

        "<div style=\"background-color:#ffd; border:black solid 2px;",
        "margin:1em;padding:5px\">",

        "<table>",
        
        "<tr><td>", "IIMB course credits completed (*): ", "</td><td>",
        textfield(-name=>'iccredits',  -size=>5, -maxlength=>3), "</td></tr>", 

        "<tr><td>", "IIMB project credits completed (*): ", "</td><td>",
        textfield(-name=>'ipcredits',  -size=>5, -maxlength=>3), "</td></tr>",

        "<tr><td>", "Exchange credits completed (*): ", "</td><td>", 
        textfield(-name=>'excredits',  -size=>5, -maxlength=>3), "(0 if none)</td></tr>",

        "</table>",
        
        "</div>",

        "Information collected for graduation book:",

        "<div style=\"background-color:#ccffcc; border:black solid 2px;",
        "margin:1em;padding:5px\">",

        "<table>",
        
        "<tr><td>", "Date of birth (dd-mm-yyyy) (*): ", "</td><td>",
        textfield(-name=>'dob', -size=>20, -maxlength=>10), "</td></tr>",

        "<tr><td>", "Photo (upload file): ", "</td><td>",
        filefield(-name=>'photo', -size=>40, -maxlength=>10_000), "</td></tr>",

        "<tr><td>", "Contact E-Mail (*): ", "</td><td>",
        textfield(-name=>'contactemail',  -size=>40, -maxlength=>50), "</td></tr>",

        "<tr><td>", "Current work role: ", "</td><td>",
        textfield(-name=>'currentworkrole',  -size=>40, -maxlength=>50), "</td></tr>",

        "<tr><td>", "Current employer: ", "</td><td>",
        textfield(-name=>'currentemployer',  -size=>40, -maxlength=>50), "</td></tr>",

        "<tr><td>", "Future career plans: ", "</td><td>",
        textfield(-name=>'careerplan',  -size=>40, -maxlength=>50), "</td></tr>",

        "<tr><td>", "PGSEM memories / quotes / interesting experiences: ", "</td><td>",
        textarea(-name=>'memories',  -rows=>10, -columns=>40),  "</td></tr>",
        
        "</table>",

        "</div>",

        to_page('Submit'), br, br,

        local_end_html();
}

sub print_thanks
{
    my $iccredits = param('iccredits');
    my $ipcredits = param('ipcredits');
    my $excredits = param('excredits');
    my $dob = param('dob');
    my $photo = param('photo');
    my $contactemail = param('contactemail');
    my $currentworkrole = param('currentworkrole');
    my $currentemployer = param('currentemployer');
    my $careerplan = param('careerplan');
    my $memories = param('memories');

    
    print header(), start_html($title), h3($title);
 
    my @error_messages;

    unless ($iccredits =~ /\d+/) {
        push @error_messages, "Invalid IIMB course credits", br;
    }

    unless ($ipcredits =~ /\d+/) {
        push @error_messages, "Invalid IIMB project credits", br;
    }

    unless ($excredits =~ /\d+/) {
        push @error_messages, "Invalid exchange credits", br;
    }

    unless ($dob =~ /\d\d\-\d\d-\d\d\d\d/) {
        push @error_messages, "Invalid date of birth", br;
    }

    unless ($contactemail =~ /\w+\@\w+/) {
        push @error_messages, "Invalid contact e-mail", br;
    }

    if (@error_messages) {

        print "The following errors were found in the data you entered.", br;
        print "Please fix the errors and resubmit.", br;
        print br;

        foreach my $msg (@error_messages) {
            print $msg;
        }

        print br;

    } else {


        print "$iccredits", br;
        print "$ipcredits", br;
        print "$excredits", br;
        print "$excredits", br;
        print "$dob", br;
        print "$photo", br;
        print uploadInfo($photo)->{'Content-Type'}, br;

        {
            no strict;

            while (<$photo>) {
                print;
                print br;
            }
        }

        print "$contactemail", br;
        print "$currentworkrole", br;
        print "$currentemployer", br;
        print "$careerplan", br;
        print "$memories", br;
    }

    print local_end_html();
  }

sub main()
{
    read_config_info("$config_dir/config.txt");
    assign_config_info;

    my $page = param(".state") || "default";

    if ($states{$page}) {
      $states{$page}->();
    } else {
      no_such_page();
    }
}

main;

# end of file
