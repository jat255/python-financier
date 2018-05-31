import requests
from urllib.parse import urljoin, urlunsplit
from time import sleep
from requests.adapters import HTTPAdapter


class EasyCouchdb:
    SESSION = '_session'
    ALL_DBS = '_all_dbs'
    ALL_DOCS = '_all_docs'
    FIND = '_find'
    TIMEOUT = 10

    req_session = None

    def __init__(self, url):
        self.url = url
        self.SESSION_URL = urljoin(self.url, self.SESSION)
        self.ALL_DBS_URL = urljoin(self.url, self.ALL_DBS)
        print(self.SESSION_URL)

    def login(self, username, password):
        self.req_session = requests.session()
        self.req_session.mount(self.url, HTTPAdapter(max_retries=5))
        return self.req_session.post(self.SESSION_URL,
                                     data={'name': username,
                                           'password': password},
                                     timeout=self.TIMEOUT)

    def all_docs(self, db_name):
        return self.req_session.get(
            urljoin(self.url, '/'.join([db_name, self.ALL_DOCS])),
            timeout=self.TIMEOUT)

    def query(self, db_name, selector):
        sleep(0.5)
        print('executing query: {0}'.format(selector))
        ret = self.req_session.post(
            urljoin(self.url, '/'.join([db_name, self.FIND])), json=selector,
            timeout=self.TIMEOUT)
        print('query executed')
        return ret

    def insert(self, db_name, doc):
        sleep(0.5)
        return self.req_session.post(urljoin(self.url, db_name), json=doc,
                                     timeout=self.TIMEOUT)

    def save(self, db_name, doc):
        sleep(0.5)
        return self.req_session.put(
            urljoin(self.url, '/'.join([db_name, doc['_id']])), json=doc)

    def get_doc(self, db_name, _id):
        sleep(0.5)
        return self.req_session.get(
            urljoin(self.url, '/'.join([db_name, _id])),
            timeout=self.TIMEOUT)
