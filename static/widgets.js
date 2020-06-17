import { h, ui, colors, Lines } from './smanmi/util.js'

export const Sonar = (output) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('sonar'),
    h.button('override').of('override'),
    h.input('sonar', {type: 'range', min: -1, max: 50, value: 50}),
  ).into(output).els

  let override = false
  disp.sonar.style.display = 'none'
  disp.override.addEventListener('click', () => {
    override = !override
    disp.override.classList.toggle('on')
    disp.sonar.style.display = override ? 'block' : 'none'
    update()
  })
  disp.sonar.addEventListener('change', update)

  let sender
  function update() {
    if (!override) {
      if (sender) sender({sonar: null})
      return
    }
    if (sender) sender({sonar: parseInt(disp.sonar.value) / 100})
  }
  function listener(data) {
    if (override) return
    if (data.sonar) disp.sonar.value = 100 * data.sonarsig
  }
  function sendto(sender_) {
    sender = sender_
  }
  return {
    listener,
    sendto,
  }
}

export const Debug = (output, { network, record_timestamps }) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('debug'),
    h.button('download').of('download traces')
  ).into(output).els
  disp.download.addEventListener('click', network.download_timestamps)
  disp.download.style.display = record_timestamps ? 'inline-block' : 'none'
}

export const Recorder = (output, defs) => {
  const disp = h.div({class: 'flex'}).of(
    h.div({class: 'flex widget'}).of(
      h.div({class: 'header'}).of('recorder'),
      h.div('cont').of(
        h.div('record', {class: 'record'}).of(
          h.input('input', {type: 'text'}),
          h.span('name', {class: 'name'}),
          h.button('start', {class: 'start'}).of('start'),
          h.button('stop', {class: 'stop'}).of('stop'),
        ),
        h.div('playback', {class: 'playback'}).of(
          h.div().of(
            h.select('sel').of(h.option({value: ''})),
            h.input('loop', {id: 'loop', type: 'checkbox'}),
            h.label({for: 'loop'}).of('loop'),
          ),
          h.div('playing .h').of(
            h.div('bars', {class: 'bars'}),
            h.div('dt', {class: 'dt'}),
          ),
        ),
      ),
    ),
  ).into(output).els

  disp.input.addEventListener('change', e => {
    disp.name.textContent = e.target.value
  })
  disp.input.addEventListener('keyup', e => {
    if (e.keyCode === 13) {
      disp.start.dispatchEvent(new Event('click'))
    }
  })
  disp.start.addEventListener('click', () => {
    const record = disp.input.value
    if (!record) return
    sender({recorder: { record } })
    disp.sel.value = ''
    disp.record.classList.toggle('recording')
  })
  disp.stop.addEventListener('click', () => {
    sender({recorder: { record: null } })
    disp.record.classList.toggle('recording')
  })

  let recs=defs.recordings, playback, bari
  const names = Object.keys(recs)
  names.sort()
  names.reverse()
  names.forEach(name => {
    h.option({value: name}).of(name).into(disp.sel)
  })
  disp.sel.addEventListener('change', e => {
    playback = e.target.value || null
    disp.playing.classList[playback ? 'remove' : 'add']('h')
    sender({recorder: { playback } })
    disp.bars.innerHTML = ''
    bari = 0
    if (!playback) return
    recs[playback].envelope.forEach(value => {
      const height = Math.max(2, Math.min(150, Math.floor(value**2 * 20)))
      h.span({style: `height:${height}px`}
      ).of(' ').into(disp.bars)
    })
  })
  disp.loop.addEventListener('change', e => {
    const loop = e.target.checked
    sender({recorder: { loop } })
  })
  disp.bars.addEventListener('click', e => {
    if (!playback) return
    const rect = disp.bars.getBoundingClientRect()
    const t = recs[playback].secs * ((e.pageX - rect.left) / rect.width)
    sender({recorder: { t } })
  })

  function secsmin(secs) {
    const min = Math.floor(secs / 60)
    secs = Math.floor(secs) % 60
    return `${min < 10 ? '0'+min : min}:${secs < 10 ? '0'+secs : secs}`
  }
  function update(fraction) {
    const uptobar =  fraction * recs[playback].envelope.length
    while (bari < uptobar) {
      disp.bars.children[bari++].classList.add('on')
    }
    while (bari - 1 >= uptobar) {
      disp.bars.children[--bari].classList.remove('on')
    }
    const secs = recs[playback].secs
    disp.dt.textContent = `${secsmin(fraction*secs)}/${secsmin(secs)}`
    const width = disp.playback.getBoundingClientRect().width
    const left = Math.floor(fraction * width)
  }
  function listener(signals) {
    if (!playback) return
    const t = signals.playback_t
    if ('undefined' === typeof(t)) return
    update(t / recs[playback].secs)
  }
  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    sendto,
    listener,
  }
}

export const Subsample = output => {
  const subsamples = [1, 2, 5, 10, 15, 20, 30]
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('subsample'),
    h.div({class: 'flex'}).of(
      h.button('full', {class: 'on'}).of('full on'),
      h.div('controls', {style: 'display: none'}).of(
        'recorder', h.select('recorder').of(subsamples.map(
          value => h.option({value}).of(`1/${value}`))),
        'animator', h.select('animator').of(subsamples.map(
          value => h.option({value}).of(`1/${value}`))),
      ),
    ),
  ).into(output).els
  disp.recorder.value = disp.animator.value = 10

  let full = true
  disp.full.addEventListener('click', () => {
    full = !full
    disp.full.classList.toggle('on')
    disp.controls.style.display = full ? 'none' : 'block'
    update()
  })
  function update() {
    sender({
      'recorder': {
        subsample: full ? 1 : parseInt(disp.recorder.value),
      },
      'animator': {
        subsample: full ? 1 : parseInt(disp.animator.value),
      },
    })
  }
  disp.recorder.addEventListener('change', update)
  disp.animator.addEventListener('change', update)

  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    sendto,
  }
}

export const Cmd = (output, defs) => {
  const cont = h.div().into(output).el
  let {colors, states} = defs
  colors.unshift('')
  states.unshift('')
  const fcs = [0, 1, 2, 3]
  let disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('cmd'),
    ui.h(
      'fc',
      h.select('fc').of(fcs.map(value =>
        h.option({value}).of(value))),
      'color',
      h.select('color').of(colors.map(value =>
        h.option({value}).of(value))),
      'state',
      h.select('state').of(states.map(value =>
        h.option({value}).of(value))),
    ),
  ).into(cont).els

  disp.fc.addEventListener('change', e => {
    sender({fc: e.target.value === '' ? null : parseInt(e.target.value)})
  })
  disp.color.addEventListener('change', e => {
    const color = e.target.value === '' ? null : e.target.value
    sender({setstate: { color }})
  })
  disp.state.addEventListener('change', e => {
    const state = e.target.value === '' ? null : e.target.value
    sender({setstate: { state }})
  })

  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    sendto,
  }
}

export const Midi = (output) => {
  const notes = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
  ]
  const re = /(\d+): ([A-G]#?)(-?\d+) (.*)/
  const ports = new Map()
  const keys = new Map()
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('midi'),
    ui.v(
      ui.h(
        'port ',
        ui.choice('port', {values: ['0', '1', '2']}),
        'octave ',
        ui.choice('octave', {values: ['0', '1', '2', '3', '4'], initial: '2'}),
      ),
      notes.map(note => h.button(note).of(note)),
      h.div('cont'),
    ),
  ).into(output).els

  let port, octave
  disp.port.change(value => port = value)
  disp.octave.change(value => octave = value)

  notes.forEach(note => {
    disp[note].addEventListener('mousedown', function() {
      this.classList.add('on')
      sender({midi: `${port}: ${note}${octave} on`})
    })
    disp[note].addEventListener('mouseup', function() {
      this.classList.remove('on')
      sender({midi: `${port}: ${note}${octave} off`})
    })
  })

  function value(note) {
    const octave = parseInt(note.substr(note.length - 1))
    const idx = notes.indexOf(note.substr(0, note.length - 1))
    return octave * 12 + idx
  }
  function sort(cont) {
    const arr = Array.from(cont.children).map(child => [
      value(child.textContent), child])
    while (cont.firstChild) cont.removeChild(cont.firstChild)
    arr.sort()
    arr.forEach(idx_child => cont.appendChild(idx_child[1]))
  }

  function listener(signals) {
    if (!signals.midi) return
    const m = re.exec(signals.midi)
    if (m === null) {
      console.warn('Could not parse signals.midi', signals.midi)
      return
    }
    let [_, port, letter, octave, command] = m
    if (!ports.has(port)) {
      ports.set(port, ui.h(
        `${port}:`,
        h.div('cont'),
      ).into(disp.cont).els.cont)
    }
    const key = `${port}:${letter}${octave}`
    if (!keys.has(key)) {
      keys.set(
        key, h.span('.key').of(
          `${letter}${octave}`,
        ).into(ports.get(port)).el)
      sort(ports.get(port))
    }
    if (command === 'on') {
      keys.get(key).classList.add('on')
    } else if (command === 'off') {
      keys.get(key).classList.remove('on')
    }
  }

  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    listener,
    sendto,
  }
}

export const Css = (output) => {
  const width = 200
  const height = 200
  const xlim = [-1, 1]
  const ylim = [-1, 1]
  const r = 8
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('css'),
    ui.v(
      h.div().of(
        ui.toggle('show', true),
        h.button('clear').of('clear'),
      ),
      h.canvas('xy .css', {width, height}),
    ),
  ).into(output).els
  const ctx = disp.xy.getContext('2d')

  disp.show.change(value => {
    disp.xy.classList[value ? 'remove' : 'add']('h')
  })
  disp.clear.addEventListener('click', () => update(null))

  const tox = x => width  * (x - xlim[0]) / (xlim[1] - xlim[0])
  const toy = y => height - height * (y - ylim[0]) / (ylim[1] - ylim[0])
  const fromx = x => xlim[0] + x / width * (xlim[1] - xlim[0])
  const fromy = y => ylim[0] + (height - y) / height * (ylim[1] - ylim[0])

  disp.xy.addEventListener('click', e => {
    update([fromx(e.offsetX), fromy(e.offsetY)])
  })

  let sender
  function update(target_css) {
    if (!sender) return
    sender({target_css})
  }

  function grid(dist) {
    ctx.lineWidth = 1
    ctx.strokeStyle = '#444'
    ctx.beginPath()
    for(let x = Math.floor(xlim[0]) - dist; x <= xlim[1]; x += dist) {
      ctx.moveTo(tox(x), toy(ylim[0]))
      ctx.lineTo(tox(x), toy(ylim[1]))
    }
    for(let y = Math.floor(ylim[0]) - dist; y <= ylim[1]; y += dist) {
      ctx.moveTo(tox(xlim[0]), toy(y))
      ctx.lineTo(tox(xlim[1]), toy(y))
    }
    ctx.stroke()
  }

  const palette = colors.strong_palette
  const cmap = new Map()
  const lcm = new Map()
  function listener(data) {
    ctx.clearRect(0, 0, width, height)
    grid(0.25)
    const { target_css, css } = data

    if (target_css) {
      ctx.strokeStyle = '#f00'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(tox(target_css[0]), toy(target_css[1]), r * 1.4, 0, 2 * Math.PI)
      ctx.stroke()
    }
    if (css) {
      ctx.fillStyle = '#0f0'
      ctx.beginPath()
      ctx.arc(tox(css[0]), toy(css[1]), r, 0, 2 * Math.PI)
      ctx.fill()
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

export const Animation = (output, defs) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('animation'),
    ui.hw(
      defs.animations.map(a => h.button(a).of(a))
    )
  ).into(output).els
  let sender = null
  defs.animations.forEach(a => {
    disp[a].addEventListener('click', () => {
      sender({action: `animation=${a}`})
    })
  })
  function sendto(sender_) {
    sender = sender_
  }
  return {
    sendto,
  }
}

export const Sound = (output, defs) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('sound'),
    ui.hw(
      defs.sounds.map(a => h.button(a).of(a))
    )
  ).into(output).els
  let sender = null
  defs.sounds.forEach(a => {
    disp[a].addEventListener('click', () => {
      sender({action: `sound=${a}`})
    })
  })
  function sendto(sender_) {
    sender = sender_
  }
  return {
    sendto,
  }
}
