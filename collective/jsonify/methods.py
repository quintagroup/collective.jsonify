import base64
import sys
import pprint
import traceback
from Products.Five.browser import BrowserView

try:
    import simplejson as json
except:
    import json

from wrapper import Wrapper


def _clean_dict(dct, error):
    new_dict = dct.copy()
    message = str(error)
    for key, value in dct.items():
        if message.startswith(repr(value)):
            del new_dict[key]
            return key, new_dict
    raise ValueError("Could not clean up object")

def get_item(self):
    """
    """

    try:
        context_dict = Wrapper(self)
    except Exception, e:
        tb = pprint.pformat(traceback.format_tb(sys.exc_info()[2]))
        return 'ERROR: exception wrapping object: %s\n%s' % (str(e), tb)
    passed = False
    while not passed:
        try:
            if 'query' in context_dict.keys():
                res = []
                for item in context_dict['query']:
                    rr = [(key, item[key]) for key in item]
                    res.append(rr)
                context_dict['query'] = res
            JSON = json.dumps(context_dict)
            passed = True
        except Exception, error:
            if "serializable" in str(error):
                key, context_dict = _clean_dict(context_dict, error)
                pprint.pprint('Not serializable member %s of %s ignored'
                     % (key, repr(self)))
                passed = False
            else:
                return ('ERROR: Unknown error serializing object: %s' %
                    str(error))
    self.REQUEST.RESPONSE.setHeader("Content-type", "application/json")
    return JSON


def get_children(self):
    """
    """
    from Acquisition import aq_base

    children = []
    if getattr(aq_base(self), 'objectIds', False):
        children = self.objectIds()
        # Btree based folders return an OOBTreeItems
        # object which is not serializable
        # Thus we need to convert it to a list
        if not isinstance(children, list):
            children = [item for item in children]
    self.REQUEST.RESPONSE.setHeader("Content-type", "application/json")
    return json.dumps(children)


def get_catalog_results(self):
    """Returns a list of paths of all items found by the catalog.
       Query parameters can be passed in the request.
    """
    if not hasattr(self.aq_base, 'unrestrictedSearchResults'):
        return
    query = self.REQUEST.form.get('catalog_query', None)
    if query:
        query = eval(base64.b64decode(query),
                     {"__builtins__": None}, {})
    item_paths = [item.getPath() for item
                  in self.unrestrictedSearchResults(**query)]
    self.REQUEST.RESPONSE.setHeader("Content-type", "application/json")
    return json.dumps(item_paths)



class Jsonify(BrowserView):


    def get_item(self):
        """
        """      
        return get_item(self.context)


    def get_children(self):
        """
        """
        return get_children(self.context)


    def get_catalog_results(self):
        """
        """
        return get_catalog_results(self.context)

    def update_uids(self):
        """Check for UIDs on original site and set
        """
        import urllib2
        from plone.uuid.interfaces import ATTRIBUTE_NAME
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(realm='Zope',
                                  uri='http://localhost:23603/',
                                  user='admin',
                                  passwd='12345')
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        #req = urllib2.Request('http://localhost:23603/')
        #try:
        #    f = urllib2.urlopen(req)
        #    resp = f.read()
        #except urllib2.URLError:
        #    raise

        self.item_paths = sorted(simplejson.loads(resp))

        res = self.context.portal_catalog()
        import pdb;pdb.set_trace()
        for item in res[:10]:
            path = item.getPath().replace('/www','/cells')+'/get_item'
            req = urllib2.Request('http://localhost:23603'+path)
            f = urllib2.urlopen(req)
            resp = f.read()
            data = simplejson.loads(resp)
            obj = item.getObject()
            setatttr(obj, ATTRIBUTE_NAME, data['uid'])