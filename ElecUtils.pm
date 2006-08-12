
# $Id: ElecUtils.pm,v 1.1 2006/08/12 20:17:05 a14562 Exp $

# Copyright (c) 2006
# Sankaranaryananan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

# ElecUtils.pm
# This module contains common utilities used by
# all electives allocation modules and scripts.

package ElecUtils;

use strict;
use vars qw($VERSION @ISA @EXPORT @EXPORT_OK);

require Exporter;

@ISA = qw(Exporter AutoLoader);
# Items to export into callers namespace by default. Note: do not export
# names by default without a very good reason. Use EXPORT_OK instead.
# Do not simply export all your public functions/methods/constants.

@EXPORT = qw(
    err_print
    skip_line
);

my $VERSION = '0.01';

use strict;

sub err_print($)
{
    my $msg = shift;
    print $msg, "\n";
}

sub skip_line($)
{
    my $line = shift;
    return 1 if ($line =~ /^\s*\#/); # comment lines
    return 1 if ($line =~ /^\s*$/); # blank lines
    return 0;
}

1;

# end of file
