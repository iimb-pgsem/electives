#perl -w

use strict;

use POSIX;

my %allocation;

# === begin library

my %courses;
my $default_cap = 65;
my $default_status = 'R'; # running

sub err_print($)
{
    my $msg = shift;
    print STDERR $msg, "\n";
}

sub skip_line($)
{
    my $line = shift;
    return 1 if ($line =~ /^\s*\#/); # comment lines
    return 1 if ($line =~ /^\s*$/); # blank lines
    return 0;
}

sub load_courses($)
{
    my $file = shift;
    open IN, "<$file" or die "Can't open file $file: $!";
    while (<IN>) {
        chomp;
        next if skip_line($_);
        my ($code, $name, $instructor, $cap, $slot, $status) = 
            split(/\s*\;\s*/, $_) unless skip_line($_); 

        $cap = undef if (defined($cap) && ($cap eq ''));
        $slot = undef if (defined($slot) && ($slot eq ''));
        $status = undef if (defined($status) && ($status eq ''));
        # status can be 'A' (active) or 'D' dropped

        if (!defined($code) || ($code eq "")) {
            err_print("error:$file:$.: no course code");
            next;
        }

        if (defined($courses{$code})) {
            err_print("error:$file:$.: course '$code' already defined");
            next;
        }

        if (defined($cap) && ($cap < 1)) {
            err_print("error:$file:$.: invalid cap '$cap'");
            next;
        }

        if (defined($status) && !($status =~ /[AD]/)) {
            err_print("error:$file:$.: invalid status '$status'");
            next;
        }

        $name ||= "";
        $instructor ||= "";
        $cap ||= $default_cap;
        $status ||= $default_status;

        $courses{$code}{"name"} = $name;
        $courses{$code}{"instructor"} = $instructor;
        $courses{$code}{"cap"} = $cap;
        $courses{$code}{"slot"} = $slot;
        $courses{$code}{"status"} = $status;

    }
    close IN;
}

# === end library

sub load_allocation ($)
{
    my $filename = shift;

    open IN, "<$filename" or die "Can't open $filename: $!";

    while (<IN>) {
        chomp;
        
        my ($rollno, $name, $email, $nasked, $nallotted, $ca) = 
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
        $allocation{$rollno}{'nallotted'} = $nallotted;
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
        "\n\nPlease find the results of the course allocation below:\n\n";

        print OUT "Roll number: $rollno\n";
        print OUT "Name: $allocation{$rollno}{'name'}\n";
        print OUT "E-Mail: $allocation{$rollno}{'email'}\n";
        print OUT "\n\n";
        print OUT "#Courses asked: $allocation{$rollno}{'nasked'}\n";
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
    load_courses("courses.txt");
    load_allocation("allocation-internal.txt");

    write_mailbody_files("mailbodies");
}

main;

# end of file


