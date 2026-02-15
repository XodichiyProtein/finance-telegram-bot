from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import torch
from torch.utils.data import DataLoader, Dataset
from torch import nn
from sentence_transformers import SentenceTransformer, InputExample
from enum import Enum

from src.classifier.classifier import (
    Category,
    CLASSIFIER_MODEL,
    clean_text,
)
from src.core.logger import setup_logger
import json
from typing import Protocol

logger = setup_logger(__name__)


FINETUNED_MODEL_PATH: Final[Path] = Path("models/finance-e5-finetuned")
OUTPUT_DIR: Final[Path] = Path("models/finance-e5-finetuned")


@dataclass(slots=True, frozen=True)
class LabeledSample:
    text: str
    category: Category


class CategoryId(int, Enum):
    FOOD = 0
    TRANSPORT = 1
    FASTFOOD = 2
    ELECTRONICS = 3
    FINANCE = 4
    DIGITAL = 5
    HEALTH = 6
    UTILITIES = 7
    HOUSEHOLD = 8
    CLOTHING = 9
    BEAUTY = 10
    LEISURE = 11
    PETS = 12
    UNKNOWN = 13


class ExpenseDataset(Dataset):
    def __init__(self, texts: list[str], labels: list[int]) -> None:
        self._texts = texts
        self._labels = labels

    def __len__(self) -> int:
        return len(self._texts)

    def __getitem__(self, idx: int) -> tuple[str, int]:
        return self._texts[idx], self._labels[idx]


class JsonDatasetLoader:
    """Отвечает только за чтение файла (SRP)."""

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def load(self) -> list[tuple[str, Category]]:
        if not self._file_path.exists():
            return []

        with open(self._file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [(item["text"], Category[item["category"]]) for item in data]


def build_examples(
    samples: list[LabeledSample],
) -> tuple[list[InputExample], dict[Category, int]]:
    """
    Преобразовать размеченные примеры в InputExample для sentence-transformers.
    """
    categories = sorted({sample.category for sample in samples}, key=lambda c: c.value)
    category_to_id: dict[Category, int] = {
        cat: idx for idx, cat in enumerate(categories)
    }

    train_examples: list[InputExample] = []
    for sample in samples:
        cleaned = clean_text(sample.text)
        query = f"query: {cleaned}"
        label_id = category_to_id[sample.category]
        train_examples.append(InputExample(texts=[query], label=label_id))

    return train_examples, category_to_id


def load_training_data() -> tuple[list[str], list[int]]:
    data_path = Path("data_learn/data.json")

    if not data_path.exists():
        raise FileNotFoundError(
            f"❌ Файл с данными не найден по пути: {data_path.absolute()}"
        )

    loader = JsonDatasetLoader(data_path)
    raw_data: list[tuple[str, Category]] = loader.load()

    if not raw_data:
        raise ValueError(f"❌ Файл {data_path} пуст или содержит некорректные данные")

    categories = sorted({cat for _, cat in raw_data}, key=lambda c: c.value)
    cat_to_id: dict[Category, int] = {cat: idx for idx, cat in enumerate(categories)}

    texts: list[str] = []
    labels: list[int] = []

    for text, cat in raw_data:
        cleaned = clean_text(text)
        texts.append(f"query: {cleaned}")
        labels.append(cat_to_id[cat])

    return texts, labels


def build_train_examples(
    samples: list[LabeledSample],
) -> tuple[list[InputExample], dict[Category, int]]:
    categories = sorted({s.category for s in samples}, key=lambda c: c.value)
    category_to_id: dict[Category, int] = {
        cat: idx for idx, cat in enumerate(categories)
    }

    examples: list[InputExample] = []
    for sample in samples:
        cleaned = clean_text(sample.text)
        query = f"query: {cleaned}"
        label_id = category_to_id[sample.category]
        examples.append(InputExample(texts=[query], label=label_id))

    return examples, category_to_id


def train() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"

    texts, labels = load_training_data()
    dataset = ExpenseDataset(texts, labels)
    dataloader = DataLoader(dataset, batch_size=16, shuffle=True)

    base_model = SentenceTransformer(CLASSIFIER_MODEL, device=device)
    embedding_dim = base_model.get_sentence_embedding_dimension()
    num_labels = max(labels) + 1

    classifier_head = nn.Linear(embedding_dim, num_labels).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(classifier_head.parameters(), lr=1e-4)

    epochs = 10
    classifier_head.train()

    for epoch in range(epochs):
        total_loss = 0
        num_batches = 0

        for batch_texts, batch_labels in dataloader:
            batch_labels_tensor = torch.tensor(
                batch_labels, dtype=torch.long, device=device
            )

            with torch.no_grad():
                embeddings = base_model.encode(
                    list(batch_texts),
                    convert_to_tensor=True,
                    device=device,
                )

            embeddings = embeddings.clone().detach().requires_grad_(True)

            logits = classifier_head(embeddings)
            loss = criterion(logits, batch_labels_tensor)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            num_batches += 1

        avg_loss = total_loss / num_batches
        print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")

    FINETUNED_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    base_model.save(str(FINETUNED_MODEL_PATH))
    torch.save(
        {
            "state_dict": classifier_head.state_dict(),
            "num_labels": num_labels,
        },
        FINETUNED_MODEL_PATH / "classifier_head.pt",
    )
    print(f"✅ Модель сохранена в {FINETUNED_MODEL_PATH}")


if __name__ == "__main__":
    train()
