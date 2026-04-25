import os, traceback
p = r'c:\Users\HP\PycharmProjects\Andd_baay\baay\migrations\0009_projet_ferme_required.py'
try:
    if os.path.exists(p):
        os.remove(p)
        print('deleted')
    else:
        print('not_found')
except Exception as e:
    print('error:', e)
    traceback.print_exc()
