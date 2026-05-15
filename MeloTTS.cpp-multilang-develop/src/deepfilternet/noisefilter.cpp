/**
 * Copyright      2024    Vincent Liu (vincent1.liu@intel.com)
 *
 * See LICENSE for clarification regarding multiple authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#ifdef USE_DEEPFILTERNET
#include "noisefilter.h"
#include <string>
#include <vector>
#include <iostream>
#include <openvino/openvino.hpp>

namespace melo {
  NoiseFilter::NoiseFilter()
  {
    std::cout << " NoiseFilter " << std::endl;
  }

  NoiseFilter::~NoiseFilter()
  {}

  void NoiseFilter::init(std::unique_ptr<ov::Core>& core,
                         const std::string aModel_path,
                         const std::string aModel_device) {
  	/* can be DEEPFILTERNET2 or DEEPFILTERNET3 */
    std::cout << " NoiseFilter::init. aModel_path = " << aModel_path << " nf devices = " << aModel_device << std::endl;
    auto dfnet_version = ov_deepfilternet::ModelSelection::DEEPFILTERNET3;
    mDeepfilter.Init(core, aModel_path, aModel_device, dfnet_version, set_nf_ov_cfg(aModel_device));
  }

  ov::AnyMap NoiseFilter::set_nf_ov_cfg(const std::string& device_name) {
    ov::AnyMap device_config = {};
    device_config[ov::cache_dir.name()] = "cache";

    if (device_name.find("CPU") != std::string::npos) {
      device_config[ov::hint::scheduling_core_type.name()] = ov::hint::SchedulingCoreType::PCORE_ONLY;
      device_config[ov::hint::enable_hyper_threading.name()] = false;
      device_config[ov::hint::enable_cpu_pinning.name()] = true;
      device_config[ov::enable_profiling.name()] = false;
    }

    if (device_name.find("GPU") != std::string::npos) {
      device_config[ov::intel_gpu::hint::queue_throttle.name()] = ov::intel_gpu::hint::ThrottleLevel::MEDIUM;
      device_config[ov::intel_gpu::hint::queue_priority.name()] = ov::hint::Priority::MEDIUM;
      device_config[ov::intel_gpu::hint::host_task_priority.name()] = ov::hint::Priority::HIGH;
      device_config[ov::hint::enable_cpu_pinning.name()] = true;
      device_config[ov::enable_profiling.name()] = false;
      device_config[ov::intel_gpu::hint::enable_kernels_reuse.name()] = true;
    }

    if (device_name.find("NPU") != std::string::npos) {
      device_config["NPU_COMPILER_TYPE"] = "DRIVER";
      device_config["NPU_COMPILATION_MODE"] = "DefaultHW";
      device_config["PERF_COUNT"] = "NO";
      device_config["NPU_COMPILATION_MODE_PARAMS"] = "vertical-fusion=true dpu-profiling=false dma-profiling=false sw-profiling=false dump-task-stats=true enable-schedule-trace=false";
      device_config["NPU_USE_ELF_COMPILER_BACKEND"] = "YES";
      device_config["PERFORMANCE_HINT"] = "LATENCY";
      device_config["NPU_DPU_GROUPS"] = "2";
    }

    return device_config;
  }


  void NoiseFilter::proc(std::vector<float>& aMamples) {
    torch::Tensor input_wav_tensor = torch::from_blob(aMamples.data(), { 1, (int64_t)aMamples.size() });
    aMamples = mDeepfilter.filter(input_wav_tensor);
  }
}
#endif // USE_DEEPFILTERNET
