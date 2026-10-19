# Project guide

This is the existing PyQt5 desktop pet, reskinned to Chiikawa. Do not replace it with a demo or restore retired chat/legacy-character fallbacks.

- desktop_pet.py: native transparent/topmost pet, drag, bounded walk, message queue and state transition painting.
- care.py: local Windows idle-time sampling and care clock; ten default messages and non-activating bubble.
- schedule.py: separate greeting and appearance schedules, validated local config, backups and persisted greeting deduplication.
- settings_ui.py: native resizable settings tabs and development-only time preview.
- theme.py, pet_menu.py: shared resource identity and visual styling.
- assets/chiikawa/processed/: runtime art only; no legacy-character resource fallback.
- tools/prepare_assets.py: deterministic documented crops and masks. Original photos remain untouched.
- tests/: scheduling and native Qt integration tests with isolated configuration files.

Run tests with python -m unittest discover -s tests -v. Build with build.ps1. See docs/chiikawa/验收报告.md for feature inventory, asset mappings and verification limitations. Files under docs/superpowers/ are the original historical plans, not the current architecture.

- body_animation.py plays pre-baked true-alpha atlases with a two-atlas LRU cache. Keep body playback independent of whole-pet transforms.
- tools/author_body_animation.py and animation_sources/*/rig.json are editable continuous-mesh authoring sources; see docs/body-animation/交付报告.md.
