#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# cpso.py - copy program's dependencies (.so files)
# Copyright (C) 2017, 2019 Artur "suve" Iwicki
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License,
# either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program (LICENCE.txt). If not, see <http://www.gnu.org/licenses/>.
#

import os
import subprocess
import sys


PROGRAM_AUTHOR  = "suve"
PROGRAM_NAME    = "cpso"
PROGRAM_VERSION = "2.0"

FILE_FORMAT_ELF32 = 0
FILE_FORMAT_ELF64 = 1


def run(program, args = []):
	args.insert(0, program)
	proc = subprocess.run(args=args, capture_output=True)

	status = proc.returncode
	stdout = proc.stdout.decode("utf-8").split("\n")
	stderr = proc.stderr.decode("utf-8").split("\n")

	return status, stdout, stderr


def find_so(soname, file_format):
	if file_format == FILE_FORMAT_ELF32:
		prefixes = ["/lib/", "/usr/lib/", "/usr/local/lib/"]
	elif file_format == FILE_FORMAT_ELF64:
		prefixes = ["/lib64/", "/usr/lib64/", "/usr/local/lib64/"]
	else:
		return None

	for prefix in prefixes:
		path = prefix + soname
		if os.path.isfile(path):
			return path

	return None


def get_deps_recursive(executable, deps):
	code, output, err = run("objdump", ["-x", executable])
	if code != 0:
		print(PROGRAM_NAME + ": \"objdump\" returned an error\n" + err[0], file=sys.stderr)
		sys.exit(1)

	header = output[:5]
	output = output[5:]

	file_format = None
	for line in header:
		if " file format " not in line:
			continue

		parts = line.split(" file format ")
		format_str = parts[1]

		if format_str[:6] == "elf32-":
			file_format = FILE_FORMAT_ELF32
		elif format_str[:6] == "elf64-":
			file_format = FILE_FORMAT_ELF64
		else:
			print(PROGRAM_NAME + ": unrecognized file format \"" + format_str + "\" (file: \"" + executable + "\")", file=sys.stderr)
			sys.exit(1)

	if file_format is None:
		print(PROGRAM_NAME + ": could not determine file format for \"" + executable + "\"", file=sys.stderr)
		sys.exit(1)

	for line in output:
		if "  NEEDED  " not in line:
			continue

		parts = line.split(" ")
		so_name = parts[len(parts)-1]

		if so_name in deps:
			continue

		so_path = find_so(so_name, file_format)
		if so_path is None:
			print(PROGRAM_NAME + ": unable to resolve \"" + so_name + "\"", file=sys.stderr)
			sys.exit(1)

		deps[so_name] = so_path
		get_deps_recursive(so_path, deps)


def get_deps(executable):
	deps = {}
	get_deps_recursive(executable, deps)

	return deps


def copy_deps(deps, target_dir):
	blacklist = ["libasan.", "libc.", "libgcc_s.", "libm.", "libpthread.", "libstdc++.", "ld-linux.", "ld-linux-"]

	for key, value in deps.items():
		so_name = key
		so_path = value

		copy = True
		for blackentry in blacklist:
			if blackentry in so_name:
				copy = False
				break

		if copy:
			code, _, err = run("cp", ["--preserve=timestamps", so_path, target_dir])
			if code == 0:
				print(PROGRAM_NAME + ": \"" + so_name + "\" copied from \"" + so_path + "\"")
			else:
				print(PROGRAM_NAME + ": \"" + so_name + "\" could not be copied (" + err[0] + ")")
		else:
			print(PROGRAM_NAME + ": \"" + so_name + "\" is blacklisted, skipping")


def parse_args():
	argc = len(sys.argv)
	if argc < 2:
		print(PROGRAM_NAME + ": EXECUTABLE is missing\nUsage: cpso EXECUTABLE [TARGET-DIR]", file=sys.stderr)
		sys.exit(1)

	if sys.argv[1] == "--help":
		print(PROGRAM_NAME + " is a script for bundling the .so files needed by binary executables.\nUsage: cpso EXECUTABLE [TARGET-DIR]", file=sys.stderr)
		sys.exit(0)

	if sys.argv[1] == "--version":
		print(PROGRAM_NAME + " v." + PROGRAM_VERSION + " by " + PROGRAM_AUTHOR, file=sys.stderr)
		sys.exit(0)

	executable = sys.argv[1]
	if not os.path.isfile(executable):
		print(PROGRAM_NAME + ": File \"" + executable + "\" does not exist", file=sys.stderr)
		sys.exit(1)

	if argc >= 3:
		target_dir = sys.argv[2]
		if not os.path.isdir(target_dir):
			print(PROGRAM_NAME + ": Directory \"" + target_dir + "\" does not exist", file=sys.stderr)
			sys.exit(1)
	else:
		target_dir = os.getcwd()
	target_dir = target_dir + "/"

	return executable, target_dir


def main():
	executable, target_dir = parse_args()
	deps = get_deps(executable)
	copy_deps(deps, target_dir)


if __name__ == "__main__":
	main()
