# -*- coding: utf-8 -*-
'''
.py
Created on 15.03.2013
@author: escaP
'''
from datetime import datetime
import logging

from eventsync.redmine.redmineapi import *

i = Issue.find(495)
print(i.to_dict())