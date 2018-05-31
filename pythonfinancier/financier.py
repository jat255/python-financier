from pythonfinancier.easycouchdb import EasyCouchdb
import uuid


def split_id(full_id):
    return full_id.split('_')[-1]


class Financier:
    selector = {}

    def __init__(self, urlcouchdb, username, password):
        self.cdb = EasyCouchdb(urlcouchdb)
        # print(self.cdb.login(username, password).json())
        login_json = self.cdb.login(username, password).json()
        roles = login_json['roles']

        self.user_db = next(r for r in roles if r.startswith('userdb'))
        self.account_map = {}
        self.payee_map = {}
        self.budget_selector = ''
        print('Connecting on db {0}'.format(self.user_db))

    def get_all_budgets(self):
        return self.cdb.query(self.user_db,
                              {'selector': {'_id': {'$regex': '^budget_'}},
                               'fields': ['_id', 'name']}).json()['docs']

    def connect_budget(self, name):
        budget = self.find_budget(name)
        if budget:
            self.budget_selector = budget[0]['_id'].replace('budget', 'b')
            print('connecting on budget {0}'.format(self.budget_selector))
        else:
            raise Exception('Budget not found')

    def get_all_accounts(self):
        selector = {
            '_id': {'$regex': '^{0}_account_'.format(self.budget_selector)}}
        return self.cdb.query(self.user_db,
                              {'selector': selector,
                               'fields': ['_id', 'name']}).json()['docs']

    def save_transaction(self, account_name, this_id, value, date, payee_name,
                         memo):
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
        return self.cdb.get_doc(self.user_db, id_transaction).json()

    def get_id_transaction(self, this_id):
        return '{0}_transaction_{1}'.format(self.budget_selector, this_id)

    def find_budget(self, name):
        return self.cdb.query(self.user_db, {
            'selector': {'_id': {'$regex': '^budget_'}, 'name': name},
            'fields': ['_id', 'name']}).json()['docs']

    def find_account(self, name):
        selector = {
            '_id': {'$regex': '^{0}_account_'.format(self.budget_selector)},
            'name': name}
        return self.cdb.query(self.user_db,
                              {'selector': selector,
                               'fields': ['_id', 'name']}).json()['docs']

    def find_payee(self, name):
        selector = {
            '_id': {'$regex': '^{0}_payee_'.format(self.budget_selector)},
            'name': name}
        return self.cdb.query(self.user_db,
                              {'selector': selector,
                               'fields': ['_id', 'name',
                                          'categorySuggest']}).json()['docs']

    def insert_payee(self, name):
        doc = {
            '_id': '{0}_payee_{1}'.format(self.budget_selector, uuid.uuid4()),
            'name': name, 'internal': False, 'autosuggest': True}
        return self.cdb.insert(self.user_db, doc).json()

    # return a id of payee, if not exists create a new one
    def get_or_create_payee(self, name):
        payee = self.find_payee(name)
        if payee:
            return payee[0]
        else:
            ret = self.insert_payee(name)
            ret['_id'] = ret['id']
            return ret
