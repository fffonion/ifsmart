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

def relay_on(device):
    status = _do("info", device, payloads["info"])
    system = json.loads(status)
    state = system['system']['get_sysinfo']['relay_state']
    return state

def _do(op, device, payload):
    sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_tcp.connect((device, 9999))
    sock_tcp.send(encrypt(payload))
    data = sock_tcp.recv(2048)
    sock_tcp.close()

    return decrypt(data[4:])

def call(*addresses, **kwargs):
    ret = "op" in kwargs and kwargs["op"] == "and"
    for addr in addresses:
        now = False
        try:
            now = relay_on(addr)
        except:
            pass
        if "op" in kwargs and kwargs["op"] == "and":
            ret = ret and now
        else:
            ret = ret or now
    return ret
