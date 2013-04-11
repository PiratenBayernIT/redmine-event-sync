# -*- coding: utf-8 -*-
'''
scripts.redmine_elsa_sync_runner.py
Created on 10.04.2013
@author: tobixx0
'''
from datetime import datetime
import logging
import shelve

import eventsync.redmine_elsa_sync as redmine_elsa_sync
from eventsync.redmine.redmineapi import *
from eventsync.redmine.issues import get_event_issues
import eventsync.elsaevent
from eventsync.elsaevent.datamodel import *

logging.basicConfig(level=logging.DEBUG)

shv = shelve.open("eventsync.shelve")
last_updated = shv["last_updated"]
now = datetime.now()
    
logg.debug("last update was %s", last_updated)
iss_with_new = get_event_issues(False, last_updated, now)
event_issues = list(filter(lambda i: not i.status.name == "Neu", iss_with_new))
start_dt = last_updated.replace(hour=0, minute=0, second=0, microsecond=0)
update_dt = eventsync.redmine_elsa_sync.update_event_database(event_issues, last_update_dt=last_updated, start_dt=start_dt)
logg.debug("update datetime is %s", update_dt)
shv["last_updated"] = update_dt