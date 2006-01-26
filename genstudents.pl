#!/usr/bin/perl -w 

use strict;

my @rollnos = (2002101 .. 2002105, 2003101 .. 2003105, 2004101 .. 2004110);

print "\n";

srand(time ^ $$);

foreach my $rollno (@rollnos) {
  print "$rollno; Roll Number ${rollno}; kvsankar\+$rollno\@gmail.com; ";
  printf("%4.2f; ;\n", rand(4.0));
}

print "\n";

# end of file

