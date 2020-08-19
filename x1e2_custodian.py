#!/usr/bin/env python3.8
# --------------------------------------------------------------------
# x1e2_custodian.py
#
# Author: Lain Musgrove (lain.proliant@gmail.com)
# Date: Saturday January 18, 2020
#
# Distributed under terms of the MIT license.
# --------------------------------------------------------------------
from datetime import datetime
from pathlib import Path

import ansilog
import click
import json
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
CONFIG_DEFAULTS = {
    'cooldown_freq': 2000000,
    'battery_freq': 1500000,
    'max_freq': 9999999,
    'hot_threshold': 90,
    'cool_threshold': 70,
    'cpu_base_path': '/sys/devices/system/cpu',
    'cpu_freq_max_path': 'cpufreq/scaling_max_freq',
    'temperature_path': '/sys/class/thermal/thermal_zone0/temp',
    'ac_status_path': '/sys/class/power_supply/AC/online',
    'kill_nvidia_on_battery': False,
    'nvidia_kill_command': '/usr/bin/disable-nvidia'
}


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
@click.group()
@click.option('-c', '--config', 'config_filename', default="/etc/x1e2-custodian.json")
@click.pass_context
def cli(ctx: click.Context, config_filename: str):
    config_file = Path(config_filename)
    if not config_file.exists():
        log.warning("Missing config file at {}, using defaults...".format(config_file))
        ctx.obj = CONFIG_DEFAULTS
    else:
        with open(config_file, 'r') as infile:
            ctx.obj = json.load(infile)


# --------------------------------------------------------------------
@cli.command()
@click.pass_context
def config(ctx: click.Context):
    """ Dump the current configuration as JSON. """
    print(json.dumps(ctx.obj, indent=4))


# --------------------------------------------------------------------
@cli.command()
@click.argument('speed', default=-1.0)
@click.option('-C', '--cpu', 'cpuspec', default='all')
@click.pass_context
def freq(ctx: click.Context, speed: int, cpuspec: str):
    """ Print or set the max CPU frequency in GHz. """
    if cpuspec == 'all':
        cpus = [*CPU.get_all()]
    else:
        cpus = [CPU(int(x)) for x in cpuspec.split(',')]

    if speed == -1:
        for cpu in cpus:
            print("%2d: %.2f" % (cpu.num, cpu.get_max_freq() / 1000000))
    else:
        for cpu in cpus:
            cpu.set_max_freq(int(speed * 1000000))
        log.info("Set max frequency to %.2fGHz.", cpus[0].get_max_freq() / 1000000)






# --------------------------------------------------------------------
@cli.command()
@click.pass_context
def daemon(ctx: click.Context):
    """ Runs the custodian daemon.  Automatically adjusts CPU frequency to
    prefer temperatures in a range defined by the settings. """
    @gauge()
    async def cpu_freq():
        return CPU(0).get_max_freq()

    @gauge(freq=2)
    async def temp():
        return int(await sh("cat /sys/class/thermal/thermal_zone0/temp")) / 1000

    @sensor()
    async def ac_status():
        status = int(await sh("cat /sys/class/power_supply/AC/online"))
        return "on" if status == 1 else "off"

    @sensor()
    async def gpu():
        output = await sh(
            "DISPLAY=:0 sudo -u lainproliant optimus-manager --print-mode"
        )
        return output.split(":")[1].strip()

    @agent()
    def log_agent(temp, cpu_freq, ac_status):
        time = datetime.now().isoformat()
        log.info(f"{time=}, {temp=}, {cpu_freq=}, {ac_status=}.")

    if ctx.obj['kill_nvidia_on_battery']:
        @when("ac_status=off", "gpu=intel")
        @state("nvidia@poweroff")
        async def on_nvidia_poweroff():
            await sh("/usr/bin/disable-nvidia")

    @when("ac_status=off")
    @state("power@battery")
    def on_battery():
        CPU.set_all_max_freq(ctx.obj['battery_freq'])

    @when("ac_status=on", "temp<{}".format(ctx.obj['cool_threshold']))
    @state("power@cool")
    def on_cool():
        CPU.set_all_max_freq(ctx.obj['max_freq'])

    @when("ac_status=on", "temp>{}".format(ctx.obj['hot_threshold']))
    @state("power@hot")
    def on_hot():
        CPU.set_all_max_freq(ctx.obj['cooldown_freq'])

    start()


# --------------------------------------------------------------------
def main():
    # pylint: disable=E1120
    cli()


# --------------------------------------------------------------------
if __name__ == "__main__":
    main()
