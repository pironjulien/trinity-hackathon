from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR

DATA_DIR = MEMORIES_DIR / "youtuber"
QUEUE_FILE = DATA_DIR / "data" / "queue.json"


def clean_queue():
    queue = load_json(QUEUE_FILE)
    original_count = len(queue["published"])

    # Remove entry with id containing "day0" if it's the ghost one
    # The real videos have YouTube IDs like 11-char strings
    queue["published"] = [
        v
        for v in queue["published"]
        if v["id"] != "day0_fr_published" and v["id"] != "2026-01-10T12:00:00"
    ]

    new_count = len(queue["published"])
    print(f"Cleaned queue: {original_count} -> {new_count} items")
    save_json(QUEUE_FILE, queue)


if __name__ == "__main__":
    clean_queue()
