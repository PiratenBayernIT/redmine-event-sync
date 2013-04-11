# -*- coding: utf-8 -*-
'''
redmine_elsa_sync.py
Created on 15.03.2013
@author: escaP

Fetches event tickets from redmine and writes them to an ELSAEvent database.
'''
from configparser import ConfigParser
from dateutil.rrule import rrule 
from datetime import datetime
import logging
from sqlalchemy.sql import and_

from .redmine.redmineapi import Project
from .elsaevent.datamodel import Event, User, Group, Category, Status
from . import elsaevent
from .redmine.localsettings import REDMINE_HOST, REDMINE_SCHEMA, REDMINE_DATETIME_FORMAT
from .elsaevent.localsettings import ELSA_REDMINE_USERNAME, ELSA_DEFAULT_CATEGORY

logg = logging.getLogger(__name__)
URL_PATTERN = "{}://{}/issues/".format(REDMINE_SCHEMA, REDMINE_HOST)

esession = elsaevent.session
query = esession.query 
event_query = query(Event)

redmine_user = query(User).filter_by(username=ELSA_REDMINE_USERNAME).one()
default_category = query(Category).filter_by(name=ELSA_DEFAULT_CATEGORY).one()
status_new = query(Status).filter_by(name="Neu").one()
status_confirmed = query(Status).filter_by(name="Bestätigt").one()
status_cancelled = query(Status).filter_by(name="Abgesagt").one()


def load_project_mappings():
    """Map a project id (Redmine) to a group id (ELSAEvent).
    Every mapping must be defined.
    Fails when groups are not found.
    """
    c = ConfigParser()
    c.read_file(open("eventsync/mappings"))
    project_mappings = {}
    for project_name, group_name in c.items("projects"):
        project = Project.find_first_by_identifier(project_name)
        if project is None:
            logg.warn("project %s doesn't exist or is not accessible!", project_name)
        else:
            group_id = query(Group.id).filter_by(name=group_name).one().id
            project_mappings[project.id] = group_id
    return project_mappings


project_mappings = load_project_mappings()


def create_or_update_event_from_issue(issue, url, event=None):
    """Conversion from redmine resource object (issue) to ELSAEvent DB object (event).
    
    :param issue: activeResource objects which represents an event.
    :param url: Redmine API URL for the event like https://red.de/issues/123
    :param event: event DB object to update. Create new one if none is given.
    :returns: Updated or created event object. None if project for issue is not mapped.
    """
    now = datetime.utcnow()
    if not event:
        event = Event()
        event.created = now
    assert isinstance(event, Event)
    event.group_id = project_mappings.get(issue.project.id)
    if event.group_id is None:
        logg.warn("don't create event for unmapped project %s (issue #%s)", issue.project.id, issue.id)
        return None
    event.modified = now
    event.url = url
    event.title = issue.subject
    event.startdate = issue.start_date
    event.enddate = issue.due_date
    event.body = issue.description
    if issue.status.name == "Neu":
        event.status = status_new
    elif issue.status.name == "Bestätigt":
        event.status = status_confirmed
    elif issue.status.name == "Abgesagt":
        event.status = status_cancelled
    else:
        raise Exception("wrong issue status {} for issue #{}".format(issue.status.name, issue.id))
    event.user = redmine_user
    event.starttime = issue.startzeit
    event.endtime = issue.ende
    event.location = issue.veranstaltungsort
    event.address = issue.adresse
    # multi value field is given as a simple list
    for category_name in issue.kategorien:
        category = query(Category).filter_by(name=category_name).first()
        if category is not None:
            event.categories.append(category)
            
    event.remarks = "Hinweis: Event automatisch generiert von redmine_elsa_sync. Bitte nicht verändern, sonst gibt's Ärger!"
    event.timezone = "Europe/Berlin"
    event.alias = ""
    # XXX: remove after testing!
    # no category given by category field or custom field, we have to assign some default category
    if not event.categories:
        event.categories.append(default_category)
    if not event.location:
        event.location = "unbekannt"
    return event


def _update_existing_event(last_update_dt, urls_to_issues, event):
    assert isinstance(event, Event)
    url = event.url
    issue = urls_to_issues.get(url)
    if issue is None:
        logg.warn("issue for event %s not found!", event.title)
        return
    
    if event.status == status_confirmed:
        if event.modified > last_update_dt:
            logg.warn("oops, event '%s' was updated in ELSAEvent (%s > %s), this should not happen!", event.title, 
                      datetime.strftime(event.modified, REDMINE_DATETIME_FORMAT), 
                      datetime.strftime(last_update_dt, REDMINE_DATETIME_FORMAT))
        if issue.updated_on > last_update_dt:
            logg.info("event '%s' was changed in Redmine issue #%s (%s > %s), update", event.title, issue.id, 
                      datetime.strftime(issue.updated_on, REDMINE_DATETIME_FORMAT), 
                      datetime.strftime(last_update_dt, REDMINE_DATETIME_FORMAT))
            if issue.status.name == "Abgesagt":
                logg.info("last event was cancelled")
            try:
                event = create_or_update_event_from_issue(issue, url, event)
            except Exception as e:
                logg.exception("error occured for issue #%s: %s", issue.id, e)
        else:
            logg.debug("unchanged confirmed event #%s", issue.id)
    else:
        logg.debug("skipping already cancelled event #%s", issue.id)
    del urls_to_issues[url]


def update_event_database(redmine_issues, last_update_dt, start_dt=None, end_dt=None):
    """Updates ELSAEvent database with some event issues.
    Ignore events with a start datetime outside of ]start_dt, end_dt[.
    
    :param redmine_issues: activeResource objects which represent events.
    :param last_update_dt: datetime for last DB update.
    :param start_dt: start of datetime interval
    :param end_dt: end of datetime interval
    """
    
    # map REST url for issue to issue object
    urls_to_issues = {URL_PATTERN + str(issue.id) : issue for issue in redmine_issues}
#    logg.debug("created urls %s", urls_to_issues.keys())
    filter_expr = Event.url.in_(list(urls_to_issues.keys()))
    if start_dt and end_dt:
        filter_expr = and_(filter_expr, Event.startdate.between(start_dt, end_dt))
    elif not start_dt and end_dt:
        filter_expr = and_(filter_expr, Event.startdate < end_dt)
    elif start_dt and not end_dt:
        filter_expr = and_(filter_expr, Event.startdate > start_dt)
    events = event_query.filter(Event.status_id.in_([status_confirmed.id, status_cancelled.id])). \
                filter_by(user=redmine_user).filter(filter_expr).all()
    logg.info("%s matching events in ELSAEvent DB", len(events))
    now = datetime.utcnow()
    for event in events:
        _update_existing_event(last_update_dt, urls_to_issues, event)
        
    # remaining issues in urls_to_issues are new, insert them
    logg.info("%s new events found", len(urls_to_issues))
    for url, issue in urls_to_issues.items():
        try:
            event = create_or_update_event_from_issue(issue, url)
        except Exception as e:
            logg.exception("error occured for issue #%s: %s", issue.id, e)
        else:
            if event is None:
                logg.warn("no event was created for %s from issue #%s", event.title, issue.id)
            else:
                logg.info("created new event '%s' from issue #%s", event.title, issue.id)
                esession.add(event)
        
    esession.commit()
    return now
        
        