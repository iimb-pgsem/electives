#!/usr/bin/perl -Tw

# $Id: graduation.cgi,v 1.5 2007/03/10 07:58:56 a14562 Exp $

# Copyright (c) 2006-07
# Sankaranarayanan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

BEGIN {
    unshift @INC, '/home/kvsankar/public_html/cgi-bin/';
}

use strict;

use CGI qw(:standard);
use Net::SMTP;
use Net::POP3;
use FindBin;
use DBI;
use POSIX qw(strftime);

# use Image::Magick;

use ConfigDir;
use ElecConfig;
use Elec;

# begin global data
my $url = "http://gator290.hostgator.com/~kvsankar/"; # TODO change later
my $files_dir = "/home/kvsankar/files";
my $photopath_dir = "pgsem/graduation/uploads/images/";
my $passcode = "560076";
my $debugprint = 0;
# my $config_dir = "$FindBin::Bin"; # at least for the present
my $title = "PGSEM Graduation 2007";
my $book_view = 0;
my %states = (
              'default' => \&print_login_form,
              'Login' => \&print_profiles,
              'Submit' => \&print_thanks
             );
# end global data

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

        "Passcode: ", 
        password_field(-name=>'passcode',  -size=>20, -maxlength=>20),

        to_page('Login'), br, br,

        local_end_html();
}

sub print_profiles()
{
    print header(), start_html($title), h3($title);

    if (!defined(param('passcode'))) {

      print "Invalid input: please try again", local_end_html();
      return;
    }

    my $given_passcode = param('passcode');

    if ($given_passcode ne $passcode) {
        print "Invalid passcode: please try again", local_end_html();
        return;
    }

    my $errors = load_students("$config_dir/graduate-candidates.txt");

    my %graduation;

    foreach my $rollno (sort keys %students) {
        my %rec;
        my $rec = \%rec;
        my $status = get_profile_from_db($rollno, \%rec);

        if ($status == 0) {
            if ($rec{'found'}) {

                $graduation{$rollno} = $rec;
            }
        }
     }

     my $total = keys %graduation;

     unless ($book_view) {
         print "<b id=\"top\">List of $total students who have submitted their profiles so far: </b>", br;
         print br;

         foreach my $rollno (sort keys %graduation) {
            print "<a href=\"#$rollno\">", $rollno, "</a>, ", $students{$rollno}->{'name'}, br;
         }
    
         print br;
     }

     print "<b>Profiles: </b>", br;
     print br;

     foreach my $rollno (sort keys %graduation) {

        my $rec = $graduation{$rollno};

        print "<table width=\"1000\" border=\"0\">";

        print "<tr><td width=\"200\" id=\"$rollno\"><i>Roll number:</i></td><td>$rollno", "</td></tr>";
        print "<tr><td><i>Name:</i></td><td>$students{$rollno}->{'name'}", "</td></tr>";
        print "<tr><td><i>Date of Birth:</i></td><td>$rec->{'dob'}", "</td></tr>";
        print "<tr><td><i>Contact E-Mail:</i></td><td>", $rec->{'contactemail'}, "</td></tr>";
        print "<tr><td><i>Mobile Number:</i></td><td>", $rec->{'mobilenumber'},"</td></tr>";
        print "<tr><td><i>Education:</i></td><td>", $rec->{'eduqual'}, "</td></tr>";
        print "<tr><td><i>Experience in years:</i></td><td>", $rec->{'expyears'}, "</td></tr>";
        print "<tr><td><i>Project Topic:</i></td><td>", $rec->{'projecttopic'}, "</td></tr>";
        print "<tr><td><i>Publications:</i></td><td>", $rec->{'publications'}, "</td></tr>";
        print "<tr><td><i>Current Work Role:</i></td><td>", $rec->{'currentworkrole'}, "</td></tr>";
        print "<tr><td><i>Current Employer:</i></td><td>", $rec->{'currentemployer'}, "</td></tr>";
        print "<tr><td><i>Career Plan</i></td><td>", $rec->{'careerplan'}, "</td></tr>";
        print "<tr><td><i>Academic Interests:</i></td><td>", $rec->{'interest'}, "</td></tr>";
        print "<tr><td><i>Hobbies:</i></td><td>", $rec->{'hobbies'}, "</td></tr>";
        print "<tr><td><i>Memories:</i></td><td>", $rec->{'memories'}, "</td></tr>";

        if (!$book_view && $rec->{'photopath'}) {

            # the following s/// hack for change of paths when the site
            # migrated from networksolutions to hostgator

            $rec->{'photopath'} =~ s,pgsem/uploads/graduation,pgsem/graduation/uploads,;

            print "<tr><td>Photo</td><td><img src=\"${url}cgi-bin/images.cgi/$rec->{'photopath'}\" " .
                "width=\"100\"></td></tr>";
        }

        print "</table>";
        $book_view or print "<a href=\"#top\">Go to top</a>";
        print br;
    }

    local_end_html();
}

sub get_profile_from_db($$)
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
    $sth = $dbh->prepare("SELECT dob, phototype, photopath, " .
			 "contactemail, mobilenumber, eduqual, " .
			 "expyears, projecttopic, publications, " .
			 "currentworkrole, currentemployer, " .
			 "careerplan, interest, hobbies, memories " .
    "FROM graduation WHERE rollno = '$rollno';");

    $status = $sth->execute();
    
    unless ($status) {
      print br, "Error: unable to read from database",
        br, local_end_html();
      $dbh->disconnect();
      return -1;
    }
    
    my ($dob, $phototype, $photopath, $contactemail);
    my ($mobilenumber, $eduqual, $expyears, $projecttopic, $publications);
    my ($currentworkrole, $currentemployer, $careerplan, $interest, $hobbies, $memories);

    $sth->bind_columns(\$dob, \$phototype, \$photopath, \$contactemail, 
		       \$mobilenumber, \$eduqual, \$expyears,
		       \$projecttopic, \$publications,
                       \$currentworkrole, \$currentemployer,
		       \$careerplan, \$interest, \$hobbies, \$memories);

    while ($sth->fetch()) {

        $rec->{'found'} = 1;
        $rec->{'dob'} = $dob;
        $rec->{'phototype'} = $phototype;
        $rec->{'photopath'} = $photopath;
        $rec->{'contactemail'} = $contactemail;
        $rec->{'mobilenumber'} = $mobilenumber;
        $rec->{'eduqual'} = $eduqual;
        $rec->{'expyears'} = $expyears;
        $rec->{'projecttopic'} = $projecttopic;
        $rec->{'publications'} = $publications;
        $rec->{'currentworkrole'} = $currentworkrole;
        $rec->{'currentemployer'} = $currentemployer;
        $rec->{'careerplan'} = $careerplan;
        $rec->{'interest'} = $interest;
        $rec->{'hobbies'} = $hobbies;
        $rec->{'memories'} = $memories;
    }
    
    $sth->finish();
    $dbh->disconnect();
    
    return 0; 
}

sub update_profile_in_db($$)
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

    eval {
      # $dbh->begin_work();
      $status = $dbh->do("DELETE FROM graduation WHERE rollno = '$rollno';");
      die "DELETE failed" unless $status;
      $status = $dbh->do("INSERT INTO graduation VALUES (" .
        "'\Q$rollno\E', " .
        "'\Q$rec->{\"dob\"}\E', " .
        "'\Q$rec->{\"phototype\"}\E', " .
        "'\Q$rec->{\"photopath\"}\E', " .
        "'\Q$rec->{\"contactemail\"}\E', " .
        "'\Q$rec->{\"mobilenumber\"}\E', " .
        "'\Q$rec->{\"eduqual\"}\E', " .
        "'\Q$rec->{\"expyears\"}\E', " .
        "'\Q$rec->{\"projecttopic\"}\E', " .
        "'\Q$rec->{\"publications\"}\E', " .
        "'\Q$rec->{\"currentworkrole\"}\E', " .
        "'\Q$rec->{\"currentemployer\"}\E', " .
        "'\Q$rec->{\"careerplan\"}\E', " .
        "'\Q$rec->{\"interest\"}\E', " .
        "'\Q$rec->{\"hobbies\"}\E', " .
        "'\Q$rec->{\"memories\"}\E');");

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

    return 0; 
}

sub save_image_file ($$)
{
    my $rollno = shift;
    my $photo = shift;

    my $ext;
    if ($photo =~ /(\.....?)$/) {
        $ext = $1;
    }

    my $photopath = "$photopath_dir/$rollno$ext";

    open OUT, ">$files_dir/$photopath" or 
        return undef; # TODO better error reporting

    my ($bytesread, $buffer);
    while ($bytesread = read($photo, $buffer, 1024)) {
        print OUT $buffer;
    }

    return $photopath;
}

sub print_thanks
{
    my $rollno = param('rollno');
    my $dob = param('dob');
    my $photo = param('photo');
    my $phototype = ($photo ? uploadInfo{$photo}->{'Content-Type'} : "");
    my $photopath; # will be populated below
    my $contactemail = param('contactemail');
    my $mobilenumber = param('mobilenumber');
    my $eduqual = param('eduqual');
    my $expyears = param('expyears');
    my $projecttopic = param('projecttopic');
    my $publications = param('publications');
    my $currentworkrole = param('currentworkrole');
    my $currentemployer = param('currentemployer');
    my $careerplan = param('careerplan');
    my $interest = param('interest');
    my $hobbies = param('hobbies');
    my $memories = param('memories');

    
    print header(), start_html($title), h3($title);
 
    my @error_messages;

    unless ($dob =~ /\d\d\d\d-\d\d-\d\d/) {
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

        $photopath = save_image_file($rollno, $photo) if ($photo);

        if ($debugprint) {
            print "$dob", br;

            unless ($photopath) {
                print "No valid photo uploaded", br;
            } else {
                print "$phototype", br;
            }

            print "$contactemail", br;
            print "$mobilenumber", br;
            print "$eduqual", br;
            print "$expyears", br;
            print "$projecttopic", br;
            print "$publications", br;
            print "$currentworkrole", br;
            print "$currentemployer", br;
            print "$careerplan", br;
            print "$interest", br;
            print "$hobbies", br;
            print "$memories", br;
        }

        my %rec;

        @rec{'dob', 'phototype', 'photopath', 'contactemail', 
	       'mobilenumber', 'eduqual', 'expyears', 'projecttopic',
		 'publications', 'currentworkrole', 'currentemployer',
		   'careerplan', 'interest', 'hobbies', 'memories'} = 

            ($dob, $phototype, $photopath, $contactemail,
	     $mobilenumber, $eduqual, $expyears, $projecttopic,
	     $publications, $currentworkrole, $currentemployer,
	     $careerplan, $interest, $hobbies, $memories);


        my $status = update_profile_in_db($rollno, \%rec);
        return if ($status == -1);
    }

    print br, "Data updated successfully.", br;

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
