"use strict";

const episodes = [
  { id: "rainbow", title: "무지개 과일 샐러드" },
  { id: "sandwich", title: "무지개 샌드위치" },
  { id: "bubbles", title: "비눗방울 소동" },
  { id: "red-ball", title: "사라진 빨간 공" },
  { id: "number-friends", title: "안녕, 넘버랜드!" },
];

const slotsPerPage = 6;
const pageCount = Math.max(1, Math.ceil(episodes.length / slotsPerPage));
const sheets = document.querySelector("#sheets");
const previous = document.querySelector("#previous");
const next = document.querySelector("#next-page");
const counter = document.querySelector("#counter");
let page = 0;

function makeTile(episode) {
  const card = document.createElement(episode ? "a" : "div");
  card.className = episode ? "card" : "card empty";
  if (!episode) {
    card.setAttribute("aria-hidden", "true");
    card.append(document.createElement("div"));
    return card;
  }
  const dir = "episodes/" + episode.id + "/";
  card.href = dir + "index.html";
  const photo = document.createElement("img");
  photo.src = dir + "cover.jpg";
  photo.alt = "";
  photo.draggable = false;

  const label = document.createElement("div");
  label.className = "label";
  const name = document.createElement("span");
  name.textContent = episode.title;
  const play = document.createElement("span");
  play.className = "play-icon";
  play.setAttribute("aria-hidden", "true");
  label.append(name, play);
  card.append(photo, label);
  return card;
}

for (let index = 0; index < pageCount; index++) {
  const sheet = document.createElement("section");
  sheet.className = "sheet";
  sheet.setAttribute("aria-label", (index + 1) + "쪽");
  for (let i = 0; i < slotsPerPage; i++) {
    sheet.append(makeTile(episodes[index * slotsPerPage + i]));
  }
  sheets.append(sheet);
}

function showPage(index) {
  if (index === page && counter.textContent) return;
  page = Math.max(0, Math.min(pageCount - 1, index));
  counter.textContent = (page + 1) + " / " + pageCount;
  previous.disabled = page === 0;
  next.disabled = page === pageCount - 1;
}
function jump(offset) {
  const target = Math.max(0, Math.min(pageCount - 1, page + offset));
  sheets.scrollTo({ left: sheets.clientWidth * target,
    behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}
sheets.addEventListener("scroll", () => {
  if (sheets.clientWidth) showPage(Math.round(sheets.scrollLeft / sheets.clientWidth));
}, { passive: true });
previous.addEventListener("click", () => jump(-1));
next.addEventListener("click", () => jump(1));
if (pageCount > 1) {
  previous.hidden = false;
  next.hidden = false;
  document.querySelector("#swipe").hidden = false;
}
showPage(0);

window.addEventListener("album-update", event => {
  const note = document.querySelector("#update-note");
  note.textContent = event.detail.message || "";
  note.hidden = !note.textContent;
});
