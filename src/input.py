'''
Copyright 2024 ITProjects
Copyright 2012 Joakim Fors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import json
import logging
import os
import re
import gc
import subprocess
from os.path import basename
from subprocess import CalledProcessError

import numpy as np

from .utils import find_bin

log = logging.getLogger(__package__)

ffprobe_bin = None # FFPROBE binary location
ffmpeg_bin = None # FFMPEG binary location
file_information = None # temporary metadata storage


def load_file(infile, inbuffer=None):
    convs = {
        8: {'format': 's8', 'codec': 'pcm_s8', 'dtype': np.dtype('i1')},
        16: {'format': 's16le', 'codec': 'pcm_s16le', 'dtype': np.dtype('<i2')},
        24: {'format': 's32le', 'codec': 'pcm_s32le', 'dtype': np.dtype('<i4')},
        32: {'format': 's32le', 'codec': 'pcm_s32le', 'dtype': np.dtype('<i4')},
    }
    size = -1
    name = os.path.splitext(basename(infile))[0]
    ext = os.path.splitext(infile)[1][1:].strip().lower()
    fmt = None
    title = None
    artist = None
    date = None
    album = None
    track = None
    bps = 1411000
    bits = 16
    cl = None

    global ffprobe_bin
    global ffmpeg_bin

    if ffprobe_bin == None or ffmpeg_bin == None:
        ffprobe_bin, ffmpeg_bin = find_bin('ffprobe', 'ffmpeg')
        if not ffprobe_bin:
            log.warning("ffprobe not found")
            return 1
        if not ffmpeg_bin:
            log.warning("ffmpeg not found")
            return 1

    log.info("Probing file")
    _infile = infile
    if inbuffer:
        _infile = '-'
    try:
        ffprobe = subprocess.Popen(
            [
                ffprobe_bin,
                '-of',
                'json',
                '-show_format',
                '-show_streams',
                '-select_streams',
                'a',
                _infile,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        output, error = ffprobe.communicate(inbuffer)
        log.debug(output)
    except CalledProcessError as e:
        log.warning('Could not probe %s')
        return e.returncode
    if ffprobe.returncode > 0:
        log.warning("Failed to probe file %s", infile)
        log.debug(error)
        return ffprobe.returncode
    probe = json.loads(output)

    # Parse and clarify json.
    global file_information
    file_information = []
    print_values(probe)
    output_save_txt = '\n'.join(file_information) # raw ffmpeg track metadata
    file_information = []

    if 'streams' not in probe:
        log.warning("No streams found in %s", infile)
        return 2
    if not probe['streams']:
        log.warning("No audio stream found in %s", infile)
        return 2
    container = probe['format']
    stream = probe['streams'][0]
    if 'tags' in container:
        tags = {k.lower(): v for k, v in container['tags'].items()}
    else:
        tags = {}
    if 'size' in container:
        size = int(container['size'])
    if 'format_name' in container:
        fmts = container['format_name'].split(',')
        if ext in fmts:
            fmt = ext
        else:
            fmt = fmts[0]
    if 'bit_rate' in container:
        bps = int(container['bit_rate'])
    if 'bit_rate' in stream:
        bps = int(stream['bit_rate'])
    if 'duration_ts' in stream:
        ns = int(stream['duration_ts'])
    if 'sample_rate' in stream:
        fs = int(stream['sample_rate'])
    if 'channels' in stream:
        nc = stream['channels']
    if 'channel_layout' in stream:
        cl = stream['channel_layout']
    if 'bits_per_raw_sample' in stream:
        bits = int(stream['bits_per_raw_sample'])
    if 'bits_per_sample' in stream and int(stream['bits_per_sample']) > 0:
        bits = int(stream['bits_per_sample'])
    if 'duration' in stream:
        sec = float(stream['duration'])
    if 'codec_name' in stream:
        enc = stream['codec_name']
        if 'pcm_' == enc[0:4]:
            enc = fmt
    if 'artist' in tags:
        artist = tags['artist']
    if 'title' in tags:
        title = tags['title']
    if 'album' in tags:
        album = tags['album']
    if 'track' in tags:
        track = int(tags['track'].split('/')[0])
    if 'date' in tags:
        date = tags['date']
    conv = convs[bits]
    log.info("Converting using ffmpeg")
    command = [
        ffmpeg_bin,
        '-y',
        '-i',
        _infile,
        '-vn',
        '-f',
        conv['format'],
        '-acodec',
        conv['codec'],
        '-flags',
        'bitexact',
        '-',
    ]
    try:
        ffmpeg = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        outbuf, error = ffmpeg.communicate(inbuffer)
        log.debug(error)
    except CalledProcessError as e:
        log.warning('Could not convert %s', infile)
        return e.returncode
    raw_data = np.frombuffer(outbuf, dtype=conv['dtype'])
    del outbuf # clean
    gc.collect() # free RAM
    raw_data = raw_data.reshape((nc, -1), order='F').copy(order='C')
    log.debug(raw_data.shape)
    ns = raw_data[0].shape[0]
    sec = ns / float(fs)
    if bits == 24:
        raw_data //= 2**8
    data = raw_data.astype('float')
    data /= 2 ** (bits - 1)
    if not fmt:
        fmt = ext
    if artist and title:
        name = '%s - %s' % (artist, title)
    output = {
        'data': {'fixed': raw_data, 'float': data},
        'samples': ns,
        'samplerate': fs,
        'channels': nc,
        'channel_layout': cl,
        'bitdepth': bits,
        'duration': sec,
        'format': fmt,
        'metadata': {
            'size': size,
            'filename': basename(infile),
            'extension': ext,
            'encoding': enc,
            'name': name,
            'artist': artist,
            'title': title,
            'album': album,
            'track': track,
            'date': date,
            'bps': bps,
        },
        'raw_meta': output_save_txt
    }
    return output


def file_formats():
    foo = re.compile(r'\s+DE?\s+(\S+)\s+\S+')
    formats = []
    try:
        result = subprocess.check_output(
            ['ffprobe', '-v', 'quiet', '-formats'], stderr=subprocess.STDOUT, text=True
        )
    except CalledProcessError as e:
        log.debug(e)
        return formats
    for line in result.split('\n')[4:]:  # skip preamble
        bar = foo.match(line)
        if bar:
            formats += bar.group(1).split(',')
    for foo in ['mjpeg', 'gif', 'vobsub']:
        if foo in formats:
            formats.remove(foo)
    return formats

# Format json audio file metadata.
def print_values(obj, indent=0):
    global file_information
    if isinstance(obj, dict):
        for key, value in obj.items():
            file_information.append(' ' * indent + f'{key}:')
            print_values(value, indent + 8)
    elif isinstance(obj, list):
        for item in obj:
            print_values(item, indent)
    else:
        file_information.append(' ' * indent + str(obj))
