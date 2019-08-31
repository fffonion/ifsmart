import time
from scapy.all import AsyncSniffer
from scapy.layers.dhcp import DHCP
from scapy.layers.l2 import Ether

import gevent

conditions = {}

def register(f, *args):
    for c in args:
        c = c.lower()
        if c not in conditions:
            conditions[c] = [f]
        else:
            conditions[c].append(f)

anti_flood = {}
flood_interval = 2

def detect_button(pkt):
    if pkt.haslayer(DHCP):
        mac = pkt[Ether].src.lower()
        if mac in conditions:
            if mac not in anti_flood or time.time() - anti_flood[mac] > flood_interval:
                for f in conditions[mac]:
                    f()
            anti_flood[mac] = time.time()
    gevent.sleep(0)

AsyncSniffer(prn=detect_button, filter="(udp and (port 67 or 68))", store=0).start()