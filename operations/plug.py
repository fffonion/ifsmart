import socket
import json
from struct import pack


# Predefined Smart Plug Commands
# For a full list of commands, consult tplink_commands.txt
payloads = {
    'info': '{"system":{"get_sysinfo":{}}}',
    'on': '{"system":{"set_relay_state":{"state":1}}}',
    'off': '{"system":{"set_relay_state":{"state":0}}}',
    'cloudinfo': '{"cnCloud":{"get_info":{}}}',
    'wlanscan': '{"netif":{"get_scaninfo":{"refresh":0}}}',
    'time': '{"time":{"get_time":{}}}',
    'schedule': '{"schedule":{"get_rules":{}}}',
    'countdown': '{"count_down":{"get_rules":{}}}',
    'antitheft': '{"anti_theft":{"get_rules":{}}}',
    'reboot': '{"system":{"reboot":{"delay":1}}}',
    'reset': '{"system":{"reset":{"delay":1}}}',
    'energy': '{"emeter":{"get_realtime":{}}}'
}

# Encryption and Decryption of TP-Link Smart Home Protocol
# XOR Autokey Cipher with starting key = 171


def encrypt(string):
    key = 171
    result = pack('>I', len(string))
    for i in string:
        a = key ^ ord(i)
        key = a
        result += chr(a)
    return result


def decrypt(string):
    key = 171
    result = ""
    for i in string:
        a = key ^ ord(i)
        key = ord(i)
        result += chr(a)
    return result

def _flip(device, payload):
    status = _do("info", device, payloads["info"])
    system = json.loads(status)
    state = system['system']['get_sysinfo']['relay_state']
    if state:
        return _do("off", device, payloads["off"])
    return _do("on", device, payloads["on"])

combinations = {
    'flip': _flip,
}

def _do(op, device, payload):
    sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_tcp.connect((device, 9999))
    sock_tcp.send(encrypt(payload))
    data = sock_tcp.recv(2048)
    sock_tcp.close()

    return decrypt(data[4:])

def call(op, device, payload=None):
    if op in combinations:
        body = combinations[op](device, payload)
        return "Received: %s" % body

    if op in payloads and not payload:
        payload = payloads[op]
    body = _do(op, device, payload)
    return "Sent: %s Received: %s" % (payload, body)
