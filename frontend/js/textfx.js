(function(){
  function escapeHtml(s){
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  
  window.mmRevealText = function(el, opts){
    if(!el) return;
    const stepMs = (opts && opts.stepMs) || 40;
    const startMs = (opts && opts.startMs) || 0;
    const text = el.textContent;
    let wi = 0;
    el.innerHTML = text.split(/(\s+)/).map(chunk => {
      if(!chunk.trim()) return chunk; // preserve whitespace as-is
      const delay = startMs + (wi++ * stepMs);
      return `<span class="mm-reveal-word" style="animation-delay:${delay}ms">${escapeHtml(chunk)}</span>`;
    }).join("");
  };

  // Highlights important standard codes, clause references and critical evidence
  // keywords inside already-rendered HTML (Ask AI answers + Research/Compliance
  // reports), so the reader's eye lands on the parts that matter most.
  const KEY_PATTERN = /\b(?:IS|SP|IRC)\s?\d{2,6}(?:\s*:\s*\d{4})?\b|\bclause\s+\d+(?:\.\d+)*\b|\b(?:MUST|SHALL|MANDATORY|REQUIRED|CRITICAL|PROHIBITED|IMPORTANT|WARNING|UNKNOWN|REQUIRES[_\s]VERIFICATION|NON[-\s]COMPLIANT|COMPLIANT|VERIFIED|UNVERIFIED|CONFORMS?)\b/gi;
  const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "CODE", "PRE", "A", "MARK", "TEXTAREA", "INPUT"]);

  window.mmHighlightKeywords = function(root){
    if(!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node){
        if(!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        let p = node.parentElement;
        while(p && p !== root){ if(SKIP_TAGS.has(p.tagName)) return NodeFilter.FILTER_REJECT; p = p.parentElement; }
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    const nodes = []; let n; while((n = walker.nextNode())) nodes.push(n);
    nodes.forEach(node => {
      const text = node.nodeValue;
      KEY_PATTERN.lastIndex = 0;
      if(!KEY_PATTERN.test(text)) return;
      KEY_PATTERN.lastIndex = 0;
      const frag = document.createDocumentFragment();
      let last = 0, m;
      while((m = KEY_PATTERN.exec(text))){
        if(m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        const mark = document.createElement("mark");
        mark.className = "mm-key";
        mark.textContent = m[0];
        frag.appendChild(mark);
        last = m.index + m[0].length;
      }
      if(last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
      node.parentNode.replaceChild(frag, node);
    });
  };
})();
