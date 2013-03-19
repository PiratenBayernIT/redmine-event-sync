# -*- coding: utf-8 -*-
'''
eventsync.redmine.issues.py
Created on 18.03.2013
@author: escaP

Issue handling on the side of Redmine.
'''
import logging
from .redmineapi import Issue, Tracker

logg = logging.getLogger(__name__)


def get_event_issues(start_dt=None, end_dt=None):
    """Fetch event issues from redmine server created in a given time span
    ]start_dt, end_dt[.
    If no parameter is given, all issues are fetched.
    
    :param start_dt: datetime which marks the start of the time interval
    :param end_dt: datetime, end of the time interval
    """
    fargs = {}
    start_timestr = start_dt.strftime("%Y-%m-%d") if start_dt else "1970-01-01"
    end_timestr = end_dt.strftime("%Y-%m-%d") if end_dt else "2037-12-31"
    if start_dt or end_dt:
        fargs["created_on"] = "><{}|{}".format(start_timestr, end_timestr) 
        logg.debug("time constraints given, start %s end %s, encoded %s", start_timestr, end_timestr, fargs["created_on"])
    tracker_termin_id = Tracker.find_first_by_name("Termin").id
    tracker_termin_ext_id = Tracker.find_first_by_name("Termin extern").id
    termine = Issue.find(tracker_id=tracker_termin_id, **fargs)
    termine_ext = Issue.find(tracker_id=tracker_termin_ext_id, **fargs)
    return termine + termine_ext
    
    
