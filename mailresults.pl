#perl -w

# $Id: mailresults.pl,v 1.4 2006/09/05 19:52:56 a14562 Exp $

my %senreasons = 
  (
   "NO:P1" => "Missed phase 1",
   "NO:CRED" => "Completion of credits",
   "NO:P2A" => "Missed phase 2A",
   "NO:LATE" => "Late submission"
  );

use strict;

use POSIX;

use Elec;
use ElecUtils;

my %allocation;

sub load_allocation ($)
{
    my $filename = shift;

    open IN, "<$filename" or die "Can't open $filename: $!";

    while (<IN>) {
        chomp;
        
        my ($rollno, $name, $email, $nasked, $nallowed, 
	    $nallotted, $seniority, $senreason, $ca) = 
          split(/\s*;\s*/);

        my @calist = split(/,/, $ca);

        my @clist;
        my %alloc;

        foreach my $token (@calist) {
            my ($course, $status) = split(/=/, $token);
            push @clist, $course;
            $alloc{$course} = $status;
        }

        $allocation{$rollno}{'name'} = $name;
        $allocation{$rollno}{'email'} = $email;
        $allocation{$rollno}{'nasked'} = $nasked;
        $allocation{$rollno}{'nallowed'} = $nallowed;
        $allocation{$rollno}{'nallotted'} = $nallotted;
        $allocation{$rollno}{'seniority'} = $seniority;
        $allocation{$rollno}{'senreason'} = $senreason;
        $allocation{$rollno}{'clist'} = \@clist;
        $allocation{$rollno}{'alloc'} = \%alloc;
    }

    close IN;
}

sub write_mailbody_files($)
{
    my $outdir = shift;

    mkdir($outdir);

    foreach my $rollno (sort keys %allocation) {

        my $file = "$outdir/$rollno.txt";
        open OUT, ">$file" or die "Can't write $file: $!";
        
        print OUT 
        "\n\nPlease find the results of the course allocation below:\n";
        print OUT
        "(Overall results are available in the attached spread sheet.)\n\n";

        print OUT "Roll number: $rollno\n";
        print OUT "Name: $allocation{$rollno}{'name'}\n";
        print OUT "E-Mail: $allocation{$rollno}{'email'}\n";
        print OUT "Seniority: "
	  . (($allocation{$rollno}{'seniority'} ne $allocation{$rollno}{'senreason'})
	    ? "None ($senreasons{$allocation{$rollno}{'senreason'}})"
	    : "$allocation{$rollno}{'seniority'}")
	    . "\n";
        print OUT "\n\n";
        print OUT "#Courses asked: $allocation{$rollno}{'nasked'}\n";
        print OUT "#Courses max allowed: $allocation{$rollno}{'nallowed'}\n";
        print OUT "#Courses allotted: $allocation{$rollno}{'nallotted'}\n";
        print OUT "\n\n";

        my $count = 1;
        foreach my $course (@{$allocation{$rollno}{'clist'}}) {

            my $status = $allocation{$rollno}{'alloc'}->{$course};

            print OUT "Preference $count: ",
                $allocation{$rollno}{'clist'}->[$count-1], " - ",
                $status;

            if ($status =~ /Allotted/) {
                print OUT " (", $courses{$course}{'slot'}, ")";
            }

            print OUT "\n";

            ++$count;
        }
        
        print OUT<<'EOF';


For any clarifications regarding the allocation, 
please get in touch with the PGSEM office.

We would be grateful if you can provide us feedback
on the the preferences submission, allocation, and 
communication processes at:

http://sankara.net/cgi-bin/feedback.cgi


Legend:
=======

Allotted   - Course is allotted.

Allowed:n  - Course is NOT allotted. Reasons coud be either of:
             1. CGPA <  2.75, doing project course, 3 requested
             2. CGPA <  2.75, not doing project course, 4 requested
             3. CGPA >= 2.75, doing project course, 4 requested

Capped     - Course NOT allotted. Reasons can be either of:
             1. Course capped due to instructor set cap.
                Only M&A capped at 60.
                Instructor set caps were CMS=60, IPRs=60, LCM=60, M&A=60.

             2. Course capped due to class capacity constraints.
                NEF=68

Complete   - Course NOT allotted. 
             Number of courses asked for has been allotted.

Dropped    - Course NOT allotted. 
             Course has been dropped (only for EEE/LCM/MOSIT).

SC:XXX     - Course NOT allotted. 
             There is a schedule conflict with the course XXX
             requested by you at a higher preference and 
             XXX has been allotted. 

-- 
Sankaranarayanan K. V. and Abhay Ghaisas
pgsemelectives@sankara.net

EOF

        close OUT;
    }
}

sub main
{
    load_courses("courses-internal.txt", 1);
    load_allocation("allocation-internal.txt");

    write_mailbody_files("mailbodies");
}

main;

# end of file


