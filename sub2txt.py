#!/usr/bin/env python3

#     sub2srt  - Convert subtitles from microdvd or subrip ".sub" to subviewer ".srt" format
#    (c) 2003-2005 Roland "Robelix" Obermayer <roland@robelix.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
import re
import sys
import subprocess
from tempfile import NamedTemporaryFile
from getopt import getopt, GetoptError

version = "0.5.5"

def help():
    print(__doc__)
    sys.exit(2)

def license():
    print(__license__)
    sys.exit(2)

def version():
    print(f"sub2srt {version}")
    sys.exit(2)

def convert_encoding(input_file, output_file, from_encoding, to_encoding):
    with NamedTemporaryFile(delete=False) as tmp_file:
        subprocess.run(["iconv", "-f", from_encoding, "-t", to_encoding, input_file, "-o", tmp_file.name])
        os.rename(tmp_file.name, output_file)

def detect_format(file):
    with open(file, "r", encoding="ISO-8859-1") as f:
        lines = f.readlines()

    if len(lines) < 3:
        return None

    line1 = lines[0].strip()
    line2 = lines[1].strip()
    line3 = lines[2].strip()

    if re.match(r'^\{\d+\}\{\d+\}.+$', line1):
        if re.match(r'^\{\d+\}\{\d+\}.+$', line2):
            return "microdvd"

    if re.match(r'^\[\d+\]\[\d+\].+$', line1):
        if re.match(r'^\[\d+\]\[\d+\].+$', line2):
            return "mpl2"

    if re.match(r'^\d?\d:\d?\d:\d?\d:.+$', line1):
        if re.match(r'^\d?\d:\d?\d:\d?\d:.+$', line2):
            return "tmp"

    if re.match(r'^\d\d:\d\d:\d\d\.\d\d,\d\d:\d\d:\d\d\.\d\d$', line1):
        if re.match(r'^.+$', line2) and re.match(r'^\s*$', line3) and re.match(r'^\d\d:\d\d:\d\d\.\d\d,\d\d:\d\d:\d\d\.\d\d$', lines[3]):
            return "subrip"

    if re.match(r'^\[\d\d:\d\d:\d\d(\.\d\d\d)?\]$', line1):
        if line2 != "" and re.match(r'^\[\d\d:\d\d:\d\d(\.\d\d\d)?\]$', line3):
            return "txtsub"

    if re.match(r'^\d\d:\d\d:\d\d\,\d\d\d\s-->\s\d\d:\d\d:\d\d\,\d\d\d$', line1):
        return "srt"

    return None

def main(argv):
    input_file = ""
    output_file = ""
    fps = 25
    show_version = False
    debug = False
    quiet = False
    dos = False
    license = False
    ntsc = False
    ntsc24 = False
    force = False
    convert = False
    from_encoding = "ISO-8859-1"
    to_encoding = "UTF-8"

    try:
        opts, args = getopt(argv, "hvf:ndlcq", ["help", "version", "fps=", "ntsc", "ntsc24", "debug", "license", "dos", "quiet", "force", "convert", "fenc=", "tenc="])
    except GetoptError:
        help()

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            help()
        elif opt in ("-v", "--version"):
            show_version = True
        elif opt in ("-f", "--fps"):
            fps = float(arg)
        elif opt in ("-n", "--ntsc"):
            fps = 29.97
        elif opt in ("-n2", "--ntsc24"):
            fps = 23.976
        elif opt in ("-d", "--debug"):
            debug = True
        elif opt in ("-l", "--license"):
            license = True
        elif opt in ("-c", "--convert"):
            convert = True
        elif opt in ("-q", "--quiet"):
            quiet = True
            debug = False
        elif opt in ("--dos"):
            dos = True
        elif opt in ("--force"):
            force = True
        elif opt in ("--fenc"):
            from_encoding = arg
        elif opt in ("--tenc"):
            to_encoding = arg

    if show_version:
        version()

    if license:
        license()

    if len(args) < 1:
        help()

    input_file = args[0]

    if not os.path.isfile(input_file):
        print(f"Input file {input_file} does not exist.")
        sys.exit(0)

    if len(args) > 1:
        output_file = args[1]
    else:
        output_file = os.path.splitext(input_file)[0] + ".srt"

    if os.path.isfile(output_file) and not force:
        while True:
            overwrite = input("File \"{}\" already exists. Overwrite? <y/n> ".format(output_file))
            if overwrite.lower() in ("y", "n"):
                break
        if overwrite.lower() != "y":
            sys.exit(0)

    format = detect_format(input_file)
    if not format:
        print("Could not detect {} format!".format(input_file))
        sys.exit(0)

    if debug:
        print(f"Input-file:  {input_file}")
        print(f"Output-file: {output_file}")
        print(f"Converting from {format} to srt")

    with open(input_file, "r", encoding=from_encoding) as infile, open(output_file, "w", encoding=to_encoding) as outfile:
        if format == "subrip":
            conv_subrip(infile, outfile)
        elif format == "microdvd":
            conv_microdvd(infile, outfile, fps)
        elif format == "txtsub":
            conv_txtsub(infile, outfile)
        elif format == "mpl2":
            conv_mpl2(infile, outfile)
        elif format == "tmp":
            conv_tmp(infile, outfile)
        elif format == "srt":
            print("Input file is already subviewer srt format.")

    if convert:
        convert_encoding(output_file, output_file, from_encoding, to_encoding)

if __name__ == "__main__":
    main(sys.argv[1:])python
# subrip conversion function
def conv_subrip(infile, outfile):
    converted = 0
    failed = 0

    for line in infile:
        line = line.strip()
        if re.match(r'^\d\d:\d\d:\d\d\.\d\d,\d\d:\d\d:\d\d\.\d\d$', line):
            start_time, end_time = line.split(",")
            start_time = re.sub(r'\.(\d\d)$', r",\100", start_time)
            end_time = re.sub(r'\.(\d\d)$', r",\100", end_time)
            text = next(infile).strip()
            empty = next(infile).strip()

            converted += 1

            if debug:
                print(f"  Subtitle #{converted}: start: {start_time}, end: {end_time}, Text: {text}")

            # convert line-ends
            text = text.replace("[br]", "\n")

            write_srt(outfile, converted, start_time, end_time, text)
        else:
            if not converted:
                if debug:
                    print(f"  Header line: {line} ignored")
            else:
                failed += 1
                if debug:
                    print(f"  failed to convert: {line}")

    if not quiet:
        print(f"{converted} subtitles written")
        if failed:
            print(f"{failed} lines failed")python
# microdvd conversion function
def conv_microdvd(infile, outfile, fps):
    converted = 0
    failed = 0

    for line in infile:
        line = line.strip()
        if re.match(r'^\{\d+\}\{\d+\}(.+)$', line):
            start_frame, end_frame, text = re.match(r'^\{\d+\}\{\d+\}(.+)$', line).groups()
            start_time = frames_2_time(int(start_frame), fps)
            end_time = frames_2_time(int(end_frame), fps)

            converted += 1

            if debug:
                print(f"  Subtitle #{converted}: start: {start_time}, end: {end_time}, Text: {text}")

            # convert line-ends
            text = text.replace("|", "\n")

            write_srt(outfile, converted, start_time, end_time, text)
        else:
            failed += 1
            if debug:
                print(f"  failed to convert: {line}")

    if not quiet:
        print(f"{converted} subtitles written")
        if failed:
            print(f"{failed} lines failed")python
# txtsub conversion function
def conv_txtsub(infile, outfile):
    converted = 0
    failed = 0
    start_time = ""

    for line in infile:
        line = line.strip()

        if re.match(r'^\[(\d\d:\d\d:\d\d)\.?(\d\d\d)?\]$', line):
            start_time = line[1:-1]
            if re.match(r'\d\d\d$', start_time):
                start_time += "000"
            else:
                start_time += ",000"
        else:
            text = line

            line = next(infile).strip()
            if re.match(r'^\[(\d\d:\d\d:\d\d)\.?(\d\d\d)?\]$', line):
                end_time = line[1:-1]
                if re.match(r'\d\d\d$', end_time):
                    end_time += "000"
                else:
                    end_time += ",000"

                # ignore if text is empty
                if text:
                    converted += 1

                    if debug:
                        print(f"  Subtitle #{converted}: start: {start_time}, end: {end_time}, Text: {text}")

                    # convert line-ends
                    text = text.replace("|", "\n")
                    text = text.replace("[br]", "\n")

                    write_srt(outfile, converted, start_time, end_time, text)

                start_time = end_time
            else:
                if not converted:
                    if debug:
                        print(f"  Header line: {line} ignored")
                else:
                    failed += 1
                    if debug:
                        print(f"  failed to convert: {line}")python
# mpl2 conversion function
def conv_mpl2(infile, outfile):
    converted = 0
    failed = 0

    for line in infile:
        line = line.strip()
        if re.match(r'^\[(\d+)\]\[(\d+)\](.+)$', line):
            start_time = seconds_2_time(int(float(line[1:-1].split("][")[0]) / 10))
            end_time = seconds_2_time(int(float(line[1:-1].split("][")[1]) / 10))
            text = line.split("][")[2]

            converted += 1

            if debug:
                print(f"  Subtitle #{converted}: start: {start_time}, end: {end_time}, Text: {text}")

            # convert line-ends
            text = text.replace("|", "\n")

            write_srt(outfile, converted, start_time, end_time, text)
        else:
            failed += 1
            if debug:
                print(f"  failed to convert: {line}")

    if not quiet:
        print(f"{converted} subtitles written")
        if failed:
            print(f"{failed} lines failed")python
# tmp conversion function
def conv_tmp(infile, outfile):
    converted = 0
    failed = 0

    for line in infile:
        line = line.strip()
        if re.match(r'^(\d?\d):(\d?\d):(\d?\d):(.+)$', line):
            text = line.split(":")[-1]
            hh, mm, ss = map(int, line.split(":")[:3])
            start_time = f"{hh:02d}:{mm:02d}:{ss:02d},000"
            start_time_sec = hh * 3600 + mm * 60 + ss
            end_time_sec = get_tmp_endtime(start_time_sec, len(text))
            end_time = seconds_2_time(end_time_sec)

            converted += 1

            if debug:
                print(f"  Subtitle #{converted}: start: {start_time} end: {end_time}, Text: {text}")

            # convert line-ends
            text = text.replace("|", "\n")

            write_srt(outfile, converted, start_time, end_time, text)
        else:
            failed += 1
            if debug:
                print(f"  failed to convert: {line}")

    if not quiet:
        print(f"{converted} subtitles written")
        if failed:
            print(f"{failed} lines failed")python
# function to write srt format
def write_srt(outfile, nr, start, end, text):
    print(f"{nr}\n{start} --> {end}\n{text}\n\n", file=outfile)python
# function to convert frames to time
def frames_2_time(frames, fps):
    seconds = frames / fps
    ms = int((seconds - int(seconds)) * 1000)
    if ms % 2 == 1:
        ms += 1
    return f"{int(seconds):02d}:{int((seconds % 1) * 60):02d}:{ms:03d}"python
# function to convert seconds to time
def seconds_2_time(seconds):
    s = int(seconds % 60)
    m = int((seconds // 60) % 60)
    h = int(seconds // 3600)
    return f"{h:02d}:{m:02d}:{s:02d}"python
# function to get tmp end time
def get_tmp_endtime(start_time, length, max_duration=99999999999999999999):
    duration = ((30 / (length + 8.8)) - 150) / (length + 8.8) + 17
    end_time = start_time + duration

    if end_time > max_duration:
        end_time = max_duration - 1

    if debug:
        print(f"  StartTime: {start_time:.3f}; TextLength: {length}; NextStartTime: {max_duration:.3f}; Duration: {duration:.3f}; EndTime: {end_time:.3f}")

    return end_timepython
# license text
__license__ = """
    sub2srt $version - Convert subtitles from .sub to .srt format
    (c) 2003 Roland "Robelix" Obermayer <roland@robelix.com>
    Project Homepage: http://www.robelix.com/sub2srt/
    Please report problems, ideas, patches... to sub2srt@robelix.com


    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

    Perl to Python conversion done using https://www.codeconvert.ai/ mail to "Saurabh" <saurabh.gayali@gmail.com>
"""

