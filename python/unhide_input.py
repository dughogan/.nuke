#!/usr/bin/env python
# -*- coding: utf-8 -*-

#PUBLISHTO /data/film/apps/reelfx/python/
#SETMODE 777

"""
NAME: unhide_input
AUTHOR: Doug Hogan

"""

import sys
import nuke


def main():
  
    # If nodes are selected then...
    not n['hide_input'].value()