/* Pure recommendation model shared by the browser and regression checks. */
(function (root) {
  "use strict";
  const criteria = {
    players: {label: "Состав компании", weight: 20},
    genre: {label: "Жанр", weight: 24},
    format: {label: "Формат", weight: 22},
    minutes: {label: "Время партии", weight: 14},
    difficulty: {label: "Сложность игры", weight: 12},
    rules: {label: "Объяснение правил", weight: 8},
    rulesDifficulty: {label: "Сложность правил", weight: 10},
    mood: {label: "Впечатление", weight: 10},
    mechanic: {label: "Механика", weight: 8},
    available: {label: "Наличие в клубе", weight: 6},
    favorites: {label: "Избранное", weight: 6},
    search: {label: "Поисковый запрос", weight: 30}
  };
  // Choice lists are populated from actual catalogue values, never game titles.
  const genres = {}, moods = {}, mechanics = {};
  const formats = {competitive:"Каждый за себя", coop:"Кооператив", teams:"Команда против команды", semi:"Полукооператив", duel:"Дуэль"};
  function terms(value) {
    return (Array.isArray(value) ? value : typeof value === "string" ? [value] : [])
      .flatMap(item => typeof item === "string" ? item.split(";") : [])
      .map(item => item.trim().replace(/\s+/g," ")).filter(Boolean);
  }
  function genreTerms(game) {const list=terms(game.genres);return list.length?list:terms(game.genre);}
  function profile(game) {
    const cooperation=norm(game.level_of_cooperation);
    let format=null;
    if (/полукоопера|частичн.*коопера/.test(cooperation)) format="semi";
    else if (/командн.*(?:противосто|соревн)|команда против команды/.test(cooperation)) format="teams";
    else if (/^(?:полная коопера|кооператив|кооперация)/.test(cooperation)) format="coop";
    else if (/соревн|противосто|конкурен/.test(cooperation)) format="competitive";
    if (format==="competitive" && (/двух игроков|двух игрок|дуэл/.test(cooperation) || (game.min_players===2 && game.max_players===2))) format="duel";
    return {
      genres:[...new Set(genreTerms(game).map(norm))],
      format,
      moods:[...new Set(terms(game.impression).map(norm))],
      mechanics:[...new Set(terms(game.mechanics).map(norm))]
    };
  }
  function configure(games) {
    for(const list of [genres,moods,mechanics])for(const key of Object.keys(list))delete list[key];
    for(const game of games) {
      for(const [list,values] of [[genres,genreTerms(game)],[moods,terms(game.impression)],[mechanics,terms(game.mechanics)]]) {
        for(const value of values) {
          const key=norm(value);
          if(!list[key])list[key]=value.charAt(0).toLocaleUpperCase("ru")+value.slice(1);
        }
      }
    }
  }
  const label = (list, key) => list[key] || key;
  function choices(value) {
    return [...new Set((Array.isArray(value) ? value : [value]).filter(v=>typeof v==="string").map(norm).filter(Boolean))];
  }
  function hasPreference(value) {return Array.isArray(value) ? choices(value).length>0 : Boolean(value);}

  function defaults() {return Object.fromEntries(Object.entries(criteria).map(([key, c]) => [key, c.weight]));}
  function activeKeys(preferences) {
    return Object.keys(criteria).filter(key => hasPreference(preferences[key]) && Number(preferences.weights?.[key] ?? criteria[key].weight) > 0);
  }
  const known = value => value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
  const norm = value => String(value ?? "").toLocaleLowerCase("ru").replace(/ё/g,"е").replace(/\s+/g," ").trim();
  function evaluate(game, preferences, favorites = new Set()) {
    const p = preferences, tags = profile(game), parts = [], warnings = [];
    // The only hard exclusion: explicitly known maximum player count exceeded.
    if (p.players && known(game.max_players) && +p.players > +game.max_players) return null;
    if (p.players && known(game.min_players) && +p.players < +game.min_players) warnings.push("Нужно минимум " + game.min_players + " игроков — вас меньше");
    if (p.players && !known(game.max_players)) warnings.push("Максимум игроков не указан — уточните перед партией");
    function add(key, fit, text) {
      if (!hasPreference(p[key])) return;
      const weight = Math.max(0, Number(p.weights?.[key] ?? criteria[key].weight) || 0);
      if (!weight) return;
      const unknown = fit == null;
      // Missing data gets zero points and an explicit explanation, never a match.
      const ratio = unknown ? 0 : Math.max(0, Math.min(1, fit));
      parts.push({key, label:criteria[key].label, weight, fit:ratio, points:ratio * weight, unknown, text});
    }
    if (p.players) {
      let fit = null, text = "Диапазон игроков неизвестен";
      if (known(game.min_players) && known(game.max_players)) {
        const within = +p.players >= +game.min_players;
        const recommended = known(game.min_recommended_players) && known(game.max_recommended_players);
        fit = !within ? Math.max(0, 0.3 - (game.min_players - p.players) * 0.1) : !recommended || (+p.players >= +game.min_recommended_players && +p.players <= +game.max_recommended_players) ? 1 : 0.75;
        text = !within ? "Вас меньше минимума: нужно " + game.min_players : fit === 1 ? "Подходит для " + p.players + " игроков" : "Можно играть; рекомендовано " + game.min_recommended_players + "–" + game.max_recommended_players;
      }
      add("players", fit, text);
    }
    function addChoices(key, available, names, caption) {
      const selected=choices(p[key]), matched=selected.filter(value=>available.includes(value));
      const description=!available.length ? caption+" в базе не указаны"
        : selected.length===1 ? matched.length ? caption+": "+label(names,matched[0]) : "Другие "+caption.toLocaleLowerCase("ru")+": "+available.map(value=>label(names,value)).join(", ")
        : caption+": совпало "+matched.length+" из "+selected.length+(matched.length?" · "+matched.map(value=>label(names,value)).join(", "):" · у игры: "+available.map(value=>label(names,value)).join(", "));
      add(key,available.length && selected.length ? matched.length/selected.length : null,description);
    }
    addChoices("genre",tags.genres,genres,"Жанры");
    add("format", tags.format ? Number(tags.format === p.format || (p.format === "competitive" && tags.format === "duel")) : null, tags.format ? "Формат: " + formats[tags.format] : game.level_of_cooperation ? "Формат не определён: " + game.level_of_cooperation : "Кооперация в базе не указана");
    for (const [key, field, label] of [["minutes","max_play_time","Партия"],["rules","time_for_rules_min","Правила"]]) {
      const value = game[field], target = +p[key];
      add(key, known(value) ? +value <= target ? 1 : target / +value : null, known(value) ? label + ": " + value + " мин" + (+value > target ? " — дольше желаемого" : " — укладывается") : label + ": время неизвестно");
    }
    add("difficulty", known(game.complexity_of_game) ? 1 - Math.abs(game.complexity_of_game - p.difficulty) / 8 : null, known(game.complexity_of_game) ? "Сложность " + game.complexity_of_game + "/9 (вы выбрали " + p.difficulty + ")" : "Сложность неизвестна");
    add("rulesDifficulty", known(game.rules_difficulty) ? 1 - Math.max(0, game.rules_difficulty - p.rulesDifficulty) / 4 : null, known(game.rules_difficulty) ? "Сложность правил " + game.rules_difficulty + "/5" + (game.rules_difficulty > p.rulesDifficulty ? " — сложнее желаемого" : " — подходит") : "Сложность правил в базе не указана");
    add("mood", tags.moods.length ? Number(tags.moods.includes(p.mood)) : null, tags.moods.length ? tags.moods.includes(p.mood) ? "Впечатление: " + label(moods,p.mood) : "Другие впечатления: " + tags.moods.map(m=>label(moods,m)).join(", ") : "Впечатления в базе не указаны");
    addChoices("mechanic",tags.mechanics,mechanics,"Механики");
    add("available", known(game.available_now) ? Number(+game.available_now === 1) : null, +game.available_now === 1 ? "В наличии в клубе" : game.available_now === 0 ? "Сейчас нет в наличии" : "Наличие нужно уточнить");
    add("favorites", Number(favorites.has(game.id)), favorites.has(game.id) ? "В вашем избранном" : "Пока не в избранном");
    if (p.search) {
      const query = norm(p.search), title = norm(game.game_title + " " + (game.original_title || ""));
      const haystack = norm([title, game.description, game.impression, game.level_of_cooperation, ...tags.genres, ...tags.mechanics, formats[tags.format]].join(" "));
      const tokens = query.split(/\s+/).filter(Boolean);
      const fit = title.includes(query) ? 1 : haystack.includes(query) ? 0.8 : tokens.filter(t=>haystack.includes(t)).length / tokens.length * 0.6;
      add("search", fit, fit === 1 ? "Совпадение в названии" : fit > 0 ? "Совпадение по описанию" : "Не совпадает с поиском");
    }
    const total = parts.reduce((n,c)=>n+c.points,0), possible = parts.reduce((n,c)=>n+c.weight,0);
    return {game, tags, parts, warnings, total, possible, percent:possible ? Math.round(total / possible * 100) : null};
  }
  function rank(games, preferences, favorites) {
    return games.map(g=>evaluate(g, preferences, favorites)).filter(Boolean).sort((a,b)=>b.total-a.total || a.game.game_title.localeCompare(b.game.game_title,"ru") || a.game.id-b.game.id);
  }
  root.Recommender = {criteria, genres, formats, moods, mechanics, configure, profile, defaults, activeKeys, choices, hasPreference, evaluate, rank};
  if (typeof module !== "undefined" && module.exports) module.exports = root.Recommender;
})(typeof globalThis === "undefined" ? window : globalThis);
