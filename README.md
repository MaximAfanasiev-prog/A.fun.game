# A.fun.game

## 🌐 Сайт

Публичный каталог: https://maximafanasiev-prog.github.io/A.fun.game/

Предыдущая Streamlit-версия: https://a-fun-game.streamlit.app/

Текущий каталог находится в `catalogue/`: 72 игры, обложки, поиск, фильтры,
избранное и случайный выбор. GitHub Pages публикует каталог в режиме просмотра.
Для обновления данных измените `catalogue/data/catalogue.json` и отправьте изменения
в `main`; workflow `Publish catalogue` пересоберёт и опубликует сайт.

Локальный запуск: `cd catalogue`, `pip install -r requirements.txt`,
`python -B app.py --open`. Для подключения MySQL задайте `MYSQL_HOST`,
`MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` в окружении. Пароли не хранятся
в репозитории. Без MySQL используется сохранённый каталог.

Локальная сборка публичной версии: `python catalogue/build_public.py`.
В настройках репозитория **Pages → Source** выберите **GitHub Actions**.

## About the project
A.fun.game is a board game discovery and recommendation platform designed to help groups find the perfect game for their gaming session.
The main idea is not just to create a board game catalog, but to help users choose a game based on their specific situation and preferences

If you can answer these questions:
- How many people are playing?
- Are you beginners or experienced players?
- How much time do you have?
- Do you want cooperation, competition or a party game?
- What type of experience are you looking for?
  And so on...
My system analyzes these preferences and recommends suitable board games, explaining why each game matches your group.

## Features (planned)

- Advanced board game search
- Recommendation system based on player preferences
- Game mechanics and genre analysis
- Rules overview for quick start
- Detailed information about game features and mechanics
- Ability to see examples of other players' game sessions
## Goal
The goal of this project is to build a complete recommendation system using real data, SQL database design, Python analysis and a web interface.
## Status
 Work in progress :)
