import * as THREE from './threejs/three.module.js'

import Stats from './threejs/stats.module.js'

import { FBXLoader } from './threejs/FBXLoader.js'
import { TrackballControls } from './threejs/TrackballControls.js'
import { OrbitControls } from './threejs/OrbitControls.js'
import { GUI } from './threejs/dat.gui.module.js'
import { LineMaterial } from './threejs/LineMaterial.js'
import { Wireframe } from './threejs/Wireframe.js'
import { WireframeGeometry2 } from './threejs/WireframeGeometry2.js'


// improvement ideas
// - better camera controls


// https://github.com/mrdoob/three.js/blob/master/examples/webgl_interactive_buffergeometry.html
// - raycaster to find intersecting element
// - set individual colors as BufferedGeometry color attribute

const Geometry = mesh => {
  const positions = mesh.geometry.getAttribute('position').array
  const normals = new Float32Array(positions.length)
  const colors = new Float32Array(positions.length)
  const color = new THREE.Color()
  const pA = new THREE.Vector3()
  const pB = new THREE.Vector3()
  const pC = new THREE.Vector3()
  const cb = new THREE.Vector3()
  const ab = new THREE.Vector3()
  let idx = 0
  for (let i = 0; i < positions.length; i += 9) {
    pA.set(positions[i + 0], positions[i + 1], positions[i + 2])
    pB.set(positions[i + 3], positions[i + 4], positions[i + 5])
    pC.set(positions[i + 6], positions[i + 7], positions[i + 8])
    ab.subVectors(pA, pB)
    cb.subVectors(pC, pB)
    cb.cross(ab)
    cb.normalize()
    if (idx < 2) console.log(idx, pA, pB, pC)
    if (++idx % 2) color.setRGB(Math.random(), 0, 0)
    for (let j = 0; j < 3; j++) {
      normals[i + j * 3 + 0] = cb.x
      normals[i + j * 3 + 1] = cb.y
      normals[i + j * 3 + 2] = cb.z
      colors [i + j * 3 + 0] = color.r
      colors [i + j * 3 + 1] = color.g
      colors [i + j * 3 + 2] = color.b
    }
  }
  console.log('triangles', idx, 'quads', idx / 2)
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  geometry.computeBoundingSphere()
  console.log(geometry)
  return geometry
}

export const Mapping = mesh => {
  const positions = mesh.geometry.getAttribute('position').array
  const centers = []
  for (let i = 0; i < positions.length; i += 18) {
    const corners = []
    const sum = new THREE.Vector3()
    for (let j = 0; j < 6; j++) {
      const v = new THREE.Vector3(
        positions[i + j * 3 + 0],
        positions[i + j * 3 + 1],
        positions[i + j * 3 + 2]
      )
      let k
      for (k = 0; k < corners.length; k++) {
        if (v.equals(corners[k])) break
      }
      if (k >= corners.length) {
        corners.push(v)
        sum.add(v)
      }
    }
    if (corners.length !== 4) throw `Invalid quad at i=${i}`
    centers.push(sum.divideScalar(4))
  }

  const weights = []  // of lists of [pixel_i, weight]
  const onready = fetch('3D/mapping.json'
  ).then(res => res.json()).then(mapping => {
    const t0 = Date.now()
    mapping = mapping.xyz_mapping
    // Bucketize space into cubes of length `d`.
    const d = 0.1
    const buck = x => Math.floor(x / d)
    const unbuck = x => x * d
    const diag = (3 * d / 2) ** .5
    const bucket = xyz => `${buck(xyz[0])}_${buck(xyz[1])}_${buck(xyz[2])}`
    const buckcenter = b => {
      const xyz = b.split(/_/).map(x => unbuck(parseFloat(x)))
      return new THREE.Vector3(xyz[0] + d / 2, xyz[1] + d / 2, xyz[2] + d / 2)
    }

    const bs = new Map()
    mapping.forEach((xyz, pixel_i) => {
      const b = bucket(xyz)
      if (!bs.has(b)) bs.set(b, [])
      bs.get(b).push([pixel_i, new THREE.Vector3(xyz[0], xyz[1], xyz[2])])
    })

    const radius = 0.3
    const maxn = 20
    const weightf = dist => 1 / (dist + 1e-6) ** 2
    centers.forEach(center => {
      const ws = []
      weights.push(ws)
      Array.from(bs.entries()).forEach(([b, points]) => {
        const dist = buckcenter(b).distanceTo(center)
        if (dist > radius + diag) return
        points.forEach(([pixel_i, v]) => {
          const dist = v.distanceTo(center)
          if (dist > radius) return
          const w = weightf(dist)
          ws.push([pixel_i, w])
        })
      })
      if (ws.length > maxn) {
        ws.sort((w1, w2) => w2[1] - w1[1])
        while (ws.length > maxn) ws.pop()
      }
      const sum = ws.reduce((acc, w) => acc + w[1], 0)
      ws.forEach(w => {
        w[1] /= sum
      })
    })
    const bsps = Array.from(bs.entries()).map(([b, points]) => points.length)
    console.log(
      'mapping',
      'buckets', bsps.length,
      '.min', Math.min.apply(null, bsps),
      '.max', Math.max.apply(null, bsps),
      '.avg', bsps.reduce((acc, n) => acc + n),
      'weights', weights.length,
      '.min', Math.min.apply(null, weights.map(ws => ws.length)),
      '.max', Math.max.apply(null, weights.map(ws => ws.length)),
      '.avg', weights.reduce((acc, ws) => acc + ws.length, 0),
      'ms', Date.now() - t0)
  })

  function load(values) {
    const colors = new Float32Array(centers.length * 18)
    const color = new THREE.Color()
    for (let i = 0; i < centers.length; i++) {
      let r = 0, g = 0, b = 0
      weights[i].forEach(([pixel_i, w]) => {
        r += values[pixel_i * 3 + 0] * w
        g += values[pixel_i * 3 + 1] * w
        b += values[pixel_i * 3 + 2] * w
      })
      for (let j = 0; j < 6; j++) {
        colors[i * 18 + j * 3 + 0] = r / 255
        colors[i * 18 + j * 3 + 1] = g / 255
        colors[i * 18 + j * 3 + 2] = b / 255
      }
    }
    mesh.geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  }

  return {
    load,
    onready,
  }
}

const Colored = mesh => {
  const material2 = new THREE.MeshBasicMaterial({
    color: 0xffffff, vertexColors: true,
    transparent: false, opacity: 0.5,
  });
  return new THREE.Mesh(Geometry(mesh), material2)
}

// https://github.com/mrdoob/three.js/blob/master/examples/webgl_lines_fat_wireframe.html
// buggy : currently freezes renderer ...
const MakeWireframe = mesh => {
  const material = new LineMaterial({
    color: 0x00ff00, lineWidth: 3, dashed: false,
  });
  const geometry = new WireframeGeometry2(mesh.geometry)
  const wireframe = new Wireframe(geometry, material)
  wireframe.computeLineDistances()
  wireframe.scale.set(1, 1, 1)
  return wireframe
}

const MakeWireframe2 = mesh => {
  const material = new THREE.MeshBasicMaterial({
    color: 0x00ff00,
    wireframe: true,
    wireframeLinewidth: 30,
  });
  return new THREE.Mesh(mesh.geometry, material)
  // const material = new THREE.LineBasicMaterial({
  //   color: 0xffffff, transparent: true,
  // })
  // return new THREE.Line(Geometry(mesh), material)
}

const Colorer = (mesh, mapping) => {
  const positions = mesh.geometry.getAttribute('position').array
  const centers = new Float32Array(positions.length / 3)
  const pA = new THREE.Vector3()
  const pB = new THREE.Vector3()
  const pC = new THREE.Vector3()
  for (let i = 0; i < centers.length; i += 9) {
    pA.set(positions[i*3 + 0], positions[i*3 + 1], positions[i*3 + 2])
    pB.set(positions[i*3 + 3], positions[i*3 + 4], positions[i*3 + 5])
    pC.set(positions[i*3 + 6], positions[i*3 + 7], positions[i*3 + 8])
    pA.add(pB).add(pC).divideScalar(3)
    centers[i + 0] = pA.x
    centers[i + 1] = pA.y
    centers[i + 2] = pA.z
  }
}

export const Scene = (container, options) => {
  window.THREE = THREE
  options = options || {}
  let fps = options.fps || 10
  let stats, camera, cameraTarget, scene, renderer, controls

  camera = new THREE.PerspectiveCamera(
    50, window.innerWidth / window.innerHeight, 0.1, 1000 );
  camera.position.set(0, -6, 2);
  cameraTarget = new THREE.Vector3( 0, 0, 0 );

  scene = new THREE.Scene();

  // Ground
  var plane = new THREE.Mesh(
    new THREE.PlaneBufferGeometry( 40, 40 ),
    new THREE.MeshPhongMaterial( { color: 0x999999, specular: 0x101010 } )
  );
  plane.rotation.x = - Math.PI / 2;
  plane.position.y = - 0.5;
  plane.receiveShadow = true;
  // scene.add( plane );

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio( window.devicePixelRatio );
  renderer.setSize( window.innerWidth, window.innerHeight );
  container.appendChild(renderer.domElement);

  stats = new Stats();
  container.appendChild(stats.dom);

  window.controls = controls = new TrackballControls(
    camera, renderer.domElement);

  const gui = new GUI()
  gui.close()
  const param = { fps }
  gui.add(param, 'fps', { 10: 10, 20: 20, 30: 30, max: 1000}).onChange(
    val => { fps = parseInt(val) }
  )

  window.addEventListener( 'resize', onWindowResize, false );
  function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize( window.innerWidth, window.innerHeight );
  }

  let t0 = Date.now()
  function animate() {
    requestAnimationFrame(animate);
    const now = Date.now()
    if (now - t0 > 1e3 / fps) {
      t0 = now
      render();
      stats.update();
    }
  }

  function render() {
    controls.update();
    renderer.render( scene, camera );
  }

  return {
    animate,
    add: obj => scene.add(obj),
  }
}

export const Nuru = scene => {
  const arms = Array.from(new Array(6)).map(() => new Array(2))
  const strips = Array.from(new Array(16)).map(() => null)
  const loader = new FBXLoader();
  let lowres, colored
  const onready = new Promise((resolve, reject) => {
    let found = false
    function update() {
      // scene.add(MakeWireframe2(lowres))
      colored = Colored(lowres)
      scene.add(colored)
      // scene.add(new THREE.Mesh(lowres.geometry, colW));
      resolve()
    }
    function rek(child) {
      if (child.children.length) {
        child.children.forEach(rek)
      }
      if (child.name === 'lowres') {
        found = true
        window.lowres = child  //dbg
        lowres = child
        window.setTimeout(update, 0)
        return
      }
    }
    loader.load('3d/kinect_lowres.fbx', function(obj) {
      window.obj = obj  //dbg
      obj.children.forEach(rek)
      if (!found) reject()
    });
  })
  function obj() {
    return colored
  }
  return {
    onready,
    obj,
  }
}

export const Test = () => {
  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(
    75, window.innerWidth/window.innerHeight, 0.1, 1000 );

  var renderer = new THREE.WebGLRenderer();
  renderer.setSize(window.innerWidth, window.innerHeight);
  document.body.appendChild(renderer.domElement);

  var geometry = new THREE.BoxGeometry(1, 1, 1);
  var red = new THREE.MeshBasicMaterial({ color: 0xff0000 });
  var redW = new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true });
  var green = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
  var cube = new THREE.Mesh(geometry, green);
  window.cube = cube;
  // scene.add(cube);

  camera.position.z = 5;
  let controls = new TrackballControls(camera, renderer.domElement);

  var animate = function () {
    requestAnimationFrame( animate );

    red.color.setHex(0x800000);

    cube.rotation.x += 0.01;
    cube.rotation.y += 0.01;

    controls.update();
    renderer.render(scene, camera);
  };

  const loader = new FBXLoader();
  loader.load('cube.fbx', function(obj) {
    console.log(obj);
    const cube2 = window.cube2 = obj.children.find(child => child.name === 'Cube');
    // scene.add(new THREE.Mesh(cube2.geometry, [red, green]));
    scene.add(new THREE.Mesh(cube2.geometry, redW));
    // cube2.material = [red, green];
    // scene.add(cube2);
  });

  animate();
}
