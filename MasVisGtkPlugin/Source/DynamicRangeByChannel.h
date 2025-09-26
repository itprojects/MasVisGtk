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

class DynamicRangeByChannel : public juce::DialogWindow
{
public:
    DynamicRangeByChannel(std::string name, juce::Colour colour, bool escapeCloses, juce::String& dynamic_ranges)
        : DialogWindow(name, colour, escapeCloses)
    {
        setSize(320, 160);

        label.setText(dynamic_ranges, juce::dontSendNotification);
        label.setJustificationType(juce::Justification::centred);
        label.setFont(juce::Font(juce::FontOptions(16.0f)));
        label.setColour(juce::Label::textColourId, juce::Colours::bisque);

        setContentOwned(&label, false); // content owned flag false because label is member
        centreWithSize(getWidth(), getHeight());
        setResizable(true, true);
    }

    void closeButtonPressed() override
    {
        delete this;
    }

    juce::Label label;
};