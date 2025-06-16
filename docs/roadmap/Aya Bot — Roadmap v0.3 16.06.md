# Aya Bot — Roadmap v0.3 (основной рабочий)

> Обновлено: 2025-06-16. Объединены изменения из v0.2.3 и Roadmap_v0.1-rc3. Добавлены teachingNodes‑migration (A‑5, A‑6) и календарь спринтов до 22 июля.

---

## Таблица задач

| ID | Блок | Что делаем | Зависимости | Приор. | Оценка* |
|----|------|-----------|-------------|--------|---------|
| **A‑0** | **Core API** | Вынести «мозг» (FastAPI / Python) за пределы адаптеров. Эндпойнты: `/chat`, `/prompt`, `/health`. | ― | **1** | 2–3 дня |
| **A‑0.2** | **Combined Guide (architect·curator·helper)** | Новый системный промпт: одна роль объединяет Архитектора, Куратора и Общего помощника. Команда `/improve` для тех‑совета. | A‑0 | **1** | 0,5 дня |
| **A‑1** | Telegram‑адаптер | Переключить на Core API. | A‑0 | 1 | 0,5 дня |
| **A‑2** | **Prompt Sync → Firestore** | Коллекция `prompts`, auto‑reload. | A‑0 | **1** | 1 день |
| **A‑2.1** | Canvas → GitHub Upload | Ручная процедура Download → Upload. | A‑2 | **1** | — |
| **A‑2.2** | Firestore structure cleanup | Схема: `dialogs`, `prompts`, `model_rules`, `user_settings`, `logs`. | A‑2 | **1** | 0,5 дня |
| **A‑2.3** | Repo folder conventions | `/docs/prompts/`, `/docs/roadmaps/`, `/docs/specs/`. | A‑2 | 2 | 0,5 дня |
| **A‑3** | Autodetect topic | В Core API. | A‑0 | 2 | 2 дня |
| **A‑4** | `/opts` | Личные настройки (темп‑ра, язык). | A‑0 | 3 | 1–2 дня |
| **A‑5** | teachingNodes migration I | Перенести существующие teachingNodes в `knowledge/nodes`. | A‑0, A‑2.2 | **1** | 1 день |
| **A‑6** | teachingNodes schema final | Валидация, индексы, тесты + docs. | A‑5 | 2 | 1 день |
| **A‑7** | RAG‑stub (100 FAQ) | Заглушка FAQ на Qdrant; использует teachingNodes schema. | A‑5, A‑6 | 3 | 2 дня |
| **B‑1** | **Model Rules** | Коллекция `model_rules` (channel→model) + `select_model()`. | A‑0 | **1** | 1 день |
| **B‑2** | WhatsApp‑адаптер | Meta Cloud API MVP. | A‑0, A‑2, B‑1 | 4 | 2–3 дня |
| **B‑3** | Instagram‑DM адаптер | После WhatsApp. | A‑0, A‑2, B‑1 | 4 | 3–4 дня |
| **C‑1** | Alt‑LLM (Anthropic‑Sonnet) | Подключение через `select_model()`. | B‑1 | 5 | 1 день |
| **C‑2** | Expand metric sources | Cloud Trace latency, BigQuery‑экспорт, Billing API детализация. | A‑2.2 | 5 | 1 день |

\* Dev‑оценка без буфера (+30–40 % тесты/ревью).

---

## Спринт‑календарь (до 22 июля 2025)

| Sprint | Даты | Цели |
|-------|-------|-------|
| **S‑1** | 17 июн – 30 июн | A‑0, A‑1, A‑2, A‑2.1, A‑2.2, A‑2.3 |
| **S‑2** | 1 июл – 14 июл | A‑0.2, A‑3, A‑4, A‑5, A‑6 |
| **S‑3** | 15 июл – 22 июл | A‑7, B‑1 |

> Куратор обновляет статус спринтов каждую пятницу.

---

## Каналы → Модели (TBD)
*Конкретные LLM‑привязки будут определены после запуска Core API и нагрузочных тестов.*

---

## Canvas → GitHub → Firestore (A‑2 + A‑2.1)
Не изменилось.

---

## Эпохи
**Виток 1**: Core API, Prompt Sync, teachingNodes migration, Telegram.  
**Виток 2**: новые каналы, Model Rules.  
**Виток 3**: альтернативные LLM, расширенные метрики.

---

## История изменений
* 2025‑06‑16 — **v0.3**: объединение v0.2.3 и rc3; teachingNodes, календарь.

— Конец файла —

