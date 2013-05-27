# -*- coding: utf-8 -*-
'''
scripts.redmine_elsa_sync_runner.py
Created on 10.04.2013
@author: tobixx0
'''
from datetime import datetime
import shelve
import sys
from time import sleep

sys.path.append(".")
print(sys.path)

import eventsync.redmine_elsa_sync as redmine_elsa_sync
from eventsync.redmine.redmineapi import *
from eventsync.redmine.issues import get_event_issues
import eventsync.elsaevent
from eventsync.elsaevent.datamodel import *
from eventsync import runner_settings

import eventsync.logconfig
logg = eventsync.logconfig.configure_logging(runner_settings.LOG_FILENAME, runner_settings.LOG_SMTP_SETTINGS)

shv = shelve.open("eventsync.shelve")

def do_sync():
    last_updated = shv["last_updated"]
    now = datetime.now()  
    logg.debug("last update was %s", last_updated)
    iss_with_new = get_event_issues(True, last_updated, now)
    event_issues = list(filter(lambda i: not i.status.name == "Neu", iss_with_new))
    start_dt = last_updated.replace(hour=0, minute=0, second=0, microsecond=0)
    update_dt = eventsync.redmine_elsa_sync.update_event_database(event_issues, last_update_dt=last_updated, start_dt=start_dt)
    logg.debug("update datetime is %s", update_dt)
    shv["last_updated"] = update_dt
    

if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) == 2 else 0
    
    if interval > 0:
        # run sync every 'interval' seconds
        while 1:
            do_sync()
            logg.info("sleeping for %s seconds", interval)
            sleep(interval)
    else:
        # run it once and exit
        do_sync()