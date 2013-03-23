import logging
from pyactiveresource.activeresource import ActiveResource
from functools import wraps, partial
from datetime import datetime, time, date

from .localsettings import REDMINE_DATETIME_FORMAT, REDMINE_DATE_FORMAT, REDMINE_TIME_FORMAT
from pyactiveresource.element_containers import ElementDict

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
        """Find which searches all objects. 
        Redmine returns only a limited number of objects for some resources,
        so we have to repeat the query multiple times.
        """
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


def find_by_attrib(attrib):
    """Add two find helpers for easy filtering by single attributes.
    This will add two methods to the decorated class:
    * cls.find_first_by_<attrib>(value)
    * cls.find_all_by_<attrib>(value)
    """
    def _find_by_attrib(cls):
        find_meth = cls._find_orig if hasattr(cls, "_find_orig") else cls.find
        def __find_first_by_attrib(cls, value):
            offset = 0
            limit = 60

            cur_result = [None]
            while cur_result:
                cur_result = find_meth(limit=limit, offset=offset)
                filtered = filter(lambda u: getattr(u, attrib) == value, cur_result)
                try:
                    return next(filtered)
                except:
                    pass
                offset += len(cur_result)
            return None

        def __find_all_by_attrib(cls, value):
            offset = 0
            limit = 60
            cur_result = [None]
            result = []
            while cur_result:
                cur_result = find_meth(limit=limit, offset=offset)
                filtered = filter(lambda u: getattr(u, attrib) == value, cur_result)
                result += filtered
                offset += len(cur_result)
            return result
        
        setattr(cls, "find_first_by_" + attrib, classmethod(__find_first_by_attrib))
        setattr(cls, "find_all_by_" + attrib, classmethod(__find_all_by_attrib))
        return cls

    return _find_by_attrib


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


def custom_fields(cls):
    """Add some sugar to Redmine API objects for custom fields.
    Custom fields can be read like an object attribute, like a.end, and
    written like a.end = 6.
    The custom field object is synchronized automatically (only client, not on the server!)
    """
    logg.info("cust fields for %s", cls)
    orig_getattr = cls.__getattr__
    orig_setattr = cls.__setattr__
    orig_init = cls.__init__
    
    def _getattr(self, attrib):
        try:
            cf = self.__dict__["_custom_fields"][attrib]
            self.__dict__[attrib] = cf.value
            return cf.value
        except:
            return orig_getattr(self, attrib)
            
    def _setattr(self, attrib, value):
        try:
            cf = self.__dict__["_custom_fields"][attrib]
            self.__dict__[attrib] = value
            cf.value = value
        except:
            orig_setattr(self, attrib, value)
    
        
    def _init(self, *args):
        orig_init(self, *args)
        try:
            custom_fields = self.__dict__["attributes"]["custom_fields"]
            if not hasattr(custom_fields[0], "name"):
                custom_fields = args[0]["custom_fields"]
        except:
            return
        else:
            custom_field_dict = {}
            for cf in custom_fields:
                custom_field_dict[cf.name.lower()] = cf
            self.__dict__["_custom_fields"] = custom_field_dict
                
            
    setattr(cls, "__getattr__", _getattr)
    setattr(cls, "__setattr__", _setattr)
    setattr(cls, "__init__", _init)
    return cls