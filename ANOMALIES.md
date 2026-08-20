# ANOMALIES — review.csv

Короткий отчет по сюрпризам в `data/review.csv`.

- Строк в CSV (без заголовка): **207**
- Уникальных id: **202**
- Записей с аномалиями / кодов: **40**
- Валидных строк, влитых в `companies`: **190**
- Итого в `companies` после merge: **1178**

## Главный сюрприз

Файл называется `review.csv`, но это не отзывы. Это снова компании: те же поля, что в `page_*.json` (`id`, `name`, `category`, `city`, `address`, `rating`, `reviews_count`, `site`, `phone`). Обнаружено по заголовку CSV и сравнению со схемой JSON.

## Сайты компаний не открываются

В данных **нет email** клиентов — только поле `site` (и телефон). Сами ссылки на сайты выглядят как синтетика и по факту не открываются.

Как проверял:
1. Собрал уникальные `site` из JSON + CSV: **884** штуки.
2. Почти все в шаблонах `имя-число.ru/.com/.net` (**704**) или `ip-число.*` (**178**).
3. Пробил выборку из **35** случайных URL сетевым запросом: **0 рабочих**, все с `URLError` / недоступны.
4. «Особые» значения: пустой `https://` и общий `https://shared-site.ru` — тоже не выглядят как реальные сайты компаний.

Рабочих сайтов клиентов в датасете **не нашел**, поэтому подставлять нечего. В UI ссылки остаются как в выгрузке (для воспроизводимости), но на них опираться как на живые лендинги нельзя.

Примеры неоткрывающихся:
- `https://expert-service-861.ru` (json, `c_000776`)
- `https://ip-344.ru` (json, `c_000410`)
- `https://kvarts-group-977.ru` (csv, `c_001123`)
- `http://orion-pro-596.net` (json, `c_000091`)
- `https://polet-stroy-83.ru` (csv, `c_001019`)

## Как искал

1. Сверил колонки CSV с полями JSON.
2. Посчитал пересечение id с уже загруженной базой.
3. Прогнал валидацию: рейтинг, отзывы, телефон, сайт, город, пустые строки, дубли id.
4. Всё странное сложил в `load_anomalies` и в этот файл.

## Найденные аномалии

### `rating_empty` (18)

rating=''
- row 44, id=c_001190: rating=''
- row 49, id=c_001098: rating=''
- row 63, id=c_001068: rating=''
- row 81, id=c_001180: rating=''
- row 86, id=c_001045: rating=''
- … и еще 13

### `duplicate_id_in_csv` (3)

id c_001075 appears 2 times in review.csv
- file-level, id=c_001075: id c_001075 appears 2 times in review.csv
- file-level, id=c_001049: id c_001049 appears 2 times in review.csv
- file-level, id=c_001050: id c_001050 appears 2 times in review.csv

### `empty_row` (2)

Completely empty CSV row
- row 207, id=-: Completely empty CSV row
- row 208, id=-: Completely empty CSV row

### `rating_out_of_range` (2)

rating='-3'
- row 96, id=c_001122: rating='-3'
- row 197, id=c_001186: rating='7.2'

### `reviews_non_integer` (2)

reviews_count='45.5'
- row 98, id=c_001079: reviews_count='45.5'
- row 200, id=c_001187: reviews_count='много'

### `city_case` (1)

City casing anomaly: 'москва'
- row 166, id=c_001047: City casing anomaly: 'москва'

### `city_english` (1)

City written in English: Moscow
- row 127, id=c_001108: City written in English: Moscow

### `city_looks_like_address` (1)

Address value in city column: 'ул. Советская, д. 89, офис 43'
- row 37, id=c_001015: Address value in city column: 'ул. Советская, д. 89, офис 43'

### `city_mojibake` (1)

Broken encoding in city: 'РЎР°РЅРєС‚-РџРµС‚РµСЂР±СѓСЂРі'
- row 155, id=c_001128: Broken encoding in city: 'РЎР°РЅРєС‚-РџРµС‚РµСЂР±СѓСЂРі'

### `city_typo` (1)

Typo in city: Санкат-Петербург
- row 22, id=c_001182: Typo in city: Санкат-Петербург

### `filename_vs_schema` (1)

File is named review.csv but columns are company fields (id,name,category,...), not review text/ratings per review
- file-level, id=-: File is named review.csv but columns are company fields (id,name,category,...), not review text/ratings per review

### `phone_garbage` (1)

Phone contains letters: '8 (925) abc-12-34'
- row 28, id=c_001004: Phone contains letters: '8 (925) abc-12-34'

### `phone_incomplete` (1)

Phone is only '+7'
- row 199, id=c_001091: Phone is only '+7'

### `rating_comma_decimal` (1)

rating='4,5'
- row 14, id=c_001010: rating='4,5'

### `rating_na` (1)

rating='N/A'
- row 9, id=c_001083: rating='N/A'

### `reviews_negative` (1)

reviews_count='-10'
- row 61, id=c_001116: reviews_count='-10'

### `site_placeholder` (1)

Non-URL site placeholder: 'нет сайта'
- row 130, id=c_001064: Non-URL site placeholder: 'нет сайта'

### `site_typo_scheme` (1)

Broken URL scheme: 'htp://sintez-service-453.ru'
- row 141, id=c_001020: Broken URL scheme: 'htp://sintez-service-453.ru'

## Что сделал со странными строками

- Все сырые строки положил в `companies_staging`.
- Блокирующие ошибки не пускал в основную таблицу (битый рейтинг/отзывы, мусорный телефон, адрес в поле city, mojibake, пустые строки).
- Мягкие проблемы (хвостовой пробел в городе, English `Moscow`, опечатка `Санкат-Петербург`) оставил в отчете; строку можно импортировать, если остальные поля валидны.

_Автогенерация скриптом `scripts/load_reviews.py`. В БД сохранено аномалий: 40.__
