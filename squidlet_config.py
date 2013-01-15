import sys

dbdir = ''

if bkdir not in sys.path:
    sys.path.insert(0, bkdir)

DBPATH = '/u/t/cs.welcher/assemblies'
DB = DBconf(DBPATH, 'db.conf')

BLAST = '/usr/local/bin/blastall'
TEMPDIR = '/storage/project/squidlet/tmp'

SECRET_KEY = '\tD,\xb1\xd3\x89zd\x87\x8b\xb7\x9f\xf8c\x8e\x0eH\xdc\xb21\x9cY\xdcK'
DEBUG = True
PASSWORD = 'africanoreuropean?'
