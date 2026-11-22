// Brass alethiometer design viewer. Assets come from export_viewer.py.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

const HDR_URL = 'https://cdn.jsdelivr.net/gh/mrdoob/three.js@r170/examples/textures/equirectangular/royal_esplanade_1k.hdr';

const $ = (id) => document.getElementById(id);
const stage = $('stage');
const status = (msg) => { $('status').innerHTML = msg; $('status').hidden = !msg; };

// ---------------------------------------------------------------- renderer & scene
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.localClippingEnabled = true;
stage.prepend(renderer.domElement);

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
// Swap in a real HDR for livelier brass reflections; the room stays if the CDN is unreachable.
// The sky is ~20x brighter than the horizon, which bleaches any up-facing polished brass, so
// its dynamic range is compressed (Reinhard) before prefiltering.
new RGBELoader().setDataType(THREE.FloatType).loadAsync(HDR_URL).then((hdr) => {
  const d = hdr.image.data;
  const warm = [1.0, 0.96, 0.84];
  for (let i = 0; i < d.length; i += 4) {
    for (let c = 0; c < 3; c++) d[i + c] = (1.8 * warm[c] * d[i + c]) / (1 + d[i + c]);
  }
  hdr.needsUpdate = true;
  scene.environment = pmrem.fromEquirectangular(hdr).texture;
  scene.environmentRotation.y = 0.6;
  scene.environmentIntensity = 1.15;
  hdr.dispose();
}).catch(() => {});
const key = new THREE.DirectionalLight(0xfff1dd, 1.0);
key.position.set(150, 300, 220);
scene.add(key, new THREE.HemisphereLight(0xfff4e0, 0x2a2018, 0.35));

const camera = new THREE.PerspectiveCamera(32, 1, 1, 5000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.12;
controls.addEventListener('start', () => {
  tween = null;
  activeView = null;
  document.querySelectorAll('[data-view]').forEach((b) => b.classList.remove('active'));
});

// CAD is Z-up millimetres; three.js is Y-up. CAD (x, y, z) -> world (x, z, -y).
const root = new THREE.Group();
root.rotation.x = -Math.PI / 2;
scene.add(root);
const cadDir = (x, y, z) => new THREE.Vector3(x, z, -y).normalize();

// Section plane keeps CAD y > offset, so the "Side" view (from -y) looks at the cut face.
const clipPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);

// ---------------------------------------------------------------- state
const state = {
  explode: 0, explodeTarget: 0,
  lid: 0, lidTarget: 0,
  section: false, sectionPos: 0,
  selected: null,
};
let manifest, parts = [], dirty = true, tween = null;
const hinge = { point: new THREE.Vector3(), axis: new THREE.Vector3(0, 1, 0) };

function lidMatrix(deg) {
  const p = hinge.point;
  return new THREE.Matrix4().makeTranslation(p.x, p.y, p.z)
    .multiply(new THREE.Matrix4().makeRotationAxis(hinge.axis, THREE.MathUtils.degToRad(deg)))
    .multiply(new THREE.Matrix4().makeTranslation(-p.x, -p.y, -p.z));
}

function makeMaterial(p, dialTex) {
  const color = new THREE.Color().setRGB(p.color[0], p.color[1], p.color[2], THREE.SRGBColorSpace);
  const common = { color, side: THREE.DoubleSide };
  switch (p.finish) {
    case 'metal': {
      const patina = p.name.startsWith('hand_') && p.name !== 'hand_needle' && p.name !== 'hand_cap_rosette';
      // Nudge brass/copper toward orange: the CAD swatch reads olive once it's a dim PBR metal.
      const { h } = color.getHSL({});
      if (h > 0.05 && h < 0.17) color.offsetHSL(-0.018, 0, 0.02);
      return new THREE.MeshPhysicalMaterial({
        ...common, metalness: 1, roughness: patina ? 0.4 : 0.34,
        clearcoat: patina ? 0.5 : 0.1, clearcoatRoughness: 0.3,
      });
    }
    case 'glass':
      return new THREE.MeshPhysicalMaterial({
        ...common, metalness: 0, roughness: 0.04, transparent: true, opacity: 0.14, depthWrite: false,
        envMapIntensity: 0.5,
      });
    case 'dial':
      return dialTex
        ? new THREE.MeshStandardMaterial({ ...common, color: 0xffffff, map: dialTex, roughness: 0.55 })
        : new THREE.MeshStandardMaterial({ ...common, roughness: 0.6 });
    default:
      return new THREE.MeshStandardMaterial({ ...common, metalness: 0, roughness: 0.6 });
  }
}

function dialUVs(geom, half) {
  const pos = geom.attributes.position;
  const uv = new Float32Array(pos.count * 2);
  for (let i = 0; i < pos.count; i++) {
    uv[2 * i] = (pos.getX(i) + half) / (2 * half);
    uv[2 * i + 1] = (pos.getY(i) + half) / (2 * half);
  }
  geom.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
}

// ---------------------------------------------------------------- loading
async function load() {
  let res;
  try {
    res = await fetch('assets/parts.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
  } catch {
    status('No assets yet. Run <code>python hardware/viewer/export_viewer.py</code> first.');
    return;
  }
  manifest = await res.json();
  hinge.point.fromArray(manifest.hinge.point);
  hinge.axis.fromArray(manifest.hinge.axis).normalize();
  $('lid').max = manifest.hinge.open_deg;
  const restDeg = manifest.hinge.rest_deg ?? manifest.hinge.open_deg;
  state.lid = restDeg;
  setLid(restDeg);

  const v = `?v=${manifest.generated ?? Date.now()}`;
  const [gltf, dialTex] = await Promise.all([
    new GLTFLoader().loadAsync('assets/alethiometer.glb' + v),
    manifest.dial.texture
      ? new THREE.TextureLoader().loadAsync('assets/' + manifest.dial.texture + v).catch(() => null)
      : Promise.resolve(null),
  ]);
  if (dialTex) {
    dialTex.colorSpace = THREE.SRGBColorSpace;
    dialTex.anisotropy = renderer.capabilities.getMaxAnisotropy();
  }
  const geoms = {};
  gltf.scene.traverse((o) => { if (o.isMesh) geoms[o.name] = o.geometry; });

  for (const meta of manifest.parts) {
    const geom = geoms[meta.name];
    if (!geom) { console.warn('missing mesh', meta.name); continue; }
    geom.computeVertexNormals();
    if (meta.finish === 'dial') dialUVs(geom, manifest.dial.half);
    const material = makeMaterial(meta, dialTex);
    const rec = { meta, material, visible: true, meshes: [], lidPart: !!meta.open };
    for (const arr of meta.placements) {
      const mesh = new THREE.Mesh(geom, material);
      mesh.name = meta.name;
      mesh.matrixAutoUpdate = false;
      mesh.userData = { rec, base: new THREE.Matrix4().fromArray(arr) };
      if (meta.finish === 'glass') mesh.renderOrder = 10;
      root.add(mesh);
      rec.meshes.push(mesh);
    }
    parts.push(rec);
  }

  buildSidebar();
  $('lid').disabled = false;
  $('lidToggle').disabled = false;
  updateMatrices();
  setView('iso', false);
  status('');
  const pieces = parts.reduce((n, r) => n + r.meshes.length, 0);
  const tris = parts.reduce((n, r) => n + r.meta.triangles * r.meshes.length, 0);
  $('stats').textContent = `${parts.length} part types, ${pieces} pieces, ${(tris / 1000).toFixed(0)}k triangles`
    + ` · lid stop: ${Math.round(manifest.hinge.open_deg)}°`
    + (manifest.dial.source ? ` · dial: ${manifest.dial.source}` : ' · no dial texture');
}

// ---------------------------------------------------------------- transforms
function updateMatrices() {
  const lidM = lidMatrix(state.lid);
  const m = new THREE.Matrix4();
  for (const rec of parts) {
    const dz = state.explode * rec.meta.explode;
    for (const mesh of rec.meshes) {
      m.makeTranslation(0, 0, dz);
      if (rec.lidPart) m.multiply(lidM);
      mesh.matrix.copy(m.multiply(mesh.userData.base));
      mesh.matrixWorldNeedsUpdate = true;
    }
  }
  dirty = false;
}

// ---------------------------------------------------------------- sidebar
const groupEls = {};

function swatchColor(c) { return `rgb(${c.map((v) => Math.round(v * 255)).join(',')})`; }

function buildSidebar() {
  const ul = $('groups');
  ul.innerHTML = '';
  for (const g of manifest.groups) {
    const recs = parts.filter((r) => r.meta.group === g.id);
    if (!recs.length) continue;
    const li = document.createElement('li');
    const row = document.createElement('div');
    row.className = 'group-row';
    const twisty = document.createElement('button');
    twisty.className = 'twisty';
    twisty.textContent = '▸';
    twisty.title = 'Show parts';
    const label = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = true;
    label.append(cb, ' ' + g.label);
    const count = document.createElement('span');
    count.className = 'count';
    count.textContent = recs.reduce((n, r) => n + r.meshes.length, 0);
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = swatchColor(recs[0].meta.color);
    row.append(twisty, sw, label, count);

    const list = document.createElement('ul');
    list.hidden = true;
    for (const rec of recs) {
      const pr = document.createElement('li');
      pr.className = 'part-row';
      const pcb = document.createElement('input');
      pcb.type = 'checkbox';
      pcb.checked = true;
      pcb.addEventListener('click', (e) => e.stopPropagation());
      pcb.addEventListener('change', () => { setPartVisible(rec, pcb.checked); syncGroup(g.id); });
      const psw = document.createElement('span');
      psw.className = 'swatch';
      psw.style.background = swatchColor(rec.meta.color);
      const name = document.createElement('span');
      name.className = 'pname';
      name.textContent = rec.meta.name;
      name.title = `${rec.meta.name}: ${rec.meta.spec}`;
      const qty = document.createElement('span');
      qty.className = 'qty';
      qty.textContent = rec.meta.qty > 1 ? `×${rec.meta.qty}` : '';
      pr.append(pcb, psw, name, qty);
      pr.addEventListener('click', () => select(rec, true));
      rec.row = pr;
      rec.checkbox = pcb;
      list.append(pr);
    }
    twisty.addEventListener('click', () => {
      list.hidden = !list.hidden;
      twisty.textContent = list.hidden ? '▸' : '▾';
    });
    cb.addEventListener('change', () => {
      for (const r of recs) setPartVisible(r, cb.checked);
      syncGroup(g.id);
    });
    li.append(row, list);
    ul.append(li);
    groupEls[g.id] = { cb, list, twisty, recs };
  }
}

function setPartVisible(rec, on) {
  rec.visible = on;
  for (const m of rec.meshes) m.visible = on;
  if (rec.checkbox) rec.checkbox.checked = on;
  if (!on && state.selected === rec) select(null);
}

function syncGroup(id) {
  const g = groupEls[id];
  const n = g.recs.filter((r) => r.visible).length;
  g.cb.checked = n > 0;
  g.cb.indeterminate = n > 0 && n < g.recs.length;
}

function setAll(on) {
  for (const r of parts) setPartVisible(r, on);
  Object.keys(groupEls).forEach(syncGroup);
}

// ---------------------------------------------------------------- selection
const HILITE = new THREE.Color(0x6a4300);

function select(rec, fromList = false) {
  if (state.selected) {
    state.selected.material.emissive?.set(0x000000);
    state.selected.row?.classList.remove('selected');
  }
  state.selected = rec;
  if (!rec) { $('info').hidden = true; return; }
  rec.material.emissive?.copy(HILITE);
  rec.row?.classList.add('selected');
  if (!fromList && rec.row) {
    const g = groupEls[rec.meta.group];
    if (g.list.hidden) { g.list.hidden = false; g.twisty.textContent = '▾'; }
    rec.row.scrollIntoView({ block: 'nearest' });
  }
  const m = rec.meta;
  const label = manifest.groups.find((g) => g.id === m.group)?.label ?? m.group;
  const rows = [
    ['Layer', label],
    ['Kind', { scs: 'laser cut (SendCutSend)', 'scs-bent': 'laser cut + bent (SendCutSend)', stock: 'K&S stock', bought: 'bought' }[m.kind] ?? m.kind],
    ['Material', m.material],
    ['Spec', m.spec],
    ['Qty', m.qty + (m.qty_extra ? ` (+${m.qty_extra} spare)` : '')],
    ['Z', `${m.z[0].toFixed(2)} – ${m.z[1].toFixed(2)} mm`],
  ];
  $('infoName').textContent = m.name;
  $('infoBody').innerHTML = '';
  for (const [k, v] of rows) {
    const dt = document.createElement('dt');
    dt.textContent = k;
    const dd = document.createElement('dd');
    dd.textContent = v;
    $('infoBody').append(dt, dd);
  }
  $('info').hidden = false;
}

const raycaster = new THREE.Raycaster();
function pick(ev) {
  const r = renderer.domElement.getBoundingClientRect();
  const ndc = new THREE.Vector2(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  raycaster.setFromCamera(ndc, camera);
  const meshes = parts.filter((p) => p.visible).flatMap((p) => p.meshes);
  const hits = raycaster.intersectObjects(meshes, false)
    .filter((h) => !state.section || clipPlane.distanceToPoint(h.point) >= 0);
  const hit = hits.find((h) => h.object.userData.rec.meta.finish !== 'glass') ?? hits[0];
  select(hit ? hit.object.userData.rec : null);
}

let downAt = null;
renderer.domElement.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (downAt && e.button === 0 && Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) < 5) pick(e);
  downAt = null;
});

// ---------------------------------------------------------------- views
const VIEWS = {
  iso: cadDir(0.55, -0.85, 0.6),
  top: cadDir(0, -0.0001, 1),
  side: cadDir(0, -1, 0.12),
  under: cadDir(0.45, -0.7, -0.8),
};

// Distance along `dir` from the box centre at which every box corner fits the frustum.
function fitDistance(box, dir, margin = 1.12) {
  const center = box.getCenter(new THREE.Vector3());
  const fwd = dir.clone().negate();
  const right = new THREE.Vector3().crossVectors(fwd, camera.up).normalize();
  const up = new THREE.Vector3().crossVectors(right, fwd);
  const tv = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
  const th = tv * camera.aspect;
  let d = 0;
  const c = new THREE.Vector3();
  for (let i = 0; i < 8; i++) {
    c.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z).sub(center);
    const z = c.dot(dir);
    d = Math.max(d, z + Math.abs(c.dot(right)) * margin / th, z + Math.abs(c.dot(up)) * margin / tv);
  }
  return { center, d };
}

// `view` is a preset name, or omitted to re-frame along the active preset / current direction.
let activeView = null;
function setView(view, animate = true) {
  view = view ?? activeView;
  const dir = VIEWS[view]?.clone() ?? (tween ? tween.toPos.clone().sub(tween.toT) : camera.position.clone().sub(controls.target)).normalize();
  // Frame the target pose, not a mid-animation one.
  const cur = [state.explode, state.lid];
  [state.explode, state.lid] = [state.explodeTarget, state.lidTarget];
  updateMatrices();
  const box = new THREE.Box3();
  root.updateMatrixWorld(true);
  const visible = parts.filter((p) => p.visible);
  for (const p of visible.length ? visible : parts) for (const m of p.meshes) box.expandByObject(m);
  [state.explode, state.lid] = cur;
  dirty = true;
  const { center, d } = fitDistance(box, dir);
  const toPos = center.clone().addScaledVector(dir, d);
  activeView = view ?? null;
  document.querySelectorAll('[data-view]').forEach((b) => b.classList.toggle('active', b.dataset.view === activeView));
  if (!animate) {
    camera.position.copy(toPos);
    controls.target.copy(center);
    controls.update();
    return;
  }
  tween = { t0: performance.now(), dur: 700, fromPos: camera.position.clone(), toPos,
            fromT: controls.target.clone(), toT: center.clone() };
}

// ---------------------------------------------------------------- controls wiring
function setExplode(v) { state.explodeTarget = v; $('explode').value = v; }
function setLid(deg) {
  const angle = THREE.MathUtils.clamp(deg, 0, manifest.hinge.open_deg);
  state.lidTarget = angle;
  $('lid').value = angle;
  $('lidToggle').textContent = angle > 90 ? 'Close' : 'Open';
}
function setSection(on, pos = state.sectionPos) {
  state.section = on;
  state.sectionPos = pos;
  clipPlane.constant = -pos;
  $('section').checked = on;
  $('sectionPos').disabled = !on;
  $('sectionPos').value = pos;
  for (const r of parts) {
    r.material.clippingPlanes = on ? [clipPlane] : [];
    r.material.needsUpdate = true;
  }
}

$('explode').addEventListener('input', (e) => setExplode(+e.target.value));
$('explode').addEventListener('change', () => setView());
$('lid').addEventListener('input', (e) => setLid(+e.target.value));
$('lid').addEventListener('change', () => setView());
$('lidToggle').addEventListener('click', () => {
  setLid(state.lidTarget > 90 ? 0 : (manifest.hinge.rest_deg ?? manifest.hinge.open_deg));
  setView();
});
$('section').addEventListener('change', (e) => setSection(e.target.checked));
$('sectionPos').addEventListener('input', (e) => setSection(true, +e.target.value));
document.querySelectorAll('[data-view]').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));
$('showAll').addEventListener('click', () => { setAll(true); setView(); });
$('hideAll').addEventListener('click', () => setAll(false));
$('infoClose').addEventListener('click', () => select(null));
$('isolate').addEventListener('click', () => {
  const keep = state.selected;
  if (!keep) return;
  for (const r of parts) setPartVisible(r, r === keep);
  Object.keys(groupEls).forEach(syncGroup);
  select(keep);
  setView();
});
$('hidePart').addEventListener('click', () => {
  const r = state.selected;
  if (r) { setPartVisible(r, false); syncGroup(r.meta.group); }
});
$('collapse').addEventListener('click', () => document.body.classList.add('collapsed'));
$('expand').addEventListener('click', () => document.body.classList.remove('collapsed'));
window.addEventListener('keydown', (e) => { if (e.key === 'Escape') select(null); });

// ---------------------------------------------------------------- loop
function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(stage);
resize();

const approach = (cur, target, k, eps) => (Math.abs(target - cur) < eps ? target : cur + (target - cur) * k);
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

renderer.setAnimationLoop(() => {
  if (state.explode !== state.explodeTarget || state.lid !== state.lidTarget) {
    state.explode = approach(state.explode, state.explodeTarget, 0.14, 0.001);
    state.lid = approach(state.lid, state.lidTarget, 0.1, 0.1);
    dirty = true;
  }
  if (dirty) updateMatrices();
  if (tween) {
    const t = Math.min(1, (performance.now() - tween.t0) / tween.dur), k = ease(t);
    camera.position.lerpVectors(tween.fromPos, tween.toPos, k);
    controls.target.lerpVectors(tween.fromT, tween.toT, k);
    if (t >= 1) tween = null;
  }
  controls.update();
  renderer.render(scene, camera);
});

// Small hook for scripted screenshots / debugging from the console.
window.viewer = {
  state, scene, renderer, setExplode, setLid, setSection, setView, setAll,
  select: (name) => select(parts.find((p) => p.meta.name === name) ?? null),
  setGroup: (id, on) => { for (const r of groupEls[id].recs) setPartVisible(r, on); syncGroup(id); },
  get ready() { return parts.length > 0; },
};

load().catch((err) => { console.error(err); status('Failed to load: ' + err.message); });
