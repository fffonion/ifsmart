import subprocess

def call(*addresses, **kwargs):
    ret = "op" in kwargs and kwargs["op"] == "and"
    for addr in addresses:
        now = False
        try:
            r = subprocess.check_output('ping %s -W1 -c4 2>&1' % addr, shell=True)
            # pylint: disable=unsupported-membership-test
            now = "0% packet loss" in r  
        except:
            pass
        if "op" in kwargs and kwargs["op"] == "and":
            ret = ret and now
        else:
            ret = ret or now
    return ret
