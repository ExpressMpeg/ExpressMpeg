"""Config file manager for ExpressMpeg"""

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon
from json import load

with open('config.json', 'r') as f:
    data = load(f)

# MainWindow settings
WIN_SIZE = QSize(data['WIN_SIZE'][0], data['WIN_SIZE'][1])  # Size of the window
FAV_ICON = QIcon(data['FAV_ICON'])                          # Icon of the window

# Ouput folder location
OUTPUT_FOLDER = data['OUTPUT_FOLDER']

# Number of files processed at the same time
# This is called a Semaphore in asyncronious systems
SEMAPHORE = data['SEMAPHORE']

# Help URL
HELP_URL = data['HELP_URL']
