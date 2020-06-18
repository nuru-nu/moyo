
import { h, ui, colors } from './smanmi/util.js'

const color = id => (
  colors.strong_palette[(id - 1) % colors.strong_palette.length])

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

const Simulating = () => {
  const people = new Map()
  let attractors = []
  let selids = new Set()
  let id = 0
  const els = h.div('cont').of(
    ui.h(
      h.button('add').of('add'),
      h.button('del').of('del'),
    ),
    h.div('people'),
  ).els
  els.del.addEventListener('click', () => {
    els.people.removeChild(people.get(id).els.cont)
    people.delete(id--)
  })
  els.add.addEventListener('click', () => {
    ++id
    const p = Person(id)
    people.set(id, p)
    p.els.id.addEventListener('click', () => {
      p.set(!p.data.selected)
      selids[p.data.selected ? 'add' : 'delete'](p.data.id)
    })
    els.people.appendChild(p.els.cont)
  })
  function click(x, y) {
    if (selids.size) {
      attractors.push({ms: Date.now(), x, y, ids: new Set(selids)})
    }
  }
  function step(from, to, dt) {
    return (to - from) / Math.abs(to - from) / 30 / Math.max(1, dt/1000)
  }
  function tick() {
    attractors = attractors.filter(a => Date.now() - a.ms < 1e4)
    for(let p of people.values()) {
      attractors.forEach(a => {
        if (a.ids.has(p.data.id)) {
          const dt = Date.now() - a.ms
          p.data.x += step(p.data.x, a.x, dt)
          p.data.y += step(p.data.y, a.y, dt)
        }
      })
    }
  }
  return {
    el: els.cont,
    people: () => Array.from(people.values()).map(p => ({
      id: p.data.id,
      cm: [p.data.x, p.data.y],
    })),
    click,
    tick,
  }
}

export const Kinect = (output) => {
  const width = 200
  const height = 200
  const xlim = [-2.5, 2.5]
  const ylim = [-4, 1]
  const r = 8
  let presence = 0
  const simulating = Simulating()
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('kinect'),
    ui.v(
      ui.toggle('simulate'),
      ui.h(
        'presence ',
        h.input('presence', {type: 'range', min: 0, max: 1, step: 0.05, value: 0.5}),
      ),
      ui.h(
        h.canvas('xy', {width, height}),
        simulating.el,
      ),
    ),
  ).into(output).els
  const ctx = disp.xy.getContext('2d')

  const tox = x => width  * (x - xlim[0]) / (xlim[1] - xlim[0])
  const toy = y => height - height * (y - ylim[0]) / (ylim[1] - ylim[0])
  const fromx = x => x / width * (xlim[1] - xlim[0]) + xlim[0]
  const fromy = y => (height - y) / height * (ylim[1] - ylim[0]) + ylim[0]

  disp.xy.addEventListener('click', e => {
    if (!simulate) return
    const {left, top} = disp.xy.getBoundingClientRect()
    simulating.click(fromx(e.clientX - left), fromy(e.clientY - top))
  })

  let simulate = false
  disp.simulate.change(value => {
      simulate = value
      simulating.el.classList[simulate ? 'remove' : 'add']('h')
  })

  disp.presence.addEventListener('change', e => {
      if (simulate) {
          sender({presence: parseFloat(e.target.value)})
      }
      e.target.value = presence
  })

  let sender
  function grid() {
    ctx.lineWidth = 2
    ctx.strokeStyle = '#444'
    ctx.beginPath()
    ctx.moveTo(0, toy(0))
    ctx.lineTo(width, toy(0))
    ctx.moveTo(tox(0), 0)
    ctx.lineTo(tox(0), height)
    ctx.stroke()
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
  function listener(data) {
    ctx.clearRect(0, 0, width, height)
    grid()
    if (data.hasOwnProperty('people')) {
      data.people.forEach(p => {
        if (!cmap.has(p.id)) {
          cmap.set(p.id, color(p.id))
        }
        ctx.fillStyle = cmap.get(p.id)
        ctx.beginPath()
        if (p.cm[0] == 0 && p.cm[1] == 0 && lcm.has(p.id)) {
          ctx.arc(tox(lcm.get(p.id)[0]), toy(lcm.get(p.id)[1]), r, 0, 2 * Math.PI)
        } else {
          ctx.arc(tox(p.cm[0]), toy(p.cm[1]), r, 0, 2 * Math.PI)
          lcm.set(p.id, p.cm)
        }
        ctx.fill()
      })
    }
    if (data.hasOwnProperty('presence')) disp.presence.value = data.presence
    if (simulate) {
      simulating.tick()
      sender({people: simulating.people()}, 'silent')
    }
  }
  function sendto(sender_) {
    sender = sender_
  }
  return {
    listener,
    sendto,
  }
}
