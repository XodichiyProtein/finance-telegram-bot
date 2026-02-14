import torch
import torch.nn.functional as F
from enum import StrEnum
from dataclasses import dataclass
from typing import Final, Optional
from sentence_transformers import SentenceTransformer

CLASSIFIER_MODEL = "intfloat/multilingual-e5-large"


class Category(StrEnum):
    """Перечисление всех доступных категорий транзакций."""

    FOOD = "needs:food"
    TRANSPORT = "needs:transport"
    FASTFOOD = "fun:fastfood"
    ELECTRONICS = "wants:electronics"
    FINANCE = "skip:finance"
    DIGITAL = "other:digital"
    HEALTH = "needs:health"
    UTILITIES = "needs:utilities"
    HOUSEHOLD = "needs:household"
    CLOTHING = "wants:clothing"
    BEAUTY = "wants:beauty"
    LEISURE = "fun:leisure"
    PETS = "needs:pets"
    UNKNOWN = "unknown:check_me"


CATEGORY_ANCHORS: Final[dict[Category, list[str]]] = {
    Category.FOOD: [
        "Продукты питания, бакалея, молоко, хлеб, овощи в супермаркете",
        "Покупка еды в магазине Пятерочка, Магнит, Перекресток",
        "Ингредиенты для готовки, сырое мясо, крупы, фрукты",
    ],
    Category.FASTFOOD: [
        "Фастфуд, бургер, чизбургер, картошка фри, наггетсы",
        "Готовая еда из ресторана, доставка пиццы, суши, роллы",
        "Кофе с собой, латте, капучино, посещение кофейни или столовой",
    ],
    Category.ELECTRONICS: [
        "Компьютерная периферия, игровая мышь, клавиатура, монитор",
        "Смартфоны, айфон, наушники, зарядные устройства, гаджеты",
        "Бытовая техника, ноутбуки, видеокарты, электроника",
    ],
    Category.HOUSEHOLD: [
        "Мебель, товары для дома, ремонт, стройматериалы",
        "Покупка недвижимости, дом, квартира, апартаменты",
        "Хозяйственные товары, посуда, декор для интерьера",
    ],
    Category.TRANSPORT: [
        "Оплата общественного транспорта, метро, автобус, проездной",
        "Поездка на такси, каршеринг, аренда авто",
        "Бензин, автозаправка, техническое обслуживание автомобиля",
    ],
    Category.FINANCE: [
        "Брокерский счет, инвестиции, покупка акций и облигаций",
        "Перевод средств, пополнение банковской карты",
        "Оплата налогов, кредитов, ипотеки, штрафов",
    ],
    Category.DIGITAL: [
        "Оплата домашнего интернета, мобильная связь, тариф",
        "Подписки на сервисы, игры, программное обеспечение",
        "VPN услуги, хостинг, облачные хранилища",
    ],
    Category.HEALTH: [
        "Аптека, покупка лекарств, таблетки, витамины",
        "Медицинские услуги, платная клиника, сдача анализов",
        "Стоматология, прием врача, лечение",
    ],
    Category.UTILITIES: [
        "Оплата услуг ЖКХ, квартплата, счета за электричество",
        "Водоснабжение, отопление, вывоз мусора, домофон",
    ],
    Category.CLOTHING: [
        "Покупка одежды, куртка, штаны, джинсы, футболки",
        "Обувь, кроссовки, ботинки, туфли",
        "Аксессуары, сумки, покупки на маркетплейсах одежды",
    ],
    Category.BEAUTY: [
        "Салон красоты, парикмахерская, мужская стрижка, барбершоп",
        "Косметика, парфюмерия, средства по уходу за кожей",
        "Маникюр, педикюр, спа-процедуры, массаж",
    ],
    Category.LEISURE: [
        "Кинотеатр, театр, выставка, концерт, билеты на мероприятия",
        "Хобби, настольные игры, развлечения, активный отдых",
        "Вейп, сигареты, табак, электронные испарители",
    ],
    Category.PETS: [
        "Товары для животных, зоомагазин, игрушки для питомцев",
        "Корм для кошек, собак, наполнитель для лотка",
        "Ветеринарная клиника, груминг, услуги для животных",
    ],
}


def clean_text(text: str) -> str:
    """
    Очищает текст транзакции от информационного шума.

    Args:
        text (str): Исходное описание транзакции.

    Returns:
        str: Очищенная строка без стоп-слов и спецсимволов.
    """
    noise: Final = {"купил", "оплатил", "оплата", "чек", "покупка", "за", "в", "на"}
    words = text.lower().replace("|", " ").split()
    return " ".join(w for w in words if w not in noise)


def hard_rules_match(text: str) -> Optional[Category]:
    """
    Проверяет текст по жестким правилам (эвристикам) для быстрого возврата результата.
    Реализует принцип Fail-Fast: позволяет обойти тяжелую ML-модель для очевидных случаев.

    Args:
        text (str): Исходное описание транзакции.

    Returns:
        Optional[Category]: Найденная категория или None, если совпадений нет.
    """
    rules: Final[dict[str, Category]] = {
        "иис": Category.FINANCE,
        "брокер": Category.FINANCE,
        "инвестиц": Category.FINANCE,
        "перевод": Category.FINANCE,
        "жижа": Category.LEISURE,
        "картридж": Category.LEISURE,
        "дубай": Category.HOUSEHOLD,
        "дубаи": Category.HOUSEHOLD,
        "впн": Category.DIGITAL,
        "vpn": Category.DIGITAL,
        "чизбургер": Category.FASTFOOD,
        "бургер": Category.FASTFOOD,
        "мышь": Category.ELECTRONICS,
    }

    clean = text.lower()
    for trigger, cat in rules.items():
        if trigger in clean:
            return cat
    return None


@dataclass(frozen=True)
class ClassifierModel:
    """
    Неизменяемый контейнер данных модели для функционального пайплайна.

    Attributes:
        model (SentenceTransformer): Загруженная модель.
        anchor_embeddings (torch.Tensor): Нормализованные тензоры фраз-якорей.
        anchor_to_cat (list[Category]): Маппинг индексов тензоров на категории Enum.
        threshold (float): Порог косинусного сходства для отсечения неизвестных.
    """

    model: SentenceTransformer
    anchor_embeddings: torch.Tensor
    anchor_to_cat: list[Category]
    threshold: float = 0.82


def init_classifier(
    model_name: str, anchors_dict: dict[Category, list[str]]
) -> ClassifierModel:
    """
    Инициализирует ML-модель и предрассчитывает эмбеддинги для всех категорий.

    Для моделей архитектуры E5 обязательно использование префикса 'passage: '
    для эталонных фраз.

    Args:
        model_name (str): HuggingFace ID модели (напр., 'intfloat/multilingual-e5-large').
        anchors_dict (dict[Category, list[str]]): Словарь категорий и их якорных фраз.

    Returns:
        ClassifierModel: Готовый к работе инстанс датакласса с тензорами.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(model_name, device=device)

    all_phrases = []
    anchor_to_cat = []

    for cat, phrases in anchors_dict.items():
        for phrase in phrases:
            all_phrases.append(f"passage: {phrase}")
            anchor_to_cat.append(cat)

    embeddings = model.encode(all_phrases, convert_to_tensor=True)
    embeddings = F.normalize(embeddings, p=2, dim=1)

    return ClassifierModel(
        model=model, anchor_embeddings=embeddings, anchor_to_cat=anchor_to_cat
    )


def predict(model_data: ClassifierModel, text: str) -> Category:
    """
    Классифицирует входящую текстовую транзакцию.

    Сначала применяются жесткие правила. Если они не сработали, текст очищается,
    преобразуется в вектор с префиксом 'query: ' и сравнивается с якорями
    через скалярное произведение (dot product).

    Args:
        model_data (ClassifierModel): Инициализированный контейнер с моделью.
        text (str): Текст транзакции.

    Returns:
        Category: Определенная категория или Category.UNKNOWN при низкой уверенности.
    """
    if rule_result := hard_rules_match(text):
        return rule_result

    cleaned_text = clean_text(text)
    query = f"query: {cleaned_text}"

    text_emb = model_data.model.encode(query, convert_to_tensor=True)
    text_emb = F.normalize(text_emb.unsqueeze(0), p=2, dim=1)

    scores = torch.mm(text_emb, model_data.anchor_embeddings.T)[0]

    best_idx = torch.argmax(scores).item()
    confidence = scores[best_idx].item()

    if confidence < model_data.threshold:
        return Category.UNKNOWN

    return model_data.anchor_to_cat[best_idx]


class ExpenseClassifier:
    """
    Класс-обертка над ML-пайплайном для использования в хендлерах Telegram-бота.
    Хранит состояние (загруженную модель) и предоставляет простой метод классификации.
    """

    def __init__(self, model_name: str = CLASSIFIER_MODEL):
        """
        Инициализирует модель при создании инстанса класса.
        Вызывается один раз на старте бота.
        """
        self._model_data = init_classifier(model_name, CATEGORY_ANCHORS)

        predict(self._model_data, "warmup init text")

    def classify(self, text: str) -> str:
        """
        Классифицирует текст транзакции.

        Args:
            text (str): Описание расхода, например "купил кофе".

        Returns:
            str: Строковый код категории (например, "fun:fastfood").
        """
        category = predict(self._model_data, text)
        return str(category.value)
