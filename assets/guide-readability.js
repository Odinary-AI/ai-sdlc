/* Optional read-only browser probe. Evaluate in the loaded page; no network or mutation.
 * Returned geometry is evidence, not a semantic/visual acceptance decision.
 * Defaults describe this package's diagrams. Pass explicit project baselines for custom SVG.
 */
(globalThis.auditGuideReadability = function(options = {}) {
  const root = document.querySelector(options.selector || 'main') || document.body;
  const failures = [], texts = [];
  const minimum = options.minimumTextPx ?? 14, titleMinimum = options.minimumTitlePx ?? 16;
  const graphs = [...root.querySelectorAll('svg')].filter(svg => svg.getBoundingClientRect().width > 0);
  if (!graphs.length) failures.push({code:'no-rendered-svg'});
  graphs.forEach((svg, graph) => {
    for (const text of svg.querySelectorAll('text')) {
      if (text.closest('defs')) continue;
      const style = getComputedStyle(text), matrix = text.getScreenCTM();
      if (!matrix || style.display === 'none' || style.visibility === 'hidden') continue;
      const scale = Math.min(Math.hypot(matrix.a,matrix.b), Math.hypot(matrix.c,matrix.d));
      const pixels = parseFloat(style.fontSize) * scale;
      const floor = text.matches('.basis') ? 12 : text.matches('.node-title') ? titleMinimum : minimum;
      texts.push({graph,text:text.textContent,pixels});
      if (!Number.isFinite(pixels) || pixels + .1 < floor) failures.push({code:'small-text',graph,text:text.textContent,pixels,minimum:floor});
      const container = text.closest('.node,.edge-label,.map-group');
      const rect = container && container.querySelector('rect');
      if (rect) {
        const a = text.getBoundingClientRect(), b = rect.getBoundingClientRect();
        if (a.left < b.left - 1 || a.right > b.right + 1 || a.top < b.top - 1 || a.bottom > b.bottom + 1)
          failures.push({code:'text-outside-box',graph,text:text.textContent});
      }
    }
    const scroller = svg.closest('.map-scroll');
    if(scroller && scroller.scrollWidth > scroller.clientWidth + 1) {
      if(!['auto','scroll'].includes(getComputedStyle(scroller).overflowX) || scroller.tabIndex < 0)
        failures.push({code:'wide-map-not-accessible',graph});
    }
  });
  if (!texts.length) failures.push({code:'no-rendered-text'});
  if (document.documentElement.scrollWidth > innerWidth + 1) failures.push({code:'page-overflow'});
  return {status:failures.length?'failed':'passed',graphs:graphs.length,texts,failures,
    boundary:'只检查当前可见SVG的显示字号、已识别底框及滚动入口；不证明对比度、关系语义、全部重叠、键盘实际可用或截图可读。'};
})
