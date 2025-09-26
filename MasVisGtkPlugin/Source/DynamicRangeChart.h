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

class DynamicRangeChart : public juce::DialogWindow
{
public:
    DynamicRangeChart(std::string name, juce::Colour colour, bool escapeCloses, std::unique_ptr<juce::Drawable>& drawable_chart)
        : DialogWindow(name, colour, escapeCloses)
    {
        setSize(320, 550);
        addAndMakeVisible(drawable_chart.get());
        drawable_chart->setTransformToFit(getLocalBounds().toFloat(), juce::RectanglePlacement::onlyReduceInSize);
        centreWithSize(getWidth(), getHeight());
    }

    void closeButtonPressed() override
    {
        delete this;
    }
};