import datetime

def call(*days):
    return datetime.datetime.today().weekday() in days