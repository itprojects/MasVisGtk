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

#include "PluginProcessor.h"
#include "PluginEditor.h"
#include <cmath>

MasVisGtkPluginAudioProcessor::MasVisGtkPluginAudioProcessor()
#ifndef JucePlugin_PreferredChannelConfigurations
    : AudioProcessor(BusesProperties()
#if ! JucePlugin_IsMidiEffect
#if ! JucePlugin_IsSynth
        .withInput("Input", juce::AudioChannelSet::stereo(), true)
#endif
        .withOutput("Output", juce::AudioChannelSet::stereo(), true)
#endif
    )
#endif
{
    //debugging to file as DAW plugin
    //log_file.open("C:\\Users\\tester\\masvisgtk_log.txt", std::ios::out | std::ios::app | std::ios::binary);
    //log_file << "Writing in the log file." << std::endl;
}

MasVisGtkPluginAudioProcessor::~MasVisGtkPluginAudioProcessor()
{
}

#ifndef JucePlugin_PreferredChannelConfigurations
bool MasVisGtkPluginAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
#if JucePlugin_IsMidiEffect
    juce::ignoreUnused(layouts);
    return true;
#else
    // This is the place where you check if the layout is supported.
    // In this template code we only support mono or stereo.
    // Some plugin hosts, such as certain GarageBand versions, will only
    // load plugins that support stereo bus layouts.
    if (layouts.getMainOutputChannelSet() != juce::AudioChannelSet::mono()
        && layouts.getMainOutputChannelSet() != juce::AudioChannelSet::stereo())
        return false;

    // This checks if the input layout matches the output layout
#if ! JucePlugin_IsSynth
    if (layouts.getMainOutputChannelSet() != layouts.getMainInputChannelSet())
        return false;
#endif

    return true;
#endif
}
#endif

const juce::String MasVisGtkPluginAudioProcessor::getName() const
{
    return JucePlugin_Name;
}

bool MasVisGtkPluginAudioProcessor::acceptsMidi() const
{
#if JucePlugin_WantsMidiInput
    return true;
#else
    return false;
#endif
}

bool MasVisGtkPluginAudioProcessor::producesMidi() const
{
#if JucePlugin_ProducesMidiOutput
    return true;
#else
    return false;
#endif
}

bool MasVisGtkPluginAudioProcessor::isMidiEffect() const
{
#if JucePlugin_IsMidiEffect
    return true;
#else
    return false;
#endif
}

double MasVisGtkPluginAudioProcessor::getTailLengthSeconds() const
{
    return 0.0;
}

int MasVisGtkPluginAudioProcessor::getNumPrograms()
{
    return 1;   // NB: some hosts don't cope very well if you tell them there are 0 programs,
    // so this should be at least 1, even if you're not really implementing programs.
}

int MasVisGtkPluginAudioProcessor::getCurrentProgram()
{
    return 0;
}

void MasVisGtkPluginAudioProcessor::setCurrentProgram(int index)
{
}

const juce::String MasVisGtkPluginAudioProcessor::getProgramName(int index)
{
    return {};
}

void MasVisGtkPluginAudioProcessor::changeProgramName(int index, const juce::String& newName)
{
}

void MasVisGtkPluginAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    if (is_plugin_enabled)
    {
        processing_error = juce::String("");//reset errors
        fs = (float)sampleRate;
        do_init = true;//trigger init in processBlock()
        dr_blocks = (int)(3.0 * sampleRate);
        samples_per_block = samplesPerBlock;
    }
}

void MasVisGtkPluginAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages)
{
    if (is_plugin_enabled)
    {

        juce::ScopedNoDenormals noDenormals;
        auto totalNumInputChannels = getTotalNumInputChannels();
        auto totalNumOutputChannels = getTotalNumOutputChannels();

        if (do_init)
        {
            nc = totalNumInputChannels;//number of channels in audio
            total_samples = 0;
            clear();
            prepare_params();
            do_init = false;
        }

        for (auto i = totalNumInputChannels; i < totalNumOutputChannels; ++i)
            buffer.clear(i, 0, buffer.getNumSamples());

        int n_samples = buffer.getNumSamples();
        total_samples += n_samples;//total_samples is per channel

        for (int channel = 0; channel < totalNumInputChannels; ++channel)
        {
            float last_sample = 0.0f;
            float previous_y_sample = 0.0f;
            float cache_sum_of_square_block = 0.0f;
            float cache_sum_of_squares_local = 0.0f;
            float cache_sum_of_squares_total = 0.0f;

            //create first rms and peak blocks on channel
            if (dr_channel_block_rms.at(channel).size() == 0)
            {
                dr_channel_block_rms.at(channel).push_back(0.0f);
                dr_channel_block_peaks.at(channel).push_back(0.0f);
            }

            for (int ith_freq = 0; ith_freq < len_ap_freq; ++ith_freq)
            {
                for (int nth_sample = 0; nth_sample < n_samples; ++nth_sample)
                {
                    float sample = buffer.getSample(channel, nth_sample);//new sample to process

                    if (nth_sample == 0)//restore cached values
                    {
                        last_sample = last_sample_caches.at(channel).at(ith_freq);
                        previous_y_sample = previous_y_sample_caches.at(channel).at(ith_freq);
                        cache_sum_of_squares_local = ap_rms.at(channel).at(ith_freq);
                        cache_sum_of_squares_total = total_peak_rms_cf.at(channel).at(1);
                    }

                    //calculate channel histogram, peak, rms, dr,
                    //only once, in the first processed frequency,
                    //calculation is the same for evey frequency
                    if (ith_freq == 0)
                    {
                        //block peak finding, dynaimc range
                        if (std::fabs(sample) > dr_channel_block_peaks.at(channel).back())
                            dr_channel_block_peaks.at(channel).back() = std::fabs(sample);

                        //total channel peak, crest factor
                        if (std::fabs(sample) > total_peak_rms_cf.at(channel).at(0))
                            total_peak_rms_cf.at(channel).at(0) = std::fabs(sample);

                        //rms, dynamic range
                        cache_sum_of_square_block = sample * sample;
                        dr_channel_block_rms.at(channel).back() += cache_sum_of_square_block;

                        //check if new rms block should be create, dynamic range
                        if ((total_samples - n_samples + (nth_sample + 1)) % dr_blocks == 0)
                        {
                            dr_channel_block_rms.at(channel).push_back(0);
                            dr_channel_block_peaks.at(channel).push_back(0.0f);

                            //marking tail samples index (last remaining)
                            dr_channel_block_tail_rms.at(channel) = current_samples.at(channel)[0] + 1;
                        }

                        //rms, crest factor
                        cache_sum_of_squares_total += cache_sum_of_square_block;

                        //histogram, expecting samples to be -1.0f to 1.0f, i.e. 0.5555f
                        int hist_value = std::lround(sample * 300);// or 100 for -100:100
                        if (hist_value <= -300)
                        {
                            histogram_bins[channel][-300] += 1;//left shoulder of histogram
                        }
                        else if (hist_value >= 300)
                        {
                            histogram_bins[channel][300] += 1;//right shoulder of histogram
                        }
                        else
                        {
                            histogram_bins[channel][hist_value] += 1;
                        }
                    }

                    float y_sample = 0.0f;//lfilter value of sample
                    if (current_samples.at(channel).at(ith_freq) >= 1)
                    {
                        y_sample = ap_ba.at(ith_freq)[0] * sample;
                        y_sample = y_sample + ap_ba.at(ith_freq)[1] * last_sample;
                        y_sample = y_sample - ap_ba.at(ith_freq)[3] * previous_y_sample;
                    }

                    //store processed local peak maxima
                    if (y_sample > ap_peak[channel][ith_freq])
                        ap_peak[channel][ith_freq] = y_sample;

                    last_sample = sample;
                    previous_y_sample = y_sample;

                    cache_sum_of_squares_local += y_sample * y_sample;

                    //store values for next loop iteration
                    if (nth_sample + 1 == n_samples)
                    {
                        last_sample_caches.at(channel).at(ith_freq) = sample;
                        previous_y_sample_caches.at(channel).at(ith_freq) = y_sample;
                        ap_rms.at(channel).at(ith_freq) = cache_sum_of_squares_local;
                        total_peak_rms_cf.at(channel).at(1) = cache_sum_of_squares_total;
                    }

                    //keep count of processed samples
                    ++current_samples.at(channel).at(ith_freq);
                }
            }
        }
    }
}

void MasVisGtkPluginAudioProcessor::releaseResources()
{
    if (is_plugin_enabled) {
        try {
            if (dr_channel_block_rms.size() > 0)
            {
                if (dr_channel_block_rms[0].size() >= 3)//check 3 seconds minimum
                {
                    for (int channel = 0; channel < nc; ++channel)
                    {
                        // Is array non-zero valued
                        bool array_has_values = false;
                        for (int i = -300; i < 301; ++i)
                        {
                            if (histogram_bins[channel][i] > 0)
                            {
                                if (!array_has_values)
                                    array_has_values = true;

                                histogram_bins[channel][i] = log2(histogram_bins[channel][i]);//log2 scaling of data

                                //find minimum and maximum (log2) per channel
                                if (histogram_bins[channel][i] < histogram_channel_minimums[channel])
                                    histogram_channel_minimums[channel] = histogram_bins[channel][i];//minimum

                                if (histogram_bins[channel][i] > histogram_channel_maximums[channel])
                                    histogram_channel_maximums[channel] = histogram_bins[channel][i];//maximum
                            }
                        }

                        if (array_has_values)
                        {
                            for (int i = -300; i < 301; ++i)
                            {
                                if (histogram_bins[channel][i] > 0)
                                {
                                    //min-max peak scaling, width:height 600 3:2 ratio, 200 for peak
                                    float rescaled = 200 * (
                                        (histogram_bins[channel][i] - histogram_channel_minimums[channel]) /
                                        (histogram_channel_maximums[channel] - histogram_channel_minimums[channel])
                                        );

                                    if (rescaled > 0)
                                        histogram_bins[channel][i] = std::roundf(y_offset - rescaled);//ints for pixels
                                }
                                else
                                {
                                    histogram_bins[channel][i] = y_offset;
                                }

                                //prepare histogram paths
                                if (i == -300)//renew path(s) at first index
                                {
                                    histogram_paths[channel].startNewSubPath
                                    (
                                        (float)(x_offset_hist + i + 300),
                                        y_offset
                                    );
                                }
                                else
                                {
                                    //add points to path
                                    histogram_paths[channel].lineTo
                                    (
                                        (float)(x_offset_hist + i + 300),
                                        histogram_bins[channel][i]
                                    );
                                }
                            }
                        }
                    }

                    for (int j = 0; j < len_ap_freq; ++j)
                    {
                        for (int i = 0; i < nc; ++i)
                        {
                            //final parameter calculations
                            ap_rms[i][j] = rms(ap_rms[i][j], total_samples);
                            ap_crest[i][j] = db(ap_peak[i][j], ap_rms[i][j]);

                            //prepare allpass crest factor paths
                            if (j == 0)//renew path(s) at first index
                            {
                                allpass_crest_factor_paths[i].startNewSubPath(
                                    x_offset_ap + (50 * j),
                                    std::roundf(y_offset - (10 * ap_crest[i][j]))
                                );
                            }
                            else
                            {
                                //add points to path
                                allpass_crest_factor_paths[i].lineTo(
                                    x_offset_ap + (50 * j),//50 pixels separation at 300 px horizontal width
                                    std::roundf(y_offset - (10 * ap_crest[i][j]))
                                );
                            }
                        }
                    }

                    for (int channel = 0; channel < nc; ++channel)
                    {
                        total_peak_rms_cf[channel][1] = rms(total_peak_rms_cf[channel][1], total_samples);
                        total_peak_rms_cf[channel][2] = db(total_peak_rms_cf[channel][0], total_peak_rms_cf[channel][1]);

                        //make crest factor lines
                        float y_dimension = y_offset - (10 * total_peak_rms_cf[channel][2]);
                        cf_lines.push_back
                        (
                            juce::Line<float>((float)x_offset_ap, y_dimension, (float)x_offset_ap + 300, y_dimension)
                        );
                    }

                    for (int channel = 0; channel < nc; ++channel)
                    {
                        int dr_blocks_ = dr_blocks;
                        int tail_samples = total_samples - dr_channel_block_tail_rms.at(channel);
                        for (size_t i = 0; i < dr_channel_block_rms[channel].size(); ++i)
                        {
                            if ((i == dr_channel_block_rms[channel].size() - 1) && tail_samples > 0)
                            {
                                //rms tail block size to rms block size
                                dr_blocks_ = tail_samples;
                            }
                            //process rms or rms tail block
                            dr_channel_block_rms[channel][i] = std::sqrt(
                                2 * (dr_channel_block_rms[channel][i] / dr_blocks_)
                            );
                        }
                    }

                    for (int channel = 0; channel < dr_channel_block_peaks.size(); ++channel)
                    {
                        std::sort(dr_channel_block_peaks[channel].begin(), dr_channel_block_peaks[channel].end());
                    }

                    //sort rms blocks in ascending order 0.1, 0.2, 0.3
                    for (int channel = 0; channel < dr_channel_block_rms.size(); ++channel)
                    {
                        std::sort(dr_channel_block_rms[channel].begin(), dr_channel_block_rms[channel].end());
                    }

                    int dr_20 = (int)std::round(0.2 * dr_channel_block_rms[0].size());
                    if (dr_20 < 1)
                        throw std::invalid_argument("Too few blocks.\nMinimum 3 seconds of audio. (1)");

                    //calculate channel dynamic range
                    for (int channel = 0; channel < nc; ++channel)
                    {
                        //remove elements not part of rms channel sum
                        dr_channel_block_rms[channel].erase(
                            dr_channel_block_rms[channel].begin(),
                            dr_channel_block_rms[channel].begin() +
                            (dr_channel_block_rms[channel].size() - dr_20)
                        );

                        std::for_each(
                            dr_channel_block_rms[channel].begin(),
                            dr_channel_block_rms[channel].end(),
                            [](float& element) {
                                element = element * element;
                            }
                        );

                        float avg = 0.0f;//average of all elements
                        for (float f : dr_channel_block_rms[channel])
                        {
                            avg += f;
                        }

                        avg = avg / dr_channel_block_rms[0].size();

                        float dr_ch = -20 * std::log10
                        (
                            std::sqrt(avg) /
                            dr_channel_block_peaks[channel][dr_channel_block_peaks[channel].size() - 2]
                        );

                        dr_measurements.push_back(dr_ch);
                    }

                    float dr_avg = 0.0f;

                    //channel information, i.e. L R
                    dr_measurements_channels_text = getBusesLayout().getMainInputChannelSet().getDescription();
                    for (int i = 0; i < dr_measurements.size(); ++i)
                    {
                        dr_avg += dr_measurements[i];
                        dr_measurements_channels_text += juce::String("\nChannel #") +
                            juce::String(i + 1) + juce::String("  ") +
                            juce::String::formatted("%.2f", dr_measurements[i]);
                    }
                    if (dr_measurements.size() > 1)
                    {
                        dr_measurements_avg = dr_avg / dr_measurements.size();
                        dr_measurements_avg_text = juce::String::formatted("DR %.1f", dr_measurements_avg);
                    }
                    else
                    {
                        dr_measurements_avg = 0.0f;
                        dr_measurements_avg_text = "DR 00.0";
                        dr_measurements_channels_text = "No measurements";
                    }

                    //free memory
                    dr_channel_block_peaks.clear();
                    dr_channel_block_rms.clear();
                    dr_channel_block_tail_rms.clear();
                    dr_blocks = 0;

                    //calculate differences between specific frequency
                    //crest factor and overall crest factor
                    table_crest_factor_params[0][0] = juce::String("20 ");//label column values
                    table_crest_factor_params[1][0] = juce::String("60 ");
                    table_crest_factor_params[2][0] = juce::String("200 ");
                    table_crest_factor_params[3][0] = juce::String("600 ");
                    table_crest_factor_params[4][0] = juce::String("2000 ");
                    table_crest_factor_params[5][0] = juce::String("6000 ");
                    table_crest_factor_params[6][0] = juce::String("20000 ");
                    for (int i = 0; i < nc; ++i)
                    {
                        for (int j = 0; j < len_ap_freq; ++j)
                        {
                            table_crest_factor_params[j][i + 1] = juce::String::formatted(
                                "%+.2f", ap_crest[i][j] - total_peak_rms_cf[i][2]
                            );
                        }
                    }
                }
                else
                {
                    //not enough samples for analysis
                    clear();
                    processing_error = juce::String("Too few blocks.\nMinimum 3 seconds of audio.(2)");
                }
            }
        }
        catch (std::exception e)
        {
            clear();
            processing_error = juce::String(e.what());
        }

        //notify GUI to repaint
        sendChangeMessage();
    }
}

void MasVisGtkPluginAudioProcessor::clear()
{
    total_samples = 0;

    dr_channel_block_peaks.clear();
    dr_channel_block_rms.clear();
    dr_channel_block_tail_rms.clear();
    dr_measurements.clear();
    dr_measurements_avg = 0.0f;
    dr_measurements_avg_text = juce::String("DR 00.0");
    dr_measurements_channels_text = juce::String("No measurements");

    histogram_channel_minimums.clear();
    histogram_channel_maximums.clear();
    histogram_bins.clear();
    histogram_paths.clear();

    current_samples.clear();
    last_sample_caches.clear();
    previous_y_sample_caches.clear();

    total_peak_rms_cf.clear();

    allpass_crest_factor_paths.clear();
    histogram_paths.clear();
    cf_lines.clear();

    ap_ba.clear();
    ap_peak.clear();
    ap_rms.clear();
    ap_crest.clear();

    table_crest_factor_params.clear();
}

void MasVisGtkPluginAudioProcessor::prepare_params()
{
    // Init counting variable
    for (int i = 0; i < nc; ++i)
    {
        dr_channel_block_peaks.push_back(std::vector<float>{});
        dr_channel_block_rms.push_back(std::vector<float>{});
        dr_channel_block_tail_rms.push_back(0);

        histogram_channel_minimums.push_back(0.0f);
        histogram_channel_maximums.push_back(0.0f);
        histogram_bins.push_back(std::unordered_map<int, float>());
        histogram_paths.push_back(juce::Path());

        ap_peak.push_back(std::vector<float>{ 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f });
        ap_rms.push_back(std::vector<float>{ 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f });
        ap_crest.push_back(std::vector<float>{ 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f });

        current_samples.push_back(std::vector<int>{ 0, 0, 0, 0, 0, 0, 0 });
        last_sample_caches.push_back(std::vector<float>{ 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f });
        previous_y_sample_caches.push_back(std::vector<float>{ 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f });

        total_peak_rms_cf.push_back(std::vector<float>{ 0.0f, 0.0f, 0.0f });

        allpass_crest_factor_paths.push_back(juce::Path());

        table_crest_factor_params = std::vector<std::vector<juce::String>>(len_ap_freq, std::vector<juce::String>(nc + 1));
    }

    //produce parameters from crest factor analysis
    for (int i = 0; i < len_ap_freq; ++i)
    {
        float fc = (float) ap_freqs[i];
        if (fc > (fs / 2.0001))
            fc = fs / (float) 2.0001;
        float rho_b = tan(pi * fc / fs);
        float p_d = (1 - rho_b) / (1 + rho_b);
        ap_ba.push_back(std::vector<float>{ p_d, -1.0, 1.0, -p_d });
    }
}

float MasVisGtkPluginAudioProcessor::db(float a, float b)
{
    float c = a / b;
    if (b == 0)//division by 0
        return -128.0;
    else
        return c = 20 * log10(c);
}

float MasVisGtkPluginAudioProcessor::rms(float mean, int total_samples_)
{
    return std::sqrt(mean / total_samples_);
}

bool MasVisGtkPluginAudioProcessor::hasEditor() const
{
    return true; // (change this to false if you choose to not supply an editor)
}

juce::AudioProcessorEditor* MasVisGtkPluginAudioProcessor::createEditor()
{
    return new MasVisGtkPluginAudioProcessorEditor(*this);
}

void MasVisGtkPluginAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    // You should use this method to store your parameters in the memory block.
    // You could do that either as raw data, or use the XML or ValueTree classes
    // as intermediaries to make it easy to save and load complex data.
}

void MasVisGtkPluginAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    // You should use this method to restore your parameters from this memory block,
    // whose contents will have been created by the getStateInformation() call.
}

// This creates new instances of the plugin..
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new MasVisGtkPluginAudioProcessor();
}
