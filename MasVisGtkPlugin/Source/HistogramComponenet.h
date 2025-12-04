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

class HistogramComponenet : public juce::Component
{
public:
    HistogramComponenet
    (
        std::vector<juce::Colour>& audio_colours_,
        juce::Colour main_text_colour_,
        juce::Colour shade_colour_look_and_feel1_,
        std::vector<juce::Path>& histogram_paths_
    )
    {
        setBufferedToImage(true);//optimal painting
        audio_colours = &audio_colours_;
        main_text_colour = main_text_colour_;
        shade_colour_look_and_feel1 = shade_colour_look_and_feel1_;
        histogram_paths = &histogram_paths_;
        setSize(600, 300);
    }

    void paint(juce::Graphics& g) override
    {
        g.fillAll(juce::Colours::black);

        //histogram background
        g.setColour(shade_colour_look_and_feel1);
        g.fillRect(0, 0, 600, 300);

        //histogram labels
        g.setColour(main_text_colour);
        g.setFont(juce::FontOptions(12.0f));
        g.drawText("-100", 0, 295, 30, 20, juce::Justification::bottomLeft, false);
        g.drawText("-50", 150, 295, 30, 20, juce::Justification::centredBottom, false);
        g.drawText("0", 301, 295, 30, 20, juce::Justification::centredBottom, false);
        g.drawText("+50", 450, 295, 30, 20, juce::Justification::centredBottom, false);
        g.drawText("+100", 570, 295, 30, 20, juce::Justification::bottomRight, false);

        //plot audio channels' histograms (as lines)
        int colour_index = 0;
        if (histogram_paths->size() > 0)
        {
            for (juce::Path histogram_path : *histogram_paths)
            {
                g.setColour((*audio_colours)[colour_index]);
                g.strokePath(histogram_path, juce::PathStrokeType(1.0f));
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

    std::vector<juce::Path>* histogram_paths;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(HistogramComponenet)
};