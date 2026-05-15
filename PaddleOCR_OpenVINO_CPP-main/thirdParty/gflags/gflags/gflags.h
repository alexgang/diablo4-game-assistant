#pragma once
#include <string>
#include <vector>
#include <iostream>

namespace gflags {

inline std::vector<std::pair<std::string*, std::string>>& GetFlagRegistry() {
    static std::vector<std::pair<std::string*, std::string>> registry;
    return registry;
}

inline bool ParseCommandLineFlags(int* argc, char*** argv, bool remove_flags) {
    for (int i = 1; i < *argc; i++) {
        std::string arg((*argv)[i]);
        if (arg.substr(0, 2) == "--") {
            size_t eq = arg.find('=');
            if (eq != std::string::npos) {
                std::string key = arg.substr(2, eq - 2);
                std::string val = arg.substr(eq + 1);
                for (auto& flag : GetFlagRegistry()) {
                    if (flag.second == key) {
                        *flag.first = val;
                        break;
                    }
                }
            }
        }
    }
    return true;
}

} // namespace gflags

#define DEFINE_string(name, val, desc) \
    std::string FLAGS_##name = val; \
    static bool _reg_##name = (gflags::GetFlagRegistry().push_back({&FLAGS_##name, #name}), true);

#define DECLARE_string(name) \
    extern std::string FLAGS_##name;
