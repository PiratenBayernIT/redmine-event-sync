import logging
from pyactiveresource.activeresource import ActiveResource
from .resourceaddons import find_extended, get_all_resource_objects, find_by_attrib
from .localsettings import API_SITE
from eventsync.redmine.resourceaddons import date_attrib, datetime_attrib,\
    custom_fields

logg = logging.getLogger(__name__)


def make_logger():
    global logg
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("pyactiveresource").setLevel(logging.INFO)
    logg = logging.getLogger("redmine_apitest")
    logg.setLevel(logging.DEBUG)
    return logg


class BaseRedmineResource(ActiveResource):
    _site = API_SITE
    _headers = {}
    _all_limit = 100
    all = classmethod(get_all_resource_objects)

    @classmethod
    def impersonate_user(cls, user_name):
        if not user_name:
            try:
                del cls._headers["X-Redmine-Switch-User"]
            except:
                pass
        else:
            cls._headers["X-Redmine-Switch-User"] = user_name

    @classmethod
    def map(cls, func):
        offset = 0
        limit = 60
        cur_result = [None]
        result = []
        while cur_result:
            logg.debug("getting %ix %s offset %s", limit, cls, offset)
            cur_result = cls.find(limit=limit, offset=offset)
            mapped = map(func, cur_result)
            result += mapped
            offset += len(cur_result)
        return result

    @classmethod
    def filter(cls, func):
        offset = 0
        limit = 60
        cur_result = [None]
        result = []
        while cur_result:
            logg.debug("getting %ix %s offset %s", limit, cls, offset)
            cur_result = cls.find(limit=limit, offset=offset)
            logg.debug("current result %s", cur_result)
            filtered = filter(func, cur_result)
            result += filtered
            offset += len(cur_result)
        return result


@find_extended
@custom_fields
@datetime_attrib("updated_on")
@datetime_attrib("created_on")
@date_attrib("start_date")
@date_attrib("due_date")
class Issue(BaseRedmineResource):
    pass


@find_by_attrib("identifier")
class Project(BaseRedmineResource):
    def all_subprojects(self):
        pass


#class ProjectMembership(BaseRedmineResource):
#    pass


@find_by_attrib("login")
class User(BaseRedmineResource):
    pass


class TimeEntry(BaseRedmineResource):
    pass


class News(BaseRedmineResource):
    pass


#class IssueRelation(BaseRedmineResource):
#    pass


#class WikiPage(BaseRedmineResource):
#    pass


class Version(BaseRedmineResource):
    pass


class Query(BaseRedmineResource):
    pass


#class Attachment(BaseRedmineResource):
#    pass


class IssueStatus(BaseRedmineResource):
    @classmethod
    def filter(cls, func):
        return filter(func, cls.find())

    @classmethod
    def map(cls, func):
        return map(func, cls.find())


@find_by_attrib("name")
class Tracker(BaseRedmineResource):
    pass


#class Enumeration(BaseRedmineResource):
#    pass


class IssueCategory(BaseRedmineResource):
    pass


class Role(BaseRedmineResource):
    pass


class Group(BaseRedmineResource):
    pass


### plugins

# contact plugin

@find_extended
@find_by_attrib("company")
class Contact(BaseRedmineResource):
    pass


class NiceDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)

    def __getattr__(self, key):
        return self.__getitem__(key)


def create_stammtisch_termin(d):
    german_dateformat = "%d.%m.%y"
    us_dateformat = "%Y-%m-%d"
    t = Issue()
    t.subject = "Infostammtisch Weiden " + d.strftime(german_dateformat)
    t.description = "In der Sportgaststätte Anpfiff, Königsberger Str. 48, 92637 Weiden"
    t.assigned_to_id = User.find_first_by_login("escaP").id
    t.tracker_id = Tracker.find_first_by_name("Termin").id
    t.project_id = Project.find_first_by_identifier("opf_termine").id
    t.start_date = d
    t.due_date = d
    custom_fields = [dict(name="Startzeit", id=2, value="19:00"), dict(name="Ende", id=3, value="23:00")]
    t.custom_fields = custom_fields
    t.save()
