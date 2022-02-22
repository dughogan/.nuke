#!/usr/bin/env python
# -*- coding: utf-8 -*-

#PUBLISHTO /data/film/apps/reelfx/python/
#SETMODE 777

"""
NAME: countChannels.py
AUTHOR: Doug Hogan
DATE: November 2013

Usage:
Gives you a channel count print out of your current 

"""

import os
import re
import nuke
import nukescripts

def countChannels():
  totalChannels = nuke.channels()
  channelCount = len(totalChannels)
  channelDifference = 1024-len(totalChannels)
  
  nodes = nuke.allNodes()
  allCh = []
  for n in nodes:
	allCh.extend(n.channels())
  allCh = (list(set(allCh)))
  rootCh = nuke.root().channels()
  exCh = [ch for ch in rootCh if ch not in allCh]
  exChannelCount = len(exCh)
  
  if channelCount<1024:
    nuke.message('Your script has %s channels.\n%s channels are unused' % (channelCount, exChannelCount))
  
  elif channelCount>1024:
    nuke.message('Your script is %s over the channel limit!\n%s channels are unused' % (channelDifference, exChannelCount))