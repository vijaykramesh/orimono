'''
a wrapper for writing to the log table
also sends out a comet message
'''

import web
import config
import database
import comet.client
import datetime


db = database.db

def log(logtype, logtext, logsite = None, comet_message = None, nocomet = False):
    db.insert('logs', type=logtype, text=logtext, site=logsite, datetime=datetime.datetime.now())
    if not nocomet:
        if not comet_message: comet_message = logtype
        comet.client.send('success', comet_message)
