#!/bin/bash

# install dependency
python3 -m pip install pyinotify --target recursive-gobuster

# remove metadata and cache; we're done with pip
rm -rvf recursive-gobuster/pyinotify-* recursive-gobuster/__pycache__

# package it up into an executable zip
python3 -m zipapp -p "/usr/bin/env python3" recursive-gobuster

chmod 755 recursive-gobuster.pyz