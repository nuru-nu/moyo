import { h, colors, ui } from './smanmi/util.js'
import { Scene, Nuru } from './nuru.js';

export const Leds = (output, defs, opts) => {

  let phi_r_mapping = defs.mapping.phi_r

  opts = opts || {}
  const min_value = opts.min_value || 20

  let width=600, height=480
  const sizes = {
    s: { width: 600, height: 480 },
    m: { width: 800, height: 600 },
    l: { width: 1024, height: 768 },
  }
  const rows=32, cols=64, sz=10

  const disp = ui.v(
    ui.h(
      ui.choice('view', {values: ['r-phi', 'x-y-z']}),
      ui.choice('size', {values: Object.keys(sizes), initial: 's'}),
      h.div('xyzcontrols').of(ui.h(
        'fps ',
        ui.dropdown('fps', {values: ['10', '20', '30', '60']}),
        ui.toggle('wireframe'),
        ui.toggle('stats'),
      )),
      ui.h(
        h.button('pause').of('pause'),
        h.button('download').of('download'),
      ),
    ),
    ui.v(
      h.canvas('rphi', {width, height}),
      h.div('xyz', {class: 'xyz'}),
    ),
  ).into(output).els

  const scene = Scene(disp.xyz, {width, height})
  const nuru = Nuru(scene)
  nuru.mapping(defs.mapping.xyz)

  let view = null
  disp.view.change(value => {
    view = value
    if (view == 'r-phi') {
      disp.xyz.style.display = 'none'
      disp.xyzcontrols.style.display = 'none'
      disp.rphi.style.display = 'block'
      scene.stop()
    } else {
      disp.xyz.style.display = 'block'
      disp.xyzcontrols.style.display = 'block'
      disp.rphi.style.display = 'none'
      scene.start()
    }
  }).init()
  disp.size.change(value => {
    width = sizes[value].width
    height = sizes[value].height
    scene.size(width, height)
    disp.rphi.setAttribute('width', width)
    disp.rphi.setAttribute('height', height)
  }).init()

  disp.fps.change(fps => scene.fps(parseFloat(fps)))
  disp.wireframe.change(nuru.wireframe)
  disp.stats.change(scene.stats)

  let paused = false
  disp.pause.addEventListener('click', () => {
    paused = !paused
    disp.pause.textContent = paused ? 'unpause' : 'pause'
  })

  disp.download.addEventListener('click', () => {
    const s = JSON.stringify(Array.from(lvalues))
    const a = h.a({
      href: 'data:text/plain;charset=utf8,' + encodeURIComponent(s),
      download: `${Math.floor(Date.now() / 1e3)}.json`
    }).into(document.body).el
    a.click()
    document.body.removeChild(a)
  })

  const ctx = disp.rphi.getContext('2d')

  function led(phi, r, col) {
    const x = width / 2 + Math.sin(phi) * r * 77
    const y = height / 2 - Math.cos(phi) * r * 77
    ctx.fillStyle = col
    ctx.fillRect(x, y, 3, 3)
  }

  let lvalues = null
  function listener(values) {
    if (paused || !phi_r_mapping) {
      return
    }
    if (view === 'x-y-z') {
      nuru.load(values)
      return
    }
    lvalues = values
    ctx.clearRect(0, 0, width, height)
    for(let i = 0; i < values.byteLength / 3; i++) {
      const x=i%cols, y=Math.floor(i/cols)
      const col = (
        '#' +
        colors.hex2[Math.max(min_value, values[3 * i])] +
        colors.hex2[Math.max(min_value, values[3 * i + 1])] +
        colors.hex2[Math.max(min_value, values[3 * i + 2])]
      )
      const [phi, r] = phi_r_mapping[i]
      led(phi, r, col)
      // ctx.fillStyle = col
      // ctx.fillRect(x*sz, y*sz, sz, sz)
    }
  }

  return {
    listener
  }
}
