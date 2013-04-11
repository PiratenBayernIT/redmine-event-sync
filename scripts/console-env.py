# -*- coding: utf-8 -*-
'''
.py
Created on 15.03.2013
@author: escaP
'''
from __future__ import division, absolute_import, print_function

from datetime import datetime
import logging
from imp import reload
import importlib

from dateutil.relativedelta import relativedelta
import eventsync.redmine_elsa_sync as redmine_elsa_sync
from eventsync.redmine.redmineapi import *
from eventsync.redmine.issues import get_event_issues
import eventsync.redmine.resourceaddons
import eventsync.elsaevent
from eventsync.elsaevent.datamodel import *

    
s = eventsync.elsaevent.session
q = s.query

midnight_today = datetime.now() - relativedelta(hour=0, minute=0)
midnight_yesterday = datetime.now() - relativedelta(days=1, hour=0, minute=0)
midnight_tomorrow = datetime.now() - relativedelta(days=-1, hour=0, minute=0)
iss_with_new = get_event_issues(False, midnight_yesterday, midnight_tomorrow)
iss = list(filter(lambda i: not i.status.name == "Neu", iss_with_new))

# i = Issue.find(532)
# value = i.wiederholungsart
# print(value)
# ni = eventsync.redmine.issues.create_issues_from_template(i)[0]
# print(ni)
#ni.save()
