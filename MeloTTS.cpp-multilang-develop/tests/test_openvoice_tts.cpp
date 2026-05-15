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

        std::cout << "write wav to "<< filename << std::endl;
        return;
    }
int main() {
    std::cout <<"main start\n";
    std::filesystem::path model_dir = OV_MODEL_PATH;
    std::unique_ptr<ov::Core> core_ptr = std::make_unique<ov::Core>();
    std::filesystem::path zh_tts_path = model_dir / "tts_zn_mix_en_int8.xml";
    std::cout << std::filesystem::absolute(zh_tts_path);
    melo::OpenVoiceTTS model(core_ptr, zh_tts_path.string(),"CPU", set_tts_config("CPU", true), "ZH");

    std::vector<std::vector<float>> phone_level_feature;

    std::vector<int64_t> phones_ids{ 0,  0,  0, 19,  0, 44,  0, 99,  0, 40,  0, 73,  0, 40,  0, 57,  0, 12,
          0, 60,  0, 71,  0, 18,  0, 59,  0, 32,  0, 37,  0, 89,  0, 55,  0, 49,
          0, 57,  0, 26,  0, 62,  0, 31,  0, 21,  0, 67,  0, 37,  0, 14,  0, 77,
          0, 82,  0, 77,  0, 52,  0, 21,  0, 14,  0, 34,  0, 12,  0, 63,  0, 57,
          0, 77,  0, 12,  0, 62,  0, 10,  0, 74,  0, 35,  0, 99,  0, 12,  0, 60,
          0, 12,  0, 62,  0, 78,  0, 76,  0, 78,  0, 89,  0, 23,  0, 16,  0, 73,
          0, 95,  0, 77,  0, 52,  0, 23,  0, 26,  0, 60,  0, 82,  0, 19,  0, 14,
          0, 77,  0, 52,  0, 21,  0, 14,  0, 78,  0, 28,  0, 60,  0, 71,  0, 59,
          0, 12,  0, 78,  0, 10,  0, 74,  0, 35,  0, 99,  0, 12,  0, 60,  0, 12,
          0, 62,  0, 78,  0, 76,  0,  0,  0 };
    std::vector<int64_t> lang_ids{ 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3,
     0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3,

     0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3,
     0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3,
     0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3,
     0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3,
     0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3, 0, 3,
     0, 3, 0 };
    std::vector <int64_t> tones{ 0, 0, 0, 1, 0, 1, 0, 4, 0, 4, 0, 4, 0, 4, 0, 7, 0, 8, 0, 7, 0, 7, 0, 9,
     0, 7, 0, 8, 0, 4, 0, 4, 0, 4, 0, 4, 0, 3, 0, 3, 0, 2, 0, 2, 0, 2, 0, 2,
     0, 2, 0, 2, 0, 4, 0, 4, 0, 2, 0, 2, 0, 1, 0, 1, 0, 7, 0, 9, 0, 7, 0, 7,
     0, 7, 0, 8, 0, 7, 0, 9, 0, 7, 0, 7, 0, 7, 0, 8, 0, 7, 0, 8, 0, 7, 0, 7,
     0, 7, 0, 1, 0, 1, 0, 3, 0, 3, 0, 1, 0, 1, 0, 1, 0, 1, 0, 5, 0, 5, 0, 2,
     0, 2, 0, 3, 0, 3, 0, 2, 0, 2, 0, 1, 0, 1, 0, 7, 0, 9, 0, 7, 0, 7, 0, 7,
     0, 8, 0, 7, 0, 9, 0, 7, 0, 7, 0, 7, 0, 8, 0, 7, 0, 8, 0, 7, 0, 7, 0, 7,
     0, 0, 0 };
     std::vector<float> wav_data;
     for(int i =0;i<20;++i){
        auto startTime  = Time::now();
        wav_data = model.tts_infer(phones_ids, tones, lang_ids, phone_level_feature,1.0,1,true);//disable_bert;
        auto inferTime = get_duration_ms_till_now(startTime);
        std::cout << "model infer time:" << inferTime << " ms" << std::endl;
    }
     std::cout << "wav infer ok\n";
     write_wave("test_openvoice_tts.wav", 44100, wav_data.data(),wav_data.size());
     std::cout << "write wav ok\n";


    return 0;
}