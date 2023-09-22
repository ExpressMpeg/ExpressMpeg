import json
import os

for x in os.listdir('supported'):
    d = dict()
    with open(f'./supported/{x}', 'w') as f:
        d['ext'] = x[1:]
        d['description'] = x[1:].upper() + f' Files (*.{x[1:]})'
        json.dump(d, f)

from main import Tools


print(Tools.get_description())