const $ = s => document.querySelector(s);
const R = Recommender;
let games = [], shown = [], ranked = [], limit = 12, preset = "all", favorites = new Set(), weights = R.defaults();
try { const saved = JSON.parse(localStorage.getItem("board-favorites") || "[]"); if (Array.isArray(saved)) favorites = new Set(saved.filter(Number.isFinite)); } catch {}
const escapeHTML = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const presets = {
  all:{},
  duo:{players:"2",format:"duel",minutes:"60",mood:"спокойная"},
  quick:{minutes:"30",rules:"5",rulesDifficulty:"2",difficulty:"3"},
  party:{players:"6",genre:"вечериночная",mood:"социальная",rules:"10"},
  easy:{genre:"семейная",difficulty:"2",rulesDifficulty:"1",rules:"5",minutes:"60"},
  coop:{format:"coop",mood:"приключенческая",minutes:"90"},
  strategy:{genre:"стратегическая",difficulty:"7",minutes:"120",mood:"спокойная"}
};
function preferences() {
  return {players:+$("#players").value,minutes:+$("#minutes").value,rules:+$("#rules").value,
    difficulty:+$("#difficulty").value,genre:$("#genre").value,format:$("#format").value,
    mood:$("#mood").value,mechanic:$("#mechanic").value,rulesDifficulty:+$("#rulesDifficulty").value,available:$("#available").checked,
    favorites:$("#favorites-only").checked,search:$("#search").value.trim(),weights};
}
function cover(g) {
  const inner = g.image_url ? '<img src="'+escapeHTML(g.image_url)+'" alt="Коробка игры '+escapeHTML(g.game_title)+'" loading="lazy" decoding="async">' : '<span class="cover-symbol" aria-hidden="true">✳</span><span class="cover-number">КОЛЛЕКЦИЯ / '+String(g.id).padStart(3,"0")+'</span>';
  return '<button type="button" class="cover '+(g.image_url?'cover-photo':'cover-placeholder')+'" data-detail="'+g.id+'" aria-label="Подробнее: '+escapeHTML(g.game_title)+'">'+inner+'</button>';
}
function category(g) {const t=R.profile(g);return t.format ? R.formats[t.format] : "Коллекция клуба";}
function time(g) {return g.max_play_time == null ? "—" : g.min_play_time && g.min_play_time !== g.max_play_time ? g.min_play_time+"–"+g.max_play_time : g.max_play_time;}
function decimal(n) {return new Intl.NumberFormat("ru",{maximumFractionDigits:1}).format(n);}
function reset(shouldRender=true) {
  HTMLFormElement.prototype.reset.call($("#filters"));
  weights=R.defaults();syncWeights();$("#search").value="";$("#sort").value="match";preset="all";limit=12;
  if(shouldRender)render();
}
function syncWeights() {
  for(const key of Object.keys(R.criteria)) {
    const input=$("#weight-"+key),output=$("#weight-value-"+key);
    input.value=weights[key];output.value=weights[key];
  }
}
function changed() {preset="custom";limit=R.activeKeys(preferences()).length?6:12;render();}
function highlights(item) {return item.parts.filter(p=>p.fit>=0.75).sort((a,b)=>b.points-a.points).slice(0,2);}
function matchMarkup(item) {
  if(item.percent===null)return "";
  return '<div class="match-meter"><span>Соответствие</span><strong>'+item.percent+'%</strong><div class="meter-track"><span style="width:'+item.percent+'%"></span></div></div>';
}
function render() {
  const p=preferences(),active=R.activeKeys(p),matching=active.length>0;
  $("#difficulty-value").textContent=p.difficulty?p.difficulty+" / 9":"Любая";
  document.querySelectorAll("[data-preset]").forEach(b=>{const selected=b.dataset.preset===preset;b.classList.toggle("selected",selected);b.setAttribute("aria-pressed",String(selected));});
  for(const key of Object.keys(R.criteria))$("#weight-"+key).closest("label").classList.toggle("weight-inactive",!p[key]);
  ranked=R.rank(games,p,favorites);
  let display=[...ranked],sort=$("#sort").value;
  if(sort==="title")display.sort((a,b)=>a.game.game_title.localeCompare(b.game.game_title,"ru"));
  if(sort==="time")display.sort((a,b)=>(a.game.max_play_time??Infinity)-(b.game.max_play_time??Infinity)||b.total-a.total);
  if(sort==="new")display.sort((a,b)=>b.game.id-a.game.id);
  shown=display.map(item=>item.game);
  const visible=Math.min(limit,shown.length),excluded=games.length-shown.length;
  $("#count").textContent=matching ? "Показываем "+visible+" из "+shown.length+" вариантов · по вашим пожеланиям" : "В коллекции "+shown.length+" игр";
  if(excluded)$("#count").textContent+=" · "+excluded+" не вмещают компанию";
  $("#selection-summary").hidden=!matching;
  $("#ranking-note").hidden=!matching;
  $("#active-filters").replaceChildren(...active.map(key=>{
    const chip=document.createElement("span");chip.className="filter-chip";
    const labels={players:p.players+" игроков",minutes:"Партия до "+p.minutes+" мин",rules:"Объяснение до "+p.rules+" мин",rulesDifficulty:"Правила до "+p.rulesDifficulty+"/5",difficulty:"Сложность игры "+p.difficulty+"/9",genre:R.genres[p.genre],format:R.formats[p.format],mood:R.moods[p.mood],mechanic:R.mechanics[p.mechanic],available:"В наличии",favorites:"Избранное",search:"Поиск: "+p.search};
    chip.textContent=labels[key];return chip;
  }));
  const best=ranked[0],hero=$("#best-pick");
  hero.hidden=!matching||!best||sort!=="match";
  if(!hero.hidden) {
    const positive=highlights(best),message=best.total===0?"Точных совпадений нет. Это ближайший вариант; посмотрите, чем он отличается.":best.warnings.length?best.warnings.join(". "):positive.map(p=>p.text).join(" · ");
    hero.classList.toggle("best-caution",best.warnings.length>0||best.total===0);
    hero.innerHTML='<div><p class="eyebrow">'+(best.total===0?"БЛИЖАЙШИЙ ВАРИАНТ":best.warnings.length?"ЛУЧШЕ ПО БАЛЛАМ · ЕСТЬ ОГОВОРКА":"НАШ ВЫБОР ДЛЯ ВАС")+'</p><button data-detail="'+best.game.id+'" class="best-title">'+escapeHTML(best.game.game_title)+' <span>↗</span></button><p>'+escapeHTML(message)+'</p></div><div class="best-score"><strong>'+best.percent+'<small>%</small></strong><span>соответствие</span></div>';
  }
  $("#empty").hidden=shown.length>0;$("#more").hidden=shown.length<=limit;$("#random").disabled=!shown.length;
  $("#more").textContent="Ещё варианты ("+Math.max(0,shown.length-visible)+") ↓";
  $("#cards").innerHTML=display.slice(0,limit).map(item=>{
    const g=item.game,positive=highlights(item),mismatch=item.parts.find(part=>part.fit<0.75);
    return '<article class="game"><button class="favorite '+(favorites.has(g.id)?"active":"")+'" data-favorite="'+g.id+'" aria-label="'+(favorites.has(g.id)?"Убрать из избранного":"Добавить в избранное")+'" aria-pressed="'+favorites.has(g.id)+'">'+(favorites.has(g.id)?"♥":"♡")+'</button>'+cover(g)+'<div class="game-body"><span class="tag">'+escapeHTML(category(g))+'</span><h3><button data-detail="'+g.id+'">'+escapeHTML(g.game_title)+'</button></h3><div class="genre-tags">'+item.tags.genres.slice(0,2).map(t=>'<span>'+escapeHTML(R.genres[t]||t)+'</span>').join("")+'</div><p class="description">'+escapeHTML(g.description||"Описание скоро появится в каталоге.")+'</p><div class="meta"><span title="Игроки">♙ '+(g.min_players??"?")+'–'+(g.max_players??"?")+'</span><span title="Время партии">◷ '+time(g)+' мин</span><span title="Сложность">◈ '+(g.complexity_of_game??"—")+'/9</span></div><div class="rules-meta">Правила: '+(g.time_for_rules_min==null?'время неизвестно':g.time_for_rules_min+' мин')+'</div>'+matchMarkup(item)+(positive.length?'<p class="match">'+positive.map(part=>'✓ '+escapeHTML(part.text)).join("<br>")+'</p>':"")+(item.warnings.length?'<p class="match-warning">'+escapeHTML(item.warnings.join(". "))+'</p>':mismatch?'<p class="match-difference">'+escapeHTML(mismatch.text)+'</p>':"")+'<button class="card-link" data-detail="'+g.id+'">'+(matching?"Почему подходит":"Об игре")+' <span>↗</span></button></div></article>';
  }).join("");
}
function showDetail(id) {
  const g=games.find(g=>g.id===id);if(!g)return;
  const item=R.evaluate(g,preferences(),favorites),tags=R.profile(g);
  const sources=([g.source_urls,g.image_source].filter(Boolean).join(" | ")).split(/\s*\|\s*/).filter(u=>/^https?:\/\//i.test(u));
  const breakdown=item?.parts.length?'<section class="score-breakdown"><h3>Почему '+item.percent+'%?</h3><p>Баллы за каждый критерий складываются: <b>'+decimal(item.total)+' из '+decimal(item.possible)+'</b>. Результат делится на сумму весов и переводится в проценты.</p>'+item.parts.map(part=>'<div class="score-row"><div><strong>'+part.label+'</strong><small>'+escapeHTML(part.text)+'</small></div><span>'+decimal(part.points)+' / '+part.weight+'</span></div>').join("")+'</section>':"";
  const facts = [
    ["Жанры",tags.genres.map(t=>R.genres[t]||t).join(", ")||"В базе не указаны"],
    ["Механики",tags.mechanics.map(t=>R.mechanics[t]||t).join(", ")||"В базе не указаны"],
    ["Уровень кооперации",g.level_of_cooperation||"В базе не указан"],
    ["Впечатления",g.impression||"В базе не указаны"],
    ["Объяснение правил",g.time_for_rules_min!=null?g.time_for_rules_min+" мин":"В базе не указано"],
    ["Наличие",g.available_now===1?"В наличии":g.available_now===0?"Нет в наличии":"Нужно уточнить"]
  ];
  const numbers = [
    ["Игроков",(g.min_players??"?")+"–"+(g.max_players??"?")],
    ["Минут на партию",time(g)],
    ["Сложность игры",(g.complexity_of_game??"—")+" / 9"],
    ["Сложность правил",(g.rules_difficulty??"—")+" / 5"]
  ];
  $("#detail-content").innerHTML=cover(g)+'<p class="eyebrow">'+escapeHTML(category(g))+'</p><h2 id="detail-title">'+escapeHTML(g.game_title)+'</h2>'
    +(item?.warnings.length?'<p class="match-warning">'+escapeHTML(item.warnings.join(". "))+'</p>':"")
    +'<p>'+escapeHTML(g.description||"Описание пока не добавлено.")+'</p>'
    +'<div class="detail-meta">'+numbers.map(([label,value])=>'<span>'+label+'<strong>'+escapeHTML(value)+'</strong></span>').join("")+'</div>'
    +'<p>'+facts.map(([label,value])=>'<b>'+label+':</b> '+escapeHTML(value)).join("<br>")+'</p>'+breakdown
    +sources.map((u,i)=>'<a class="source" target="_blank" rel="noopener noreferrer" href="'+escapeHTML(u)+'">Источник '+(i+1)+' ↗</a>').join("")
    +'<p class="scale-note">Характеристики взяты из базы клуба. Сложность игры и сложность правил — разные оценки. У разных изданий параметры могут отличаться.</p>';
  if(!$("#detail").open)$("#detail").showModal();
}

async function load() {
  $("#random").disabled=true;
  try {
    const response=await fetch("/api/games");const data=await response.json();if(!response.ok)throw Error(data.error);
    if(!Array.isArray(data.games))throw Error("Не удалось прочитать каталог.");
    games=data.games;R.configure(games);populateChoices();$("#total").textContent=games.length;
    $("#connection").textContent=data.mode==="mysql"?"● Коллекция клуба онлайн":"◷ Резервная копия · только просмотр";
    $("#add-open").disabled=data.mode!=="mysql";$("#error").hidden=true;render();
  } catch(error) {
    $("#error").hidden=false;$("#error").textContent=error.message+" Обновите страницу для повторной попытки.";
    $("#count").textContent="Каталог недоступен";$("#connection").textContent="Нет подключения";
  }
}
for(let i=1;i<=20;i++)$("#players").add(new Option(i+" чел.",i));
function populateChoices() {
  for(const [id,options] of [["genre",R.genres],["format",R.formats],["mood",R.moods],["mechanic",R.mechanics]]) {
    const select=$("#"+id),previous=select.value;
    while(select.options.length>1)select.remove(1);
    const entries=Object.entries(options);
    if(id!=="format")entries.sort((a,b)=>a[1].localeCompare(b[1],"ru"));
    for(const [key,label] of entries)select.add(new Option(label,key));
    if([...select.options].some(option=>option.value===previous))select.value=previous;
  }
}
$("#weights").innerHTML=Object.entries(R.criteria).map(([key,c])=>'<label for="weight-'+key+'">'+c.label+'<output id="weight-value-'+key+'" for="weight-'+key+'">'+c.weight+'</output><input id="weight-'+key+'" data-weight="'+key+'" type="range" min="0" max="50" value="'+c.weight+'"></label>').join("");
$("#weights").addEventListener("input",e=>{if(!e.target.dataset.weight)return;weights[e.target.dataset.weight]=+e.target.value;$("#weight-value-"+e.target.dataset.weight).value=e.target.value;changed();});
$("#weights-reset").onclick=()=>{weights=R.defaults();syncWeights();changed();};
$("#filters").addEventListener("submit",e=>{e.preventDefault();limit=R.activeKeys(preferences()).length?6:12;render();$("#best-pick").hidden?$("#count").scrollIntoView({block:"nearest"}):$("#best-pick").scrollIntoView({block:"nearest"});});
["players","minutes","rules","rulesDifficulty","difficulty","genre","format","mood","mechanic","available","favorites-only"].forEach(id=>$("#"+id).addEventListener("input",changed));
$("#sort").addEventListener("change",()=>{limit=R.activeKeys(preferences()).length?6:12;render();});
$("#search").addEventListener("input",changed);
$("#reset").onclick=()=>reset();$("#empty-reset").onclick=()=>reset();
document.querySelectorAll("[data-preset]").forEach(b=>b.onclick=()=>{
  reset(false);preset=b.dataset.preset;
  for(const [key,value] of Object.entries(presets[preset]))$("#"+key).value=value;
  limit=preset==="all"?12:6;render();
});
$("#more").onclick=()=>{limit+=6;render();};
$("#random").onclick=()=>{
  if(!ranked.length)return;
  const candidates=R.activeKeys(preferences()).length?ranked.slice(0,3):ranked;
  showDetail(candidates[Math.floor(Math.random()*candidates.length)].game.id);
};
$(".results").addEventListener("click",e=>{
  const fav=e.target.closest("[data-favorite]"),detail=e.target.closest("[data-detail]");
  if(fav) {
    const id=+fav.dataset.favorite;favorites.has(id)?favorites.delete(id):favorites.add(id);
    try{localStorage.setItem("board-favorites",JSON.stringify([...favorites]));}catch{}
    render();
  } else if(detail)showDetail(+detail.dataset.detail);
});
document.querySelectorAll("dialog").forEach(d=>{
  d.querySelector(".close").onclick=()=>d.close();
  d.addEventListener("click",e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}});
});
$("#add-open").onclick=()=>{$("#add-error").textContent="";$("#add-dialog").showModal();};
$("#add-form").addEventListener("submit",async e=>{
  e.preventDefault();const form=e.target,data=Object.fromEntries(new FormData(form));
  ["min_players","max_players","max_play_time","complexity_of_game"].forEach(k=>data[k]=+data[k]);
  data.time_for_rules_min=data.time_for_rules_min===""?null:+data.time_for_rules_min;data.available_now=data.available_now===""?null:+data.available_now;
  const button=form.querySelector("button[type=submit]");button.disabled=true;$("#add-error").textContent="";
  try {
    const r=await fetch("/api/games",{method:"POST",headers:{"Content-Type":"application/json","X-Catalogue-Request":"1"},body:JSON.stringify(data)});
    const result=await r.json();if(!r.ok)throw Error(result.error);
    $("#add-dialog").close();form.reset();reset();$("#sort").value="new";await load();
    $("#toast").textContent="Игра добавлена в базу";$("#toast").hidden=false;setTimeout(()=>$("#toast").hidden=true,3500);
  }catch(err){$("#add-error").textContent=err.message;}finally{button.disabled=false;}
});
load();
