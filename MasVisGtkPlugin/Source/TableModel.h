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

class TableModel : public juce::TableListBoxModel
{
public:
    TableModel()
    {
    }

    int getNumRows() override
    {
        if (table_init_done)
           return (int) data->size();
        else
            return 0;
    }

    void paintRowBackground(juce::Graphics& g, int rowNumber, int /*width*/, int /*height*/, bool rowIsSelected) override
    {
        if (rowIsSelected)
            g.fillAll(shade_colour2);
        else if (rowNumber % 2 == 0)
            g.fillAll(shade_colour1);
        else
            g.fillAll(shade_colour_look_and_feel1);
    }

    void paintCell(juce::Graphics& g, int rowNumber, int columnId, int width, int height, bool /*rowIsSelected*/) override
    {
        if (columnId == 1)
        {
            //label column font colours
            g.setColour(juce::Colours::bisque);
            g.drawText(
                juce::String("Diff ") + juce::String(rowNumber + 1),
                2, 0, width - 4, height,
                juce::Justification::centred
            );
        }
        else
        {
            bool to_be_bold = (columnId - 2 == ap_peak_index->at(rowNumber));
            if (to_be_bold)
            {
                g.setColour(juce::Colours::bisque);
                g.setFont(bold_font);
            }
            else
            {
                //font colour as per channel colour
                g.setColour((*audio_colours)[rowNumber]);
            }

            g.drawText(
                data->at(rowNumber)[columnId - 1],
                2, 0, width - 4, height,
                juce::Justification::centred
            );

            if (to_be_bold)
            {
                g.setFont(plain_font);
            }
        }
    }

    bool table_init_done = false;

    juce::Colour shade_colour_look_and_feel1;
    juce::Colour shade_colour1;
    juce::Colour shade_colour2;

    juce::Font bold_font = juce::Font(juce::FontOptions(14.0f, juce::Font::bold));
    juce::Font plain_font = juce::Font(juce::FontOptions(14.0f, juce::Font::plain));

    std::vector<juce::Colour>* audio_colours;
    std::vector<std::vector<juce::String>>* data;
    std::vector<int>* ap_peak_index;
};