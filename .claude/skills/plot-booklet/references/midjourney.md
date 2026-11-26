# Ілюстрації

Потрібні дві на буклет:

| файл | пропорції | що на ній |
|---|---|---|
| `art/cover.png` | 2:3 (вертикальна) | центральні персонажі або ключовий образ сюжету |
| `art/inner.png` | 1:1 | конфлікт, ініціюючий інцидент або центральна фігура історії |

Обидві верстка обріже по `object-fit: cover` — головне тримай у центрі кадру.
Титульна ілюстрація задає палітру всього буклета, тож обирай ту, де кольори
виразні й узгоджені. Для християнських сюжетів палітра фіксована, і зображення
на неї не впливає.

## Промпт
Потрібну інформацію для помпту знайдеш у `plot.json`


Збирай так:

```
[сцена: хто, де, що робить], [епоха і сеттінг],
[світло і настрій], oil painting, cinematic composition, muted [домінантний колір] palette
--ar 2:3 --style raw
```

Тримай палітру однією між обома картинками — інакше внутрішня сторінка
випадатиме з кольорів титульної.

## Як їх отримати

### A. Автоматично — через сервіс GptProto

Генерація Midjourney-зображень тепер іде через сервіс **GptProto**
(`https://gptproto.com/model/midjourney/midjourney`)

Приклад запиту до сервісу:
```bash
curl --request POST "https://gptproto.com/api/v3/midjourney/midjourney/text-to-image" \
    --header "Authorization: Bearer $GPTPROTO_API_KEY" \
    --header "Content-Type: application/json" \
    --data '{
        "prompt": "A tiny origami fox sailing a teacup across a moonlit puddle"
    }'
```

Ключ `GPTPROTO_API_KEY` лежить у `.env` - підстав його у запит.
Підстав промпт у значення `"prompt": `
Передай туди готовий промпт (див. вище) і потрібні `--ar`/`--style`; отримане зображення збережи
як `art/cover.png` / `art/inner.png`, за потреби нормалізуй у PNG (`sips -s
format png ...`).


Відповідь на цей запит поверне URL з кодом результату:
```json
{
    "code":200,
    "data":{
        "createdAt":"2026-11-26T15:00:29.599",
        "executionTime":0,
        "hasNsfwContents":[],
        "id":"1795676429690824",
        "model":"Midjourney",
        "outputs":[],
        "status":"created",
        "timings":{"inference":0},
        "urls":{"get":"https://gptproto.com/api/v3/predictions/1795676429690824/result"}},
        "message":"success"
}
```
Якщо `"code"`" не дорівнює `200` або `"message"` не є `"success"` - доповідай користувачу і зупиняйся.

Щоб отримати резутат, звернись за запропонованим посиланням у відповіді: `"urls"` у полі `"get"`:
```bash
curl --request GET "https://gptproto.com/api/v3/predictions/1795676429690824/result" \
    --header "Authorization: Bearer $GPTPROTO_API_KEY"
```
Отримаєш відповідь:
```json
{
  "data": {
    "id": "1795676429690824",
    "model": "Midjourney",
    "outputs": [
      "http://yc4.cn-sy1.rains3.com/attachments/merges/2026/11/26/merged_37cfbb4151b44b16a57533fe258787f1.webp?AWSAccessKeyId=...&Expires=...&Signature=...",
      "https://imagine-cdn.youchuan.cn/0cad1fbf-7278-47a2-a569-23a824a9151c_0_0.png",
      "https://imagine-cdn.youchuan.cn/0cad1fbf-7278-47a2-a569-23a824a9151c_0_1.png",
      "https://imagine-cdn.youchuan.cn/0cad1fbf-7278-47a2-a569-23a824a9151c_0_2.png",
      "https://imagine-cdn.youchuan.cn/0cad1fbf-7278-47a2-a569-23a824a9151c_0_3.png"
    ],
    "urls": {
      "get": "https://gptproto.com/api/v3/predictions/1795676429690824/result"
    },
    "status": "completed",
    "error": null,
    "executionTime": 0,
    "timings": {
      "inference": 0
    },
    "has_nsfw_contents": [],
    "created_at": "2026-11-26T15:00:30",
    "extra_params": {
      "buttons": [
        {
          "emoji": "",
          "style": 2,
          "label": "U1",
          "type": 2,
          "customId": "MJ::JOB::upsample::1::6b07d90d39c8be08dab45c30"
        },
        {
          "emoji": "",
          "style": 2,
          "label": "U2",
          "type": 2,
          "customId": "MJ::JOB::upsample::2::6b07d90d39c8be08dab45c30"
        },
        {
          "emoji": "",
          "style": 2,
          "label": "U3",
          "type": 2,
          "customId": "MJ::JOB::upsample::3::6b07d90d39c8be08dab45c30"
        },
        {
          "emoji": "",
          "style": 2,
          "label": "U4",
          "type": 2,
          "customId": "MJ::JOB::upsample::4::6b07d90d39c8be08dab45c30"
        },
        {
          "emoji": "🔄",
          "style": 2,
          "label": "",
          "type": 2,
          "customId": "MJ::JOB::reroll::0::6b07d90d39c8be08dab45c30::SOLO"
        },
        {
          "emoji": "",
          "style": 2,
          "label": "V1",
          "type": 2,
          "customId": "MJ::JOB::variation::1::6b07d90d39c8be08dab45c30"
        },
        {
          "emoji": "",
          "style": 2,
          "label": "V2",
          "type": 2,
          "customId": "MJ::JOB::variation::2::6b07d90d39c8be08dab45c30"
        },
        {
          "emoji": "",
          "style": 2,
          "label": "V3",
          "type": 2,
          "customId": "MJ::JOB::variation::3::6b07d90d39c8be08dab45c30"
        },
        {
          "emoji": "",
          "style": 2,
          "label": "V4",
          "type": 2,
          "customId": "MJ::JOB::variation::4::6b07d90d39c8be08dab45c30"
        }
      ]
    }
  },
  "message": "success",
  "code": 200
}
```

Тут у параметрі `"outputs"` список посилань:
1. Композиція прев'ю 4 варіантів генерації(2x2).
2. Посилання на малюнок 1 рядок, 1 колонка
3. Посилання на малюнок 1 рядок, 2 колонка
4. Посилання на малюнок 2 рядок, 1 колонка
5. Посилання на малюнок 2 рядок, 2 колонка

Переглянь на прев'ю та перевір за критеріями що нижче та обери найбільш переконливу генерацію і забери її за відповідним посиланням. 
Зенерований малюнок поклади у `out/NAME/art/`і назви її або `cover.png`(якщо це ілюстрація на обкладинку) або `inner.png`(якщо це ілюстрація на сторінку з фактами)

## Перевірки
Обов'язково порахуй персонажів на зображенні - їх кількість має відповідати параметру `characters_count`
Порахуй руки кожного персонажа та пальці
Якщо у людей рук більше 2 або палців на руці більше чи менше 5 - перегенеруй ілюстрацію.
 
### B. Якщо MCP недоступний — заглушка

Скажи користувачу, що автоматична генерація недоступна, і збери буклет із
заглушкою, щоб було видно верстку:

```bash
python3 scripts/placeholder_art.py out/NAME/art/cover.png --ar 2:3 --seed "NAME"
python3 scripts/placeholder_art.py out/NAME/art/inner.png --ar 1:1 --seed "NAME2"
```

Заглушка — тільки для перевірки верстки, у фінальний буклет вона не йде.
Обов'язково попередь, що ілюстрації в PDF тимчасові.
