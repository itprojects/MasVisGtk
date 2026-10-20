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


import logging

import numpy as np
import gc, json, os, re, subprocess
from os.path import basename
from subprocess import CalledProcessError

import gi
from gi.repository import Gio

# GStreamer imported once, not strictly required.
gst_is_installed = False
try:
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstPbutils', '1.0')
    from gi.repository import Gio, Gst, GstPbutils
    Gst.init(None) # Init Gst once.
except Exception:
    gst_is_installed = False
else: # no errors
    gst_is_installed = True

from .utils import find_bin

log = logging.getLogger(__package__)

ffprobe_bin = None # FFPROBE binary location
ffmpeg_bin = None # FFMPEG binary location

d = None # GstPbutils.Discoverer

pipeline_is_prepared = False

# Audio file bit depth.
file_bit_depth = None

# Metadata storage for menu item.
file_information = None

# GStreamer pipeline.
pipeline = None
filesrc = None
decodebin = None
audioconvert = None
appsink = None

# Hold audio bytes, must clear later.
outbuf = None

# Format to convert GStreamer audio to. Make float into int (F32LE -> S32LE).
# [GstAudio.AudioFormat.S24_32, 8-bit padding to 32 bits]
# S8, S16LE, S24_32LE, S24LE, S32LE
decodebin_format = None

convs_ffmpeg = {
    8: {'format': 's8', 'codec': 'pcm_s8', 'dtype': np.dtype('i1')},
    16: {'format': 's16le', 'codec': 'pcm_s16le', 'dtype': np.dtype('<i2')},
    24: {'format': 's32le', 'codec': 'pcm_s32le', 'dtype': np.dtype('<i4')},
    32: {'format': 's32le', 'codec': 'pcm_s32le', 'dtype': np.dtype('<i4')},
}

# gstreamer.freedesktop.org/documentation/audio/audio-format.html
convs_gst = {
    8: {'format': 'S8', 'dtype': np.dtype('i1')},
    16: {'format': 'S16LE', 'dtype': np.dtype('<i2')},
    24: {'format': 'S32LE', 'dtype': np.dtype('<i4')},
    32: {'format': 'S32LE', 'dtype': np.dtype('<i4')},
}


def load_file(infile, inbuffer=None, processing_with_gst=False):
    size = -1
    name_ = os.path.splitext(basename(infile))[0]
    ext = os.path.splitext(infile)[1][1:].strip().lower()
    enc = None
    fmt = None
    title = None
    artist = None
    date = None
    album = None
    track = None
    bps = 0
    bits = 16
    cl = None

    global gst_is_installed
    global outbuf
    global file_information

    log.info('Probing file')
    probe = None # json object
    if gst_is_installed and processing_with_gst:
        probe = gst_probe(infile)
        if isinstance(probe, int):
            return 1 # errors
    else: # FFMPEG
        global ffprobe_bin
        global ffmpeg_bin
        if ffprobe_bin == None or ffmpeg_bin == None:
            ffprobe_bin, ffmpeg_bin = find_bin('ffprobe', 'ffmpeg')
            if not ffprobe_bin:
                log.warning('ffprobe not found')
                return 1
            if not ffmpeg_bin:
                log.warning('ffmpeg not found')
                return 1
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
            log.warning('Failed to probe file ' + infile)
            log.debug(error)
            return ffprobe.returncode
        probe = json.loads(output)

    # Parse and save json in memory.
    file_information = []

    parse_values(probe)

    output_save_txt = '\n'.join(file_information) # raw ffmpeg track metadata
    file_information = []

    if 'streams' not in probe:
        log.warning('No streams found in '+ infile)
        return 2
    if not probe['streams']:
        log.warning('No audio stream found in ', infile)
        return 2
    container = probe['format']
    stream = probe['streams'][0]

    if 'tags' in container:
        tags = {k.lower(): v for k, v in container['tags'].items()}
    else:
        tags = {}
    if 'size' in container:
        size = int(container['size'])
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
    if 'artist' in tags:
        artist = tags['artist']
    if 'title' in tags:
        title = tags['title']
    if 'album' in tags:
        album = tags['album']
    if 'track' in tags:
        if len(tags['track']) > 0:
            track = int(tags['track'].split('/')[0])
    if 'date' in tags:
        date = tags['date']

    conv = None
    if gst_is_installed and processing_with_gst:
        log.info('Converting using GStreamer')
        conv = convs_gst[bits]
        enc = stream['codec_name']
        global pipeline_is_prepared
        if not pipeline_is_prepared:
            gst_setup() # init
        if gst_process(infile) > 0:
            return 1
    else: # FFMPEG
        log.info('Converting using ffmpeg')
        conv = convs_ffmpeg[bits]
        if 'format_name' in container:
            fmts = container['format_name'].split(',')
        if ext in fmts:
            fmt = ext
        else:
            fmt = fmts[0]
        if 'codec_name' in stream:
            enc = stream['codec_name']
            if 'pcm_' == enc[0:4]:
                enc = fmt
        try:
            # Convert (24/32 bit float) audio format to integer.
            command_ = [
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
            ffmpeg = subprocess.Popen(
                command_,
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
    outbuf = None # clean
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
        name_ = '%s - %s' % (artist, title)
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
            'name': name_,
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

# Discover Media file audio tags, and properties.
# Note: discover_uri_async() exists,
# however async causes concurrency issues.
def gst_probe(audio_path):
    try:
        # 7s second timeout for scanning.
        d = GstPbutils.Discoverer.new(7 * Gst.SECOND) 
    except Exception as e:
        log.warning('Could not create GstPbutils.Discoverer object: ' + str(e))
        return 1

    try:
        # Template stream metadata.
        json_str = '''
            {
              "streams": [
                {
                }
              ],
              "format": {
                "tags": {
                }
              }
            }
        '''
        json_object = json.loads(json_str)

        json_object['format']['filename'] = audio_path

        # Look for audio tags.
        uri_audio_path = Gst.filename_to_uri(audio_path)
        discoverer_info = d.discover_uri(uri_audio_path)

        gstreamer_discovery_successful = False
        match discoverer_info.get_result():
            case GstPbutils.DiscovererResult.OK:
                gstreamer_discovery_successful = True
            case GstPbutils.DiscovererResult.URI_INVALID:
                log.warning('GStreamer could not process: ' + uri + ': (invalid URI)')
            case GstPbutils.DiscovererResult.ERROR:
                log.warning('GStreamer could not process: ' + uri + f': {str(err)}')
            case GstPbutils.DiscovererResult.TIMEOUT:
                log.warning('GStreamer could not process: ' + uri + ': (discovery timed out)')
            case GstPbutils.DiscovererResult.BUSY:
                log.warning('GStreamer could not process: ' + uri + ': (already discovering a file)')
            case GstPbutils.DiscovererResult.MISSING_PLUGINS:
                log.warning('GStreamer could not process: ' + uri + ': (missing plugins)')
            case _:
                log.warning('GStreamer could not process: Unknown Error')

        if not gstreamer_discovery_successful:
            log.warning('Unsuccessful probing for ' + audio_path)
            return 1

        # Get audio duration in nanoseconds, convert to seconds.
        json_object['streams'][0]['duration'] = str(discoverer_info.get_duration() / 1000000000)

        # [GstPbutils.DiscovererAudioInfo]
        for audio_info in discoverer_info.get_audio_streams():
            # File size.
            file = Gio.File.new_for_path(audio_path)
            info = file.query_info(
                Gio.FILE_ATTRIBUTE_STANDARD_SIZE,
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None
            )
            json_object['format']['size'] = str(info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_STANDARD_SIZE))

            json_object['streams'][0]['channels'] = audio_info.get_channels()

            sample_rate = audio_info.get_sample_rate()
            json_object['streams'][0]['sample_rate'] = str(sample_rate)

            global file_bit_depth
            file_bit_depth = audio_info.get_depth()
            json_object['streams'][0]['bits_per_sample'] = audio_info.get_depth()

            tags = audio_info.get_tags()
            if tags:
                result, value = tags.get_string(Gst.TAG_TITLE)
                if result == True:
                    json_object['format']['tags']['title'] = value

                result, value = tags.get_string(Gst.TAG_ARTIST)
                if result == True:
                    json_object['format']['tags']['artist'] = value

                result, value = tags.get_string(Gst.TAG_ALBUM)
                if result == True:
                    json_object['format']['tags']['album'] = value

                result, value = tags.get_string(Gst.TAG_AUDIO_CODEC)
                if result == True:
                    json_object['streams'][0]['codec_name'] = value
                    #audio_info.get_caps().get_structure(0).get_name() # short codec name

                result, value = tags.get_uint(Gst.TAG_TRACK_NUMBER)
                if result == True:
                    json_object['format']['tags']['track'] = str(value)

                # Get the year, try datetime first, otherwise try date.
                result, value = tags.get_date_time(Gst.TAG_DATE_TIME) # Gst.DateTime
                if result == True:
                    json_object['format']['tags']['date'] = str(value.get_year())
                else:
                    result, value = tags.get_date(Gst.TAG_DATE) # GLib.Date
                    if result == True:
                        json_object['format']['tags']['date'] = str(value.get_year())

                result, value = tags.get_uint(Gst.TAG_BITRATE)
                if result == True: # bitrate tag exists
                    json_object['streams'][0]['bit_rate'] = value
                else: # no bitrate tag, then estimate average bitrare
                    avg_bit_rate = (8 * info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_STANDARD_SIZE)) / ((discoverer_info.get_duration() / 1000000000))
                    json_object['streams'][0]['bit_rate'] = avg_bit_rate

            break # Only process first audio stream.

        return json_object
    except Exception as e:
        log.warning('Could not probe. Exception ' + f'{str(e)} in ' + audio_path)
        return 1

# Called many times to process a new block of audio samples.
def on_new_sample_to_process(sink):
    sample = sink.emit('pull-sample')
    buf = sample.get_buffer()
    # copy whole block of samples
    global outbuf
    outbuf.extend(buf.extract_dup(0, buf.get_size()))
    return Gst.FlowReturn.OK

# Link dynamic pad from decodebin to static pad on audioconvert.
# Change the audio data type to match an integer type (F32LE -> S32LE).
def on_pad_added(decodebin, pad):
    sink_pad = audioconvert.get_static_pad('sink')
    if not pad.is_linked():
        pad.link(sink_pad)

    # Detect audio format type
    caps = pad.get_current_caps()
    if caps and caps.get_structure(0).get_name().startswith('audio'):
        global conv_gst, decodebin_format, file_bit_depth
        cap_format = caps.get_structure(0).get_value('format')
        # Request pipeline conversion, at processing time.
        if cap_format != decodebin_format:
            decodebin_format = cap_format
            global appsink
            appsink.set_property('caps', Gst.Caps.from_string(f'audio/x-raw, format={convs_gst[file_bit_depth]["format"]}'))

# Setup GStreamer for processing.
def gst_setup():
    global pipeline_is_prepared, decodebin_format
    global pipeline, filesrc, decodebin, audioconvert, appsink
    pipeline = Gst.Pipeline.new('audio_pipeline')
    filesrc = Gst.ElementFactory.make('filesrc', 'source')
    decodebin = Gst.ElementFactory.make('decodebin', 'decoder')
    audioconvert = Gst.ElementFactory.make('audioconvert', 'converter')
    appsink = Gst.ElementFactory.make('appsink', 'sink')

    # Check if all elements were created successfully
    for elem in [filesrc, decodebin, audioconvert, appsink]:
        if elem is None:
            log.warning('Failed to create element ', elem.get_name())
            return 1

    appsink.set_property('emit-signals', True)
    appsink.set_property('sync', False)
    appsink.set_property('max-buffers', 1)
    appsink.connect('new-sample', on_new_sample_to_process)

    pipeline.add(filesrc)
    pipeline.add(decodebin)
    pipeline.add(audioconvert)
    pipeline.add(appsink)

    filesrc.link(decodebin)

    decodebin.connect('pad-added', on_pad_added)

    audioconvert.link(appsink)

    pipeline_is_prepared = True
    return 0

# GStreamer processing function.
def gst_process(file_path):
    try:
        # Set file path as source of audio.
        global pipeline, filesrc, outbuf
        filesrc.set_property('location', file_path)

        outbuf = bytearray(b'')

        # Start pipeline processing.
        pipeline.set_state(Gst.State.PLAYING)

        # Wait for the end of the stream or an error.
        bus = pipeline.get_bus()

        bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS)
        #bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)

        # End pipeline processing.
        pipeline.set_state(Gst.State.NULL)
        return 0
    except Exception as e:
        log.warning(str(e))
        return 1

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
def parse_values(obj, indent=0):
    global file_information
    if isinstance(obj, dict):
        for key, value in obj.items():
            file_information.append(' ' * indent + f'{key}:')
            parse_values(value, indent + 8)
    elif isinstance(obj, list):
        for item in obj:
            parse_values(item, indent)
    else:
        file_information.append(' ' * indent + str(obj))
