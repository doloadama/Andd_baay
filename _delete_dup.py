import os
p = r'c:\Users\HP\PycharmProjects\Andd_baay\baay\migrations\0009_projet_ferme_required.py'
print('exists', os.path.exists(p))
if os.path.exists(p):
    os.remove(p)
    print('removed', not os.path.exists(p))
