import logging
from pyactiveresource.activeresource import ActiveResource
from functools import wraps, partial
from datetime import datetime, time, date

from .localsettings import REDMINE_DATETIME_FORMAT, REDMINE_DATE_FORMAT, REDMINE_TIME_FORMAT

logg = logging.getLogger(__name__)


def get_all_resource_objects(cls):
    offset = 0
    cur_result = [None]
    result = []
    while cur_result:
        cur_result = cls.find(limit=cls._all_limit, offset=offset)
        result += cur_result
        offset += len(cur_result)
    return result


def find_extended(cls):
    def _find_extended(cls, *args, **kwargs):
        cur_result = [None]
        result = []
        fargs = kwargs.copy()
        fargs["offset"] = 0
        fargs["limit"] = 60
        while cur_result:
            cur_result = cls._find_orig(*args, **fargs)
            if isinstance(cur_result, cls):
                return cur_result
            result += cur_result
            fargs["offset"] += len(cur_result)
        return result
    
    cls._find_orig = cls.find
    cls.find = classmethod(_find_extended)
    return cls


def find_first_by_attrib(attrib):
    def _find_first_by_attrib(cls):
        def _func(cls, value):
            offset = 0
            limit = 60

            cur_result = [None]
            while cur_result:
                cur_result = cls.find(limit=limit, offset=offset)
                filtered = filter(lambda u: getattr(u, attrib) == value, cur_result)
                try:
                    return next(filtered)
                except:
                    pass
                offset += len(cur_result)
            return None

        setattr(cls, "find_first_by_" + attrib, classmethod(_func))
        return cls

    return _find_first_by_attrib


def find_all_by_attrib(attrib):
    def _find_all_by_attrib(cls):
        def _func(cls, value):
            offset = 0
            limit = 60
            cur_result = [None]
            result = []
            while cur_result:
                cur_result = cls.find(limit=limit, offset=offset)
                filtered = filter(lambda u: getattr(u, attrib) == value, cur_result)
                result += filtered
                offset += len(cur_result)
            return result

        setattr(cls, "find_all_by_" + attrib, classmethod(_func))
        return cls

    return _find_all_by_attrib


# factory function, see below for derived decorators

def _datetime_attrib(klass, attrib):
    if klass == date:
        time_format = REDMINE_DATE_FORMAT
    elif klass == time:
        time_format = REDMINE_TIME_FORMAT
    elif klass == datetime:
        time_format = REDMINE_DATETIME_FORMAT
    else:
        raise TypeError("klass must be 'date', 'time' or 'datetime' class!")
        
    def __datetime_attrib(cls):
        def _get(self):
            value = self.attributes[attrib]
            if value is None:
                return None
            return datetime.strptime(value, time_format)
            
        def _set(self, value):
            self.attributes[attrib] = datetime.strftime(value, time_format)
            
        def _del(self):
            del self.attributes[attrib]
            
        prop = property(_get, _set, _del, "{} property, returns a {} object".format(attrib, klass.__name__))
        setattr(cls, attrib, prop)
        return cls
    
    return __datetime_attrib


datetime_attrib = partial(_datetime_attrib, datetime)
date_attrib = partial(_datetime_attrib, date)
time_attrib = partial(_datetime_attrib, time)