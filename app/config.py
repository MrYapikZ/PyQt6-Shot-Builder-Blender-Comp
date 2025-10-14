import os

class Config:
    CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'yp-sbbc')
    CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')
    LOG_PATH = os.path.join(CONFIG_DIR, 'logs')
    os.makedirs(CONFIG_DIR, exist_ok=True)