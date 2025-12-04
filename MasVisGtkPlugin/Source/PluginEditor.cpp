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

#include "PluginProcessor.h"
#include "PluginEditor.h"

MasVisGtkPluginAudioProcessorEditor::MasVisGtkPluginAudioProcessorEditor(MasVisGtkPluginAudioProcessor& p)
    : AudioProcessorEditor(&p), audioProcessor(p)
{
    setBufferedToImage(true);//optimal painting

    //listens for signals to GUI to repaint()
    audioProcessor.addChangeListener(this);

    addAndMakeVisible(hist_component);
    addAndMakeVisible(ap_cf_component);

    button_invert_plot.setTooltip("Plot paths upside-down");
    button_invert_plot.setToggleState(audioProcessor.invert_cf_plot, juce::sendNotification);
    button_invert_plot.setColour(juce::ToggleButton::textColourId, main_text_colour);
    button_invert_plot.onClick = [this]() {
        audioProcessor.invert_cf_plot = button_invert_plot.getToggleState();
    };
    addAndMakeVisible(button_invert_plot);

    std::unique_ptr svg_xml_dynamic_range_chart = juce::XmlDocument::parse(svg_string_dynamic_range_chart);
    drawable_chart = juce::Drawable::createFromSVG(*svg_xml_dynamic_range_chart);

    std::unique_ptr svg_xml_normal_info = juce::XmlDocument::parse(svg_string_normal_info);
    drawable_normal_info = juce::Drawable::createFromSVG(*svg_xml_normal_info);

    std::unique_ptr svg_xml_highlight_info = juce::XmlDocument::parse(svg_string_highlight_info);
    drawable_highlight_info = juce::Drawable::createFromSVG(*svg_xml_highlight_info);

    button_info.setTooltip("See DR range chart");
    button_info.setImages(drawable_normal_info.get(), drawable_highlight_info.get());
    button_info.onClick = [this]() {
        DynamicRangeChart* popup = new DynamicRangeChart(
            "Dynamic Range Chart",
            juce::Colours::black,
            true,
            drawable_chart
        );
        popup->setVisible(true);
    };
    addAndMakeVisible(button_info);

    std::unique_ptr svg_xml_normal_copy_params = juce::XmlDocument::parse(svg_string_normal_copy_params);
    drawable_normal_copy_params = juce::Drawable::createFromSVG(*svg_xml_normal_copy_params);

    std::unique_ptr svg_xml_highlight_copy_params = juce::XmlDocument::parse(svg_string_highlight_copy_params);
    drawable_highlight_copy_params = juce::Drawable::createFromSVG(*svg_xml_highlight_copy_params);

    button_copy_params.setTooltip("Show Measurements as Text");
    button_copy_params.setImages(drawable_normal_copy_params.get(), drawable_highlight_copy_params.get());
    button_copy_params.onClick = [this]() {
        auto parameters = juce::String("Frequencies [Hz], Delta N-th Channel Gains [dB]\n===============================================\n");
        for (int i = 0; i < audioProcessor.len_ap_freq;++i)
        {
            parameters += juce::String(audioProcessor.ap_freqs[i]);
            if (i == audioProcessor.len_ap_freq - 1)
                continue;
            else
                parameters += juce::String(", ");
        }
        
        parameters << juce::String("\n");

        for (int i = 0; i < audioProcessor.table_crest_factor_params.size();++i)
        {
            size_t loop_size = audioProcessor.table_crest_factor_params[i].size();
            for (int j = 1; j < loop_size;++j)
            {
                parameters += audioProcessor.table_crest_factor_params[i][j];
                if (j == loop_size - 1)
                    continue;
                else
                    parameters += juce::String(", ");
            }
            parameters += juce::String("\n");
        }

        TableWindow* popup = new TableWindow(
            "Allpass Crest Factor Table Parameters",
            juce::Colours::black,
            true,
            parameters.removeCharacters("+")
        );
        popup->setVisible(true);
    };
    addAndMakeVisible(button_copy_params);

    std::unique_ptr svg_xml_normal_reset = juce::XmlDocument::parse(svg_string_normal_reset);
    drawable_normal_reset = juce::Drawable::createFromSVG(*svg_xml_normal_reset);

    std::unique_ptr svg_xml_highlight_reset = juce::XmlDocument::parse(svg_string_highlight_reset);
    drawable_highlight_reset = juce::Drawable::createFromSVG(*svg_xml_highlight_reset);

    button_reset.setTooltip("Clear Plot");
    button_reset.setImages(drawable_normal_reset.get(), drawable_highlight_reset.get());
    button_reset.onClick = [this]() {
        clear();
    };
    addAndMakeVisible(button_reset);

    button_dr_meter.setTooltip("DR Meter");
    button_dr_meter.setButtonText(juce::String("00"));
    button_dr_meter.setColour(juce::TextButton::textColourOffId, main_text_colour);
    button_dr_meter.setColour(juce::TextButton::buttonColourId, shade_colour_look_and_feel1);
    button_dr_meter.onClick = [this]() {
        DynamicRangeByChannel* popup = new DynamicRangeByChannel(
            "Dynamic Range of Channels",
            juce::Colours::black,
            true,
            audioProcessor.dr_measurements_channels_text
        );
        popup->setVisible(true);
    };
    addAndMakeVisible(button_dr_meter);

    std::unique_ptr svg_xml_normal_enable_disable_operations = juce::XmlDocument::parse(
        svg_string_normal_enable_disable_operations
    );
    drawable_normal_enable_disable_operations = juce::Drawable::createFromSVG(
        *svg_xml_normal_enable_disable_operations
    );

    std::unique_ptr svg_xml_highlight_enable_disable_operations = juce::XmlDocument::parse(
        svg_string_highlight_enable_disable_operations
    );
    drawable_highlight_enable_disable_operations = juce::Drawable::createFromSVG(
        *svg_xml_highlight_enable_disable_operations
    );

    button_enable_disable_operations.setTooltip("Enable or disable");
    button_enable_disable_operations.setClickingTogglesState(true);
    button_enable_disable_operations.setImages(
        drawable_normal_enable_disable_operations.get(),//normalImage
        drawable_normal_enable_disable_operations.get(),//overImage
        drawable_normal_enable_disable_operations.get(),//downImage
        drawable_normal_enable_disable_operations.get(),//disabledImage
        drawable_highlight_enable_disable_operations.get(),//normalImageOn
        drawable_highlight_enable_disable_operations.get(),//overImageOn
        drawable_highlight_enable_disable_operations.get(),//downImageOn
        drawable_normal_enable_disable_operations.get()//disabledImageOn
    );
    button_enable_disable_operations.setToggleState(
        audioProcessor.is_plugin_enabled,
        juce::NotificationType::dontSendNotification
    );
    button_enable_disable_operations.setColour(
        //background colour, when enabled
        juce::DrawableButton::backgroundOnColourId,
        juce::Colours::transparentWhite
    );
    button_enable_disable_operations.onClick = [this]() {
        audioProcessor.is_plugin_enabled = button_enable_disable_operations.getToggleState();
    };
    addAndMakeVisible(button_enable_disable_operations);

    crest_plot_type.setTooltip("Bands for Allpass Crest Factor Plot");
    crest_plot_type.setColour(juce::ComboBox::textColourId, main_text_colour);
    crest_plot_type.addItem("7 QUICK OCTAVES", 1);
    crest_plot_type.addItem("10 ISO 266", 2);
    crest_plot_type.addItem("31 1/3 OCTAVES", 3);
    crest_plot_type.onChange = [this] {
        audioProcessor.set_ap_freqs(crest_plot_type.getSelectedId());
    };
    crest_plot_type.setSelectedId(2);
    addAndMakeVisible(crest_plot_type);

    //initial crest factor table
    //link data in AudioProcessor with TableModel
    audioProcessor.table_crest_factor_params = std::vector<std::vector<juce::String>>();
    table_crest_factor.model.data = &audioProcessor.table_crest_factor_params;
    table_crest_factor.model.ap_peak_index = &audioProcessor.ap_peak_index;
    table_crest_factor.model.table_init_done = true;
    table_crest_factor.model.audio_colours = &audio_colours;
    table_crest_factor.model.shade_colour_look_and_feel1 = shade_colour_look_and_feel1;
    table_crest_factor.model.shade_colour1 = shade_colour_look_and_feel1.brighter(0.06f);
    table_crest_factor.model.shade_colour2 = shade_colour_look_and_feel1.brighter(0.2f);
    addAndMakeVisible(table_crest_factor);

    setSize(956, 412);//window size, 5px pading
    setResizable(false, false);
}

MasVisGtkPluginAudioProcessorEditor::~MasVisGtkPluginAudioProcessorEditor()
{
    audioProcessor.removeChangeListener(this);
}

void MasVisGtkPluginAudioProcessorEditor::paint(juce::Graphics& g)
{
    //check GUI does need to paint
    if (audioProcessor.ready_to_paint)
    {
        //component is opaque, so we must completely
        //fill the background with a solid colour
        g.fillAll(juce::Colours::black);

        hist_component.repaint();
        ap_cf_component.repaint();

        //reset columns, if files have changed (mono, stereo, etc.)
        table_crest_factor.reset_columns(audioProcessor.len_ap_freq, audioProcessor.ap_freqs);
        table_crest_factor.table.updateContent();

        //show dynamic range meter measurements
        button_dr_meter.setButtonText(audioProcessor.dr_measurements_avg_text);

        //paint dynamic range meter background
        switch ((int)audioProcessor.dr_measurements_avg)
        {
            case 1:
            case 2:
            case 3:
            case 4:
            case 5:
            case 6:
            case 7:
                button_dr_meter.setColour(button_dr_meter.textColourOffId, shade_colour_look_and_feel1);
                button_dr_meter.setColour(juce::TextButton::buttonColourId, dr_style07);
                break;
            case 8:
                button_dr_meter.setColour(button_dr_meter.textColourOffId, shade_colour_look_and_feel1);
                button_dr_meter.setColour(juce::TextButton::buttonColourId, dr_style08);
                break;
            case 9:
                button_dr_meter.setColour(button_dr_meter.textColourOffId, shade_colour_look_and_feel1);
                button_dr_meter.setColour(juce::TextButton::buttonColourId, dr_style09);
                break;
            case 10:
                button_dr_meter.setColour(button_dr_meter.textColourOffId, shade_colour_look_and_feel1);
                button_dr_meter.setColour(juce::TextButton::buttonColourId, dr_style10);
                break;
            case 11:
                button_dr_meter.setColour(button_dr_meter.textColourOffId, shade_colour_look_and_feel1);
                button_dr_meter.setColour(juce::TextButton::buttonColourId, dr_style11);
                break;
            case 12:
                button_dr_meter.setColour(button_dr_meter.textColourOffId, shade_colour_look_and_feel1);
                button_dr_meter.setColour(juce::TextButton::buttonColourId, dr_style12);
                break;
            case 13:
                button_dr_meter.setColour(button_dr_meter.textColourOffId, shade_colour_look_and_feel1);
                button_dr_meter.setColour(juce::TextButton::buttonColourId, dr_style13);
                break;
            case 14:
                button_dr_meter.setColour(button_dr_meter.textColourOffId, shade_colour_look_and_feel1);
                button_dr_meter.setColour(juce::TextButton::buttonColourId, dr_style14);
                break;
            default:
                button_dr_meter.setColour(button_dr_meter.textColourOffId, main_text_colour);
                button_dr_meter.setColour(juce::TextButton::buttonColourId, shade_colour_look_and_feel1);
                break;
        }
    }

    //finished painting
    if (audioProcessor.ready_to_paint)
        audioProcessor.ready_to_paint = false;
}

//update UI components
void MasVisGtkPluginAudioProcessorEditor::changeListenerCallback(juce::ChangeBroadcaster* source)
{
    if (source == &audioProcessor) {
        audioProcessor.ready_to_paint = true;
        repaint();

        //show any errors in popup
        if (audioProcessor.processing_error.length() > 0)
        {
            //show alert on exception
            juce::AlertWindow alertWindow("", "", juce::AlertWindow::WarningIcon);
            alertWindow.showMessageBoxAsync(
                juce::AlertWindow::WarningIcon,
                "Error Information",
                audioProcessor.processing_error,
                "Dismiss",
                this,
                NULL
            );
        }
    }
}

void MasVisGtkPluginAudioProcessorEditor::clear()
{
    audioProcessor.clear();
    audioProcessor.prepare_params();
    audioProcessor.ready_to_paint = true;
    repaint();
}

//size and placement
void MasVisGtkPluginAudioProcessorEditor::resized()
{
    hist_component.setBounds(5, 5, 600, 315);
    ap_cf_component.setBounds(600, 5, 356, 315);
    table_crest_factor.setBounds(5, 325, 600, 82);
    button_invert_plot.setBounds(735, 335, 100, 30);
    button_info.setBounds(635, 373, 30, 30);
    button_dr_meter.setBounds(670, 373, 60, 30);
    crest_plot_type.setBounds(738, 373, 99, 30);
    button_copy_params.setBounds(842, 373, 30, 30);
    button_reset.setBounds(875, 373, 30, 30);
    button_enable_disable_operations.setBounds(907, 373, 30, 30);
}