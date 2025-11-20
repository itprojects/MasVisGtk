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

class TableWindow : public juce::DialogWindow
{
public:
    TableWindow(std::string name, juce::Colour colour, bool escapeCloses, juce::String allpass_cf_parameters)
        : DialogWindow(name, colour, escapeCloses)
    {
        setSize(640, 240);

        text_editor.setText(allpass_cf_parameters, juce::dontSendNotification);
        text_editor.setFont(juce::Font(juce::FontOptions(16.0f)));
        text_editor.setColour(juce::Label::textColourId, juce::Colours::bisque);

        setContentOwned(&text_editor, false);//content owned flag false because text_editor is member
        centreWithSize(getWidth(), getHeight());
        setResizable(true, true);
    }

    void closeButtonPressed() override
    {
        delete this;
    }

    juce::TextEditor text_editor;
};