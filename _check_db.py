import os
print('DB:', 'SET' if os.environ.get('DATABASE_URL') else 'NOT_SET')
