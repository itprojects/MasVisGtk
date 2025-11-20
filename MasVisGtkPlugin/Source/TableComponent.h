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
#include "TableModel.h"

class TableComponent : public juce::Component
{
public:
    TableComponent()
    {
        table.autoSizeAllColumns();
        table.getHeader().addColumn("Hz", 1, 50);
        ++n_columns;
        table.setModel(&model);
        addAndMakeVisible(table);
        setSize(600, 85);//change to make larger (with scrollbars)
    }

    //reset columns, if files have changed (mono, stereo, etc.)
    void reset_columns(size_t n_freqs, std::vector<float> ap_freqs)
    {
        if (n_columns != n_freqs)
        {
            table.getHeader().removeAllColumns();
            table.getHeader().addColumn("Hz", 1, 50);
            for (int i = 0;i < n_freqs; ++i) {
                table.getHeader().addColumn(juce::String(ap_freqs[i]), 2 + i, 50);
            }
        }
    }

    void resized() override
    {
        table.setBounds(getLocalBounds());
    }

    TableModel model;
    juce::TableListBox table;

private:
    int n_columns = 0;
};