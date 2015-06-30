#!/bin/bash

set -e

# assert that required programs are installed.
if [ ! `command -v virtualenv` ]; then
    echo -e "'virtualenv' is not installed on the machine.\nPlease install the program to continue."
    exit -1
fi

# Global scope variables.
TOPDIR=`git rev-parse --show-toplevel`
VIRTUAL_DIR=venv

# initialize the virtual environment
virtualenv $TOPDIR/$VIRTUAL_DIR
source $TOPDIR/$VIRTUAL_DIR/bin/activate

# install prerequisite packages
INSTALLED=`$TOPDIR/$VIRTUAL_DIR/bin/pip freeze | sort | md5sum`
REQUIRED=`cat $TOPDIR/scripts/pip-requirements.txt | sort | md5sum`

if [ "$INSTALLED" != "$REQUIRED" ]; then
    pip install -r $TOPDIR/scripts/pip-requirements.txt
fi

