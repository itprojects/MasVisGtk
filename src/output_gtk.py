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
import time

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib, Pango, Gdk

import numpy as np
import matplotlib
matplotlib.use('Agg') # non-GUI
#matplotlib.use('GTK4Agg') # interactive
import matplotlib.pyplot as plt
from matplotlib.backends.backend_gtk4agg import FigureCanvasGTK4Agg as FigureCanvasGTK4
from matplotlib.backends.backend_gtk4 import NavigationToolbar2GTK4 as NavigationToolbar
from matplotlib import gridspec, rc
from matplotlib.pyplot import (
    plot,
    semilogx,
    semilogy,
    setp,
    subplot,
    text,
    title,
    xlabel,
    xlim,
    xticks,
    ylabel,
    ylim,
    yticks,
)
from matplotlib.ticker import FormatStrFormatter, MaxNLocator, ScalarFormatter

from . import __version__
from .utils import Steps, Timer
from .params import c_color
from .params import channel_layouts_names
from .params import channel_layouts_params

log = logging.getLogger(__package__)

VERSION = __version__
R128_OFFSET = 23
STYLE = None
FONT = False
FONT_SMALL_SIZE = 10.0 # 'small'
FONT_LARGE_SIZE = 14.4 # 'large'

# Displays time format MM:SS
TIME_FMT = matplotlib.ticker.FuncFormatter(lambda sec, x: time.strftime('%M:%S', time.gmtime(sec)))

matplotlib.rcParams['legend.fontsize'] = 'medium' # medium = 12.0
matplotlib.rcParams['figure.titlesize'] = 'large'
matplotlib.rcParams['lines.linewidth'] = 1.0
matplotlib.rcParams['lines.dashed_pattern'] = [6, 6]
matplotlib.rcParams['lines.dashdot_pattern'] = [3, 5, 1, 5]
matplotlib.rcParams['lines.dotted_pattern'] = [1, 3]
matplotlib.rcParams['lines.scale_dashes'] = False
matplotlib.rcParams['xtick.direction'] = 'in'
matplotlib.rcParams['ytick.direction'] = 'in'

class MaxNLocatorMod(MaxNLocator):
    def __init__(self, *args, **kwargs):
        super(MaxNLocatorMod, self).__init__(*args, **kwargs)

    def tick_values(self, vmin, vmax):
        ticks = super(MaxNLocatorMod, self).tick_values(vmin, vmax)
        span = vmax - vmin
        if ticks[-1] > vmax - 0.05 * span:
            ticks = ticks[0:-1]
        return ticks

def positions(nc=1):
    w = 606.0
    h = 1060.0
    h_single = 81.976010101
    h_sep = 31.61931818181818181240
    h = round(h + (nc - 2) * (h_single + h_sep))
    left = 45.450
    right = 587.82
    top = 95.40
    bottom = 37.100
    header_y = 8.480
    subheader_y = 26.500
    footer_y = 7.420
    hr = [1] * nc + [1, 2, 2, 1, 1]
    n = len(hr)
    return {
        'w': w,
        'h': h,
        'left': left / w,
        'right': right / w,
        'top': (h - top) / h,
        'bottom': bottom / h,
        'header_y': (h - header_y) / h,
        'subheader_y': (h - subheader_y) / h,
        'footer_y': footer_y / h,
        'hspace': (h_sep * n) / (h - top - bottom - h_sep * (n - 1)),
        'hr': hr,
        'hn': n,
    }

def render(
    track, analysis, header, r128_unit='LUFS', overview_mode=None, callback=None, tab_page=None, win=None,
):
    # Set matplotlib style.
    global STYLE
    if not STYLE:
        STYLE = win.app.pref_matplotlib_style
        plt.style.use([STYLE])

    # Set matplotlib font, if enabled.
    if win.app.pref_custom_font:
        global FONT
        if not FONT:
            font_desc = Pango.FontDescription.from_string(win.app.pref_custom_font_value)
            matplotlib.rcParams['font.family'] = font_desc.get_family()
            matplotlib.rcParams['font.size'] = f'{int(font_desc.get_size() / Pango.SCALE)}'
            font_weight = 'bold'
            match font_desc.get_weight():
                case 100:
                    font_weight = 'thin'
                case 200:
                    font_weight = 'ultralight'
                case 300:
                    font_weight = 'light'
                case 350:
                    font_weight = 'semilight'
                case 380:
                    font_weight = 'book'
                case 400:
                    font_weight = 'normal'
                case 500:
                    font_weight = 'medium'
                case 600:
                    font_weight = 'semibold'
                case 700:
                    font_weight = 'bold'
                case 800:
                    font_weight = 'ultrabold'
                case 900:
                    font_weight = 'heavy'
                case 100:
                    font_weight = 'ultraheavy'
                case _:
                    pass
            matplotlib.rcParams['font.weight'] = font_weight
            FONT = True

    subplot_background_color = None
    if win.app.pref_custom_background:
        subplot_background_color = win.app.pref_custom_background_value

    DPI = win.app.pref_dpi_application

    #
    # Plot
    #
    nc = track['channels']
    c_name = None # Channel [layout] names.
    c_layout = track['channel_layout']
    if c_layout == None:
        if nc == 0: # no audio
            str_error = _('Input file has no audio stream: ') + track['metadata']['filename']
            log.warning(str_error)
            raise Exception(str_error)
            return
        elif nc == 1:
            c_layout = 'mono'
        elif nc == 2:
            c_layout = 'stereo'
        else:
            pass
    if (c_layout != None) and (c_layout in channel_layouts_names): # Assign channel layout names.
        c_name = channel_layouts_names[c_layout]
    else:
        c_name = []
        for i in range(35):
            c_name.append(f'#{i+1}')

    fs = track['samplerate']
    crest_db = analysis['crest_db']
    crest_total_db = analysis['crest_total_db']
    dr = analysis['dr']
    l_kg = analysis['l_kg']
    lra = analysis['lra']
    plr = analysis['plr_lu']
    checksum = analysis['checksum']
    lufs_to_lu = 23.0
    if r128_unit == 'LUFS':
        r128_offset = 0
    else:
        r128_offset = R128_OFFSET
    nc_max = len(c_color)
    data = track['data']['float']
    pos = positions(nc)
    peak_dbfs = analysis['peak_dbfs']

    if win.app.check_cancellations():
        return

    if overview_mode == None:# Detailed one track plot.
        with Timer('Drawing plot...', Steps.draw_plot, callback):
            subtitle_analysis = _('Crest: {:0.2f} dB,  DR: {},  L$_K$: {:0.1f} {},  LRA: {:0.1f} LU,  PLR: {:0.1f} LU').format(
                float(crest_total_db), dr, l_kg + r128_offset, r128_unit, lra, plr
            )
            subtitle_source = _('Encoding: {},  Channels: {},  Layout: {},  Bits: {},\nSample rate: {} Hz,  Bitrate: {} kbps,  Duration: {},  Size: {:0.1f} MB').format(
                track['metadata']['encoding'],
                track['channels'],
                c_layout,
                track['bitdepth'],
                fs,
                int(round(track['metadata']['bps'] / 1000.0)),
                time.strftime('%M:%S', time.gmtime(track['duration'])),
                track['metadata']['size'] / (1024 * 1024), # MB file size
            )
            subtitle_meta = []
            if track['metadata']['album']:
                subtitle_meta.append(_('Album') + ': %.*s' % (50, track['metadata']['album']))
            if track['metadata']['track']:
                subtitle_meta.append(_('Track') + ': %s' % track['metadata']['track'])
            if track['metadata']['date']:
                subtitle_meta.append(_('Date') + ': %s' % track['metadata']['date'])
            subtitle_meta = ',  '.join(subtitle_meta)
            subtitle = '\n'.join([subtitle_analysis, subtitle_source, subtitle_meta])
            win.n_figures += 1
            fig_d = plt.figure(win.n_figures)
            fig_d.dict_fontsizes = dict() # (type, font_size, obj_with_text)
            fig_d.dpi = DPI
            fig_d.figsize = (pos['w'] / DPI, pos['h'] / DPI)
            #fig_d.facecolor = 'white'
            f_suptitle = fig_d.suptitle(
                header,
                fontweight='bold',
                fontsize=FONT_LARGE_SIZE,
                y=pos['header_y']
            )
            f_subtitle = fig_d.text(
                0.5,
                pos['subheader_y'],
                subtitle,
                fontsize=FONT_SMALL_SIZE,
                horizontalalignment='center',
                verticalalignment='top',
                linespacing=1.6,
            )
            f_checksum = fig_d.text(
                pos['left'],
                pos['footer_y'],
                _('Checksum (energy): ') + str(checksum),
                fontsize=FONT_SMALL_SIZE,
                va='bottom',
                ha='left',
            )
            f_version = fig_d.text(
                pos['right'],
                pos['footer_y'],
                _('MasVisGtk ') + str(VERSION),
                fontsize=FONT_SMALL_SIZE,
                va='bottom',
                ha='right',
            )
            rc('lines', linewidth=0.5, antialiased=True)
            gs = gridspec.GridSpec(
                pos['hn'],
                2,
                width_ratios=[2, 1],
                height_ratios=pos['hr'],
                hspace=pos['hspace'],
                wspace=0.2,
                left=pos['left'],
                right=pos['right'],
                bottom=pos['bottom'],
                top=pos['top'],
            )
            fig_d.dict_fontsizes['suptitle'] = (f_suptitle, 14.4, 'text')
            fig_d.dict_fontsizes['subtitle'] = (f_subtitle, 10.0, 'text')
            fig_d.dict_fontsizes['checksum'] = (f_checksum, 10.0, 'text')
            fig_d.dict_fontsizes['version'] = (f_version, 10.0, 'text')

        if win.app.check_cancellations():
            return

        # Channels
        data = track['data']['float']
        sec = track['duration']
        rms_dbfs = analysis['rms_dbfs']
        true_peak_dbtp = analysis['true_peak_dbtp']
        c_max = analysis['c_max']
        w_max = analysis['w_max']
        with Timer('Drawing channels...', Steps.draw_ch, callback):
            ax_ch = []
            c = 0
            while c < nc and c < nc_max:
                if c == 0:
                    ax_ch.append(subplot(gs[c, :]))
                else:
                    ax_ch.append(subplot(gs[c, :], sharex=ax_ch[0]))
                new_data, new_ns, new_range = pixelize(
                    data[c], ax_ch[c], which='both', oversample=2
                )
                new_fs = new_ns / sec
                new_range = np.arange(0.0, new_ns, 1) / new_fs
                plot(new_range, new_data, color=c_color[c], linestyle='-')
                xlim(0, round(sec))
                ylim(-1.0, 1.0)
                f_channel_title = title(
                    _('{}: Crest = {:0.2f} dB / RMS = {:0.2f} dBFS / Peak = {:0.2f} dBFS / True Peak ≈ {:0.2f} dBTP').format(
                        c_name[c].capitalize(), crest_db[c], rms_dbfs[c], peak_dbfs[c], true_peak_dbtp[c]
                    ),
                    fontsize=FONT_SMALL_SIZE,
                    loc='left',
                )
                fig_d.dict_fontsizes[f'channel_title_{c}'] = (f_channel_title, 10.0, 'text')
                yticks([1, -0.5, 0, 0.5, 1], ('', -0.5, 0, '', ''))
                if c_max == c:
                    mark_span(ax_ch[c], (w_max[0] / float(fs), w_max[1] / float(fs)))
                if c + 1 == nc or c + 1 == nc_max:
                    #ax_ch[c].xaxis.set_major_locator(MaxNLocatorMod(prune='both'))
                    #ax_ch[c].xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
                    ax_ch[c].xaxis.set_major_formatter(TIME_FMT)
                    f_channel_xlabel = xlabel(':sec', fontsize=FONT_SMALL_SIZE)
                    fig_d.dict_fontsizes[f'channel_xlabel'] = (f_channel_xlabel, 10.0, 'text')
                else:
                    setp(ax_ch[c].get_xticklabels(), visible=False)
                axis_defaults(ax_ch[c])
                c += 1
            for axia in ax_ch:
                if subplot_background_color:
                    axia.set_facecolor((subplot_background_color)) # plot background
                axia.yaxis.grid(True, which='major', linestyle=':', color='k', linewidth=0.5)
        spi = c - 1

        if win.app.check_cancellations():
            return

        # Loudest
        s_max = analysis['s_max']
        ns_max = analysis['ns_max']
        with Timer('Drawing loudest...', Steps.draw_loud, callback):
            ax_max = subplot(gs[spi + 1, :])
            if subplot_background_color:
                ax_max.set_facecolor((subplot_background_color)) # plot background
            plot(
                np.arange(*w_max) / float(fs),
                data[c_max][np.arange(*w_max)],
                c_color[c_max],
            )
            ylim(-1.0, 1.0)
            xlim(w_max[0] / float(fs), w_max[1] / float(fs))
            f_loudest_title = title(
                _('Loudest part ({} channel, {} samples > 95{} during 20 ms at {:0.2f} sec)').format(
                    c_name[c_max], ns_max, '%', s_max / float(fs),
                ),
                fontsize=FONT_SMALL_SIZE,
                loc='left',
            )
            fig_d.dict_fontsizes['loudest_title'] = (f_loudest_title, 10.0, 'text')
            yticks([1, -0.5, 0, 0.5, 1], ('', -0.5, 0, '', ''))
            #ax_max.xaxis.set_major_locator(MaxNLocatorMod(nbins=5, prune='both'))
            #ax_max.xaxis.set_major_formatter(FormatStrFormatter('%0.2f'))
            ax_max.xaxis.set_major_formatter(TIME_FMT)
            f_loudness_xlabel = xlabel(':sec', fontsize=FONT_SMALL_SIZE)
            fig_d.dict_fontsizes[f'loudness_xlabel'] = (f_loudness_xlabel, 10.0, 'text')
            axis_defaults(ax_max)

        if win.app.check_cancellations():
            return

        # Spectrum
        norm_spec = analysis['norm_spec']
        frames = analysis['frames']
        with Timer('Drawing spectrum...', Steps.draw_spec, callback):
            ax_norm = subplot(gs[spi + 2, 0])
            if subplot_background_color:
                ax_norm.set_facecolor((subplot_background_color)) # plot background
            semilogx(
                [0.02, 0.06],
                [-80, -90],
                'k-',
                [0.02, 0.2],
                [-70, -90],
                'k-',
                [0.02, 0.6],
                [-60, -90],
                'k-',
                [0.02, 2.0],
                [-50, -90],
                'k-',
                [0.02, 6.0],
                [-40, -90],
                'k-',
                [0.02, 20.0],
                [-30, -90],
                'k-',
                [0.02, 20.0],
                [-20, -80],
                'k-',
                [0.02, 20.0],
                [-10, -70],
                'k-',
                [0.06, 20.0],
                [-10, -60],
                'k-',
                [0.20, 20.0],
                [-10, -50],
                'k-',
                [0.60, 20.0],
                [-10, -40],
                'k-',
                [2.00, 20.0],
                [-10, -30],
                'k-',
                [6.00, 20.0],
                [-10, -20],
                'k-',
                base=10,
            )
            for c in range(nc):
                new_spec, new_n, new_r = pixelize(
                    norm_spec[c],
                    ax_norm,
                    which='max',
                    oversample=1,
                    method='log10',
                    span=(20, int(fs * 0.5)), # Nyquist-Shannon, originally span=(20, 20000)
                )
                semilogx(new_r / 1000.0, new_spec, color=c_color[c], linestyle='-', base=10)
            ylim(-90, -10)
            xlim(0.02, 20)
            ax_norm.yaxis.grid(True, which='major', linestyle=':', color='k', linewidth=0.5)
            ax_norm.xaxis.grid(True, which='both', linestyle='-', color='k', linewidth=0.5)
            f_spectrum_ylabel = ylabel('dB', fontsize=FONT_SMALL_SIZE, verticalalignment='top', rotation=0)
            fig_d.dict_fontsizes[f'spectrum_ylabel'] = (f_spectrum_ylabel, 10.0, 'text')
            f_spectrum_xlabel = xlabel('kHz', fontsize=FONT_SMALL_SIZE, horizontalalignment='right')
            fig_d.dict_fontsizes[f'spectrum_xlabel'] = (f_spectrum_xlabel, 10.0, 'text')
            f_spectrum_title = title(
                _('Normalised average spectrum, ') + str(frames) + _(' frames'),
                fontsize=FONT_SMALL_SIZE,
                loc='left',
            )
            fig_d.dict_fontsizes['spectrum_title'] = (f_spectrum_title, 10.0, 'text')
            ax_norm.set_xticks([0.05, 0.1, 0.2, 0.5, 1, 2, 3, 4, 5, 7, 10, 20], minor=False)
            ax_norm.set_xticks(
                [
                    0.03,
                    0.04,
                    0.06,
                    0.07,
                    0.08,
                    0.09,
                    0.3,
                    0.4,
                    0.6,
                    0.7,
                    0.8,
                    0.9,
                    6,
                    8,
                    9,
                    10,
                ],
                minor=True,
            )
            ax_norm.set_xticklabels([0.05, 0.1, 0.2, 0.5, 1, 2, 3, 4, 5, 7, 10, 20], minor=False)
            ax_norm.set_xticklabels([], minor=True)
            yticks(np.arange(-90, 0, 10), ('', -80, -70, -60, -50, -40, -30, '', ''))
            axis_defaults(ax_norm)

        if win.app.check_cancellations():
            return

        # Allpass
        ap_freqs = analysis['ap_freqs']
        ap_crest = analysis['ap_crest']
        with Timer('Drawing allpass...', Steps.draw_ap, callback):
            ax_ap = subplot(gs[spi + 2, 1])
            if subplot_background_color:
                ax_ap.set_facecolor((subplot_background_color)) # plot background
            for c in range(nc):
                semilogx(
                    ap_freqs / 1000.0,
                    crest_db[c] * np.ones(len(ap_freqs)),
                    color=c_color[c],
                    linestyle='--',
                    base=10,
                )
                semilogx(
                    ap_freqs / 1000.0,
                    ap_crest.swapaxes(0, 1)[c],
                    color=c_color[c],
                    linestyle='-',
                    base=10,
                )
            ylim(0, 30)
            xlim(0.02, 20)
            f_allpass_title = title(
                _('Allpassed crest factor'),
                fontsize=FONT_SMALL_SIZE,
                loc='left'
            )
            fig_d.dict_fontsizes['allpass_title'] = (f_allpass_title, 10.0, 'text')
            yticks(np.arange(0, 30, 5), ('', 5, 10, 15, 20, ''))
            xticks([0.1, 1, 2], (0.1, 1, 2))
            f_allpass_xlabel = xlabel('kHz', fontsize=FONT_SMALL_SIZE)
            fig_d.dict_fontsizes['allpass_xlabel'] = (f_allpass_xlabel, 10.0, 'text')
            f_allpass_ylabel = ylabel('dB', fontsize=FONT_SMALL_SIZE, rotation=0)
            fig_d.dict_fontsizes['f_allpass_ylabel'] = (f_allpass_ylabel, 10.0, 'text')
            axis_defaults(ax_ap)

        if win.app.check_cancellations():
            return

        # Histogram
        hist = analysis['hist']
        hist_bits = analysis['hist_bits']
        hist_title_bits = []
        with Timer('Drawing histogram...', Steps.draw_hist, callback):
            ax_hist = subplot(gs[spi + 3, 0])
            if subplot_background_color:
                ax_hist.set_facecolor((subplot_background_color)) # plot background
            for c in range(nc):
                new_hist, new_n, new_range = pixelize(
                    hist[c], ax_hist, which='max', oversample=2
                )
                new_hist[(new_hist == 1.0)] = 1.3
                new_hist[(new_hist < 1.0)] = 1.0
                semilogy(
                    np.arange(new_n) * 2.0 / new_n - 1.0,
                    new_hist,
                    color=c_color[c],
                    linestyle='-',
                    base=10,
                    drawstyle='steps',
                )
                hist_title_bits.append('%0.1f' % hist_bits[c])
            xlim(-1.1, 1.1)
            ylim(1, 50000)
            xticks(
                np.arange(-1.0, 1.2, 0.2),
                (-1, -0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1),
            )
            yticks([10, 100, 1000], (10, 100, 1000))
            hist_title = _('Histogram, \'bits\': ') + '/'.join(hist_title_bits)
            f_histogram_title = title(hist_title,
                fontsize=FONT_SMALL_SIZE,
                loc='left'
            )
            fig_d.dict_fontsizes['histogram_title'] = (f_histogram_title, 10.0, 'text')
            f_histogram_ylabel = ylabel('n', fontsize=FONT_SMALL_SIZE, rotation=0)
            fig_d.dict_fontsizes['histogram_ylabel'] = (f_histogram_ylabel, 10.0, 'text')
            axis_defaults(ax_hist)

        if win.app.check_cancellations():
            return

        # Peak vs RMS
        rms_1s_dbfs = analysis['rms_1s_dbfs']
        peak_1s_dbfs = analysis['peak_1s_dbfs']
        with Timer('Drawing peak vs RMS...', Steps.draw_pvsr, callback):
            ax_pr = subplot(gs[spi + 3, 1])
            if subplot_background_color:
                ax_pr.set_facecolor((subplot_background_color)) # plot background
            plot(
                [-50, 0],
                [-50, 0],
                'k-',
                [-50, -10],
                [-40, 0],
                'k-',
                [-50, -20],
                [-30, 0],
                'k-',
                [-50, -30],
                [-20, 0],
                'k-',
                [-50, -40],
                [-10, 0],
                'k-',
            )
            text_style = {
                'fontsize': 'small',
                'rotation': 45,
                'va': 'bottom',
                'ha': 'left',
            }
            text(-48, -45, '0 dB', **text_style)
            text(-48, -35, '10', **text_style)
            text(-48, -25, '20', **text_style)
            text(-48, -15, '30', **text_style)
            text(-48, -5, '40', **text_style)
            for c in range(nc):
                plot(
                    rms_1s_dbfs[c],
                    peak_1s_dbfs[c],
                    linestyle='',
                    marker='o',
                    markerfacecolor='w',
                    markeredgecolor=c_color[c],
                    markeredgewidth=0.7,
                )
            xlim(-50, 0)
            ylim(-50, 0)
            f_peak_title = title(
                _('Peak vs RMS level'),
                fontsize=FONT_SMALL_SIZE,
                loc='left'
            )
            fig_d.dict_fontsizes['peak_title'] = (f_peak_title, 10.0, 'text')
            f_peak_xlabel = xlabel('dBFS', fontsize=FONT_SMALL_SIZE)
            fig_d.dict_fontsizes['peak_xlabel'] = (f_peak_xlabel, 10.0, 'text')
            f_peak_ylabel = ylabel('dBFS', fontsize=FONT_SMALL_SIZE, rotation=0)
            fig_d.dict_fontsizes['peak_ylabel'] = (f_peak_ylabel, 10.0, 'text')
            xticks([-50, -40, -30, -20, -10, 0], ('', -40, -30, -20, '', ''))
            yticks([-50, -40, -30, -20, -10, 0], ('', -40, -30, -20, -10, ''))
            axis_defaults(ax_pr)

        if win.app.check_cancellations():
            return

        # Shortterm crest
        crest_1s_db = analysis['crest_1s_db']
        n_1s = analysis['n_1s']
        with Timer('Drawing short term crest...', Steps.draw_stc, callback):
            ax_1s = subplot(gs[spi + 4, :])
            if subplot_background_color:
                ax_1s.set_facecolor((subplot_background_color)) # plot background
            for c in range(nc):
                plot(
                    np.arange(n_1s) + 0.5,
                    crest_1s_db[c],
                    linestyle='',
                    marker='o',
                    markerfacecolor='w',
                    markeredgecolor=c_color[c],
                    markeredgewidth=0.7,
                )
            ylim(0, 30)
            xlim(0, n_1s)
            yticks([10, 20], (10, ''))
            ax_1s.yaxis.grid(True, which='major', linestyle=':', color='k', linewidth=0.5)
            f_shortterm_title = title(
                _('Short term (1 s) crest factor'),
                fontsize=FONT_SMALL_SIZE,
                loc='left'
            )
            fig_d.dict_fontsizes['shortterm_title'] = (f_shortterm_title, 10.0, 'text')
            f_shortterm_xlabel = xlabel(':sec', fontsize=FONT_SMALL_SIZE)
            fig_d.dict_fontsizes['shortterm_xlabel'] = (f_shortterm_xlabel, 10.0, 'text')
            f_shortterm_ylabel = ylabel('dB', fontsize=FONT_SMALL_SIZE, rotation=0)
            fig_d.dict_fontsizes['shortterm_ylabel'] = (f_shortterm_ylabel, 10.0, 'text')
            #ax_1s.xaxis.set_major_locator(MaxNLocatorMod(prune='both'))
            #ax_1s.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
            ax_1s.xaxis.set_major_formatter(TIME_FMT)
            axis_defaults(ax_1s)

        if win.app.check_cancellations():
            return

        # EBU R 128
        stl = analysis['stl']
        stplr = analysis['stplr_lu']
        with Timer('Drawing EBU R 128 loudness...', Steps.draw_ebur128, callback):
            ax_ebur128 = subplot(gs[spi + 5, :])
            if subplot_background_color:
                ax_ebur128.set_facecolor((subplot_background_color)) # plot background
            plot(
                np.arange(stl.size) + 1.5,
                stl + r128_offset,
                'ko',
                markerfacecolor='w',
                markeredgecolor='k',
                markeredgewidth=0.7,
            )
            ylim(-41 + r128_offset, -5 + r128_offset)
            xlim(0, n_1s)
            yticks(
                [-33 + r128_offset, -23 + r128_offset, -13 + r128_offset],
                (-33 + r128_offset, -23 + r128_offset, ''),
            )
            f_ebu_short_title = title(
                _('EBU R 128 Short term loudness'),
                fontsize=FONT_SMALL_SIZE,
                loc='left'
            )
            fig_d.dict_fontsizes['ebu_short_title'] = (f_ebu_short_title, 10.0, 'text')
            f_short_plr_title = title(
                _('Short term PLR'),
                fontsize=FONT_SMALL_SIZE,
                loc='right',
                color='grey'
            )
            fig_d.dict_fontsizes['short_plr_title'] = (f_short_plr_title, 10.0, 'text')
            f_short_plr_xlabel = xlabel(':sec', fontsize=FONT_SMALL_SIZE)
            fig_d.dict_fontsizes['short_plr_xlabel'] = (f_short_plr_xlabel, 10.0, 'text')
            f_short_plr_ylabel = ylabel('%s' % r128_unit, fontsize=FONT_SMALL_SIZE, rotation=0)
            fig_d.dict_fontsizes['short_plr_ylabel'] = (f_short_plr_ylabel, 10.0, 'text')
            ax_ebur128.yaxis.grid(
                True, which='major', linestyle=':', color='k', linewidth=0.5
            )
            ax_ebur128_stplr = ax_ebur128.twinx()
            plot(
                np.arange(stplr.size) + 1.5,
                stplr,
                'o',
                markerfacecolor='w',
                markeredgecolor='grey',
                markeredgewidth=0.7,
            )
            xlim(0, n_1s)
            ylim(0, 36)
            yticks([0, 18], (0, 18))
            for tl in ax_ebur128_stplr.get_yticklabels():
                tl.set_color('grey')
            #ax_ebur128.xaxis.set_major_locator(MaxNLocatorMod(prune='both'))
            #ax_ebur128.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
            ax_ebur128.xaxis.set_major_formatter(TIME_FMT)
            axis_defaults(ax_ebur128)
            axis_defaults(ax_ebur128_stplr)
            ax_ebur128_stplr.tick_params(
                axis='y', which='major', labelsize=FONT_SMALL_SIZE, length=0
            )

        #
        # Plot/Paint/Draw detailed track analysis on GTK canvas.
        #
        canvas = FigureCanvasGTK4(fig_d)
        canvas.set_hexpand(True)
        canvas.set_vexpand(True)

        # Keep pyplot canvas works best with a fixed aspect ratio.
        aspect_frame = Gtk.AspectFrame()
        aspect_ratio = pos['w']/pos['h']
        aspect_frame.set_ratio(aspect_ratio)
        aspect_frame.set_child(canvas)

        tab_page.get_child().scrolled.set_child(aspect_frame)

        nav_bar = NavigationToolbar(canvas)

        # Add translations to the tab NavigationToolbar.
        nav_bar_widgets = nav_bar.observe_children()
        for item in nav_bar_widgets:
            if 'Configure subplots' == item.get_tooltip_text():
                item.set_visible(False) # hide config (unused) button

            # Prevent button stretching.
            item.set_valign(Gtk.Align.CENTER)

            # Translate button texts.
            match item.get_tooltip_text():
                case 'Reset original view':
                    item.set_tooltip_text(_('Reset original view'))
                case 'Back to previous view':
                    item.set_tooltip_text(_('Back to previous view'))
                case 'Forward to next view':
                    item.set_tooltip_text(_('Forward to next view'))
                case 'Left button pans, Right button zooms\nx/y fixes axis, CTRL fixes aspect':
                    item.set_tooltip_text(_('Left button pans, Right button zooms\nx/y fixes axis, CTRL fixes aspect'))
                case 'Zoom to rectangle\nx/y fixes axis':
                    item.set_tooltip_text(_('Zoom to rectangle\nx/y fixes axis'))
                #case 'Configure subplots':
                #    item.set_tooltip_text(_('Configure subplots'))
                case 'Save the figure':
                    item.set_tooltip_text(_('Save the figure'))
                case _:
                    pass

        # Gtk.SpinButton to zoom-in/rescale the plot size.
        spin_zoom = Gtk.SpinButton.new_with_range(1080, 4096, 500) # lower, upper, step
        spin_zoom.set_valign(Gtk.Align.CENTER)
        spin_zoom.set_tooltip_text(_('Zoom Level [px]'))
        spin_zoom.set_digits(0)
        spin_zoom.canvas = canvas
        spin_zoom.aspect_ratio = aspect_ratio
        spin_zoom.connect('value-changed', on_value_changed)

        btn_zoom_original = Gtk.Button(icon_name='system-search-symbolic', tooltip_text=_('Restore original dimensions'))
        btn_zoom_original.set_valign(Gtk.Align.CENTER)
        btn_zoom_original.connect('clicked', on_scale_to_default, spin_zoom.get_adjustment())

        # Resize button to scale canvas to window width.
        btn_scale_to_win = Gtk.Button(label='⇤ ⇥', tooltip_text=_('Scale to Window Width'))
        btn_scale_to_win.set_name('btn_scale_to_win')
        btn_scale_to_win.connect('clicked', on_scale_to_win, spin_zoom.get_adjustment(), win)
        btn_scale_to_win.set_halign(Gtk.Align.CENTER)
        btn_scale_to_win.set_valign(Gtk.Align.CENTER)
        btn_scale_to_win.canvas = canvas
        btn_scale_to_win.aspect_ratio = aspect_ratio

        # Dynamic Range indicator widget.
        btn_dr = Gtk.Button()
        btn_dr.set_name('btn_dr')

        btn_dr = Gtk.Button()
        btn_dr.set_name('btn_dr')

        nav_bar.prepend(btn_dr)
        nav_bar.append(btn_zoom_original)
        nav_bar.append(spin_zoom)
        nav_bar.append(btn_scale_to_win)

        tab_page.get_child().prepend(nav_bar)

        if win.app.check_cancellations():
            return

        # Set initial canvas size to be window width.
        new_canvas_width = 1080
        canvas.set_size_request(new_canvas_width, new_canvas_width//aspect_ratio)

        # Paint the Dynamic Range widget.
        dr_val = None
        try:
            dr_val = int(dr)
            if dr_val < 0:
                dr_val = '??'
        except:
            dr_val = '??'

        match dr_val:
            case 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7:
                btn_dr.add_css_class('dr_style07')
            case 8:
                btn_dr.add_css_class('dr_style08')
            case 9:
                btn_dr.add_css_class('dr_style09')
            case 10:
                btn_dr.add_css_class('dr_style10')
            case 11:
                btn_dr.add_css_class('dr_style11')
            case 12:
                btn_dr.add_css_class('dr_style12')
            case 13:
                btn_dr.add_css_class('dr_style13')
            case _:
                if dr_val != '??' and dr_val > 13:
                    btn_dr.add_css_class('dr_style14')

        if dr_val == '??':
            btn_dr.set_label('??')
            btn_dr.set_tooltip_text(_('Unknown Dynamic Range'))
        else:
            str_dr = f'{dr_val:0>2d}'
            btn_dr.set_label(str_dr)
            btn_dr.set_tooltip_text(_('Dynamic Range'))
    else:# Overview plot.
        w_o = 1212 # originally 606
        h_o = 128 # originally 64

        # Overview started?
        overview_not_started = tab_page.get_child().scrolled.get_child() == None

        n_axes = 1

        box_as_frame = None
        canvas = None
        fig_d = None
        ax_o = None
        if overview_not_started:
            win.n_figures += 1
            fig_d = plt.figure(win.n_figures)
            fig_d.dict_fontsizes = dict()
            fig_d.dpi = DPI
            fig_d.figsize = (w_o / DPI, h_o / DPI)

            # Make subplot for current file.
            ax_o = fig_d.add_subplot(111)
            canvas = FigureCanvasGTK4(fig_d)
            canvas.set_hexpand(True)

            # Hold canvas.
            box_as_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box_as_frame.append(canvas)

            # Feature, not bug. Prevents expansion in width.
            box_as_frame.set_halign(Gtk.Align.CENTER)
            tab_page.get_child().scrolled.set_child(box_as_frame)
        else:
            # Find canvas. backend_gtk4agg.FigureCanvasGTK4Agg
            canvas = tab_page.get_child().scrolled.get_child().get_child().get_last_child()

            fig_d = canvas.figure

            # Update figure size.
            n_axes = len(fig_d.get_axes())
            n_axes += 1

        if win.app.check_cancellations():
            return

        # Set new canvas height.
        new_height = (64 + 128) * n_axes

        if not box_as_frame:
            box_as_frame = canvas.get_parent()

        # Resize figure's canvas.
        fig_d.figsize = (w_o / DPI, new_height / DPI)
        canvas.set_size_request(1212, new_height)
        box_as_frame.set_size_request(1212, new_height)

        # Add subplot, refresh grid, which maintains axes spacing.
        if ax_o == None:
            gs = gridspec.GridSpec(n_axes, 1)
            for i, ax in enumerate(fig_d.axes):
                ax.set_position(gs[i].get_position(fig_d))
                ax.set_subplotspec(gs[i])
            ax_o = fig_d.add_subplot(gs[n_axes - 1])

        # Adjust borders, to gain space.
        plt.subplots_adjust(left=0.04, right=0.82, top=1, bottom=0)

        # Set Y-axis label, to display audio info.
        info_o = _('DR = {}\nPeak = {:0.1f} dBFS\nCrest = {:0.1f} dB\nL$_k$ = {:0.1f} LU').format(
            dr, float(peak_dbfs.max()), float(crest_total_db), l_kg + lufs_to_lu
        )

        ax_o.set_ylabel(info_o, fontsize='small', horizontalalignment='left', rotation=0)
        ax_o.yaxis.set_label_position("right")
        ax_o.yaxis.set_label_coords(1.01, 0.8, transform=None)
        ax_o.set_xticks([])
        ax_o.set_yticks([])
        header_o = _('{} [{}, {} channels, {} bits, {:0.1f} kHz, {} kbps]').format(
            header, track['metadata']['encoding'], track['channels'], track['bitdepth'],
            fs/1000, int(round(track['metadata']['bps'] / 1000.0))
        )

        ax_o.set_title(header_o, fontsize='small', loc='left')
        fig_buf = plt.figure('buffer', figsize=(w_o / DPI, h_o / DPI), dpi=DPI)
        w, h = fig_buf.canvas.get_width_height()
        fig_buf.patch.set_visible(False)
        ax_buf = plt.gca()

        img_buf = np.zeros((h, w, 4), np.uint8)
        img_buf[:, :, 0:3] = 255

        if win.app.check_cancellations():
            return

        for i, ch in enumerate(data):
            ax_buf.clear()
            ax_buf.axis('off')
            ax_buf.set_position([0, 0, 1, 1])
            ax_buf.set_ylim(-1, 1)
            ax_buf.set_xticks([])
            ax_buf.set_yticks([])
            new_ch, new_n, new_r = pixelize(ch, ax_buf, which='both', oversample=2)
            ax_buf.plot(range(len(new_ch)), new_ch, color=c_color[i])
            ax_buf.set_xlim(0, len(new_ch))
            fig_buf.canvas.draw()
            img = np.frombuffer(fig_buf.canvas.buffer_rgba(), np.uint8).reshape(
                h, w, -1
            )
            img_buf[:, :, 0:3] = img[:, :, 0:3] * (img_buf[:, :, 0:3] / 255.0)
            img_buf[:, :, -1] = np.maximum(img[:, :, -1], img_buf[:, :, -1])
        img_buf[:, :, 0:3] = (img_buf[:, :, 3:4] / 255.0) * img_buf[:, :, 0:3] + (255 - img_buf[:, :, 3:4])
        img_buf[:, :, -1] = 255

        if win.app.check_cancellations():
            return

        plt.figure(fig_d.number)
        plt.imshow(img_buf, aspect='1', interpolation='none')
        plt.close(fig_buf) # close buffer

    canvas.draw()
    canvas.flush_events()
    #del data # clean?

# Save canvas figure to image on disk.
# Format 0=png, 1=jpeg, 2=svg, 3=webp, 4=tiff, 5=pdf, 6=eps
def save_figure(fig, path, save_format, dpi):
    # select image source figure
    plt.figure(fig.number)

    # If params are different than canvas plot,
    # there will be a flicker, during saving.
    plt.savefig(path, format=save_format, bbox_inches='tight', dpi=dpi)

# Set new canvas size. [1080 px, 4096 px]
# Maximum width is artificially set to 4096 px (4K).
# Scale font sizes, using width.
def on_value_changed(spin_btn):
    new_canvas_width = spin_btn.get_value()
    spin_btn.canvas.set_size_request(new_canvas_width, new_canvas_width//spin_btn.aspect_ratio)

    # Change font sizes of axes texts.
    scale_factor = new_canvas_width / 1080
    for k, v in spin_btn.canvas.figure.dict_fontsizes.items():
        if v[2] == 'text':
            v[0].set_fontsize(round(v[1] * scale_factor))

    # Change font sizes of axis ticks.
    for ax in spin_btn.canvas.figure.get_axes():

        xticklabels_ = ax.get_xticklabels()
        for xt in xticklabels_:
            xt.set_fontsize(round(10.0 * scale_factor))

        yticklabels_ = ax.get_yticklabels()
        for yt in yticklabels_:
            yt.set_fontsize(round(10.0 * scale_factor))

# Set new canvas size (and scale), equal to window width.
def on_scale_to_win(btn, scale_adjustment, win):
    new_canvas_width = win.get_allocated_width()
    if new_canvas_width <= 1080: # minimum
        scale_adjustment.set_value(1080)
    elif new_canvas_width >= 4096: # maximum
        scale_adjustment.set_value(4096)
    else: # calculate exact scale change.
        scale_adjustment.set_value(new_canvas_width)

# Set new canvas size (and scale), equal (by default) to 1080 pixels.
def on_scale_to_default(btn, scale_adjustment):
    scale_adjustment.set_value(1080)

def list_styles():
    return plt.style.available

def xpixels(ax):
    return np.round(ax.bbox.bounds[2])

def pixelize(x, ax, method='linear', which='both', oversample=1, span=None):
    if not span:
        span = (0, len(x))
        if method == 'log10':
            span = (1, len(x) + 1)
    pixels = xpixels(ax)
    minmax = 1
    if which == 'both':
        minmax = 2
    nw = int(pixels * oversample)
    w = (span[1] - span[0]) / (pixels * oversample)
    n = nw * minmax
    y = np.zeros(n)
    r = np.zeros(n)
    for i in range(nw):
        if method == 'linear':
            j = int(np.round(i * w + span[0]))
            k = int(np.round(j + w + span[0]))
        elif method == 'log10':
            a = np.log10(span[1]) - np.log10(span[0])
            b = np.log10(span[0])
            j = int(np.round(10 ** (i / float(nw) * a + b)) - 1)
            k = int(np.round(10 ** ((i + 1) / float(nw) * a + b)))
        if i == nw - 1 and k != span[1]:
            log.debug('pixelize tweak k')
            k = span[1]
        r[i] = k
        if which == 'max':
            y[i] = x[j:k].max()
        elif which == 'min':
            y[i] = x[j:k].min()
        elif which == 'both':
            y[i * minmax] = x[j:k].max()
            y[i * minmax + 1] = x[j:k].min()
    return (y, n, r)

def mark_span(ax, span):
    ax.axvspan(
        *span,
        edgecolor='0.2',
        facecolor='0.98',
        fill=False,
        linestyle='dotted',
        linewidth=0.8,
        zorder=10,
    )

def axis_defaults(ax):
    ax.tick_params(direction='in', top='off', right='off')
    ax.tick_params(axis='both', which='major', labelsize=FONT_SMALL_SIZE)
    ax.tick_params(axis='both', which='minor', labelsize=FONT_SMALL_SIZE)
    xpad = ax.xaxis.labelpad
    ypad = ax.yaxis.labelpad
    xpos = ax.transAxes.transform((1.0, 0.0))
    xpos[1] -= xpad
    xpos = ax.transAxes.inverted().transform(xpos)
    ypos = ax.transAxes.transform((0.0, 1.0))
    ypos[0] -= ypad
    ypos = ax.transAxes.inverted().transform(ypos)
    ax.xaxis.set_label_coords(*xpos)
    ax.yaxis.set_label_coords(*ypos)
    ax.xaxis.get_label().set_ha('right')
    ax.xaxis.get_label().set_va('top')
    ax.yaxis.get_label().set_ha('right')
    ax.yaxis.get_label().set_va('top')

