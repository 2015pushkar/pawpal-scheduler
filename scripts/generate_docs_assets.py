from __future__ import annotations

from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DOCS_IMAGES = ROOT / "docs" / "images"


BACKGROUND = "#f6f2ea"
INK = "#1f2937"
MUTED = "#5b6472"
LINE = "#324255"
DOMAIN_FILL = "#fdf7dc"
AI_FILL = "#ddefff"
OUTPUT_FILL = "#e6f5e6"
BOX_BORDER = "#213247"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                Path("C:/Windows/Fonts/segoeuib.ttf"),
                Path("C:/Windows/Fonts/arialbd.ttf"),
                Path("C:/Windows/Fonts/calibrib.ttf"),
            ]
        )
    else:
        candidates.extend(
            [
                Path("C:/Windows/Fonts/segoeui.ttf"),
                Path("C:/Windows/Fonts/arial.ttf"),
                Path("C:/Windows/Fonts/calibri.ttf"),
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


TITLE_FONT = load_font(42, bold=True)
SUBTITLE_FONT = load_font(24, bold=False)
CLASS_TITLE_FONT = load_font(26, bold=True)
BODY_FONT = load_font(20, bold=False)
SMALL_FONT = load_font(18, bold=False)
LABEL_FONT = load_font(18, bold=True)


def ensure_dirs() -> None:
    DOCS_IMAGES.mkdir(parents=True, exist_ok=True)


def text_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=6)
    return bbox[3] - bbox[1]


def draw_centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font, fill=INK) -> None:
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=6, align="center")
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = box[0] + ((box[2] - box[0]) - width) / 2
    y = box[1] + ((box[3] - box[1]) - height) / 2
    draw.multiline_text((x, y), text, font=font, fill=fill, spacing=6, align="center")


def draw_class_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    attributes: list[str],
    methods: list[str],
    fill: str,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=BOX_BORDER, width=3)

    title_y = y1 + 18
    draw_centered(draw, (x1 + 20, title_y, x2 - 20, title_y + 40), title, CLASS_TITLE_FONT)

    title_divider_y = y1 + 70
    method_divider_y = y1 + 70 + max(110, 16 + len(attributes) * 28)
    if method_divider_y > y2 - 80:
        method_divider_y = y2 - 80

    draw.line((x1, title_divider_y, x2, title_divider_y), fill=BOX_BORDER, width=2)
    draw.line((x1, method_divider_y, x2, method_divider_y), fill=BOX_BORDER, width=2)

    attr_text = "\n".join(attributes)
    method_text = "\n".join(methods)
    draw.multiline_text((x1 + 18, title_divider_y + 16), attr_text, font=BODY_FONT, fill=INK, spacing=6)
    draw.multiline_text((x1 + 18, method_divider_y + 16), method_text, font=BODY_FONT, fill=INK, spacing=6)


def _draw_arrow_head(draw: ImageDraw.ImageDraw, tip: tuple[int, int], direction: str, fill: str = LINE) -> None:
    x, y = tip
    if direction == "down":
        points = [(x, y), (x - 10, y - 18), (x + 10, y - 18)]
    elif direction == "up":
        points = [(x, y), (x - 10, y + 18), (x + 10, y + 18)]
    elif direction == "left":
        points = [(x, y), (x + 18, y - 10), (x + 18, y + 10)]
    else:
        points = [(x, y), (x - 18, y - 10), (x - 18, y + 10)]
    draw.polygon(points, fill=fill)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    head: str,
    dashed: bool = False,
    label: str | None = None,
    label_xy: tuple[int, int] | None = None,
    color: str = LINE,
) -> None:
    if dashed:
        for start, end in zip(points, points[1:]):
            x1, y1 = start
            x2, y2 = end
            steps = max(abs(x2 - x1), abs(y2 - y1)) // 12
            if steps <= 0:
                continue
            for i in range(steps):
                if i % 2:
                    continue
                sx = x1 + (x2 - x1) * i / steps
                sy = y1 + (y2 - y1) * i / steps
                ex = x1 + (x2 - x1) * min(i + 1, steps) / steps
                ey = y1 + (y2 - y1) * min(i + 1, steps) / steps
                draw.line((sx, sy, ex, ey), fill=color, width=3)
    else:
        draw.line(points, fill=color, width=3, joint="curve")

    _draw_arrow_head(draw, points[-1], head, fill=color)
    if label and label_xy:
        bbox = draw.textbbox((0, 0), label, font=LABEL_FONT)
        padding = 8
        label_box = (
            label_xy[0] - padding,
            label_xy[1] - padding,
            label_xy[0] + (bbox[2] - bbox[0]) + padding,
            label_xy[1] + (bbox[3] - bbox[1]) + padding,
        )
        draw.rounded_rectangle(label_box, radius=10, fill="#ffffff", outline="#d3dae5", width=1)
        draw.text(label_xy, label, font=LABEL_FONT, fill=INK)


def draw_diamond(draw: ImageDraw.ImageDraw, center: tuple[int, int], fill: str) -> None:
    x, y = center
    points = [(x, y - 12), (x + 12, y), (x, y + 12), (x - 12, y)]
    draw.polygon(points, fill=fill, outline=fill)


def draw_title(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    draw.text((80, 50), title, font=TITLE_FONT, fill=INK)
    draw.text((80, 105), subtitle, font=SUBTITLE_FONT, fill=MUTED)


def draw_legend(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    legend_box = (x, y, x + 430, y + 120)
    draw.rounded_rectangle(legend_box, radius=18, fill="#ffffff", outline="#d8e0ea", width=2)
    draw.text((x + 18, y + 14), "Legend", font=LABEL_FONT, fill=INK)
    entries = [
        (DOMAIN_FILL, "Domain scheduling classes"),
        (AI_FILL, "Care-helper and retrieval classes"),
        (OUTPUT_FILL, "Result / output objects"),
    ]
    for idx, (fill, label) in enumerate(entries):
        top = y + 44 + idx * 24
        draw.rounded_rectangle((x + 18, top, x + 40, top + 16), radius=4, fill=fill, outline=BOX_BORDER, width=1)
        draw.text((x + 52, top - 4), label, font=SMALL_FONT, fill=INK)


def make_domain_class_diagram() -> None:
    image = Image.new("RGB", (1900, 1420), BACKGROUND)
    draw = ImageDraw.Draw(image)

    draw_title(
        draw,
        "PawPal+ UML Class Diagram",
        "Deterministic scheduling domain model used by the app and by AI-generated follow-up tasks.",
    )
    draw_legend(draw, 1370, 48)

    boxes = {
        "Scheduler": (710, 190, 1180, 520),
        "Owner": (120, 410, 560, 760),
        "Schedule": (1280, 410, 1720, 760),
        "Pet": (150, 920, 600, 1310),
        "Task": (980, 920, 1430, 1340),
    }

    draw_class_box(
        draw,
        boxes["Scheduler"],
        "Scheduler",
        ["- owner: Owner"],
        [
            "+ get_all_tasks()",
            "+ sort_by_time(tasks)",
            "+ filter_by_pet(tasks, pet_name)",
            "+ filter_by_status(tasks, completed)",
            "+ mark_task_complete(task, pet)",
            "+ detect_conflicts(schedule)",
            "+ generate_schedule()",
            "+ explain_plan(schedule)",
        ],
        DOMAIN_FILL,
    )
    draw_class_box(
        draw,
        boxes["Owner"],
        "Owner",
        ["- name: str", "- available_minutes_per_day: int", "- preferences: list[str]", "- pets: list[Pet]"],
        ["+ add_pet(pet)", "+ remove_pet(name)", "+ get_all_tasks()", "+ get_available_time()", "+ update_preferences(prefs)"],
        DOMAIN_FILL,
    )
    draw_class_box(
        draw,
        boxes["Schedule"],
        "Schedule",
        ["- tasks: list[Task]", "- skipped_tasks: list[Task]"],
        ["+ add_task(task)", "+ get_total_duration()", "+ get_summary()"],
        DOMAIN_FILL,
    )
    draw_class_box(
        draw,
        boxes["Pet"],
        "Pet",
        ["- name: str", "- species: str", "- age: int", "- special_needs: list[str]", "- tasks: list[Task]"],
        ["+ add_task(task)", "+ remove_task(title)", "+ get_tasks()", "+ get_info()"],
        DOMAIN_FILL,
    )
    draw_class_box(
        draw,
        boxes["Task"],
        "Task",
        [
            "- title: str",
            "- duration_minutes: int",
            "- priority: str",
            "- frequency: str",
            "- category: str",
            "- time_of_day: str",
            "- due_date: date",
            "- completed: bool",
        ],
        ["+ mark_complete()", "+ is_valid()", "+ to_dict()"],
        DOMAIN_FILL,
    )

    draw_arrow(draw, [(710, 355), (560, 355), (560, 585)], head="down", label="uses", label_xy=(580, 370))
    draw_arrow(draw, [(1180, 355), (1280, 355), (1280, 585)], head="down", dashed=True, label="produces", label_xy=(1185, 320))

    draw_diamond(draw, (375, 760), fill=BOX_BORDER)
    draw_arrow(draw, [(375, 760), (375, 920)], head="down", label="1 owns *", label_xy=(248, 820))

    draw_diamond(draw, (600, 1090), fill=BOX_BORDER)
    draw_arrow(draw, [(600, 1090), (980, 1090)], head="right", label="1 has *", label_xy=(710, 1048))

    draw_diamond(draw, (1280, 1090), fill="#ffffff")
    draw_arrow(draw, [(1280, 1090), (1430, 1090)], head="right", label="contains *", label_xy=(1245, 1048))

    note = (1500, 980, 1770, 1120)
    draw.rounded_rectangle(note, radius=18, fill="#ffffff", outline="#d8e0ea", width=2)
    note_text = "AI suggestions are converted\ninto Task objects before\nentering this model."
    draw.multiline_text((1530, 1010), note_text, font=SMALL_FONT, fill=INK, spacing=6)

    image.save(DOCS_IMAGES / "pawpal-uml-class-diagram.png")


def make_ai_class_diagram() -> None:
    image = Image.new("RGB", (2100, 1540), BACKGROUND)
    draw = ImageDraw.Draw(image)

    draw_title(
        draw,
        "PawPal+ Care-Helper UML Diagram",
        "Local classification, retrieval, and advice objects used to turn symptom text into grounded follow-up tasks.",
    )
    draw_legend(draw, 1570, 48)

    boxes = {
        "SymptomExample": (120, 240, 530, 520),
        "SymptomClassifier": (610, 240, 1110, 560),
        "KnowledgeDocument": (1570, 240, 1980, 600),
        "KnowledgeBase": (1350, 760, 1840, 1080),
        "PetCareAdvisor": (820, 700, 1240, 1010),
        "AdviceResult": (650, 1140, 1120, 1480),
        "TaskSuggestion": (1370, 1140, 1850, 1480),
    }

    draw_class_box(
        draw,
        boxes["SymptomExample"],
        "SymptomExample",
        ["- text: str", "- condition: str", "- record_type: str"],
        ["<<data object>>"],
        AI_FILL,
    )
    draw_class_box(
        draw,
        boxes["SymptomClassifier"],
        "SymptomClassifier",
        ["- examples: list[SymptomExample]", "- example_vectors: list[(SymptomExample, Counter)]"],
        ["+ classify(query, top_k=5) -> ClassificationResult"],
        AI_FILL,
    )
    draw_class_box(
        draw,
        boxes["KnowledgeDocument"],
        "KnowledgeDocument",
        [
            "- doc_id: str",
            "- title: str",
            "- conditions: list[str]",
            "- source_url: str",
            "- care_steps: list[str]",
            "- warning_signs: list[str]",
            "- suggested_tasks: list[TaskSuggestion]",
        ],
        ["+ searchable_text"],
        AI_FILL,
    )
    draw_class_box(
        draw,
        boxes["KnowledgeBase"],
        "KnowledgeBase",
        ["- documents: list[KnowledgeDocument]", "- document_vectors: dict[str, Counter]"],
        ["+ retrieve(query, condition, species, limit=3)"],
        AI_FILL,
    )
    draw_class_box(
        draw,
        boxes["PetCareAdvisor"],
        "PetCareAdvisor",
        ["- classifier: SymptomClassifier", "- knowledge_base: KnowledgeBase"],
        ["+ advise(pet, query) -> AdviceResult"],
        AI_FILL,
    )
    draw_class_box(
        draw,
        boxes["AdviceResult"],
        "AdviceResult",
        [
            "- condition: str",
            "- confidence: float",
            "- simple_summary: str",
            "- care_steps: list[str]",
            "- warning_signs: list[str]",
            "- citations: list[SourceCitation]",
            "- suggested_tasks: list[TaskSuggestion]",
        ],
        ["<<result object>>"],
        OUTPUT_FILL,
    )
    draw_class_box(
        draw,
        boxes["TaskSuggestion"],
        "TaskSuggestion",
        ["- title: str", "- duration_minutes: int", "- priority: str", "- frequency: str", "- rationale: str"],
        ["+ to_task() -> Task"],
        OUTPUT_FILL,
    )
    draw_arrow(draw, [(530, 380), (610, 380)], head="right", label="training data", label_xy=(520, 337))
    draw_arrow(draw, [(1110, 430), (1240, 430), (1240, 855)], head="down", label="used by advisor", label_xy=(1150, 520))
    draw_arrow(draw, [(1570, 920), (1240, 920)], head="left", label="retrieval service", label_xy=(1330, 875))
    draw_arrow(draw, [(1775, 600), (1775, 760)], head="down", label="indexed docs", label_xy=(1668, 660))
    draw_arrow(draw, [(1030, 1010), (1030, 1140)], head="down", label="returns", label_xy=(1048, 1060))

    draw_diamond(draw, (1120, 1260), fill="#ffffff")
    draw_arrow(draw, [(1120, 1260), (1370, 1260)], head="right", label="contains *", label_xy=(1170, 1218))

    note = (120, 630, 560, 880)
    draw.rounded_rectangle(note, radius=22, fill="#ffffff", outline="#d8e0ea", width=2)
    note_text = (
        "Scope note:\n"
        "This layer stays local and bounded.\n"
        "It classifies symptom text,\n"
        "retrieves local guidance, and\n"
        "proposes structured follow-up tasks.\n"
        "It does not directly schedule the day."
    )
    draw.multiline_text((150, 665), note_text, font=BODY_FONT, fill=INK, spacing=10)

    domain_note = (120, 1120, 560, 1380)
    draw.rounded_rectangle(domain_note, radius=22, fill="#fffaf0", outline="#d8e0ea", width=2)
    domain_note_text = (
        "Domain integration:\n"
        "TaskSuggestion.to_task()\n"
        "converts a suggested action\n"
        "into the scheduler's Task model\n"
        "before the daily plan is built."
    )
    draw.multiline_text((150, 1160), domain_note_text, font=BODY_FONT, fill=INK, spacing=10)

    image.save(DOCS_IMAGES / "pawpal-care-helper-uml-diagram.png")


def draw_layer(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    lines: list[str],
    fill: str,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=28, fill=fill, outline=BOX_BORDER, width=3)
    draw.text((x1 + 24, y1 + 18), title, font=CLASS_TITLE_FONT, fill=INK)
    draw.line((x1 + 20, y1 + 64, x2 - 20, y1 + 64), fill=BOX_BORDER, width=2)
    draw.multiline_text((x1 + 24, y1 + 88), "\n".join(lines), font=BODY_FONT, fill=INK, spacing=10)


def make_architecture_diagram() -> None:
    image = Image.new("RGB", (2200, 1450), BACKGROUND)
    draw = ImageDraw.Draw(image)

    draw_title(
        draw,
        "PawPal+ System Architecture",
        "The AI layer interprets and grounds care guidance; the scheduler remains the final deterministic planner.",
    )

    left = (100, 210, 520, 520)
    classify = (620, 210, 1040, 520)
    retrieve = (1140, 210, 1560, 520)
    compose = (1660, 210, 2080, 520)

    domain = (280, 770, 930, 1250)
    outputs = (1180, 770, 1900, 1250)

    draw_layer(
        draw,
        left,
        "1. User Inputs",
        [
            "Owner profile and time budget",
            "Pet records and manual care tasks",
            "Free-text symptom or care question",
            "Selected pet for the question",
        ],
        "#fff3dc",
    )
    draw_layer(
        draw,
        classify,
        "2. Symptom Classification",
        [
            "Tokenize and normalize the query",
            "Compare against local symptom examples",
            "Apply keyword boosts per condition",
            "Return condition + confidence",
        ],
        "#dff1ff",
    )
    draw_layer(
        draw,
        retrieve,
        "3. Grounded Retrieval",
        [
            "Use condition + query + species",
            "Score local knowledge documents",
            "Return top matching care guidance",
            "Keep source links attached",
        ],
        "#dff1ff",
    )
    draw_layer(
        draw,
        compose,
        "4. Safe Advice Composition",
        [
            "Build summary from retrieved content",
            "Surface warning signs and escalation",
            "Generate suggested follow-up tasks",
            "Return AdviceResult for the UI",
        ],
        "#dff1ff",
    )
    draw_layer(
        draw,
        domain,
        "5. Deterministic Scheduling Core",
        [
            "Owner, Pet, Task, Scheduler, Schedule",
            "One shared task model for manual and AI tasks",
            "Greedy priority-first schedule generation",
            "Conflict detection and skipped-task reporting",
            "Recurring task completion creates next occurrence",
        ],
        "#fdf7dc",
    )
    draw_layer(
        draw,
        outputs,
        "6. User-Facing Outputs",
        [
            "Grounded care summary with citations",
            "Suggested next steps and warning signs",
            "Tasks added back into the same workflow",
            "Daily schedule that respects time limits",
            "Explainable plan rather than opaque automation",
        ],
        "#e6f5e6",
    )

    # Data source pills
    for box, title in [
        ((690, 560, 980, 640), "Local symptom CSV"),
        ((1210, 560, 1510, 640), "Local knowledge JSON"),
    ]:
        draw.rounded_rectangle(box, radius=20, fill="#ffffff", outline="#cad7e5", width=2)
        draw_centered(draw, box, title, LABEL_FONT)

    # Arrows across the top flow
    draw_arrow(draw, [(520, 365), (620, 365)], head="right", label="query", label_xy=(548, 327))
    draw_arrow(draw, [(1040, 365), (1140, 365)], head="right", label="condition + confidence", label_xy=(1030, 325))
    draw_arrow(draw, [(1560, 365), (1660, 365)], head="right", label="ranked docs", label_xy=(1590, 327))

    draw_arrow(draw, [(835, 520), (835, 560)], head="down", dashed=True)
    draw_arrow(draw, [(1360, 520), (1360, 560)], head="down", dashed=True)

    draw_arrow(draw, [(1870, 520), (1870, 700), (1460, 700), (1460, 770)], head="down", label="task suggestions", label_xy=(1580, 655))
    draw_arrow(draw, [(420, 520), (420, 650), (620, 650), (620, 770)], head="down", label="manual tasks + owner context", label_xy=(340, 605))
    draw_arrow(draw, [(930, 1010), (1180, 1010)], head="right", label="daily plan", label_xy=(1010, 970))

    # Bottom callouts
    callout = (100, 1310, 2080, 1400)
    draw.rounded_rectangle(callout, radius=22, fill="#ffffff", outline="#d8e0ea", width=2)
    callout_text = (
        "Key design choice: AI is used for fuzzy interpretation and grounded guidance. "
        "Execution stays deterministic because both manual work and AI follow-ups are normalized "
        "into the same Task model before scheduling."
    )
    draw.multiline_text((130, 1335), callout_text, font=BODY_FONT, fill=INK, spacing=8)

    image.save(DOCS_IMAGES / "pawpal-system-architecture.png")


def copy_existing_screenshots() -> None:
    mappings = {
        ROOT / "rag functionality.png": DOCS_IMAGES / "care-guidance-screen.png",
        ROOT / "schedule monitoring.png": DOCS_IMAGES / "suggested-tasks-and-schedule-screen.png",
        ROOT / "Screenshot.png": DOCS_IMAGES / "schedule-screen.png",
    }
    for src, dest in mappings.items():
        if src.exists():
            shutil.copyfile(src, dest)


def main() -> None:
    ensure_dirs()
    make_domain_class_diagram()
    make_ai_class_diagram()
    make_architecture_diagram()
    copy_existing_screenshots()
    print(f"Generated assets in {DOCS_IMAGES}")


if __name__ == "__main__":
    main()
