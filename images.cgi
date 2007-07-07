#!/usr/local/bin/perl -Tw

# Copyright (c) 2007
# Sankaranarayanan K V <kvsankar@gmail.com>
# All rights reserved.

use strict;

use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use FindBin;

# begin/config
my $prefix = "/home/kvsankar/files";
# end/config

my $info = path_info();

unless ($info =~ /\.(jpg|bmp|gif|tiff)$/i) {
    print header(-status => '404 Not Found');
    exit 0;
}

my $file = "${prefix}${info}";

unless (-f $file) {
    print header(-status => '404 Not Found');
    exit 0;
}

my $suffix;

if ($info =~ /\.(jpg|bmp|gif|tiff)$/i) {
    $suffix = $1;
}

print header("image/$suffix");

open IN, "<$file" or die "Can't find file: $file: $!";
my @contents = <IN>; # TODO find a better way to read
close IN;

print @contents;

# end of file
