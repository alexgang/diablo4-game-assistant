#include <filesystem>
#include <fstream>
#include <memory>
#include <iostream>
#include <openvino/openvino.hpp>
#define USE_DEEPFILTERNET 0
//#include "bert.h"
#include "openvoice_tts.h"
#include "info_data.h"
#define OV_MODEL_PATH "ov_models"
/*This file to test openvoice tts model only,
decoupled with bert and other part
The file must compile with -DUSE_DEEPFILTERNET=OFF
*/

void write_wave(const std::string& filename, int32_t sampling_rate, const float* samples, int32_t n)
{

    melo::WaveHeader header;
    header.chunk_id = 0x46464952;     // FFIR
    header.format = 0x45564157;       // EVAW
    header.subchunk1_id = 0x20746d66; // "fmt "
    header.subchunk1_size = 16;       // 16 for PCM
    header.audio_format = 1;          // PCM =1

    int32_t num_channels = 1;
    int32_t bits_per_sample = 16; // int16_t
    header.num_channels = num_channels;
    header.sample_rate = sampling_rate;
    header.byte_rate = sampling_rate * num_channels * bits_per_sample / 8;
    header.block_align = num_channels * bits_per_sample / 8;
    header.bits_per_sample = bits_per_sample;
    header.subchunk2_id = 0x61746164; // atad
    header.subchunk2_size = n * num_channels * bits_per_sample / 8;

    header.chunk_size = 36 + header.subchunk2_size;

    std::vector<int16_t> samples_int16(n);
    for (int32_t i = 0; i != n; ++i)
    {
        samples_int16[i] = samples[i] * 32676;
    }

    std::ofstream os(filename, std::ios::binary);
    if (!os)
    {
        std::string msg = "Failed to create " + filename;
    }

    os.write(reinterpret_cast<const char*>(&header), sizeof(header));
    os.write(reinterpret_cast<const char*>(samples_int16.data()),
        samples_int16.size() * sizeof(int16_t));

    std::cout << "write wav to " << filename << std::endl;
    return;
}
std::unordered_map<int, std::string> speaker_ids = {
    {0, "EN-US"},
    {1, "EN-BR"},
    {2, "EN-INDIA"},
    {3, "EN-AU"},
    {4, "EN-Default"}
};

int main() {
    std::filesystem::path model_dir = "C:\\Users\\gta\\source\\repos\\MeloTTS.cpp\\ov_models";
    std::unique_ptr<ov::Core> core_ptr = std::make_unique<ov::Core>();
    std::filesystem::path zh_tts_path = model_dir / "tts_en.xml";
    std::cout << std::filesystem::absolute(zh_tts_path);
    melo::OpenVoiceTTS model(core_ptr, zh_tts_path.string(), "CPU", set_tts_config("CPU", true), "EN");

    std::vector<std::vector<float>> phone_level_feature;

    std::vector<int64_t> phones_ids{ 0,   0,   0,  29,   0, 215,   0,  39,   0,  71,   0,  87,   0,  80,
          0,  90,   0,  85,   0,  59,   0,  70,   0,  34,   0,  89,   0, 103,
          0,  30,   0,  65,   0,  87,   0,  89,   0,  39,   0,  82,   0,  59,
          0,  74,   0,  59,   0,  73,   0,  89,   0, 103,   0,  23,   0,  73,
          0, 103,   0,  33,   0,  22,   0,  82,   0,  89,   0,  43,   0,  23,
          0,  14,   0,  71,   0,  29,   0,  70,   0,  29,   0,  45,   0, 210,
          0,   0,   0 };
    std::vector<int64_t> lang_ids{ 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2,
        0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2,
        0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2,
        0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0 };
    std::vector <int64_t> tones{ 0, 7, 0, 9, 0, 7, 0, 9, 0, 7, 0, 7, 0, 9, 0, 7, 0, 7, 0, 9, 0, 7, 0, 7,
        0, 7, 0, 9, 0, 7, 0, 9, 0, 7, 0, 7, 0, 9, 0, 7, 0, 8, 0, 7, 0, 8, 0, 7,
        0, 7, 0, 9, 0, 8, 0, 7, 0, 9, 0, 7, 0, 9, 0, 7, 0, 7, 0, 8, 0, 9, 0, 7,
        0, 7, 0, 9, 0, 7, 0, 9, 0, 7, 0, 7, 0, 7, 0 };
    std::vector<float> wav_data;
    for (auto &[speaker_id, style_name]:speaker_ids) {
        auto startTime = Time::now();
        wav_data = model.tts_infer(phones_ids, tones, lang_ids, phone_level_feature, 1.0, speaker_id, true);//disable_bert;
        auto inferTime = get_duration_ms_till_now(startTime);
        std::cout << "model infer time:" << inferTime << " ms" << std::endl;

        std::cout << "wav infer ok\n";
        write_wave(std::format("test_openvoice_tts_{}.wav",style_name), 44100, wav_data.data(), wav_data.size());
        std::cout << "write wav ok\n";
    }

    std::cout << "Succeed!\n";
    return 0;
}