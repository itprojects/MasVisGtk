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
import os
import sys
import time

import numpy as np

log = logging.getLogger(__package__)


class Timer:
    def __init__(self, description=None, tid=None, callback=None):
        self.description = description
        self.callback = callback
        self.tid = tid

    def __enter__(self):
        if self.callback:
            self.callback('start', self.tid, desc=self.description)
        elif self.description:
            log.info(self.description)
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        self.msecs = self.secs * 1000
        if self.callback:
            self.callback('stop', self.tid, secs=self.secs)
        else:
            log.debug('%7.1f ms', self.msecs)


class Steps:
    steps = 23
    (
        total,
        calc_pr,
        calc_loud,
        calc_tp,
        calc_ebur128,
        calc_plr,
        calc_spec,
        calc_ap,
        calc_hist,
        calc_pvsr,
        calc_dr,
        calc_csum,
        draw_plot,
        draw_ch,
        draw_loud,
        draw_spec,
        draw_ap,
        draw_hist,
        draw_pvsr,
        draw_stc,
        draw_ebur128,
        draw_overview,
        save,
    ) = range(steps)
    times = [0] * steps
    descs = [''] * steps

    @classmethod
    def callback(cls, event, tid, desc=None, secs=None):
        if event == 'start':
            cls.start(tid, desc)
        elif event == 'stop':
            cls.stop(tid, secs)

    @classmethod
    def start(cls, tid, desc=None):
        if desc:
            cls.descs[tid] = desc
            log.info(desc)

    @classmethod
    def stop(cls, tid, secs):
        log.debug('%7.1f ms', secs * 1000)
        cls.times[tid] = secs

    @classmethod
    def report(cls):
        for desc, t in zip(cls.descs, cls.times):
            log.info("%s took %5.1f %%", desc, 100 * t / cls.times[0])


class Supervisor(object):
    pass


def aid(x):
    # This function returns the memory
    # block address of an array.
    return x.__array_interface__['data'][0]


def get_data_base(arr):
    """For a given Numpy array, finds the
    base array that "owns" the actual data."""
    base = arr
    while isinstance(base.base, np.ndarray):
        base = base.base
    return base


def arrays_share_data(x, y):
    return get_data_base(x) is get_data_base(y)


def gcd(a, b):
    """Return greatest common divisor using Euclid's Algorithm."""
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    """Return lowest common multiple."""
    return a * b // gcd(a, b)


def find_bin(ffprobe, ffmpeg):
    paths = [d for d in sys.path if 'Contents/Resources' in d]
    paths.extend(os.getenv('PATH').split(os.pathsep))
    binpath_ffprobe_return = None
    binpath_ffmpeg_return = None
    for ospath in paths:
        for binext in ['', '.exe']:
            binpath_ffprobe = os.path.join(ospath, ffprobe) + binext
            if os.path.isfile(binpath_ffprobe):
                log.debug('Found %s at %s', ffprobe, binpath_ffprobe)
                binpath_ffprobe_return = binpath_ffprobe
            binpath_ffmpeg = os.path.join(ospath, ffmpeg) + binext
            if os.path.isfile(binpath_ffmpeg):
                log.debug('Found %s at %s', ffmpeg, binpath_ffmpeg)
                binpath_ffmpeg_return = binpath_ffmpeg
            if binpath_ffprobe_return != None and binpath_ffmpeg_return != None:
                return binpath_ffprobe_return, binpath_ffmpeg_return
    return None, None
