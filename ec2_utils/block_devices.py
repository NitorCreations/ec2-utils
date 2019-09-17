from glob import glob

def linux_block_devices():
    for device_size in glob("/sys/block/*/size"):
        with open(device_size, "r") as sf:
            yield device_size.split("/")[3], int(sf.readlines()[0]) * 512

def linux_block_devices_largest_first():
    devs = [dev for dev in linux_block_devices()]
    devs.sort(key = lambda dev: dev[1], reverse=True)
    return devs

def linux_unmounted_block_devices():
    for dev in linux_block_devices():
        if not linux_is_dev_mounted(dev[0]):
            yield dev

def linux_unmounted_block_devices_largest_first():
    devs = [dev for dev in linux_unmounted_block_devices()]
    devs.sort(key = lambda dev: dev[1], reverse=True)
    return devs

def linux_is_dev_mounted(device):
    with open("/proc/mounts", "r") as mounts:
        for mount in mounts.readlines():
            if mount.startswith(("/dev/" + device)):
                return True
    return False