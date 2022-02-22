# -*- coding: utf-8 -*-

#!/usr/bin/env python
# -*- coding: utf-8 -*-

#PUBLISHTO /data/film/apps/reelfx/python/
#SETMODE 777

"""

NAME: submit_seq_report.py
AUTHOR: Ed Whetstone

Report various problematic nodes in a comp

"""

import nuke
import nkReport as report

def main():
  report.seqReport()