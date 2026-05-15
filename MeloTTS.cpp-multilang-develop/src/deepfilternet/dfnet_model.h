// Copyright (C) 2024 Intel Corporation
// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#ifdef USE_DEEPFILTERNET
#include <optional>
#include <openvino/openvino.hpp>
#include "multiframe.h"

namespace melo {
      namespace ov_deepfilternet {
         enum class ModelSelection
         {
            DEEPFILTERNET2,
            DEEPFILTERNET3,
         };

         class Mask;
         class DFNetModel
         {
         public:

            DFNetModel(
               std::unique_ptr<ov::Core>& core,
               std::string model_folder,
               std::string device,
               ModelSelection model_selection,
               const ov::AnyMap& nf_ov_cfg,
               torch::Tensor erb_widths,
               int64_t lookahead = 2, int64_t nb_df = 96);

            torch::Tensor
               forward(torch::Tensor spec, torch::Tensor feat_erb, torch::Tensor feat_spec, bool post_filter=false);

            int64_t num_static_hops()
            {
               return _num_hops;
            };
         private:

            torch::Tensor
               forward_df3(torch::Tensor spec, torch::Tensor feat_erb, torch::Tensor feat_spec, bool post_filter);

            [[maybe_unused]] torch::Tensor
               forward_df2(torch::Tensor spec, torch::Tensor feat_erb, torch::Tensor feat_spec);

            std::unique_ptr<ov::CompiledModel> _model_request_enc;
            std::unique_ptr<ov::CompiledModel> _model_request_erb_dec;
            std::unique_ptr<ov::CompiledModel> _model_request_df_dec;

            std::unique_ptr<ov::InferRequest> _infer_request_enc;
            std::unique_ptr<ov::InferRequest> _infer_request_erb_dec;
            std::unique_ptr<ov::InferRequest> _infer_request_df_dec;

            std::shared_ptr< torch::nn::ConstantPad3d > _pad_spec;
            std::shared_ptr< torch::nn::ConstantPad2d > _pad_feat;
            std::shared_ptr< Mask > _mask;

            int64_t _nb_df;
            DF _df;

            int64_t _num_hops;

            bool _bDF3;
         };
      }
}
#endif // USE_DEEPFILTERNET



