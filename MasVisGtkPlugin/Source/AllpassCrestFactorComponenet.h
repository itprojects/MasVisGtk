/*
Copyright 2025 ITProjects

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

class AllpassCrestFactorComponenet : public juce::Component
{
public:
    AllpassCrestFactorComponenet
    (
        std::vector<juce::Colour>& audio_colours_,
        juce::Colour main_text_colour_,
        juce::Colour shade_colour_look_and_feel1_,
        juce::Colour shade_colour_look_and_feel2_,
        std::vector<juce::Path>& allpass_crest_factor_paths_,
        std::vector<juce::Line<float>> & cf_lines_
    )
    {
        setBufferedToImage(true);//optimal painting

        audio_colours = &audio_colours_;
        main_text_colour = main_text_colour_;
        shade_colour_look_and_feel1 = shade_colour_look_and_feel1_;
        shade_colour_look_and_feel2 = shade_colour_look_and_feel2_;
        allpass_crest_factor_paths = &allpass_crest_factor_paths_;
        cf_lines = &cf_lines_;

        setSize(356, 315);
    }

    void paint(juce::Graphics& g) override
    {
        g.fillAll(juce::Colours::black);

        //conversions to log10 scale
        //same procedure as apFreqPxLog10Locations...
        //log10(1)      0             |  35.000
        //log10(10)     1             | 104.751
        //log10(100)    2             | 174.501
        //log10(1000)   3             | 244.252
        //log10(10000)  4             | 314.003
        //log10(20000)  4.301029996   | 335.000

        //allpass crest factor region backgrounds
        g.setColour(shade_colour_look_and_feel1);
        g.fillRect(35, 0, 70, 300);
        g.setColour(shade_colour_look_and_feel2);
        g.fillRect(104, 0, 70, 300);
        g.setColour(shade_colour_look_and_feel1);
        g.fillRect(174, 0, 70, 300);
        g.setColour(shade_colour_look_and_feel2);
        g.fillRect(244, 0, 70, 300);
        g.setColour(shade_colour_look_and_feel1);
        g.fillRect(314, 0, 20, 300);

        //allpass crest factor log10 horizonal markings
        allpass_crest_factor_hmark_1.startNewSubPath(36.000f, 300);
        allpass_crest_factor_hmark_1.lineTo(36.000f, 297);
        allpass_crest_factor_hmark_2.startNewSubPath(104.000f, 300);
        allpass_crest_factor_hmark_2.lineTo(104.000f, 297);
        allpass_crest_factor_hmark_3.startNewSubPath(174.000f, 300);
        allpass_crest_factor_hmark_3.lineTo(174.000f, 297);
        allpass_crest_factor_hmark_4.startNewSubPath(244.000f, 300);
        allpass_crest_factor_hmark_4.lineTo(244.000f, 297);
        allpass_crest_factor_hmark_5.startNewSubPath(314.000f, 300);
        allpass_crest_factor_hmark_5.lineTo(314.000f, 297);
        allpass_crest_factor_hmark_6.startNewSubPath(333.000f, 300);
        allpass_crest_factor_hmark_6.lineTo(333.000f, 297);

        //allpass crest factor linear vertical markings
        float y_unit = 30;//height of division ex. 0 to 5 dB, 150/5
        allpass_crest_factor_vmark_1.startNewSubPath(35, 150 - 4 * y_unit);
        allpass_crest_factor_vmark_1.lineTo(38, 150 - 4 * y_unit);
        allpass_crest_factor_vmark_2.startNewSubPath(35, 150 - 3 * y_unit);
        allpass_crest_factor_vmark_2.lineTo(38, 150 - 3 * y_unit);
        allpass_crest_factor_vmark_3.startNewSubPath(35, 150 - 2 * y_unit);
        allpass_crest_factor_vmark_3.lineTo(38, 150 - 2 * y_unit);
        allpass_crest_factor_vmark_4.startNewSubPath(35, 150 - 1 * y_unit);
        allpass_crest_factor_vmark_4.lineTo(38, 150 - 1 * y_unit);
        allpass_crest_factor_vmark_5.startNewSubPath(35, 150);//0th
        allpass_crest_factor_vmark_5.lineTo(38, 150);
        allpass_crest_factor_vmark_6.startNewSubPath(35, 150 + 1 * y_unit);
        allpass_crest_factor_vmark_6.lineTo(38, 150 + 1 * y_unit);
        allpass_crest_factor_vmark_7.startNewSubPath(35, 150 + 2 * y_unit);
        allpass_crest_factor_vmark_7.lineTo(38, 150 + 2 * y_unit);
        allpass_crest_factor_vmark_8.startNewSubPath(35, 150 + 3 * y_unit);
        allpass_crest_factor_vmark_8.lineTo(38, 150 + 3 * y_unit);
        allpass_crest_factor_vmark_9.startNewSubPath(35, 150 + 4 * y_unit);
        allpass_crest_factor_vmark_9.lineTo(38, 150 + 4 * y_unit);

        //allpass crest factor log10 horizonal markings
        g.setColour(juce::Colours::grey);
        g.strokePath(allpass_crest_factor_hmark_1, juce::PathStrokeType(2.0f));
        g.strokePath(allpass_crest_factor_hmark_2, juce::PathStrokeType(2.0f));
        g.strokePath(allpass_crest_factor_hmark_3, juce::PathStrokeType(2.0f));
        g.strokePath(allpass_crest_factor_hmark_4, juce::PathStrokeType(2.0f));
        g.strokePath(allpass_crest_factor_hmark_5, juce::PathStrokeType(2.0f));
        g.strokePath(allpass_crest_factor_hmark_6, juce::PathStrokeType(2.0f));

        //allpass crest factor linear labels
        g.setColour(main_text_colour);
        g.setFont(juce::FontOptions(12.0f));
        g.drawText("1", 25, 295, 20, 20, juce::Justification::centredBottom, false);
        g.drawText("10", 94, 295, 20, 20, juce::Justification::centredBottom, false);
        g.drawText("100", 164, 295, 20, 20, juce::Justification::centredBottom, false);
        g.drawText("1k", 234, 295, 20, 20, juce::Justification::centredBottom, false);
        g.drawText("10k", 304, 295, 20, 20, juce::Justification::centredBottom, false);
        g.drawText("20k", 335, 295, 20, 20, juce::Justification::centredBottom, false);
        g.drawText("Hz", 335, 280, 20, 20, juce::Justification::centredBottom, false);

        g.setColour(juce::Colours::grey);
        g.strokePath(allpass_crest_factor_vmark_1, juce::PathStrokeType(1.0f));
        g.strokePath(allpass_crest_factor_vmark_2, juce::PathStrokeType(1.0f));
        g.strokePath(allpass_crest_factor_vmark_3, juce::PathStrokeType(1.0f));
        g.strokePath(allpass_crest_factor_vmark_4, juce::PathStrokeType(1.0f));
        g.strokePath(allpass_crest_factor_vmark_5, juce::PathStrokeType(1.0f));
        g.strokePath(allpass_crest_factor_vmark_6, juce::PathStrokeType(1.0f));
        g.strokePath(allpass_crest_factor_vmark_7, juce::PathStrokeType(1.0f));
        g.strokePath(allpass_crest_factor_vmark_8, juce::PathStrokeType(1.0f));
        g.strokePath(allpass_crest_factor_vmark_9, juce::PathStrokeType(1.0f));

        g.setColour(main_text_colour);
        g.drawText("dB", 10, 0, 20, 20, juce::Justification::topRight, false);
        g.drawText("20", 10, 20, 20, 20, juce::Justification::centredRight, false);
        g.drawText("15", 10, 50, 20, 20, juce::Justification::centredRight, false);
        g.drawText("10", 10, 80, 20, 20, juce::Justification::centredRight, false);
        g.drawText("5", 10, 110, 20, 20, juce::Justification::centredRight, false);
        g.drawText("0", 10, 140, 20, 20, juce::Justification::centredRight, false);
        g.drawText("-5", 10, 170, 20, 20, juce::Justification::centredRight, false);
        g.drawText("-10", 10, 200, 20, 20, juce::Justification::centredRight, false);
        g.drawText("-15", 10, 230, 20, 20, juce::Justification::centredRight, false);
        g.drawText("-20", 10, 260, 20, 20, juce::Justification::centredRight, false);

        //paint average crest factor level (dashed lines)
        //horizontally from 35 to 335 px; 300 px wide
        //vertical from 0 to 30 dB (10 px / dB on y-axis)
        int colour_index = 0;
        if (cf_lines->size() > 0)
        {
            colour_index = 0;
            for (juce::Line<float> cf_line : *cf_lines)
            {
                for (int i = 0; i < 3; ++i)
                {
                    g.setColour((*audio_colours)[colour_index]);
                    g.drawDashedLine(cf_line, dash_lengths, 2, 1, 0);
                }
                ++colour_index;
            }
        }

        //paint allpass crest factor (loudness) paths
        if (allpass_crest_factor_paths->size() > 0)
        {
            colour_index = 0;
            for (juce::Path ap_path : *allpass_crest_factor_paths)
            {
                g.setColour((*audio_colours)[colour_index]);
                g.strokePath(ap_path, juce::PathStrokeType(1.0f));
                ++colour_index;
            }
        }
    }

    void resized() override
    {
    }

private:
    std::vector<juce::Colour>* audio_colours;

    juce::Colour main_text_colour;
    juce::Colour shade_colour_look_and_feel1;
    juce::Colour shade_colour_look_and_feel2;

    std::vector<juce::Path>* allpass_crest_factor_paths;
    std::vector<juce::Line<float>>* cf_lines;

    const float dash_lengths[2] = { 10, 5 };//for dashed paths

    //allpass crest factor scale markings
    juce::Path allpass_crest_factor_hmark_1;//horizontal mark 1     1 Hz
    juce::Path allpass_crest_factor_hmark_2;//horizontal mark 2    10 Hz
    juce::Path allpass_crest_factor_hmark_3;//horizontal mark 3   100 Hz
    juce::Path allpass_crest_factor_hmark_4;//horizontal mark 4  1000 Hz
    juce::Path allpass_crest_factor_hmark_5;//horizontal mark 5 10000 Hz
    juce::Path allpass_crest_factor_hmark_6;//horizontal mark 6 20000 Hz

    juce::Path allpass_crest_factor_vmark_1;//vertical mark 1   20 dB
    juce::Path allpass_crest_factor_vmark_2;//vertical mark 2   15 dB
    juce::Path allpass_crest_factor_vmark_3;//vertical mark 3   10 dB
    juce::Path allpass_crest_factor_vmark_4;//vertical mark 4    5 dB
    juce::Path allpass_crest_factor_vmark_5;//vertical mark 5    0 dB
    juce::Path allpass_crest_factor_vmark_6;//vertical mark 6   -5 dB
    juce::Path allpass_crest_factor_vmark_7;//vertical mark 7  -10 dB
    juce::Path allpass_crest_factor_vmark_8;//vertical mark 8  -15 dB
    juce::Path allpass_crest_factor_vmark_9;//vertical mark 9  -20 dB

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(AllpassCrestFactorComponenet)
};