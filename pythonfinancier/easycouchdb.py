"""
A module for more easily interacting with a CouchDB instance. Handles
login, querying, listing all documents, and inserting/saving values
"""

import requests
from urllib.parse import urljoin
from time import sleep
from requests.adapters import HTTPAdapter
import logging


class EasyCouchdb:
    """
    Easily get, insert, and update documents within a CouchDB database.
    """

    SESSION = '_session'
    ALL_DBS = '_all_dbs'
    ALL_DOCS = '_all_docs'
    FIND = '_find'
    TIMEOUT = 10

    req_session = None

    def __init__(self, url):
        """
        Create an EasyCouchdb instance

        Parameters
        ----------
        url : str
        """
        self.logger = logging.getLogger(__name__)
        self.url = url
        self.SESSION_URL = urljoin(self.url, self.SESSION)
        self.ALL_DBS_URL = urljoin(self.url, self.ALL_DBS)
        self.logger.debug('SESSION_URL: {}'.format(self.SESSION_URL))

    def login(self, username, password):
        """
        Login to the database

        Parameters
        ----------
        username : str
        password : str

        Returns
        -------
            Response to the login POST request
        """
        self.req_session = requests.session()
        self.req_session.mount(self.url, HTTPAdapter(max_retries=5))
        return self.req_session.post(self.SESSION_URL,
                                     data={'name': username,
                                           'password': password},
                                     timeout=self.TIMEOUT)

    def all_docs(self, db_name):
        """
        Get all documents from the CouchDB instance

        Parameters
        ----------
        db_name : str
            Name of the database to query

        Returns
        -------
            Response to the all_docs GET request
        """
        return self.req_session.get(
            urljoin(self.url, '/'.join([db_name, self.ALL_DOCS])),
            timeout=self.TIMEOUT)

    def query(self, db_name, selector):
        """
        Query the database with a given selector

        Parameters
        ----------
        db_name : str
            Name of the database to query
        selector : dict
            Selector to use for the query

        Returns
        -------
        ret : list
            List of the documents that match the given query
        """
        sleep(0.5)
        self.logger.debug('executing query: {0}'.format(selector))
        ret = self.req_session.post(
            urljoin(self.url, '/'.join([db_name, self.FIND])), json=selector,
            timeout=self.TIMEOUT)
        self.logger.debug('query executed')
        return ret

    def insert(self, db_name, doc):
        """
        Insert a document into the database

        Parameters
        ----------
        db_name : str
            Name of the database into which to insert
        doc : dict
            JSON-formatted dictionary of the document to add

        Returns
        -------
            Response of the POST request for the insertion
        """
        sleep(0.5)
        self.logger.debug('inserting', urljoin(self.url, db_name))
        return self.req_session.post(urljoin(self.url, db_name), json=doc,
                                     timeout=self.TIMEOUT)

    def save(self, db_name, doc):
        """
        Update a document with a given id in the database

        Parameters
        ----------
        db_name : str
            Name of the database into which to insert
        doc : dict
            JSON-formatted dictionary of the document to add

        Returns
        -------
            Response of the PUT request for the document update
        """
        sleep(0.5)
        self.logger.debug('putting', urljoin(self.url,
                                         '/'.join([db_name, doc['_id']])))
        return self.req_session.put(
            urljoin(self.url, '/'.join([db_name, doc['_id']])), json=doc)

    def get_doc(self, db_name, _id):
        """
        Get a document from the database with a given id value

        Parameters
        ----------
        db_name : str
            Name of the database from which to get the document
        _id : str
            ID value of the document

        Returns
        -------
            Response of the GET request for the document retrieval
        """
        sleep(0.5)
        self.logger.debug('getting',
                          urljoin(self.url, '/'.join([db_name, _id])))
        return self.req_session.get(
            urljoin(self.url, '/'.join([db_name, _id])),
            timeout=self.TIMEOUT)
