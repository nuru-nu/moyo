
import { h, ui, colors } from './smanmi/util.js'

const color = id => (
  colors.user_colors[(id - 1) % colors.user_colors.length])

const Simulating = (pr) => {
  let last_people = null
  let n = null
  const targets = new Map()
  let selid = null
  function add() {
    n++
  }
  function del() {
    if (n > 0) n--
  }
  function click(cx, cy) {
    if (!(last_people && last_people.length)) return
    const dists = last_people.map(p => {
      const [x, y] = p.cm
      const dist = ((cx - x)**2 + (cy - y)**2)**.5
      return [dist, p.id]
    })
    dists.sort()
    if (dists[0][0] < pr) {
      if (selid === dists[0][1]) selid = null
      else selid = dists[0][1]
    } else if (selid !== null) {
      targets.set(selid, [cx, cy])
    }
  }
  function tick(people) {
    last_people = people.map(p => {
      let [x, y] = p.cm
      if (targets.has(p.id)) {
        const [tx, ty] = targets.get(p.id)
        let dx = tx - x, dy = ty - y
        const d = Math.sqrt(dx * dx + dy * dy)
        dx /= d * 5
        dy /= d * 5
        if (Math.abs(dx) < Math.abs(tx - x)) {
          x += dx
          y += dy
        } else {
          x = tx
          y = ty
          targets.delete(p.id)
        }
      }
      return {id: p.id, cm: [x, y, 0]}
    })
    if (n === null) n = last_people.length
    if (n > last_people.length) {
      last_people.push({id: last_people.length + 1, cm: [0, -3.5, 0]})
    } else if (n < last_people.length) {
      last_people = last_people.slice(0, n)
    }
    return last_people
  }
  return {
    click,
    tick,
    add,
    del,
    sel: () => selid,
    target: id => targets.get(id),
    should_update: () => targets.size || (last_people !== null && n != last_people.length)
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
        h.button('simulate').of('simulate'),
        h.button('add', {class: 'h'}).of('add'),
        h.button('del', {class: 'h'}).of('del'),
      ),
      h.div().of(
        ui.range('kinect_dphi', {network, text: null}),
      ),
      h.canvas('xy', {width, height}),
      ui.choice('kinect_alg', {network, values:['algo', 'nite', 'merged']})
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
  disp.simulate.addEventListener('click', () => {
    network.sender({people_override: simulate ? null : [] })
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
    ctx.fillStyle = ctx.strokeStyle = "#ff6600";
    ctx.beginPath()
    ctx.moveTo(tox(-r_z1 * Math.cos(Math.PI/2 + phi)), toy(-r_z1 * Math.sin(Math.PI/2 + phi)))
    ctx.arc(tox(0), toy(0), tox(r_z1) - tox(0), Math.PI/2 - phi, Math.PI/2 + phi, false)  
    ctx.lineTo(tox(r * Math.cos(Math.PI/2 + phi)), toy(-r * Math.sin(Math.PI/2 + phi)))
    ctx.arc(tox(0), toy(0), tox(r) - tox(0), Math.PI/2 + phi, Math.PI/2 - phi, true)
    ctx.lineTo(tox(-r_z1 * Math.cos(Math.PI/2 + phi)), toy(-r_z1 * Math.sin(Math.PI/2 + phi)))
    ctx.fill()
    ctx.stroke()

    ctx.globalAlpha = z2_alpha;
    ctx.fillStyle = ctx.strokeStyle = "#ebc034";
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

    if (data.people_override) {
      simulate = true
      disp.add.classList.remove('h')
      disp.del.classList.remove('h')
      const should_update = simulating.should_update()
      const people_override = simulating.tick(data.people_override)
      if (should_update) {
        network.sender({ people_override }, 'silent')
      }
      disp.simulate.classList.add('on')
    } else {
      simulate = false
      disp.add.classList.add('h')
      disp.del.classList.add('h')
      disp.simulate.classList.remove('on')
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
        ctx.strokeStyle = '#000'
        ctx.beginPath()
        const r = p.id === simulating.sel() ? pr * 1.2 : pr
        ctx.arc(tox(x), toy(y), r, 0, 2 * Math.PI)
        ctx.stroke()
      })
    }
    if (data.hasOwnProperty('people')) {
      data.people.forEach(p => {
        if (!cmap.has(p.id)) {
          if (p.id < 0) {
            cmap.set(p.id, color(10 - p.id))
          } else {
            cmap.set(p.id, color(p.id))
          }
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
