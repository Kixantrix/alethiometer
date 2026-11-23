// Assemble mode: plays the step-by-step guide (assets/assembly.json, written by
// hardware/assembly/guide.py) over the viewer's scene. guide.py replays the whole build and hands
// us each step's start state and per-instance tracks; this module only interpolates them.
import * as THREE from 'three';

const ACTIVE = new THREE.Color(0x10303a);
const KIND_ICON = { apply: '●', tool: '◆', check: '✓' };
const ease = (s) => (s < 0.5 ? 4 * s * s * s : 1 - Math.pow(-2 * s + 2, 3) / 2);
const clamp01 = (v) => Math.min(1, Math.max(0, v));

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

// Just enough Markdown for the guide's prose: paragraphs, lists, tables, **bold**, *italic*,
// `code` and links. Repository-relative links can't be followed from the viewer, so they are
// shown as references with the path in a tooltip.
function inline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<i>$2</i>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, text, url) => (/^https?:/.test(url)
      ? `<a href="${url}" target="_blank" rel="noopener">${text}</a>`
      : `<span class="ref" title="${url}">${text}</span>`));
}

export function markdown(src) {
  const out = [];
  const blocks = String(src || '').trim().split(/\n\s*\n/);
  for (const block of blocks) {
    const lines = block.split('\n');
    if (lines.every((l) => /^\s*\|/.test(l))) {
      const rows = lines.filter((l) => !/^\s*\|[\s|:-]+\|\s*$/.test(l))
        .map((l) => l.trim().replace(/^\||\|$/g, '').split('|').map((c) => inline(c.trim())));
      out.push('<table>' + rows.map((r, i) => '<tr>' + r.map((c) => (i ? `<td>${c}</td>` : `<th>${c}</th>`)).join('') + '</tr>').join('') + '</table>');
    } else if (lines.every((l, i) => /^\s*([-*]|\d+\.)\s/.test(l) || (i && /^\s{2,}\S/.test(l)))) {
      const ordered = /^\s*\d+\./.test(lines[0]);
      const items = [];
      for (const l of lines) {
        if (/^\s*([-*]|\d+\.)\s/.test(l)) items.push(l.replace(/^\s*([-*]|\d+\.)\s+/, ''));
        else items[items.length - 1] += ' ' + l.trim();
      }
      const tag = ordered ? 'ol' : 'ul';
      out.push(`<${tag}>` + items.map((i) => `<li>${inline(i)}</li>`).join('') + `</${tag}>`);
    } else if (/^###\s/.test(lines[0])) {
      out.push(`<h4>${inline(lines[0].replace(/^###\s+/, ''))}</h4>`);
      if (lines.length > 1) out.push(markdown(lines.slice(1).join('\n')));
    } else {
      out.push(`<p>${inline(lines.join(' '))}</p>`);
    }
  }
  return out.join('');
}

function poseMatrix(p, m = new THREE.Matrix4()) {
  m.identity();
  if (p.rot && p.rot.deg) {
    const [ax, ay, az] = p.rot.axis;
    const [cx, cy, cz] = p.rot.about;
    m.makeTranslation(cx, cy, cz)
      .multiply(new THREE.Matrix4().makeRotationAxis(new THREE.Vector3(ax, ay, az), THREE.MathUtils.degToRad(p.rot.deg)))
      .multiply(new THREE.Matrix4().makeTranslation(-cx, -cy, -cz));
  }
  m.premultiply(new THREE.Matrix4().makeTranslation(p.t[0], p.t[1], p.t[2]));
  return m;
}

function lerpPose(a, b, s) {
  const t = a.t.map((v, i) => v + (b.t[i] - v) * s);
  if (!a.rot && !b.rot) return { t, rot: null };
  const frame = a.rot || b.rot;
  const da = a.rot ? a.rot.deg : 0, db = b.rot ? b.rot.deg : 0;
  return { t, rot: { axis: frame.axis, about: frame.about, deg: da + (db - da) * s } };
}

const HOME = { t: [0, 0, 0], rot: null };

export function createAssembly(ctx) {
  const { root, parts, manifest, lidMatrix, $ } = ctx;
  let data = null;
  const insts = new Map();          // key -> { rec, meshes, corners (installed CAD bbox corners) }
  const asm = { index: 0, t: 0, playing: false, speed: 1, playAll: false, wait: 0, active: false };
  const markerGroup = new THREE.Group();
  const driverGroup = new THREE.Group();
  root.add(markerGroup, driverGroup);
  markerGroup.visible = driverGroup.visible = false;
  let markers = [], drivers = [], activeRecs = new Set();
  const tmp = new THREE.Matrix4(), tmpV = new THREE.Vector3();

  // ---------------------------------------------------------------- instances
  function buildInstances() {
    insts.clear();
    for (const rec of parts) {
      const groups = rec.meta.name === manifest.pcb?.attach && rec.meshes.length !== rec.meta.placements.length
        ? [rec.meshes] : rec.meshes.map((m) => [m]);
      groups.forEach((meshes, i) => {
        const box = new THREE.Box3();
        for (const m of meshes) {
          if (!m.geometry.boundingBox) m.geometry.computeBoundingBox();
          box.union(m.geometry.boundingBox.clone().applyMatrix4(m.userData.base));
        }
        const corners = [];
        for (let k = 0; k < 8; k++) {
          corners.push(new THREE.Vector3(k & 1 ? box.max.x : box.min.x, k & 2 ? box.max.y : box.min.y,
            k & 4 ? box.max.z : box.min.z));
        }
        insts.set(`${rec.meta.name}#${i}`, { rec, meshes, corners, center: box.getCenter(new THREE.Vector3()) });
      });
    }
    for (const rec of parts) {
      for (const mat of rec.materials) {
        mat.userData.baseOpacity ??= mat.opacity;
        mat.userData.baseTransparent ??= mat.transparent;
      }
    }
  }

  // ---------------------------------------------------------------- timeline
  const step = () => data.steps[asm.index];

  function segAt(segs, t) {
    let seg = segs[0];
    for (const s of segs) if (t >= s.t0) seg = s;
    return seg;
  }

  function lidAt(S, t) {
    const L = S.lid;
    if (L.t1 <= L.t0) return L.b;
    if (t <= L.t0) return L.a;
    if (t >= L.t1) return L.b;
    return L.a + (L.b - L.a) * ease((t - L.t0) / (L.t1 - L.t0));
  }

  // Pose, spin angle, opacity and presence of one instance at time t of step S.
  function instState(S, key, t) {
    const segs = S.tracks[key];
    if (!segs) return { pose: S.start[key] ?? HOME, spin: 0, opacity: 1, present: key in S.start, seg: null };
    const seg = segAt(segs, t);
    const inStart = key in S.start;
    let present = inStart || t >= segs[0].t0;
    const s = seg.t1 > seg.t0 ? clamp01((t - seg.t0) / (seg.t1 - seg.t0)) : (t >= seg.t1 ? 1 : 0);
    const k = ease(s);
    let opacity = 1;
    if (seg.fade === 'in') opacity = t < seg.t0 ? 0 : s;
    else if (seg.fade === 'out') opacity = 1 - s;
    if (seg.remove && t > seg.t1 && seg === segs[segs.length - 1]) present = false;
    const moving = seg.a.t.some((v, i) => Math.abs(v - seg.b.t[i]) > 1e-6);
    let spin = 0;
    if (seg.spin && t >= seg.t0) spin = (moving ? k : Math.sin(Math.PI * s)) * seg.spin * Math.PI * 2;
    return { pose: lerpPose(seg.a, seg.b, k), spin, opacity, present, seg, moving, s };
  }

  function instMatrix(key, pose, lidDeg, spin, seg, out = new THREE.Matrix4()) {
    const inst = insts.get(key);
    poseMatrix(pose, out);
    if (inst?.rec.lidPart) out.multiply(lidMatrix(lidDeg));
    if (spin && inst) {
      let axis = new THREE.Vector3(0, 0, 1);
      if (seg) {
        const d = new THREE.Vector3().fromArray(seg.b.t).sub(new THREE.Vector3().fromArray(seg.a.t));
        if (d.lengthSq() > 1e-9) axis = d.normalize();
      }
      const c = inst.center.clone().applyMatrix4(out);
      out.premultiply(new THREE.Matrix4().makeTranslation(-c.x, -c.y, -c.z))
        .premultiply(new THREE.Matrix4().makeRotationAxis(axis, spin))
        .premultiply(new THREE.Matrix4().makeTranslation(c.x, c.y, c.z));
    }
    return out;
  }

  // ---------------------------------------------------------------- per-frame update
  function update() {
    const S = step();
    const t = asm.t;
    const lid = lidAt(S, t);
    const visible = new Set(S.visible);
    const opacity = new Map();
    const highlight = new Set();
    for (const [key, inst] of insts) {
      if (!visible.has(key)) { for (const m of inst.meshes) m.visible = false; continue; }
      const st = instState(S, key, t);
      const on = st.present && st.opacity > 0.001;
      instMatrix(key, st.pose, lid, st.spin, st.seg, tmp);
      for (const m of inst.meshes) {
        m.visible = on;
        m.matrix.multiplyMatrices(tmp, m.userData.base);
        m.matrixWorldNeedsUpdate = true;
      }
      if (on && st.opacity < 1) opacity.set(inst.rec, Math.min(opacity.get(inst.rec) ?? 1, st.opacity));
      if (st.seg && t >= st.seg.t0 && t <= st.seg.t1 + 0.25) highlight.add(inst.rec);
    }
    for (const rec of parts) {
      const o = opacity.get(rec) ?? 1;
      for (const mat of rec.materials) {
        const base = mat.userData.baseOpacity ?? 1;
        const transparent = o < 1 || mat.userData.baseTransparent;
        if (mat.transparent !== transparent) { mat.transparent = transparent; mat.needsUpdate = true; }
        mat.opacity = base * o;
        mat.depthWrite = !transparent;
        if (mat.emissive && rec !== ctx.state.selected) mat.emissive.copy(highlight.has(rec) ? ACTIVE : BLACK);
      }
    }
    activeRecs = highlight;
    updateMarkers(S, t, lid);
    updateDrivers(S, t, lid);
  }
  const BLACK = new THREE.Color(0x000000);

  // ---------------------------------------------------------------- markers
  function clearMarkers() {
    for (const m of markers) { markerGroup.remove(m.mesh); m.label?.remove(); }
    markers = [];
  }

  function buildMarkers(S) {
    clearMarkers();
    const geom = new THREE.SphereGeometry(0.9, 16, 12);
    S.apply.forEach((a) => {
      const style = data.markers[a.what] ?? { label: a.what, color: '#ffffff' };
      const mat = new THREE.MeshBasicMaterial({ color: style.color, depthTest: false, transparent: true, opacity: 0.95 });
      a.at.forEach((at, i) => {
        const mesh = new THREE.Mesh(geom, mat);
        mesh.renderOrder = 20;
        markerGroup.add(mesh);
        let label = null;
        if (i === 0) {
          label = document.createElement('div');
          label.className = 'mlabel';
          label.style.borderColor = style.color;
          label.innerHTML = `<span style="color:${style.color}">${KIND_ICON[style.kind] ?? '●'}</span> ${esc(style.label)}`;
          if (a.note) label.title = a.note;
          $('labels').append(label);
        }
        markers.push({ mesh, label, a, at, p: new THREE.Vector3().fromArray(at.p), off: new THREE.Vector3().fromArray(a.offset) });
      });
    });
  }

  function updateMarkers(S, t, lid) {
    for (const m of markers) {
      const st = instState(S, m.at.key, t);
      // A marker on a part that arrives later in the step waits for it; markers on parts not in
      // the step (reference positions, e.g. holes to drill) show from their time.
      const on = t >= m.a.time && (!(m.at.key in S.tracks) || st.present);
      instMatrix(m.at.key, st.pose, lid, 0, st.seg, tmp);
      m.mesh.position.copy(m.p).applyMatrix4(tmp).add(m.off);
      m.mesh.visible = on;
      m.mesh.scale.setScalar(on ? 1 + 0.25 * Math.sin((t - m.a.time) * 6) : 1);
      if (m.label) m.label.dataset.on = on ? '1' : '';
    }
  }

  // HTML labels are positioned after the frame is rendered, from the markers' screen positions.
  function placeLabels(camera, canvas) {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    for (const m of markers) {
      if (!m.label) continue;
      if (!asm.active || !m.label.dataset.on) { m.label.style.display = 'none'; continue; }
      m.mesh.getWorldPosition(tmpV).project(camera);
      if (tmpV.z > 1) { m.label.style.display = 'none'; continue; }
      m.label.style.display = '';
      m.label.style.left = `${(tmpV.x + 1) / 2 * w}px`;
      m.label.style.top = `${(1 - tmpV.y) / 2 * h}px`;
    }
  }

  // ---------------------------------------------------------------- screwdrivers
  function buildDrivers(S) {
    for (const d of drivers) driverGroup.remove(d.mesh);
    drivers = [];
    const mat = new THREE.MeshStandardMaterial({ color: 0x9aa0a6, metalness: 0.8, roughness: 0.35, transparent: true, opacity: 0.85 });
    for (const [key, segs] of Object.entries(S.tracks)) {
      for (const seg of segs) {
        if (!seg.driver || !insts.has(key)) continue;
        const d = seg.driver.d ?? 3, len = seg.driver.len ?? 40;
        const geom = new THREE.CylinderGeometry(d / 2, d / 2, len, 20, 1, !!seg.driver.bore);
        const mesh = new THREE.Mesh(geom, mat);
        mesh.visible = false;
        driverGroup.add(mesh);
        drivers.push({ mesh, key, seg, len, gap: seg.driver.gap ?? 0.05 });
      }
    }
  }

  function updateDrivers(S, t, lid) {
    for (const dv of drivers) {
      const { seg } = dv;
      const on = t >= seg.t0 && t <= seg.t1 + 0.4 && visibleKey(S, dv.key);
      dv.mesh.visible = on;
      if (!on) continue;
      const dir = new THREE.Vector3().fromArray(seg.b.t).sub(new THREE.Vector3().fromArray(seg.a.t));
      if (dir.lengthSq() < 1e-9) { dv.mesh.visible = false; continue; }
      dir.normalize();
      const st = instState(S, dv.key, t);
      instMatrix(dv.key, st.pose, lid, 0, st.seg, tmp);
      const inst = insts.get(dv.key);
      const pts = inst.corners.map((c) => c.clone().applyMatrix4(tmp));
      const c = inst.center.clone().applyMatrix4(tmp);
      const back = Math.min(...pts.map((p) => p.clone().sub(c).dot(dir)));
      const head = c.addScaledVector(dir, back - dv.gap);
      dv.mesh.position.copy(head).addScaledVector(dir, -dv.len / 2);
      dv.mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().negate());
      dv.mesh.rotateY(st.spin);
    }
  }

  const visibleKey = (S, key) => S.visible.includes(key);

  // ---------------------------------------------------------------- framing
  function stepBox(S) {
    const box = new THREE.Box3();
    const add = (key, t) => {
      if (!insts.has(key)) return;
      const st = instState(S, key, t);
      instMatrix(key, st.pose, lidAt(S, t), 0, st.seg, tmp);
      for (const c of insts.get(key).corners) box.expandByPoint(c.clone().applyMatrix4(tmp));
    };
    const moving = Object.keys(S.tracks).filter((k) => S.tracks[k].some((s) => s.a.t.some((v, i) => Math.abs(v - s.b.t[i]) > 1e-6)
      || (s.a.rot?.deg ?? 0) !== (s.b.rot?.deg ?? 0) || s.fade));
    for (const key of moving) for (const s of S.tracks[key]) {
      if (s.fade === 'out') continue;                         // leaving: don't frame it
      add(key, s.t0); add(key, s.t1);
    }
    for (const key of S.frame) add(key, S.duration);
    if (box.isEmpty() || (S.lid.a !== S.lid.b && !S.frame.length)) {
      for (const key of S.visible) add(key, S.duration);
    }
    if (S.apply.length) {
      for (const m of markers) box.expandByPoint(m.mesh.position);
    }
    return box;
  }

  // ---------------------------------------------------------------- UI
  function renderCard(S) {
    const sec = data.sections.find((s) => s.number === S.section);
    $('stepNum').textContent = `Step ${asm.index + 1} of ${data.steps.length} · ${S.num}`;
    $('stepSection').textContent = sec ? `§${sec.number} ${sec.title}` : '';
    $('stepTitle').innerHTML = (S.test ? '<span class="badge">Test</span> ' : '') + esc(S.title);
    const html = [];
    const first = data.steps.findIndex((s) => s.section === S.section) === asm.index;
    if (first && sec?.intro) {
      html.push(`<details class="intro"><summary>About this section</summary>${markdown(sec.intro)}</details>`);
    }
    html.push(markdown(S.text));
    if (S.apply.length) {
      const seen = new Set();
      const chips = [];
      for (const a of S.apply) {
        const style = data.markers[a.what] ?? { label: a.what, color: '#fff' };
        const id = a.what + '|' + a.note;
        if (seen.has(id)) continue;
        seen.add(id);
        chips.push(`<span class="chip" title="${esc(a.note || '')}"><span class="dot" style="background:${style.color}"></span>${esc(style.label)}${a.note ? ': ' + esc(a.note) : ''}</span>`);
      }
      html.push(`<h4>Apply / mark</h4><div class="chips">${chips.join('')}</div>`);
    }
    if (S.tools.length) html.push(`<h4>Tools</h4><div class="chips">${S.tools.map((t) => `<span class="chip">${esc(t)}</span>`).join('')}</div>`);
    if (S.checks.length) html.push(`<h4>${S.test ? 'Passes when' : 'Check'}</h4><ul class="notes checks">${S.checks.map((c) => `<li>${inline(c)}</li>`).join('')}</ul>`);
    if (S.fixes.length) html.push(`<h4>If it fails</h4><ul class="notes fixes">${S.fixes.map((c) => `<li>${inline(c)}</li>`).join('')}</ul>`);
    if (S.cautions.length) html.push(`<h4>Caution</h4><ul class="notes cautions">${S.cautions.map((c) => `<li>${inline(c)}</li>`).join('')}</ul>`);
    if (S.findings.length) html.push('<h4>Design review</h4>' + S.findings.map((f) => findingHtml(data.findings[f])).join(''));
    const moving = [...new Set(Object.keys(S.tracks).map((k) => k.split('#')[0]))]
      .map((n) => parts.find((p) => p.meta.name === n)).filter(Boolean);
    if (moving.length) {
      const chips = moving.map((r) => {
        const n = Object.keys(S.tracks).filter((k) => k.startsWith(r.meta.name + '#')).length;
        const c = r.meta.color.map((v) => Math.round(v * 255)).join(',');
        return `<span class="chip part" data-part="${esc(r.meta.name)}"><span class="dot" style="background:rgb(${c})"></span>${esc(r.meta.name)}${n > 1 ? ' ×' + n : ''}</span>`;
      }).join('');
      html.push(moving.length > 12
        ? `<details><summary><h4 style="display:inline">Parts in this step (${moving.length})</h4></summary><div class="chips">${chips}</div></details>`
        : `<h4>Parts in this step</h4><div class="chips">${chips}</div>`);
    }
    $('stepCard').innerHTML = html.join('');
    $('stepCard').scrollTop = 0;
    $('stepCard').querySelectorAll('.chip.part').forEach((el) => el.addEventListener('click', () => {
      ctx.select(parts.find((p) => p.meta.name === el.dataset.part) ?? null);
    }));
    $('stepPrev').disabled = asm.index === 0;
    $('stepNext').disabled = asm.index === data.steps.length - 1;
    document.querySelectorAll('#toc .st').forEach((el) => el.classList.toggle('current', +el.dataset.i === asm.index));
    document.querySelector('#toc .st.current')?.scrollIntoView({ block: 'nearest' });
  }

  function findingHtml(f, open = false) {
    if (!f) return '';
    const steps = data.steps.map((s, i) => (s.findings.includes(f.id) ? `<a href="#assemble/${s.id}" data-goto="${i}">${s.num}</a>` : null))
      .filter(Boolean);
    return `<details class="finding"${open ? ' open' : ''}><summary><b>${esc(f.id)}</b> ${esc(f.title)}</summary>`
      + `<div class="meta">Impact: ${esc(f.impact)} · Status: ${esc(f.status)}${f.area ? ' · ' + esc(f.area) : ''}`
      + (steps.length ? ` · Steps ${steps.join(', ')}` : '') + '</div>'
      + `<p><b>Observation.</b> ${inline(f.observation.trim().replace(/\n/g, ' '))}</p>`
      + `<p><b>Recommendation.</b> ${inline(f.recommendation.trim().replace(/\n/g, ' '))}</p></details>`;
  }

  function buildToc() {
    const ol = $('toc');
    ol.innerHTML = '';
    let sec = null;
    data.steps.forEach((S, i) => {
      if (S.section !== sec) {
        sec = S.section;
        const s = data.sections.find((x) => x.number === sec);
        const li = document.createElement('li');
        li.className = 'sec';
        li.textContent = `§${s.number} ${s.title}`;
        ol.append(li);
      }
      const li = document.createElement('li');
      li.className = 'st';
      li.dataset.i = i;
      li.innerHTML = `<span class="n">${S.num}</span><span>${S.test ? '<span class="badge">Test</span> ' : ''}${esc(S.title)}</span>`
        + (S.findings.length ? `<span class="flag" title="Design review: ${S.findings.join(', ')}">⚑</span>` : '');
      li.addEventListener('click', () => go(i, true));
      ol.append(li);
    });
    $('tocCount').textContent = `(${data.steps.length})`;
    const order = { high: 0, medium: 1, low: 2 };
    const fs = Object.values(data.findings).sort((a, b) => (order[a.impact] ?? 9) - (order[b.impact] ?? 9) || a.id.localeCompare(b.id));
    $('review').innerHTML = fs.map((f) => findingHtml(f)).join('');
    $('reviewCount').textContent = `(${fs.length})`;
  }

  document.addEventListener('click', (e) => {
    const a = e.target.closest('[data-goto]');
    if (!a) return;
    e.preventDefault();
    go(+a.dataset.goto, true);
  });

  // ---------------------------------------------------------------- control
  function go(i, autoplay = false) {
    asm.index = Math.max(0, Math.min(data.steps.length - 1, i));
    asm.t = 0;
    asm.wait = 0;
    const S = step();
    buildMarkers(S);
    buildDrivers(S);
    renderCard(S);
    setPlaying(autoplay);
    update();
    ctx.frame(stepBox(S), S.view);
    history.replaceState(null, '', `#assemble/${S.id}`);
    $('scrub').value = 0;
  }

  function setPlaying(on) {
    asm.playing = on;
    $('stepPlay').innerHTML = on ? '&#x23F8;' : '&#x25B6;';
  }

  function tick(dt) {
    if (!asm.active || !data) return;
    const S = step();
    if (asm.playing) {
      asm.t = Math.min(S.duration, asm.t + dt * asm.speed);
      $('scrub').value = S.duration ? asm.t / S.duration : 1;
      if (asm.t >= S.duration) {
        if (asm.playAll && asm.index < data.steps.length - 1) {
          asm.wait += dt;
          if (asm.wait > 1.2) go(asm.index + 1, true);
        } else {
          setPlaying(false);
        }
      }
    }
    update();
  }

  function togglePlay() {
    const S = step();
    if (!asm.playing && asm.t >= S.duration) asm.t = 0;
    setPlaying(!asm.playing);
  }

  $('stepPrev').addEventListener('click', () => go(asm.index - 1, true));
  $('stepNext').addEventListener('click', () => go(asm.index + 1, true));
  $('stepPlay').addEventListener('click', togglePlay);
  $('scrub').addEventListener('input', (e) => {
    setPlaying(false);
    asm.t = +e.target.value * step().duration;
  });
  $('speed').addEventListener('change', (e) => { asm.speed = +e.target.value; });
  $('playAll').addEventListener('change', (e) => {
    asm.playAll = e.target.checked;
    if (asm.playAll && !asm.playing) togglePlay();
  });

  return {
    async load() {
      try {
        const res = await fetch('assets/assembly.json', { cache: 'no-cache' });
        if (!res.ok) throw new Error(res.status);
        data = await res.json();
      } catch {
        return false;
      }
      buildInstances();
      buildToc();
      return true;
    },
    get loaded() { return !!data; },
    get state() { return asm; },
    get data() { return data; },
    enter(id) {
      asm.active = true;
      markerGroup.visible = driverGroup.visible = true;
      $('labels').hidden = false;
      const i = id ? data.steps.findIndex((s) => s.id === id) : asm.index;
      go(i >= 0 ? i : 0, false);
    },
    leave() {
      asm.active = false;
      setPlaying(false);
      markerGroup.visible = driverGroup.visible = false;
      $('labels').hidden = true;
      for (const rec of parts) {
        for (const mat of rec.materials) {
          mat.opacity = mat.userData.baseOpacity ?? 1;
          mat.transparent = !!mat.userData.baseTransparent;
          mat.depthWrite = !mat.userData.baseTransparent;
          mat.needsUpdate = true;
          if (mat.emissive && rec !== ctx.state.selected) mat.emissive.set(0x000000);
        }
        for (const m of rec.meshes) m.visible = rec.visible !== false;
      }
    },
    tick, update, placeLabels, go, togglePlay,
    next: () => go(asm.index + 1, true),
    prev: () => go(asm.index - 1, true),
    isActive: (rec) => activeRecs.has(rec),
  };
}
