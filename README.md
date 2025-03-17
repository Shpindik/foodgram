Проект [Foodgram](https://foodgramya.webhop.me/) позволяет пользователям
создавать кулинарные рецепты, скачивать списки продуктов, необходимых для
приготовления блюд, подписываться на других пользователей и сохранять
рецепты в избранное.

#### Технологии изпользовавшиеся в разработке проекта:

- Django
- DRF
- Djoser
- PostgreSQL
- Nginx
- Gunicorn
- Docker

### Запуск проекта

#### 1. Клонирование репозитория

```bash
git clone https://github.com/Shpindik/foodgram
cd foodgram
```

#### 2. Настройка переменных окружения

Создайте файл `.env` в корневой директории и укажите настройки:

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres
DB_HOST=db
DB_PORT=5432
SECRET_KEY='Сгенерированный Secret key django' 
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1  # Для сервера укажите домен или IP
CSRF_TRUSTED_ORIGINS=localhost, #Домен вашего сервера или IP
```

#### 3. Запуск контейнеров

```bash
docker-compose up -d --build
```

#### 4. Применяем миграции и собираем статику

```bash
docker-compose exec backend python manage.py makemigrations
```
```bash
docker-compose exec backend python manage.py migrate
```
```bash
docker-compose exec backend python manage.py collectstatic --no-input
```

#### 5. Загружаем ингредиенты и теги в базу

```bash
docker-compose exec backend python manage.py load_tags tags.json
```
```bash
docker-compose exec backend python manage.py load_ingredients ingredients.json
```

#### 6. Примеры API-запросов
- Получение списка пользователей
> Request:
```
[GET] /api/users/
```
> Response:
```json
{
  "count": 123,
  "next": "http://foodgram.example.org/api/users/?page=4",
  "previous": "http://foodgram.example.org/api/users/?page=2",
  "results": [
    {
      "email": "user@example.com",
      "id": 0,
      "username": "string",
      "first_name": "Вася",
      "last_name": "Иванов",
      "is_subscribed": false,
      "avatar": "http://foodgram.example.org/media/users/image.png"
    }
  ]
}
```
- Получение списка рецептов
> Request:
```
[GET] /api/recipes/
```
> Response:
```json
{
  "count": 123,
  "next": "http://foodgram.example.org/api/recipes/?page=4",
  "previous": "http://foodgram.example.org/api/recipes/?page=2",
  "results": [
    {
      "id": 0,
      "tags": [
        {
          "id": 0,
          "name": "Завтрак",
          "slug": "breakfast"
        }
      ],
      "author": {
        "email": "user@example.com",
        "id": 0,
        "username": "string",
        "first_name": "Вася",
        "last_name": "Иванов",
        "is_subscribed": false,
        "avatar": "http://foodgram.example.org/media/users/image.png"
      },
      "ingredients": [
        {
          "id": 0,
          "name": "Картофель отварной",
          "measurement_unit": "г",
          "amount": 1
        }
      ],
      "is_favorited": true,
      "is_in_shopping_cart": true,
      "name": "string",
      "image": "http://foodgram.example.org/media/recipes/images/image.png",
      "text": "string",
      "cooking_time": 1
    }
  ]
}
```
- Добавить рецепт в избранное
> Request:
```
[POST] /api/recipes/{id}/favorite/
```
> Response:
```json
{
  "id": 0,
  "name": "string",
  "image": "http://foodgram.example.org/media/recipes/images/image.png",
  "cooking_time": 1
}
```


Автор проекта: [Александр (Shpindik) Прокофьев](https://github.com/Shpindik)

