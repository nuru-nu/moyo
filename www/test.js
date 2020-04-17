import * as THREE from './threejs/three.module.js'

const cubeverts = [
  0, 0, 0,
  1, 0, 0,
  1, 1, 0,
  0, 1, 0,
  0, 1, 1,
  1, 1, 1,
  1, 0, 1,
  0, 0, 1,
]
const cubetris = [
  0, 2, 1, //face front
  0, 3, 2,
  2, 3, 4, //face top
  2, 4, 5,
  1, 2, 5, //face right
  1, 5, 6,
  0, 7, 4, //face left
  0, 4, 3,
  5, 4, 7, //face back
  5, 7, 6,
  0, 6, 7, //face bottom
  0, 1, 6
]

const Geometry = () => {
  const vertices = new Float32Array(cubetris.length * 3)
  const colors = new Float32Array(cubetris.length * 3)
  const c = new THREE.Color()
  cubetris.map((t, i) => {
    vertices[i * 3 + 0] = cubeverts[t * 3 + 0]
    vertices[i * 3 + 1] = cubeverts[t * 3 + 1]
    vertices[i * 3 + 2] = cubeverts[t * 3 + 2]
    c.setHSL(i * 3 / (cubetris.length + 1), 1, 0.5)
    colors[i * 3 + 0] = c.r
    colors[i * 3 + 1] = c.g
    colors[i * 3 + 2] = c.b
  })

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  geometry.computeBoundingSphere()

  return geometry
}

const Mesh = geometry => {
  const material = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    vertexColors: true,
    transparent: false,
    opacity: 1,
    // wireframe: true,
  })

  return new THREE.Mesh(geometry, material)
}

const Wireframe = geometry => {
  const material = new THREE.LineBasicMaterial({
    color: 0x000000,
    linewidth: 10,
    vertexColors: false,
  })

  const edges = new THREE.EdgesGeometry(geometry)
  return new THREE.LineSegments(edges, material)
}

export const Cube = scene => {

  const geometry = Geometry()
  const mesh = Mesh(geometry)
  const wireframe = Wireframe(geometry)
  scene.add(mesh)
  scene.add(wireframe)

  return {mesh, wireframe}
}
