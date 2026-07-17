import unittest

import cv2
import numpy as np

from class_icon_detector import crop_skill_bar, detect_skill_bar_slots, split_skill_bar_icons


class TestSkillBarDetection(unittest.TestCase):
    def test_crop_skill_bar_uses_centered_bottom_region(self):
        frame = np.zeros((1000, 2000, 3), dtype=np.uint8)
        cropped = crop_skill_bar(frame)
        self.assertEqual((220, 1000, 3), cropped.shape)

    def test_detects_real_square_slots(self):
        skill_bar = np.zeros((220, 1000, 3), dtype=np.uint8)
        for index in range(6):
            left = 260 + index * 78
            cv2.rectangle(skill_bar, (left, 105), (left + 58, 163), (220, 220, 220), 3)
            cv2.circle(skill_bar, (left + 29, 134), 12, (80 + index * 20,) * 3, -1)

        slots = detect_skill_bar_slots(skill_bar)
        icons = split_skill_bar_icons(skill_bar)

        self.assertEqual(6, len(slots))
        self.assertEqual(6, len(icons))
        self.assertTrue(all(abs(icon.shape[0] - icon.shape[1]) <= 3 for icon in icons))

    def test_does_not_equal_split_unrelated_content(self):
        skill_bar = np.random.default_rng(7).integers(0, 255, (220, 1000, 3), dtype=np.uint8)
        self.assertEqual([], split_skill_bar_icons(skill_bar))


if __name__ == '__main__':
    unittest.main()
