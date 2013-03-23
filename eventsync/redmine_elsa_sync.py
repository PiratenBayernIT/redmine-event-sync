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

logg = logging.getLogger(__name__)
URL_PATTERN = "{}://{}/issues/".format(REDMINE_SCHEMA, REDMINE_HOST)

esession = elsaevent.session
query = esession.query 
event_query = query(Event)

redmine_user = query(User).filter_by(username="redmine").one()
default_category = query(Category).filter_by(name="Schmarnn").one()
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
    for project_name, group_name in c["projects"].items():
        project_id = Project.find_first_by_identifier(project_name).id
        group_id = query(Group.id).filter_by(name=group_name).one().id
        project_mappings[project_id] = group_id
    return project_mappings


project_mappings = load_project_mappings()


def create_or_update_event_from_issue(issue, url, event=None):
    """Conversion from redmine resource object (issue) to ELSAEvent DB object (event).
    
    :param issue: activeResource objects which represents an event.
    :param url: Redmine API URL for the event like https://red.de/issues/123
    :param event: event DB object to update. Create new one if none is given.
    """
    now = datetime.utcnow()
    if not event:
        event = Event()
        event.created = now
    assert isinstance(event, Event)
    event.modified = now
    event.url = url
    event.title = issue.subject
    event.startdate = issue.start_date
    event.enddate = issue.due_date
    event.body = issue.description
    event.group_id = project_mappings[issue.project.id]
    if issue.status.name == "Bestätigt":
        event.status = status_confirmed
    elif issue.status.name == "Abgesagt":
        event.status = status_cancelled
    else:
        raise Exception("wrong issue status {} for issue #{}".format(issue.status.name, issue.id))
    event.user = redmine_user
    for name, value in issue._custom_fields.items():
        if name == "Startzeit":
            event.starttime = value
        elif name == "Ende":
            event.endtime = value
        elif name == "Veranstaltungsort":
            event.location = value
        elif name == "Adresse":
            event.address = value
        elif name == "Kategorien":
            # multi value field is given as a simple list
            for category_name in value:
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


def update_event_database(redmine_issues, last_update_dt, start_dt=None, end_dt=None):
    """Updates ELSAEvent database with some event issues.
    Ignore events with a start datetime outside of ]start_dt, end_dt[.
    
    :param redmine_issues: activeResource objects which represent events.
    :param last_update_dt: datetime for last DB update.
    :param start_dt: start of datetime interval
    :param end_dt: end of datetime interval
    
    TODO: issues with status "abgesagt".
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
        assert isinstance(event, Event)
        url = event.url
        issue = urls_to_issues[url]
        if event.status == status_confirmed:
            if event.modified > last_update_dt:
                logg.warn("oops, event '%s' was updated in ELSAEvent (%s > %s), this should not happen!", 
                          event.title, 
                          datetime.strftime(event.modified, REDMINE_DATETIME_FORMAT),
                          datetime.strftime(last_update_dt, REDMINE_DATETIME_FORMAT))
            if issue.updated_on > last_update_dt:
                logg.info("event '%s' was changed in Redmine issue #%s (%s > %s), update", 
                          event.title, issue.id,
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
        
    # remaining issues in urls_to_issues are new, insert them
    logg.info("%s new events found", len(urls_to_issues))
    for url, issue in urls_to_issues.items():
        try:
            event = create_or_update_event_from_issue(issue, url)
        except Exception as e:
            logg.exception("error occured for issue #%s: %s", issue.id, e)
        else:
            if event is not None:
                logg.info("created new event '%s' from issue #%s", event.title, issue.id)
                esession.add(event)
        
    esession.commit()
    return now
        
        