/*
Copyright 2024 ITProjects

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
*/

#pragma once

#include <JuceHeader.h>
#include <fstream>//debugging to file as DAW plugin

class MasVisGtkPluginAudioProcessor : public juce::AudioProcessor, public juce::ChangeBroadcaster
{
public:
    MasVisGtkPluginAudioProcessor();
    ~MasVisGtkPluginAudioProcessor() override;

    void prepareToPlay(double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;

#ifndef JucePlugin_PreferredChannelConfigurations
    bool isBusesLayoutSupported(const BusesLayout& layouts) const override;
#endif

    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override;

    const juce::String getName() const override;

    bool acceptsMidi() const override;
    bool producesMidi() const override;
    bool isMidiEffect() const override;
    double getTailLengthSeconds() const override;

    int getNumPrograms() override;
    int getCurrentProgram() override;
    void setCurrentProgram(int index) override;
    const juce::String getProgramName(int index) override;
    void changeProgramName(int index, const juce::String& newName) override;

    void getStateInformation(juce::MemoryBlock& destData) override;
    void setStateInformation(const void* data, int sizeInBytes) override;

    void clear();
    void prepare_params();
    float db(float a, float b);
    float rms(float mean, int total_samples);
    void set_ap_freqs(int index);

    //std::ofstream log_file;//debug logging

    bool is_plugin_enabled = true;

    bool do_init = false;//controls resets
    
    bool ready_to_paint = true;//optimal painting

    bool invert_cf_plot = false;//shows vertically flipped plot

    juce::String processing_error;//error recorded here

    float y_offset = 300.0f;
    float x_offset_ap = 35.0f;
    float y_offset_ap = 149.0f;
    float y_scale_ap = 5;//px/dB scale factor

    std::vector<float> histogram_channel_minimums;
    std::vector<float> histogram_channel_maximums;
    std::vector<std::unordered_map<int, float>> histogram_bins;

    //graphical representations of histogram (as lines)
    std::vector<juce::Path> histogram_paths;

    //allpass crest factor analysis parameters
    std::vector<std::vector<float>> ap_ba;

    int crest_plot_type_choice = 1;//default = 1

    size_t len_ap_freq = 7;//size of ap_freq, default = 7
    std::vector<float> ap_freqs = { 20.0f, 60.0f, 200.0f, 600.0f, 2000.0f, 6000.0f, 20000.0f };

    //log10 locations by default
    std::vector<float> ap_freq_px_locations =
    {
        35.000f, 82.712f, 135.000f, 182.712f, 235.000f,
        282.712f, 335.000f
    };

    //=========================================================================

    //7 default frequencies
    float ap_freqs_default[7] = { 20.0f, 60.0f, 200.0f, 600.0f, 2000.0f, 6000.0f, 20000.0f };

    float ap_freq_px_locations_default[7] =
    {
        35.000f, 82.712f, 135.000f, 182.712f, 235.000f,
        282.712f, 335.000f
    };

    //10 ISO 266:1997(E)

    float ap_freqs_10_octave[10] = { 31.62f, 63.10f, 125.89f, 251.19f, 501.19f, 1000.0f, 1995.3f, 3981.1f, 7943.3f, 15848.3f };

    float ap_freq_px_locations_10_octave[10] =
    {
        35.000f, 68.341f, 101.669f, 135.004f, 168.337f,
        201.670f, 235.004f, 268.336f, 301.669f, 335.000f
    };

    //31 octaves

    float ap_freqs_31_octave[31] =
    {
        20.0f, 25.0f, 31.5f, 40.0f, 50.0f, 63.0f, 80.0f, 100.0f, 125.0f, 160.0f,
        200.0f, 250.0f, 315.0f, 400.0f, 500.0f, 630.0f, 800.0f, 1000.0f, 1250.0f, 1600.0f,
        2000.0f, 2500.0f, 3150.0f, 4000.0f, 5000.0f, 6300.0f, 8000.0f, 10000.0f, 12500.0f, 16000.0f,
        20000.0f
    };

    float ap_freq_px_locations_31_octave[31] =
    {
        35.000f, 44.691f, 54.728f, 65.103f, 74.794f,
        84.831f, 95.206f, 104.897f, 114.588f, 125.309f,
        135.000f, 144.691f, 154.728f, 165.103f, 174.794f,
        184.831f, 195.206f, 204.897f, 214.588f, 225.309f,
        235.000f, 244.691f, 254.728f, 265.103f, 274.794f,
        284.831f, 295.206f, 304.897f, 314.588f, 325.309f,
        335.000f
    };

    //=========================================================================
    //normalisation procedure for frequency range, of a linear scale
    //float min_frequency = 20.0f;
    //float max_frequency = 20000.0f;
    //for (auto frequency : ap_freqs):
    //    normalised_frequency = (frequency - min_frequency) / (max_frequency - min_frequency)
    //    pixel_value = 300 * normalised_frequency//range of 300 pixels
    //
    //normalisation procedure for frequency range, of a log10 scale
    //float log10_min = log10(ap_freqs[0]);
    //float log10_max = log10(ap_freqs[len_ap_freq - 1]);
    //float px_min = x_offset_ap;
    //float px_max = x_offset_ap + 300;// range of 300 pixels
    //float px_scaled_value_log10 = px_min + (px_max - px_min) * ((log10(ap_freqs[j]) - log10_min) / (log10_max - log10_min));
    //=========================================================================

    int nc = 0;//number of channels in audio
    float fs = 0;//sample rate of audio
    int samples_per_block = 0;//samples per block from DAW
    int total_samples = 0;//total samples

    //dynamic range measurements
    std::vector<float> dr_measurements;
    float dr_measurements_avg = 0.0f;
    juce::String dr_measurements_avg_text = juce::String("DR 00.0");
    juce::String dr_measurements_channels_text = juce::String("No measurements");

    //abs(peak) blocks, on every channel
    std::vector<std::vector<float>> dr_channel_block_peaks;

    //channel rms blocks, on every channel
    std::vector<std::vector<float>> dr_channel_block_rms;
    
    //number of samples ber block can be different in channel end
    //tail remainders of samples not in 3 second blocks
    std::vector<int> dr_channel_block_tail_rms;

    //channel rms block size, number of samples for 3 seconds
    int dr_blocks = 0;

    //samples processed in blocs, requiring cached variables
    std::vector<std::vector<int>> current_samples;
    std::vector<std::vector<float>> last_sample_caches;
    std::vector<std::vector<float>> previous_y_sample_caches;

    //allpass crest factors index of maximum value per channel
    //shown as bold font in table
    std::vector<int> ap_peak_index;

    //allpass peak per channel and frequency
    std::vector<std::vector<float>> ap_peak;

    //allpass lfiler rms of  per channel and frequency
    std::vector<std::vector<float>> ap_rms;

    //allpass crest factors per channel and frequency
    std::vector<std::vector<float>> ap_crest;

    std::vector<std::vector<juce::String>> ap_crest_strings;//holds

    //channel total peak, rms, crest factor
    std::vector<std::vector<float>> total_peak_rms_cf;

    //graphical representations of allpass crest factor
    std::vector<juce::Path> allpass_crest_factor_paths;

    //graphical overall dashed allpass crest factor lines
    std::vector<juce::Line<float>> cf_lines;

    //holds differences between crest factor lines
    std::vector<std::vector<juce::String>> table_crest_factor_params;

private:
    const float pi = (float) 3.141592653589793;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MasVisGtkPluginAudioProcessor)
};
