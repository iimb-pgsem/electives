# Copyright (c) 2006-07
# Sankaranaryananan K V <kvsankar@gmail.com>
# Abhay Ghaisas <abhay.ghaisas@gmail.com>
# All rights reserved.

# ConfigDir.pm
# This module holds just one variable containing
# the location of the configuration directory.

package ConfigDir;

use strict;
use vars qw($VERSION @ISA @EXPORT @EXPORT_OK);

require Exporter;

@ISA = qw(Exporter AutoLoader);
# Items to export into callers namespace by default. Note: do not export
# names by default without a very good reason. Use EXPORT_OK instead.
# Do not simply export all your public functions/methods/constants.

@EXPORT = qw(
    $config_dir
);

my $VERSION = '0.01';

our $config_dir = "/home/kvsankar/files/pgsem/electives/config";

1;

# end of file



