const $ = s => document.querySelector(s);
let games = [], shown = [], limit = 12, preset = "all", favorites = new Set();
try { favorites = new Set(JSON.parse(localStorage.getItem("board-favorites") || "[]")); } catch {}
const escapeHTML = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const themes = [["#dce4d2","#426245","♧"],["#e8cdb7","#965236","✦"],["#d1dfe1","#3f626f","◈"],["#e9dba5","#8b6831","☀"],["#ded5e5","#775a85","✧"],["#d6ddc5","#5d7045","♜"]];
function theme(g) {return themes[g.id % themes.length];}
function cover(g) {if(g.image_url)return '<div class="cover cover-photo" data-detail="'+g.id+'"><img src="'+escapeHTML(g.image_url)+'" alt="Коробка игры '+escapeHTML(g.game_title)+'" loading="lazy" decoding="async"></div>';const [bg,fg,symbol]=theme(g);return '<div class="cover" style="--cover-bg:'+bg+';--cover-fg:'+fg+'" data-detail="'+g.id+'"><span class="cover-symbol" aria-hidden="true">'+symbol+'</span><span class="cover-number">КОЛЛЕКЦИЯ / '+String(g.id).padStart(3,"0")+'</span></div>';}
function coop(g) {return /^(кооператив|полная кооперац)/i.test((g.level_of_cooperation || "").trim());}
function category(g) {return coop(g) ? "Общая победа" : g.max_players >= 6 ? "Для компании" : g.complexity_of_game >= 6 ? "Время для стратегии" : "За одним столом";}
function time(g) {return g.max_play_time == null ? "—" : g.min_play_time && g.min_play_time !== g.max_play_time ? g.min_play_time+"–"+g.max_play_time : g.max_play_time;}
function reset() {HTMLFormElement.prototype.reset.call($("#filters"));$("#search").value="";$("#sort").value="match";preset="all";render();}
function score(g) {const d=+$("#difficulty").value,p=+$("#players").value;let points=0;if(d && g.complexity_of_game != null) points+=Math.max(0,30-Math.abs(g.complexity_of_game-d)*6);if(p && g.min_recommended_players && p>=g.min_recommended_players && p<=g.max_recommended_players)points+=10;return points;}
function reasons(g) {let a=[];const d=+$("#difficulty").value,p=+$("#players").value;if(p)a.push(p+" игроков подходят");if(d && g.complexity_of_game != null)a.push(Math.abs(g.complexity_of_game-d)<=1?"близко к вашей сложности":"сложность "+g.complexity_of_game+"/9");if($("#minutes").value)a.push("в пределах времени");if($("#rules").value)a.push("правила: "+g.time_for_rules_min+" мин");return a.join(" · ");}
function render() {
  $("#difficulty-value").textContent=$("#difficulty").value==="0"?"Любая":$("#difficulty").value+" / 9";
  document.querySelectorAll("[data-preset]").forEach(b=>b.classList.toggle("selected",b.dataset.preset===preset));
  const p=+$("#players").value,t=+$("#minutes").value,r=+$("#rules").value,q=$("#search").value.trim().toLocaleLowerCase("ru");
  shown=games.filter(g=>(!p || (g.min_players<=p && g.max_players>=p)) && (!t || (g.max_play_time!=null && g.max_play_time<=t)) && (!r || (g.time_for_rules_min != null && g.time_for_rules_min <= r)) && (!$("#available").checked || g.available_now===1) && (!$("#favorites-only").checked || favorites.has(g.id)) && (preset!=="easy" || (g.complexity_of_game!=null && g.complexity_of_game<=3)) && (preset!=="coop" || coop(g)) && (!q || [g.game_title,g.original_title,g.description,g.impression].join(" ").toLocaleLowerCase("ru").includes(q)));
  const sort=$("#sort").value;
  shown.sort((a,b)=>sort==="title"?a.game_title.localeCompare(b.game_title,"ru"):sort==="time"?(a.max_play_time??9999)-(b.max_play_time??9999):sort==="new"?b.id-a.id:score(b)-score(a)||a.game_title.localeCompare(b.game_title,"ru"));
  $("#count").textContent="Найдено: "+shown.length+" из "+games.length;
  $("#empty").hidden=shown.length>0;$("#more").hidden=shown.length<=limit;$("#random").disabled=!shown.length;
  $("#cards").innerHTML=shown.slice(0,limit).map(g=>'<article class="game"><button class="favorite '+(favorites.has(g.id)?"active":"")+'" data-favorite="'+g.id+'" aria-label="'+(favorites.has(g.id)?"Убрать из избранного":"Добавить в избранное")+'" aria-pressed="'+favorites.has(g.id)+'">'+(favorites.has(g.id)?"♥":"♡")+'</button>'+cover(g)+'<div class="game-body"><span class="tag">'+category(g)+'</span><h3><button data-detail="'+g.id+'">'+escapeHTML(g.game_title)+'</button></h3><p class="description">'+escapeHTML(g.description||"Описание скоро появится в каталоге.")+'</p><div class="meta"><span>♙ '+g.min_players+'–'+g.max_players+'</span><span>◷ '+time(g)+' мин</span><span>◈ '+(g.complexity_of_game??"—")+'/9</span></div><div class="rules-meta">Правила: '+(g.time_for_rules_min==null?'время не указано':g.time_for_rules_min+' мин')+'</div>'+(reasons(g)?'<div class="match">'+escapeHTML(reasons(g))+'</div>':"")+'</div></article>').join("");
}
function showDetail(id) {
  const g=games.find(g=>g.id===id);if(!g)return;
  const sources=([g.source_urls,g.image_source].filter(Boolean).join(" | ")).split(/\s*\|\s*/).filter(u=>/^https?:\/\//i.test(u));
  $("#detail-content").innerHTML=cover(g)+'<p class="eyebrow">'+category(g)+'</p><h2>'+escapeHTML(g.game_title)+'</h2><p>'+escapeHTML(g.description||"Описание пока не добавлено.")+'</p><div class="detail-meta"><span>Игроков<strong>'+g.min_players+'–'+g.max_players+'</strong></span><span>Минут на партию<strong>'+time(g)+'</strong></span><span>Сложность<strong>'+(g.complexity_of_game??"—")+' / 9</strong></span></div><p><b>Взаимодействие:</b> '+escapeHTML(g.level_of_cooperation||"Не указано")+'<br><b>Настроение:</b> '+escapeHTML(g.impression||"Не указано")+'<br><b>Объяснение правил:</b> '+(g.time_for_rules_min!=null?g.time_for_rules_min+" мин":"Не указано")+'<br><b>Наличие:</b> '+(g.available_now===1?"В наличии":g.available_now===0?"Нет в наличии":"Нужно уточнить")+'</p>'+sources.map((u,i)=>'<a class="source" target="_blank" rel="noopener noreferrer" href="'+escapeHTML(u)+'">Источник '+(i+1)+' ↗</a>').join("")+'<p class="scale-note">Оценка сложности ориентировочная. У разных изданий параметры могут отличаться.</p>';
  $("#detail").showModal();
}
async function load() {
  try {const response=await fetch("/api/games");const data=await response.json();if(!response.ok)throw Error(data.error);games=data.games;$("#total").textContent=games.length;$("#connection").textContent=data.mode==="mysql"?"● База подключена":"◷ Резервная копия · только просмотр";$("#add-open").disabled=data.mode!=="mysql";$("#error").hidden=true;render();}
  catch(error){$("#error").hidden=false;$("#error").textContent=error.message+" Обновите страницу для повторной попытки.";$("#count").textContent="Каталог недоступен";$("#connection").textContent="Нет подключения";}
}
for(let i=1;i<=20;i++)$("#players").add(new Option(i+" чел.",i));
$("#filters").addEventListener("submit",e=>{e.preventDefault();limit=12;render();});
["players","minutes","rules","difficulty","available","favorites-only","sort"].forEach(id=>$("#"+id).addEventListener("input",()=>{limit=12;render();}));
$("#search").addEventListener("input",()=>{limit=12;render();});
$("#reset").onclick=reset;$("#empty-reset").onclick=reset;
document.querySelectorAll("[data-preset]").forEach(b=>b.onclick=()=>{reset();preset=b.dataset.preset;if(preset==="duo")$("#players").value="2";if(preset==="quick")$("#minutes").value="30";if(preset==="party")$("#players").value="6";if(preset==="easy")$("#difficulty").value="2";render();});
$("#more").onclick=()=>{limit+=12;render();};
$("#random").onclick=()=>{if(shown.length)showDetail(shown[Math.floor(Math.random()*shown.length)].id);};
$("#cards").addEventListener("click",e=>{const fav=e.target.closest("[data-favorite]"),detail=e.target.closest("[data-detail]");if(fav){const id=+fav.dataset.favorite;if(favorites.has(id))favorites.delete(id);else favorites.add(id);try{localStorage.setItem("board-favorites",JSON.stringify([...favorites]));}catch{}render();}else if(detail)showDetail(+detail.dataset.detail);});
document.querySelectorAll("dialog").forEach(d=>{d.querySelector(".close").onclick=()=>d.close();d.addEventListener("click",e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}});});
$("#add-open").onclick=()=>{$("#add-error").textContent="";$("#add-dialog").showModal();};
$("#add-form").addEventListener("submit",async e=>{e.preventDefault();const form=e.target,data=Object.fromEntries(new FormData(form));["min_players","max_players","max_play_time","complexity_of_game"].forEach(k=>data[k]=+data[k]);data.time_for_rules_min=data.time_for_rules_min===""?null:+data.time_for_rules_min;data.available_now=data.available_now===""?null:+data.available_now;const button=form.querySelector("button[type=submit]");button.disabled=true;$("#add-error").textContent="";try{const r=await fetch("/api/games",{method:"POST",headers:{"Content-Type":"application/json","X-Catalogue-Request":"1"},body:JSON.stringify(data)});const result=await r.json();if(!r.ok)throw Error(result.error);$("#add-dialog").close();form.reset();reset();$("#sort").value="new";await load();$("#toast").textContent="Игра добавлена в базу";$("#toast").hidden=false;setTimeout(()=>$("#toast").hidden=true,3500);}catch(err){$("#add-error").textContent=err.message;}finally{button.disabled=false;}});
load();



