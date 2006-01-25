#!perl -w

use strict;

use CGI qw(:standard);
# use CGI::Carp qw(fatalsToBrowser);
use Net::SMTP;
use Net::POP3;

my $pop_required = 0;
my $login = 'sankara';
my $password = 'brealy16myers';

my %states = (
    'default' => \&form_page,
    'Send Mail' => \&results_page
);

sub to_page ($)
{
    return submit(-NAME => ".state", -VALUE => shift) 
}

sub no_such_page()
{
    die "No such page exists";
}

sub form_page()
{
    print 
        header(), 
        start_html("E-Mail Application"),
        start_form(),
        "<table><tr><td>From:</td>", 
        "<td>", textfield(-name=>'from', -size=>50, -maxlength=>80), "</td></tr>",
        "<tr><td>To:</td>", 
        "<td>", textfield(-name=>'to', -size=>50, -maxlength=>80), "</td></tr>", br,
        "<tr><td>Subject:</td>", 
        "<td>", textfield(-name=>'subject', -size=>50, -maxlength=>80), "</td></tr></table>", br,
        "Please type your message below:", br,
        textarea(-name=>'body', -rows=>10, -columns=>50), br,
        to_page('Send Mail'), 
        end_html();
}

sub results_page()
{
    my ($from, $to, $subject, $body);

    print header(), start_html("E-Mail Application");

    if (!defined(param('from')) ||
        !defined(param('to')) ||
        !defined(param('subject')) ||
        !defined(param('body'))) {

        print "Invalid input: please try again", end_html();
        return;
    }

    $from = param('from');
    $to = param('to');
    $subject = param('subject');
    $body = param('body');

    my $pop = Net::POP3->new('mail.sankara.net', Timeout => 60, Debug => 1);

    my $errors = 0;

    if (!$pop_required || $pop->login($login, $password)) {
       
        my $smtp = Net::SMTP->new(
            "mail.sankara.net", 
            Debug => 1);

        my $retval;

        $retval = $smtp->mail($from);
        $errors += ($retval != 1);
        $retval = $smtp->to($to);
        $errors += ($retval != 1);

        $retval = $smtp->data();
        $errors += ($retval != 1);

        $smtp->datasend("To: $to\n");
        $smtp->datasend("From: $from\n");
        $smtp->datasend("Subject: $subject\n");
        $smtp->datasend("\n");
        $smtp->datasend("$body\n\n");

        $retval = $smtp->dataend();
        $errors += ($retval != 1);

        $smtp->quit();

    } else {

       print "Error sending mail: unable to authenticate using POP3";
       print end_html;
       return;
    }
   
    # success

    if ($errors) {
        print "Error sending mail using SMTP";
        print end_html;
        return;
    }
    
    print "Mail sent successfully.";
    print end_html;
}

my $page = param(".state") || "default";

if ($states{$page}) {
    $states{$page}->();
} else {
    no_such_page();
}

# end of file
