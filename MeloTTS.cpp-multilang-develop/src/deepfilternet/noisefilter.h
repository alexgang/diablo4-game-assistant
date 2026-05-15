#ifndef NOISE_FILTER_H
#define NOISE_FILTER_H
#ifdef USE_DEEPFILTERNET
#include "deepfilter.h"
#include <string>
#include <vector>

namespace melo {
  class NoiseFilter {
    public:
      explicit NoiseFilter();
      ~NoiseFilter();
      void init(std::unique_ptr<ov::Core>& core,
                const std::string aModel_path,
                const std::string aModel_device);
      ov::AnyMap set_nf_ov_cfg(const std::string& device_name);
      void proc(std::vector<float>& aMamples);
    private:
      ov_deepfilternet::DeepFilter mDeepfilter;
  };
}
#endif // USE_DEEPFILTERNET
#endif // NOISE_FILTER_H