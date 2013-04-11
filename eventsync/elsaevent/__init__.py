# -*- coding: utf-8 -*-
'''
elsaevent
Created on 15.03.2013
@author: escaP
'''
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .datamodel import DeclarativeBase
from .localsettings import ELSA_SQLALCHEMY_CONNECTION_STR

engine = create_engine(ELSA_SQLALCHEMY_CONNECTION_STR)
DeclarativeBase.metadata.bind = engine
session = sessionmaker(bind=engine)()
