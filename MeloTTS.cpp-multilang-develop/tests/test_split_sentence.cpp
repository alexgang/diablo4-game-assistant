//#define CRT_
#ifdef CRT_
#define _CRTDBG_MAP_ALLOC
#include <stdlib.h>
#include <crtdbg.h>
#endif
#define OV_MODEL_PATH "ov_models"
#include <iostream>
#include <vector>
#include <numeric>
#include <darts.h>
#include <string>
#include <algorithm>
#include <sstream>
#include <filesystem>
#include <unordered_set>
#ifdef _WIN32
#include <codecvt>
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#endif
#include "darts.h"

Darts::DoubleArray da;

// This function mimics Python's len() function.
// It counts each character, treating both letters, Chinese characters and space as 1 unit of length.
// use utf-8 Chinese characters
// no punctuation here!
inline size_t str_len(const std::string& s) {
    int strSize = s.size();
    int i = 0;
    int cnt = 0;
    while (i < strSize)
    {
        //English letters
        if (s[i] <= 'z' && s[i] >= 'a' || s[i] <= 'Z' && s[i] >= 'A') {
            ++cnt;
            ++i;
        }
        else { //Chinese characters
            int len = 1;
            for (int j = 0; j < 6 && (s[i] & (0x80 >> j)); j++)
            {
                len = j + 1;
            }
            ++cnt;
            i += len;
        }
    }
    return cnt;
}
std::unordered_set<int> sentence_splitter = {
    // "，", "。", "！", "？","；",
     ',', '.', '!', '?', ';',
};

std::vector<std::string> split_sentences_zh(const std::string& text, size_t min_len = 10) {
    std::vector<std::string> sentences;
    int n = text.length();
    int MAX_HIT = 1;
    std::string tmp;
    for (int i = 0; i < n; ) {
        const char* query = text.data() + i;
        std::vector<Darts::DoubleArray::result_pair_type> results(MAX_HIT);
        size_t num_matches = da.commonPrefixSearch(query, results.data(), MAX_HIT);
        for (int i = 0; i < n; ) {
            const char* query = text.data() + i;
            std::vector<Darts::DoubleArray::result_pair_type> results(MAX_HIT);
            size_t num_matches = da.commonPrefixSearch(query, results.data(), MAX_HIT);
            if (!num_matches) {
                tmp += text[i++];
            }
            else if ((text[i] == ',' || text[i] == '.') && i > 0 && i < n && std::isdigit(static_cast<int>(text[i - 1])) && std::isdigit(static_cast<int>(text[i + 1]))) {
                if (text[i] == '.')
                    tmp += "."; // Keep the decimal point here for subsequent text normalization processing.
                i += results.front().length;
            }
            else if (sentence_splitter.contains(results.front().value)) { // text splitter
                tmp += static_cast<char>(results.front().value);
                sentences.emplace_back(std::move(tmp));
                tmp.clear();
                i += results.front().length;
            }
            else if (results.front().value == 3) { // space it is meaningful to english words
                tmp += " ";
                i += results.front().length;
            }
            else if (results.front().value == 0) { // skip certain punctuations
                i += results.front().length;
            }
            else {
                tmp += static_cast<char>(results.front().value);
                i += results.front().length;
            }

        }

    }
    if(tmp.size())
        sentences.emplace_back(std::move(tmp));
    
    std::vector<std::string> new_sentences;
    size_t count_len = 0;
    std::string new_sent;
    int m = sentences.size();
    for (int i = 0; i < m; ++i) {
        new_sent += sentences[i] + " ";
        count_len += str_len(sentences[i]);
        if (count_len > min_len || i == m - 1) {

            if (new_sent.back() == ' ') new_sent.pop_back();
            new_sentences.emplace_back(std::move(new_sent));
            new_sent.clear();
            count_len = 0;
        }
    }
    // merge_short_sentences_zh
    // here we fix use the default min_len, so only need to check if the len(new_sentences[-1])<= 2 ;consistent with the Python code
    if (new_sentences.size() >= 2 && str_len(new_sentences.back()) <= 2) {
        new_sentences[new_sentences.size() - 2] += new_sentences.back();
        new_sentences.pop_back();
    }
    return new_sentences;

}

std::vector<std::string> split_sentences_into_pieces(const std::string& text, bool quiet = false) {

    auto pieces = split_sentences_zh(text);
    if (!quiet) {
        std::cout << " > Text split to sentences." << std::endl;
        for (const auto& piece : pieces) {
            std::cout <<"   "<<piece << std::endl;
        }
        std::cout << " > ===========================" << std::endl;
    }
    return pieces;
}


int main() {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    system("chcp 65001"); //Using UTF-8 Encoding
#endif
   std::string a = ", ";
    std::cout << a.size() << std::endl;
    std::filesystem::path model_dir = "C:\\Users\\gta\\source\\develop\\MeloTTS.cpp\\build\\tests";
    std::filesystem::path punc_dir = model_dir / "punc_.dic";
    da.open(punc_dir.string().c_str());
    std::cout << "open dict\n";
    auto res = split_sentences_into_pieces("，\n我最近在学习machine learning, 希望'\n能够在未来的artificial intelligence领域有所建树");

   // auto res1= splitTextByPunctuation("我最近在学习machine learning, 希望能够在未来的artificial intelligence领域有所建树");

#ifdef CRT_
#define _CRTDBG_MAP_ALLOC
#include <stdlib.h>
#include <crtdbg.h>
#endif
}