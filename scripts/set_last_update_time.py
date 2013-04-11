# -*- coding: utf-8 -*-
'''
scripts.set_last_update_time.py
Created on 11.04.2013
@author: tobixx0
'''

from datetime import datetime
import sys
import shelve

shv = shelve.open("eventsync.shelve")
dp = [int(p) for p in sys.argv[1].split("-")]
tp = [int(p) for p in sys.argv[2].split(":")] if len(sys.argv) == 3 else [0, 0, 0]

dt = datetime(year=dp[0], month=dp[1], day=dp[2], hour=tp[0], minute=tp[1], second=tp[2])
shv["last_updated"] = dt
shv.close()
