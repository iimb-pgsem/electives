#perl -w

use strict;

my %choices;

while (<>) {
  chomp;
  if (/preferences: rollno=(\d+), ncourses=(\d), courselist=(.+)/) {
    $choices{$1}{'ncourses'} = $2;
    $choices{$1}{'courses'} = $3;
  }
}

foreach my $rollno (sort keys %choices) {
  print "$rollno; $choices{$rollno}{'ncourses'}; ";
  print join(',', split(/:/, $choices{$rollno}{'courses'}));
  print "\n";
}


