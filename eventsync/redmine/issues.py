# -*- coding: utf-8 -*-
'''
eventsync.redmine.issues.py
Created on 18.03.2013
@author: escaP

Issue handling on the side of Redmine, building upon the basic redmine API.
'''
import logging
import string
from .redmineapi import Issue, Tracker, IssueStatus
from eventsync.redmine.resourceaddons import custom_fields
from dateutil.rrule import rrule, WEEKLY, MONTHLY, DAILY
from eventsync.redmine.localsettings import READABLE_DATE_FORMAT, READABLE_TIME_FORMAT

logg = logging.getLogger(__name__)


# maybe find a better way to cache these API objects
tracker_termin = Tracker.find_first_by_name("Termin")
tracker_termin_ext = Tracker.find_first_by_name("Termin extern")
tracker_template = Tracker.find_first_by_name("Terminvorlage")
    
def _make_time_constraint(start_dt=None, end_dt=None):
    start_timestr = start_dt.strftime("%Y-%m-%d") if start_dt else "1970-01-01"
    end_timestr = end_dt.strftime("%Y-%m-%d") if end_dt else "2037-12-31"
    if start_dt or end_dt:
        redmine_time_constraint = "><{}|{}".format(start_timestr, end_timestr) 
        logg.debug("time constraints given, start %s end %s, encoded %s", start_timestr, end_timestr, redmine_time_constraint)
        return redmine_time_constraint
    else:
        return None


def get_event_issues(fetch_closed=False, start_dt=None, end_dt=None):
    """Fetch event issues from redmine server updated in a given time span
    ]start_dt, end_dt[.
    If no parameter is given, all issues are fetched.
    
    :param fetch_closed: Redmine fetches open issues by default, also get closed ones when True. 
    :param start_dt: datetime which marks the start of the time interval
    :param end_dt: datetime, end of the time interval
    """
    fargs = {}
    time_constraint = _make_time_constraint(start_dt, end_dt)
    if fetch_closed:
        fargs["status_id"]= "*"
    if time_constraint:
        fargs["updated_on"] = time_constraint
    termine = Issue.find(tracker_id=tracker_termin.id, **fargs)
    termine_ext = Issue.find(tracker_id=tracker_termin_ext.id, **fargs)
    return termine + termine_ext
    

def get_cancelled_issues(start_dt=None, end_dt=None):
    """Fetch cancelled issues from redmine server updated in a given time span
    ]start_dt, end_dt[.
    If no parameter is given, all issues are fetched.
    
    :param start_dt: datetime which marks the start of the time interval
    :param end_dt: datetime, end of the time interval
    """
    fargs = {}
    time_constraint = _make_time_constraint(start_dt, end_dt)
    if time_constraint:
        fargs["updated_on"] = time_constraint
    cancelled_status_id = next(IssueStatus.filter(lambda s: s.name == "Abgesagt")).id
    c_termine = Issue.find(tracker_id=tracker_termin.id, status_id=cancelled_status_id, **fargs)
    c_termine_ext = Issue.find(tracker_id=tracker_termin_ext.id, status_id=cancelled_status_id, **fargs)
    return c_termine + c_termine_ext


def get_event_templates(start_dt=None, end_dt=None):
    """Fetch event template issues from redmine server created in a given time span
    ]start_dt, end_dt[.
    If no parameter is given, all issues are fetched.
    
    :param start_dt: datetime which marks the start of the time interval
    :param end_dt: datetime, end of the time interval
    """
    fargs = {}
    time_constraint = _make_time_constraint(start_dt, end_dt)
    if time_constraint:
        fargs["created_on"] = time_constraint
    event_templates = Issue.find(tracker_id=tracker_template.id,  **fargs)
    return event_templates


def create_rrule_from_issue(issue_template):
    """Create a rrule from an event template issue."""
    start_dt = issue_template.start_date
    end_dt = issue_template.due_date
    
    opts = { 
        "Jede Woche": dict(freq=WEEKLY, byweekday=start_dt.weekday()),
        "Tag im Monat": dict(freq=MONTHLY, bymonthday=start_dt.day),
        "Abstand in Tagen": dict(freq=DAILY, interval=issue_template.intervall),
        "Abstand in Wochen": dict(freq=WEEKLY, interval=issue_template.intervall),
        "1. Wochentag im Monat": dict(freq=MONTHLY, byweekday=start_dt.weekday(), bysetpos=1),
        "2. Wochentag im Monat": dict(freq=MONTHLY, byweekday=start_dt.weekday(), bysetpos=2),
        "3. Wochentag im Monat": dict(freq=MONTHLY, byweekday=start_dt.weekday(), bysetpos=3),
        "4. Wochentag im Monat": dict(freq=MONTHLY, byweekday=start_dt.weekday(), bysetpos=4),
    }
    chosen_opts = opts[issue_template.wiederholungsart]
    return rrule(dtstart=start_dt, until=end_dt, **chosen_opts)
    
    
def new_issue_from_template(issue_template):
    custom_fields = list(filter(lambda cf: cf.name.lower() not in ["intervall", "wiederholungsart", "terminart"], issue_template.custom_fields)) 
    logg.info("custom fields: %s, %s", custom_fields ,[(cf.name, cf.value) for cf in custom_fields])
    issue = Issue(dict(custom_fields=custom_fields))
    # XXX: works better when we assign it again, don't ask me why...
    issue.custom_fields = custom_fields
    issue.project_id = issue_template.project.id
    if issue_template.terminart == "Termin":
        issue.tracker_id = tracker_termin.id
    elif issue_template.terminart == "Termin":
        issue.tracker_id = tracker_termin_ext.id
    else:
        raise Exception("Whoops, not possible ;)")
    logg.info("issue created: %s", issue)
    logg.info("dict: %s", issue.__dict__)
    return issue


def create_issues_from_template(issue_template):
    rrule = create_rrule_from_issue(issue_template)
    subject_tmpl = string.Template(issue_template.subject)
    description_tmpl = string.Template(issue_template.description)
    created_issues = []
    for dt in rrule:
        issue = new_issue_from_template(issue_template)
        readable_date_str = dt.strftime(READABLE_DATE_FORMAT) 
        custom_fields = {k: cf.value for k, cf in issue._custom_fields.items()}
        logg.info("custom_fields %s", custom_fields)
        issue.subject = subject_tmpl.substitute(datum=readable_date_str, **custom_fields)
        issue.description = description_tmpl.substitute(datum=readable_date_str, **custom_fields)
        issue.start_date = dt
        issue.due_date = dt
        logg.info("creating issue from template %s", issue.attributes)
        created_issues.append(issue)
        
    return created_issues
