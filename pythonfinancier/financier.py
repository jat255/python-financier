"""
This module allows you insert transactions and payees on Financier
"""

from pythonfinancier.easycouchdb import EasyCouchdb
import uuid
import configparser
import logging


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
                 conf_file='python-financier.ini',
                 url_couch_db=None,
                 username=None,
                 password=None):
        """
        Create a new instance of the Financier class

        Parameters
        ----------
        conf_file : str
            Location of configuration file from which to read settings
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
            config.read(conf_file)
            url_couch_db = config['Financier']['url_couch_db']
        if username is None:
            config.read(conf_file)
            username = config['Financier']['username']
        if password is None:
            config.read(conf_file)
            password = config['Financier']['password']

        self.logger = logging.getLogger(__name__)

        self.cdb = EasyCouchdb(url_couch_db)
        self.login_json = self.cdb.login(username, password).json()
        self.logger.debug('login_json: {}'.format(self.login_json))
        if 'error' in self.login_json:
            raise ConnectionError('Could not connect: ' + self.login_json[
                'reason'])
        roles = self.login_json['roles']

        self.user_db = next(r for r in roles if r.startswith('userdb'))
        self.account_map = {}
        self.category_map = {}
        self.payee_map = {}
        self.budget_selector = ''
        self.logger.debug('Connecting on db {0}'.format(self.user_db))

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
            self.logger.debug('connecting on '
                          'budget {0}'.format(self.budget_selector))
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

    def save_transaction(self, account_name,
                         category_name, value, date,
                         payee_name, memo):
        """
        Add a transaction to the database of the active budget.

        Parameters
        ----------
        account_name : str
            Name of the account to use
        category_name : str
            Name of the category to use
            Can also be "income" (for this month) or "incomeNextMonth" (for
            next month)
        value : float or int
            The value of the transaction (positive for inflow, negative for
            outflow). This value is in cents (so $4 = a value of 400).
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
        this_id = uuid.uuid4()

        # getting account from either map or database
        account_id = self.find_account(account_name)['_id']

        # getting payee or creating a new one
        payee_id = self.get_or_create_payee(payee_name)['_id']

        # find category id from map or database:
        category_id = self.find_category(category_name)['_id']

        id_transaction = self.get_id_transaction(str(this_id))
        tr = self.get_transaction(id_transaction)

        if not tr or '_id' not in tr:
            doc = {'_id': id_transaction, 'value': value,
                   'account': account_id,
                   'payee': payee_id, 'date': date,
                   'category': category_id, 'memo': memo}
            self.logger.debug('Adding', doc)

            if '_rev' in tr:
                doc['_rev'] = tr['_rev']
            self.logger.debug('importing transaction {0}'.format(doc['_id']))

            return self.cdb.save(self.user_db, doc)
        else:
            self.logger.warning(
                'transaction {0} has already been imported '.format(tr['_id']))

    def save_split(self, account_name,
                   value, date, payee_name,
                   memo, transactions):
        """
        Add a split transaction to the database.

        Parameters
        ----------
        account_name : str
            Name of the account to use
        value : float or int
            The value of the transaction (positive for inflow, negative for
            outflow). This value is in cents (so $4 = a value of 400).
        date : str
            The date of the transaction (formatted YYYY-MM-DD)
        payee_name : str
            Name of the payee to use (will be created if it does not
            already exist)
        memo : str
            Memo to save in the transaction
        transactions : list
            a list of dictionaries, each with keys [value, category_name,
            memo, payee_name], which will be included in the split transaction

        Returns
        -------
            JSON response of the database upon inserting the transaction
        """
        this_id = uuid.uuid4()

        # getting account from either map or database
        account_id = self.find_account(account_name)['_id']

        # getting payee or creating a new one
        payee_id = self.get_or_create_payee(payee_name)['_id']

        id_transaction = self.get_id_transaction(str(this_id))
        tr = self.get_transaction(id_transaction)

        self.logger.info(transactions)
        for i, t in enumerate(transactions):
            t['category'] = self.find_category(t.pop('category_name'))['_id']
            t['payee'] = self.get_or_create_payee(t.pop('payee_name'))['_id']
            transactions[i] = t

        self.logger.info(transactions)

        if not tr or '_id' not in tr:
            # category is "split"
            doc = {'_id': id_transaction, 'value': value,
                   'account': account_id,
                   'payee': payee_id, 'date': date,
                   'category': 'split', 'memo': memo,
                   'splits': transactions}
            self.logger.debug('Adding', doc)

            if '_rev' in tr:
                doc['_rev'] = tr['_rev']
            self.logger.debug('importing transaction {0}'.format(doc['_id']))

            return self.cdb.save(self.user_db, doc)
        else:
            self.logger.warning(
                'transaction {0} has already been imported '.format(tr['_id']))

    def save_transfer(self,
                      from_account_name,
                      to_account_name,
                      value,
                      date,
                      memo=None,
                      from_category_name=None):
        """
        Add a split transaction to the database.

        Parameters
        ----------
        from_account_name : str
            Name of the account from which the transfer occurs
        to_account_name : str
            Name of the account to which the transfer occurs
        value : float or int
            The value of the transaction in cents (so $4 = a value of 400).
            A positive value represents an outflow from ``from_account_name``
            and inflow into ``to_account_name`` and vice versa for negative.
        date : str
            The date of the transaction (formatted YYYY-MM-DD)
        memo : str or None
            Memo to save in the transactions (optional)
        from_category_name : str or None
            If the transfer is to an off-budget account, the category should
            be provided (optional)

        Returns
        -------
            JSON response of the database upon inserting the transaction
        """
        from_id = uuid.uuid4()
        to_id = uuid.uuid4()

        # getting account from either map or database
        from_account_id = self.find_account(from_account_name)['_id']
        to_account_id = self.find_account(to_account_name)['_id']

        # Get category (if needed)
        if from_category_name:
            from_category_id = self.find_category(from_category_name)['_id']
        else:
            from_category_id = None

        # Need to create two transactions for each side of the transfer
        # 'payee' is null; 'account' is the bare uuid of this account
        # 'transfer' is the bare uuid of the corresponding transaction in
        # the other account; 'category' is null (if the transfer is on-budget

        from_id_transaction = self.get_id_transaction(str(from_id))
        to_id_transaction = self.get_id_transaction(str(to_id))
        from_tr = self.get_transaction(from_id_transaction)
        to_tr = self.get_transaction(to_id_transaction)

        # setup from transaction:
        if not from_tr or '_id' not in from_tr:
            from_doc = {'_id': from_id_transaction,
                        'value': -1 * value,
                        'account': from_account_id,
                        'date': date,
                        'memo': memo,
                        'category': from_category_id,
                        'transfer': str(to_id)
                        }
            if '_rev' in from_tr:
                from_doc['_rev'] = from_tr['_rev']

            self.logger.debug('Adding from_doc', from_doc)
            from_save_output = self.cdb.save(self.user_db, from_doc)
        else:
            self.logger.warning(
                'from_transaction {0} has already been '
                'imported '.format(from_tr['_id']))
            from_save_output = None

        # setup to transaction:
        if not to_tr or '_id' not in to_tr:
            to_doc = {'_id': to_id_transaction,
                      'value': value,
                      'account': to_account_id,
                      'date': date,
                      'memo': memo,
                      'transfer': str(from_id)
                      }
            if '_rev' in to_tr:
                to_doc['_rev'] = to_tr['_rev']

            self.logger.debug('Adding to_doc', to_doc)
            to_save_output = self.cdb.save(self.user_db, to_doc)
        else:
            self.logger.warning(
                'to_transaction {0} has already been '
                'imported '.format(to_tr['_id']))
            to_save_output = None

        return from_save_output, to_save_output

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
        Find account(s) by name within the database, checking the local
        account map first. Raises a ValueError if the account is not found.

        Parameters
        ----------
        name : str
            Name for which to search (must be an exact match)
        Returns
        -------
        res : dict
            The doc dictionary of the account
        """
        if name in self.account_map:
            self.logger.info('got account ({}) '
                             'from self.account_map'.format(name))
            res = self.account_map[name]

        else:
            selector = {
                '_id': {'$regex':
                        '^{0}_account_'.format(self.budget_selector)},
                'name': name}

            try:
                # result of query is a list of dicts:
                res = self.cdb.query(self.user_db,
                                     {'selector': selector,
                                      'fields': ['_id',
                                                 'name']}).json()['docs']
                # so we need to take first value:
                res = res[0]
                res['_id'] = split_id(res['_id'])
                self.logger.info('got account ({}) '
                                 'from remote db'.format(name))
                self.account_map[name] = res
            except Exception:
                raise ValueError("Account not found")

        return res

    def find_transaction(self,
                         memo=None,
                         value=None,
                         date=None):
        """
        Find transaction(s) by memo or value within the database

        Parameters
        ----------
        memo : str
            Memo for which to search (must be an exact match)
        value : float or int
            Value for which to search in cents (must be exact match)
        date : str
            Date for which to search (YYYY-MM-DD)

        Returns
        -------
            List of transaction json objects that match the given name
        """
        selector = {
            '_id': {'$regex': '^{0}_transaction_'.format(
                self.budget_selector)}}
        if memo:
            selector['memo'] = memo
        if value:
            selector['value'] = value
        if date:
            selector['date'] = date

        return self.cdb.query(self.user_db,
                              {'selector': selector}).json()['docs']

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

    def find_category(self, name):
        """
        Find category(ies) by name within the database, checking the local
        category map first. Raises a ValueError if the category is not found.

        Parameters
        ----------
        name : str
            Name for which to search (must be an exact match)
        Returns
        -------
        res : dict
            Doc dictionary of the category with bare ``_id`` (without budget
            id) and ``name``
        """
        if name in ['income', 'incomeNextMonth']:
            self.logger.debug('*** got category ({})'.format(name))
            res = {'_id': name,
                   'name': name}

        elif name in self.category_map:
            self.logger.debug('*** got category ({}) '
                              'from self.category_map'.format(name))
            res = self.category_map[name]

        else:
            selector = {
                '_id': {'$regex':
                        '^{0}_category_'.format(self.budget_selector)},
                'name': name}
            try:
                # result of query is a list of dicts:
                res = self.cdb.query(self.user_db,
                                     {'selector': selector,
                                      'fields': ['_id',
                                                 'name']}).json()['docs']
                # so we need to take first value:
                res = res[0]
                res['_id'] = split_id(res['_id'])
                self.logger.debug('*** got category ({}) '
                                  'from remote db'.format(name))
                self.category_map[name] = res
            except Exception:
                raise ValueError("Category not found")

        return res

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
        Return id of a payee, and create one if it does not exist, adding it
        to the payee_map cache for later use

        Parameters
        ----------
        name : str
            Name of the payee to use or get

        Returns
        -------
        ret : dict
            The doc dictionary of the existing (or created) payee
        """
        # first check the cache map
        if name in self.payee_map:
            self.logger.info('Got payee ({}) from payee_map'.format(name))
            return self.payee_map[name]

        else:
            payee = self.find_payee(name)
            if payee:
                payee = payee[0]
                payee['_id'] = split_id(payee['_id'])
                self.logger.info('found payee ({}) in remote database'.format(
                    name))
                self.payee_map[name] = payee  # add to payee_map
                return payee
            else:
                payee = self.insert_payee(name)
                payee['_id'] = split_id(payee['id'])
                self.logger.info('added payee ({}) to remote database'.format(
                    name))
                self.payee_map[name] = payee  # add to payee_map
                return payee
