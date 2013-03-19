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
import eventsync.redmine.redmineapi
import eventsync.redmine.resourceaddons
import eventsync.elsaevent
from eventsync.elsaevent.datamodel import *

    
s = eventsync.elsaevent.session
q = s.query

midnight_today = datetime.now() - relativedelta(hour=0, minute=0)
#i = Issue.find(495)
#print(i.to_dict())
iss = redmine_elsa_sync.get_issues(start_dt = midnight_today)