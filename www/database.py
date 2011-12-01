import web
import config

db = web.database(dbn='mysql', user=config.DB_USER, pw=config.DB_PASSWORD, db=config.DB_DATABASE)
