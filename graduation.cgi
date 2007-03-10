#!/usr/bin/perl -w

# $Id: graduation.cgi,v 1.5 2007/03/10 07:58:56 a14562 Exp $

# Copyright (c) 2006-07
# Sankaranarayanan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

use strict;

use CGI qw(:standard);
use Net::SMTP;
use Net::POP3;
use FindBin;
use DBI;
use POSIX qw(strftime);

# use Image::Magick;

use ElecConfig;
use Elec;

$CGI::POST_MAX=1024 * 100;  # max 100K postsuse CGI::Carp qw(fatalsToBrowser);

# begin global data
my $debugprint = 0;
my $config_dir = "$FindBin::Bin"; # at least for the present
my $title = "PGSEM Graduation 2007";
my $admin_rights = 0;
my %states = (
              'default' => \&print_login_form,
              'Login' => \&print_profile_form,
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
    
    my %rec;
    my $status = get_profile_from_db($rollno, \%rec);

    if ($status == 0) {
        if ($rec{'photopath'}) {
            print "<img src=\"http://sankara.net/$rec{'photopath'}\">", br;
            # TODO find a better way to do this
        }
    }

    print "Roll number: $rollno", br;
    print "Name: $name", br;
    print br;

    print
        start_multipart_form(), hidden('rollno'), hidden('email'),
       
        "Information being collected for the graduation book:",

        "<div style=\"background-color:#ffd; border:black solid 2px;",
        "margin:1em;padding:5px\">",

        "<table>",
        
        "<tr><td>", "Date of birth (yyyy-mm-dd) (*): ", "</td><td>",
        textfield(-name=>'dob', -size=>20, -maxlength=>10, -default=>$rec{'dob'}), "</td></tr>",

        "<tr><td>", "Photo (upload file): ", "</td><td>",
        filefield(-name=>'photo', -size=>40, -maxlength=>10_000), "</td></tr>",

        "<tr><td>", "Contact E-Mail (*): ", "</td><td>",
        textfield(-name=>'contactemail',  -size=>40, -maxlength=>50, -default=>$rec{'contactemail'}), "</td></tr>",

        "<tr><td>", "Mobile number: ", "</td><td>",
        textfield(-name=>'mobilenumber',  -size=>40, -maxlength=>50, -default=>$rec{'mobilenumber'}), "</td></tr>",

        "<tr><td>", "Educational qualifications (prior to PGSEM, separate by comma if more than one): ", "</td><td>",
        textfield(-name=>'eduqual',  -size=>40, -maxlength=>50, -default=>$rec{'eduqual'}), "</td></tr>",

        "<tr><td>", "Years of experience (as of now): ", "</td><td>",
        textfield(-name=>'expyears',  -size=>5, -maxlength=>5, -default=>$rec{'expyears'}), "</td></tr>",

        "<tr><td>", "PGSEM project topic (separate by comma if more than one): ", "</td><td>",
        textfield(-name=>'projecttopic',  -size=>100, -maxlength=>400, -default=>$rec{'projecttopic'}), "</td></tr>",

        "<tr><td>", "Publications, if any (separate by comma if more than one): ", "</td><td>",
        textfield(-name=>'publications',  -size=>100, -maxlength=>400, -default=>$rec{'publications'}), "</td></tr>",

        "<tr><td>", "Current work role: ", "</td><td>",
        textfield(-name=>'currentworkrole',  -size=>40, -maxlength=>50, -default=>$rec{'currentworkrole'}), "</td></tr>",

        "<tr><td>", "Current employer: ", "</td><td>",
        textfield(-name=>'currentemployer',  -size=>40, -maxlength=>50, -default=>$rec{'currentemployer'}), "</td></tr>",

        "<tr><td>", "Future career plans: ", "</td><td>",
        textfield(-name=>'careerplan',  -size=>40, -maxlength=>50, -default=>$rec{'careerplan'}), "</td></tr>",

        "<tr><td>", "Areas of academic interest: ", "</td><td>",
        textfield(-name=>'interest',  -size=>40, -maxlength=>100, -default=>$rec{'interest'}), "</td></tr>",

        "<tr><td>", "Hobbies: ", "</td><td>",
        textfield(-name=>'hobbies',  -size=>40, -maxlength=>100, -default=>$rec{'hobbies'}), "</td></tr>",

        "<tr><td>", "PGSEM memories / quotes / interesting experiences: ", "</td><td>",
        textarea(-name=>'memories',  -rows=>10, -columns=>40, -default=>$rec{'memories'}),  "</td></tr>",
        
        "</table>",

        "</div>",

        to_page('Submit'), br, br,

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

    my $photopath = "pgsem/uploads/graduation/images/$rollno$ext";

    open OUT, ">../htdocs/$photopath" or
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
