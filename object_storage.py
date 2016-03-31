'''
Created on 31/mar/2016
@author: giovanni
'''

import httplib
import json
import sys
import logging

from settings import HOST_AUTH, FILAB_USERNAME, FILAB_PASSWORD

TEST_CONTAINER_NAME = 'AlfaBeta'
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
    print 'verb: ', verb
    print 'resource: ', resource
    print 'body: ', body
    print 'headers: ', headers
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
def os_test():
    # display basic info
    logger.info('Authorisation host is: ' + HOST_AUTH)

    # get authentication response
    auth_response = authentication_request(FILAB_USERNAME, FILAB_PASSWORD)

    # extract token
    token = auth_response['access']['token']['id']
    logger.info('Security token is: ' + token)

    # extract authentication string required for addressing users resources
    for i in auth_response['access']['serviceCatalog']:
        if i['name'] == 'swift':
            # may take here any of the available entries that works
            auth_url = i['endpoints'][1]['publicURL']
            break
    logger.info('auth_url is: ' + auth_url)

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

    """
    response = delete_object(token, auth_url, TEST_CONTAINER_NAME, TEST_OBJECT_NAME)
    logger.info('Delete Object Response: ' + response)

    response = list_container(token, auth_url, TEST_CONTAINER_NAME)
    logger.info('List Container Response: ' + response)

    response = delete_container(token, auth_url, TEST_CONTAINER_NAME)
    logger.info('Delete Container Response: ' + response)
    """

