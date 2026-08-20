import os
from decimal import Decimal

import mysql.connector
from mysql.connector import Error
import streamlit as st


st.set_page_config(
    page_title="A_Fun_Game",
    page_icon="🎲",
    layout="centered",
)


# -------------------------
# Подключение к базе данных
# -------------------------

def get_db_config():
    """Берём настройки из Streamlit Secrets, а локально — из переменных окружения."""
    try:
        mysql_secrets = st.secrets["mysql"]
        return {
            "host": mysql_secrets["host"],
            "port": int(mysql_secrets.get("port", 3306)),
            "user": mysql_secrets["user"],
            "password": mysql_secrets["password"],
            "database": mysql_secrets["database"],
        }
    except Exception:
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "mda_board"),
        }


def fetch_games(players):
    """Возвращает игры, которые физически поддерживают выбранное число игроков."""
    connection = None
    cursor = None

    try:
        connection = mysql.connector.connect(**get_db_config())
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                game_title,
                min_players,
                max_players,
                min_recommended_players,
                max_recommended_players,
                complexity_of_game,
                rules_difficulty,
                min_play_time,
                max_play_time,
                time_for_rules_min
            FROM games
            WHERE min_players <= %s
              AND max_players >= %s
            """,
            (players, players),
        )

        return cursor.fetchall()

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


# -------------------------
# Алгоритм рекомендации
# -------------------------

def score_game(game, players, complexity, play_time, rules_difficulty, rules_time):
    """Логика перенесена из test_mysql.py."""
    score = 0
    reasons = []

    # 1. Рекомендованное количество игроков
    min_rec = game["min_recommended_players"]
    max_rec = game["max_recommended_players"]

    if min_rec is not None and max_rec is not None and min_rec <= players <= max_rec:
        score += 3
        reasons.append("подходит для вашей компании")

    # 2. Сложность игры
    game_complexity = game["complexity_of_game"]

    if game_complexity is not None:
        complexity_difference = abs(Decimal(game_complexity) - Decimal(complexity))

        if complexity_difference == 0:
            score += 4
            reasons.append("идеальное совпадение по сложности")
        elif complexity_difference == 1:
            score += 2
            reasons.append("близкая сложность")

    # 3. Время партии
    max_play_time = game["max_play_time"]

    if max_play_time is not None and max_play_time <= play_time:
        difference = play_time - max_play_time

        if difference <= 10:
            score += 3
            reasons.append("идеально подходит по времени")
        else:
            score += 2
            reasons.append("укладывается в ваше время")

    # 4. Сложность правил
    game_rules_difficulty = game["rules_difficulty"]

    if game_rules_difficulty is not None:
        rules_difference = abs(game_rules_difficulty - rules_difficulty)

        if rules_difference == 0:
            score += 3
            reasons.append("подходит по сложности правил")
        elif rules_difference == 1:
            score += 1

    # 5. Время изучения правил
    time_for_rules = game["time_for_rules_min"]

    if time_for_rules is not None and time_for_rules <= rules_time:
        score += 2
        reasons.append("быстрое объяснение правил")

    game["score"] = score
    game["reasons"] = reasons
    return game


def recommend_games(games, players, complexity, play_time, rules_difficulty, rules_time):
    scored_games = [
        score_game(
            game,
            players,
            complexity,
            play_time,
            rules_difficulty,
            rules_time,
        )
        for game in games
    ]

    # Как в исходном test_mysql.py: сортировка по сумме баллов.
    scored_games.sort(key=lambda game: game["score"], reverse=True)
    return scored_games[:5]


# -------------------------
# Интерфейс
# -------------------------

st.title("🎲 A_Fun_Game")
st.write("Подберём настольную игру под вашу компанию и желаемый формат вечера.")

with st.form("recommendation_form"):
    st.caption("Минимум: 1 • Максимум: 12")

    players = st.slider(
        "👥 Сколько вас будет играть?",
        min_value=1,
        max_value=12,
        value=4,
)

    complexity = st.slider(
        "🧠 Какую сложность игры хотите?",
        min_value=1,
        max_value=10,
        value=5,
    )

    play_time = st.slider(
        "⏱ Сколько максимум минут вы готовы играть?",
        min_value=10,
        max_value=300,
        value=60,
        step=10,
    )

    rules_difficulty = st.slider(
        "📖 Какую сложность правил готовы изучать?",
        min_value=1,
        max_value=5,
        value=3,
    )

    rules_time = st.slider(
        "⏱ Сколько минут готовы изучать правила?",
        min_value=5,
        max_value=60,
        value=15,
        step=5,
    )

    submitted = st.form_submit_button(
        "🎯 Подобрать игру",
        use_container_width=True,
    )


if submitted:
    try:
        games = fetch_games(players)
    except Error as error:
        st.error("Не удалось подключиться к базе данных.")
        st.caption(
            "Проверьте настройки MySQL в Streamlit Secrets или переменных окружения. "
            f"Техническая информация: {error}"
        )
        st.stop()

    st.header("🏆 Рекомендации")

    if not games:
        st.warning("Для такого количества игроков игр пока не найдено.")
    else:
        recommendations = recommend_games(
            games,
            players,
            complexity,
            play_time,
            rules_difficulty,
            rules_time,
        )

        for number, game in enumerate(recommendations, start=1):
            with st.container(border=True):
                st.subheader(f"{number}. {game['game_title']}")
                st.metric("Совпадение", f"{game['score']} баллов")

                if game["reasons"]:
                    st.write("**Почему рекомендуем:** " + ", ".join(game["reasons"]) + ".")
                else:
                    st.write("**Почему рекомендуем:** игра подходит по числу игроков, но по остальным параметрам совпадение слабое.")

                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"👥 Игроки: {game['min_players']}–{game['max_players']}")
                    if (
                        game["min_recommended_players"] is not None
                        and game["max_recommended_players"] is not None
                    ):
                        st.write(
                            "👍 Лучше всего: "
                            f"{game['min_recommended_players']}–{game['max_recommended_players']}"
                        )
                    st.write(f"🧠 Сложность: {game['complexity_of_game']}/10")

                with col2:
                    st.write(
                        f"⏱ Партия: {game['min_play_time']}–{game['max_play_time']} мин."
                    )
                    st.write(f"📖 Сложность правил: {game['rules_difficulty']}/5")
                    st.write(f"🕐 Изучение правил: ~{game['time_for_rules_min']} мин.")