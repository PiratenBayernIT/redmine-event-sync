# -*- coding: utf-8 -*-
'''
eventsync.redmine.eventtemplate.py
Created on 22.03.2013
@author: tobixx0
'''

from . import redmineapi
from .resourceaddons import custom_fields


@custom_fields("Wiederholungsart", "Intervall", "Veranstaltungsort")
class Issue(redmineapi.Issue):
    pass

