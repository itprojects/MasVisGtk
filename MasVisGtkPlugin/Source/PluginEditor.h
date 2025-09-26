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
#include "PluginProcessor.h"
#include "DynamicRangeByChannel.h"
#include "DynamicRangeChart.h"
#include "TableComponent.h"

class MasVisGtkPluginAudioProcessorEditor : public juce::AudioProcessorEditor, public juce::ChangeListener
{
public:
    MasVisGtkPluginAudioProcessorEditor(MasVisGtkPluginAudioProcessor&);
    ~MasVisGtkPluginAudioProcessorEditor() override;
    void paint(juce::Graphics&) override;
    void resized() override;
    void changeListenerCallback(juce::ChangeBroadcaster* source) override;

private:
    MasVisGtkPluginAudioProcessor& audioProcessor;

    std::vector<juce::Colour> audio_colours = {
        juce::Colours::deepskyblue, juce::Colours::orangered, juce::Colours::blueviolet,
        juce::Colours::aqua, juce::Colours::beige , juce::Colours::crimson,
        juce::Colours::darkolivegreen, juce::Colours::olive, juce::Colours::hotpink,
        juce::Colours::firebrick, juce::Colours::fuchsia, juce::Colours::gainsboro,
        juce::Colours::gold, juce::Colours::honeydew, juce::Colours::lavenderblush,
        juce::Colours::lime,  juce::Colours::magenta, juce::Colours::violet,
        juce::Colours::orange,  juce::Colours::silver, juce::Colours::darkseagreen,
        juce::Colours::whitesmoke
    };

    juce::Colour main_text_colour = juce::Colours::bisque;

    juce::Colour shade_colour_look_and_feel1 = getLookAndFeel()
        .findColour(juce::ResizableWindow::backgroundColourId);

    juce::Colour shade_colour_look_and_feel2 = shade_colour_look_and_feel1.darker(0.08f);

    //dynamic range meter colour styles
    juce::Colour dr_style07 = juce::Colour::fromRGB(255, 0, 0);//#ff0000
    juce::Colour dr_style08 = juce::Colour::fromRGB(255, 72, 0);//#ff4800
    juce::Colour dr_style09 = juce::Colour::fromRGB(255, 145, 0);//#ff9100
    juce::Colour dr_style10 = juce::Colour::fromRGB(255, 217, 0);//#ffd900
    juce::Colour dr_style11 = juce::Colour::fromRGB(217, 255, 0);//#d9ff00
    juce::Colour dr_style12 = juce::Colour::fromRGB(144, 255, 0);//#90ff00
    juce::Colour dr_style13 = juce::Colour::fromRGB(72, 255, 0);//#48ff00
    juce::Colour dr_style14 = juce::Colour::fromRGB(0, 255, 0);//#00ff00

    //table for allpass crest factor data
    //differences beteen line and dashed
    TableComponent table_crest_factor;

    //allpass crest factor scale markings
    juce::Path allpass_crest_factor_hmark_1;//horizontal mark 1   60 Hz
    juce::Path allpass_crest_factor_hmark_2;//horizontal mark 2  200 Hz
    juce::Path allpass_crest_factor_hmark_3;//horizontal mark 3  600 Hz
    juce::Path allpass_crest_factor_hmark_4;//horizontal mark 4 2000 Hz
    juce::Path allpass_crest_factor_hmark_5;//horizontal mark 5 6000 Hz

    juce::Path allpass_crest_factor_vmark_1;//vertical mark 1 25 dB
    juce::Path allpass_crest_factor_vmark_2;//vertical mark 2 20 dB
    juce::Path allpass_crest_factor_vmark_3;//vertical mark 3 15 dB
    juce::Path allpass_crest_factor_vmark_4;//vertical mark 4 10 dB
    juce::Path allpass_crest_factor_vmark_5;//vertical mark 5  5 dB

    const float dash_lengths[2] = { 10, 5 };//painting histogram

    //UI buttons
    const char* svg_string_normal_reset = R"(
        <svg height="16px" viewBox="0 0 16 16" width="16px" xmlns="http://www.w3.org/2000/svg">
            <path fill="#4F646B" d="m 1 3 h 14 c 0.550781 0 1 0.449219 1 1 s -0.449219 1 -1 1 h -14 c -0.550781 0 -1 -0.449219 -1 -1 s 0.449219 -1 1 -1 z m 0 0"/>
            <path fill="#4F646B" d="m 4 4 v -1.5 c 0 -1.386719 1.113281 -2.5 2.5 -2.5 h 2.980469 c 1.382812 0 2.5 1.113281 2.5 2.5 v 1.5 h -2 v -1.5 c 0 -0.269531 -0.230469 -0.5 -0.5 -0.5 h -2.980469 c -0.269531 0 -0.5 0.230469 -0.5 0.5 v 1.5 z m 0 0"/>
            <path fill="#4F646B" d="m 4 4 v 9 c 0 0.546875 0.453125 1 1 1 h 6 c 0.546875 0 1 -0.453125 1 -1 v -9 h 2 v 9 c 0 1.660156 -1.339844 3 -3 3 h -6 c -1.660156 0 -3 -1.339844 -3 -3 v -9 z m 0 0"/>
            <path fill="#4F646B" d="m 7 7 v 5 c 0 0.277344 -0.222656 0.5 -0.5 0.5 s -0.5 -0.222656 -0.5 -0.5 v -5 c 0 -0.277344 0.222656 -0.5 0.5 -0.5 s 0.5 0.222656 0.5 0.5 z m 0 0"/>
            <path fill="#4F646B" d="m 10 7 v 5 c 0 0.277344 -0.222656 0.5 -0.5 0.5 s -0.5 -0.222656 -0.5 -0.5 v -5 c 0 -0.277344 0.222656 -0.5 0.5 -0.5 s 0.5 0.222656 0.5 0.5 z m 0 0"/>
        </svg>
    )";
    std::unique_ptr<juce::Drawable> drawable_normal_reset;

    const char* svg_string_highlight_reset = R"(
        <svg height="16px" viewBox="0 0 16 16" width="16px" xmlns="http://www.w3.org/2000/svg">
            <path fill="#9bc0d3" d="m 1 3 h 14 c 0.550781 0 1 0.449219 1 1 s -0.449219 1 -1 1 h -14 c -0.550781 0 -1 -0.449219 -1 -1 s 0.449219 -1 1 -1 z m 0 0"/>
            <path fill="#9bc0d3" d="m 4 4 v -1.5 c 0 -1.386719 1.113281 -2.5 2.5 -2.5 h 2.980469 c 1.382812 0 2.5 1.113281 2.5 2.5 v 1.5 h -2 v -1.5 c 0 -0.269531 -0.230469 -0.5 -0.5 -0.5 h -2.980469 c -0.269531 0 -0.5 0.230469 -0.5 0.5 v 1.5 z m 0 0"/>
            <path fill="#9bc0d3" d="m 4 4 v 9 c 0 0.546875 0.453125 1 1 1 h 6 c 0.546875 0 1 -0.453125 1 -1 v -9 h 2 v 9 c 0 1.660156 -1.339844 3 -3 3 h -6 c -1.660156 0 -3 -1.339844 -3 -3 v -9 z m 0 0"/>
            <path fill="#9bc0d3" d="m 7 7 v 5 c 0 0.277344 -0.222656 0.5 -0.5 0.5 s -0.5 -0.222656 -0.5 -0.5 v -5 c 0 -0.277344 0.222656 -0.5 0.5 -0.5 s 0.5 0.222656 0.5 0.5 z m 0 0"/>
            <path fill="#9bc0d3" d="m 10 7 v 5 c 0 0.277344 -0.222656 0.5 -0.5 0.5 s -0.5 -0.222656 -0.5 -0.5 v -5 c 0 -0.277344 0.222656 -0.5 0.5 -0.5 s 0.5 0.222656 0.5 0.5 z m 0 0"/>
        </svg>
    )";
    std::unique_ptr<juce::Drawable> drawable_highlight_reset;

    //clear all buffers, plots, and data
    juce::DrawableButton button_reset{ "Reset", juce::DrawableButton::ImageFitted };

    const char* svg_string_normal_info = R"(
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <ellipse style="fill: rgb(50, 62, 68); stroke: rgb(255, 255, 255); stroke-opacity: 0;" cx="100" cy="100" rx="100.0" ry="100.0"/>
            <path  style="fill: rgb(255, 255, 255); text-wrap-mode: nowrap;" d="M 94 107.2 Q 94 103.4 94.75 100.65 Q 95.5 97.9 97.35 95.4 Q 99.2 92.9 102.4 90.2 Q 106.3 86.9 108.45 84.7 Q 110.6 82.5 111.5 80.4 Q 112.4 78.3 112.4 75.3 Q 112.4 70.5 109.3 67.9 Q 106.2 65.3 100.3 65.3 Q 95.4 65.3 91.6 66.55 Q 87.8 67.8 84.3 69.5 L 81.2 62.5 Q 85.2 60.4 90.05 59 Q 94.9 57.6 100.9 57.6 Q 110.4 57.6 115.6 62.3 Q 120.8 67 120.8 75.1 Q 120.8 79.6 119.35 82.75 Q 117.9 85.9 115.25 88.55 Q 112.6 91.2 109 94.2 Q 105.7 97 103.95 99.1 Q 102.2 101.2 101.6 103.25 Q 101 105.3 101 108.2 L 101 109.9 L 94 109.9 Z M 91.7 124.6 Q 91.7 120.9 93.45 119.4 Q 95.2 117.9 97.9 117.9 Q 100.4 117.9 102.2 119.4 Q 104 120.9 104 124.6 Q 104 128.2 102.2 129.8 Q 100.4 131.4 97.9 131.4 Q 95.2 131.4 93.45 129.8 Q 91.7 128.2 91.7 124.6 Z"/>
        </svg>
    )";
    std::unique_ptr<juce::Drawable> drawable_normal_info;

    const char* svg_string_highlight_info = R"(
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <ellipse style="fill: rgb(50, 62, 68); stroke: rgb(255, 255, 255); stroke-opacity: 0;" cx="100" cy="100" rx="100.0" ry="100.0"/>
            <path  style="fill: rgb(255, 0, 0); text-wrap-mode: nowrap;" d="M 94 107.2 Q 94 103.4 94.75 100.65 Q 95.5 97.9 97.35 95.4 Q 99.2 92.9 102.4 90.2 Q 106.3 86.9 108.45 84.7 Q 110.6 82.5 111.5 80.4 Q 112.4 78.3 112.4 75.3 Q 112.4 70.5 109.3 67.9 Q 106.2 65.3 100.3 65.3 Q 95.4 65.3 91.6 66.55 Q 87.8 67.8 84.3 69.5 L 81.2 62.5 Q 85.2 60.4 90.05 59 Q 94.9 57.6 100.9 57.6 Q 110.4 57.6 115.6 62.3 Q 120.8 67 120.8 75.1 Q 120.8 79.6 119.35 82.75 Q 117.9 85.9 115.25 88.55 Q 112.6 91.2 109 94.2 Q 105.7 97 103.95 99.1 Q 102.2 101.2 101.6 103.25 Q 101 105.3 101 108.2 L 101 109.9 L 94 109.9 Z M 91.7 124.6 Q 91.7 120.9 93.45 119.4 Q 95.2 117.9 97.9 117.9 Q 100.4 117.9 102.2 119.4 Q 104 120.9 104 124.6 Q 104 128.2 102.2 129.8 Q 100.4 131.4 97.9 131.4 Q 95.2 131.4 93.45 129.8 Q 91.7 128.2 91.7 124.6 Z"/>
        </svg>
    )";
    std::unique_ptr<juce::Drawable> drawable_highlight_info;

    const char* svg_string_dynamic_range_chart = R"(
        <svg width="320" height="550" xmlns="http://www.w3.org/2000/svg">

          <!-- Table Headers -->
          <text x="85" y="60" font-size="14" fill="white" text-anchor="start" font-weight="bold">Synth</text>
          <text x="85" y="77" font-size="14" fill="white" text-anchor="start">Goa</text>
          <text x="85" y="90" font-size="14" fill="white" text-anchor="start">Disco</text>
          <text x="85" y="105" font-size="14" fill="white" text-anchor="start">Trance</text>
          <text x="85" y="120" font-size="14" fill="white" text-anchor="start">Electro</text>
          <text x="85" y="135" font-size="14" fill="white" text-anchor="start">House</text>
          <text x="85" y="150" font-size="14" fill="white" text-anchor="start">Techno</text>

          <text x="160" y="60" font-size="14" fill="white" text-anchor="start" font-weight="bold">Radio</text>
          <text x="160" y="75" font-size="14" fill="white" text-anchor="start">Pop</text>
          <text x="160" y="90" font-size="14" fill="white" text-anchor="start">Rock</text>
          <text x="160" y="105" font-size="14" fill="white" text-anchor="start">RnB</text>
          <text x="160" y="120" font-size="14" fill="white" text-anchor="start">Blues</text>
          <text x="160" y="135" font-size="14" fill="white" text-anchor="start">Hip-Hop</text>
          <text x="160" y="150" font-size="14" fill="white" text-anchor="start">Hard Rock</text>

          <text x="240" y="60" font-size="14" fill="white" text-anchor="start" font-weight="bold">Acoustic</text>
          <text x="240" y="75" font-size="14" fill="white" text-anchor="start">Jazz</text>
          <text x="240" y="90" font-size="14" fill="white" text-anchor="start">Folk</text>
          <text x="240" y="105" font-size="14" fill="white" text-anchor="start">Country</text>
          <text x="240" y="120" font-size="14" fill="white" text-anchor="start">Classic</text>
          <text x="240" y="135" font-size="14" fill="white" text-anchor="start">Chill-out</text>
          <text x="240" y="150" font-size="14" fill="white" text-anchor="start">Relax</text>

          <!-- Table Rows -->
          <rect x="20" y="160" width="275" height="30" fill="transparent" />
          <text x="75" y="180" font-family="Arial" font-size="14" fill="white" text-anchor="end">DR 04</text>

          <rect x="85" y="160" width="70" height="30" fill="red" stroke="black" stroke-width="1" />
          <rect x="155" y="160" width="70" height="30" fill="red" stroke="black" stroke-width="1" />
          <rect x="225" y="160" width="70" height="30" fill="red" stroke="black" stroke-width="1" />

          <rect x="20" y="190" width="275" height="30" fill="transparent" />
          <text x="75" y="210" font-family="Arial" font-size="14" fill="white" text-anchor="end">DR 05</text>

          <rect x="85" y="190" width="70" height="30" fill="red" stroke="black" stroke-width="1" />
          <rect x="155" y="190" width="70" height="30" fill="red" stroke="black" stroke-width="1" />
          <rect x="225" y="190" width="70" height="30" fill="red" stroke="black" stroke-width="1" />

          <rect x="20" y="220" width="275" height="30" fill="transparent" />
          <text x="75" y="240" font-family="Arial" font-size="14" fill="white" text-anchor="end">DR 06</text>

          <rect x="85" y="220" width="70" height="30" fill="yellow" stroke="black" stroke-width="1" />
          <rect x="155" y="220" width="70" height="30" fill="red" stroke="black" stroke-width="1" />
          <rect x="225" y="220" width="70" height="30" fill="red" stroke="black" stroke-width="1" />

          <rect x="20" y="250" width="275" height="30" fill="transparent" />
          <text x="75" y="270" font-family="Arial" font-size="14" fill="white" text-anchor="end">DR 07</text>

          <rect x="85" y="250" width="70" height="30" fill="yellow" stroke="black" stroke-width="1" />
          <rect x="155" y="250" width="70" height="30" fill="red" stroke="black" stroke-width="1" />
          <rect x="225" y="250" width="70" height="30" fill="red" stroke="black" stroke-width="1" />

          <rect x="20" y="280" width="275" height="30" fill="transparent" />
          <text x="75" y="300" font-family="Arial" font-size="14" fill="white" text-anchor="end">DR 08</text>

          <rect x="85" y="280" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="155" y="280" width="70" height="30" fill="yellow" stroke="black" stroke-width="1" />
          <rect x="225" y="280" width="70" height="30" fill="red" stroke="black" stroke-width="1" />

          <rect x="20" y="310" width="275" height="30" fill="transparent" />
          <text x="75" y="330" font-family="Arial" font-size="14" fill="white" text-anchor="end">DR 09</text>

          <rect x="85" y="310" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="155" y="310" width="70" height="30" fill="yellow" stroke="black" stroke-width="1" />
          <rect x="225" y="310" width="70" height="30" fill="red" stroke="black" stroke-width="1" />

          <rect x="20" y="340" width="275" height="30" fill="transparent" />
          <text x="75" y="360" font-family="Arial" font-size="14" fill="white" text-anchor="end">DR 10</text>

          <rect x="85" y="340" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="155" y="340" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="225" y="340" width="70" height="30" fill="yellow" stroke="black" stroke-width="1" />

          <rect x="20" y="370" width="275" height="30" fill="transparent" />
          <text x="75" y="390" font-family="Arial" font-size="14" fill="white" text-anchor="end">DR 11</text>

          <rect x="85" y="370" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="155" y="370" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="225" y="370" width="70" height="30" fill="yellow" stroke="black" stroke-width="1" />

          <rect x="20" y="400" width="275" height="30" fill="transparent" />
          <text x="75" y="420" font-family="Arial" font-size="14" fill="white" text-anchor="end">DR 12</text>

          <rect x="85" y="400" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="155" y="400" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="225" y="400" width="70" height="30" fill="green" stroke="black" stroke-width="1" />

          <rect x="20" y="430" width="275" height="30" fill="transparent" />
          <text x="75" y="450" font-family="Arial" font-size="14" fill="white" text-anchor="end">DR 13</text>

          <rect x="85" y="430" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="155" y="430" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="225" y="430" width="70" height="30" fill="green" stroke="black" stroke-width="1" />

          <rect x="20" y="460" width="275" height="30" fill="transparent" />
          <text x="75" y="480" font-family="Arial" font-size="14" fill="white" text-anchor="end">&#8805; DR 14</text>

          <rect x="85" y="460" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="155" y="460" width="70" height="30" fill="green" stroke="black" stroke-width="1" />
          <rect x="225" y="460" width="70" height="30" fill="green" stroke="black" stroke-width="1" />

          <text x="85" y="510" font-family="Arial" font-size="10" fill="white" text-anchor="start">OVERCOMPRESSED, UNPLEASANT (RED)</text>
          <text x="85" y="520" font-family="Arial" font-size="10" fill="white" text-anchor="start">TRANSITIONAL (YELLOW)</text>
          <text x="85" y="530" font-family="Arial" font-size="10" fill="white" text-anchor="start">DYNAMIC, PLEASANT (GREEN)</text>
        </svg>
    )";
    std::unique_ptr<juce::Drawable> drawable_chart;

    //shows dynamic range chart
    juce::DrawableButton button_info{ "Info", juce::DrawableButton::ImageFitted };

    const char* svg_string_normal_enable_disable_operations = R"(
        <svg height="16px" viewBox="0 0 16 16" width="16px" xmlns="http://www.w3.org/2000/svg">
            <path style="fill: rgb(50, 62, 68); stroke: rgb(0, 0, 0); stroke-opacity: 0;" d="M 9.918 0.309 C 9.464 0.2 6.536 0.2 6.082 0.309 C 2.501 1.177 0 4.31 0 7.928 C 0 12.253 3.59 15.773 8 15.773 C 12.411 15.773 16 12.253 16 7.928 C 16 4.31 13.5 1.177 9.918 0.309 Z M 8 13.601 C 4.81 13.601 2.215 11.054 2.215 7.928 C 2.215 5.429 3.832 3.213 6.265 2.475 C 6.319 2.458 7.41 2.113 7.762 2.218 C 7.888 2.256 8.073 2.67 7.817 2.83 C 7.574 2.982 6.892 2.876 6.892 3.024 L 6.864 12.9 C 6.864 13.498 9.081 13.498 9.081 12.9 L 9.108 3.024 C 9.108 2.942 8.51 2.986 8.248 2.825 C 7.951 2.641 8.222 2.27 8.306 2.226 C 8.714 2.01 9.532 2.32 9.701 2.37 C 12.134 3.108 13.785 5.429 13.785 7.928 C 13.785 11.054 11.19 13.601 8 13.601 Z"/>
        </svg>
    )";
    std::unique_ptr<juce::Drawable> drawable_normal_enable_disable_operations;

    const char* svg_string_highlight_enable_disable_operations = R"(
        <svg height="16px" viewBox="0 0 16 16" width="16px" xmlns="http://www.w3.org/2000/svg">
            <path style="fill: rgb(47, 135, 255); stroke: rgb(0, 0, 0); stroke-opacity: 0; background-color:red" d="M 9.918 0.309 C 9.464 0.2 6.536 0.2 6.082 0.309 C 2.501 1.177 0 4.31 0 7.928 C 0 12.253 3.59 15.773 8 15.773 C 12.411 15.773 16 12.253 16 7.928 C 16 4.31 13.5 1.177 9.918 0.309 Z M 8 13.601 C 4.81 13.601 2.215 11.054 2.215 7.928 C 2.215 5.429 3.832 3.213 6.265 2.475 C 6.319 2.458 7.41 2.113 7.762 2.218 C 7.888 2.256 8.073 2.67 7.817 2.83 C 7.574 2.982 6.892 2.876 6.892 3.024 L 6.864 12.9 C 6.864 13.498 9.081 13.498 9.081 12.9 L 9.108 3.024 C 9.108 2.942 8.51 2.986 8.248 2.825 C 7.951 2.641 8.222 2.27 8.306 2.226 C 8.714 2.01 9.532 2.32 9.701 2.37 C 12.134 3.108 13.785 5.429 13.785 7.928 C 13.785 11.054 11.19 13.601 8 13.601 Z"/>
        </svg>
    )";
    std::unique_ptr<juce::Drawable> drawable_highlight_enable_disable_operations;

    juce::DrawableButton button_enable_disable_operations{ "Enable or disable", juce::DrawableButton::ImageFitted };

    juce::TextButton button_dr_meter;

    juce::TooltipWindow tooltip_window{ this };//to show tooltips

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (MasVisGtkPluginAudioProcessorEditor)
};
