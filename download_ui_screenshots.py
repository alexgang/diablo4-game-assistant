#!/usr/bin/env python3
"""
从 Blizzard 官方下载 Diablo 4 各类场景的截图

包含：装备/技能/地图/世界 等 UI 界面
"""

import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'game_screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Season 4 Loot Reborn - 包含装备/物品相关UI
SCREENSHOTS = [
    # 装备/物品栏 UI
    ("Diablo4_S4_Inventory_Itemization_Before", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfQITUHmRCDE3ka%2bzA2tHCYEOodAZcp5OhL9e%2bDXqoYFvKKf0%2fx59ABl3BE%2f%2fqlRPsZseN7tkZyaGJOaWn8uuajJvP9xApYmDv3X%2b8tRw0tBAOJtDBAaLkCcPEanUikgqR0dqXT7PpUtpbJXf%2ftiyBAHu1i09mbg15mzkuS985W%2bl72BvyZ5N2mewwxl7D52iy14fGqV5vtB7B74n586mfqwE6a73csvdwH0ZWFKrqGv17oa28pAyaIMvmetF1iCtf69lIgOV2GyPMGC%2fACDHo%2fwB5tvqfwwmVXt6Gg0j0UZOz0iI4MK9FWCY1ZivOsD9lpPnUtxg87h%2f4C%2fafNvw3mIkg0XgbtE6IBLeykjlwAjKtX6OmREHdZvt26DAtn2HTBO7rWaugKx86iknPnTbQG85h05J8fEGw8zL9Tkp2sKMevYJGrO0i%2fKyA0IHJ%2f3XRsRnb3fTc%2bZ1b3pqR3NtkUE%3d"),
    ("Diablo4_S4_Inventory_Itemization_After", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfQITUHmRCDE3ka%2bzA2tHCYEOodAZcp5OhL9e%2bDXqoYFvKKf0%2fx59ABl3BE%2f%2fqlRPsfTKTfXZ3u6OM%2fN1OMWU7YfBCN%2bY5Ra6wr5IrS18yGtjIvA7m%2fwYhqKbVD7Cn1EDFkItk67kXx173p1msZ1V0yJrm%2bKbtOC%2bO0JNrH7zBJwbLOqmK9rRHlJDrpWRnPkV3vWoPGGuB8xsSR8Gtm4fYrhNNeTyz4fVsW3Ld%2bluq6m9SBsvI9YwHxbQPV%2f%2fWhQ4Ltgbd5NU3SjaMvW4oCFSBXo%2b76WNA3OghgbEGFWT9qdzL5LgsQmtAW01iqgI9R%2b0B6KfKgbTk0jkui6rmubx9kB3CKtxBBGvp%2bp1tVrHtCmq0Pqb67in3jUveGC64KxgMKPoK6zI4Nl6GEcSyduMKn%2f0HUQizeyvF3h659fVtSAkk%2bkblb3nt6SL0dIOByvBYhl8Vso0CFVIRpQB89FmYiU%3d"),
    # 技能 UI
    ("Diablo4_S4_Skill_Tree_01", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfQITUHmRCDE3ka%2bzA2tHCYEOodAZcp5OhL9e%2bDXqoYFvwWytJJjInqTXY6BfTUCIxSkLkpo38Tzm312nFvCzitp97ohMRjiRxDLBch3poz1kDeds0PdEn1xz3Jn7jkT%2f%2fDzafeNhl0E%2fdrGi2QheySHUoWFJFF5lpOw15iXeM3a5PwuNFJAicpBfGIv6Y3rz%2bXmO60ocT7qVmq0alI1u8ecasD7WWtBMu3%2fAax108PKyxYe8FYrVrVuEGtFrllQYWF51iS0UJiSLRhnjnjg7oqB01blBhUwM4xFSZ%2fLw04gj6rVAOHjv%2fYUBEp37Cbvl31GiypXORCCyLsHAyTyZnVLodU3LOzT4zLaMkGzPgkFQBaGSnYdnoKJtYEF0rk52Vh78UmC%2fgerHpoxdKoAzD7eTTObGbgiFpSYfQfJSwI7fJ1vKMw7dn8%2bpeghl0cZWNQ%3d"),
    # Code of Power - 装备词条
    ("Diablo4_S4_Codex_of_Power", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfQITUHmRCDE3ka%2bzA2tHCYEOodAZcp5OhL9e%2bDXqoYFvKKf0%2fx59ABl3BE%2f%2fqlRPsRsZUwsVwqeKca4uyPO5V5vIQY8oUEmvYRmWhMeif0mnqOeds3omTeawntQ8mOMJ%2b9c6J%2b4ZZq0861Y3d1XpxTKYamRuNr7wlsmgJmZUSaDoHk%2bffeVkAHs7WpXSLawSqY5L3%2b%2bFqXkecE1KQpoUj3TpZsOZWvizgEwq62D4Ewe1aM3Pnw%2fuBSJKqJrq2wSSCq1hnbFJGRSGhCVrMKfE61Rz1gFht7lV1w%2bpticvosJvEMM8tTlg3cPHP1rC46qk88kURwT%2bTl0RdbHMdzk5i56ZExVNH8rdQZ8vvVSbZAG6g5YM5jQkmckw7EVOfiTNeny9rhGioe91w9mteSY9n4EChQLmVcmc3jrvs%2fV0tR92D2q1YYVLj1FuRiA%2fOPJbP9X1skstWa7ajFHzeX0nRfwh8wQ8d2Ae9y9%2faXpEZ9R0"),
    # Tempering 装备强化
    ("Diablo4_S4_Tempering", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfQITUHmRCDE3ka%2bzA2tHCYEOodAZcp5OhL9e%2bDXqoYFvKKf0%2fx59ABl3BE%2f%2fqlRPseUhVlDM4%2btVDgMoBjSI1MJQGOuYEoshh4XBVBk%2fGdmMcmLW7XNHmySA1P6GC07JNlTaapSHh02O0yjSWBlR%2fMv9G13cgAoFhRKl4EmXCA6fXwmv6WBG89bAIdoSg793ADXlEU7EX0ZNApIPkSEr7Url3hnc6w0mY53DHTk0w%2fEq%2bls%2fAH9LSCrwcxOTYG5QVFLipWBRZYkPNPhYi4VkOOIQDHEe85JRm2WD%2fau%2bJcmf2HXOG7d9QlDsGszrvrHeAYb2Gkk8yk1lebsdRPooAoZnxwwfs4emfs%2bl4fTSc%2b8PZbDPU7NuLWr3yi15aHFQwHs5qb1wezAkt%2byKLzaaaif30AaZB3JcyKw8qypOoBxzjVBrT%2fsXO5NYhFXWAOmBYPMM9nU8h2gY84n6QZCs3Rc%3d"),
    # Masterworking 装备精工
    ("Diablo4_S4_Masterworking", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfQITUHmRCDE3ka%2bzA2tHCYEOodAZcp5OhL9e%2bDXqoYFvKKf0%2fx59ABl3BE%2f%2fqlRPsV%2fXZC%2fJKY9y7hGVhDxuBgQeR3vkxX1jMYQZupMM%2fBisGM1OMsjlDIySRLqzbr9oJ4vtpz4s8weRUWrecjB%2bkK2LTy0A2ln1xDtvoYTanFH4Rp%2fnrZEWYw9iznMdO6uH%2bEHhyczHXGZVdHGPwuLKljXcOFvisImuBVyhyPsXttuluGrVwmxwSUGyAngJaCB00qYDdBp%2fDpvRDChHeypx5b%2f0bzmz2TgMUuN63y5Nk%2b8Xg2FggjwBfSGTDN03GaPGJKGqect%2f0wQneXZQwuK9HPpZ4fQkqYNyj%2bQQ6tv4jWBOXHdznwTpfLktWOEPI%2boR0MzK%2f0zdXgJR9N1ekZbHqaP0vz0wC4Ehx7QpVBIyfyiF2kgpb%2fCpMERexyPT%2b5LVV%2fw7GRwymTk09EkI8Cy1sxA%3d"),
    # Helltide Gameplay
    ("Diablo4_S4_Helltide_Gameplay_001", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfQITUHmRCDE3ka%2bzA2tHCYEOodAZcp5OhL9e%2bDXqoYFvUptWpswnVsOyWvSHeP57upxlEABCW11CVnj4QvcjLZeEBviZsrQip05O3%2fxHizNdb8NtDHAOeuD41I1UrKSxImV9Tsq7apMUCiV9lqvQyT5f4UZJMDqp1yVORzCb8eiVgY0hGqK8tuwDHsrMBjpNyXEIxV1l1QeFZTgEq9seS2O%2f6Z5rt68sRZsjLI7cBmVcidXdBzLqskADXcBWB105G%2bBeVncpSpowMZDiw%2biCGFxK3MUrCwt4DxGOwGUHwCrPr%2fMMhmDTgT4fz1PZYgzNYtN4h3nN8E81YFgwVaWgpbdU8EXrT8jdz%2bs7r9A7WXItv9WXqUx8NlL0L%2fcAFrW91Xo%2b9kmCPEjskZR7ygEgTpQMGzXkWrPeK%2fk3WYhS%2bG8O9ECvvyV01ItlDtJGDLEqpO2dt%2bTwj1wDvhA28JX%2fwg9thg1LcoA1ibs8oKmp1Rk8"),
    ("Diablo4_S4_Helltide_Gameplay_002", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfQITUHmRCDE3ka%2bzA2tHCYEOodAZcp5OhL9e%2bDXqoYFvUptWpswnVsOyWvSHeP57upxlEABCW11CVnj4QvcjLZep8FuBvfxNcX8CM51etg83umQM%2fXp4ZhAPLuW7mjb2TByUhIn9lAc4J3QMDjlayPDUHCPqgbWnzrTxz%2bN02keRJukdcpj6g0bRLBa9RDkxGPMJm8gDu%2b2m5QUcDraJn7XRNck%2f0mqY8E5lOMU3hnPcyxhfm1tKa3bn6z3fG7i4U%2fBvc73WE%2bHip%2bE5Yik9cjt%2b2xBB6DRe60K%2f%2fGhd5jUJWz98U6rezT9ilqD4wp%2bDYLd9QfZSyE0ztre6FDUSPml7m80lCjlAyG99GLYXdwMR0UEFjuxRTzJ66VLlqLXc2dFSUZll7l0%2f8Gb%2fQbF5GU8tRgpREpoFLPYFLIwKaAvWeaNVDfv95YH1bZ3TCFMAlBQxLNPCl5rDckSXPgs9v%2b4%3d"),
]


def download_image(name, url):
    save_path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    if os.path.exists(save_path):
        size = os.path.getsize(save_path) / 1024 / 1024
        if size > 0.5:
            print(f"  已存在: {name}.png ({size:.1f} MB)")
            return True
        else:
            os.remove(save_path)

    print(f"  下载中: {name}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Referer': 'https://blizzard.gamespress.com/',
        }
        response = requests.get(url, headers=headers, timeout=120, allow_redirects=True)
        response.raise_for_status()

        if len(response.content) < 10000:
            print(f"  ✗ 文件太小: {len(response.content)} bytes")
            return False

        with open(save_path, 'wb') as f:
            f.write(response.content)

        size = os.path.getsize(save_path) / 1024 / 1024
        print(f"  ✓ {name}.png ({size:.1f} MB)")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def main():
    print("=" * 60)
    print("Diablo 4 UI 界面截图下载（装备/技能/地图）")
    print("=" * 60)
    print(f"\n目标: {len(SCREENSHOTS)} 张")
    print(f"目录: {SCREENSHOTS_DIR}\n")

    success = 0
    for name, url in SCREENSHOTS:
        if download_image(name, url):
            success += 1

    print(f"\n下载完成: {success}/{len(SCREENSHOTS)}")


if __name__ == "__main__":
    main()
