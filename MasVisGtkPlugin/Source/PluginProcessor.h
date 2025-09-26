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

    //std::ofstream log_file;//debug logging

    bool is_plugin_enabled = true;

    bool do_init = false;//controls resets
    
    bool ready_to_paint = true;//optimal painting

    juce::String processing_error;//error recorded here

    int x_offset_hist = 5;
    float x_offset_ap = 635;
    float y_offset = 304;

    std::vector<float> histogram_channel_minimums;
    std::vector<float> histogram_channel_maximums;
    std::vector<std::unordered_map<int, float>> histogram_bins;

    //graphical representations of histogram (as lines)
    std::vector<juce::Path> histogram_paths;

    //allpass crest factor analysis parameters
    //should be renewed for every render.
    const int len_ap_freq = 7;//size of ap_freq
    int ap_freqs[7] = { 20, 60, 200, 600, 2000, 6000, 20000 };
    std::vector<std::vector<float>> ap_ba;

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

    //allpass peak per channel and frequency
    std::vector<std::vector<float>> ap_peak;

    //allpass lfiler rms of  per channel and frequency
    std::vector<std::vector<float>> ap_rms;

    //allpass crest factors per channel and frequency
    std::vector<std::vector<float>> ap_crest;

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
