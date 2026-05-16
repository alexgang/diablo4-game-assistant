#!/usr/bin/env python3
"""
OpenVINO 模型推理模块 - 直接使用 Python OpenVINO 库推理

支持：
1. PaddleOCR (检测 + 识别)
2. MeloTTS (语音合成)
"""

import sys
import os
import time
import re
import json
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylibs'))

from openvino import Core


class OpenVINOInferenceEngine:
    """OpenVINO 推理引擎基类"""

    def __init__(self, model_dir=None, device='AUTO'):
        self.core = Core()
        self.device = device
        self.model_dir = model_dir
        self.models = {}
        self.compiled_models = {}
        self.infer_requests = {}

    def load_model(self, name, model_path, weights_path=None):
        """加载模型"""
        if weights_path:
            model = self.core.read_model(model=model_path, weights=weights_path)
        else:
            model = self.core.read_model(model=model_path)
        self.models[name] = model
        compiled = self.core.compile_model(model, self.device)
        self.compiled_models[name] = compiled
        self.infer_requests[name] = compiled.create_infer_request()
        return compiled

    def infer(self, name, inputs):
        """推理"""
        request = self.infer_requests[name]
        if isinstance(inputs, dict):
            request.infer(inputs)
        else:
            request.infer({0: inputs})
        outputs = {}
        for i, output in enumerate(self.compiled_models[name].outputs):
            outputs[i] = request.get_output_tensor(i).data
        return outputs


class PaddleOCREngine(OpenVINOInferenceEngine):
    """PaddleOCR OpenVINO 引擎 - 检测 + 识别"""

    def __init__(self, model_dir=None, device='AUTO'):
        if not model_dir:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            model_dir = os.path.join(base_dir, 'PaddleOCR_OpenVINO_CPP-main', 'models')
        super().__init__(model_dir=model_dir, device=device)
        self._load_models()
        self._load_characters()

    def _load_models(self):
        """加载 OCR 模型"""
        det_model = os.path.join(self.model_dir, 'ch_PP-OCRv4_det_infer', 'inference.pdmodel')
        det_params = os.path.join(self.model_dir, 'ch_PP-OCRv4_det_infer', 'inference.pdiparams')
        rec_model = os.path.join(self.model_dir, 'ch_PP-OCRv4_rec_infer', 'inference.pdmodel')
        rec_params = os.path.join(self.model_dir, 'ch_PP-OCRv4_rec_infer', 'inference.pdiparams')
        cls_model = os.path.join(self.model_dir, 'ch_ppocr_mobile_v2.0_cls_infer', 'inference.pdmodel')
        cls_params = os.path.join(self.model_dir, 'ch_ppocr_mobile_v2.0_cls_infer', 'inference.pdiparams')

        self.load_model('det', det_model, det_params)
        self.load_model('rec', rec_model, rec_params)
        self.load_model('cls', cls_model, cls_params)

    def _load_characters(self):
        """加载字符表"""
        label_path = os.path.join(
            os.path.dirname(self.model_dir), 'data', 'ppocr_keys_v1.txt'
        )
        self.characters = []
        if os.path.exists(label_path):
            with open(label_path, 'r', encoding='utf-8') as f:
                self.characters = [line.rstrip('\n') for line in f.readlines()]
        else:
            self.characters = []

    def preprocess_det(self, img):
        """预处理检测输入"""
        h, w = img.shape[:2]
        max_side = 1920
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            new_h = int(h * scale)
            new_w = int(w * scale)
            img = cv2.resize(img, (new_w, new_h))
        new_h = img.shape[0]
        new_w = img.shape[1]
        new_h = new_h + (32 - new_h % 32) if new_h % 32 != 0 else new_h
        new_w = new_w + (32 - new_w % 32) if new_w % 32 != 0 else new_w
        img = cv2.resize(img, (new_w, new_h))

        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)
        img = (img.astype(np.float32) / 255 - mean) / std
        img = img.transpose(2, 0, 1)
        img = np.expand_dims(img, axis=0)
        return img

    def postprocess_det(self, det_out, original_shape, processed_shape):
        """后处理检测输出 - 简单阈值化"""
        heatmap = det_out[0, 0, :, :]
        binary = (heatmap > 0.3).astype(np.uint8)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w * h < 50:
                continue
            boxes.append([x, y, x + w, y + h])
        return boxes

    def preprocess_rec(self, img):
        """预处理识别输入"""
        h, w = img.shape[:2]
        target_h = 48
        target_w = int(target_h * w / h)
        target_w = max(target_w, 10)
        if target_w % 4 != 0:
            target_w = target_w + (4 - target_w % 4)
        img = cv2.resize(img, (target_w, target_h))

        mean = np.array([0.5, 0.5, 0.5], dtype=np.float32).reshape(1, 1, 3)
        std = np.array([0.5, 0.5, 0.5], dtype=np.float32).reshape(1, 1, 3)
        img = (img.astype(np.float32) / 255 - mean) / std
        img = img.transpose(2, 0, 1)
        img = np.expand_dims(img, axis=0)
        return img

    def postprocess_rec(self, rec_out):
        """后处理识别输出"""
        preds = rec_out[0]
        text_indices = []
        prev_idx = -1
        for t in range(preds.shape[0]):
            idx = np.argmax(preds[t])
            if idx != 0 and idx != prev_idx:
                text_indices.append(idx)
            prev_idx = idx

        text = ''
        for idx in text_indices:
            if idx - 1 < len(self.characters):
                text += self.characters[idx - 1]
        return text

    def ocr(self, img):
        """完整 OCR 流程"""
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        original_shape = img.shape[:2]
        det_input = self.preprocess_det(img)

        det_out = self.infer('det', det_input)
        boxes = self.postprocess_det(det_out[0], original_shape, det_input.shape[2:])

        results = []
        for box in boxes:
            x1, y1, x2, y2 = box
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(original_shape[1], x2)
            y2 = min(original_shape[0], y2)
            crop = img[y1:y2, x1:x2]
            if crop.shape[0] < 10 or crop.shape[1] < 10:
                continue

            rec_input = self.preprocess_rec(crop)
            rec_out = self.infer('rec', rec_input)
            text = self.postprocess_rec(rec_out[0])

            if text.strip():
                results.append({
                    'text': text,
                    'bbox': [x1, y1, x2, y2],
                    'confidence': 0.8,
                })
        return results

    def extract_text(self, img):
        """简单提取文字"""
        results = self.ocr(img)
        texts = [r['text'] for r in results if r.get('text')]
        return ' '.join(texts)


class MeloTTSEngine(OpenVINOInferenceEngine):
    """MeloTTS OpenVINO 引擎 - 语音合成"""

    def __init__(self, model_dir=None, device='AUTO'):
        if not model_dir:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            model_dir = os.path.join(base_dir, 'MeloTTS.cpp-multilang-develop', 'ov_models')
        super().__init__(model_dir=model_dir, device=device)
        self._load_models()
        self._load_assets()

    def _load_models(self):
        """加载 TTS 模型"""
        tts_xml = os.path.join(self.model_dir, 'tts_zn_mix_en_int8.xml')
        tts_bin = os.path.join(self.model_dir, 'tts_zn_mix_en_int8.bin')
        bert_xml = os.path.join(self.model_dir, 'bert_ZH_int8.xml')
        bert_bin = os.path.join(self.model_dir, 'bert_ZH_int8.bin')
        df_enc_xml = os.path.join(self.model_dir, 'deepfilternet3', 'enc.xml')
        df_enc_bin = os.path.join(self.model_dir, 'deepfilternet3', 'enc.bin')
        df_dec_xml = os.path.join(self.model_dir, 'deepfilternet3', 'df_dec.xml')
        df_dec_bin = os.path.join(self.model_dir, 'deepfilternet3', 'df_dec.bin')

        try:
            self.load_model('tts', tts_xml, tts_bin)
        except Exception as e:
            print(f'TTS model load failed: {e}')
        try:
            self.load_model('bert', bert_xml, bert_bin)
        except Exception as e:
            print(f'BERT model load failed: {e}')
        try:
            self.load_model('df_enc', df_enc_xml, df_enc_bin)
        except Exception as e:
            print(f'DF enc model load failed: {e}')
        try:
            self.load_model('df_dec', df_dec_xml, df_dec_bin)
        except Exception as e:
            print(f'DF dec model load failed: {e}')

    def _load_assets(self):
        """加载资源"""
        vocab_path = os.path.join(self.model_dir, 'vocab.txt')
        self.vocab = []
        if os.path.exists(vocab_path):
            with open(vocab_path, 'r', encoding='utf-8') as f:
                self.vocab = [line.rstrip('\n') for line in f.readlines()]
        self.vocab_to_idx = {phone: idx for idx, phone in enumerate(self.vocab)}
        
        vocab_bert_path = os.path.join(self.model_dir, 'vocab_bert.txt')
        self.bert_vocab = []
        if os.path.exists(vocab_bert_path):
            with open(vocab_bert_path, 'r', encoding='utf-8') as f:
                self.bert_vocab = [line.rstrip('\n') for line in f.readlines()]
        
        # 加载拼音到音素映射
        opencpop_path = os.path.join(self.model_dir, 'opencpop-strict.txt')
        self.pinyin_to_symbol = {}
        if os.path.exists(opencpop_path):
            with open(opencpop_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        self.pinyin_to_symbol[parts[0]] = parts[1].split()
        
        # 加载 cmudict
        cmudict_path = os.path.join(self.model_dir, 'cmudict_cache.txt')
        self.cmudict = {}
        if os.path.exists(cmudict_path):
            with open(cmudict_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        word = parts[0].lower()
                        self.cmudict[word] = [syl.split() for syl in parts[1].split('|')]
        
        # 声母表
        self.simple_initials = {'b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 'g', 'k', 'h',
                               'j', 'q', 'x', 'zh', 'ch', 'sh', 'r', 'z', 'c', 's', 'y', 'w'}
        self.compound_initials = {'zh', 'ch', 'sh'}
        self.v_rep_map = {'uei': 'ui', 'iou': 'iu', 'uen': 'un'}
        
        # 初始化 jieba 和 pypinyin
        try:
            import jieba
            import pypinyin
            self.jieba = jieba
            self.pypinyin = pypinyin
            self._has_jieba = True
        except ImportError:
            print('[WARNING] jieba or pypinyin not installed, using simple fallback')
            self._has_jieba = False

    def _split_initials_finals(self, raw_pinyin):
        """分割声母和韵母，例如：'bian1' -> ('b', 'ian1')"""
        n = len(raw_pinyin)
        if n == 0:
            return '', ''
        
        # 检查双字母声母
        if n > 2 and raw_pinyin[:2] in self.compound_initials:
            return raw_pinyin[:2], raw_pinyin[2:]
        elif raw_pinyin[0] in self.simple_initials:
            return raw_pinyin[:1], raw_pinyin[1:]
        else:
            return '', raw_pinyin

    def _get_initials_finals(self, word):
        """获取汉字的声母和韵母列表"""
        import re
        initials = []
        finals = []
        
        if not self._has_jieba:
            # 简单回退
            return initials, finals
        
        # 使用 pypinyin 获取拼音
        pinyin_list = self.pypinyin.lazy_pinyin(word, style=self.pypinyin.Style.TONE3)
        
        rep_map = {'.', '...', '?', ',', '!', '-', "'"}
        for piece in pinyin_list:
            if piece in rep_map:
                initials.append(piece)
                finals.append(piece)
            else:
                orig_initial, orig_final = self._split_initials_finals(piece)
                initials.append(orig_initial)
                finals.append(orig_final)
        
        return initials, finals

    def _chinese_g2p(self, word):
        """中文 G2P 处理"""
        phones_list = []
        tones_list = []
        
        initials, finals = self._get_initials_finals(word)
        
        for i in range(len(initials)):
            c = initials[i]
            v = finals[i]
            
            if c == v:
                phones_list.append(c)
                tones_list.append(0)
            else:
                # 提取声调
                tone = 0
                if v and v[-1].isdigit():
                    try:
                        tone = int(v[-1])
                        v = v[:-1]
                    except:
                        pass
                
                pinyin = c + v
                if v in self.v_rep_map:
                    pinyin = c + self.v_rep_map[v]
                
                # 映射到音素
                if pinyin in self.pinyin_to_symbol:
                    phones = self.pinyin_to_symbol[pinyin]
                    phones_list.extend(phones)
                    tones_list.extend([tone] * len(phones))
        
        return phones_list, tones_list

    def _english_g2p(self, word):
        """英文 G2P 处理"""
        phones_list = []
        tones_list = []
        
        word_lower = word.lower()
        
        # 处理缩写（单个字符）
        if len(word) <= 5:
            for ch in word_lower:
                if ch in self.cmudict:
                    syllables = self.cmudict[ch]
                    for syl in syllables:
                        for ph in syl:
                            if ph and ph[-1].isdigit():
                                phones_list.append(ph[:-1])
                                tones_list.append(int(ph[-1]) + 1)
                            else:
                                phones_list.append(ph)
                                tones_list.append(0)
        elif word_lower in self.cmudict:
            syllables = self.cmudict[word_lower]
            for syl in syllables:
                for ph in syl:
                    if ph and ph[-1].isdigit():
                        phones_list.append(ph[:-1])
                        tones_list.append(int(ph[-1]) + 1)
                    else:
                        phones_list.append(ph)
                        tones_list.append(0)
        
        return phones_list, tones_list

    def text_to_phones(self, text):
        """完整的文本到音素转换"""
        # 清理文本
        text = text.lower().strip()
        
        phones_list = ['_']
        tones_list = [0]
        
        if self._has_jieba:
            # 使用 jieba 分词和词性标注
            try:
                import jieba.posseg as pseg
                words = pseg.cut(text)
                
                tmp_chinese = []
                for word, tag in words:
                    if word == ' ':
                        continue
                    # 检查是否是英文
                    is_english = tag == 'eng' or all(ord(c) < 128 and (c.isalpha() or c.isspace()) for c in word)
                    
                    if is_english:
                        if tmp_chinese:
                            # 处理积累的中文
                            ch_phones, ch_tones = self._chinese_g2p(''.join(tmp_chinese))
                            phones_list.extend(ch_phones)
                            tones_list.extend(ch_tones)
                            tmp_chinese = []
                        # 处理英文
                        en_phones, en_tones = self._english_g2p(word)
                        phones_list.extend(en_phones)
                        tones_list.extend(en_tones)
                    else:
                        tmp_chinese.append(word)
                
                # 处理剩余的中文
                if tmp_chinese:
                    ch_phones, ch_tones = self._chinese_g2p(''.join(tmp_chinese))
                    phones_list.extend(ch_phones)
                    tones_list.extend(ch_tones)
            except Exception as e:
                print(f'[WARNING] G2P with jieba failed: {e}, falling back to simple')
                # 回退到简单处理
                return self._text_to_phones_simple(text)
        else:
            # 简单回退
            return self._text_to_phones_simple(text)
        
        phones_list.append('_')
        tones_list.append(0)
        
        # 转换为索引
        phone_indices = []
        for phone in phones_list:
            if phone in self.vocab_to_idx:
                phone_indices.append(self.vocab_to_idx[phone])
            else:
                phone_indices.append(0)
        
        return np.array(phone_indices, dtype=np.int64), np.array(tones_list, dtype=np.int64)

    def _text_to_phones_simple(self, text):
        """简单回退的文本转音素"""
        phones_list = ['_']
        tones_list = [0]
        
        for c in text:
            if '\u4e00' <= c <= '\u9fff':
                phones_list.append('SP')
                tones_list.append(1)
            elif c == ' ':
                phones_list.append('_')
                tones_list.append(0)
            elif c.isalpha():
                phones_list.append(c.lower())
                tones_list.append(0)
        
        phones_list.append('_')
        tones_list.append(0)
        
        phone_indices = []
        for phone in phones_list:
            if phone in self.vocab_to_idx:
                phone_indices.append(self.vocab_to_idx[phone])
            else:
                phone_indices.append(0)
        
        return np.array(phone_indices, dtype=np.int64), np.array(tones_list, dtype=np.int64)

    def synthesize(self, text, speaker=1, lang='ZH'):
        """合成语音"""
        phones, tones = self.text_to_phones(text)
        phones_length = np.array([len(phones)], dtype=np.int64)
        speakers = np.array([speaker], dtype=np.int64)
        lang_ids = np.zeros_like(phones, dtype=np.int64)
        bert_emb = np.zeros((1, 1024, len(phones)), dtype=np.float32)
        ja_bert = np.zeros((1, 768, len(phones)), dtype=np.float32)
        noise_scale = np.array([0.667], dtype=np.float32)
        length_scale = np.array([1.0], dtype=np.float32)
        noise_scale_w = np.array([0.8], dtype=np.float32)
        sdp_ratio = np.array([0.2], dtype=np.float32)

        t0 = time.time()
        tts_out = self.infer('tts', {
            0: np.expand_dims(phones, 0),
            1: phones_length,
            2: speakers,
            3: np.expand_dims(tones, 0),
            4: np.expand_dims(lang_ids, 0),
            5: bert_emb,
            6: ja_bert,
            7: noise_scale,
            8: length_scale,
            9: noise_scale_w,
            10: sdp_ratio,
        })
        audio = tts_out[0][0, 0, :]
        audio = (audio * 32767).clip(-32768, 32767).astype(np.int16)
        return audio, 44100

    def synthesize_to_file(self, text, output_path, speaker=1, lang='ZH'):
        """合成到文件"""
        import wave
        audio, sr = self.synthesize(text, speaker, lang)
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio.tobytes())
        return output_path


if __name__ == '__main__':
    print('Testing PaddleOCR...')
    ocr = PaddleOCREngine()

    test_img = np.ones((100, 500, 3), dtype=np.uint8) * 255
    test_img = cv2.rectangle(test_img, (0, 0), (500, 100), (255, 255, 255), -1)
    print('Testing OCR with blank image...')
    results = ocr.ocr(test_img)
    print(f'OCR found {len(results)} text regions')

    print('\nTesting MeloTTS...')
    tts = MeloTTSEngine()
    try:
        import tempfile
        output_wav = os.path.join(tempfile.gettempdir(), 'test_tts.wav')
        tts.synthesize_to_file('测试语音合成', output_wav)
        print(f'Synthesized audio to: {output_wav}')
        print(f'File size: {os.path.getsize(output_wav)} bytes')
    except Exception as e:
        print(f'TTS test failed: {e}')
