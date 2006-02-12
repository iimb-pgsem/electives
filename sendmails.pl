#!perl -w

# $Id: sendmails.pl,v 1.1 2006/02/12 11:39:15 a14562 Exp $

use strict;

use Net::SMTP;
use Net::POP3;
use MIME::Lite;

my $pop_required = 1;
my $login = 'sankara';
my $password = 'brealy16myers';

my $debug = 0;

sub send_mail ($$$$$)
{
    my ($from, $to, $subject, $body, $filename) = @_;

    my $pop = Net::POP3->new('mail.sankara.net', Timeout=>60, Debug=>$debug);

    my $errors = 0;

    if (!$pop_required || $pop->login($login, $password)) {
       
        my $msg = MIME::Lite->new(
            From => $from,
            To => $to,
            Subject => $subject,
            Type => 'multipart/mixed');

        
        $msg->attach(
            Type => 'TEXT',
            Data => $body);

        $msg->attach(
            Type => 'application/vnd.ms-excel',
            Filename => $filename,
            Path => $filename,
            Disposition => 'attachment');

        MIME::Lite->send('smtp', "mail.sankara.net", 
                         Timeout=>60, Debug=>$debug) or
          die "Can't send mail to $to: $!";
        $msg->send() or die "Can't send mail to $to: $!";

    } else {

       print STDERR "Error sending mail: unable to authenticate using POP3";
       return;
    }
   
    # success

    if ($errors) {
        print STDERR "Error sending mail using SMTP";
        return;
    }
}

sub main
{
    my @files = @ARGV;

    foreach my $file (@files) {

        open IN, "<$file" or die "Can't open $file: $!";
        my @lines = <IN>;
        close IN;

        my @emails = grep(/^E-Mail: /, @lines);
        my $email = $1 if ($emails[0] =~ /E-Mail: (.+)/);
   
        print "$file: Sending mail to $email: ";
        
        eval {
            send_mail("PGSEM Electives <pgsemelectives\@sankara.net>",
                      $email,
                      "Course allotment results",
                      join("", @lines),
                      "allocation.xls");
        }; 

        if ($@) {
            print "FAIL: $@\n";
        } else {
            print "OK\n";
        }

    }
}

main;

# end of file
