
import { h, ui, colors } from './smanmi/util.js'

const color = id => (
  colors.user_colors[(id - 1) % colors.user_colors.length])

function Person(id) {
  const data = {id, x: 0, y: -3.5, selected: false}
  const els = h.div('cont', {style: 'margin-bottom: 0.5rem;'}).of(
    h.div('id').of(`id=${id}`),
    ui.h(
      h.span('x').of(`x=${data.x}`),
      ', ',
      h.span('y').of(`y=${data.y}`),
    )
  ).els
  function update() {
    els.id.style.backgroundColor = data.selected ? color(id) : null
    els.id.style.color = data.selected ? 'black' : color(id)
  }
  function set(selected) {
    data.selected = selected
    update()
  }
  update()
  return {
    els,
    data,
    set,
  }
}

const Simulating = (pr) => {
  const people = new Map()
  const targets = new Map()
  let selid = null
  let id = 0
  function add() {
    ++id
    const p = Person(id)
    people.set(id, p)
    click(p.data.x, p.data.y)
  }
  function del() {
    if (!id) return
    people.delete(id--)
  }
  function click(x, y) {
    if (!id) return
    const dists = Array.from(people.keys()).map(id => {
      const p = people.get(id)
      const dist = ((x - p.data.x)**2 + (y - p.data.y)**2)**.5
      return [dist, id]
    })
    dists.sort()
    if (dists[0][0] < pr) {
      if (selid === dists[0][1]) selid = null
      else selid = dists[0][1]
      return
    }
    if (selid) {
      targets.set(selid, [x, y])
    }
  }
  function tick() {
    for(let id of people.keys()) {
      const p = people.get(id)
      if (targets.has(id)) {
          let [tx, ty] = targets.get(id)
          let dx = (tx - p.data.x)
          let dy = (ty - p.data.y)
          const d = Math.sqrt(dx * dx + dy * dy)
          dx /= d * 30
          dy /= d * 30
          if (Math.abs(dx) < Math.abs(tx - p.data.x)) {
            p.data.x += dx
            p.data.y += dy
          } else {
            p.data.x = tx
            p.data.y = ty
            targets.delete(id)
          }
      }
    }
  }
  return {
    people: () => Array.from(people.values()).map(p => ({
      id: p.data.id,
      cm: [p.data.x, p.data.y, 0],
    })),
    click,
    tick,
    add,
    del,
    sel: () => selid,
    target: id => targets.get(id),
  }
}

export const Kinect = (output, {network}) => {
  const r_z0 = 0.3
  const r_z1 = 2
  const d_z2 = 5
  const d_z3 = 6
  const width = 200
  const height = 200
  const xlim = [-3, 3]
  const ylim = [-6, 0] // Needs to be square for arc drawing
  const tox = x => width  * (x - xlim[0]) / (xlim[1] - xlim[0])
  const toy = y => height - height * (y - ylim[0]) / (ylim[1] - ylim[0])
  const fromx = x => x / width * (xlim[1] - xlim[0]) + xlim[0]
  const fromy = y => (height - y) / height * (ylim[1] - ylim[0]) + ylim[0]
  const pr = 8
  const simulating = Simulating(Math.min(
    Math.abs(fromx(0) - fromx(pr)), Math.abs(fromy(0) - fromy(pr))))
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('kinect'),
    ui.v(
      ui.h(
        ui.toggle('simulate'),
        h.button('add', {class: 'h'}).of('add'),
        h.button('del', {class: 'h'}).of('del'),
      ),
      h.canvas('xy', {width, height}),
    ),
  ).into(output).els
  const ctx = disp.xy.getContext('2d')

  disp.add.addEventListener('click', simulating.add)
  disp.del.addEventListener('click', simulating.del)

  disp.xy.addEventListener('click', e => {
    if (!simulate) return
    const {left, top} = disp.xy.getBoundingClientRect()
    simulating.click(fromx(e.clientX - left), fromy(e.clientY - top))
  })

  let simulate = false
  disp.simulate.change(value => {
      simulate = value
      disp.add.classList[simulate ? 'remove' : 'add']('h')
      disp.del.classList[simulate ? 'remove' : 'add']('h')
      if (!simulate) network.sender({people_override: null})
  })

  function background(z0_alpha, z1_alpha, z2_alpha, z3_alpha) {
    ctx.lineWidth = 2
    ctx.strokeStyle = '#444'
    ctx.beginPath()
    ctx.moveTo(0, toy(0))
    ctx.lineTo(width, toy(0))
    ctx.moveTo(tox(0), 0)
    ctx.lineTo(tox(0), height)
    const r = 0.8
    const phi = Math.PI / 4.0
    // ctx.moveTo(tox(xlim[0]), toy(xlim[0] * Math.tan(phi)))
    // ctx.lineTo(tox(r * Math.cos(Math.PI/2 + phi)), toy(-r * Math.sin(Math.PI/2 + phi)))
    // ctx.arc(tox(0), toy(0), tox(r) - tox(0), Math.PI/2 + phi, Math.PI/2 - phi, true)
    // ctx.lineTo(tox(xlim[1]), toy(-xlim[1] * Math.tan(phi)))
    ctx.stroke()

    ctx.globalAlpha = z0_alpha;
    ctx.fillStyle = ctx.strokeStyle = "red"
    ctx.beginPath()
    ctx.moveTo(tox(r_z0), toy(-0.4))
    ctx.arc(tox(0), toy(-0.4), tox(r_z0) - tox(0), 0, 2*Math.PI, false)  
    ctx.fill()
    ctx.stroke()

    ctx.globalAlpha = z1_alpha;
    ctx.fillStyle = ctx.strokeStyle = "orange";
    ctx.beginPath()
    ctx.moveTo(tox(-r_z1 * Math.cos(Math.PI/2 + phi)), toy(-r_z1 * Math.sin(Math.PI/2 + phi)))
    ctx.arc(tox(0), toy(0), tox(r_z1) - tox(0), Math.PI/2 - phi, Math.PI/2 + phi, false)  
    ctx.lineTo(tox(r * Math.cos(Math.PI/2 + phi)), toy(-r * Math.sin(Math.PI/2 + phi)))
    ctx.arc(tox(0), toy(0), tox(r) - tox(0), Math.PI/2 + phi, Math.PI/2 - phi, true)
    ctx.lineTo(tox(-r_z1 * Math.cos(Math.PI/2 + phi)), toy(-r_z1 * Math.sin(Math.PI/2 + phi)))
    ctx.fill()
    ctx.stroke()

    ctx.globalAlpha = z2_alpha;
    ctx.fillStyle = ctx.strokeStyle = "yellow";
    ctx.beginPath()
    ctx.moveTo(tox(-r_z1 * Math.cos(Math.PI/2 + phi)), toy(-r_z1 * Math.sin(Math.PI/2 + phi)))
    ctx.arc(tox(0), toy(0), tox(r_z1) - tox(0), Math.PI/2 - phi, Math.PI/2 + phi, false) 
    ctx.lineTo(tox(-  3), -toy(d_z2))
    ctx.lineTo(tox(3), -toy(d_z2))
    ctx.lineTo(tox(-r_z1 * Math.cos(Math.PI/2 + phi)), toy(-r_z1 * Math.sin(Math.PI/2 + phi)))
    ctx.fill()
    ctx.stroke()

    ctx.globalAlpha = z3_alpha;
    ctx.fillStyle = ctx.strokeStyle = "gray";
    ctx.beginPath()
    ctx.fillRect(tox(-3), toy(-d_z2), tox(3), toy(-d_z3));
    ctx.fill()
    ctx.stroke()

    ctx.globalAlpha = 1;
    ctx.fillStyle = ctx.strokeStyle = "white";


    ctx.lineWidth = 1
    ctx.beginPath()
    for (let x = Math.floor(xlim[0] - 1); x <= xlim[1]; ++x) {
      if (x < xlim[0]) continue
      ctx.moveTo(tox(x), 0)
      ctx.lineTo(tox(x), height)
    }
    for (let y = Math.floor(ylim[0] - 1); y <= ylim[1]; ++y) {
      if (y < ylim[0]) continue
      ctx.moveTo(0, toy(y))
      ctx.lineTo(height, toy(y))
    }
    ctx.stroke()
  }

  const cmap = new Map()
  const lcm = new Map()
  network.listenJson('signals', function(data) {
    if (simulate) {
      simulating.tick()
      network.sender({
        people_override: simulating.people(),
      }, 'silent')
    }
    ctx.clearRect(0, 0, width, height)

    var z0_alpha, z1_alpha, z2_alpha, z3_alpha
    z0_alpha = 0.15
    if (data.hasOwnProperty('sonar') && data["sonar"] > 0.5) {
      z0_alpha = 1
    }
    z1_alpha = 0.15
    z2_alpha = 0.15
    if (data.hasOwnProperty('people')) {
      data.people.forEach(p => {
        let [x, y] = p.cm
        if (Math.sqrt(Math.pow(x, 2) + Math.pow(y, 2)) > r_z1){
          z2_alpha = 1.0
        } else {
          z1_alpha = 1.0
        }
      })
    }
    z3_alpha = 0.15
    if (data.hasOwnProperty('pir') && data['pir'] > 0) {
      z3_alpha = 1.0
    }
    
    background(z0_alpha, z1_alpha, z2_alpha, z3_alpha)
    if (data.hasOwnProperty('people_2')) {
      data.people_2.forEach(p => {
        let [x, y] = p.cm
        ctx.strokeStyle = '#c0c0c0'
        ctx.beginPath()
        const r = p.id === simulating.sel() ? pr * 1.2 : pr
        ctx.arc(tox(x), toy(y), r, 0, 2 * Math.PI)
        ctx.stroke()
      })
    }
    if (data.hasOwnProperty('people')) {
      data.people.forEach(p => {
        if (!cmap.has(p.id)) {
          cmap.set(p.id, color(p.id))
        }
        let [x, y] = p.cm

         ctx.fillStyle = ctx.strokeStyle = cmap.get(p.id)

        if (x == 0 && y == 0 && lcm.has(p.id)) {
          [x, y] = lcm.get(p.id)
        }
        const target = simulating.target(p.id)
        if (target) {
          ctx.lineWidth = 3
          ctx.beginPath()
          ctx.moveTo(tox(p.cm[0]), toy(p.cm[1]))
          ctx.lineTo(tox(target[0]), toy(target[1]))
          ctx.stroke()
        }
        ctx.beginPath()
        const r = p.id === simulating.sel() ? pr * 1.2 : pr
        ctx.arc(tox(x), toy(y), r, 0, 2 * Math.PI)
        ctx.fill()

        ctx.font = "15px Arial";
        ctx.fillText(data.likes[p.id].toFixed(2), tox(p.cm[0]) + 7, toy(p.cm[1]) - 7);
        ctx.fillStyle = ctx.strokeStyle = "white";
        ctx.fillText(p.id, tox(p.cm[0]) - 5, toy(p.cm[1]) + 6);

        if (x != 0 || y != 0) lcm.set(p.id, p.cm)
      })
    }
  })
}
