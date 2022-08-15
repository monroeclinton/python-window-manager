#!/bin/sh

# Stop running if we hit an error
set -e

# Run xinit then specify Xephyr server with a display of 1 to use.
# In X11 this basically means that an X server runs on localhost:1.0
# If display 1 is in use, change it to another number like 10
xinit ./xinitrc -- $(command -v Xephyr) :1 -screen 1024x768
