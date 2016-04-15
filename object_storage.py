'''
Created on 31/mar/2016
@author: giovanni
'''

import httplib
import json
import sys
import logging

from settings import HOST_AUTH, FILAB_USERNAME, FILAB_PASSWORD
BudapestPublicUrl = u"http://148.6.80.5:8080/v1/AUTH_00000000000000000000000000008813"

TEST_CONTAINER_NAME = 'TestContainerPython'
TEST_OBJECT_NAME = 'TestObjectPython.txt'
TEST_TEXT = 'Hello SWIFT World'

# Init a simple logger...
logging.basicConfig(level=logging.INFO)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logger = logging.getLogger()
logger.addHandler(console)

# from wip.object_storage import os_get_token
def get_token(username, password, conn=None):
    if not conn:
        conn = httplib.HTTPConnection(HOST_AUTH)
    headers = {'Content-Type': 'application/json'}
    body = '{"auth": {"passwordCredentials":{"username": "'+username+'", "password": "'+password+'"}}}'
    conn.request("POST", "/v2.0/tokens", body, headers)
    response = conn.getresponse()
    data = response.read()
    datajson = json.loads(data)
    token = datajson['access']['token']['id']      
    return token
# retrieve tenant
def get_tenant(token, conn=None):
    if not conn:
        conn = httplib.HTTPConnection(HOST_AUTH)
    headers = {'x-auth-token': token}
    conn.request("GET", "/v2.0/tenants", None, headers)
    response = conn.getresponse()
    data = response.read()
    datajson = json.loads(data)
    tenant = datajson['tenants'][0]['id']
    return tenant

# retrieve tenant authentication json
def get_tenant_authentication(tenant, username, password, conn=None):
    username = FILAB_USERNAME
    password  = FILAB_PASSWORD
    if not conn:
        conn = httplib.HTTPConnection(HOST_AUTH)
    headers = {'Content-Type': 'application/json'}
    body = '{"auth": {"tenantId": "'+tenant+'", "passwordCredentials":{"username": "'+username+'", "password": "'+password+'"}}}'
    conn.request("POST", "/v2.0/tokens", body, headers)
    response = conn.getresponse()
    data = response.read()
    return json.loads(data)

# Request authentication of user
def authentication_request(username, password):
    conn = httplib.HTTPConnection(HOST_AUTH)
    
    # retrieve initial token
    initialtoken = get_token(username, password, conn=None)
    logger.info('Initial Token is: ' + initialtoken)
    
    # retrieve tenant
    tenant = get_tenant(initialtoken, conn=conn)
    logger.info('Tenant is: ' + tenant)
    
    # retrieve authentication json
    return get_tenant_authentication(tenant, username, password, conn=conn)   

# Do a HTTP request defined by HTTP verb, a Url, a dict of headers and a body.
def swift_request(verb, url, headers, body):    
    logger.info('swift_request verb is: ' + verb)
    substring = url[url.find("//")+2:]
    marker = substring.find("/")
    host = substring[:marker]
    resource = substring[marker:]
    logger.info('host is: ' + host)
    logger.info('resource is: ' + resource)
    conn = httplib.HTTPConnection(host)
    conn.request(verb, resource, body, headers)
    response = conn.getresponse()

    if response.status not in [200, 201, 202, 204]:
        logger.error(response.reason)
        logger.warn(response.read())
        sys.exit(1)

    result = "Status: " + str(response.status) + ", Reason: " + response.reason + ", Body: " +  response.read()   
    conn.close()
    return result

def create_container(token, auth, name):
    headers = {"X-Auth-Token": token}
    body = None
    url = auth + "/" + name
    return swift_request('PUT', url, headers, body)

def list_container(token, auth, name):
    headers = {"X-Auth-Token": token}
    body = None
    url = auth + "/" + name
    return swift_request('GET', url, headers, body)

def store_text(token, auth, container_name, object_name, object_text):
    headers = {"X-Auth-Token": token}
    body = object_text
    url = auth + "/" + container_name + "/" + object_name
    return swift_request('PUT', url, headers, body)

def retrieve_text(token, auth, container_name, object_name):
    headers = {"X-Auth-Token": token}
    body = None
    url = auth + "/" + container_name + "/" + object_name
    return swift_request('GET', url, headers, body)

def delete_object(token, auth, container_name, object_name):
    headers = {"X-Auth-Token": token}
    body = None
    url = auth + "/" + container_name + "/" + object_name
    return swift_request('DELETE', url, headers, body)

def delete_container(token, auth, container_name):
    headers = {"X-Auth-Token": token}
    body = None
    url = auth + "/" + container_name
    return swift_request('DELETE', url, headers, body)

# perform some basic Object Store operations
def os_test(delete=False):
    # display basic info
    logger.info('Authorisation host is: ' + HOST_AUTH)

    # get authentication response
    auth_response = authentication_request(FILAB_USERNAME, FILAB_PASSWORD)

    # extract token
    token = auth_response['access']['token']['id']
    logger.info('Security token is: ' + token)

    """
    # extract authentication string required for addressing users resources
    n = 0
    for i in auth_response['access']['serviceCatalog']:
        if i['name'] == 'swift':
            n += 1
            # may take here any of the available entries that works
            # auth_url = i['endpoints'][1]['publicURL']
            endpoints = i['endpoints']
            for endpoint in endpoints:
                auth_url = endpoint['publicURL']
                try:
                    response = create_container(token, auth_url, TEST_CONTAINER_NAME)
                    logger.info('Create Container Response: ' + response)
                    break
                except:
                    continue
            break
    """
    auth_url = BudapestPublicUrl
    logger.info('auth_url is: ' + auth_url)

    if delete:
        response = delete_object(token, auth_url, TEST_CONTAINER_NAME, TEST_OBJECT_NAME)
        logger.info('Delete Object Response: ' + response)
    
        response = list_container(token, auth_url, TEST_CONTAINER_NAME)
        logger.info('List Container Response: ' + response)
    
        response = delete_container(token, auth_url, TEST_CONTAINER_NAME)
        logger.info('Delete Container Response: ' + response)

    response = create_container(token, auth_url, TEST_CONTAINER_NAME)
    logger.info('Create Container Response: ' + response)

    response = list_container(token, auth_url, TEST_CONTAINER_NAME)
    logger.info('List Container Response: ' + response)

    response = store_text(token, auth_url, TEST_CONTAINER_NAME, TEST_OBJECT_NAME, TEST_TEXT)
    logger.info('Store Text Response: ' + response)

    response = list_container(token, auth_url, TEST_CONTAINER_NAME)
    logger.info('List Container Response: ' + response)

    response = retrieve_text(token, auth_url, TEST_CONTAINER_NAME, TEST_OBJECT_NAME)
    logger.info('Retrieve Text Response: ' + response)


def put_page_version(token, auth_url, site_slug, action_id, page_path, version_time, page_body):
    container_name = site_slug
    action_string = str(action_id).zfill(6)
    safe_path = page_path.replace('/', '_')
    safe_time = version_time.strftime('%Y-%m-%d %H:%M')
    object_name = '%s_%s' % (action_string, safe_path)
    object_dict = {'name': object_name, 'site': site_slug, 'event': action_id, 'path': page_path, 'datetime': safe_time, 'html': page_body}
    object_text = json.dumps(object_dict)
    response = store_text(token, auth_url, container_name, object_name, object_text)
    return response

def put_pages_test(n_pages=1, description=''):
    from django.contrib.auth.models import User
    from actstream.models import Action
    from wip.journal import site_archive_pages
    from wip.models import Site, Webpage, PageVersion

    # display basic info
    logger.info('Authorisation host is: ' + HOST_AUTH)
    # get authentication response
    auth_response = authentication_request(FILAB_USERNAME, FILAB_PASSWORD)
    # extract token
    token = auth_response['access']['token']['id']
    logger.info('Security token is: ' + token)
    auth_url = BudapestPublicUrl
    logger.info('auth_url is: ' + auth_url)

    site_id = 1
    site = Site.objects.get(pk=site_id)
    user = User.objects.get(pk=1)
    site_archive_pages(user, site, description=description)
    action_id = Action.objects.latest('id').id
    if n_pages:
        pages = Webpage.objects.filter(site=site)[:n_pages]
    else:
        pages = Webpage.objects.filter(site=site).all()
    for page in pages:
        versions = PageVersion.objects.filter(webpage=page).order_by('-time')
        last_version = versions and versions[0] or None
        if last_version:
            response = put_page_version(token, auth_url, site.slug, action_id, page.path, last_version.time, last_version.body)
            logger.info('Store Text Response: ' + response)
