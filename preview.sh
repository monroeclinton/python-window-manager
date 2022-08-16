#!/bin/sh

# Stop running if we hit an error
set -e

# The xinit command takes a first option of a xinitrc script to run
# and a second option of the command to start an X server.

# Run xinit then specify Xephyr command to start a nested X server
# with a display of 1 to use. In X11 this basically means that
# an X server runs on localhost:1 If display 1 is in use, change it
# to another number like 10.
xinit ./xinitrc -- $(command -v Xephyr) :1 -screen 1024x768
