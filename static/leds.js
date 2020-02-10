import { h } from './smanmi/util.js'

export const Leds = (output) => {

  let mapping = null
  fetch('/mapping').then(res => res.json()).then(json => mapping = json)

  const width=800, height=600
  const rows=32, cols=64, sz=10

  const disp = h.div().of(
    h.button('pause').of('pause'),
    h.br(),
    h.canvas('leds', {width, height}),
  ).into(output).els

  let paused = false
  disp.pause.addEventListener('click', () => {
    paused = !paused
    disp.pause.textContent = paused ? 'unpause' : 'pause'
  })

  const ctx = disp.leds.getContext('2d')

  function led(phi, r, col) {
    const x = width / 2 + Math.sin(phi) * r * 77
    const y = height / 2 - Math.cos(phi) * r * 77
    ctx.fillStyle = col
    ctx.fillRect(x, y, 3, 3)
  }

  function listener(values) {
    if (paused || !mapping) {
      return
    }
    ctx.clearRect(0, 0, width, height)
    for(let i = 0; i < values.byteLength / 3; i++) {
      const x=i%cols, y=Math.floor(i/cols)
      const col = (
        '#' +
        colors.hex2[values[3 * i]] +
        colors.hex2[values[3 * i + 1]] +
        colors.hex2[values[3 * i + 2]]
      )
      const [phi, r] = mapping[i]
      led(phi, r, col)
      // ctx.fillStyle = col
      // ctx.fillRect(x*sz, y*sz, sz, sz)
    }
  }

  return {
    listener
  }
}
