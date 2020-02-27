#!/usr/bin/env python
# --------------------------------------------------------------------
# bake.py
#
# Author: Lain Musgrove (lain.proliant@gmail.com)
# Date: Tuesday February 11, 2020
#
# Distributed under terms of the MIT license.
# --------------------------------------------------------------------
from pathlib import Path

from panifex import build, default, sh, seq
from panifex.errors import BuildError
from panifex.recipes import Recipe, FileRecipe

# --------------------------------------------------------------------
class InstallFile(FileRecipe):
    def __init__(self, src, dst, user=None, group=None, chmod=644):
        super().__init__()
        self.src = Path(src)
        self.dst = Path(dst)
        self.chmod = chmod
        self.user = user
        self.group = None

    async def _resolve(self):
        flags = ["-Dm{chmod}"]

        if self.user is not None:
            flags.append("-o{user}")

        if self.group is not None:
            flags.append("-g{group}")

        if (
            not sh(
                ["sudo", "install", *flags, "{src}", "{dst}"],
                chmod=self.chmod,
                user=self.user,
                group=self.group,
                src=self.src,
                dst=self.dst,
            )
            .interactive()
            .sync()
            .succeeded()
        ):
            raise BuildError("Failed to install file.")

    async def _clean(self):
        if not self.output().exists():
            return

        if (
            not sh("sudo rm {dst}", dst=self.dst)
            .interactive()
            .no_echo()
            .sync()
            .succeeded()
        ):
            raise BuildError("Failed to delete installed file.")

    def input(self):
        return self.src

    def output(self):
        return self.dst

# --------------------------------------------------------------------
@build
class Custodian:
    def install_service_file(self):
        return InstallFile(
            "x1e2-custodian.service",
            "/etc/systemd/system/x1e2-custodian.service",
            chmod=444
        )

    def install_executable(self, install_service_file):
        return InstallFile(
            "x1e2-custodian.py",
            "/usr/sbin/x1e2-custodian.py",
            chmod=555
        )

    @default
    def enable_service(self, install_executable):
        if Recipe.cleaning:
            sh("sudo systemctl stop x1e2-custodian").interactive().sync()
            sh("sudo systemctl disable x1e2-custodian").interactive().sync()
        else:
            sh("sudo systemctl enable x1e2-custodian").interactive().sync()
            sh("sudo systemctl start x1e2-custodian").interactive().sync()
