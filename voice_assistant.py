#!/usr/bin/env python3
"""
语音助手模块 - 语音输入识别 + 意图解析 + 语音回复

功能：
1. 语音输入：优先用服务端 ASR(Qwen ASR,OpenVINO iGPU),本地引擎(Google/Sphinx/Whisper)回退
2. 意图识别：解析玩家语音为搜索意图（查装备/查BOSS/查技能等）
3. 语音输出：TTS语音回复玩家（pyttsx3/edge-tts）
4. 热词唤醒：支持唤醒词激活语音输入
"""

import re
import time
import logging
import threading
import subprocess
import tempfile
import os
from collections import OrderedDict

from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

logger = logging.getLogger(__name__)

SPEECH_REC_AVAILABLE = False
WHISPER_AVAILABLE = False
PYTTSX3_AVAILABLE = False
EDGE_TTS_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_REC_AVAILABLE = True
except ImportError:
    pass

try:
    import importlib.util
    WHISPER_AVAILABLE = importlib.util.find_spec("whisper") is not None
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    pass

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    pass

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class VoiceInput:
    """语音输入识别"""

    ENGINES = ['google', 'sphinx', 'whisper']

    def __init__(self, engine='google', language='zh-CN', use_sdk_asr=True):
        self.engine_name = None
        self.language = language
        self.recognizer = None
        self.microphone = None
        self._sd_device_index = None
        self._sd_sample_rate = None
        self._use_pyaudio = False
        self._pyaudio_channels = 1
        self.whisper_model = None
        self.available = False
        self.use_sdk_asr = use_sdk_asr
        self.sdk = None
        self.sdk_available = False
        # 录音静音检测阈值(统一来源,recognizer 为 None 时也能用)
        self._energy_threshold = 300
        self._pause_threshold = 0.8

        if self.use_sdk_asr:
            try:
                self.sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
                if self.sdk.check_server():
                    self.sdk_available = True
                    logger.info("SDK ASR 服务已连接")
                else:
                    logger.warning("SDK ASR 服务不可用，将回退到本地引擎")
            except Exception as e:
                logger.warning(f"SDK ASR 初始化失败: {e}")

        if SPEECH_REC_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = self._energy_threshold
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = self._pause_threshold
            self._init_microphone()
        elif self.sdk_available:
            # speech_recognition 不可用但 SDK ASR 可用:仍可录音(用 pyaudio/sounddevice)
            logger.info("speech_recognition 不可用,SDK ASR 可用,启用语音输入(仅服务端识别)")
            self._init_microphone()

        self._init_engine(engine)

        # SDK ASR 可用时强制启用语音输入(即使本地引擎不可用)
        if self.sdk_available and not self.available:
            self.available = True
            if not self.engine_name:
                self.engine_name = 'sdk'
            logger.info("语音输入已启用(服务端 ASR 优先,本地引擎回退)")

    def _init_microphone(self):
        try:
            import pyaudiowpatch as pyaudio
            p = pyaudio.PyAudio()

            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    name = info.get('name', '')
                    is_loopback = 'loopback' in name.lower()
                    sr_rate = int(info['defaultSampleRate'])
                    try:
                        stream = p.open(
                            format=pyaudio.paInt16,
                            channels=min(1, info['maxInputChannels']),
                            rate=sr_rate,
                            input=True,
                            input_device_index=i,
                            frames_per_buffer=1024,
                        )
                        data = stream.read(int(0.5 * sr_rate), exception_on_overflow=False)
                        stream.stop_stream()
                        stream.close()
                        import numpy as np
                        arr = np.frombuffer(data, dtype=np.int16)
                        if np.max(np.abs(arr)) == 0 and not is_loopback:
                            logger.warning(f"设备 [{i}] {name} 录音数据为空")
                            continue
                        self._sd_device_index = i
                        self._sd_sample_rate = sr_rate
                        self._use_pyaudio = True
                        self._pyaudio_channels = min(1, info['maxInputChannels'])
                        self.microphone = True
                        mode = "系统音频回录" if is_loopback else "麦克风"
                        logger.info(f"音频输入初始化成功: [{i}] {name} ({mode}, sr={sr_rate})")
                        p.terminate()
                        return
                    except Exception as e:
                        logger.warning(f"设备 [{i}] {name} 测试失败: {e}")
                        continue

            p.terminate()
            logger.warning("未找到可用的音频输入设备（请在Windows声音设置中确认麦克风已启用）")
        except ImportError:
            self._try_sounddevice_fallback()
        except Exception as e:
            logger.warning(f"音频输入初始化失败: {e}")

    def _try_sounddevice_fallback(self):
        try:
            import sounddevice as sd
            import numpy as np
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    sr_rate = int(dev['default_samplerate'])
                    try:
                        recording = sd.rec(int(0.5 * sr_rate), samplerate=sr_rate, channels=1, device=i, dtype='int16')
                        sd.wait()
                        if np.max(np.abs(recording)) == 0:
                            continue
                        self._sd_device_index = i
                        self._sd_sample_rate = sr_rate
                        self._use_pyaudio = False
                        self._pyaudio_channels = 1
                        self.microphone = True
                        logger.info(f"音频输入初始化成功: [{i}] {dev['name']} (sr={sr_rate})")
                        return
                    except Exception:
                        continue
            logger.warning("未找到可用的音频输入设备")
        except Exception as e:
            logger.warning(f"sounddevice 回退也失败: {e}")

    def _test_microphone(self, mic):
        pass

    def _init_engine(self, preferred_engine=None):
        engines_to_try = [preferred_engine] if preferred_engine else self.ENGINES
        for eng in engines_to_try:
            if eng is None:
                continue
            try:
                if eng == 'google' and SPEECH_REC_AVAILABLE:
                    self.engine_name = 'google'
                    self.available = True
                    logger.info(f"语音识别引擎: Google Speech Recognition")
                    return
                elif eng == 'sphinx' and SPEECH_REC_AVAILABLE:
                    self.engine_name = 'sphinx'
                    self.available = True
                    logger.info(f"语音识别引擎: Sphinx (离线)")
                    return
                elif eng == 'whisper' and WHISPER_AVAILABLE:
                    import whisper as _whisper
                    self.whisper_model = _whisper.load_model("base")
                    self.engine_name = 'whisper'
                    self.available = True
                    logger.info(f"语音识别引擎: Whisper (离线)")
                    return
            except Exception as e:
                logger.debug(f"语音引擎 {eng} 初始化失败: {e}")
                continue

        logger.warning("所有语音识别引擎均不可用")

    def listen(self, timeout=5, phrase_time_limit=10):
        """
        监听并识别语音

        Returns:
            str: 识别出的文字，失败返回空字符串
        """
        if not self.available or not self.microphone:
            return ''

        try:
            audio = self._record_audio(timeout=timeout, phrase_time_limit=phrase_time_limit)
            if audio is None:
                return ''
            return self._recognize(audio)

        except sr.WaitTimeoutError:
            return ''
        except sr.UnknownValueError:
            return ''
        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return ''

    def _record_audio(self, timeout=5, phrase_time_limit=10):
        import audioop
        import time

        device_index = self._sd_device_index
        sample_rate = self._sd_sample_rate
        chunk_size = 1024

        if self._use_pyaudio:
            return self._record_audio_pyaudio(device_index, sample_rate, chunk_size, timeout, phrase_time_limit)
        else:
            return self._record_audio_sounddevice(device_index, sample_rate, chunk_size, timeout, phrase_time_limit)

    def _record_audio_pyaudio(self, device_index, sample_rate, chunk_size, timeout, phrase_time_limit):
        import pyaudiowpatch as pyaudio
        import audioop
        import time

        p = pyaudio.PyAudio()
        stream = None
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=self._pyaudio_channels,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=chunk_size,
            )

            frames = bytearray()
            started = False
            start_time = time.time()
            silence_start = None

            while True:
                try:
                    data = stream.read(chunk_size, exception_on_overflow=False)
                except Exception:
                    break

                if self._pyaudio_channels > 1:
                    import numpy as np
                    arr = np.frombuffer(data, dtype=np.int16).reshape(-1, self._pyaudio_channels)
                    data = arr[:, 0].tobytes()

                frames.extend(data)
                energy = audioop.rms(data, 2)

                now = time.time()
                elapsed = now - start_time

                if energy > self._energy_threshold:
                    if not started:
                        started = True
                    silence_start = None
                else:
                    if started and silence_start is None:
                        silence_start = now

                if not started and elapsed > timeout:
                    raise sr.WaitTimeoutError()

                if started and silence_start and (now - silence_start) > self._pause_threshold:
                    break

                if phrase_time_limit and started and elapsed > phrase_time_limit:
                    break

            frame_data = bytes(frames)
            return sr.AudioData(frame_data, sample_rate, 2)

        except sr.WaitTimeoutError:
            raise
        except Exception as e:
            logger.error(f"录音失败: {e}")
            return None
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            try:
                p.terminate()
            except Exception:
                pass

    def _record_audio_sounddevice(self, device_index, sample_rate, chunk_size, timeout, phrase_time_limit):
        import sounddevice as sd
        import audioop
        import time
        import queue

        audio_queue = queue.Queue()

        def audio_callback(indata, frames, time_info, status):
            audio_queue.put(indata.copy())

        stream = None
        try:
            stream = sd.InputStream(
                callback=audio_callback,
                device=device_index,
                channels=1,
                samplerate=sample_rate,
                dtype='int16',
                blocksize=chunk_size,
            )
            stream.start()

            frames = bytearray()
            started = False
            start_time = time.time()
            silence_start = None

            while True:
                try:
                    chunk = audio_queue.get(timeout=max(timeout, 1))
                    buf = chunk.tobytes()
                except queue.Empty:
                    now = time.time()
                    if not started and (now - start_time) > timeout:
                        raise sr.WaitTimeoutError()
                    continue

                frames.extend(buf)
                energy = audioop.rms(buf, 2)

                now = time.time()
                elapsed = now - start_time

                if energy > self._energy_threshold:
                    if not started:
                        started = True
                    silence_start = None
                else:
                    if started and silence_start is None:
                        silence_start = now

                if not started and elapsed > timeout:
                    raise sr.WaitTimeoutError()

                if started and silence_start and (now - silence_start) > self._pause_threshold:
                    break

                if phrase_time_limit and started and elapsed > phrase_time_limit:
                    break

            frame_data = bytes(frames)
            return sr.AudioData(frame_data, sample_rate, 2)

        except sr.WaitTimeoutError:
            raise
        except Exception as e:
            logger.error(f"录音失败: {e}")
            return None
        finally:
            if stream is not None:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass

    def recognize_from_file(self, audio_path):
        """从音频文件识别(优先用服务端 ASR)

        Args:
            audio_path: 音频文件路径(wav)

        Returns:
            str: 识别出的文字,失败返回空字符串
        """
        if not self.available:
            return ''

        try:
            # 优先用 SDK ASR 服务(直接传文件路径,无需转 AudioData)
            if self.use_sdk_asr and self.sdk_available:
                text = self.sdk.asr_transcribe(audio_path, hotwords=SDK_CONFIG['asr']['hotwords'])
                if text:
                    return text.strip()
                logger.warning("SDK ASR 文件识别失败,回退到本地引擎")

            # 回退:本地引擎
            if self.engine_name == 'whisper' and self.whisper_model:
                result = self.whisper_model.transcribe(audio_path, language='zh')
                return result.get('text', '').strip()

            if self.recognizer is not None:
                with sr.AudioFile(audio_path) as source:
                    audio = self.recognizer.record(source)
                    return self._recognize(audio)
        except Exception as e:
            logger.error(f"文件识别失败: {e}")
            return ''
        return ''

    def _transcribe_with_sdk(self, audio_data):
        """使用SDK ASR服务进行语音识别"""
        import tempfile
        import os
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_path = f.name
            with open(temp_path, 'wb') as f:
                f.write(audio_data.get_wav_data())
            text = self.sdk.asr_transcribe(temp_path, hotwords=SDK_CONFIG['asr']['hotwords'])
            return text.strip() if text else ''
        except Exception as e:
            logger.error(f"SDK ASR 识别失败: {e}")
            return ''
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    def _recognize(self, audio):
        """调用识别引擎"""
        if self.use_sdk_asr and self.sdk_available:
            text = self._transcribe_with_sdk(audio)
            if text:
                return text
            logger.warning("SDK ASR 识别失败，回退到本地引擎")

        try:
            if self.engine_name == 'google':
                text = self.recognizer.recognize_google(audio, language=self.language)
                return text.strip()
            elif self.engine_name == 'sphinx':
                text = self.recognizer.recognize_sphinx(audio, language='zh-CN')
                return text.strip()
            elif self.engine_name == 'whisper':
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    wav_path = f.name
                with open(wav_path, 'wb') as f:
                    f.write(audio.get_wav_data())
                result = self.whisper_model.transcribe(wav_path, language='zh')
                os.unlink(wav_path)
                return result.get('text', '').strip()
        except sr.UnknownValueError:
            return ''
        except sr.RequestError as e:
            logger.error(f"语音服务请求失败: {e}")
            return ''
        except Exception as e:
            logger.error(f"识别异常: {e}")
            return ''
        return ''


class VoiceOutput:
    """语音输出（TTS）"""

    ENGINES = ['edge_tts', 'pyttsx3']

    def __init__(self, engine='auto', voice=None, rate=180, device='AUTO'):
        self.engine_name = None
        self.pyttsx3_engine = None
        self.voice = voice
        self.rate = rate
        self.available = False
        self._speaking = False
        self._speech_queue = []
        self._lock = threading.Lock()
        self.device = device
        self._init_engine(engine)

        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception:
                pass

    def _init_engine(self, preferred_engine=None):
        engines_to_try = [preferred_engine] if preferred_engine and preferred_engine != 'auto' else self.ENGINES
        for eng in engines_to_try:
            if eng is None:
                continue
            try:
                if eng == 'edge_tts' and EDGE_TTS_AVAILABLE:
                    self.engine_name = 'edge_tts'
                    self.available = True
                    logger.info("语音输出引擎: Edge TTS")
                    return
                elif eng == 'pyttsx3' and PYTTSX3_AVAILABLE:
                    self.pyttsx3_engine = pyttsx3.init()
                    self.pyttsx3_engine.setProperty('rate', self.rate)
                    voices = self.pyttsx3_engine.getProperty('voices')
                    for v in voices:
                        if 'chinese' in v.name.lower() or 'zh' in v.id.lower():
                            self.pyttsx3_engine.setProperty('voice', v.id)
                            break
                    self.engine_name = 'pyttsx3'
                    self.available = True
                    logger.info("语音输出引擎: pyttsx3")
                    return
            except Exception as e:
                logger.debug(f"TTS引擎 {eng} 初始化失败: {e}")
                continue

        logger.warning("所有TTS引擎均不可用")

    def speak(self, text, blocking=False):
        """
        语音播报

        Args:
            text: 要播报的文字
            blocking: 是否阻塞等待播报完成
        """
        if not self.available or not text:
            return

        if blocking:
            self._speak_internal(text)
        else:
            t = threading.Thread(target=self._speak_internal, args=(text,), daemon=True)
            t.start()

    def _speak_internal(self, text):
        """内部播报实现"""
        with self._lock:
            self._speaking = True
        try:
            if self.engine_name == 'edge_tts':
                self._speak_edge_tts(text)
            elif self.engine_name == 'pyttsx3':
                self._speak_pyttsx3(text)
        except Exception as e:
            logger.error(f"语音播报失败: {e}")
        finally:
            with self._lock:
                self._speaking = False

    def _speak_edge_tts(self, text):
        """使用Edge TTS播报(微软在线 TTS,音质好,需联网)

        在子线程中调用,用 asyncio.run 创建新事件循环。
        """
        import asyncio
        import tempfile
        import os

        async def _async_speak():
            voice = self.voice or 'zh-CN-XiaoxiaoNeural'
            communicate = edge_tts.Communicate(text, voice)
            # 用进程ID+时间戳避免并发冲突
            tmp_path = os.path.join(
                tempfile.gettempdir(),
                f'game_tts_{os.getpid()}_{int(time.time() * 1000)}.mp3'
            )
            await communicate.save(tmp_path)
            return tmp_path

        tmp_path = None
        try:
            # 子线程里没有运行中的事件循环,直接 asyncio.run
            # 加 30 秒超时防止网络卡死阻塞 TTS 线程
            tmp_path = asyncio.run(asyncio.wait_for(_async_speak(), timeout=30))
            logger.info(f"[EdgeTTS] 合成完成: {os.path.basename(tmp_path)}, {len(text)} 字")
        except asyncio.TimeoutError:
            logger.error("[EdgeTTS] 合成超时 (30s)")
            return
        except Exception as e:
            logger.error(f"[EdgeTTS] 合成失败: {e}", exc_info=True)
            return

        if tmp_path and os.path.isfile(tmp_path):
            self._play_audio_file(tmp_path)
        else:
            logger.error("[EdgeTTS] 合成完成但文件不存在")

    def _speak_pyttsx3(self, text):
        """使用pyttsx3播报"""
        if self.pyttsx3_engine:
            self.pyttsx3_engine.say(text)
            self.pyttsx3_engine.runAndWait()

    def _play_audio_file(self, filepath):
        """播放音频文件(支持 wav/mp3)

        优先用 pygame(支持 mp3),其次用 Windows Media Player(支持 mp3),
        最后用 PowerShell SoundPlayer(仅 wav)。
        WMP 通过文件时长估算等待时间,避免 playState 轮询死循环。
        """
        import os
        if not os.path.exists(filepath):
            return

        try:
            if PYGAME_AVAILABLE:
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                pygame.mixer.music.unload()
            else:
                ext = os.path.splitext(filepath)[1].lower()
                if ext == '.mp3':
                    # 用 Windows Media Player 播放 mp3(无依赖)
                    # 通过 WMP COM 获取时长,估算等待,避免 playState 死循环
                    import subprocess
                    # 转义路径中的单引号(PowerShell)
                    ps_path = filepath.replace("'", "''")
                    ps_cmd = (
                        f'$p = New-Object -ComObject WMPlayer.OCX; '
                        f'$p.settings.autoStart = $true; '
                        f'$p.URL = "{ps_path}"; '
                        f'Start-Sleep -Milliseconds 500; '
                        f'$dur = 10; '
                        f'try {{ $dur = [math]::Ceiling($p.currentMedia.duration) + 1 }} catch {{}}; '
                        f'Start-Sleep -Seconds $dur; '
                        f'$p.close()'
                    )
                    subprocess.run(
                        ['powershell', '-c', ps_cmd],
                        creationflags=0x08000000,
                        timeout=60,
                    )
                else:
                    # wav 用 SoundPlayer
                    import subprocess
                    subprocess.Popen(
                        ['powershell', '-c', f'(New-Object Media.SoundPlayer "{filepath}").PlaySync()'],
                        creationflags=0x08000000,
                    ).wait()
        except Exception as e:
            logger.error(f"音频播放失败: {e}")
        finally:
            try:
                os.unlink(filepath)
            except Exception:
                pass

    @property
    def is_speaking(self):
        with self._lock:
            return self._speaking

    def stop(self):
        """停止播报"""
        if self.engine_name == 'pyttsx3' and self.pyttsx3_engine:
            self.pyttsx3_engine.stop()
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass


class IntentRecognizer:
    """意图识别 - 解析玩家语音为搜索意图"""

    INTENT_PATTERNS = OrderedDict([
        ('skill_search', [
            r'(.+?)(?:技能|天赋|加点)',
            r'(.+?)(?:怎么加点|技能搭配|天赋树)',
            r'(.+?)(?:升级|开荒|练级).{0,4}(?:攻略|推荐|路线)',
        ]),
        ('build_search', [
            r'(?:查|找|看|搜).{0,4}(.+?)(?:构筑|BD|build|流派)',
            r'(.+?)(?:构筑|BD|build|流派).{0,4}(?:推荐|攻略)',
            r'(.+?)(?:最强|热门|推荐).{0,2}(?:构筑|BD|build|流派)',
            r'(.+?)(?:升级|开荒).{0,4}(?:流派|BD|build)',
        ]),
        ('boss_info', [
            r'怎么打(.+)',
            r'(.+?)怎么打',
            r'(.+?)(?:打法|弱点|技巧)',
            r'(?:查|看|问).{0,2}BOSS.{0,2}(.+)',
            r'(.+?)(?:boss|BOSS|首领|王)',
            r'(.+?)(?:攻略)',
        ]),
        ('equipment_search', [
            r'(?:查|找|看|搜|有没有).{0,4}(.+?)(?:装备|武器|护甲|暗金|传奇|套装)',
            r'(.+?)(?:装备|武器|护甲|暗金|传奇|套装).{0,4}(?:推荐|在哪|怎么得|掉落)',
            r'(?:推荐|最好的).{0,4}(.+?)(?:装备|武器)',
        ]),
        ('quest_guide', [
            r'(?:怎么|如何).{0,4}(?:完成|做|过).{0,4}(.+?)(?:任务|主线|支线)',
            r'(.+?)(?:任务|主线|支线).{0,4}(?:怎么做|攻略|在哪)',
            r'(?:查|看).{0,4}(.+?)(?:任务|剧情)',
        ]),
        ('location_guide', [
            r'(.+?)(?:在哪|在哪里|怎么去|位置)',
            r'(?:怎么去|如何去|去).{0,4}(.+)',
        ]),
        ('general_search', [
            r'(?:查|找|看|搜|帮我|告诉我).{0,4}(.+)',
            r'(.+?)(?:是什么|怎么样|好不好)',
        ]),
    ])

    CATEGORY_KEYWORDS = {
        'boss_info': ['boss', '首领', '王', '打', '攻略', '弱点', '技能'],
        'equipment_search': ['装备', '武器', '护甲', '暗金', '传奇', '套装', '掉落', '推荐'],
        'skill_search': ['技能', '天赋', '加点', '搭配', '天赋树'],
        'build_search': ['构筑', 'bd', 'build', '流派', '最强'],
        'quest_guide': ['任务', '主线', '支线', '剧情', '完成'],
        'location_guide': ['在哪', '哪里', '位置', '怎么去'],
    }

    GAME_CLASS_NAMES = [
        '野蛮人', '法师', '游侠', '死灵法师', '德鲁伊', '盗贼',
        'barbarian', 'sorcerer', 'rogue', 'necromancer', 'druid',
    ]

    def recognize(self, text):
        """
        识别语音意图

        Args:
            text: 语音识别的文字

        Returns:
            dict: {
                'intent': 意图类型,
                'query': 提取的搜索关键词,
                'class_name': 职业名（如果识别到）,
                'raw_text': 原始文字,
            }
        """
        if not text or not text.strip():
            return {'intent': 'none', 'query': '', 'class_name': None, 'raw_text': text}

        text = text.strip()
        class_name = self._extract_class(text)

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    query = match.group(1).strip() if match.groups() else text
                    query = self._clean_query(query)
                    return {
                        'intent': intent,
                        'query': query or text,
                        'class_name': class_name,
                        'raw_text': text,
                    }

        query = self._clean_query(text)
        return {
            'intent': 'general_search',
            'query': query,
            'class_name': class_name,
            'raw_text': text,
        }

    def _extract_class(self, text):
        """提取职业名"""
        for cls_name in self.GAME_CLASS_NAMES:
            if cls_name.lower() in text.lower():
                return cls_name
        return None

    def _clean_query(self, query):
        """清理搜索关键词"""
        query = re.sub(r'[的了吗呢啊呀吧嗯]', '', query)
        query = re.sub(r'\s+', ' ', query).strip()
        filler_words = ['帮我', '请', '我想', '能不能', '可以', '一下', '请问']
        for word in filler_words:
            query = query.replace(word, '')
        return query.strip()

    def get_search_categories(self, intent, class_name=None):
        """
        根据意图返回应搜索的分类

        Args:
            intent: 识别的意图类型
            class_name: 识别到的职业名（如果有）

        Returns:
            list: 要搜索的分类列表，None表示搜索所有分类
        """
        mapping = {
            'boss_info': ['bosses', 'boss_schedule'],
            'equipment_search': ['equipment', 'items'],
            'skill_search': ['skills', 'web_skills', 'build_details'],
            'build_search': ['build_details', 'web_skills', 'skills'],
            'quest_guide': ['quests', 'guides'],
            'location_guide': ['quests', 'guides'],
            'general_search': None,
        }
        categories = mapping.get(intent, None)

        if class_name:
            if intent in ('boss_info', 'general_search'):
                return ['skills', 'build_details', 'web_skills', 'bosses']
            return categories

        return categories


class VoiceAssistant:
    """语音助手 - 整合语音输入/输出/意图识别/数据搜索"""

    def __init__(self, content_indexer=None, stt_engine='google', tts_engine='auto',
                 voice=None, language='zh-CN'):
        self.voice_input = VoiceInput(engine=stt_engine, language=language, use_sdk_asr=SDK_CONFIG['asr']['enabled'])
        self.voice_output = VoiceOutput(engine=tts_engine, voice=voice)
        self.intent_recognizer = IntentRecognizer()
        self.indexer = content_indexer

        self.is_listening = False
        self._listen_thread = None
        self._stop_event = threading.Event()

        self.last_intent = None
        self.last_query = None
        self.last_results = None
        self.last_response_text = None

        self.on_result = None

    def set_indexer(self, indexer):
        """设置内容索引器"""
        self.indexer = indexer

    def process_voice(self, timeout=5, phrase_time_limit=10):
        """
        完整语音交互流程：听 -> 识别意图 -> 搜索 -> 回复

        Returns:
            dict: {
                'text': 识别的文字,
                'intent': 意图,
                'query': 搜索关键词,
                'results': 搜索结果,
                'response': 回复文字,
                'spoken': 是否已语音播报,
            }
        """
        text = self.voice_input.listen(timeout=timeout, phrase_time_limit=phrase_time_limit)
        if not text:
            return {
                'text': '',
                'intent': 'none',
                'query': '',
                'results': [],
                'response': '未识别到语音，请重试',
                'spoken': False,
            }

        return self.process_text(text)

    def process_text(self, text):
        """
        处理文字输入（可用于手动输入或测试）

        Args:
            text: 文字输入

        Returns:
            dict: 处理结果
        """
        intent_result = self.intent_recognizer.recognize(text)
        intent = intent_result['intent']
        query = intent_result['query']
        class_name = intent_result['class_name']

        self.last_intent = intent
        self.last_query = query

        search_query = query
        if class_name:
            search_query = f"{class_name} {query}"

        results = []
        if self.indexer:
            categories = self.intent_recognizer.get_search_categories(intent, class_name)
            results = self.indexer.search(search_query, top_n=5, categories=categories)

        self.last_results = results

        response_text = self._generate_response(intent_result, results)
        self.last_response_text = response_text

        if self.voice_output.available:
            self.voice_output.speak(response_text, blocking=False)

        return {
            'text': text,
            'intent': intent,
            'query': query,
            'class_name': class_name,
            'results': results,
            'response': response_text,
            'spoken': self.voice_output.available,
        }

    def _generate_response(self, intent_result, results):
        """根据意图和搜索结果生成语音回复"""
        intent = intent_result['intent']
        query = intent_result['query']
        raw_text = intent_result['raw_text']

        if not results:
            return f'抱歉，没有找到关于{query}的相关信息。'

        top = results[0]
        category = top['category']
        data = top['data']
        score = top['score']

        if category == 'bosses':
            name = data.get('name', query)
            weakness = data.get('weakness', [])
            guide = data.get('guide', '')
            weak_str = '、'.join(weakness) if weakness else '未知'
            resp = f'{name}的弱点是{weak_str}。'
            if guide:
                resp += f'攻略建议：{guide[:80]}'
            return resp

        elif category in ('equipment', 'items'):
            name = data.get('name', query)
            rarity = data.get('rarity', '')
            desc = data.get('description', data.get('effect', ''))
            resp = f'{name}，{rarity}品质。'
            if desc:
                resp += f'效果：{desc[:60]}'
            return resp

        elif category in ('skills', 'web_skills'):
            name = data.get('name', query)
            cls = data.get('class', data.get('name', ''))
            builds = data.get('builds', {})
            if builds:
                build_list = ['、'.join(skills) for build_name, skills in builds.items()]
                resp = f'{cls}推荐流派：{"；".join(build_list[:2])}'
            else:
                skills = data.get('skills', {})
                if skills:
                    skill_str = '、'.join([s for cat in list(skills.values())[:1] for s in cat[:4]])
                    resp = f'{cls}核心技能：{skill_str}'
                else:
                    resp = f'{cls}'
            return resp

        elif category == 'build_details':
            title = data.get('title', query)
            cls = data.get('class', '')
            skills_list = data.get('skills', [])
            resp = f'推荐构筑：{title}'
            if cls:
                resp += f'（{cls}）'
            if skills_list:
                resp += f'，核心技能：{skills_list[0]}'
            return resp

        elif category == 'quests':
            name = data.get('name', query)
            location = data.get('location', '')
            guide = data.get('guide', '')
            resp = f'任务：{name}'
            if location:
                resp += f'，地点：{location}'
            if guide:
                resp += f'。{guide[:60]}'
            return resp

        elif category == 'guides':
            title = data.get('title', query)
            tags = data.get('tags', [])
            resp = f'攻略：{title}'
            if tags:
                resp += f'，标签：{tags[0]}'
            return resp

        else:
            name = data.get('name', data.get('title', query))
            return f'找到相关信息：{name}'

    def start_continuous_listening(self, wake_word='大菠萝', callback=None,
                                  cooldown=10.0, min_text_length=2):
        """启动持续监听模式（唤醒词激活）

        Args:
            wake_word: 唤醒词，默认 'diablo'。检测到唤醒词后激活语音交互。
            callback: 结果回调函数
            cooldown: 唤醒词触发后的冷却时间（秒），避免频繁误激活
            min_text_length: 识别文本最小长度，短于此长度视为噪声丢弃
        """
        if self.is_listening:
            return

        self.is_listening = True
        self._stop_event.clear()
        self.on_result = callback
        self._wake_word = wake_word

        # 唤醒词匹配容错: 用中文"大菠萝"(暗黑玩家常用昵称),中文ASR识别中文远比英文稳。
        # 收集常见谐音变体(应对ASR小误差),命中任一即视为唤醒。
        # 实测STT把"大菠萝"听成过"阿波罗",故补两字核心变体(波罗/波萝/菠萝/波楼等)。
        _wake_variants = [w.lower() for w in [
            wake_word, '大菠萝', '大波萝', '大波罗', '大菠罗', '打菠萝',
            '打波萝', '大伯罗', '大播罗', '阿波罗', '啊波罗', '波罗蜜',
            '菠萝', '波萝', '波罗', '菠罗', '播罗', '波楼', '波露',
        ] if w]

        def _hit_wake(t_lower):
            return any(v in t_lower for v in _wake_variants)

        def _listen_loop():
            logger.info(f"持续监听已启动 (唤醒词='{wake_word}', 冷却={cooldown}s, 变体={_wake_variants})")
            last_trigger_time = 0.0
            while not self._stop_event.is_set():
                try:
                    text = self.voice_input.listen(timeout=3, phrase_time_limit=8)
                    if not text:
                        continue

                    # 噪声过滤:文本太短视为噪声
                    text = text.strip()
                    # 诊断: 打印每次识别到的原始文字(定位"没唤醒"是否因STT识别成了别的词)
                    logger.info(f"[唤醒监听] STT识别: '{text}'")
                    if len(text) < min_text_length:
                        continue

                    # 唤醒词检测(带谐音容错)
                    if wake_word:
                        if not _hit_wake(text.lower()):
                            logger.debug(f"[唤醒监听] 未含唤醒词,忽略: '{text}'")
                            continue
                        logger.info(f"[唤醒监听] ✓ 命中唤醒词 → '{text}'")
                        # 冷却时间检查(避免频繁误激活)
                        now = time.time()
                        if now - last_trigger_time < cooldown:
                            logger.debug(f"唤醒词冷却中,跳过 (距上次 {now-last_trigger_time:.1f}s)")
                            continue
                        last_trigger_time = now
                        # 去除唤醒词及其谐音变体,提取实际指令
                        for _v in _wake_variants:
                            text = re.sub(re.escape(_v), '', text, flags=re.IGNORECASE)
                        text = text.strip(' ,，。.、?？!！')
                        logger.info(f"[唤醒监听] 去唤醒词后指令: '{text}'")

                    if not text:
                        # 只说了唤醒词,没有指令 → 待命响应
                        logger.info("[唤醒监听] 无指令,待命响应")
                        result = {
                            'text': wake_word,
                            'intent': 'wake',
                            'query': '',
                            'response': '我在听,请说指令',
                            'spoken': True,
                        }
                        if self.voice_output.available:
                            self.voice_output.speak(result['response'], blocking=False)
                    else:
                        logger.info(f"[唤醒监听] 调用process_text: '{text}'")
                        result = self.process_text(text)
                        logger.info(f"[唤醒监听] process_text完成: intent={result.get('intent')} query={result.get('query')}")

                    if self.on_result:
                        logger.info("[唤醒监听] 调用 on_result 回调")
                        try:
                            self.on_result(result)
                            logger.info("[唤醒监听] on_result 回调完成")
                        except Exception as cbe:
                            logger.error(f"[唤醒监听] on_result 回调异常: {cbe}", exc_info=True)

                except Exception as e:
                    logger.error(f"监听异常: {e}", exc_info=True)
                    time.sleep(1)

            self.is_listening = False
            logger.info("持续监听已停止")

        self._listen_thread = threading.Thread(target=_listen_loop, daemon=True)
        self._listen_thread.start()

    def stop_listening(self):
        """停止持续监听"""
        self._stop_event.set()
        if self._listen_thread:
            self._listen_thread.join(timeout=5)
        self.is_listening = False

    def get_status(self):
        """获取语音助手状态"""
        return {
            'stt_available': self.voice_input.available,
            'stt_engine': self.voice_input.engine_name or 'none',
            'sdk_asr_available': self.voice_input.sdk_available,
            'tts_available': self.voice_output.available,
            'tts_engine': self.voice_output.engine_name or 'none',
            'is_listening': self.is_listening,
            'is_speaking': self.voice_output.is_speaking,
            'last_query': self.last_query,
            'last_intent': self.last_intent,
        }
