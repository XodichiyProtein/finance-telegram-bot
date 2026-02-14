from collections.abc import Mapping

class ExpenseClassifier:
    _KEYWORDS_MAP: Mapping[str, str] = {
        "магнит": "needs:food",
        "пятероч": "needs:food",
        "перекрест": "needs:food",
        "еда": "needs:food",
        "такси": "needs:transport",
        "метро": "needs:transport",
        "автобус": "needs:transport",
        "кофе": "fun:fastfood",
        "мак": "fun:fastfood",
        "бургер": "fun:fastfood",
        "игра": "fun:fastfood",
        "steam": "fun:fastfood",
        "наушник": "wants:electronics",
        "клава": "wants:electronics",
        "мышк": "wants:electronics",
    }
    _DEFAULT_CATEGORY: str = "needs:food"

    def classify(self, text: str) -> str:
        lowered = text.lower()
        for keyword, category_code in self._KEYWORDS_MAP.items():
            if keyword in lowered:
                return category_code
        return self._DEFAULT_CATEGORY
