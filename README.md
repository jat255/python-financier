---------
Python Module for managing [financier](https://financier.io/)

DISCLAIMER: not a official API from financier
============

That module allows you insert transactions and payee on financier.

Install
------------------
```console
$ pip install python-financier
```

AUTHENTICATION
--------------
Modify the file `python-financier.ini` to include your username and
password in the appropriate places. The `url_couch_db` parameter should
correct, but can be changed if your database is located elsewhere.
The configuration file should be in the directory from which you run the
code (or your script). Alternatively, the path to the file can be
supplied.

If you would rather authenticate manually each time, just
supply the appropriate values in the constructor for the `Financier`
class.


USAGE
----------------

```python
from pythonfinancier import Financier
import uuid

# If using the default config file location:
f = Financier()

# Using a custom config file location:
f = Financier(conf_file='/home/user/financier.ini')

# If authenticating manually:
f = Financier(url_couch_db='https://app.financier.io/db/',
              username=EMAIL,
              password=PASSWORD)

f.connect_budget('Personal')

f.save_transaction('nubank',
                   uuid.uuid4(),
                   400,
                   '2017-10-10',
                   'Carrefour',
                   'teste memo') #acount, id, value, date, payee, memo

```

Notes: 
- If payee doesn't exists, it will create a new one.
- That script will use the suggest_category on payee, so will automatically import transactions using the previously category set for thath payee

FINDING ALL BUDGETS AVAILABLE
----------------


```python
from pythonfinancier.financier import Financier

f = Financier('https://app.financier.io/db/', EMAIL, PASSWORD)

print(f.get_all_budgets())


```

**ENJOY!!**
