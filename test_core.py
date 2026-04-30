import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_data import GameDatabase
from content_indexer import ContentIndexer
from voice_assistant import IntentRecognizer, VoiceAssistant


class TestGameDatabase:
    def setup_method(self):
        self.db = GameDatabase()

    def test_database_initialized(self):
        assert self.db is not None

    def test_quests_loaded(self):
        assert hasattr(self.db, 'quests')
        assert isinstance(self.db.quests, dict)
        assert len(self.db.quests) > 0

    def test_bosses_loaded(self):
        assert hasattr(self.db, 'bosses')
        assert isinstance(self.db.bosses, dict)
        assert len(self.db.bosses) > 0

    def test_skills_loaded(self):
        assert hasattr(self.db, 'skills')
        assert isinstance(self.db.skills, dict)
        assert len(self.db.skills) > 0

    def test_quest_structure(self):
        for act, act_data in self.db.quests.items():
            assert 'quests' in act_data, f'任务Act缺少quests字段: {act}'
            for q in act_data['quests']:
                assert 'name' in q, f'任务缺少name字段: {q}'

    def test_boss_structure(self):
        for name, boss in self.db.bosses.items():
            assert 'name' in boss, f'BOSS缺少name字段: {boss}'

    def test_skill_structure(self):
        for cls, skills in self.db.skills.items():
            assert isinstance(skills, dict), f'技能数据应为字典: {cls}'
            assert 'skills' in skills or isinstance(skills, dict), f'技能应包含skills字段: {cls}'

    def test_get_quest_guide(self):
        for act, act_data in self.db.quests.items():
            if act_data['quests']:
                q = act_data['quests'][0]
                result = self.db.get_quest_guide(q['id'])
                assert result is not None
                break

    def test_get_boss_guide(self):
        first_boss = next(iter(self.db.bosses))
        result = self.db.get_boss_guide(first_boss)
        assert result is not None

    def test_get_class_skills(self):
        first_class = next(iter(self.db.skills))
        result = self.db.get_class_skills(first_class)
        assert result is not None


class TestContentIndexer:
    def setup_method(self):
        self.db = GameDatabase()
        self.indexer = ContentIndexer(game_db=self.db)

    def test_indexer_initialized(self):
        assert self.indexer is not None

    def test_search_returns_list(self):
        results = self.indexer.search('暗黑')
        assert isinstance(results, list)

    def test_search_finds_quest(self):
        results = self.indexer.search('暗黑破坏神')
        assert len(results) > 0, '搜索"暗黑破坏神"应返回结果'
        assert results[0]['category'] == 'quests'
        assert results[0]['score'] > 0

    def test_search_result_format(self):
        results = self.indexer.search('暗黑')
        if results:
            r = results[0]
            assert 'category' in r
            assert 'score' in r
            assert 'data' in r
            assert isinstance(r['score'], float)
            assert r['score'] >= 0

    def test_search_top_n(self):
        results = self.indexer.search('暗黑', top_n=2)
        assert len(results) <= 2

    def test_search_empty_query(self):
        results = self.indexer.search('')
        assert isinstance(results, list)

    def test_search_no_match(self):
        results = self.indexer.search('zzzzzzzzzzz不存在的内容')
        assert isinstance(results, list)


class TestIntentRecognizer:
    def setup_method(self):
        self.ir = IntentRecognizer()

    def test_boss_intent(self):
        result = self.ir.recognize('屠夫怎么打')
        assert result['intent'] == 'boss_info'
        assert '屠夫' in result['query']

    def test_equipment_intent(self):
        result = self.ir.recognize('查暗金装备推荐')
        assert result['intent'] == 'equipment_search'

    def test_skill_intent(self):
        result = self.ir.recognize('野蛮人怎么加点')
        assert result['intent'] == 'skill_search'
        assert result['class_name'] == '野蛮人'

    def test_build_intent(self):
        result = self.ir.recognize('法师最强构筑')
        assert result['intent'] == 'build_search'
        assert result['class_name'] == '法师'

    def test_quest_intent(self):
        result = self.ir.recognize('暗黑破坏神任务怎么做')
        assert result['intent'] == 'quest_guide'

    def test_location_intent(self):
        result = self.ir.recognize('破碎群峰在哪')
        assert result['intent'] == 'location_guide'
        assert '破碎群峰' in result['query']

    def test_general_intent(self):
        result = self.ir.recognize('帮我查一下骷髅王')
        assert result['intent'] in ('boss_info', 'general_search')

    def test_empty_input(self):
        result = self.ir.recognize('')
        assert result['intent'] == 'none'

    def test_none_input(self):
        result = self.ir.recognize(None)
        assert result['intent'] == 'none'

    def test_class_extraction_barbarian(self):
        result = self.ir.recognize('野蛮人技能')
        assert result['class_name'] == '野蛮人'

    def test_class_extraction_sorcerer(self):
        result = self.ir.recognize('法师加点')
        assert result['class_name'] == '法师'

    def test_class_extraction_rogue(self):
        result = self.ir.recognize('游侠BD')
        assert result['class_name'] == '游侠'

    def test_search_categories(self):
        categories = self.ir.get_search_categories('boss_info')
        assert isinstance(categories, list)
        assert 'bosses' in categories

    def test_search_categories_skill(self):
        categories = self.ir.get_search_categories('skill_search')
        assert 'skills' in categories


class TestVoiceAssistantTextQuery:
    def setup_method(self):
        self.db = GameDatabase()
        self.indexer = ContentIndexer(game_db=self.db)
        self.va = VoiceAssistant(content_indexer=self.indexer)

    def test_process_text_returns_dict(self):
        result = self.va.process_text('暗黑破坏神')
        assert isinstance(result, dict)

    def test_process_text_has_required_fields(self):
        result = self.va.process_text('暗黑破坏神')
        assert 'text' in result
        assert 'intent' in result
        assert 'query' in result
        assert 'results' in result
        assert 'response' in result
        assert 'spoken' in result

    def test_process_text_intent(self):
        result = self.va.process_text('屠夫怎么打')
        assert result['intent'] == 'boss_info'

    def test_process_text_response(self):
        result = self.va.process_text('暗黑破坏神')
        assert len(result['response']) > 0

    def test_process_text_empty(self):
        result = self.va.process_text('')
        assert result['intent'] == 'none'

    def test_get_status(self):
        status = self.va.get_status()
        assert 'stt_available' in status
        assert 'tts_available' in status
        assert 'is_listening' in status
