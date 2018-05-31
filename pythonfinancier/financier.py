"""
This module allows you insert transactions and payees on Financier
"""

from pythonfinancier.easycouchdb import EasyCouchdb
import uuid
import configparser


def split_id(full_id):
    """
    Split an id value to get the last part of the string

    Parameters
    ----------
    full_id : str
        The full id value containing the budget, account, and transaction (
        etc.) information
    Returns
    -------
        Just the last part of the id value (which is usually the part of
        interest)
    """
    return full_id.split('_')[-1]


class Financier:
    """
    A class to more easily interact with a Financier user's database
    """

    selector = {}

    def __init__(self,
                 url_couch_db=None,
                 username=None,
                 password=None):
        """
        Create a new instance of the Financier class

        Parameters
        ----------
        url_couch_db : None or str
            If None, value is read from config file 'python-financier.ini'
            If string, Web url of the Financier database to which to connect
        username : None or str
            If None, value is read from config file 'python-financier.ini'
            If string, username to login with
        password : None or str
            If None, value is read from config file 'python-financier.ini'
            If string, password to login with
        """
        config = configparser.ConfigParser()

        if url_couch_db is None:
            config.read('python-financier.ini')
            url_couch_db = config['Financier']['url_couch_db']
        if username is None:
            config.read('python-financier.ini')
            username = config['Financier']['username']
        if password is None:
            config.read('python-financier.ini')
            password = config['Financier']['password']

        self.cdb = EasyCouchdb(url_couch_db)
        # print(self.cdb.login(username, password).json())
        self.login_json = self.cdb.login(username, password).json()
        if 'error' in self.login_json:
            raise ConnectionError('Could not connect: ' + self.login_json[
                'reason'])
        roles = self.login_json['roles']

        self.user_db = next(r for r in roles if r.startswith('userdb'))
        self.account_map = {}
        self.payee_map = {}
        self.budget_selector = ''
        print('Connecting on db {0}'.format(self.user_db))

    def get_all_budgets(self):
        """
        Get all the budgets that exist in this Financier database

        Returns
        -------
            List of the budgets as json objects, each containing the ``name``
            and ``_id`` of the budget
        """
        return self.cdb.query(self.user_db,
                              {'selector': {'_id': {'$regex': '^budget_'}},
                               'fields': ['_id', 'name']}).json()['docs']

    def connect_budget(self, name):
        """
        Set a particular budget as "active" within the Financier class

        Parameters
        ----------
        name : str
            Name of the budget to use (must be an exact match)
        """
        budget = self.find_budget(name)
        if budget:
            self.budget_selector = budget[0]['_id'].replace('budget', 'b')
            print('connecting on budget {0}'.format(self.budget_selector))
        else:
            raise Exception('Budget not found')

    def get_all_accounts(self):
        """
        Get a list of all accounts present within the active budget

        Returns
        -------
            List of accounts contained in the active budget
        """
        selector = {
            '_id': {'$regex': '^{0}_account_'.format(self.budget_selector)}}
        return self.cdb.query(self.user_db,
                              {'selector': selector,
                               'fields': ['_id', 'name']}).json()['docs']

    def save_transaction(self, account_name, this_id,
                         value, date, payee_name, memo):
        """
        Add a transaction to the database of the active budget. Category for
        transaction will be automatically determined from the autosuggest value
        for the particular payee.

        Parameters
        ----------
        account_name : str
            Name of the account to use
        this_id : str
            A UUID4 formatted id to use for the transaction
        value : float or int
            The value of the transaction (positive for inflow, negative for
            outflow)
        date : str
            The date of the transaction (formatted YYYY-MM-DD)
        payee_name : str
            Name of the payee to use (will be created if it does not
            already exist)
        memo : str
            Memo to save in the transaction

        Returns
        -------
            JSON response of the database upon inserting the transaction
        """
        # getting account
        # first check if already in cache map
        if account_name not in self.account_map:
            account = self.find_account(account_name)
            if not account:
                raise Exception("Account not found")
            else:
                account = split_id(account[0]['_id'])
                self.account_map[account_name] = account

        # getting payee or creating a new one
        # first check the cache map
        if payee_name not in self.payee_map:
            payee = self.get_or_create_payee(payee_name)
            payee['_id'] = split_id(payee['_id'])
            self.payee_map[payee_name] = payee

        id_transaction = self.get_id_transaction(this_id)
        tr = self.get_transaction(id_transaction)

        if not tr or '_id' not in tr:
            doc = {'_id': id_transaction, 'value': value,
                   'account': self.account_map[account_name],
                   'payee': self.payee_map[payee_name]['_id'], 'date': date,
                   'memo': memo}
            if 'categorySuggest' in self.payee_map[payee_name]:
                doc['category'] = self.payee_map[payee_name]['categorySuggest']
                print(
                    'Using category suggest from payee {0}'.format(payee_name))
            if '_rev' in tr:
                doc['_rev'] = tr['_rev']
            print('importing transaction {0}'.format(doc['_id']))
            return self.cdb.save(self.user_db, doc)
        else:
            print(
                'transaction {0} has already been imported '.format(tr['_id']))

    def get_transaction(self, id_transaction):
        """
        Get the JSON object representing a transaction

        Parameters
        ----------
        id_transaction : str
            transaction id of the form
            "<BUDGET UUID4>_transaction_<TRANSACTION UUID4>"

        Returns
        -------
            JSON representation of the transaction object in the database
        """
        return self.cdb.get_doc(self.user_db, id_transaction).json()

    def get_id_transaction(self, this_id):
        """
        Helper function to build a valid transaction id from the currently
        selected budget and a custom UUID4 value

        Parameters
        ----------
        this_id : str
            UUID4-formatted id for a particular transaction

        Returns
        -------
            String of the form "<BUDGET UUID4>_transaction_<TRANSACTION UUID4>"
            that can be used directly in the database
        """
        return '{0}_transaction_{1}'.format(self.budget_selector, this_id)

    def find_budget(self, name):
        """
        Find budget(s) by name within the database

        Parameters
        ----------
        name : str
            Name for which to search (must be an exact match)
        Returns
        -------
            List of account json objects that match the given name
        """
        return self.cdb.query(self.user_db, {
            'selector': {'_id': {'$regex': '^budget_'}, 'name': name},
            'fields': ['_id', 'name']}).json()['docs']

    def find_account(self, name):
        """
        Find account(s) by name within the database

        Parameters
        ----------
        name : str
            Name for which to search (must be an exact match)
        Returns
        -------
            List of account json objects that match the given name
        """
        selector = {
            '_id': {'$regex': '^{0}_account_'.format(self.budget_selector)},
            'name': name}
        return self.cdb.query(self.user_db,
                              {'selector': selector,
                               'fields': ['_id', 'name']}).json()['docs']

    def find_payee(self, name):
        """
        Find payee(s) by name within the database

        Parameters
        ----------
        name : str
            Name for which to search (must be an exact match)
        Returns
        -------
            List of payee json objects that match the given name
        """
        selector = {
            '_id': {'$regex': '^{0}_payee_'.format(self.budget_selector)},
            'name': name}
        return self.cdb.query(self.user_db,
                              {'selector': selector,
                               'fields': ['_id', 'name',
                                          'categorySuggest']}).json()['docs']

    def insert_payee(self, name):
        """
        Insert a payee into the database with the given name

        Parameters
        ----------
        name : str

        Returns
        -------
            Response from the insert request
        """
        doc = {
            '_id': '{0}_payee_{1}'.format(self.budget_selector, uuid.uuid4()),
            'name': name, 'internal': False, 'autosuggest': True}
        return self.cdb.insert(self.user_db, doc).json()

    def get_or_create_payee(self, name):
        """
        Return id of a payee, and create one if it does not exist

        Parameters
        ----------
        name : str
            Name of the payee to use or get

        Returns
        -------
        ret : str
            The ``id`` value of the existing (or created) payee
        """
        payee = self.find_payee(name)
        if payee:
            return payee[0]
        else:
            ret = self.insert_payee(name)
            ret['_id'] = ret['id']
            return ret
