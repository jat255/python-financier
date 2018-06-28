import logging

from pythonfinancier import Financier
from datetime import datetime
from pprint import pprint

# logging.getLogger().setLevel(logging.INFO)
financier_logger = logging.getLogger('pythonfinancier.financier')
couchdb_logger = logging.getLogger('pythonfinancier.easycouchdb')
financier_logger.setLevel(logging.DEBUG)
couchdb_logger.setLevel(logging.DEBUG)
logging.info('Get logging setup')

f = Financier(conf_file='my_financier.ini')
f.connect_budget('test_budget')


# f.connect_budget('Our Finances')
# pprint(f.find_transaction(value=200000, date='2018-05-26'))
# pprint(f.find_transaction(value=-200000, date='2018-05-26'))

today = datetime.now().strftime('%Y-%m-%d')


def test_saving():
    # shouldn't do any query for income category:
    f.save_transaction(account_name='Test from python',
                       category_name='income',
                       value=20000,
                       date=today,
                       payee_name='Payee1',
                       memo='Christmas memo')

    # should query remote db for category id:
    f.save_transaction(account_name='Test from python',
                       category_name='Christmas',
                       value=-5000,
                       date=today,
                       payee_name='Payee2',
                       memo='Christmas memo')

    # should get category from map:
    f.save_transaction(account_name='Test from python',
                       category_name='Christmas',
                       value=-5000,
                       date=today,
                       payee_name='Payee3',
                       memo='Christmas memo')

    # should get category and payee from map:
    f.save_transaction(account_name='Test from python',
                       category_name='Rent/Mortgage',
                       value=-5000,
                       date=today,
                       payee_name='Payee1',
                       memo='Christmas memo')


def test_splits():
    # each dict in the list must have keys [value, category_name, memo,
    # payee_name]
    split_transactions = [{'value':10000,
                           'payee_name': 'split_payee1',
                           'category_name': 'Rent/Mortgage',
                           'memo': 'split 1/3'},
                          {'value': 5000,
                           'payee_name': 'split_payee2',
                           'category_name': 'Clothing',
                           'memo': 'split 2/3'},
                          {'value': 3000,
                           'payee_name': 'split_payee1',
                           'category_name': 'incomeNextMonth',
                           'memo': 'split 3/3'}]

    f.save_split(account_name='Test from python',
                 payee_name='Payee1',
                 value=20000,
                 date=today,
                 memo='testing splits',
                 transactions=split_transactions)


def test_transfer():
    from_acct = 'account1'
    to_acct = 'account2'

    # f.save_transfer(from_acct,
    #                 to_acct,
    #                 900,
    #                 today,
    #                 'test memo',
    #                 from_category_name='Rent/Mortgage')

    f.save_transfer(from_acct,
                    'Test from python',
                    10000,
                    today,
                    'test memo',
                    from_category_name='Rent/Mortgage')


test_transfer()
