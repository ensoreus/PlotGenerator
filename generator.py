import json
from pathlib import Path

import anyio
from dotenv import load_dotenv

load_dotenv()

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)

PROJECT_DIR = Path(__file__).resolve().parent  # папка з CLAUDE.md, AGENT.md і .claude/agents
AGENT_FILE = PROJECT_DIR / "AGENT.md"
TASK_FILE = PROJECT_DIR / "task.txt"

CHARACTERS_RANGE = range(2, 6)  # [2-5]

# Допустимі відповіді користувача -> значення жанру у task.txt
GENRES = {
    "драма": "drama",
    "драматичний": "drama",
    "drama": "drama",
    "романтика": "romantic",
    "романтичний": "romantic",
    "romantic": "romantic",
    "детектив": "detective",
    "детективний": "detective",
    "detective": "detective",
    "християнський": "christian",
    "christian": "christian",
}


def ask_characters_count() -> int | None:
    answer = input("Кількість персонажів [2-5] (Enter — пропустити): ").strip()
    if not answer:
        return None
    if answer.isdigit() and int(answer) in CHARACTERS_RANGE:
        return int(answer)
    print(f"  '{answer}' не входить у [2-5] — агент обере сам.")
    return None


def ask_genre() -> str | None:
    answer = input(
        "Жанр [драма, романтика, детектив, християнський] (Enter — пропустити): "
    ).strip().lower()
    if not answer:
        return None
    if answer in GENRES:
        return GENRES[answer]
    print(f"  '{answer}' — невідомий жанр, агент обере сам.")
    return None


def ask_story() -> str:
    return input("Ідея — про що сюжет (Enter — пропустити): ").strip()


def collect_task() -> dict | None:
    """Опитує користувача. Повертає завдання, якщо хоч одна відповідь валідна."""
    characters_count = ask_characters_count()
    genre = ask_genre()
    story = ask_story()

    if characters_count is None and genre is None and not story:
        return None
    return {
        "characters_count": characters_count,
        "genre": genre,
        "story": story,
    }


def write_task(task: dict | None) -> None:
    if task is None:
        # не лишаємо агентам завдання від попереднього запуску
        TASK_FILE.unlink(missing_ok=True)
        return
    TASK_FILE.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")
    print(f"Завдання записано у {TASK_FILE.name}: {json.dumps(task, ensure_ascii=False)}")


def load_agent(path: Path) -> tuple[dict, str]:
    """Розбирає AGENT.md на frontmatter (name, model, ...) та тіло-інструкцію."""
    text = path.read_text(encoding="utf-8")
    meta: dict = {}
    if text.startswith("---"):
        _, header, text = text.split("---", 2)
        for line in header.strip().splitlines():
            key, sep, value = line.partition(":")
            if sep:
                meta[key.strip()] = value.strip().strip('"')
    return meta, text.strip()


def build_prompt(task: dict | None) -> str:
    task_hint = (
        f"Завдання лежить у `{TASK_FILE.name}`."
        if task
        else "Файлу завдання нема — жанр, кількість персонажів та ідею обери сам."
    )
    return f"Створи новий сюжет-буклет для гри Риторика. {task_hint}\n" \
           "Дій як оркестратор згідно своїх інструкцій та правил з CLAUDE.md."


async def run(task: dict | None):
    meta, orchestrator = load_agent(AGENT_FILE)

    options = ClaudeAgentOptions(
        cwd=str(PROJECT_DIR),
        # "project" підхоплює CLAUDE.md, .claude/agents та .claude/skills
        setting_sources=["project"],
        # AGENT.md — інструкція головного агента-оркестратора поверх Claude Code
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": orchestrator,
        },
        model=meta.get("model") or None,
        allowed_tools=["Agent", "Read", "Write", "Edit", "Skill", "Bash", "Glob", "Grep"],
        permission_mode="acceptEdits",
        # агент читає PNG-прев'ю буклета через Read — це base64 у одному
        # JSON-повідомленні, що легко перевищує дефолтний ліміт SDK у 1 МБ
        max_buffer_size=32 * 1024 * 1024,
    )

    async for message in query(prompt=build_prompt(task), options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(message, ResultMessage):
            print(f"\n[готово] помилка: {message.is_error}, "
                  f"вартість: ${message.total_cost_usd}")


if __name__ == "__main__":
    task = collect_task()
    write_task(task)
    anyio.run(run, task)
