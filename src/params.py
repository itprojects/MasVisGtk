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


import numpy as np
import scipy.signal as signal


def ap_coeffs(fc, fs):
    '''
    Discrete first order allpass
    https://ccrma.stanford.edu/realsimple/DelayVar/Phasing_First_Order_Allpass_Filters.html
    http://users.abo.fi/htoivone/courses/sbappl/asp_chapter1.pdf

    T = 1.0/fs
    w_b = 2*np.pi*fc
    p_d = (1 - np.tan(w_b*T/2)) / (1 + np.tan(w_b*T/2))
    b = [p_d, -1.0]
    a = [1.0, -p_d]
    '''
    if fc > fs / 2.0001:
        fc = fs / 2.0001
    rho_b = np.tan(np.pi * fc / fs)
    p_d = (1 - rho_b) / (1 + rho_b)
    b = [p_d, -1.0]
    a = [1.0, -p_d]
    return (b, a)


def kfilter_coeffs(fs):
    # Pre filter
    f0 = 1681.974450955533
    G = 3.999843853973347
    Q = 0.7071752369554196

    K = np.tan(np.pi * f0 / fs)
    Vh = 10.0 ** (G / 20.0)
    Vb = Vh**0.4996667741545416

    a0 = 1.0 + K / Q + K * K
    b0 = (Vh + Vb * K / Q + K * K) / a0
    b1 = 2.0 * (K * K - Vh) / a0
    b2 = (Vh - Vb * K / Q + K * K) / a0
    a1 = 2.0 * (K * K - 1.0) / a0
    a2 = (1.0 - K / Q + K * K) / a0

    b_pre = [b0, b1, b2]
    a_pre = [1.0, a1, a2]

    # Highpass filter
    f0 = 38.13547087602444
    Q = 0.5003270373238773
    K = np.tan(np.pi * f0 / fs)

    a1 = 2.0 * (K * K - 1.0) / (1.0 + K / Q + K * K)
    a2 = (1.0 - K / Q + K * K) / (1.0 + K / Q + K * K)

    b_hp = [1.0, -2.0, 1.0]
    a_hp = [1.0, a1, a2]

    b = signal.convolve(b_pre, b_hp)
    a = signal.convolve(a_pre, a_hp)
    return (b, a)


def fir_coeffs():
    return np.array(
        [
            [
                -0.001780280772489,
                0.003253283030257,
                -0.005447293390376,
                0.008414568116553,
                -0.012363296099675,
                0.017436805871070,
                -0.024020143876810,
                0.032746828420101,
                -0.045326602900760,
                0.066760686868173,
                -0.120643370377371,
                0.989429605248410,
                0.122160009958442,
                -0.046376232812786,
                0.022831393004364,
                -0.011580897261667,
                0.005358105753167,
                -0.001834671998839,
                -0.000103681038815,
                0.001002216283171,
                -0.001293611238062,
                0.001184842429930,
                -0.000908719377960,
                0.002061304229100,
            ],
            [
                -0.001473218555432,
                0.002925336766866,
                -0.005558126468508,
                0.009521159741206,
                -0.015296028027209,
                0.023398977482278,
                -0.034752051245281,
                0.050880967772373,
                -0.075227488678419,
                0.116949442543490,
                -0.212471239510148,
                0.788420616540440,
                0.460788819545818,
                -0.166082211358253,
                0.092555759769552,
                -0.057854829231334,
                0.037380809681132,
                -0.024098441541823,
                0.015115653825711,
                -0.009060645712669,
                0.005033299068467,
                -0.002511544062471,
                0.001030723665756,
                -0.000694079453823,
            ],
            [
                -0.000694079453823,
                0.001030723665756,
                -0.002511544062471,
                0.005033299068467,
                -0.009060645712669,
                0.015115653825711,
                -0.024098441541823,
                0.037380809681132,
                -0.057854829231334,
                0.092555759769552,
                -0.166082211358253,
                0.460788819545818,
                0.788420616540440,
                -0.212471239510148,
                0.116949442543490,
                -0.075227488678419,
                0.050880967772373,
                -0.034752051245281,
                0.023398977482278,
                -0.015296028027209,
                0.009521159741206,
                -0.005558126468508,
                0.002925336766866,
                -0.001473218555432,
            ],
            [
                0.002061304229100,
                -0.000908719377960,
                0.001184842429930,
                -0.001293611238062,
                0.001002216283171,
                -0.000103681038815,
                -0.001834671998839,
                0.005358105753167,
                -0.011580897261667,
                0.022831393004364,
                -0.046376232812786,
                0.122160009958442,
                0.989429605248410,
                -0.120643370377371,
                0.066760686868173,
                -0.045326602900760,
                0.032746828420101,
                -0.024020143876810,
                0.017436805871070,
                -0.012363296099675,
                0.008414568116553,
                -0.005447293390376,
                0.003253283030257,
                -0.001780280772489,
            ],
        ]
    )


c_color = ['blue', 'red', 'green', 'deepskyblue', 'cyan', 'magenta', 'forestgreen', 'chocolate', 'brown', 'crimson', 'gold', 'indigo', 'lime', 'navy', 'olive', 'orange', 'orchid', 'pink', 'purple', 'sienna', 'silver', 'skyblue', 'steelblue', 'violet']


# { key='NAME' : value='DECOMPOSITION'}
channel_layouts_names = {
    'mono':
        [_('Mono')],
    'stereo':
        [_('Left'), _('Right')],
    'downmix':
        [_('Downmix Left'), _('Downmix Right')],
    '2.1':
        [_('Front Left'), _('Front Right'), _('Low Frequency')],
    '3.0':
        [_('Front Left'), _('Front Right'), _('Front Center')],
    '3.0(back)':
        [_('Front Left'), _('Front Right'), _('Back Center')],
    '4.0':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Back Center')],
    'quad':
        [_('Front Left'), _('Front Right'), _('Back Left'), _('Back Right')],
    'quad(side)':
        [_('Front Left'), _('Front Right'), _('Side Left'), _('Side Right')],
    '3.1':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency')],
    '5.0':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Back Left'), _('Back Right')],
    '5.0(side)':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Side Left'), _('Side Right')],
    '4.1':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Center')],
    '5.1':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Left'), _('Back Right')],
    '5.1(side)':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Side Left'), _('Side Right')],
    '6.0':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Back Center'), _('Side Left'), _('Side Right')],
    '6.0(front)':
        [_('Front Left'), _('Front Right'), _('Front Left-of-Center'), _('Front Right-of-Center'), _('Side Left'), _('Side Right')],
    '3.1.2':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Top Front Left'), _('Top Front Right')],
    'hexagonal':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Back Left'), _('Back Right'), _('Back Center')],
    '6.1':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Center'), _('Side Left'), _('Side Right')],
    '6.1(back)':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Left'), _('Back Right'), _('Back Center')],
    '6.1(front)':
        [_('Front Left'), _('Front Right'), _('Low Frequency'), _('Front Left-of-Center'), _('Front Right-of-Center'), _('Side Left'), _('Side Right')],
    '7.0':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Back Left'), _('Back Right'), _('Side Left'), _('Side Right')],
    '7.0(front)':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Front Left-of-Center'), _('Front Right-of-Center'), _('Side Left'), _('Side Right')],
    '7.1':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Left'), _('Back Right'), _('Side Left'), _('Side Right')],
    '7.1(wide)':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Left'), _('Back Right'), _('Front Left-of-Center'), _('Front Right-of-Center')],
    '7.1(wide-side)':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Front Left-of-Center'), _('Front Right-of-Center'), _('Side Left'), _('Side Right')],
    '5.1.2':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Left'), _('Back Right'), _('Top Front Left'), _('Top Front Right')],
    'octagonal':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Back Left'), _('Back Right'), _('Back Center'), _('Side Left'), _('Side Right')],
    'cube':
        [_('Front Left'), _('Front Right'), _('Back Left'), _('Back Right'), _('Top Front Left'), _('Top Front Right'), _('Top Back Left'), _('Top Back Right')],
    '5.1.4':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Left'), _('Back Right'), _('Top Front Left'), _('Top Front Right'), _('Top Back Left'), _('Top Back Right')],
    '7.1.2':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Left'), _('Back Right'), _('Side Left'), _('Side Right'), _('Top Front Left'), _('Top Front Right')],
    '7.1.4':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Left'), _('Back Right'), _('Side Left'), _('Side Right'), _('Top Front Left'), _('Top Front Right'), _('Top Back Left'), _('Top Back Right')],
    'hexadecagonal':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Back Left'), _('Back Right'), _('Back Center'), _('Side Left'), _('Side Right'), _('Top Front Left'), _('Top Front Center'), _('Top Front Right'), _('Top Back Left'), _('Top Back Center'), _('Top Back Right'), _('Wide Left'), _('Wide Right')],
    '22.2':
        [_('Front Left'), _('Front Right'), _('Front Center'), _('Low Frequency'), _('Back Left'), _('Back Right'), _('Front Left-of-Center'), _('Front Right-of-Center'), _('Back Center'), _('Side Left'), _('Side Right'), _('Top Center'), _('Top Front Left'), _('Top Front Center'), _('Top Front Right'), _('Top Back Left'), _('Top Back Center'), _('Top Back Right'), _('Low Frequency 2'), _('Top Side Left'), _('Top Side Right'), _('Bottom Front Center'), _('Bottom Front Left'), _('Bottom Front Right')]
}


# { key='NAME' : value='WEIGHTING'}
# > 7.2 channels = guesswork.
channel_layouts_params = {
    'mono':#FC
        [1.0],
    'stereo':#FL+FR
        [1.0, 1.0],
    'downmix':#DL+DR
        [1.0, 1.0],
    '2.1':#FL+FR+LFE
        [1.0, 1.0, 0.0],
    '3.0':#FL+FR+FC
        [1.0, 1.0, 1.0],
    '3.0(back)':#FL+FR+BC
        [1.0, 1.0, 1.0],
    '4.0':#FL+FR+FC+BC
        [1.0, 1.0, 1.0, 1.0],
    'quad':#FL+FR+BL+BR
        [1.0, 1.0, 1.41, 1.41],
    'quad(side)':#FL+FR+SL+SR
        [1.0, 1.0, 1.41, 1.41],
    '3.1':#FL+FR+FC+LFE
        [1.0, 1.0, 1.0, 0.0],
    '5.0':#FL+FR+FC+BL+BR
        [1.0, 1.0, 1.0, 1.41, 1.41],
    '5.0(side)':#FL+FR+FC+SL+SR
        [1.0, 1.0, 1.0, 1.41, 1.41],
    '4.1':#FL+FR+FC+LFE+BC
        [1.0, 1.0, 1.0, 0.0, 1.0],
    '5.1':#FL+FR+FC+LFE+BL+BR
        [1.0, 1.0, 1.0, 0.0, 1.41, 1.41],
    '5.1(side)':#FL+FR+FC+LFE+SL+SR
        [1.0, 1.0, 1.0, 0.0, 1.41, 1.41],
    '6.0':#FL+FR+FC+BC+SL+SR
        [1.0, 1.0, 1.0, 1.0, 1.41, 1.41],
    '6.0(front)':#FL+FR+FLC+FRC+SL+SR
        [1.0, 1.0, 1.0, 1.0, 1.41, 1.41],
    '3.1.2':#FL+FR+FC+LFE+TFL+TFR
        [1.0, 1.0, 1.0, 0.0, 1.0, 1.0],
    'hexagonal':#FL+FR+FC+BL+BR+BC
        [1.0, 1.0, 1.0, 1.41, 1.41, 1.0],
    '6.1':#FL+FR+FC+LFE+BC+SL+SR
        [1.0, 1.0, 1.0, 0.0, 1.0, 1.41, 1.41],
    '6.1(back)':#FL+FR+FC+LFE+BL+BR+BC
        [1.0, 1.0, 1.0, 0.0, 1.41, 1.41, 1.0],
    '6.1(front)':#FL+FR+LFE+FLC+FRC+SL+SR
        [1.0, 1.0, 0.0, 1.0, 1.0, 1.41, 1.41],
    '7.0':#FL+FR+FC+BL+BR+SL+SR
        [1.0, 1.0, 1.0, 1.41, 1.41, 1.41, 1.41],
    '7.0(front)':#FL+FR+FC+FLC+FRC+SL+SR
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.41, 1.41],
    '7.1':#FL+FR+FC+LFE+BL+BR+SL+SR
        [1.0, 1.0, 1.0, 0.0, 1.41, 1.41, 1.41, 1.41],
    '7.1(wide)':#FL+FR+FC+LFE+BL+BR+FLC+FRC
        [1.0, 1.0, 1.0, 0.0, 1.41, 1.41, 1.0, 1.0],
    '7.1(wide-side)':#FL+FR+FC+LFE+FLC+FRC+SL+SR
        [1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.41, 1.41],
    '5.1.2':#FL+FR+FC+LFE+BL+BR+TFL+TFR
        [1.0, 1.0, 1.0, 0.0, 1.41, 1.41, 1.0, 1.0],
    'octagonal':#FL+FR+FC+BL+BR+BC+SL+SR
        [1.0, 1.0, 1.0, 1.41, 1.41, 1.0, 1.41, 1.41],
    'cube':#FL+FR+BL+BR+TFL+TFR+TBL+TBR
        [1.0, 1.0, 1.41, 1.41, 1.0, 1.0, 1.0, 1.0],
    '5.1.4':#FL+FR+FC+LFE+BL+BR+TFL+TFR+TBL+TBR
        [1.0, 1.0, 1.0, 0.0, 1.41, 1.41, 1.0, 1.0, 1.0, 1.0],
    '7.1.2':#FL+FR+FC+LFE+BL+BR+SL+SR+TFL+TFR
        [1.0, 1.0, 1.0, 0.0, 1.41, 1.41, 1.41, 1.41, 1.0, 1.0],
    '7.1.4':#FL+FR+FC+LFE+BL+BR+SL+SR+TFL+TFR+TBL+TBR
        [1.0, 1.0, 1.0, 0.0, 1.41, 1.41, 1.41, 1.41, 1.0, 1.0, 1.0, 1.0],
    'hexadecagonal':#FL+FR+FC+BL+BR+BC+SL+SR+TFL+TFC+TFR+TBL+TBC+TBR+WL+WR
        [1.0, 1.0, 1.0, 1.41, 1.41, 1.0, 1.41, 1.41, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    '22.2':#FL+FR+FC+LFE+BL+BR+FLC+FRC+BC+SL+SR+TC+TFL+TFC+TFR+TBL+TBC+TBR+LFE2+TSL+TSR+BFC+BFL+BFR
        [1.0, 1.0, 1.0, 0.0, 1.41, 1.41, 1.0, 1.0, 1.0, 1.41, 1.41, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.41, 1.41, 1.0, 1.0, 1.0]
}


understanding_graphs = _('''
<i>See the <b>glossary at the end</b> for <b>audio terms</b> and <b>definitions</b>.</i>\n
## <span size="larger"><b>The Overview Graph</b></span>\n
The overview graph is appropriate for displaying condensed information about an entire album. It shows the waveforms from the left and the right channels superimposed on each other. The left channel is shown in blue, the right in red. Parts where left and right channels overlap are shown in black. If a lot of color is shown, the channels are quite different.\n
The crest factor, and the level of the highest peak, are shown to the right of each graphs. The value can differ from those in the detailed analysis, since the left and right channels are analyzed as one.\n
## <span size="larger"><b>The detailed analysis graph</b></span>\n
The detailed analysis graph shows a deeper analysis of a single track. Each graph shows a different aspect of the track, as described below.\n
### <span size="large"><b>Left and Right</b></span>\n
The top graphs show the waveforms of the left and right channels, quite like in the overview graph, but separately. The crest factor, the RMS level, and the peak levels of the channels, appear above the graphs.\n
### <span size="large"><b>The loudest part</b></span>\n
In order to show how the strongest part of the track has survived the mastering processing, MasVis looks for a strong part of the track, and zooms-in on that. Around the selected part, a window of 100 milliseconds is shown. Clipping and/or brickwall limitation is typically revealed here.\n
The part show is not selectable by the user, in accordance with the idea that the MasVis graphs should appear the same, regardless of who does the analysis. The selection is automatically made, by MasVis, in the following way:\n
1. Find the highest sample value in the sound file\n
2. Apply a threshold of 95 percent of the highest sample value\n
3. For every place, that the signal exceeds the threshold, count how many samples exceed the threshold\n
4. Select the place, where the highest number of samples exceeding the threshold occur\n
The sample count, for the selected part, is displayed above the graph.\n
### <span size="large"><b>Normalized average sepctrum</b></span>\n
This graph shows the average spectrum of the signal. The graph is made by averaging 1-second Blackman windows of the signal. This graph can be used to identify timbral properties of the signal. The sloping solid lines drop by 6dB/octave and can serve as a reference for judging the spectral content of the track.\n
Even though this graph does not differentiate between mastering processing and the rest of the production, including the instruments, it is very useful, for comparing different releases of the same album. "Remastered" versions of albums often come with various spectral changes, and these are revealed in the spectrum graph quite clearly, when flipping between the two versions.\n
The spectrum graph is normalized, that is, the RMS level of the signal does not affect the graph at all.\n
### <span size="large"><b>Allpassed crest factor</b></span>\n
Is probably the most revealing graph in MasVis. It gives an estimate of how much the crest factor has been lowered, by the processing of the 2-channel master. In the graph, there are four curves, two red for the right channel, and two blue for the left channel. The dashed line shows the crest factor, i.e. the same information as above the waveform graphs. The solid line shows the crest factor of the signal after it has passed an allpass filter. The second crest factor is a rough, and typically underestimated value of how large the crest factor was prior to level maximation of the 2-channel master.\n
At first, it may seem impossible to make such an estimate, but experience shows that the method works. Of course, it does not give an exact value of the original crest factor, but it is good enough to tell when the track has been subjected to destructive loudness maximation.\n
The difference between the maximum in the solid line, and the dashed line, correlates quite well with the amount of crest factor loss that is a result of level maximation of the 2-channel mix.\n
Here is the method that MasVis uses, to make the graph:\n
1. Draw a dashed line, at the crest factor of the track\n
2. Run the track through seven different first order allpass filters at 20, 60, 200, 600, 2000, 6000, and 20000 Hz\n
3. For each of the seven filtered signals, calculate a new crest factor value\n
4. Plot a solid line, representing the crest factors of the seven signals, as a funciton of filter frequency\n
### <span size="large"><b>Histogram</b></span>\n
In 16 bit audio, such as on a CD, the waveform is represented by 16-bit numbers, giving a range of -32768 to +32727 for the sample values. Some values are more common than others. If, for example, the tracks is a completely quiet, that is all sample values are 0, the sample value 0 becomes very common. If there is a weak sound, small sample values become common, and if the signal is extremely loud  and clipped, the extreme sample values become common instead.\n
The histogram shows the number of samples for each sample value. A track that contains complete silence will show a peak near 0, and a track that contains clipping will show peaks at the high and/or low ends of the histogram.\n
It can be shown by statistical analysis that the sum of many signals with a reasonably constant amplitude over time, will result in a "normal distribution". Such a distribution takes the shape of a parabola if the y-axis is logarithmic (as in MasVis). If the signals do not have constant amplitudes, but amplitudes that vary over time, the shape becomes more like a pyramid, with approximately linear slopes.\n
However, the histogram of the sum of many uncorrelated signals, never has abrupt endings. Such abrupt endings only occur if the signals are correlated (which they almost never are), or if the 2-channel mix has been tampered.\n
One would expect a histogram with smooth slopes for any mix of several signals, unless the 2-channel mix has been subjected to clipping or brickwall limitation. Thus, the histogram is useful for revealing clipping and limitation.\n
The "bits" number, above the histogram, indicates how many of the 65536 levels, occur at least once in the sound file. If all 65536 sample levels occur in the sound file, the number of bits is shown as 16,0. If only half of them are used, (i.e. 32768), then 15,0 is shown. In mathematical terms, the number that is shown is the 2-logarithm of the number of used sample levels. Somewhat counterintuitive, recordings that have been subjected to mastering processing typically come near to 16,0 "bits", whereas unprocessed recordings at full scale typically reach 14-15 "bits".\n
### <span size="large"><b>Peak vs. RMS level</b></span>\n
This graph is based on 1 second long frames of the signal, and each is represented by a circle in the diagram. For each frame, the RMS and peak levels also give the crest factor. The crest factor for each frame can also be read from the diagram.\n
This graph is useful for showing the dynamics of the track. If a signal is amplified, the circle moves up towards the right, since both the peak and the RMS increase by the same amount. When the circles reach the top, further RMS increase is only possible if the crest factor is lowered.\n
Too many modern productions are very crowded in the upper right corner.\n
### <span size="large"><b>Short term crest factor</b></span>\n
Each of the circles in the Peak vs. RMS graph, also appear in the short term crest factor graph. Here, the crest factor of the 1-second windows is displayed against time. It is beneficial to compare this graph with the waveform graphs.\n
For natural, unprocessed sounds, the crest factor typically increases a bit, when the sound is louder. Loud sound is typically associated with a richer spectrum and an increased number of sound sources. Both these factors increase the crest factor. However, if the 2-channel mix has been subjected to clipping or limitation, the crest factor is typically lowered, when the sound becomes loud.\n
## <span size="larger"><b>Glossary</b></span>\n
### <span size="large"><b>Crest factor</b></span>\n
The crest factor is the ratio between the peak value and the RMS value during a frame. The crest factor is mostly expressed in decibels [dB], and if so, it is the difference between the peak level [dB] and the RMS level [dB]. The crest factor is never negative. A sinusoid has a crest factor of 3 dB, and a square wave 0 dB.\n
### <span size="large"><b>Spectrum</b></span>\n
A sepctrum graph is the result of a Fourier transform (FFT), and shows how the energy (in a signal) is distributed across different frequencies.\n
### <span size="large"><b>Peak and RMS values</b></span>\n
The RMS (root mean square) value is proportional to the average power of a signal seen over some time. The peak value, is the maximum absolute value within that time period.\n
### <span size="large"><b>Frame</b></span>\n
A frame is a short or long part of the sound signal. In MasVis, 1-second frames are used to generate the spectrum and the short term crest factor graph.\n
### <span size="large"><b>Allpass filter</b></span>\n
An allpass filter lets all frequencies pass, without attenuation or amplification. However, the phases of different frequencies are shifted differently. The result is a signal that sounds very similar to the original signal, but with a different waveform.\n
### <span size="large"><b>Checksum</b></span>\n
Checksums are used frequently to ensure the integrity of data file. Checksum algorithms produce results that are quite different, even if only a single bit is changed.  The checksum algorithm in MasVis is different, in that it remains the same if silence is added to the file.\n
### <span size="large"><b>Histogram</b></span>\n
A histogram is a diagram that tells "how many of each there are". For example, a simple histogram may show how many students have passed or failed an exam. This histogram would have only two bars: pass and fail. The histogram in MasVis has 65536 bars internally, each representing one level in the 16 bit PCM format. These bars are presented in the histogram, showing if some sample levels are more common than others.
''')
