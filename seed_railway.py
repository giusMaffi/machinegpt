import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:XXX@postgres.railway.internal:5432/railway'

from scripts.seed_demo import *
