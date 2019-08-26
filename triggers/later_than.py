import time

def call(hh, mm):
    hh_now = int(time.strftime("%H", time.localtime(time.time())))
    mm_now = int(time.strftime("%M", time.localtime(time.time())))
    return (hh_now, mm_now) > (hh, mm)
