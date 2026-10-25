const keywordInput = document.querySelector("#keywordInput");
const rankButton = document.querySelector("#rankButton");
const statusText = document.querySelector("#statusText");
const results = document.querySelector("#results");
const recentKeywords = document.querySelector("#recentKeywords");
const logoutButton = document.querySelector("#logoutButton");
const historyList = document.querySelector("#historyList");
const statusBar = document.querySelector("#statusBar");
const todayTitle = document.querySelector("#todayTitle");
const todayText = document.querySelector("#todayText");
const todaySummaryList = document.querySelector("#todaySummaryList");
const overviewLead = document.querySelector("#overviewLead");
const overviewSubtext = document.querySelector("#overviewSubtext");
const overviewWatchCount = document.querySelector("#overviewWatchCount");
const overviewChangeCount = document.querySelector("#overviewChangeCount");
const overviewRecentCount = document.querySelector("#overviewRecentCount");
const notificationList = document.querySelector("#notificationList");
const topBlogsButton = document.querySelector("#topBlogsButton");
const topBlogsPanel = document.querySelector("#topBlogsPanel");
const topBlogsList = document.querySelector("#topBlogsList");
const titleAnalysis = document.querySelector("#titleAnalysis");
const saveKeywordButton = document.querySelector("#saveKeywordButton");
const watchKeywords = document.querySelector("#watchKeywords");
const reloadTrendKeywordsButton = document.querySelector("#reloadTrendKeywordsButton");
const signalTrendMeta = document.querySelector("#signalTrendMeta");
const signalTrendKeywords = document.querySelector("#signalTrendKeywords");
const datalabTrendMeta = document.querySelector("#datalabTrendMeta");
const datalabTrendKeywords = document.querySelector("#datalabTrendKeywords");
const datalabCategoryButtons = document.querySelectorAll("[data-datalab-category]");
const trendPanel = document.querySelector("#trendPanel");
const trendTitle = document.querySelector("#trendTitle");
const trendList = document.querySelector("#trendList");
const keywordDetail = document.querySelector("#keywordDetail");
const detailTitle = document.querySelector("#detailTitle");
const detailText = document.querySelector("#detailText");
const detailCloseButton = document.querySelector("#detailCloseButton");
const importPostsButton = document.querySelector("#importPostsButton");
const myPosts = document.querySelector("#myPosts");
const contentAnalysisForm = document.querySelector("#contentAnalysisForm");
const analysisKeywordInput = document.querySelector("#analysisKeywordInput");
const analysisTitleInput = document.querySelector("#analysisTitleInput");
const analysisBodyInput = document.querySelector("#analysisBodyInput");
const analyzeContentButton = document.querySelector("#analyzeContentButton");
const contentAnalysisResult = document.querySelector("#contentAnalysisResult");
const viewButtons = document.querySelectorAll("[data-view-target]");
const viewPanels = document.querySelectorAll("[data-view-panel]");

const recentKey = "bms_recent_keywords";
let latestTopBlogsPayload = null;
let activeDatalabCategory = "50000000";
let latestWatchSummaryItems = [];
let latestTodaySummaryItems = [];
const titleStopWords = new Set([
  "그리고",
  "그래서",
  "네이버",
  "블로그",
  "후기",
  "리뷰",
  "추천",
  "정리",
  "모음",
  "방문",
  "진짜",
  "완전",
  "내돈내산",
]);

function getRecentKeywords() {
  try {
    return JSON.parse(localStorage.getItem(recentKey) || "[]");
  } catch {
    return [];
  }
}

function setRecentKeyword(keyword) {
  const next = [keyword, ...getRecentKeywords().filter((item) => item !== keyword)].slice(0, 8);
  localStorage.setItem(recentKey, JSON.stringify(next));
  renderRecentKeywords();
}

function renderRecentKeywords() {
  const items = getRecentKeywords();
  recentKeywords.innerHTML = "";

  if (items.length === 0) {
    recentKeywords.innerHTML = '<p class="empty-text">아직 최근 키워드가 없습니다.</p>';
    updateRankOverview();
    return;
  }

  for (const keyword of items) {
    const button = document.createElement("button");
    button.className = "chip";
    button.type = "button";
    button.textContent = keyword;
    button.addEventListener("click", () => {
      keywordInput.value = keyword;
      fetchRank();
    });
    recentKeywords.append(button);
  }

  updateRankOverview();
}

function openKeywordDetail(keyword, message = "순위, 변화, 상위글을 한 번에 확인합니다.") {
  keywordDetail.hidden = false;
  detailTitle.textContent = `${keyword} 상세`;
  detailText.textContent = message;
}

function closeKeywordDetail() {
  keywordDetail.hidden = true;
  results.innerHTML = "";
  titleAnalysis.innerHTML = "";
  topBlogsPanel.hidden = true;
  topBlogsPanel.open = false;
  trendPanel.hidden = true;
  trendPanel.open = false;
  statusText.textContent = "키워드를 입력하고 순위를 확인하세요.";
}

function setActiveView(view) {
  for (const button of viewButtons) {
    button.classList.toggle("is-active", button.dataset.viewTarget === view);
  }

  for (const panel of viewPanels) {
    const isVisible = panel.dataset.viewPanel === view;
    panel.hidden = !isVisible;
  }

  if (view !== "rank") {
    closeKeywordDetail();
  }
}

function surfaceLabel(surface) {
  const labels = {
    desktop: "PC 통합검색",
    mobile: "모바일 통합검색",
    desktop_blog: "PC 블로그탭",
    mobile_blog: "모바일 블로그탭",
    blog_section: "네이버 블로그 섹션",
  };
  return labels[surface] || surface;
}

function formatTrendTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value || "";
  }

  return `${String(date.getMonth() + 1).padStart(2, "0")}.${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function changeLabel(change) {
  if (change.direction === "up") {
    return `${surfaceLabel(change.surface)} ${change.delta}계단 상승`;
  }
  if (change.direction === "down") {
    return `${surfaceLabel(change.surface)} ${Math.abs(change.delta)}계단 하락`;
  }
  if (change.direction === "entered") {
    return `${surfaceLabel(change.surface)} 순위권 진입`;
  }
  if (change.direction === "lost") {
    return `${surfaceLabel(change.surface)} 순위권 밖`;
  }
  if (change.direction === "new") {
    return `${surfaceLabel(change.surface)} 첫 확인`;
  }
  return `${surfaceLabel(change.surface)} 유지`;
}

function changeClass(change) {
  if (change.direction === "up" || change.direction === "entered") {
    return "summary-badge good";
  }
  if (change.direction === "down" || change.direction === "lost") {
    return "summary-badge watch";
  }
  return "summary-badge";
}

function notificationTone(change) {
  if (change.direction === "up" || change.direction === "entered") {
    return "good";
  }
  if (change.direction === "down" || change.direction === "lost") {
    return "watch";
  }
  return "";
}

function notificationText(keyword, change) {
  if (change.direction === "up") {
    return `${keyword}: ${surfaceLabel(change.surface)} ${change.delta}계단 상승`;
  }
  if (change.direction === "down") {
    return `${keyword}: ${surfaceLabel(change.surface)} ${Math.abs(change.delta)}계단 하락`;
  }
  if (change.direction === "entered") {
    return `${keyword}: ${surfaceLabel(change.surface)} 순위권 진입`;
  }
  if (change.direction === "lost") {
    return `${keyword}: ${surfaceLabel(change.surface)} 순위권 밖`;
  }
  if (change.direction === "new") {
    return `${keyword}: ${surfaceLabel(change.surface)} 첫 확인`;
  }
  return `${keyword}: ${surfaceLabel(change.surface)} 유지`;
}

function bestRankText(item) {
  const ranked = (item.latest_results || []).filter((result) => result.rank);
  if (ranked.length === 0) {
    return "순위권 밖";
  }
  const best = ranked.reduce((current, result) => (result.rank < current.rank ? result : current), ranked[0]);
  return `${surfaceLabel(best.surface)} ${best.rank}위`;
}

function compactSurfaceLabel(surface) {
  const labels = {
    desktop: "PC",
    mobile: "모바일",
    desktop_blog: "PC블로그",
    mobile_blog: "모바일블로그",
    blog_section: "블로그섹션",
  };
  return labels[surface] || surface;
}

function compactBestRankText(item) {
  const ranked = (item.latest_results || []).filter((result) => result.rank);
  if (ranked.length === 0) {
    return "밖";
  }
  const best = ranked.reduce((current, result) => (result.rank < current.rank ? result : current), ranked[0]);
  return `${compactSurfaceLabel(best.surface)} ${best.rank}위`;
}

function updateRankOverview() {
  const recentItems = getRecentKeywords();
  const watchItems = latestWatchSummaryItems || [];
  const todayItems = latestTodaySummaryItems || [];
  const notableChangeCount = watchItems.reduce((count, item) => {
    return count + (item.changes || []).filter((change) => change.direction !== "same").length;
  }, 0);

  overviewWatchCount.textContent = `${watchItems.length}개`;
  overviewChangeCount.textContent = `${notableChangeCount}건`;
  overviewRecentCount.textContent = `${recentItems.length}개`;

  if (todayItems.length > 0) {
    overviewLead.textContent = `${todayItems[0].keyword}부터 다시 보면 됩니다`;
    overviewSubtext.textContent = `${bestRankText(todayItems[0])} 기준으로 가장 먼저 보입니다.`;
    return;
  }

  if (recentItems.length > 0) {
    overviewLead.textContent = `${recentItems[0]} 다시 확인`;
    overviewSubtext.textContent = "최근 검색어에서 바로 이어서 볼 수 있습니다.";
    return;
  }

  overviewLead.textContent = "오늘 먼저 볼 키워드를 고르는 중";
  overviewSubtext.textContent = "관심 키워드와 최근 검색을 바탕으로 바로 다시 확인할 항목을 모아둡니다.";
}

function latestBestRankText(results) {
  const ranked = (results || []).filter((result) => result.rank);
  if (ranked.length === 0) {
    return "순위권 밖";
  }
  const best = ranked.reduce((current, result) => (result.rank < current.rank ? result : current), ranked[0]);
  return `${surfaceLabel(best.surface)} ${best.rank}위`;
}

function bestResult(results) {
  const ranked = (results || []).filter((result) => result.rank);
  if (ranked.length === 0) {
    return null;
  }
  return ranked.reduce((current, result) => (result.rank < current.rank ? result : current), ranked[0]);
}

function renderPostResultLinks(container, results) {
  container.innerHTML = "";
  const latestResults = results || [];

  if (latestResults.length === 0) {
    container.innerHTML = '<p class="post-result-empty">아직 저장된 결과 링크가 없습니다.</p>';
    return;
  }

  const best = bestResult(latestResults);
  if (best && best.result_url) {
    const bestLink = document.createElement("a");
    bestLink.className = "post-result-link primary";
    bestLink.href = best.result_url;
    bestLink.target = "_blank";
    bestLink.rel = "noopener noreferrer";
    bestLink.textContent = `${surfaceLabel(best.surface)} 결과 보기`;
    container.append(bestLink);
  }

  for (const result of latestResults) {
    if (!result.result_url) {
      continue;
    }
    const link = document.createElement("a");
    link.className = "post-result-link";
    link.href = result.result_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = `${compactSurfaceLabel(result.surface)} ${result.rank ? `${result.rank}위` : "밖"}`;
    container.append(link);
  }
}

function titleTokens(title) {
  return title
    .replace(/[^\p{Letter}\p{Number}\s]/gu, " ")
    .split(/\s+/)
    .map((word) => word.trim())
    .filter((word) => word.length >= 2 && !titleStopWords.has(word));
}

function analyzeTitles(payload) {
  const counts = new Map();
  const posts = (payload.results || []).flatMap((group) => group.posts || []);
  const seenTitles = new Set();
  const uniquePosts = posts.filter((post) => {
    if (seenTitles.has(post.title)) {
      return false;
    }
    seenTitles.add(post.title);
    return true;
  });

  for (const post of uniquePosts) {
    for (const token of titleTokens(post.title)) {
      counts.set(token, (counts.get(token) || 0) + 1);
    }
  }

  const words = [...counts.entries()]
    .sort((first, second) => second[1] - first[1] || first[0].localeCompare(second[0]))
    .slice(0, 10)
    .map(([word, count]) => ({ word, count }));

  return {
    checkedTitleCount: uniquePosts.length,
    words,
    examples: uniquePosts.slice(0, 3),
  };
}

function topBlogsPayloadMatches(keyword) {
  return latestTopBlogsPayload && (latestTopBlogsPayload.keyword || "").trim() === keyword.trim();
}

function referencePostsFromTopBlogs(payload) {
  const posts = (payload.results || []).flatMap((group) => group.posts || []);
  const seen = new Set();
  const references = [];

  for (const post of posts) {
    const key = post.url || post.title;
    if (!key || seen.has(key) || !post.title) {
      continue;
    }
    seen.add(key);
    references.push({
      title: post.title,
      summary: post.summary || "",
      url: post.url || "",
    });
    if (references.length >= 30) {
      break;
    }
  }

  return references;
}

async function ensureReferencePostsForAnalysis(keyword) {
  if (topBlogsPayloadMatches(keyword)) {
    return referencePostsFromTopBlogs(latestTopBlogsPayload);
  }

  try {
    const response = await fetch(`/api/blogs?keyword=${encodeURIComponent(keyword)}&limit=10`);
    if (response.status === 401) {
      window.location.href = "/login";
      return [];
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "상위글 제목/요약 확인에 실패했습니다.");
    }
    latestTopBlogsPayload = payload;
    return referencePostsFromTopBlogs(payload);
  } catch (error) {
    statusText.textContent = `${error.message} 본문 분석만 계속합니다.`;
    return [];
  }
}

function keywordSuggestions(keyword, words) {
  const base = keyword.trim();
  const baseParts = new Set(base.split(/\s+/).filter(Boolean));
  const suggestions = [];

  for (const item of words) {
    if (base.includes(item.word) || baseParts.has(item.word)) {
      continue;
    }
    suggestions.push(`${base} ${item.word}`);
  }

  return [...new Set(suggestions)].slice(0, 6);
}

function renderTitleAnalysis(payload) {
  const analysis = analyzeTitles(payload);
  const suggestions = keywordSuggestions(payload.keyword || keywordInput.value, analysis.words);
  titleAnalysis.innerHTML = "";

  if (analysis.checkedTitleCount === 0) {
    titleAnalysis.innerHTML = '<p class="empty-text">분석할 상위글 제목이 없습니다.</p>';
    return;
  }

  const heading = document.createElement("div");
  heading.className = "analysis-heading";

  const title = document.createElement("div");
  const kicker = document.createElement("p");
  kicker.className = "section-kicker";
  kicker.textContent = "Title Notes";

  const headingText = document.createElement("h3");
  headingText.textContent = "상위글 제목에서 자주 보이는 말";

  const count = document.createElement("span");
  count.className = "analysis-count";
  count.textContent = `${analysis.checkedTitleCount}개 제목`;

  title.append(kicker, headingText);
  heading.append(title, count);

  const words = document.createElement("div");
  words.className = "analysis-words";

  if (analysis.words.length === 0) {
    words.innerHTML = '<p class="empty-text">반복되는 단어가 아직 뚜렷하지 않습니다.</p>';
  } else {
    for (const item of analysis.words) {
      const chip = document.createElement("span");
      chip.className = "analysis-chip";
      chip.textContent = `${item.word} ${item.count}`;
      words.append(chip);
    }
  }

  const examples = document.createElement("div");
  examples.className = "analysis-examples";
  for (const post of analysis.examples) {
    const example = document.createElement("p");
    example.textContent = post.title;
    examples.append(example);
  }

  const opportunity = document.createElement("div");
  opportunity.className = "opportunity-box";

  const opportunityTitle = document.createElement("p");
  opportunityTitle.className = "opportunity-title";
  opportunityTitle.textContent = "다음 키워드 후보";

  const opportunityList = document.createElement("div");
  opportunityList.className = "opportunity-list";

  if (suggestions.length === 0) {
    opportunityList.innerHTML = '<p class="empty-text">지금 제목들만으로는 뚜렷한 후보가 없습니다.</p>';
  } else {
    for (const suggestion of suggestions) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "opportunity-chip";
      button.textContent = suggestion;
      button.addEventListener("click", () => {
        keywordInput.value = suggestion;
        fetchRank();
      });
      opportunityList.append(button);
    }
  }

  opportunity.append(opportunityTitle, opportunityList);
  titleAnalysis.append(heading, words, opportunity, examples);
}

function renderTodaySummary(payload) {
  const items = payload.items || [];
  todaySummaryList.innerHTML = "";
  latestTodaySummaryItems = items;

  if (items.length === 0) {
    todayTitle.textContent = "아직 확인 전";
    todayText.textContent = "관심 키워드를 기다리는 중";
    todaySummaryList.innerHTML = '<p class="today-empty">관심 키워드 없음</p>';
    updateRankOverview();
    return;
  }

  todayTitle.textContent = bestRankText(items[0]);
  todayText.textContent = items[0].keyword;

  for (const item of items.slice(0, 3)) {
    const article = document.createElement("article");
    article.className = "today-summary-item";
    article.tabIndex = 0;
    article.role = "button";

    const title = document.createElement("span");
    title.className = "today-summary-keyword";
    title.textContent = item.keyword;

    const best = document.createElement("span");
    best.className = "today-summary-rank";
    best.textContent = compactBestRankText(item);

    article.append(title, best);
    article.addEventListener("click", () => {
      keywordInput.value = item.keyword;
      fetchRank();
    });
    article.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        keywordInput.value = item.keyword;
        fetchRank();
      }
    });
    todaySummaryList.append(article);
  }

  updateRankOverview();
}

function renderNotifications(payload) {
  const items = payload.items || [];
  const notifications = [];
  notificationList.innerHTML = "";

  for (const item of items) {
    const changes = item.changes || [];
    const notable = changes.filter((change) => change.direction !== "same");
    const displayChanges = notable.length > 0 ? notable : changes.slice(0, 1);

    for (const change of displayChanges) {
      notifications.push({
        keyword: item.keyword,
        change,
        text: notificationText(item.keyword, change),
      });
    }
  }

  if (notifications.length === 0) {
    notificationList.innerHTML = '<p class="empty-text">관심 키워드를 확인하면 새 소식이 여기에 모입니다.</p>';
    return;
  }

  for (const item of notifications.slice(0, 6)) {
    const article = document.createElement("article");
    const tone = notificationTone(item.change);
    article.className = tone ? `notification-item ${tone}` : "notification-item";
    article.tabIndex = 0;
    article.role = "button";

    const marker = document.createElement("span");
    marker.className = "notification-marker";
    marker.textContent = tone === "good" ? "UP" : tone === "watch" ? "CHECK" : "NEW";

    const body = document.createElement("div");
    const title = document.createElement("p");
    title.className = "notification-title";
    title.textContent = item.text;

    const meta = document.createElement("p");
    meta.className = "notification-meta";
    meta.textContent = item.change.created_at ? `최근 확인 ${formatTrendTime(item.change.created_at)}` : "최근 확인 전";

    body.append(title, meta);
    article.append(marker, body);
    article.addEventListener("click", () => {
      keywordInput.value = item.keyword;
      fetchRank();
    });
    article.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        keywordInput.value = item.keyword;
        fetchRank();
      }
    });
    notificationList.append(article);
  }
}

function renderResults(payload) {
  results.innerHTML = "";
  openKeywordDetail(payload.keyword, "기준별 현재 순위와 최근 변화를 확인합니다.");
  const foundRanks = payload.results.filter((result) => result.rank);

  if (foundRanks.length > 0) {
    const best = foundRanks.reduce((current, item) => (item.rank < current.rank ? item : current), foundRanks[0]);
    todayTitle.textContent = `${payload.keyword} ${best.rank}위`;
    todayText.textContent = `${surfaceLabel(best.surface)}에서 가장 먼저 찾았어요.`;
  } else {
    todayTitle.textContent = `${payload.keyword} 순위권 밖`;
    todayText.textContent = "확인한 기준별 30개 글 안에서는 대상 블로그를 찾지 못했어요.";
  }

  for (const result of payload.results) {
    const article = document.createElement("article");
    article.className = result.rank ? "result-item is-found" : "result-item is-missing";

    const heading = document.createElement("p");
    heading.className = "result-surface";
    heading.textContent = surfaceLabel(result.surface);

    const rank = document.createElement("p");
    rank.className = result.rank ? "rank-text" : "rank-text missing";
    rank.textContent = result.rank ? `${result.rank}위` : `30개 안에서 찾지 못함`;

    const ribbon = document.createElement("span");
    ribbon.className = result.rank ? "result-ribbon" : "result-ribbon missing";
    ribbon.textContent = result.rank ? "Ranked" : "Watching";

    const detail = document.createElement("div");
    detail.className = "result-detail";

    if (result.result_url) {
      const resultLink = document.createElement("a");
      resultLink.href = result.result_url;
      resultLink.target = "_blank";
      resultLink.rel = "noopener noreferrer";
      resultLink.textContent = "결과화면 URL";
      detail.append(resultLink);
    }

    if (result.post) {
      const title = document.createElement("p");
      title.className = "post-title";
      title.textContent = result.post.title;

      const link = document.createElement("a");
      link.href = result.post.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "글 바로가기";

      detail.append(title, link);
    } else {
      const missing = document.createElement("p");
      missing.className = "empty-text";
      missing.textContent = `${result.checked_count}개 블로그 글 안에서 대상 글을 찾지 못했습니다.`;
      detail.append(missing);
    }

    article.append(ribbon, heading, rank, detail);
    results.append(article);
  }
}

function renderHistory(items) {
  historyList.innerHTML = "";

  if (!items || items.length === 0) {
    historyList.innerHTML = '<p class="empty-text">저장된 이력이 아직 없습니다.</p>';
    return;
  }

  const grouped = new Map();
  for (const item of items) {
    const key = `${item.keyword}:${item.collected_at}`;
    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key).push(item);
  }

  for (const group of [...grouped.values()].slice(0, 6)) {
    const first = group[0];
    const article = document.createElement("article");
    article.className = "history-item";

    const title = document.createElement("p");
    title.className = "history-keyword";
    title.textContent = first.keyword;

    const meta = document.createElement("div");
    meta.className = "history-meta";
    for (const item of group) {
      const badge = document.createElement("span");
      badge.className = item.rank ? "history-badge" : "history-badge missing";
      badge.textContent = `${surfaceLabel(item.surface)} ${item.rank ? `${item.rank}위` : "순위권 밖"}`;
      meta.append(badge);
    }

    article.append(title, meta);
    historyList.append(article);
  }
}

function renderTrend(payload) {
  trendPanel.hidden = false;
  trendList.innerHTML = "";
  trendTitle.textContent = `${payload.keyword} 최근 순위 변화`;

  if (!payload.items || payload.items.length === 0) {
    trendList.innerHTML = '<p class="empty-text">아직 쌓인 순위 이력이 없습니다.</p>';
    return;
  }

  const grouped = new Map();
  for (const item of payload.items) {
    if (!grouped.has(item.surface)) {
      grouped.set(item.surface, []);
    }
    grouped.get(item.surface).push(item);
  }

  for (const [surface, items] of grouped) {
    const section = document.createElement("section");
    section.className = "trend-surface";

    const heading = document.createElement("h3");
    heading.textContent = surfaceLabel(surface);

    const points = document.createElement("div");
    points.className = "trend-points";

    for (const item of items.slice(-7)) {
      const point = document.createElement("div");
      point.className = item.rank ? "trend-point" : "trend-point missing";

      const rank = document.createElement("span");
      rank.className = "trend-rank";
      rank.textContent = item.rank ? `${item.rank}위` : "밖";

      const time = document.createElement("span");
      time.className = "trend-time";
      time.textContent = formatTrendTime(item.created_at);

      point.append(rank, time);
      points.append(point);
    }

    section.append(heading, points);
    trendList.append(section);
  }
}

function trendStateLabel(state) {
  if (state === "+" || state === "up") {
    return "상승";
  }
  if (state === "-" || state === "down") {
    return "하락";
  }
  if (state === "s" || state === "equal") {
    return "유지";
  }
  if (state === "n") {
    return "신규";
  }
  return state || "";
}

function renderTrendKeywordList(container, items, options = {}) {
  container.innerHTML = "";
  if (!items || items.length === 0) {
    container.innerHTML = '<p class="empty-text">키워드를 불러오지 못했습니다.</p>';
    return;
  }

  for (const item of items.slice(0, options.limit || 10)) {
    const button = document.createElement("button");
    button.className = "trend-keyword-button";
    button.type = "button";
    button.addEventListener("click", () => {
      keywordInput.value = item.keyword;
      fetchRank();
    });

    const rank = document.createElement("span");
    rank.className = "trend-keyword-rank";
    rank.textContent = `${item.rank}`;

    const keyword = document.createElement("strong");
    keyword.textContent = item.keyword;

    button.append(rank, keyword);
    if (item.state) {
      const state = document.createElement("span");
      state.className = "trend-keyword-state";
      state.textContent = trendStateLabel(item.state);
      button.append(state);
    }
    container.append(button);
  }
}

async function loadSignalTrendKeywords() {
  signalTrendMeta.textContent = "불러오는 중";
  signalTrendKeywords.innerHTML = '<p class="empty-text">Signal 데이터를 확인하고 있습니다.</p>';
  try {
    const response = await fetch("/api/signal/realtime-keywords");
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "Signal 실시간 검색어를 불러오지 못했습니다.");
    }
    signalTrendMeta.textContent = payload.now ? `기준 ${formatTrendTime(payload.now)}` : "실시간";
    renderTrendKeywordList(signalTrendKeywords, payload.items || []);
  } catch (error) {
    signalTrendMeta.textContent = "불러오기 실패";
    signalTrendKeywords.innerHTML = `<p class="empty-text">${error.message}</p>`;
  }
}

async function loadDatalabTrendKeywords(category = activeDatalabCategory) {
  activeDatalabCategory = category;
  datalabTrendMeta.textContent = "불러오는 중";
  datalabTrendKeywords.innerHTML = '<p class="empty-text">데이터랩을 확인하고 있습니다.</p>';
  try {
    const response = await fetch(`/api/datalab/shopping-keywords?category=${encodeURIComponent(category)}`);
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "데이터랩 인기 검색어를 불러오지 못했습니다.");
    }
    datalabTrendMeta.textContent = `${payload.category.name} · ${payload.period}`;
    renderTrendKeywordList(datalabTrendKeywords, payload.items || []);
  } catch (error) {
    datalabTrendMeta.textContent = "불러오기 실패";
    datalabTrendKeywords.innerHTML = `<p class="empty-text">${error.message}</p>`;
  }
}

async function loadTrendKeywords() {
  await Promise.all([loadSignalTrendKeywords(), loadDatalabTrendKeywords(activeDatalabCategory)]);
}

function renderWatchKeywords(items) {
  watchKeywords.innerHTML = "";
  latestWatchSummaryItems = items || [];

  if (!items || items.length === 0) {
    watchKeywords.innerHTML = '<p class="empty-text">저장된 관심 키워드가 아직 없습니다.</p>';
    updateRankOverview();
    return;
  }

  for (const item of items) {
    const article = document.createElement("article");
    article.className = "watch-keyword-item";

    const content = document.createElement("div");
    content.className = "watch-keyword-content";

    const keyword = document.createElement("span");
    keyword.textContent = item.keyword;

    const meta = document.createElement("p");
    meta.className = "watch-keyword-meta";
    meta.textContent = item.last_checked_at
      ? `최근 확인 ${formatTrendTime(item.last_checked_at)}`
      : "아직 자동 확인 전";

    const badges = document.createElement("div");
    badges.className = "watch-rank-badges";

    if (item.latest_results && item.latest_results.length > 0) {
      for (const result of item.latest_results) {
        const badge = document.createElement("span");
        badge.className = result.rank ? "watch-rank-badge" : "watch-rank-badge missing";
        badge.textContent = `${surfaceLabel(result.surface)} ${result.rank ? `${result.rank}위` : "밖"}`;
        badges.append(badge);
      }
    } else {
      const empty = document.createElement("span");
      empty.className = "watch-rank-badge missing";
      empty.textContent = "저장된 순위 없음";
      badges.append(empty);
    }

    content.append(keyword, meta, badges);

    const actions = document.createElement("div");
    actions.className = "watch-keyword-actions";

    article.addEventListener("click", () => {
      keywordInput.value = item.keyword;
      fetchRank();
    });

    const rank = document.createElement("button");
    rank.type = "button";
    rank.textContent = "상세";
    rank.addEventListener("click", (event) => {
      event.stopPropagation();
      keywordInput.value = item.keyword;
      fetchRank();
    });

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "ghost-button compact";
    remove.textContent = "삭제";
    remove.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteWatchKeyword(item.id);
    });

    actions.append(rank, remove);
    article.append(content, actions);
    watchKeywords.append(article);
  }

  updateRankOverview();
}

function renderPostCheckSummary(container, keywordSummaries) {
  const checked = (keywordSummaries || []).filter((summary) => summary.last_checked_at);
  if (checked.length === 0) {
    container.innerHTML = '<p class="post-check-empty">아직 글 순위를 확인하지 않았습니다.</p>';
    return;
  }

  container.innerHTML = "";
  for (const summary of checked.slice(0, 3)) {
    const row = document.createElement("p");
    row.className = "post-check-row";

    const keyword = document.createElement("span");
    keyword.textContent = summary.keyword;

    const rank = document.createElement("strong");
    rank.textContent = latestBestRankText(summary.latest_results);

    row.append(keyword, rank);
    container.append(row);
  }
}

function renderPostCheckPayload(container, payload) {
  const checked = payload.checked || [];
  if (checked.length === 0) {
    container.innerHTML = '<p class="post-check-empty">확인할 목표 키워드가 없습니다.</p>';
    return;
  }

  container.innerHTML = "";
  for (const item of checked) {
    const row = document.createElement("p");
    row.className = "post-check-row";

    const keyword = document.createElement("span");
    keyword.textContent = item.keyword;

    const rank = document.createElement("strong");
    rank.textContent = latestBestRankText(item.results);

    row.append(keyword, rank);
    container.append(row);
  }
}

function renderMyPosts(items) {
  myPosts.innerHTML = "";

  if (!items || items.length === 0) {
    myPosts.innerHTML = '<p class="empty-text">아직 저장한 글이 없습니다.</p>';
    return;
  }

  for (const item of items) {
    const article = document.createElement("article");
    article.className = "post-item";

    const content = document.createElement("div");
    content.className = "post-item-content";

    const title = document.createElement("p");
    title.className = "post-item-title";
    title.textContent = item.title;

    const link = document.createElement("a");
    link.href = item.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = item.url;

    const metaItems = [
      item.category ? `카테고리 ${item.category}` : "",
      item.published_at ? `발행일 ${item.published_at}` : "",
      item.blog_id ? `블로그 ${item.blog_id}` : "",
      item.post_id ? `글번호 ${item.post_id}` : "",
    ].filter(Boolean);
    const meta = document.createElement("p");
    meta.className = "post-item-meta";
    meta.textContent = metaItems.length > 0 ? metaItems.join(" · ") : "메타데이터를 추가하면 글 관리 기준이 선명해집니다.";

    const summary = document.createElement("p");
    summary.className = "post-item-summary";
    summary.textContent = item.content_summary || "요약이 없습니다.";

    const keywordList = document.createElement("div");
    keywordList.className = "post-keyword-list";

    const keywordEditor = document.createElement("div");
    keywordEditor.className = "post-keyword-editor";

    const keywordEditorLabel = document.createElement("p");
    keywordEditorLabel.className = "post-section-label";
    keywordEditorLabel.textContent = "목표 키워드";

    const keywordInputRow = document.createElement("div");
    keywordInputRow.className = "post-keyword-input-row";

    const keywordField = document.createElement("input");
    keywordField.type = "text";
    keywordField.placeholder = "예: 서촌 카페";
    keywordField.value = "";

    const addKeywordButton = document.createElement("button");
    addKeywordButton.type = "button";
    addKeywordButton.className = "ghost-button compact";
    addKeywordButton.textContent = "키워드 추가";
    addKeywordButton.addEventListener("click", () => {
      addPostKeyword(item.id, keywordField.value, addKeywordButton);
    });
    keywordField.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        addPostKeyword(item.id, keywordField.value, addKeywordButton);
      }
    });

    keywordInputRow.append(keywordField, addKeywordButton);

    const summaries = item.keyword_summaries || [];
    if (summaries.length === 0) {
      keywordList.innerHTML = '<p class="empty-text">목표 키워드가 없습니다.</p>';
    } else {
      for (const summary of summaries) {
        const keywordMeta = (item.keywords || []).find((keyword) => keyword.keyword === summary.keyword);

        const row = document.createElement("div");
        row.className = "post-keyword-row";

        const openButton = document.createElement("button");
        openButton.className = "post-keyword-open";
        openButton.type = "button";
        openButton.addEventListener("click", () => {
          keywordInput.value = summary.keyword;
          fetchRank();
        });

        const keyword = document.createElement("span");
        keyword.textContent = summary.keyword;

        const rank = document.createElement("strong");
        rank.textContent = latestBestRankText(summary.latest_results);

        openButton.append(keyword, rank);
        row.append(openButton);

        if (keywordMeta) {
          const removeKeywordButton = document.createElement("button");
          removeKeywordButton.type = "button";
          removeKeywordButton.className = "ghost-button compact post-keyword-delete";
          removeKeywordButton.textContent = "삭제";
          removeKeywordButton.addEventListener("click", () => deletePostKeyword(item.id, keywordMeta.id));
          row.append(removeKeywordButton);
        }

        keywordList.append(row);
      }
    }

    keywordEditor.append(keywordEditorLabel, keywordInputRow, keywordList);

    const checkResult = document.createElement("div");
    checkResult.className = "post-check-result";
    checkResult.dataset.postCheckResult = String(item.id);
    renderPostCheckSummary(checkResult, item.keyword_summaries || []);

    const resultLinks = document.createElement("div");
    resultLinks.className = "post-result-links";
    resultLinks.dataset.postResultLinks = String(item.id);
    const allLatestResults = summaries.flatMap((summary) => summary.latest_results || []);
    renderPostResultLinks(resultLinks, allLatestResults);

    content.append(title, link, meta, summary, keywordEditor, checkResult, resultLinks);

    const actions = document.createElement("div");
    actions.className = "post-item-actions";

    const check = document.createElement("button");
    check.type = "button";
    check.textContent = "글 순위확인";
    check.addEventListener("click", () => checkMyPost(item.id, article, check));

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "ghost-button compact";
    remove.textContent = "삭제";
    remove.addEventListener("click", () => deleteMyPost(item.id));

    actions.append(check, remove);
    article.append(content, actions);
    myPosts.append(article);
  }
}

function renderTopBlogs(payload) {
  topBlogsPanel.hidden = false;
  topBlogsList.innerHTML = "";
  renderTitleAnalysis(payload);

  if (!payload.results || payload.results.length === 0) {
    topBlogsList.innerHTML = '<p class="empty-text">상위 블로그 글을 찾지 못했습니다.</p>';
    return;
  }

  for (const group of payload.results) {
    const section = document.createElement("section");
    section.className = "top-blog-group";

    const heading = document.createElement("div");
    heading.className = "top-blog-group-heading";

    const groupTitle = document.createElement("h3");
    groupTitle.textContent = surfaceLabel(group.surface);

    const meta = document.createElement("a");
    meta.href = group.result_url;
    meta.target = "_blank";
    meta.rel = "noopener noreferrer";
    meta.textContent = `${group.checked_count}개 확인`;

    heading.append(groupTitle, meta);
    section.append(heading);

    if (group.result_url) {
      const resultLink = document.createElement("a");
      resultLink.href = group.result_url;
      resultLink.target = "_blank";
      resultLink.rel = "noopener noreferrer";
      resultLink.textContent = "결과화면 URL";
      section.append(resultLink);
    }

    if (!group.posts || group.posts.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty-text";
      empty.textContent = "이 기준에서는 블로그 글을 찾지 못했습니다.";
      section.append(empty);
      topBlogsList.append(section);
      continue;
    }

    group.posts.forEach((post, index) => {
      const article = document.createElement("article");
      article.className = "top-blog-item";

      const number = document.createElement("span");
      number.className = "top-blog-number";
      number.textContent = `${index + 1}`;

      const body = document.createElement("div");

      const title = document.createElement("p");
      title.className = "top-blog-title";
      title.textContent = post.title;

      const link = document.createElement("a");
      link.href = post.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = post.url;

      body.append(title, link);
      article.append(number, body);
      section.append(article);
    });

    topBlogsList.append(section);
  }
}

function scoreTone(score) {
  if (score >= 80) {
    return "good";
  }
  if (score >= 60) {
    return "watch";
  }
  return "risk";
}

function renderTextList(items, className = "") {
  const list = document.createElement("ul");
  list.className = className || "analysis-list";

  for (const item of items || []) {
    const entry = document.createElement("li");
    entry.textContent = item;
    list.append(entry);
  }

  return list;
}

function renderContentAnalysis(payload) {
  contentAnalysisResult.innerHTML = "";

  const overview = document.createElement("article");
  overview.className = `analysis-overview ${scoreTone(payload.score)}`;

  const score = document.createElement("div");
  score.className = "analysis-score";
  score.textContent = `${payload.score}점`;

  const copy = document.createElement("div");
  const label = document.createElement("p");
  label.className = "section-kicker";
  label.textContent = "Internal Proxy";

  const summary = document.createElement("h3");
  summary.textContent = payload.summary;

  const meta = document.createElement("p");
  meta.className = "analysis-meta";
  meta.textContent = `${payload.score_label} 예상 의도: ${payload.intent}`;

  copy.append(label, summary, meta);
  overview.append(score, copy);
  contentAnalysisResult.append(overview);

  if (payload.ai_feedback) {
    const ai = document.createElement("section");
    ai.className = "analysis-block notice";

    const heading = document.createElement("h3");
    heading.textContent = "AI 보강 분석";

    const meta = document.createElement("p");
    meta.className = "analysis-meta";
    meta.textContent = `${payload.ai_feedback.provider} · ${payload.ai_feedback.model}`;

    ai.append(heading, meta);

    if (payload.ai_feedback.summary) {
      const summary = document.createElement("p");
      summary.className = "analysis-ai-summary";
      summary.textContent = payload.ai_feedback.summary;
      ai.append(summary);
    }

    if (payload.ai_feedback.priority_actions && payload.ai_feedback.priority_actions.length > 0) {
      const actionHeading = document.createElement("strong");
      actionHeading.textContent = "AI 우선 수정";
      ai.append(actionHeading, renderTextList(payload.ai_feedback.priority_actions));
    }

    if (payload.ai_feedback.title_suggestions && payload.ai_feedback.title_suggestions.length > 0) {
      const titleHeading = document.createElement("strong");
      titleHeading.textContent = "AI 제목 제안";
      ai.append(titleHeading, renderTextList(payload.ai_feedback.title_suggestions));
    }

    if (payload.ai_feedback.opening_paragraph) {
      const openingHeading = document.createElement("strong");
      openingHeading.textContent = "AI 첫 문단 초안";
      const opening = document.createElement("p");
      opening.className = "analysis-ai-paragraph";
      opening.textContent = payload.ai_feedback.opening_paragraph;
      ai.append(openingHeading, opening);
    }

    if (payload.ai_feedback.differentiation_point) {
      const diffHeading = document.createElement("strong");
      diffHeading.textContent = "AI 차별화 포인트";
      const diff = document.createElement("p");
      diff.className = "analysis-ai-paragraph";
      diff.textContent = payload.ai_feedback.differentiation_point;
      ai.append(diffHeading, diff);
    }

    contentAnalysisResult.append(ai);
  }

  if (payload.input_warnings && payload.input_warnings.length > 0) {
    const inputNotes = document.createElement("section");
    inputNotes.className = "analysis-block notice";
    const heading = document.createElement("h3");
    heading.textContent = "입력 정리";
    inputNotes.append(heading, renderTextList(payload.input_warnings));
    contentAnalysisResult.append(inputNotes);
  }

  if (payload.content_stats) {
    const statsList = [];
    if ((payload.content_stats.estimated_photo_count || 0) > 0) {
      statsList.push(`사진 추정 ${payload.content_stats.estimated_photo_count}개`);
    }
    if ((payload.content_stats.map_place_count || 0) > 0) {
      statsList.push(`지도 블록 ${payload.content_stats.map_place_count}개`);
    }
    if (statsList.length > 0) {
      const stats = document.createElement("section");
      stats.className = "analysis-block";
      const heading = document.createElement("h3");
      heading.textContent = "본문 통계";
      stats.append(heading, renderTextList(statsList));
      contentAnalysisResult.append(stats);
    }
  }

  if (payload.photo_checklist && payload.photo_checklist.length > 0) {
    const photos = document.createElement("section");
    photos.className = "analysis-block notice";
    const heading = document.createElement("h3");
    heading.textContent = "사진 체크리스트";
    photos.append(heading, renderTextList(payload.photo_checklist.slice(0, 4)));
    contentAnalysisResult.append(photos);
  }

  if (payload.differentiation_guidance && payload.differentiation_guidance.length > 0) {
    const differentiation = document.createElement("section");
    differentiation.className = "analysis-block notice";
    const heading = document.createElement("h3");
    heading.textContent = "차별화 가이드";
    differentiation.append(heading, renderTextList(payload.differentiation_guidance.slice(0, 3)));
    contentAnalysisResult.append(differentiation);
  }

  if (payload.priority_actions && payload.priority_actions.length > 0) {
    const priority = document.createElement("section");
    priority.className = "analysis-block";
    const heading = document.createElement("h3");
    heading.textContent = "가장 먼저 고칠 것";
    priority.append(heading, renderTextList(payload.priority_actions));
    contentAnalysisResult.append(priority);
  }

  const importantSerpCandidates = (payload.serp_missing_topic_candidates || [])
    .filter((candidate) => candidate.matched_missing_topic)
    .slice(0, 3);
  if (importantSerpCandidates.length > 0) {
    const serpTopics = document.createElement("section");
    serpTopics.className = "analysis-block notice";
    const serpHeading = document.createElement("h3");
    serpHeading.textContent = "상위글에서 반복된 누락 정보";
    const candidateItems = importantSerpCandidates.map((candidate) => {
      return `${candidate.topic}: ${candidate.count}개 글에서 반복됐습니다. 내 글에도 실제 경험과 함께 보강할지 확인하세요.`;
    });
    serpTopics.append(serpHeading, renderTextList(candidateItems));
    contentAnalysisResult.append(serpTopics);
  }

  if (payload.internal_link_candidates && payload.internal_link_candidates.length > 0) {
    const linkSection = document.createElement("section");
    linkSection.className = "analysis-block notice";
    const linkHeading = document.createElement("h3");
    linkHeading.textContent = "내 글 내부 링크 후보";
    const linkItems = payload.internal_link_candidates.slice(0, 2).map((candidate) => {
      const meta = [candidate.category, candidate.published_at].filter(Boolean).join(" · ");
      const reasons = (candidate.reasons || []).join(", ");
      const suffix = meta ? ` (${meta})` : "";
      return `${candidate.title}${suffix}: ${reasons}.`;
    });
    linkSection.append(linkHeading, renderTextList(linkItems));
    contentAnalysisResult.append(linkSection);
  }

  if (payload.existing_post_overlap_warnings && payload.existing_post_overlap_warnings.length > 0) {
    const overlapSection = document.createElement("section");
    overlapSection.className = "analysis-block risk";
    const overlapHeading = document.createElement("h3");
    overlapHeading.textContent = "기존 글 중복 확인";
    const overlapItems = payload.existing_post_overlap_warnings.map((warning) => {
      const titles = (warning.matched_posts || [])
        .map((post) => `${post.title} (${post.reason})`)
        .join(", ");
      return `${warning.topic}: ${warning.count}개 글과 겹침. ${titles}. ${warning.guidance}`;
    });
    overlapSection.append(overlapHeading, renderTextList(overlapItems));
    contentAnalysisResult.append(overlapSection);
  }

  const weakChecks = (payload.checks || [])
    .filter((check) => check.score < check.max_score && check.name !== "위험 요소")
    .sort((first, second) => (first.score / first.max_score) - (second.score / second.max_score))
    .slice(0, 4);

  const checks = document.createElement("section");
  checks.className = "analysis-checks";
  for (const check of weakChecks) {
    const item = document.createElement("article");
    item.className = "analysis-check";

    const heading = document.createElement("div");
    heading.className = "analysis-check-heading";

    const name = document.createElement("strong");
    name.textContent = check.name;

    const value = document.createElement("span");
    value.textContent = `${check.score}/${check.max_score}`;

    heading.append(name, value);
    item.append(heading);

    const bar = document.createElement("div");
    bar.className = "analysis-check-bar";
    const fill = document.createElement("span");
    fill.style.width = `${Math.round((check.score / check.max_score) * 100)}%`;
    bar.append(fill);
    item.append(bar);

    if (check.suggestions && check.suggestions.length > 0) {
      item.append(renderTextList(check.suggestions));
    }

    checks.append(item);
  }
  if (weakChecks.length > 0) {
    contentAnalysisResult.append(checks);
  }

  const ideas = document.createElement("section");
  ideas.className = "analysis-suggestions";

  const titleBox = document.createElement("div");
  titleBox.className = "analysis-block";
  const titleHeading = document.createElement("h3");
  titleHeading.textContent = "제목 후보";
  titleBox.append(titleHeading, renderTextList((payload.title_suggestions || []).slice(0, 2)));

  const headingBox = document.createElement("div");
  headingBox.className = "analysis-block";
  const headingHeading = document.createElement("h3");
  headingHeading.textContent = "소제목 후보";
  headingBox.append(headingHeading, renderTextList((payload.heading_suggestions || []).slice(0, 3)));

  ideas.append(titleBox, headingBox);
  contentAnalysisResult.append(ideas);

  if (payload.risk_warnings && payload.risk_warnings.length > 0) {
    const risks = document.createElement("section");
    risks.className = "analysis-block risk";
    const riskHeading = document.createElement("h3");
    riskHeading.textContent = "위험 요소";
    risks.append(riskHeading, renderTextList(payload.risk_warnings));
    contentAnalysisResult.append(risks);
  }

}

async function analyzeContent(event) {
  event.preventDefault();
  const keyword = analysisKeywordInput.value.trim();
  const title = analysisTitleInput.value.trim();
  const body = analysisBodyInput.value.trim();

  if (!keyword || !title || !body) {
    contentAnalysisResult.innerHTML = '<p class="empty-text">키워드, 제목, 본문을 모두 입력하세요.</p>';
    return;
  }

  analyzeContentButton.disabled = true;
  document.body.dataset.loading = "true";
  contentAnalysisResult.innerHTML = `
    <article class="loading-card">
      <div class="loading-line wide"></div>
      <div class="loading-line"></div>
      <div class="loading-line short"></div>
    </article>
  `;

  try {
    const referencePosts = await ensureReferencePostsForAnalysis(keyword);
    const response = await fetch("/api/content-analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword, title, body, reference_posts: referencePosts }),
    });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "본문 분석에 실패했습니다.");
    }
    renderContentAnalysis(payload);
    if (referencePosts.length > 0) {
      statusText.textContent = `"${keyword}" 본문과 상위글 제목/요약을 함께 확인했습니다.`;
    }
  } catch (error) {
    contentAnalysisResult.innerHTML = "";
    const message = document.createElement("p");
    message.className = "error-text";
    message.textContent = error.message;
    contentAnalysisResult.append(message);
  } finally {
    analyzeContentButton.disabled = false;
    document.body.dataset.loading = "false";
  }
}

async function loadHistory(keyword = "") {
  const url = keyword ? `/api/history?keyword=${encodeURIComponent(keyword)}` : "/api/history?limit=12";
  try {
    const response = await fetch(url);
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await response.json();
    if (response.ok) {
      renderHistory(payload.items);
    }
  } catch {
    renderHistory([]);
  }
}

async function loadTrend(keyword) {
  if (!keyword) {
    trendPanel.hidden = true;
    return;
  }

  try {
    const response = await fetch(`/api/trends?keyword=${encodeURIComponent(keyword)}`);
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (response.ok) {
      renderTrend(payload);
    }
  } catch {
    renderTrend({ keyword, items: [] });
  }
}

async function loadWatchKeywords() {
  try {
    const response = await fetch("/api/watch-keywords");
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await response.json();
    if (response.ok) {
      renderWatchKeywords(payload.items);
    }
  } catch {
    renderWatchKeywords([]);
  }
}

async function loadTodaySummary() {
  try {
    const response = await fetch("/api/today-summary");
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (response.ok) {
      renderTodaySummary(payload);
      renderNotifications(payload);
    }
  } catch {
    renderTodaySummary({ items: [] });
    renderNotifications({ items: [] });
  }
}

async function loadMyPosts() {
  try {
    const response = await fetch("/api/my-posts");
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await response.json();
    if (response.ok) {
      renderMyPosts(payload.items);
    }
  } catch {
    renderMyPosts([]);
  }
}

async function saveWatchKeyword() {
  const keyword = keywordInput.value.trim();
  if (!keyword) {
    openKeywordDetail("키워드 입력", "관심 키워드로 저장할 단어를 먼저 입력합니다.");
    statusText.textContent = "저장할 키워드를 입력하세요.";
    return;
  }

  saveKeywordButton.disabled = true;
  openKeywordDetail(keyword, "관심 키워드 저장 상태를 확인합니다.");
  try {
    const response = await fetch("/api/watch-keywords", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword }),
    });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "관심 키워드 저장에 실패했습니다.");
    }
    await loadWatchKeywords();
    statusText.textContent = `"${keyword}" 관심 키워드 저장 완료`;
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    saveKeywordButton.disabled = false;
  }
}

async function deleteWatchKeyword(keywordId) {
  try {
    const response = await fetch(`/api/watch-keywords/${keywordId}`, { method: "DELETE" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "관심 키워드 삭제에 실패했습니다.");
    }
    await loadWatchKeywords();
    statusText.textContent = "관심 키워드를 삭제했습니다.";
  } catch (error) {
    statusText.textContent = error.message;
  }
}

async function importTargetBlogPosts() {
  importPostsButton.disabled = true;
  document.body.dataset.loading = "true";
  openKeywordDetail("내 블로그 글 가져오기", "설정된 내 블로그의 공개 글을 DB에 채웁니다.");
  statusText.textContent = "내 블로그 공개 글을 가져오고 있습니다.";

  try {
    const response = await fetch("/api/posts/import-target-blog", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ max_posts: 1000, include_body: true }),
    });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "내 블로그 글 가져오기에 실패했습니다.");
    }
    renderMyPosts(payload.items || []);
    statusText.textContent = `가져오기 완료: 새 글 ${payload.created_count}개, 갱신 ${payload.updated_count}개, 건너뜀 ${payload.skipped_count}개, 실패 ${payload.failed_count}개`;
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    importPostsButton.disabled = false;
    document.body.dataset.loading = "false";
  }
}

async function checkMyPost(postId, article, button) {
  document.body.dataset.loading = "true";
  const resultBox = article?.querySelector("[data-post-check-result]");
  if (button) {
    button.disabled = true;
    button.textContent = "확인 중";
  }
  if (resultBox) {
    resultBox.innerHTML = '<p class="post-check-empty">순위 확인 중...</p>';
  }
  try {
    const response = await fetch(`/api/my-posts/${postId}/check`, { method: "POST" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      if (response.status === 400 && payload.detail === "post has no keywords.") {
        const keyword = window.prompt("이 글의 목표 키워드를 입력하세요.");
        const normalizedKeyword = (keyword || "").trim();
        if (!normalizedKeyword) {
          throw new Error("목표 키워드를 입력해야 글 순위를 확인할 수 있습니다.");
        }
        await addKeywordAndCheckMyPost(postId, normalizedKeyword, article, button);
        return;
      }
      throw new Error(payload.detail || "내 글 순위 확인에 실패했습니다.");
    }
    if (resultBox) {
      renderPostCheckPayload(resultBox, payload);
    }
  } catch (error) {
    if (resultBox) {
      resultBox.innerHTML = `<p class="post-check-empty">${error.message}</p>`;
    } else {
      statusText.textContent = error.message;
    }
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "글 순위확인";
    }
    document.body.dataset.loading = "false";
  }
}

async function addKeywordAndCheckMyPost(postId, keyword, article, button) {
  const addResponse = await fetch(`/api/posts/${postId}/keywords`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyword, keyword_type: "target" }),
  });
  if (addResponse.status === 401) {
    window.location.href = "/login";
    return;
  }
  const addPayload = await parseJsonResponse(addResponse);
  if (!addResponse.ok) {
    throw new Error(addPayload.detail || "목표 키워드 저장에 실패했습니다.");
  }
  await checkMyPost(postId, article, button);
}

async function addPostKeyword(postId, rawKeyword, button) {
  const keyword = (rawKeyword || "").trim();
  if (!keyword) {
    statusText.textContent = "추가할 목표 키워드를 입력하세요.";
    return;
  }

  if (button) {
    button.disabled = true;
  }
  try {
    const response = await fetch(`/api/posts/${postId}/keywords`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword, keyword_type: "target" }),
    });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "목표 키워드 추가에 실패했습니다.");
    }
    await loadMyPosts();
    statusText.textContent = `"${keyword}" 목표 키워드를 추가했습니다.`;
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    if (button) {
      button.disabled = false;
    }
  }
}

async function deletePostKeyword(postId, keywordId) {
  try {
    const response = await fetch(`/api/posts/${postId}/keywords/${keywordId}`, { method: "DELETE" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "목표 키워드 삭제에 실패했습니다.");
    }
    await loadMyPosts();
    statusText.textContent = "목표 키워드를 삭제했습니다.";
  } catch (error) {
    statusText.textContent = error.message;
  }
}

async function deleteMyPost(postId) {
  try {
    const response = await fetch(`/api/my-posts/${postId}`, { method: "DELETE" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "내 글 삭제에 실패했습니다.");
    }
    await loadMyPosts();
    statusText.textContent = "내 글을 삭제했습니다.";
  } catch (error) {
    statusText.textContent = error.message;
  }
}

async function fetchTopBlogs() {
  const keyword = keywordInput.value.trim();
  if (!keyword) {
    openKeywordDetail("키워드 입력", "상위글을 확인할 키워드를 먼저 입력합니다.");
    statusText.textContent = "키워드를 입력하세요.";
    return;
  }

  topBlogsButton.disabled = true;
  document.body.dataset.loading = "true";
  openKeywordDetail(keyword, "기준별 상위 블로그 글을 확인합니다.");
  statusText.textContent = `"${keyword}" 기준별 상위글을 확인하고 있습니다.`;
  topBlogsPanel.hidden = false;
  topBlogsList.innerHTML = `
    <article class="loading-card">
      <div class="loading-line wide"></div>
      <div class="loading-line"></div>
      <div class="loading-line short"></div>
    </article>
  `;

  try {
    const response = await fetch(`/api/blogs?keyword=${encodeURIComponent(keyword)}&limit=10`);
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "기준별 상위글 확인에 실패했습니다.");
    }
    latestTopBlogsPayload = payload;
    renderTopBlogs(payload);
    topBlogsPanel.open = true;
    setRecentKeyword(keyword);
    statusText.textContent = `"${keyword}" 기준별 상위글 확인 완료`;
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    topBlogsButton.disabled = false;
    document.body.dataset.loading = "false";
  }
}

async function fetchRank() {
  const keyword = keywordInput.value.trim();
  if (!keyword) {
    openKeywordDetail("키워드 입력", "순위를 확인할 키워드를 먼저 입력합니다.");
    statusText.textContent = "키워드를 입력하세요.";
    return;
  }

  rankButton.disabled = true;
  document.body.dataset.loading = "true";
  openKeywordDetail(keyword, "기준별 현재 순위를 확인합니다.");
  statusText.textContent = `"${keyword}" 순위를 확인하고 있습니다.`;
  results.innerHTML = `
    <article class="loading-card">
      <div class="loading-line wide"></div>
      <div class="loading-line"></div>
      <div class="loading-line short"></div>
    </article>
  `;

  try {
    const response = await fetch(`/api/rank?keyword=${encodeURIComponent(keyword)}`);
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || "순위 확인에 실패했습니다.");
    }
    renderResults(payload);
    setRecentKeyword(keyword);
    await loadHistory(keyword);
    await loadTrend(keyword);
    await loadWatchKeywords();
    await loadTodaySummary();
    statusText.textContent = `"${keyword}" 확인 완료`;
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    rankButton.disabled = false;
    document.body.dataset.loading = "false";
  }
}

async function parseJsonResponse(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch {
    return { detail: text.slice(0, 120) };
  }
}

rankButton.addEventListener("click", fetchRank);
topBlogsButton.addEventListener("click", fetchTopBlogs);
saveKeywordButton.addEventListener("click", saveWatchKeyword);
detailCloseButton.addEventListener("click", closeKeywordDetail);
importPostsButton.addEventListener("click", importTargetBlogPosts);
contentAnalysisForm.addEventListener("submit", analyzeContent);
reloadTrendKeywordsButton.addEventListener("click", loadTrendKeywords);
for (const button of datalabCategoryButtons) {
  button.addEventListener("click", () => {
    for (const item of datalabCategoryButtons) {
      item.classList.toggle("is-active", item === button);
    }
    loadDatalabTrendKeywords(button.dataset.datalabCategory);
  });
}
for (const button of viewButtons) {
  button.addEventListener("click", () => setActiveView(button.dataset.viewTarget));
}
keywordInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    fetchRank();
  }
});

if (logoutButton) {
  logoutButton.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
  });
}

renderRecentKeywords();
loadHistory();
loadWatchKeywords();
loadTodaySummary();
loadMyPosts();
loadTrendKeywords();
