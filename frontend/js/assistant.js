function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
}
/**
 * Safely render AI responses as Markdown + LaTeX.
 *
 * Markdown is parsed to HTML and sanitized before it is inserted into the DOM.
 * KaTeX auto-render then upgrades supported math delimiters in text nodes.
 * Code/pre elements are ignored by KaTeX, so literal LaTeX in code remains code.
 */
function normalizeUndelimitedMath(source){
  let text = String(source ?? "");
  // Protect common standalone engineering equations that arrive without math delimiters.
  // Do not touch ordinary prose or fenced/code blocks.
  return text.split("\n").map(line => {
    const t = line.trim();
    if(!t || /^```/.test(t) || /^\s*[#>*-]/.test(t)) return line;
    if(/(?:^|\s)[A-Za-zα-ωΑ-Ω][A-Za-z0-9_{}()]*\s*(?:=|≤|≥)\s*[-+*/().A-Za-z0-9α-ωΑ-Ω{}_\\ ]+$/.test(t) && !t.includes("http")){
      const escaped = t.replace(/\$/g, "\\$");
      return `\\(${escaped}\\)`;
    }
    return line;
  }).join("\n");
}

function renderAiResponse(source){
  const markdown = normalizeUndelimitedMath(source);
  const renderedMarkdown = marked.parse(markdown, {
    gfm: true,
    breaks: true,
  });

  const sanitized = DOMPurify.sanitize(renderedMarkdown, {
    USE_PROFILES: { html: true },
  });

  const container = document.createElement("div");
  container.className = "ai-response-content";
  container.innerHTML = sanitized;

  renderMathInElement(container, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false },
      { left: "$", right: "$", display: false },
    ],
    throwOnError: false,
    strict: false,
    trust: false,
  });

  if(typeof window.mmHighlightKeywords === "function") window.mmHighlightKeywords(container);

  return container.innerHTML;
}

function findStandardByNumber(q){
  const norm = q.toLowerCase().replace(/[\s:]+/g, "");
  return STANDARDS.find(s => s.number.toLowerCase().replace(/[\s:]+/g, "").includes(norm.replace(/^is/, "is")))
      || STANDARDS.find(s => norm.includes(s.number.toLowerCase().replace(/[\s:]+/g,"").replace(/^is/,"")));
}

function keywordMatchStandards(q){
  const terms = q.toLowerCase().split(/\W+/).filter(w => w.length > 2 && !["the","for","and","what","how","get","are","list","find","does","latest","version"].includes(w));
  if(!terms.length) return [];
  return STANDARDS
    .map(s => {
      const hay = (s.title + " " + s.desc + " " + s.number + " " + s.category).toLowerCase();
      const score = terms.reduce((acc, t) => acc + (hay.includes(t) ? 1 : 0), 0);
      return { s, score };
    })
    .filter(r => r.score > 0)
    .sort((a,b) => b.score - a.score)
    .slice(0, 4)
    .map(r => r.s);
}

function keywordMatchServices(q){
  const terms = q.toLowerCase();
  return SERVICES.filter(sv => terms.includes(sv.id.split("-")[0]) || terms.includes(sv.name.toLowerCase().split(" ")[0]) || sv.name.toLowerCase().split(" ").some(w => w.length>3 && terms.includes(w)));
}

function answerQuery(raw){
  const q = raw.trim();
  const ql = q.toLowerCase();
  if(!q){
    return { title: "Ask me anything", html: "<p>Try a standard number like <b>IS 456</b>, or a question like “How do I get BIS certification?”.</p>", chips: ["What is IS 456?", "How to get BIS certification?"] };
  }

  if(/^is[\s-]?\d/.test(ql) || /\bis\s*\d{2,6}/.test(ql)){
    const hit = findStandardByNumber(q) || keywordMatchStandards(q)[0];
    if(hit){
      return {
        title: hit.number,
        html: `
          <p><b>${escapeHtml(hit.title)}</b></p>
          <p>${escapeHtml(hit.desc)}</p>
          <ul>
            <li>Status: <b>${hit.status}</b>${hit.reaffirmed ? ` · Reaffirmed ${hit.reaffirmed}` : ""}</li>
            <li>Technical department: ${hit.dept}</li>
            <li>Language: ${hit.language}</li>
          </ul>`,
        chips: ["Download PDF", "Related standards", "Applications"],
        standard: hit,
      };
    }
  }

  if(/(certif|isi mark|licen[sc]e|apply)/.test(ql)){
    return {
      title: "BIS Product Certification",
      html: `
        <p>Getting the ISI mark for your product takes four stages:</p>
        <ul>
          ${CERT_STEPS.map(s => `<li><b>${s.step}. ${s.title}</b> — ${s.detail}</li>`).join("")}
        </ul>
        <p>Processing time is typically 4–6 months depending on product category and lab availability.</p>`,
      chips: ["Start application", "Required documents", "Fee structure"],
      link: "certification.html",
    };
  }

  if(ql.includes("hallmark") || ql.includes("difference between isi")) {
    return {
      title: "ISI Mark vs Hallmark",
      html: `<p>The <b>ISI mark</b> certifies that an industrial product conforms to the relevant Indian Standard. The <b>Hallmark</b> specifically certifies the purity of gold and silver jewellery, issued through Assaying &amp; Hallmarking Centres.</p>`,
      chips: ["Hallmarking scheme", "Product Certification"],
    };
  }

  const faq = FAQS.find(f => {
    const words = f.q.toLowerCase().split(/\W+/).filter(w=>w.length>3);
    return words.some(w => ql.includes(w));
  });
  if(faq){
    return { title: faq.q, html: `<p>${escapeHtml(faq.a)}</p>`, chips: ["More FAQs"] };
  }

  const svcHits = keywordMatchServices(ql);
  if(svcHits.length){
    const sv = svcHits[0];
    return { title: sv.name, html: `<p>${escapeHtml(sv.detail)}</p>`, chips: ["Explore BIS Services"], link: "services.html" };
  }

  const stdHits = keywordMatchStandards(ql);
  if(stdHits.length){
    return {
      title: `${stdHits.length} related standard${stdHits.length>1?"s":""} found`,
      html: `<ul>${stdHits.map(s => `<li><b>${s.number}</b> — ${escapeHtml(s.title)}</li>`).join("")}</ul>`,
      chips: ["View all in Standards Search"],
      link: "standards.html",
    };
  }

  return {
    title: "Here's what I found",
    html: `<p>I couldn't find an exact match for “${escapeHtml(q)}”. Try searching by IS number (e.g. <b>IS 456</b>), or browse by category in Standards Search.</p>`,
    chips: ["Browse Standards", "Ask about certification", "BIS Services"],
    link: "standards.html",
  };
}

const SUGGESTED_PROMPTS = [
  "What is IS 456 and its latest version?",
  "How do I get BIS certification?",
  "ISI mark for electronics",
  "BIS labs near me",
  "Difference between ISI and Hallmark",
  "List standards for structural steel",
];

/* -------------------------------------------------------------------------
 * Phase 17: voice input/output layer.
 * This is deliberately a thin client-side adapter over the existing /chat
 * pipeline. No separate AI/translation call is made for voice.
 * ---------------------------------------------------------------------- */
const MM_VOICE_LANGUAGES = Object.freeze({
  "en-IN": "English",
  "hi-IN": "Hindi",
  "bn-IN": "Bengali",
  "te-IN": "Telugu",
  "mr-IN": "Marathi",
  "ta-IN": "Tamil",
  "gu-IN": "Gujarati",
  "kn-IN": "Kannada",
  "ml-IN": "Malayalam",
  "pa-IN": "Punjabi",
  "or-IN": "Odia",
  "as-IN": "Assamese",
  "ur-IN": "Urdu",
});

const MM_BROWSER_LOCALE_MAP = Object.freeze({
  "en": "en-IN", "en-in": "en-IN", "hi": "hi-IN", "hi-in": "hi-IN",
  "bn": "bn-IN", "bn-in": "bn-IN", "te": "te-IN", "te-in": "te-IN",
  "mr": "mr-IN", "mr-in": "mr-IN", "ta": "ta-IN", "ta-in": "ta-IN",
  "gu": "gu-IN", "gu-in": "gu-IN", "kn": "kn-IN", "kn-in": "kn-IN",
  "ml": "ml-IN", "ml-in": "ml-IN", "pa": "pa-IN", "pa-in": "pa-IN",
  "or": "or-IN", "or-in": "or-IN", "as": "as-IN", "as-in": "as-IN",
  "ur": "ur-IN", "ur-in": "ur-IN",
});

const MM_SPEECH_RECOGNITION = window.SpeechRecognition || window.webkitSpeechRecognition || null;
const mmVoice = {
  recognition: null,
  listening: false,
  paused: false,
  cancelled: false,
  processing: false,
  sendRequested: false,
  finalText: "",
  interimText: "",
  timer: null,
  selectedLocale: "auto",
  voices: [],
  activePlaybackButton: null,
  activePlaybackStopButton: null,
};

function mmVoiceElements(){
  return {
    mic: document.getElementById("chat-mic"),
    input: document.getElementById("chat-input"),
    inputBar: document.getElementById("chat-input-bar"),
    waveform: document.getElementById("voice-waveform"),
    searchIcon: document.getElementById("chat-search-icon"),
    language: document.getElementById("voice-language"),
    status: document.getElementById("voice-status"),
    record: document.getElementById("voice-record"),
    pause: document.getElementById("voice-pause"),
    send: document.getElementById("voice-send"),
    cancel: document.getElementById("voice-cancel"),
    stopSpeaking: document.getElementById("voice-stop-speaking"),
    actionGroup: document.getElementById("voice-action-group"),
    controls: document.getElementById("voice-controls"),
  };
}

function mmSetVoiceStatus(text, state = ""){
  const { status } = mmVoiceElements();
  if(!status) return;
  status.textContent = text || "";
  status.className = `voice-status${state ? ` ${state}` : ""}`;
}

function mmSetMicState(state){
  const { mic, input, inputBar, waveform, searchIcon, actionGroup } = mmVoiceElements();
  if(!mic) return;
  mic.classList.remove("voice-listening", "voice-processing", "is-hidden");
  if(inputBar) inputBar.classList.remove("voice-active", "voice-paused", "voice-processing");
  if(waveform) waveform.classList.remove("is-visible", "is-paused", "is-processing");
  if(searchIcon) searchIcon.classList.remove("is-hidden");
  if(actionGroup) actionGroup.classList.remove("is-visible");

  if(state === "listening"){
    mic.classList.add("voice-listening", "is-hidden");
    mic.setAttribute("aria-label", "Voice input active");
    mic.title = "Voice input active";
    if(input) input.placeholder = "Listening…";
    if(inputBar) inputBar.classList.add("voice-active");
    if(waveform) waveform.classList.add("is-visible");
    if(searchIcon) searchIcon.classList.add("is-hidden");
    if(actionGroup) actionGroup.classList.add("is-visible");
  }else if(state === "processing"){
    mic.classList.add("voice-processing", "is-hidden");
    mic.setAttribute("aria-label", "Voice processing");
    mic.title = "Processing voice input";
    if(input) input.placeholder = "Processing…";
    if(inputBar) inputBar.classList.add("voice-processing");
    if(waveform) waveform.classList.add("is-visible", "is-processing");
    if(searchIcon) searchIcon.classList.add("is-hidden");
  }else if(state === "paused"){
    mic.classList.add("is-hidden");
    mic.setAttribute("aria-label", "Resume voice input");
    mic.title = "Resume voice input";
    if(input) input.placeholder = "Review your voice question…";
    if(inputBar) inputBar.classList.add("voice-paused");
    if(waveform) waveform.classList.add("is-visible", "is-paused");
    if(searchIcon) searchIcon.classList.add("is-hidden");
    if(actionGroup) actionGroup.classList.add("is-visible");
  }else{
    mic.setAttribute("aria-label", "Start voice input");
    mic.title = "Voice input";
    if(input) input.placeholder = "Ask a follow-up question…";
  }
}

function mmSyncVoiceControls(){
  const { record, pause, send } = mmVoiceElements();
  const hasText = !!(String(mmVoice.finalText || "").trim() || String(mmVoiceElements().input?.value || "").trim());
  const active = mmVoice.listening || mmVoice.paused || mmVoice.processing || hasText;
  if(record){
    record.disabled = mmVoice.processing;
    record.title = mmVoice.listening ? "Recording voice" : "Resume recording";
  }
  if(pause) pause.disabled = !mmVoice.listening;
  if(send) send.disabled = !hasText || mmVoice.processing;
  if(!mmVoice.listening && !mmVoice.processing && active && mmVoice.paused) mmSetMicState("paused");
}

function mmSelectedVoiceLocale(){
  const { language } = mmVoiceElements();
  const requested = language?.value || mmVoice.selectedLocale || "auto";
  if(requested !== "auto") return requested;
  const browser = String(navigator.language || "en-IN").toLowerCase();
  return MM_BROWSER_LOCALE_MAP[browser] || MM_BROWSER_LOCALE_MAP[browser.split("-")[0]] || "en-IN";
}

function mmRecognitionSupported(){
  return !!MM_SPEECH_RECOGNITION;
}

function mmClearVoiceTimer(){
  if(mmVoice.timer){ clearTimeout(mmVoice.timer); mmVoice.timer = null; }
}

function mmStopRecognition(){
  mmClearVoiceTimer();
  if(mmVoice.recognition){
    try { mmVoice.recognition.stop(); } catch(_) {}
  }
}

function mmResetVoiceUI(){
  mmVoice.listening = false;
  mmVoice.paused = false;
  mmVoice.processing = false;
  mmSetMicState("idle");
  mmSyncVoiceControls();
}

function mmSpeechPlainText(source){
  let text = String(source || "");
  text = text.replace(/\n+Sources:\s*[\s\S]*$/i, "");
  text = text.replace(/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, "$1 divided by $2");
  text = text.replace(/\\text\s*\{([^{}]*)\}/g, "$1");
  text = text.replace(/\\(?:mathrm|mathbf|mathit|textbf|textit)\s*\{([^{}]*)\}/g, "$1");
  text = text.replace(/\^\{([^{}]*)\}/g, " to the power of $1");
  text = text.replace(/_\{([^{}]*)\}/g, " $1");
  text = text.replace(/\^([A-Za-z0-9])/g, " to the power of $1");
  text = text.replace(/_([A-Za-z0-9])/g, " $1");
  text = text.replace(/\\([a-zA-Z]+)(?![a-zA-Z])/g, "$1");
  text = text.replace(/\$\$?|\\\(|\\\)|\\\[|\\\]/g, " ");
  text = text.replace(/```[\s\S]*?```/g, "");
  text = text.replace(/`([^`]*)`/g, "$1");
  text = text.replace(/!\[[^\]]*\]\([^)]*\)/g, "");
  text = text.replace(/\[([^\]]+)\]\([^)]*\)/g, "$1");
  text = text.replace(/[*_~>#-]+/g, " ");
  text = text.replace(/[{}]/g, " ");
  return text.replace(/\s+/g, " ").trim();
}

function mmLoadTTSVoices(){
  if(!("speechSynthesis" in window)) return;
  mmVoice.voices = window.speechSynthesis.getVoices() || [];
}

function mmFindTTSVoice(locale){
  mmLoadTTSVoices();
  const wanted = String(locale || "").toLowerCase();
  const prefix = wanted.split("-")[0];
  const candidates = mmVoice.voices.filter(v => {
    const lang = String(v.lang || "").toLowerCase();
    return lang === wanted || lang.split("-")[0] === prefix;
  });
  if(!candidates.length) return null;

  // Prefer voices exposed by the browser/OS as enhanced, neural or natural
  // voices. Exact locale is preferred over language-only matches. This keeps
  // the app offline/browser-native while avoiding the most robotic fallback
  // when a higher-quality installed voice is available.
  const qualityTerms = [
    "natural", "neural", "enhanced", "premium", "wavenet", "studio",
    "samantha", "ava", "allison", "karen", "google", "microsoft"
  ];
  const score = (voice) => {
    const name = String(voice.name || "").toLowerCase();
    const lang = String(voice.lang || "").toLowerCase();
    let value = 0;
    if(lang === wanted) value += 100;
    else if(lang.split("-")[0] === prefix) value += 40;
    qualityTerms.forEach((term, index) => {
      if(name.includes(term)) value += 30 - Math.min(index, 10);
    });
    if(voice.localService === false) value += 8;
    return value;
  };
  return candidates.slice().sort((a,b) => score(b) - score(a))[0] || candidates[0];
}

function mmStopSpeaking(){
  if("speechSynthesis" in window) window.speechSynthesis.cancel();
  if(mmVoice.activePlaybackButton){
    mmVoice.activePlaybackButton.textContent = "🔊 Listen";
    mmVoice.activePlaybackButton.classList.remove("is-speaking");
  }
  if(mmVoice.activePlaybackStopButton){
    mmVoice.activePlaybackStopButton.hidden = true;
    mmVoice.activePlaybackStopButton.disabled = false;
  }
  mmVoice.activePlaybackButton = null;
  mmVoice.activePlaybackStopButton = null;
  if(!mmVoice.listening && !mmVoice.processing) mmSetVoiceStatus("");
}

function mmSpeak(text, locale, { notify = true } = {}){
  if(!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined"){
    if(notify) mmSetVoiceStatus("Voice playback isn't supported in this browser.", "error");
    return false;
  }
  const plain = mmSpeechPlainText(text);
  if(!plain) return false;
  const voice = mmFindTTSVoice(locale);
  if(!voice){
    if(notify) mmSetVoiceStatus(`No ${MM_VOICE_LANGUAGES[locale] || locale} voice is available in this browser. The text answer is still available.`, "error");
    return false;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(plain);
  utterance.lang = voice.lang || locale;
  utterance.voice = voice;
  // Slightly slower, natural conversational pacing. These values intentionally
  // stay close to normal speech so technical BIS answers remain intelligible.
  utterance.rate = 0.94;
  utterance.pitch = 1.02;
  utterance.volume = 1.0;
  utterance.onstart = () => {
    if(mmVoice.activePlaybackButton){
      mmVoice.activePlaybackButton.textContent = "🔊 Listening…";
      mmVoice.activePlaybackButton.classList.add("is-speaking");
    }
    if(mmVoice.activePlaybackStopButton) mmVoice.activePlaybackStopButton.hidden = false;
    mmSetVoiceStatus("Speaking…");
  };
  utterance.onend = () => {
    if(mmVoice.activePlaybackButton){
      mmVoice.activePlaybackButton.textContent = "🔊 Listen";
      mmVoice.activePlaybackButton.classList.remove("is-speaking");
      mmVoice.activePlaybackButton = null;
    }
    if(mmVoice.activePlaybackStopButton) mmVoice.activePlaybackStopButton.hidden = true;
    if(!mmVoice.listening && !mmVoice.processing) mmSetVoiceStatus("");
  };
  utterance.onerror = () => {
    if(mmVoice.activePlaybackButton){
      mmVoice.activePlaybackButton.textContent = "🔊 Listen";
      mmVoice.activePlaybackButton.classList.remove("is-speaking");
      mmVoice.activePlaybackButton = null;
    }
    if(mmVoice.activePlaybackStopButton) mmVoice.activePlaybackStopButton.hidden = true;
    if(!mmVoice.listening && !mmVoice.processing) mmSetVoiceStatus("Voice playback stopped. The text answer is still available.", "error");
  };
  window.speechSynthesis.speak(utterance);
  return true;
}

function mmAddReplayButton(container, reply, locale){
  if(!container || !reply) return;
  const actions = document.createElement("div");
  actions.className = "msg-actions voice-playback-actions";

  const listen = document.createElement("button");
  listen.type = "button";
  listen.className = "chip voice-replay";
  listen.textContent = "🔊 Listen";
  listen.setAttribute("aria-label", `Read response aloud in ${MM_VOICE_LANGUAGES[locale] || locale}`);

  const stop = document.createElement("button");
  stop.type = "button";
  stop.className = "chip voice-stop";
  stop.textContent = "⏹ Stop";
  stop.setAttribute("aria-label", "Stop AI voice reply");
  stop.title = "Stop AI voice reply";
  stop.hidden = true;

  listen.addEventListener("click", () => {
    // Listen is deliberately independent from Stop: clicking it always starts
    // the complete answer from the beginning.
    mmStopSpeaking();
    mmVoice.activePlaybackButton = listen;
    mmVoice.activePlaybackStopButton = stop;
    const started = mmSpeak(reply, locale);
    if(!started){
      mmVoice.activePlaybackButton = null;
      mmVoice.activePlaybackStopButton = null;
      listen.textContent = "🔊 Listen";
      stop.hidden = true;
    }
  });

  stop.addEventListener("click", () => {
    if(mmVoice.activePlaybackButton === listen) mmStopSpeaking();
    else if("speechSynthesis" in window) window.speechSynthesis.cancel();
  });

  actions.appendChild(listen);
  actions.appendChild(stop);
  container.appendChild(actions);
}

function mmStartVoiceInput({ resume = false } = {}){
  if(!mmRecognitionSupported()){
    mmSetVoiceStatus("Voice input isn't supported in this browser. You can still type your question.", "error");
    return;
  }
  if(mmVoice.processing || mmVoice.listening) return;

  if("speechSynthesis" in window) window.speechSynthesis.cancel();
  const locale = mmSelectedVoiceLocale();
  const Recognition = MM_SPEECH_RECOGNITION;
  const recognition = new Recognition();
  mmVoice.recognition = recognition;
  mmVoice.listening = true;
  mmVoice.paused = false;
  mmVoice.cancelled = false;
  mmVoice.sendRequested = false;
  if(!resume){
    mmVoice.finalText = "";
    mmVoice.interimText = "";
  }

  recognition.lang = locale;
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    mmSetMicState("listening");
    mmSetVoiceStatus(`Recording… ${MM_VOICE_LANGUAGES[locale] || locale}`, "listening");
    mmSyncVoiceControls();
    mmVoice.timer = setTimeout(() => {
      if(mmVoice.listening){
        mmSetVoiceStatus("Recording paused after the browser safety timeout. Review the text and press Send.", "listening");
        mmVoice.paused = true;
        mmStopRecognition();
      }
    }, 60000);
  };

  recognition.onresult = event => {
    let finalText = "";
    let interimText = "";
    for(let i = event.resultIndex; i < event.results.length; i++){
      const text = event.results[i][0]?.transcript || "";
      if(event.results[i].isFinal) finalText += text + " ";
      else interimText += text;
    }
    if(finalText) mmVoice.finalText = `${mmVoice.finalText} ${finalText}`.trim();
    mmVoice.interimText = interimText;
    const { input } = mmVoiceElements();
    if(input) input.value = `${mmVoice.finalText} ${mmVoice.interimText}`.trim();
    mmSyncVoiceControls();
  };

  recognition.onerror = event => {
    mmClearVoiceTimer();
    mmVoice.listening = false;
    const code = String(event.error || "unknown");
    if(code === "no-speech"){
      mmVoice.paused = true;
      mmResetVoiceUI();
      mmSetVoiceStatus("No speech detected. Review the text or press Record to continue.", "error");
      return;
    }
    mmVoice.paused = false;
    mmResetVoiceUI();
    const messages = {
      "not-allowed": "Microphone permission was denied. Please allow microphone access and try again.",
      "service-not-allowed": "This browser's speech service is unavailable. You can still type your question.",
      "audio-capture": "No working microphone was found.",
      "language-not-supported": `This browser does not support ${MM_VOICE_LANGUAGES[locale] || locale} speech recognition. Select another voice language or type your question.`,
      "network": "Speech recognition needs a network connection and could not reach the browser speech service.",
      "aborted": "Voice input was cancelled.",
    };
    mmSetVoiceStatus(messages[code] || "Unable to recognize speech. You can still type your question.", "error");
  };

  recognition.onend = () => {
    mmClearVoiceTimer();
    mmVoice.listening = false;
    const text = String(mmVoice.finalText || "").trim();
    const shouldSend = mmVoice.sendRequested;
    mmVoice.sendRequested = false;

    if(mmVoice.cancelled){
      mmResetVoiceUI();
      return;
    }

    mmVoice.paused = true;
    mmSetMicState("paused");
    mmSyncVoiceControls();
    if(shouldSend && text && typeof respond === "function"){
      const { input } = mmVoiceElements();
      mmVoice.processing = true;
      mmSetMicState("processing");
      mmSetVoiceStatus("Processing…");
      mmSyncVoiceControls();
      const accepted = respond(text, { inputType: "voice", language: locale, speak: true });
      if(input && accepted) input.value = "";
      if(accepted){ mmVoice.finalText = ""; mmVoice.interimText = ""; }
      mmVoice.processing = false;
      mmResetVoiceUI();
      return;
    }

    const { input } = mmVoiceElements();
    if(input) input.value = text;
    if(text) mmSetVoiceStatus("Paused — review your question, then Send.");
    mmSyncVoiceControls();
  };

  try {
    recognition.start();
  } catch(err){
    mmVoice.listening = false;
    mmResetVoiceUI();
    mmSetVoiceStatus("Unable to start the microphone. Please try again.", "error");
  }
}

function mmPauseVoiceInput(){
  if(!mmVoice.listening) return;
  mmVoice.sendRequested = false;
  mmVoice.paused = true;
  mmSetVoiceStatus("Pausing…");
  mmStopRecognition();
}

function mmSendVoiceQuestion(){
  const { input } = mmVoiceElements();
  const text = String(mmVoice.finalText || input?.value || "").trim();
  if(!text || mmVoice.processing) return;

  if(mmVoice.listening){
    mmVoice.sendRequested = true;
    mmSetVoiceStatus("Finishing recording…");
    mmStopRecognition();
    return;
  }

  mmVoice.processing = true;
  mmSetMicState("processing");
  mmSetVoiceStatus("Processing…");
  const locale = mmSelectedVoiceLocale();
  const accepted = typeof respond === "function" ? respond(text, { inputType: "voice", language: locale, speak: true }) : false;
  if(accepted && input) input.value = "";
  mmVoice.finalText = "";
  mmVoice.interimText = "";
  mmVoice.processing = false;
  mmResetVoiceUI();
}

function mmCancelVoiceInput(){
  mmVoice.cancelled = true;
  mmVoice.sendRequested = false;
  mmStopRecognition();
  mmVoice.finalText = "";
  mmVoice.interimText = "";
  const { input } = mmVoiceElements();
  if(input) input.value = "";
  mmResetVoiceUI();
  mmSetVoiceStatus("Voice recording cancelled.");
}

function mmBindVoiceUI(){
  const { mic, language, record, pause, send, cancel } = mmVoiceElements();
  if(!mic) return;
  if(language){
    mmVoice.selectedLocale = language.value || "auto";
    language.addEventListener("change", () => { mmVoice.selectedLocale = language.value || "auto"; });
  }

  const canResume = () => !!mmVoice.finalText && !!String(mmVoiceElements().input?.value || "").trim();
  mic.addEventListener("click", () => {
    if(mmVoice.listening) mmPauseVoiceInput();
    else mmStartVoiceInput({ resume: canResume() });
  });
  record?.addEventListener("click", () => mmStartVoiceInput({ resume: canResume() }));
  pause?.addEventListener("click", mmPauseVoiceInput);
  send?.addEventListener("click", mmSendVoiceQuestion);
  cancel?.addEventListener("click", mmCancelVoiceInput);
  document.addEventListener("keydown", event => {
    if(event.key === "Escape" && (mmVoice.listening || mmVoice.paused)) mmCancelVoiceInput();
  });

  if("speechSynthesis" in window && typeof window.speechSynthesis.onvoiceschanged !== "undefined"){
    window.speechSynthesis.addEventListener("voiceschanged", mmLoadTTSVoices);
  }
  mmLoadTTSVoices();
  mmSyncVoiceControls();
}
