import os
import glob

p = r'c:\Users\HP\PycharmProjects\Andd_baay\baay\migrations\0009_projet_ferme_required.py'
print('exists_before=', os.path.exists(p))
if os.path.exists(p):
    os.remove(p)
print('exists_after=', os.path.exists(p))

# Also clean __pycache__
for f in glob.glob(r'c:\Users\HP\PycharmProjects\Andd_baay\baay\migrations\__pycache__\0009*'):
    print('cache_file=', f)
