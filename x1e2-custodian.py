#!/usr/bin/env python3.8
# --------------------------------------------------------------------
# example.py
#
# Author: Lain Musgrove (lain.proliant@gmail.com)
# Date: Saturday January 18, 2020
#
# Distributed under terms of the MIT license.
# --------------------------------------------------------------------
from datetime import datetime
from pathlib import Path

import ansilog
import psutil
from readout import agent, gauge, sensor, sh, start, state, when

# --------------------------------------------------------------------
# Predicate syntax legend:
#
# `a>1`, `a<1`, `a>=1`, `a<=1`: gauge predicate
# `a=1`, `a=blue`: sensor predicate
# `a@b`: state predicate, a enters b state
# `a@b->c`: state predicate, a enters c state from b state
# `a@b->`: state predicate, a exits b state to any other state
#
# --------------------------------------------------------------------
MAX_FREQ = 4500000
COOLDOWN_FREQ = 3000000
BATTERY_FREQ = 1500000

log = ansilog.getLogger("x1e2-custodian")


# --------------------------------------------------------------------
class CPU:
    BASE_PATH = Path("/sys/devices/system/cpu")
    FREQ_MAX = Path("cpufreq/scaling_max_freq")

    @classmethod
    def get_all(cls):
        return (CPU(n) for n in range(psutil.cpu_count()))

    @classmethod
    def set_all_max_freq(cls, freq: int):
        for cpu in cls.get_all():
            cpu.set_max_freq(freq)

    def __init__(self, num):
        self.num = num

    def set_max_freq(self, int):
        with open(self.path() / self.FREQ_MAX, "w") as sysfile:
            sysfile.write(str(int))

    def get_max_freq(self):
        with open(self.path() / self.FREQ_MAX, "r") as sysfile:
            return int(sysfile.readline())

    def path(self):
        return self.BASE_PATH / f"cpu{self.num}"


# --------------------------------------------------------------------
@gauge()
async def cpu_freq():
    return CPU(0).get_max_freq()


# --------------------------------------------------------------------
@gauge(freq=2)
async def temp():
    return int(await sh("cat /sys/class/thermal/thermal_zone0/temp")) / 1000


# --------------------------------------------------------------------
@sensor()
async def ac_status():
    status = int(await sh("cat /sys/class/power_supply/AC/online"))
    return "on" if status == 1 else "off"


# --------------------------------------------------------------------
@sensor()
async def gpu():
    output = await sh("DISPLAY=:0 sudo -u lainproliant optimus-manager --print-mode")
    return output.split(':')[1].strip()


# --------------------------------------------------------------------
@agent()
def log_agent(temp, cpu_freq, ac_status):
    time = datetime.now().isoformat()
    log.info(f"{time=}, {temp=}, {cpu_freq=}, {ac_status=}.")


# --------------------------------------------------------------------
@when("ac_status=off", "gpu=intel")
@state("nvidia@poweroff")
async def on_nvidia_poweroff():
    await sh("/usr/bin/disable-nvidia")


# --------------------------------------------------------------------
@when("ac_status=off")
@state("power@battery")
def on_battery():
    CPU.set_all_max_freq(BATTERY_FREQ)


# --------------------------------------------------------------------
@when("ac_status=on", "temp<70")
@state("power@cool")
def on_cool():
    CPU.set_all_max_freq(MAX_FREQ)


# --------------------------------------------------------------------
@when("ac_status=on", "temp>70")
@state("power@hot")
def on_hot():
    CPU.set_all_max_freq(COOLDOWN_FREQ)


# --------------------------------------------------------------------
start()
